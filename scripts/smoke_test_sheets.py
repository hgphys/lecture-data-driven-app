"""Sheets API smoke test: write one row, read it back, verify match.

Run from public/:
    uv run python scripts/smoke_test_sheets.py
"""

from __future__ import annotations

import datetime as dt
import os
import sys
import uuid
from pathlib import Path

import gspread
from google.oauth2.service_account import Credentials


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

DEFAULT_KEY = (
    Path(__file__).resolve().parents[2]
    / "private"
    / "credentials"
    / "lecture-data-driven-app-abc933c022db.json"
)
DEFAULT_SHEET_ID = "1ouiz0yy8CKdmMRwM7HDLpGXYCXcDP_Nb4VCcKmOB7wA"
WORKSHEET_TITLE = "smoke_test"


def main() -> int:
    key_path = Path(os.environ.get("SA_KEY_PATH", DEFAULT_KEY))
    sheet_id = os.environ.get("SHEET_ID", DEFAULT_SHEET_ID)

    if not key_path.exists():
        print(f"FAIL: SA key not found at {key_path}", file=sys.stderr)
        return 1

    creds = Credentials.from_service_account_file(str(key_path), scopes=SCOPES)
    client = gspread.authorize(creds)
    book = client.open_by_key(sheet_id)
    print(f"Opened spreadsheet: {book.title}")

    try:
        ws = book.worksheet(WORKSHEET_TITLE)
    except gspread.WorksheetNotFound:
        ws = book.add_worksheet(WORKSHEET_TITLE, rows=100, cols=4)
        ws.append_row(["timestamp", "marker", "note", "client"])
        print(f"Created worksheet: {WORKSHEET_TITLE}")

    marker = uuid.uuid4().hex[:8]
    now = dt.datetime.now().isoformat(timespec="seconds")
    row = [now, marker, "smoke-test", "gspread"]
    ws.append_row(row)
    print(f"Wrote row: {row}")

    rows = ws.get_all_values()
    last = rows[-1]
    print(f"Read back last row: {last}")

    assert last[1] == marker, f"marker mismatch: wrote {marker}, read {last[1]}"
    print("OK: write/read round-trip verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
