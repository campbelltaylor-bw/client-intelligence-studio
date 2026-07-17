from abc import ABC, abstractmethod

from src.models import CRMAccount, WebResearchResult


class CRMProvider(ABC):
    @abstractmethod
    def list_accounts(self) -> list[dict]:
        """Return a list of {monday_item_id, company_name} dicts for the account selector."""

    @abstractmethod
    def get_account(self, monday_item_id: str) -> CRMAccount:
        """Return full CRM data for a given account."""


class WebResearchProvider(ABC):
    @abstractmethod
    def research(self, company_name: str, website_url: str | None) -> WebResearchResult:
        """Return public web research for the given company."""


class BlogCatalogProvider(ABC):
    @abstractmethod
    def load(self) -> list[dict]:
        """Return all blog entries as a list of dicts (one per CSV row)."""
