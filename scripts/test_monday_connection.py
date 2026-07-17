"""
Read-only Monday.com connectivity diagnostic.

Usage:
    python scripts/test_monday_connection.py

Reads MONDAY_API_TOKEN (or MONDAY_API_KEY), MONDAY_BOARD_ID, and
MONDAY_API_VERSION from environment or a .env file.

Reports:
  - Authentication status
  - Board name and ID
  - Column IDs, titles, and types
  - Up to 5 account names and item IDs
  - Update and reply counts for the first item
  - Any missing permissions or configuration

Does NOT print message bodies, secrets, raw headers, or full API responses.
"""

import os
import sys
from pathlib import Path

# Allow running from repo root or scripts/ directory
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()


def _get_token() -> str:
    token = os.getenv("MONDAY_API_TOKEN", "") or os.getenv("MONDAY_API_KEY", "")
    return token


def _separator(title: str = "") -> None:
    width = 60
    if title:
        print(f"\n{'─' * 4} {title} {'─' * max(0, width - len(title) - 6)}")
    else:
        print("─" * width)


def main() -> int:  # returns exit code
    _separator("Monday.com Connection Diagnostic")

    token = _get_token()
    board_id = os.getenv("MONDAY_BOARD_ID", "")
    api_version = os.getenv("MONDAY_API_VERSION", "2026-01")

    # --- Check required env vars ---
    missing = []
    if not token:
        missing.append("MONDAY_API_TOKEN  (or MONDAY_API_KEY as fallback)")
    if not board_id:
        missing.append("MONDAY_BOARD_ID")

    if missing:
        print("\n[FAIL] Missing required environment variables:")
        for m in missing:
            print(f"       • {m}")
        print("\nSet them in your .env file and re-run.")
        return 1

    print(f"\n  API version : {api_version}")
    print(f"  Board ID    : {board_id}")
    print(f"  Token       : {'*' * 8}  (present)")

    # --- Import provider ---
    try:
        from src.providers.real_monday import MondayCRMProvider
    except ImportError as exc:
        print(f"\n[FAIL] Could not import MondayCRMProvider: {exc}")
        print("       Run: pip install monday-api-python-sdk")
        return 1

    provider = MondayCRMProvider(
        token=token,
        board_id=board_id,
        api_version=api_version,
    )

    # --- Authentication & board access ---
    _separator("1. Authentication & board access")
    status = provider.verify_auth()
    if not status["ok"]:
        print(f"[FAIL] {status['error']}")
        return 1

    print(f"[OK]  Board name   : {status['board_name']}")
    print(f"      Board ID     : {status['board_id']}")
    print(f"      Columns found: {status['column_count']}")

    # --- Columns ---
    _separator("2. Board columns")
    try:
        columns = provider.fetch_board_columns()
        if not columns:
            print("  (no columns found — check board permissions)")
        else:
            print(f"  {'ID':<28} {'Type':<18} Title")
            print(f"  {'─'*28} {'─'*18} {'─'*20}")
            for col in columns:
                print(f"  {(col.id or ''):<28} {(col.type or ''):<18} {col.title or ''}")
    except Exception as exc:
        print(f"[WARN] Could not fetch columns: {exc}")

    # --- Account list (up to 5) ---
    _separator("3. Account list (first 5)")
    try:
        accounts = provider.list_accounts()
        total = len(accounts)
        print(f"  Total items on board: {total}")
        for acct in accounts[:5]:
            print(f"  • {acct['company_name']!r:<40}  id={acct['monday_item_id']}")
        if total > 5:
            print(f"  … and {total - 5} more")
    except Exception as exc:
        print(f"[FAIL] Could not list accounts: {exc}")
        return 1

    if not accounts:
        print("  (board has no items — nothing further to check)")
        _separator()
        print("\n[DONE] Partial check complete — board is accessible but empty.")
        return 0

    # --- Updates and replies for the first item ---
    _separator("4. Updates & replies (first item)")
    first_id = accounts[0]["monday_item_id"]
    first_name = accounts[0]["company_name"]
    print(f"  Checking item: {first_name!r}  (id={first_id})")
    try:
        from src.providers.real_monday import MondayCRMProvider  # already imported
        # Access raw update data via the SDK
        resp = provider._client.updates.fetch_updates_for_item(first_id, limit=100)
        raw_items = (resp.response_data or {}).get("data", {}).get("items", [])
        if not raw_items:
            print("  No update data returned (item may have no updates, or limited permissions).")
        else:
            raw_updates = raw_items[0].get("updates", [])
            reply_total = sum(len(u.get("replies", [])) for u in raw_updates)
            print(f"  Updates : {len(raw_updates)}")
            print(f"  Replies : {reply_total}")
    except Exception as exc:
        print(f"[WARN] Could not fetch updates: {exc}")
        print("       The integration will fall back to empty past_conversations.")

    # --- Column ID configuration hints ---
    _separator("5. Column ID configuration hints")
    print("  Use these stable column IDs in your .env:")
    print()
    print("  MONDAY_COL_INDUSTRY=<id>")
    print("  MONDAY_COL_COMPANY_SIZE=<id>")
    print("  MONDAY_COL_PRODUCTS=<id>")
    print("  MONDAY_COL_QUESTIONS=<id>")
    print("  MONDAY_COL_FOLLOWUPS=<id>")
    print()
    print("  Match the ID column above to the board columns that hold this data.")

    _separator()
    print("\n[DONE] Connection diagnostic complete.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
