"""Google Sheets access layer.

Two worksheets back the app:

- ``users``  : one row per registered participant
- ``orders`` : one row per item in a checked-out cart

Credentials are resolved in this order:

1. ``st.secrets["gcp_service_account"]`` + ``st.secrets["sheet_id"]``
   (Streamlit Community Cloud, or locally with .streamlit/secrets.toml)
2. Local SA key JSON under ``data-driven-app/private/credentials/``
   + a hard-coded fallback sheet id (local development without secrets.toml)
"""

from __future__ import annotations

import datetime as dt
import json
import uuid
from pathlib import Path
from typing import Iterable

import gspread
import streamlit as st
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

_PRIVATE_ROOT = Path(__file__).resolve().parents[2] / "private"
_FALLBACK_KEY = _PRIVATE_ROOT / "credentials" / "lecture-data-driven-app-abc933c022db.json"
_FALLBACK_SHEET_ID = "1ouiz0yy8CKdmMRwM7HDLpGXYCXcDP_Nb4VCcKmOB7wA"

USERS_SHEET = "users"
USERS_HEADER = ["handle", "registered_at", "grade", "gender", "interests"]

ORDERS_SHEET = "orders"
ORDERS_HEADER = ["timestamp", "order_id", "handle", "product", "category", "price", "quantity"]


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


def _open_worksheet(title: str, header: list[str]) -> gspread.Worksheet:
    client, sheet_id = get_client_and_sheet_id()
    book = client.open_by_key(sheet_id)
    try:
        return book.worksheet(title)
    except gspread.WorksheetNotFound:
        ws = book.add_worksheet(title, rows=1000, cols=max(len(header), 4))
        ws.append_row(header)
        return ws


def users_worksheet() -> gspread.Worksheet:
    return _open_worksheet(USERS_SHEET, USERS_HEADER)


def orders_worksheet() -> gspread.Worksheet:
    return _open_worksheet(ORDERS_SHEET, ORDERS_HEADER)


def _now_iso() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def handle_exists(handle: str) -> bool:
    ws = users_worksheet()
    handles = ws.col_values(1)[1:]
    return handle in handles


def register_user(handle: str, grade: str, gender: str, interests: Iterable[str]) -> None:
    """Append a user row. No-op if the handle already exists."""
    if handle_exists(handle):
        return
    users_worksheet().append_row(
        [handle, _now_iso(), grade, gender, ", ".join(interests)],
        value_input_option="USER_ENTERED",
    )


def append_order(handle: str, items: list[dict]) -> str:
    """Append one row per item under a shared ``order_id``.

    Each item dict needs name, category, price, quantity.
    Returns the generated order_id.
    """
    order_id = uuid.uuid4().hex[:8]
    ts = _now_iso()
    rows = [
        [ts, order_id, handle, it["name"], it["category"], it["price"], it["quantity"]]
        for it in items
    ]
    orders_worksheet().append_rows(rows, value_input_option="USER_ENTERED")
    return order_id


def list_orders_by_handle(handle: str) -> list[dict]:
    ws = orders_worksheet()
    rows = ws.get_all_records()
    return [r for r in rows if r.get("handle") == handle]


def summary_counts() -> dict:
    users = users_worksheet().col_values(1)
    orders = orders_worksheet().col_values(2)
    return {
        "users": max(0, len(users) - 1),
        "orders": max(0, len(set(orders[1:]))),
        "items": max(0, len(orders) - 1),
    }
