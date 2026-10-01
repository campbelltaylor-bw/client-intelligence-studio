"""
Unit tests for MondayCRMProvider.

All tests use mocked SDK responses — the real Monday.com API is never called.
"""
from unittest.mock import MagicMock, patch

import pytest

from monday_sdk.types.api_response_types import (
    Board,
    Column,
    ColumnValue,
    Data,
    Group,
    Item,
    MondayApiResponse,
    Update,
    User,
)

from src.models import CRMAccount, TaggedFact
from src.providers.real_monday import MondayCRMProvider, _strip_html


# ---------------------------------------------------------------------------
# Helpers to build SDK dataclass instances
# ---------------------------------------------------------------------------

def _col(col_id: str, title: str = "", col_type: str = "text") -> Column:
    return Column(id=col_id, title=title, type=col_type)


def _cv(col_id: str, text: str, col_title: str = "") -> ColumnValue:
    return ColumnValue(
        column=_col(col_id, col_title),
        text=text,
        value=f'"{text}"',
        type="text",
    )


def _item(item_id: str, name: str, col_values: list | None = None, group_title: str = "") -> Item:
    return Item(
        id=item_id,
        name=name,
        column_values=col_values or [],
        group=Group(id="grp1", title=group_title) if group_title else None,
    )


def _board_resp(board_id: str, board_name: str, columns: list[Column]) -> MondayApiResponse:
    board = Board(id=board_id, name=board_name, columns=columns)
    return MondayApiResponse(data=Data(boards=[board]), response_data={"data": {"boards": []}})


def _updates_resp(updates_raw: list[dict]) -> MondayApiResponse:
    return MondayApiResponse(
        data=Data(),
        response_data={"data": {"items": [{"updates": updates_raw}]}},
    )


def _make_provider(**kwargs) -> MondayCRMProvider:
    defaults = dict(token="test-token", board_id="board-123", api_version="2026-01")
    defaults.update(kwargs)
    with patch("src.providers.real_monday.MondayClient"):
        provider = MondayCRMProvider(**defaults)
    return provider


# ---------------------------------------------------------------------------
# _strip_html
# ---------------------------------------------------------------------------

class TestStripHtml:
    def test_plain_text_unchanged(self):
        assert _strip_html("hello world") == "hello world"

    def test_removes_p_tags(self):
        result = _strip_html("<p>Hello</p><p>World</p>")
        assert "Hello" in result
        assert "World" in result
        assert "<p>" not in result

    def test_br_to_newline(self):
        result = _strip_html("line1<br>line2")
        assert "line1" in result
        assert "line2" in result

    def test_decodes_html_entities(self):
        assert "&amp;" not in _strip_html("a &amp; b")
        assert "&" in _strip_html("a &amp; b")

    def test_empty_string(self):
        assert _strip_html("") == ""

    def test_strips_nested_tags(self):
        result = _strip_html("<b><i>bold italic</i></b>")
        assert result == "bold italic"


# ---------------------------------------------------------------------------
# MondayCRMProvider initialisation
# ---------------------------------------------------------------------------

class TestProviderInit:
    def test_creates_monday_client_with_correct_args(self):
        with patch("src.providers.real_monday.MondayClient") as MockClient:
            MondayCRMProvider(token="tok", board_id="999", api_version="2026-01")
            MockClient.assert_called_once_with(
                token="tok",
                headers={"API-Version": "2026-01"},
                debug_mode=False,
            )

    def test_board_id_stored_as_string(self):
        provider = _make_provider(board_id=12345)
        assert provider._board_id == "12345"

    def test_custom_col_map_merged_with_defaults(self):
        provider = _make_provider(col_map={"industry": "my_industry_col"})
        assert provider._col_map["industry"] == "my_industry_col"
        # Other defaults preserved
        assert provider._col_map["company_size"] == "company_size"


# ---------------------------------------------------------------------------
# verify_auth
# ---------------------------------------------------------------------------

class TestVerifyAuth:
    def test_returns_ok_on_valid_board(self):
        provider = _make_provider()
        cols = [_col("c1", "Industry"), _col("c2", "Size")]
        provider._client.boards.fetch_columns_by_board_id.return_value = _board_resp(
            "board-123", "Sales Board", cols
        )
        result = provider.verify_auth()
        assert result["ok"] is True
        assert result["board_name"] == "Sales Board"
        assert result["column_count"] == 2

    def test_returns_error_when_board_not_found(self):
        provider = _make_provider()
        provider._client.boards.fetch_columns_by_board_id.return_value = MondayApiResponse(
            data=Data(boards=[]), response_data={}
        )
        result = provider.verify_auth()
        assert result["ok"] is False
        assert "not found" in result["error"]

    def test_returns_error_on_sdk_exception(self):
        provider = _make_provider()
        provider._client.boards.fetch_columns_by_board_id.side_effect = RuntimeError("401 Unauthorized")
        result = provider.verify_auth()
        assert result["ok"] is False
        assert "401" in result["error"]


