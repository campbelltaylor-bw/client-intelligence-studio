"""
Read-only Google Sheets connectivity diagnostic.

Usage:
    python scripts/test_google_sheets_connection.py

Reads GOOGLE_SHEET_ID, GOOGLE_SHEET_RANGE, GOOGLE_APPLICATION_CREDENTIALS,
and GOOGLE_CACHE_TTL_SECONDS from environment or a .env file.

Reports:
  - Whether credentials loaded
  - Whether spreadsheet access succeeded
  - Spreadsheet ID (partially redacted)
  - Configured range
  - Detected headers
  - Total rows retrieved
  - Valid blog count, invalid row count, duplicate count
  - Up to five sample blog titles and URLs

Does NOT print:
  - Private keys
  - Full credential JSON
  - Access tokens
  - Raw API responses

This script is strictly read-only.  No write, append, update, or batch-update
calls are made at any point.
"""

import os
import sys
from pathlib import Path

# Allow running from repo root or scripts/ directory
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()


def _separator(title: str = "") -> None:
    width = 64
    if title:
        print(f"\n{'─' * 4} {title} {'─' * max(0, width - len(title) - 6)}")
    else:
        print("─" * width)


def _redact_id(sheet_id: str) -> str:
    if len(sheet_id) <= 8:
        return "****"
    return sheet_id[:4] + "****" + sheet_id[-4:]


