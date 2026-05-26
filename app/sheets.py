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
import time
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

CONFIG_SHEET = "_config"
CONFIG_HEADER = ["key", "value"]
DEFAULT_USER_PASSWORD = "shop"


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


# Google Sheets enforces ~60 read / 60 write requests per minute per user, and
# every visitor shares the single service-account "user". The spreadsheet and
# worksheet handles never change, so we cache them once instead of re-opening
# (which re-fetches metadata) on every helper call. Without this a single
# teacher-dashboard render cost ~15 API calls, and a data reset (which triggers
# several reruns back-to-back) tripped the quota -> APIError.
_TRANSIENT_CODES = {429, 500, 502, 503}


def _retry(fn, *args, _tries: int = 4, _base: float = 0.8, **kwargs):
    """Call ``fn`` retrying transient Sheets API errors with exponential backoff."""
    for attempt in range(_tries):
        try:
            return fn(*args, **kwargs)
        except gspread.exceptions.APIError as e:
            if getattr(e, "code", None) in _TRANSIENT_CODES and attempt < _tries - 1:
                time.sleep(_base * (2 ** attempt))
                continue
            raise


@st.cache_resource
def _spreadsheet() -> gspread.Spreadsheet:
    client, sheet_id = get_client_and_sheet_id()
    return client.open_by_key(sheet_id)


@st.cache_resource
def _worksheet(title: str, header: tuple[str, ...]) -> gspread.Worksheet:
    book = _spreadsheet()
    try:
        return book.worksheet(title)
    except gspread.WorksheetNotFound:
        ws = book.add_worksheet(title, rows=1000, cols=max(len(header), 4))
        ws.append_row(list(header))
        return ws


def users_worksheet() -> gspread.Worksheet:
    return _worksheet(USERS_SHEET, tuple(USERS_HEADER))


def orders_worksheet() -> gspread.Worksheet:
    return _worksheet(ORDERS_SHEET, tuple(ORDERS_HEADER))


def _now_iso() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def handle_exists(handle: str) -> bool:
    ws = users_worksheet()
    handles = _retry(ws.col_values, 1)[1:]
    return handle in handles


def register_user(handle: str, grade: str, gender: str, interests: Iterable[str]) -> None:
    """Append a user row. No-op if the handle already exists."""
    if handle_exists(handle):
        return
    _retry(
        users_worksheet().append_row,
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
    _retry(orders_worksheet().append_rows, rows, value_input_option="USER_ENTERED")
    return order_id


def list_orders_by_handle(handle: str) -> list[dict]:
    ws = orders_worksheet()
    rows = _retry(ws.get_all_records)
    return [r for r in rows if r.get("handle") == handle]


def summary_counts() -> dict:
    users = _retry(users_worksheet().col_values, 1)
    orders = _retry(orders_worksheet().col_values, 2)
    return {
        "users": max(0, len(users) - 1),
        "orders": max(0, len(set(orders[1:]))),
        "items": max(0, len(orders) - 1),
    }


def all_orders() -> list[dict]:
    return _retry(orders_worksheet().get_all_records)


def all_users() -> list[dict]:
    return _retry(users_worksheet().get_all_records)


def _config_worksheet() -> gspread.Worksheet:
    return _worksheet(CONFIG_SHEET, tuple(CONFIG_HEADER))


def _config_get_all() -> dict[str, str]:
    rows = _retry(_config_worksheet().get_all_records)
    return {str(r.get("key", "")): str(r.get("value", "")) for r in rows if r.get("key")}


def get_config(key: str, default: str = "") -> str:
    return _config_get_all().get(key, default)


def set_config(key: str, value: str) -> None:
    ws = _config_worksheet()
    rows = _retry(ws.get_all_records)
    for idx, r in enumerate(rows, start=2):  # row 1 = header
        if str(r.get("key", "")) == key:
            _retry(ws.update_cell, idx, 2, value)
            return
    _retry(ws.append_row, [key, value], value_input_option="USER_ENTERED")


def get_user_password() -> str:
    pw = get_config("user_password", "")
    if not pw:
        set_config("user_password", DEFAULT_USER_PASSWORD)
        return DEFAULT_USER_PASSWORD
    return pw


def set_user_password(new_password: str) -> None:
    set_config("user_password", new_password)


def reset_data() -> None:
    """Clear every data row (below the header) in the users / orders worksheets.

    Uses ``batch_clear`` (one API call per worksheet) rather than ``delete_rows``:
    it wipes the values while keeping the header and the grid size intact, and is
    idempotent (safe to run when the sheets are already empty).
    """
    for ws, header in (
        (users_worksheet(), USERS_HEADER),
        (orders_worksheet(), ORDERS_HEADER),
    ):
        last_col = chr(ord("A") + len(header) - 1)
        _retry(ws.batch_clear, [f"A2:{last_col}"])
