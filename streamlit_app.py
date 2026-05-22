"""Minimal Streamlit spike for the data-driven-app outreach material.

Single product, hand-rolled form: prove that Streamlit + gspread + Sheets
round-trip works end to end before building the 3-tab教材本体.
"""

from __future__ import annotations

import datetime as dt

import pandas as pd
import streamlit as st

from app.sheets import open_worksheet

ORDERS_SHEET = "orders"
ORDERS_HEADER = ["timestamp", "handle", "product", "price"]

CATALOG = [
    {"name": "たい焼き", "price": 180},
    {"name": "おにぎり", "price": 150},
    {"name": "コーヒー", "price": 250},
]


st.set_page_config(page_title="買い物アプリ（spike）", page_icon=None)
st.title("買い物アプリ（spike）")
st.caption("技術スパイク版: Streamlit + Google Sheets の動作確認用")

ws = open_worksheet(ORDERS_SHEET, header=ORDERS_HEADER)

with st.form("order", clear_on_submit=True):
    handle = st.text_input("ハンドル名", max_chars=20)
    product = st.selectbox(
        "商品",
        options=CATALOG,
        format_func=lambda p: f"{p['name']}（¥{p['price']}）",
    )
    submitted = st.form_submit_button("注文する")

if submitted:
    if not handle.strip():
        st.error("ハンドル名を入力してください")
    else:
        row = [
            dt.datetime.now().isoformat(timespec="seconds"),
            handle.strip(),
            product["name"],
            product["price"],
        ]
        ws.append_row(row)
        st.success(f"{handle.strip()} さんの注文を受け付けました：{product['name']}")

st.divider()
st.subheader("直近の注文")
rows = ws.get_all_values()
if len(rows) <= 1:
    st.info("まだ注文がありません")
else:
    df = pd.DataFrame(rows[1:], columns=rows[0])
    st.dataframe(df.tail(10), use_container_width=True)