# ---------------------------------------------------------------------------
# fetch_board_columns
# ---------------------------------------------------------------------------

class TestFetchBoardColumns:
    def test_returns_column_list(self):
        provider = _make_provider()
        cols = [_col("ind", "Industry", "text"), _col("sz", "Size", "numbers")]
        provider._client.boards.fetch_columns_by_board_id.return_value = _board_resp(
            "board-123", "Board", cols
        )
        result = provider.fetch_board_columns()
        assert len(result) == 2
        assert result[0].id == "ind"
        assert result[1].title == "Size"

    def test_returns_empty_list_when_no_board(self):
        provider = _make_provider()
        provider._client.boards.fetch_columns_by_board_id.return_value = MondayApiResponse(
            data=Data(boards=[]), response_data={}
        )
        assert provider.fetch_board_columns() == []


# ---------------------------------------------------------------------------
# list_accounts
# ---------------------------------------------------------------------------

class TestListAccounts:
    def test_returns_account_list(self):
        provider = _make_provider()
        provider._client.boards.fetch_all_items_by_board_id.return_value = [
            _item("1", "Acme Corp"),
            _item("2", "Beta Ltd"),
        ]
        accounts = provider.list_accounts()
        assert len(accounts) == 2
        assert accounts[0] == {"monday_item_id": "1", "company_name": "Acme Corp"}
        assert accounts[1] == {"monday_item_id": "2", "company_name": "Beta Ltd"}

    def test_empty_board(self):
        provider = _make_provider()
        provider._client.boards.fetch_all_items_by_board_id.return_value = []
        assert provider.list_accounts() == []

    def test_skips_items_with_no_id(self):
        provider = _make_provider()
        provider._client.boards.fetch_all_items_by_board_id.return_value = [
            _item(None, "Ghost Item"),  # type: ignore[arg-type]
            _item("2", "Real Item"),
        ]
        accounts = provider.list_accounts()
        assert len(accounts) == 1
        assert accounts[0]["monday_item_id"] == "2"

    def test_duplicate_company_names_preserved(self):
        provider = _make_provider()
        provider._client.boards.fetch_all_items_by_board_id.return_value = [
            _item("1", "Duplicate Corp"),
            _item("2", "Duplicate Corp"),
        ]
        accounts = provider.list_accounts()
        assert len(accounts) == 2
        assert accounts[0]["monday_item_id"] == "1"
        assert accounts[1]["monday_item_id"] == "2"


# ---------------------------------------------------------------------------
# get_account — column value parsing
# ---------------------------------------------------------------------------

class TestGetAccountColumns:
    def _setup_item(self, provider: MondayCRMProvider, col_values: list[ColumnValue]) -> None:
        provider._client.items.fetch_items_by_id.return_value = [
            _item("item-1", "Test Corp", col_values)
        ]
        provider._client.updates.fetch_updates_for_item.return_value = _updates_resp([])

    def test_basic_field_mapping(self):
        provider = _make_provider()
        self._setup_item(provider, [
            _cv("industry", "Technology"),
            _cv("company_size", "$1B AUM"),
        ])
        acct = provider.get_account("item-1")
        assert isinstance(acct, CRMAccount)
        assert acct.company_name == "Test Corp"
        assert acct.monday_item_id == "item-1"
        assert acct.industry is not None
        assert acct.industry.value == "Technology"
        assert acct.industry.source == "CRM_FACT"
        assert acct.company_size is not None
        assert acct.company_size.value == "$1B AUM"

    def test_evidence_contains_column_id(self):
        provider = _make_provider()
        self._setup_item(provider, [_cv("industry", "Finance")])
        acct = provider.get_account("item-1")
        assert "industry" in acct.industry.evidence

    def test_multiline_column_split_into_facts(self):
        provider = _make_provider()
        self._setup_item(provider, [
            _cv("products_discussed", "Product A\nProduct B\nProduct C"),
        ])
        acct = provider.get_account("item-1")
        assert len(acct.products_discussed) == 3
        assert acct.products_discussed[0].value == "Product A"
        assert acct.products_discussed[2].value == "Product C"

    def test_missing_column_returns_none_or_empty(self):
        provider = _make_provider()
        self._setup_item(provider, [])  # no columns at all
        acct = provider.get_account("item-1")
        assert acct.industry is None
        assert acct.company_size is None
        assert acct.products_discussed == []
        assert acct.open_questions == []
        assert acct.open_followups == []

    def test_custom_col_map_used(self):
        provider = _make_provider(col_map={"industry": "my_industry_col_xyz"})
        self._setup_item(provider, [
            _cv("my_industry_col_xyz", "Hedge Fund"),
        ])
        acct = provider.get_account("item-1")
        assert acct.industry is not None
        assert acct.industry.value == "Hedge Fund"

    def test_raises_on_item_not_found(self):
        provider = _make_provider()
        provider._client.items.fetch_items_by_id.return_value = []
        with pytest.raises(ValueError, match="not found"):
            provider.get_account("missing-id")

    def test_all_facts_tagged_crm_fact(self):
        provider = _make_provider()
        self._setup_item(provider, [
            _cv("industry", "Asset Manager"),
            _cv("products_discussed", "Product X"),
            _cv("open_questions", "Question 1"),
            _cv("open_followups", "Follow-up 1"),
        ])
        acct = provider.get_account("item-1")
        facts = (
            [acct.industry, acct.company_size]
            + acct.products_discussed
            + acct.open_questions
            + acct.open_followups
        )
        for fact in facts:
            if fact is not None:
                assert fact.source == "CRM_FACT"


