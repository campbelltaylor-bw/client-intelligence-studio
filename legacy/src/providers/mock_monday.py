import json
from pathlib import Path

from src.models import CRMAccount, TaggedFact
from src.providers.base import CRMProvider


class MockMondayProvider(CRMProvider):
    def __init__(self, data_path: str = "data/mock_monday_accounts.json"):
        with open(data_path) as f:
            raw = json.load(f)
        self._accounts: dict[str, dict] = {a["monday_item_id"]: a for a in raw}
        self._list = [{"monday_item_id": a["monday_item_id"], "company_name": a["company_name"]} for a in raw]

    def list_accounts(self) -> list[dict]:
        return self._list

    def get_account(self, monday_item_id: str) -> CRMAccount:
        raw = self._accounts[monday_item_id]

        def _fact(d: dict | None) -> TaggedFact | None:
            return TaggedFact(**d) if d else None

        def _facts(lst: list[dict]) -> list[TaggedFact]:
            return [TaggedFact(**d) for d in lst]

        return CRMAccount(
            company_name=raw["company_name"],
            monday_item_id=raw["monday_item_id"],
            industry=_fact(raw.get("industry")),
            company_size=_fact(raw.get("company_size")),
            products_discussed=_facts(raw.get("products_discussed", [])),
            open_questions=_facts(raw.get("open_questions", [])),
            open_followups=_facts(raw.get("open_followups", [])),
            past_conversations=_facts(raw.get("past_conversations", [])),
        )
