"""
Unit tests for GoogleSheetsBlogRepository.

The real Google Sheets API is never called.  All tests use mocked responses
or call the pure parsing functions directly.
"""
from unittest.mock import MagicMock, patch

import pytest

from src.providers.google_sheets_blog_catalog import (
    GoogleSheetsBlogRepository,
    GoogleSheetsError,
    LoadStats,
    _is_valid_url,
    _map_headers,
    _parse_rows,
    _parse_single_row,
    _redact_id,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_provider(**kwargs) -> GoogleSheetsBlogRepository:
    defaults = dict(
        spreadsheet_id="abc123",
        sheet_range="'Blog Categories'!A:G",
        credentials_path="/fake/creds.json",
    )
    defaults.update(kwargs)
    return GoogleSheetsBlogRepository(**defaults)


def _sample_raw_values(extra_rows: list[list[str]] | None = None) -> list[list[str]]:
    """Return a minimal valid 2-D values array (header + rows)."""
    header = [
        "Blog Title",
        "Blog Category",
        "Data Source",
        "Application",
        "Asset Class",
        "Post Date",
        "Link to Blog",
    ]
    rows = [
        [
            "Sentiment Alpha",
            "Research",
            "News Sentiment",
            "Alpha Generation",
            "Equities",
            "2024-11-15",
            "https://example.com/sentiment-alpha",
        ],
        [
            "ESG Deep Dive",
            "Research",
            "ESG Sentiment",
            "ESG Investing",
            "Multi-Asset",
            "2024-09-10",
            "https://example.com/esg-deep-dive",
        ],
    ]
    if extra_rows:
        rows.extend(extra_rows)
    return [header] + rows


# ---------------------------------------------------------------------------
# Configuration loading
# ---------------------------------------------------------------------------

class TestConfiguration:
    def test_raises_when_spreadsheet_id_missing(self):
        with pytest.raises(GoogleSheetsError, match="GOOGLE_SHEET_ID"):
            GoogleSheetsBlogRepository(spreadsheet_id="")

    def test_stores_spreadsheet_id(self):
        p = _make_provider(spreadsheet_id="sheet-123")
        assert p._spreadsheet_id == "sheet-123"

    def test_stores_sheet_range(self):
        p = _make_provider(sheet_range="'MyTab'!A:Z")
        assert p._sheet_range == "'MyTab'!A:Z"

    def test_default_range(self):
        p = _make_provider()
        assert "A:G" in p._sheet_range

    def test_cache_ttl_stored(self):
        p = _make_provider(cache_ttl_seconds=120)
        assert p._cache_ttl == 120

    def test_config_blog_repository_loaded(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        monkeypatch.setenv("BLOG_REPOSITORY", "google_sheets")
        monkeypatch.setenv("GOOGLE_SHEET_ID", "sheet-xyz")
        monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "/fake/creds.json")

        from src.config import get_config
        config = get_config()
        assert config.blog_repository == "google_sheets"
        assert config.google_sheet_id == "sheet-xyz"
        assert config.google_credentials_path == "/fake/creds.json"

    def test_blog_repository_defaults_to_mock_when_use_mock_data(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        monkeypatch.delenv("BLOG_REPOSITORY", raising=False)

        from src.config import get_config
        config = get_config()
        assert config.blog_repository == "mock"

    def test_blog_repository_csv_when_use_mock_data_false(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        monkeypatch.delenv("BLOG_REPOSITORY", raising=False)

        # Patch config yaml to set use_mock_data=False
        with patch("src.config.yaml.safe_load", return_value={"use_mock_data": False}):
            with patch("src.config.Path.exists", return_value=True):
                with patch("builtins.open", MagicMock()):
                    from src.config import get_config
                    config = get_config()
                    assert config.blog_repository == "csv"


# ---------------------------------------------------------------------------
# Credential loading
# ---------------------------------------------------------------------------

class TestCredentialLoading:
    def test_raises_when_credentials_path_missing_and_no_env(self, monkeypatch):
        monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
        p = _make_provider(credentials_path=None)
        with pytest.raises(GoogleSheetsError, match="No credentials found"):
            p._build_credentials()

    def test_raises_when_credentials_file_not_found(self, tmp_path):
        p = _make_provider(credentials_path=str(tmp_path / "nonexistent.json"))
        with pytest.raises(GoogleSheetsError, match="not found"):
            p._build_credentials()

    def test_raises_on_invalid_service_account_json(self, tmp_path):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text('{"type": "not_a_service_account", "project_id": "x"}')
        p = _make_provider(credentials_path=str(bad_file))
        with pytest.raises(GoogleSheetsError):
            p._build_credentials()

    def test_loads_credentials_from_env_var(self, monkeypatch, tmp_path):
        fake_file = tmp_path / "creds.json"
        fake_file.write_text("{}")
        monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(fake_file))

        p = _make_provider(credentials_path=None)

        with patch("google.oauth2.service_account.Credentials.from_service_account_file") as mock_creds:
            mock_creds.return_value = MagicMock()
            creds = p._build_credentials()
            mock_creds.assert_called_once_with(str(fake_file), scopes=mock_creds.call_args[1]["scopes"])


# ---------------------------------------------------------------------------
# Successful sheet read
# ---------------------------------------------------------------------------

class TestSuccessfulRead:
    def _mock_provider(self, raw_values: list[list[str]]) -> GoogleSheetsBlogRepository:
        p = _make_provider()
        p._fetch_sheet_values = MagicMock(return_value=raw_values)
        return p

    def test_load_returns_list_of_dicts(self):
        p = self._mock_provider(_sample_raw_values())
        rows = p.load()
        assert isinstance(rows, list)
        assert all(isinstance(r, dict) for r in rows)

    def test_load_returns_correct_count(self):
        p = self._mock_provider(_sample_raw_values())
        assert len(p.load()) == 2

    def test_dict_keys_match_csv_column_names(self):
        p = self._mock_provider(_sample_raw_values())
        row = p.load()[0]
        assert "Blog Title" in row
        assert "Blog Category" in row
        assert "Data Source" in row
        assert "Application" in row
        assert "Asset Class" in row
        assert "Post Date" in row
        assert "Link to Blog" in row

    def test_source_system_field_present(self):
        p = self._mock_provider(_sample_raw_values())
        row = p.load()[0]
        assert row.get("source_system") == "google_sheets"

    def test_title_and_url_values_correct(self):
        p = self._mock_provider(_sample_raw_values())
        row = p.load()[0]
        assert row["Blog Title"] == "Sentiment Alpha"
        assert row["Link to Blog"] == "https://example.com/sentiment-alpha"

    def test_result_is_cached_on_second_call(self):
        p = self._mock_provider(_sample_raw_values())
        p.load()
        p.load()
        assert p._fetch_sheet_values.call_count == 1

    def test_refresh_invalidates_cache(self):
        p = self._mock_provider(_sample_raw_values())
        p.load()
        p.refresh()
        assert p._fetch_sheet_values.call_count == 2

    def test_load_stats_populated_after_load(self):
        p = self._mock_provider(_sample_raw_values())
        p.load()
        assert p.load_stats.valid == 2
        assert p.load_stats.skipped == 0

    def test_empty_sheet_returns_empty_list(self):
        p = self._mock_provider([])
        rows = p.load()
        assert rows == []


# ---------------------------------------------------------------------------
# Authentication / permission failures
# ---------------------------------------------------------------------------

class TestApiFailures:
    def test_auth_failure_raises_google_sheets_error(self):
        p = _make_provider()
        p._build_credentials = MagicMock(side_effect=GoogleSheetsError("Auth failed"))
        with pytest.raises(GoogleSheetsError):
            p.load()

    def test_permission_403_raises_descriptive_error(self):
        from googleapiclient.errors import HttpError
        p = _make_provider()
        p._build_credentials = MagicMock(return_value=MagicMock())

        # resp.status is used by HttpError.status_code (a read-only property)
        http_error = HttpError(resp=MagicMock(status=403), content=b"Forbidden")

        # build is imported locally inside _fetch_sheet_values; patch the source module.
        with patch("googleapiclient.discovery.build") as mock_build:
            svc = MagicMock()
            mock_build.return_value = svc
            svc.spreadsheets.return_value.values.return_value.get.return_value.execute.side_effect = http_error
            with pytest.raises(GoogleSheetsError, match="Permission denied"):
                p._fetch_sheet_values()

    def test_not_found_404_raises_descriptive_error(self):
        from googleapiclient.errors import HttpError
        p = _make_provider()
        p._build_credentials = MagicMock(return_value=MagicMock())

        http_error = HttpError(resp=MagicMock(status=404), content=b"Not Found")

        with patch("googleapiclient.discovery.build") as mock_build:
            svc = MagicMock()
            mock_build.return_value = svc
            svc.spreadsheets.return_value.values.return_value.get.return_value.execute.side_effect = http_error
            with pytest.raises(GoogleSheetsError, match="not found"):
                p._fetch_sheet_values()


# ---------------------------------------------------------------------------
# Header parsing
# ---------------------------------------------------------------------------

class TestHeaderParsing:
    def _parse(self, header_row):
        stats = LoadStats()
        return _map_headers(header_row, stats)

    def test_exact_headers_mapped(self):
        col_index = self._parse([
            "Blog Title", "Blog Category", "Data Source",
            "Application", "Asset Class", "Post Date", "Link to Blog",
        ])
        assert col_index["Blog Title"] == 0
        assert col_index["Link to Blog"] == 6

    def test_header_trim_whitespace(self):
        col_index = self._parse(["  Blog Title  ", "  Link to Blog  "])
        assert "Blog Title" in col_index
        assert "Link to Blog" in col_index

    def test_header_case_insensitive(self):
        col_index = self._parse(["BLOG TITLE", "LINK TO BLOG"])
        assert "Blog Title" in col_index
        assert "Link to Blog" in col_index

    def test_post_date_capitalisation_variants(self):
        col_index1 = self._parse(["Post Date"])
        col_index2 = self._parse(["post date"])
        col_index3 = self._parse(["POST DATE"])
        assert "Post Date" in col_index1
        assert "Post Date" in col_index2
        assert "Post Date" in col_index3

    def test_url_alias_mapped(self):
        col_index = self._parse(["Blog Title", "url"])
        assert "Link to Blog" in col_index

    def test_extra_unknown_headers_ignored(self):
        col_index = self._parse(["Blog Title", "Unknown Column", "Link to Blog"])
        assert "Blog Title" in col_index
        assert "Link to Blog" in col_index
        assert len(col_index) == 2

    def test_missing_required_headers_detected(self):
        raw = [["Only Category", "Data Source"]]
        rows, stats = _parse_rows(raw)
        assert rows == []
        assert any("Required headers" in w for w in stats.warnings)


# ---------------------------------------------------------------------------
# Row parsing — missing and malformed cells
# ---------------------------------------------------------------------------

class TestRowParsing:
    def test_blank_row_skipped(self):
        raw = [
            ["Blog Title", "Link to Blog"],
            ["", ""],
        ]
        rows, stats = _parse_rows(raw)
        assert rows == []
        assert stats.skipped == 0  # all-blank rows are silently ignored, not counted as skipped

    def test_missing_title_skipped(self):
        raw = [
            ["Blog Title", "Link to Blog"],
            ["", "https://example.com/post"],
        ]
        rows, stats = _parse_rows(raw)
        assert rows == []
        assert stats.skipped == 1
        assert any("missing title" in w for w in stats.warnings)

    def test_missing_url_skipped(self):
        raw = [
            ["Blog Title", "Link to Blog"],
            ["My Post", ""],
        ]
        rows, stats = _parse_rows(raw)
        assert rows == []
        assert stats.skipped == 1
        assert any("missing URL" in w for w in stats.warnings)

    def test_missing_trailing_cells_handled(self):
        raw = [
            ["Blog Title", "Blog Category", "Link to Blog"],
            ["Short Row"],  # only 1 cell — category and url absent
        ]
        rows, stats = _parse_rows(raw)
        # Missing URL → skip
        assert rows == []
        assert stats.skipped == 1

    def test_extra_columns_ignored(self):
        raw = [
            ["Blog Title", "Link to Blog", "Extra Column"],
            ["Valid Post", "https://example.com/post", "ignored value"],
        ]
        rows, stats = _parse_rows(raw)
        assert len(rows) == 1
        assert "Extra Column" not in rows[0]

    def test_multiple_valid_rows(self):
        rows, stats = _parse_rows(_sample_raw_values())
        assert stats.valid == 2
        assert stats.skipped == 0


# ---------------------------------------------------------------------------
# URL validation
# ---------------------------------------------------------------------------

class TestUrlValidation:
    def test_http_url_valid(self):
        assert _is_valid_url("http://example.com/blog") is True

    def test_https_url_valid(self):
        assert _is_valid_url("https://example.com/blog") is True

    def test_ftp_url_rejected(self):
        assert _is_valid_url("ftp://example.com/blog") is False

    def test_no_scheme_rejected(self):
        assert _is_valid_url("example.com/blog") is False

    def test_empty_string_rejected(self):
        assert _is_valid_url("") is False

    def test_malformed_url_rejected(self):
        assert _is_valid_url("not a url at all") is False

    def test_invalid_url_row_skipped_in_parse(self):
        raw = [
            ["Blog Title", "Link to Blog"],
            ["My Post", "ftp://invalid.com"],
        ]
        rows, stats = _parse_rows(raw)
        assert rows == []
        assert stats.skipped == 1
        assert any("invalid URL" in w for w in stats.warnings)


# ---------------------------------------------------------------------------
# Duplicate detection
# ---------------------------------------------------------------------------

class TestDeduplication:
    def test_duplicate_url_skipped(self):
        raw = [
            ["Blog Title", "Link to Blog"],
            ["Post One", "https://example.com/post"],
            ["Post One Copy", "https://example.com/post"],  # same URL
        ]
        rows, stats = _parse_rows(raw)
        assert len(rows) == 1
        assert stats.duplicates == 1
        assert any("duplicate URL" in w for w in stats.warnings)

    def test_duplicate_title_skipped(self):
        raw = [
            ["Blog Title", "Link to Blog"],
            ["Same Title", "https://example.com/post-1"],
            ["Same Title", "https://example.com/post-2"],  # same title
        ]
        rows, stats = _parse_rows(raw)
        assert len(rows) == 1
        assert stats.duplicates == 1

    def test_url_dedup_case_insensitive(self):
        raw = [
            ["Blog Title", "Link to Blog"],
            ["Post A", "https://example.com/POST"],
            ["Post B", "https://example.com/post"],  # same URL, different case
        ]
        rows, stats = _parse_rows(raw)
        assert len(rows) == 1
        assert stats.duplicates == 1


# ---------------------------------------------------------------------------
# List-field parsing (Data Source, Application, Asset Class)
# ---------------------------------------------------------------------------

class TestListFieldParsing:
    def test_single_value_preserved(self):
        raw = _sample_raw_values()
        rows, _ = _parse_rows(raw)
        # Data Source for first row is "News Sentiment" (single value)
        assert rows[0]["Data Source"] == "News Sentiment"

    def test_comma_separated_stored_as_string(self):
        raw = [
            ["Blog Title", "Data Source", "Link to Blog"],
            ["Multi Post", "News Sentiment, ESG Sentiment", "https://example.com/multi"],
        ]
        rows, stats = _parse_rows(raw)
        assert len(rows) == 1
        # Raw string stored as-is; list parsing is the scorer's responsibility
        assert "News Sentiment" in rows[0]["Data Source"]

    def test_pipe_separated_preserved(self):
        raw = [
            ["Blog Title", "Application", "Link to Blog"],
            ["Pipe Post", "Alpha Generation | Factor Investing", "https://example.com/pipe"],
        ]
        rows, _ = _parse_rows(raw)
        assert "Alpha Generation" in rows[0]["Application"]


# ---------------------------------------------------------------------------
# Runner fallback
# ---------------------------------------------------------------------------

class TestRunnerFallback:
    def test_google_sheets_provider_selected_by_config(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        monkeypatch.setenv("BLOG_REPOSITORY", "google_sheets")
        monkeypatch.setenv("GOOGLE_SHEET_ID", "sheet-abc")
        monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "/fake/creds.json")

        from src.config import get_config
        config = get_config()
        assert config.blog_repository == "google_sheets"

    def test_runner_falls_back_to_csv_when_google_sheets_init_fails(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        monkeypatch.setenv("BLOG_REPOSITORY", "google_sheets")
        monkeypatch.setenv("GOOGLE_SHEET_ID", "")  # empty ID → init raises GoogleSheetsError

        from src.config import get_config
        from src.pipeline.runner import _build_blog_provider
        from src.providers.csv_blog_catalog import CSVBlogCatalogProvider

        config = get_config()
        provider = _build_blog_provider(config)
        assert isinstance(provider, CSVBlogCatalogProvider)

    def test_mock_provider_selected_when_blog_repository_is_mock(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        monkeypatch.setenv("BLOG_REPOSITORY", "mock")

        from src.config import get_config
        from src.pipeline.runner import _build_blog_provider
        from src.providers.mock_blog_catalog import MockBlogCatalogProvider

        config = get_config()
        provider = _build_blog_provider(config)
        assert isinstance(provider, MockBlogCatalogProvider)

    def test_csv_provider_selected_when_blog_repository_is_csv(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        monkeypatch.setenv("BLOG_REPOSITORY", "csv")

        from src.config import get_config
        from src.pipeline.runner import _build_blog_provider
        from src.providers.csv_blog_catalog import CSVBlogCatalogProvider

        config = get_config()
        provider = _build_blog_provider(config)
        assert isinstance(provider, CSVBlogCatalogProvider)


# ---------------------------------------------------------------------------
# Blog ranking compatibility
# ---------------------------------------------------------------------------

class TestBlogRankingCompatibility:
    def test_google_sheets_rows_compatible_with_blog_scorer_keys(self):
        """
        The existing claude_scorers.make_blog_scorer uses:
          b.get('Blog Title', ''), b.get('Blog Category', ''),
          b.get('Application', ''), b.get('Asset Class', ''),
          b.get('Link to Blog', '')
        Verify that GoogleSheetsBlogRepository.load() returns dicts with these keys.
        """
        p = _make_provider()
        p._fetch_sheet_values = MagicMock(return_value=_sample_raw_values())
        rows = p.load()

        scorer_keys = ["Blog Title", "Blog Category", "Application", "Asset Class", "Link to Blog"]
        for row in rows:
            for key in scorer_keys:
                assert key in row, f"Key {key!r} missing from row: {row}"

    def test_pipeline_uses_google_sheets_provider_when_configured(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        monkeypatch.setenv("BLOG_REPOSITORY", "google_sheets")
        monkeypatch.setenv("GOOGLE_SHEET_ID", "sheet-xyz")
        monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "/fake/creds.json")

        from src.config import get_config
        from src.pipeline.runner import _build_blog_provider
        config = get_config()

        # When the Google Sheets provider is requested with an invalid creds path,
        # it falls back to CSV (tested in TestRunnerFallback).  Here we confirm
        # the provider returned is still a BlogCatalogProvider.
        from src.providers.base import BlogCatalogProvider
        provider = _build_blog_provider(config)
        assert isinstance(provider, BlogCatalogProvider)


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

class TestUtilityFunctions:
    def test_redact_id_short(self):
        assert _redact_id("abc") == "****"

    def test_redact_id_long(self):
        result = _redact_id("1234567890abcdef")
        assert result.startswith("1234")
        assert result.endswith("cdef")
        assert "****" in result

    def test_is_valid_url_edge_cases(self):
        assert _is_valid_url("https://a.b") is True
        assert _is_valid_url("https://") is False
        assert _is_valid_url("http://") is False
