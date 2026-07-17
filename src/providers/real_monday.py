"""
Read-only Monday.com CRM provider using the official monday-api-python-sdk.

All operations are strictly read-only: no mutations, creates, updates,
deletes, archives, moves, or write-backs of any kind.
"""
import re
from typing import Any

from monday_sdk import MondayClient
from monday_sdk.types.api_response_types import Column, Item

from src.models import CRMAccount, TaggedFact
from src.providers.base import CRMProvider

# Default column-ID-to-field mapping.  Users override individual IDs via
# MONDAY_COL_* env vars (see src/config.py).  Keys are model field names;
# values are the stable Monday column IDs on the configured board.
_DEFAULT_COL_MAP: dict[str, str] = {
    "industry": "industry",
    "company_size": "company_size",
    "products_discussed": "products_discussed",
    "open_questions": "open_questions",
    "open_followups": "open_followups",
}


def _strip_html(html: str) -> str:
    """Convert HTML to readable plain text without external dependencies."""
    if not html:
        return ""
    text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    text = re.sub(r"<p[^>]*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = (
        text.replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&nbsp;", " ")
        .replace("&#39;", "'")
        .replace("&quot;", '"')
    )
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


class MondayCRMProvider(CRMProvider):
    """
    Read-only Monday.com CRM provider.

    Maps board items to CRMAccount models using stable column IDs.
    Standard updates and replies are normalized into past_conversations.
    """

    def __init__(
        self,
        token: str,
        board_id: str,
        api_version: str = "2026-01",
        col_map: dict[str, str] | None = None,
    ) -> None:
        self._board_id = str(board_id)
        self._col_map = {**_DEFAULT_COL_MAP, **(col_map or {})}
        self._client = MondayClient(
            token=token,
            headers={"API-Version": api_version},
            debug_mode=False,
        )

    # ------------------------------------------------------------------
    # Diagnostic helpers (used by scripts/test_monday_connection.py)
    # ------------------------------------------------------------------

    def verify_auth(self) -> dict[str, Any]:
        """
        Verify connectivity and board access.  Returns a status dict.
        Never raises — errors are reported in the dict.
        """
        try:
            resp = self._client.boards.fetch_columns_by_board_id(self._board_id)
            boards = resp.data.boards or []
            if not boards:
                return {"ok": False, "error": f"Board {self._board_id!r} not found or not accessible"}
            board = boards[0]
            return {
                "ok": True,
                "board_id": board.id,
                "board_name": board.name,
                "column_count": len(board.columns or []),
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def fetch_board_columns(self) -> list[Column]:
        """Return all columns on the configured board (for diagnostics)."""
        resp = self._client.boards.fetch_columns_by_board_id(self._board_id)
        boards = resp.data.boards or []
        if not boards:
            return []
        return boards[0].columns or []

    # ------------------------------------------------------------------
    # CRMProvider interface
    # ------------------------------------------------------------------

    def list_accounts(self) -> list[dict]:
        """Return [{monday_item_id, company_name}] for all board items."""
        items: list[Item] = self._client.boards.fetch_all_items_by_board_id(self._board_id)
        return [
            {"monday_item_id": item.id, "company_name": item.name or ""}
            for item in items
            if item.id
        ]

    def get_account(self, monday_item_id: str) -> CRMAccount:
        """Fetch and normalize a single board item into a CRMAccount."""
        items: list[Item] = self._client.items.fetch_items_by_id(monday_item_id)
        if not items:
            raise ValueError(f"Monday item {monday_item_id!r} not found")
        item = items[0]

        # Build col_id → text lookup
        col_text: dict[str, str] = {}
        for cv in item.column_values or []:
            if cv.column and cv.column.id:
                text = cv.text or cv.display_value or ""
                if text:
                    col_text[cv.column.id] = text

        def _fact(field: str) -> TaggedFact | None:
            col_id = self._col_map.get(field, field)
            val = col_text.get(col_id, "")
            if not val:
                return None
            return TaggedFact(
                value=val,
                source="CRM_FACT",
                evidence=f"Monday CRM column: {col_id}",
            )

        def _facts(field: str) -> list[TaggedFact]:
            col_id = self._col_map.get(field, field)
            val = col_text.get(col_id, "")
            if not val:
                return []
            return [
                TaggedFact(
                    value=line.strip(),
                    source="CRM_FACT",
                    evidence=f"Monday CRM column: {col_id}",
                )
                for line in val.splitlines()
                if line.strip()
            ]

        conversations = self._fetch_conversations(monday_item_id)

        return CRMAccount(
            company_name=item.name or "",
            monday_item_id=monday_item_id,
            industry=_fact("industry"),
            company_size=_fact("company_size"),
            products_discussed=_facts("products_discussed"),
            open_questions=_facts("open_questions"),
            open_followups=_facts("open_followups"),
            past_conversations=conversations,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_conversations(self, monday_item_id: str) -> list[TaggedFact]:
        """
        Fetch standard updates and replies for an item and normalize them
        into a chronologically sorted list of TaggedFacts.

        Note: standard updates reflect internal team notes posted on the
        Monday.com board.  Full Emails & Activities history requires a
        separate API not currently in scope.
        """
        try:
            resp = self._client.updates.fetch_updates_for_item(monday_item_id, limit=100)
        except Exception:
            return []

        raw_items: list[dict] = (
            (resp.response_data or {}).get("data", {}).get("items", [])
        )
        if not raw_items:
            return []

        raw_updates: list[dict] = raw_items[0].get("updates", [])
        entries: list[tuple[str, TaggedFact]] = []

        for update in raw_updates:
            body = update.get("body") or ""
            text = _strip_html(body).strip()
            if not text:
                continue

            creator = (update.get("creator") or {}).get("name", "Unknown")
            created_at = update.get("created_at", "")
            update_id = update.get("id", "")
            date_prefix = created_at[:10] if created_at else ""

            value = f"{creator} ({date_prefix}): {text}" if date_prefix else f"{creator}: {text}"
            entries.append((
                created_at,
                TaggedFact(
                    value=value,
                    source="CRM_FACT",
                    evidence=f"Monday update #{update_id}",
                ),
            ))

            for reply in update.get("replies", []):
                reply_body = reply.get("body") or ""
                reply_text = _strip_html(reply_body).strip()
                if not reply_text:
                    continue
                reply_creator = (reply.get("creator") or {}).get("name", "Unknown")
                reply_created_at = reply.get("created_at", "")
                reply_id = reply.get("id", "")
                reply_date = reply_created_at[:10] if reply_created_at else ""
                reply_value = (
                    f"{reply_creator} ({reply_date}): {reply_text}"
                    if reply_date
                    else f"{reply_creator}: {reply_text}"
                )
                entries.append((
                    reply_created_at,
                    TaggedFact(
                        value=reply_value,
                        source="CRM_FACT",
                        evidence=f"Monday reply #{reply_id} on update #{update_id}",
                    ),
                ))

        # Sort chronologically — ISO-8601 strings sort lexicographically
        entries.sort(key=lambda x: x[0])
        return [fact for _, fact in entries]


# ---------------------------------------------------------------------------
# Backward-compat alias — runner.py and any external code referencing the
# old class name will continue to work without changes.
# ---------------------------------------------------------------------------
RealMondayProvider = MondayCRMProvider
