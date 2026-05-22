"""Shopping demo for the data-driven-app outreach material.

Flow:
    1. ユーザ登録   — handle + 学年 + 性別(任意) + 興味カテゴリ(任意)
    2. 買い物体験   — カタログから選んでカート → 注文確定 → 履歴を見る
    3. 全体カウント — 現在の参加者数・注文数をフッタに表示
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app import sheets
from app.catalog import CATALOG, CATEGORIES, find


GRADES = ["高校1年", "高校2年", "高校3年", "卒業生", "保護者", "教員", "地域住民", "その他"]
GENDERS = ["回答しない", "女性", "男性", "その他"]


st.set_page_config(page_title="買い物アプリ", page_icon=None, layout="wide")


def _init_state() -> None:
    ss = st.session_state
    ss.setdefault("step", "register")
    ss.setdefault("handle", "")
    ss.setdefault("cart", {})  # {product_name: quantity}


def _render_register() -> None:
    st.title("買い物アプリへようこそ")
    st.write("最初に参加者の登録をお願いします。")
    with st.form("register", clear_on_submit=False):
        handle = st.text_input("ハンドル名（ニックネーム）", max_chars=20)
        grade = st.selectbox("学年・所属", options=GRADES, index=0)
        gender = st.radio("性別（任意）", options=GENDERS, horizontal=True, index=0)
        interests = st.multiselect("興味のあるカテゴリ（任意・複数可）", options=CATEGORIES)
        submitted = st.form_submit_button("登録して買い物をはじめる")

    if submitted:
        handle = handle.strip()
        if not handle:
            st.error("ハンドル名を入力してください")
            return
        sheets.register_user(handle, grade, gender, interests)
        st.session_state.handle = handle
        st.session_state.step = "shop"
        st.rerun()


def _cart_items() -> list[dict]:
    out = []
    for name, qty in st.session_state.cart.items():
        if qty <= 0:
            continue
        p = find(name)
        out.append({"name": name, "category": p["category"], "price": p["price"], "quantity": qty})
    return out


def _add_to_cart(name: str) -> None:
    st.session_state.cart[name] = st.session_state.cart.get(name, 0) + 1


def _remove_one(name: str) -> None:
    cur = st.session_state.cart.get(name, 0)
    if cur <= 1:
        st.session_state.cart.pop(name, None)
    else:
        st.session_state.cart[name] = cur - 1


def _clear_cart() -> None:
    st.session_state.cart = {}


def _render_catalog() -> None:
    st.subheader("商品カタログ")
    cols = st.columns(3)
    for idx, p in enumerate(CATALOG):
        col = cols[idx % 3]
        with col.container(border=True):
            st.markdown(f"**{p['name']}**")
            st.caption(p["category"])
            st.write(f"¥{p['price']:,}")
            st.button(
                "カートに入れる",
                key=f"add-{p['name']}",
                on_click=_add_to_cart,
                args=(p["name"],),
                use_container_width=True,
            )


def _render_cart() -> None:
    st.subheader("カート")
    items = _cart_items()
    if not items:
        st.info("カートは空です。左のカタログから選んでください。")
        return

    df = pd.DataFrame(items)
    df["小計"] = df["price"] * df["quantity"]
    display = df.rename(
        columns={"name": "商品", "category": "カテゴリ", "price": "単価", "quantity": "数量"}
    )[["商品", "カテゴリ", "単価", "数量", "小計"]]
    st.dataframe(display, hide_index=True, use_container_width=True)

    total = int(df["小計"].sum())
    st.markdown(f"### 合計: ¥{total:,}")

    for it in items:
        c1, c2 = st.columns([4, 1])
        c1.write(f"・{it['name']} ×{it['quantity']}")
        c2.button(
            "−1",
            key=f"rm-{it['name']}",
            on_click=_remove_one,
            args=(it["name"],),
            use_container_width=True,
        )

    c1, c2 = st.columns([1, 1])
    if c1.button("カートを空にする", use_container_width=True):
        _clear_cart()
        st.rerun()
    if c2.button("注文を確定する", type="primary", use_container_width=True):
        order_id = sheets.append_order(st.session_state.handle, items)
        _clear_cart()
        st.session_state.last_order_id = order_id
        st.rerun()


def _render_history() -> None:
    st.subheader("あなたの注文履歴")
    rows = sheets.list_orders_by_handle(st.session_state.handle)
    if not rows:
        st.info("まだ注文がありません")
        return
    df = pd.DataFrame(rows)
    df = df[["timestamp", "order_id", "product", "category", "price", "quantity"]]
    df.columns = ["時刻", "注文番号", "商品", "カテゴリ", "単価", "数量"]
    st.dataframe(df.iloc[::-1], hide_index=True, use_container_width=True)


def _render_sidebar() -> None:
    with st.sidebar:
        st.markdown(f"**参加者**: {st.session_state.handle}")
        if st.button("登録をやり直す"):
            for k in ("handle", "cart"):
                st.session_state.pop(k, None)
            st.session_state.step = "register"
            st.rerun()
        st.divider()
        st.caption("現在の参加状況")
        try:
            counts = sheets.summary_counts()
            st.metric("参加者数", counts["users"])
            st.metric("注文件数", counts["orders"])
            st.metric("購入アイテム数", counts["items"])
        except Exception as e:
            st.caption(f"集計取得に失敗: {e}")


def _render_shop() -> None:
    _render_sidebar()
    oid = st.session_state.pop("last_order_id", None)
    if oid:
        st.success(f"注文を受け付けました（注文番号: {oid}）")
        st.balloons()
    left, right = st.columns([2, 1])
    with left:
        _render_catalog()
    with right:
        _render_cart()
    st.divider()
    _render_history()


def main() -> None:
    _init_state()
    if st.session_state.step == "register":
        _render_register()
    else:
        _render_shop()


main()
