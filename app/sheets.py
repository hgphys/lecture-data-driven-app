"""Google Sheets access layer.

Credentials are resolved in this order:
  1. st.secrets["gcp_service_account"] + st.secrets["sheet_id"]
     (used on Streamlit Community Cloud and locally when
     .streamlit/secrets.toml is present)
  2. Local SA key JSON under data-driven-app/private/credentials/
     with the fallback sheet ID below
     (used during local development without a secrets.toml)
"""

from __future__ import annotations

import json
from pathlib import Path

import gspread
import streamlit as st
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Repo layout: data-driven-app/public/app/sheets.py
# parents[0]=app, parents[1]=public, parents[2]=data-driven-app
_REPO_ROOT = Path(__file__).resolve().parents[1]
_PRIVATE_ROOT = Path(__file__).resolve().parents[2] / "private"

_FALLBACK_KEY = _PRIVATE_ROOT / "credentials" / "lecture-data-driven-app-abc933c022db.json"
_FALLBACK_SHEET_ID = "1ouiz0yy8CKdmMRwM7HDLpGXYCXcDP_Nb4VCcKmOB7wA"


def _load_config() -> tuple[dict, str]:
    try:
        info = dict(st.secrets["gcp_service_account"])
        sheet_id = st.secrets["sheet_id"]
        return info, sheet_id
    except Exception:
        with open(_FALLBACK_KEY) as f:
            info = json.load(f)
        return info, _FALLBACK_SHEET_ID


@st.cache_resource
def get_client_and_sheet_id() -> tuple[gspread.Client, str]:
    info, sheet_id = _load_config()
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return gspread.authorize(creds), sheet_id


def open_worksheet(title: str, *, header: list[str] | None = None) -> gspread.Worksheet:
    client, sheet_id = get_client_and_sheet_id()
    book = client.open_by_key(sheet_id)
    try:
        return book.worksheet(title)
    except gspread.WorksheetNotFound:
        ws = book.add_worksheet(title, rows=1000, cols=max(4, len(header or [])))
        if header:
            ws.append_row(header)
        return ws