# ---------------------------------------------------------------------------
# get_account — update / reply parsing
# ---------------------------------------------------------------------------

class TestGetAccountConversations:
    def _setup(
        self,
        provider: MondayCRMProvider,
        updates_raw: list[dict],
        col_values: list[ColumnValue] | None = None,
    ) -> None:
        provider._client.items.fetch_items_by_id.return_value = [
            _item("item-1", "Corp", col_values or [])
        ]
        provider._client.updates.fetch_updates_for_item.return_value = _updates_resp(updates_raw)

    def test_single_update_normalized(self):
        provider = _make_provider()
        self._setup(provider, [
            {
                "id": "u1",
                "body": "<p>Had a great call today.</p>",
                "created_at": "2024-06-01T10:00:00Z",
                "creator": {"name": "Alice"},
                "replies": [],
            }
        ])
        acct = provider.get_account("item-1")
        assert len(acct.past_conversations) == 1
        fact = acct.past_conversations[0]
        assert fact.source == "CRM_FACT"
        assert "Alice" in fact.value
        assert "great call" in fact.value
        assert "2024-06-01" in fact.value

    def test_replies_included(self):
        provider = _make_provider()
        self._setup(provider, [
            {
                "id": "u1",
                "body": "<p>Update body</p>",
                "created_at": "2024-06-01T10:00:00Z",
                "creator": {"name": "Alice"},
                "replies": [
                    {
                        "id": "r1",
                        "body": "<p>Reply text</p>",
                        "created_at": "2024-06-01T11:00:00Z",
                        "creator": {"name": "Bob"},
                    }
                ],
            }
        ])
        acct = provider.get_account("item-1")
        assert len(acct.past_conversations) == 2
        texts = [f.value for f in acct.past_conversations]
        assert any("Bob" in t for t in texts)
        assert any("Reply text" in t for t in texts)

    def test_conversations_sorted_chronologically(self):
        provider = _make_provider()
        self._setup(provider, [
            {
                "id": "u2",
                "body": "<p>Second update</p>",
                "created_at": "2024-07-01T10:00:00Z",
                "creator": {"name": "Alice"},
                "replies": [],
            },
            {
                "id": "u1",
                "body": "<p>First update</p>",
                "created_at": "2024-06-01T10:00:00Z",
                "creator": {"name": "Alice"},
                "replies": [],
            },
        ])
        acct = provider.get_account("item-1")
        assert len(acct.past_conversations) == 2
        # Earlier date should come first
        assert "First update" in acct.past_conversations[0].value
        assert "Second update" in acct.past_conversations[1].value

    def test_empty_updates_ignored(self):
        provider = _make_provider()
        self._setup(provider, [
            {
                "id": "u1",
                "body": "",
                "created_at": "2024-06-01T10:00:00Z",
                "creator": {"name": "Alice"},
                "replies": [],
            },
            {
                "id": "u2",
                "body": "<p></p>",
                "created_at": "2024-06-02T10:00:00Z",
                "creator": {"name": "Alice"},
                "replies": [],
            },
        ])
        acct = provider.get_account("item-1")
        assert acct.past_conversations == []

    def test_empty_replies_ignored(self):
        provider = _make_provider()
        self._setup(provider, [
            {
                "id": "u1",
                "body": "<p>Good update</p>",
                "created_at": "2024-06-01T10:00:00Z",
                "creator": {"name": "Alice"},
                "replies": [
                    {
                        "id": "r1",
                        "body": "",
                        "created_at": "2024-06-01T11:00:00Z",
                        "creator": {"name": "Bob"},
                    }
                ],
            }
        ])
        acct = provider.get_account("item-1")
        # Only the update, not the empty reply
        assert len(acct.past_conversations) == 1

    def test_updates_api_error_returns_empty_conversations(self):
        provider = _make_provider()
        provider._client.items.fetch_items_by_id.return_value = [_item("item-1", "Corp")]
        provider._client.updates.fetch_updates_for_item.side_effect = RuntimeError("API error")
        acct = provider.get_account("item-1")
        # Should not raise; conversations fall back to empty
        assert acct.past_conversations == []

    def test_no_response_data_returns_empty(self):
        provider = _make_provider()
        provider._client.items.fetch_items_by_id.return_value = [_item("item-1", "Corp")]
        provider._client.updates.fetch_updates_for_item.return_value = MondayApiResponse(
            data=Data(), response_data=None
        )
        acct = provider.get_account("item-1")
        assert acct.past_conversations == []

    def test_reply_evidence_references_parent_update_id(self):
        provider = _make_provider()
        self._setup(provider, [
            {
                "id": "update-99",
                "body": "<p>Parent update</p>",
                "created_at": "2024-06-01T10:00:00Z",
                "creator": {"name": "Alice"},
                "replies": [
                    {
                        "id": "reply-42",
                        "body": "<p>A reply</p>",
                        "created_at": "2024-06-01T12:00:00Z",
                        "creator": {"name": "Bob"},
                    }
                ],
            }
        ])
        acct = provider.get_account("item-1")
        reply_fact = next(f for f in acct.past_conversations if "Bob" in f.value)
        assert "reply-42" in reply_fact.evidence
        assert "update-99" in reply_fact.evidence


