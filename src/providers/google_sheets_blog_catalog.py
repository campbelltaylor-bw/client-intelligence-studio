"""
Read-only Google Sheets blog catalog provider.

Authenticates with a service account, reads one configured sheet range,
normalises each row into the same dict format as the CSV catalog, and
returns the results via BlogCatalogProvider.load().

Only the spreadsheets.values.get method is used — no write, append, update,
or batch-update calls are made anywhere in this module.
"""

from __future__ import annotations

import time
import urllib.parse
from dataclasses import dataclass, field
from typing import Any

from src.providers.base import BlogCatalogProvider

# Canonical output keys — must match what claude_scorers.py expects.
_COL_TITLE = "Blog Title"
_COL_CATEGORY = "Blog Category"
_COL_DATA_SOURCE = "Data Source"
_COL_APPLICATION = "Application"
_COL_ASSET_CLASS = "Asset Class"
_COL_POST_DATE = "Post Date"
_COL_URL = "Link to Blog"

# Maps normalised header strings → canonical output key.
_HEADER_MAP: dict[str, str] = {
    "blog title": _COL_TITLE,
    "blog category": _COL_CATEGORY,
    "data source": _COL_DATA_SOURCE,
    "application": _COL_APPLICATION,
    "asset class": _COL_ASSET_CLASS,
    "post date": _COL_POST_DATE,
    "post_date": _COL_POST_DATE,
    "link to blog": _COL_URL,
    "url": _COL_URL,
    "link": _COL_URL,
}

_REQUIRED_CANONICAL = {_COL_TITLE, _COL_URL}
_SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]


@dataclass
class LoadStats:
    valid: int = 0
    skipped: int = 0
    duplicates: int = 0
    source: str = "google_sheets"
    warnings: list[str] = field(default_factory=list)


class GoogleSheetsBlogRepository(BlogCatalogProvider):
    """
    Read-only blog catalog backed by a Google Sheet.

    Falls back gracefully: if credentials or the API call fail, load()
    raises GoogleSheetsError so the caller (runner.py) can fall back to CSV.
    """

    def __init__(
        self,
        spreadsheet_id: str,
        sheet_range: str = "'Blog Categories'!A:G",
        credentials_path: str | None = None,
        cache_ttl_seconds: int = 300,
    ) -> None:
        if not spreadsheet_id:
            raise GoogleSheetsError("GOOGLE_SHEET_ID is required")
        self._spreadsheet_id = spreadsheet_id
        self._sheet_range = sheet_range
        self._credentials_path = credentials_path
        self._cache_ttl = cache_ttl_seconds

        self._cache: list[dict] | None = None
        self._cache_timestamp: float = 0.0
        self._last_stats: LoadStats = LoadStats()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def load(self) -> list[dict]:
        """Return valid blog rows as dicts compatible with the CSV catalog format."""
        if self._cache is not None and (time.monotonic() - self._cache_timestamp) < self._cache_ttl:
            return self._cache

        raw_values = self._fetch_sheet_values()
        rows, stats = _parse_rows(raw_values)
        self._cache = rows
        self._cache_timestamp = time.monotonic()
        self._last_stats = stats
        return rows

    def refresh(self) -> list[dict]:
        """Invalidate the cache and reload from Google Sheets."""
        self._cache = None
        self._cache_timestamp = 0.0
        return self.load()

    @property
    def load_stats(self) -> LoadStats:
        """Stats from the most recent load() call."""
        return self._last_stats

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_credentials(self):
        """Build google-auth credentials from a service-account file."""
        try:
            from google.oauth2 import service_account
        except ImportError as exc:
            raise GoogleSheetsError(
                "google-auth is not installed. Run: pip install google-auth"
            ) from exc

        path = self._credentials_path
        if not path:
            # Try the standard GOOGLE_APPLICATION_CREDENTIALS env var
            import os
            path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")

        if not path:
            # Try Streamlit secrets if available
            path = _try_streamlit_credentials()

        if not path:
            raise GoogleSheetsError(
                "No credentials found. Set GOOGLE_APPLICATION_CREDENTIALS to the path "
                "of your service-account JSON file."
            )

        import pathlib
        p = pathlib.Path(path)
        if not p.exists():
            raise GoogleSheetsError(
                f"Credential file not found: {path}. "
                "Check GOOGLE_APPLICATION_CREDENTIALS in your .env file."
            )

        try:
            creds = service_account.Credentials.from_service_account_file(
                str(p), scopes=_SCOPES
            )
        except Exception as exc:
            raise GoogleSheetsError(
                f"Invalid service-account credentials at {path}: {exc}"
            ) from exc

        return creds

    def _fetch_sheet_values(self) -> list[list[str]]:
        """Call the Sheets API (read-only) and return the raw 2-D value array."""
        try:
            from googleapiclient.discovery import build
            from googleapiclient.errors import HttpError
        except ImportError as exc:
            raise GoogleSheetsError(
                "google-api-python-client is not installed. "
                "Run: pip install google-api-python-client"
            ) from exc

        creds = self._build_credentials()

        try:
            service = build("sheets", "v4", credentials=creds, cache_discovery=False)
            result = (
                service.spreadsheets()
                .values()
                .get(spreadsheetId=self._spreadsheet_id, range=self._sheet_range)
                .execute()
            )
        except HttpError as exc:
            status = exc.status_code if hasattr(exc, "status_code") else "unknown"
            if status == 403:
                raise GoogleSheetsError(
                    f"Permission denied (HTTP 403). Share the spreadsheet with the "
                    f"service-account email and grant at least Viewer access. "
                    f"Spreadsheet ID: {_redact_id(self._spreadsheet_id)}"
                ) from exc
            if status == 404:
                raise GoogleSheetsError(
                    f"Spreadsheet not found (HTTP 404). "
                    f"Check GOOGLE_SHEET_ID. "
                    f"Spreadsheet ID: {_redact_id(self._spreadsheet_id)}"
                ) from exc
            raise GoogleSheetsError(f"Google Sheets API error (HTTP {status}): {exc}") from exc
        except Exception as exc:
            raise GoogleSheetsError(f"Unexpected error calling Google Sheets API: {exc}") from exc

        return result.get("values", [])