def main() -> int:
    _separator("Google Sheets Connection Diagnostic")

    sheet_id = os.getenv("GOOGLE_SHEET_ID", "")
    sheet_range = os.getenv("GOOGLE_SHEET_RANGE", "'Blog Categories'!A:G")
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
    cache_ttl = int(os.getenv("GOOGLE_CACHE_TTL_SECONDS", "300"))

    # --- Check required env vars ---
    missing = []
    if not sheet_id:
        missing.append("GOOGLE_SHEET_ID")
    if not credentials_path:
        missing.append("GOOGLE_APPLICATION_CREDENTIALS")

    if missing:
        print("\n[FAIL] Missing required environment variables:")
        for m in missing:
            print(f"       • {m}")
        print("\nSet them in your .env file and re-run.")
        print("See .env.example for the full list of Google Sheets variables.")
        return 1

    print(f"\n  Sheet ID    : {_redact_id(sheet_id)}")
    print(f"  Range       : {sheet_range}")
    print(f"  Credentials : {credentials_path}")
    print(f"  Cache TTL   : {cache_ttl}s")

    # --- Check credentials file ---
    _separator("1. Credentials")
    creds_path = Path(credentials_path)
    if not creds_path.exists():
        print(f"[FAIL] Credential file not found: {credentials_path}")
        print("       Set GOOGLE_APPLICATION_CREDENTIALS to the path of your service-account JSON.")
        return 1
    print(f"[OK]  Credential file found: {credentials_path}")

    # Verify it parses as valid JSON with expected fields
    import json
    try:
        with open(creds_path) as f:
            creds_json = json.load(f)
        acct_type = creds_json.get("type", "unknown")
        service_email = creds_json.get("client_email", "unknown")
        print(f"[OK]  Credential type   : {acct_type}")
        print(f"[OK]  Service account   : {service_email}")
        if acct_type != "service_account":
            print(
                f"[WARN] Expected type 'service_account', got '{acct_type}'. "
                "This may not work as expected."
            )
    except json.JSONDecodeError as exc:
        print(f"[FAIL] Credential file is not valid JSON: {exc}")
        return 1
    except Exception as exc:
        print(f"[FAIL] Could not read credential file: {exc}")
        return 1

    # --- Import provider ---
    _separator("2. Module imports")
    try:
        from src.providers.google_sheets_blog_catalog import (
            GoogleSheetsBlogRepository,
            GoogleSheetsError,
            _parse_rows,
        )
        print("[OK]  GoogleSheetsBlogRepository imported successfully.")
    except ImportError as exc:
        print(f"[FAIL] Could not import GoogleSheetsBlogRepository: {exc}")
        print("       Run: pip install google-api-python-client google-auth")
        return 1

    # --- Authenticate and fetch ---
    _separator("3. Spreadsheet access")
    try:
        provider = GoogleSheetsBlogRepository(
            spreadsheet_id=sheet_id,
            sheet_range=sheet_range,
            credentials_path=credentials_path,
            cache_ttl_seconds=cache_ttl,
        )
        raw_values = provider._fetch_sheet_values()
        print("[OK]  Spreadsheet access succeeded.")
        print(f"      Rows returned (incl. header): {len(raw_values)}")
    except GoogleSheetsError as exc:
        print(f"[FAIL] {exc}")
        _print_common_fixes(str(exc))
        return 1
    except Exception as exc:
        print(f"[FAIL] Unexpected error: {exc}")
        return 1

    if not raw_values:
        print("[WARN] Sheet returned no data. Check the range and that the sheet has content.")
        return 0

    # --- Headers ---
    _separator("4. Detected headers")
    header_row = raw_values[0]
    print(f"  Raw headers ({len(header_row)} columns):")
    for i, h in enumerate(header_row):
        print(f"    [{i}] {h!r}")

    from src.providers.google_sheets_blog_catalog import _map_headers, LoadStats
    stats_obj = LoadStats()
    col_index = _map_headers(header_row, stats_obj)
    mapped = {v: k for k, v in col_index.items()}  # canonical → col index for display
    if col_index:
        print(f"\n  Mapped to canonical keys:")
        for canonical, idx in col_index.items():
            print(f"    col[{idx}]  →  {canonical!r}")
    else:
        print("[WARN] No headers could be mapped to expected column names.")
        print("       Expected: Blog Title, Blog Category, Data Source, Application,")
        print("                 Asset Class, Post Date, Link to Blog")

    # --- Parse rows ---
    _separator("5. Row parsing")
    data_rows = raw_values[1:]
    print(f"  Data rows to parse: {len(data_rows)}")

    valid_rows, parse_stats = _parse_rows(raw_values)

    print(f"  Valid rows  : {parse_stats.valid}")
    print(f"  Skipped     : {parse_stats.skipped}")
    print(f"  Duplicates  : {parse_stats.duplicates}")

    if parse_stats.warnings:
        print(f"\n  Validation warnings ({len(parse_stats.warnings)}):")
        for w in parse_stats.warnings[:10]:
            print(f"    • {w}")
        if len(parse_stats.warnings) > 10:
            print(f"    … and {len(parse_stats.warnings) - 10} more")

    # --- Sample blogs ---
    if valid_rows:
        _separator("6. Sample blogs (first 5 valid rows)")
        for row in valid_rows[:5]:
            title = row.get("Blog Title", "(no title)")
            url = row.get("Link to Blog", "(no url)")
            category = row.get("Blog Category", "")
            suffix = f"  [{category}]" if category else ""
            print(f"  • {title}{suffix}")
            print(f"    {url}")

    _separator()
    if parse_stats.valid == 0:
        print("\n[WARN] No valid blog rows found. Check column headers and data.")
        return 0

    print(f"\n[DONE] Diagnostic complete. {parse_stats.valid} valid blog(s) ready.\n")
    return 0


def _print_common_fixes(error_msg: str) -> None:
    error_lower = error_msg.lower()
    if "403" in error_msg or "permission" in error_lower:
        print(
            "\n  Fix: Share the spreadsheet with the service-account email\n"
            "       and grant at least Viewer access.\n"
            "       The service-account email is in your JSON file as 'client_email'."
        )
    elif "404" in error_msg or "not found" in error_lower:
        print(
            "\n  Fix: Verify GOOGLE_SHEET_ID is the correct spreadsheet ID.\n"
            "       Copy it from the spreadsheet URL:\n"
            "       https://docs.google.com/spreadsheets/d/<SHEET_ID>/edit"
        )
    elif "credentials" in error_lower or "invalid" in error_lower:
        print(
            "\n  Fix: Ensure GOOGLE_APPLICATION_CREDENTIALS points to a valid\n"
            "       service-account JSON downloaded from Google Cloud Console."
        )
    elif "timeout" in error_lower:
        print("\n  Fix: Check network connectivity and firewall settings.")
    elif "not installed" in error_lower:
        print("\n  Fix: pip install google-api-python-client google-auth")


if __name__ == "__main__":
    sys.exit(main())