# ---------------------------------------------------------------------------
# Config integration
# ---------------------------------------------------------------------------

class TestConfigIntegration:
    def test_mock_crm_repository_uses_mock_provider(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        monkeypatch.setenv("CRM_REPOSITORY", "mock")
        monkeypatch.delenv("MONDAY_API_TOKEN", raising=False)
        monkeypatch.delenv("MONDAY_API_KEY", raising=False)
        monkeypatch.delenv("MONDAY_BOARD_ID", raising=False)

        from src.config import get_config
        config = get_config()
        assert config.crm_repository == "mock"

        from src.pipeline.runner import _build_crm_provider
        from src.providers.mock_monday import MockMondayProvider
        provider = _build_crm_provider(config)
        assert isinstance(provider, MockMondayProvider)

    def test_monday_crm_repository_uses_monday_provider(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        monkeypatch.setenv("CRM_REPOSITORY", "monday")
        monkeypatch.setenv("MONDAY_API_TOKEN", "fake-token")
        monkeypatch.setenv("MONDAY_BOARD_ID", "board-123")

        from src.config import get_config
        config = get_config()
        assert config.crm_repository == "monday"
        assert config.effective_monday_token == "fake-token"

        with patch("src.providers.real_monday.MondayClient"):
            from src.pipeline.runner import _build_crm_provider
            from src.providers.real_monday import MondayCRMProvider
            provider = _build_crm_provider(config)
            assert isinstance(provider, MondayCRMProvider)

    def test_monday_api_key_fallback(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        monkeypatch.setenv("CRM_REPOSITORY", "monday")
        monkeypatch.delenv("MONDAY_API_TOKEN", raising=False)
        monkeypatch.setenv("MONDAY_API_KEY", "legacy-key")
        monkeypatch.setenv("MONDAY_BOARD_ID", "board-123")

        from src.config import get_config
        config = get_config()
        assert config.effective_monday_token == "legacy-key"

    def test_missing_token_raises_when_monday_repository(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        monkeypatch.setenv("CRM_REPOSITORY", "monday")
        monkeypatch.delenv("MONDAY_API_TOKEN", raising=False)
        monkeypatch.delenv("MONDAY_API_KEY", raising=False)
        monkeypatch.setenv("MONDAY_BOARD_ID", "board-123")

        from src.config import get_config
        with pytest.raises(ValueError, match="MONDAY_API_TOKEN"):
            get_config()

    def test_col_map_env_vars_applied(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        monkeypatch.setenv("CRM_REPOSITORY", "monday")
        monkeypatch.setenv("MONDAY_API_TOKEN", "tok")
        monkeypatch.setenv("MONDAY_BOARD_ID", "b1")
        monkeypatch.setenv("MONDAY_COL_INDUSTRY", "col_custom_industry_abc")

        from src.config import get_config
        config = get_config()
        assert config.monday_col_industry == "col_custom_industry_abc"