# ---------------------------------------------------------------------------
# Row parsing (pure functions — easy to unit-test without Google API)
# ---------------------------------------------------------------------------

def _parse_rows(raw_values: list[list[str]]) -> tuple[list[dict], LoadStats]:
    """
    Convert the raw 2-D value array from the Sheets API into validated dicts.

    Returns (valid_rows, stats).
    """
    stats = LoadStats()
    if not raw_values:
        stats.warnings.append("Sheet returned no data.")
        return [], stats

    header_row = raw_values[0]
    col_index = _map_headers(header_row, stats)

    if _COL_TITLE not in col_index or _COL_URL not in col_index:
        stats.warnings.append(
            f"Required headers not found. Got: {header_row}. "
            "Expected 'Blog Title' and 'Link to Blog' (or equivalents)."
        )
        return [], stats

    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    valid_rows: list[dict] = []

    for row_num, row in enumerate(raw_values[1:], start=2):
        result = _parse_single_row(row, col_index, row_num, seen_urls, seen_titles, stats)
        if result is not None:
            valid_rows.append(result)
            seen_urls.add(result[_COL_URL].lower())
            seen_titles.add(result[_COL_TITLE].strip().lower())
            stats.valid += 1

    return valid_rows, stats


def _map_headers(header_row: list[str], stats: LoadStats) -> dict[str, int]:
    """Return {canonical_key: column_index} from the raw header row."""
    col_index: dict[str, int] = {}
    for i, raw_header in enumerate(header_row):
        normalised = raw_header.strip().lower()
        canonical = _HEADER_MAP.get(normalised)
        if canonical and canonical not in col_index:
            col_index[canonical] = i
    return col_index


def _parse_single_row(
    row: list[str],
    col_index: dict[str, int],
    row_num: int,
    seen_urls: set[str],
    seen_titles: set[str],
    stats: LoadStats,
) -> dict | None:
    """Validate and normalise one data row. Returns None if the row should be skipped."""

    def get(canonical_key: str) -> str:
        idx = col_index.get(canonical_key)
        if idx is None or idx >= len(row):
            return ""
        return str(row[idx]).strip()

    # Skip blank rows (all cells empty)
    if not any(str(c).strip() for c in row):
        return None

    title = get(_COL_TITLE)
    url = get(_COL_URL)

    if not title:
        stats.skipped += 1
        stats.warnings.append(f"Row {row_num}: skipped — missing title.")
        return None

    if not url:
        stats.skipped += 1
        stats.warnings.append(f"Row {row_num}: skipped — missing URL (title={title!r}).")
        return None

    if not _is_valid_url(url):
        stats.skipped += 1
        stats.warnings.append(
            f"Row {row_num}: skipped — invalid URL {url!r} (title={title!r}). "
            "Only http/https URLs are accepted."
        )
        return None

    if url.lower() in seen_urls:
        stats.skipped += 1
        stats.duplicates += 1
        stats.warnings.append(f"Row {row_num}: skipped — duplicate URL {url!r}.")
        return None

    if title.strip().lower() in seen_titles:
        stats.skipped += 1
        stats.duplicates += 1
        stats.warnings.append(f"Row {row_num}: skipped — duplicate title {title!r}.")
        return None

    return {
        _COL_TITLE: title,
        _COL_CATEGORY: get(_COL_CATEGORY),
        _COL_DATA_SOURCE: get(_COL_DATA_SOURCE),
        _COL_APPLICATION: get(_COL_APPLICATION),
        _COL_ASSET_CLASS: get(_COL_ASSET_CLASS),
        _COL_POST_DATE: get(_COL_POST_DATE),
        _COL_URL: url,
        "source_system": "google_sheets",
    }


def _is_valid_url(url: str) -> bool:
    try:
        parsed = urllib.parse.urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


def _redact_id(sheet_id: str) -> str:
    if len(sheet_id) <= 8:
        return "****"
    return sheet_id[:4] + "****" + sheet_id[-4:]


def _try_streamlit_credentials() -> str:
    """Return a credentials file path from st.secrets if available, else empty string."""
    try:
        import json
        import os
        import tempfile

        import streamlit as st  # noqa: PLC0415

        if "gcp_service_account" not in st.secrets:
            return ""
        creds_dict = dict(st.secrets["gcp_service_account"])
        # Write to a temp file so google-auth can load it the normal way
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w") as f:
            json.dump(creds_dict, f)
        return path
    except Exception:
        return ""


class GoogleSheetsError(RuntimeError):
    """Raised when the Google Sheets integration fails (config, auth, or API error)."""
