"""Shopping demo for the data-driven-app outreach material.

Flow:
    0. ログイン     — パスワードでユーザ/教員を振り分け
    1. ユーザ登録   — handle + 学年 + 性別(任意) + 興味カテゴリ(任意)
    2. 買い物体験   — カタログから選んでカート → 注文確定 → 履歴を見る
    3. 教員ページ   — 集計・パスワード管理・データリセット
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app import admin, sheets
from app.catalog import CATALOG, CATEGORIES, find


GRADES = ["高校1年", "高校2年", "高校3年", "卒業生", "保護者", "教員", "地域住民", "その他"]
GENDERS = ["回答しない", "女性", "男性", "その他"]


st.set_page_config(page_title="買い物アプリ", page_icon=None, layout="wide")


def _init_state() -> None:
    ss = st.session_state
    ss.setdefault("auth_role", None)  # None | "user" | "teacher"
    ss.setdefault("step", "register")
    ss.setdefault("handle", "")
    ss.setdefault("cart", {})


def _teacher_password() -> str:
    try:
        return str(st.secrets["teacher_password"])
    except Exception:
        return ""


def _logout() -> None:
    for k in ("auth_role", "step", "handle", "cart", "last_order_id", "_reset_armed"):
        st.session_state.pop(k, None)
    st.session_state.step = "register"
    st.rerun()


def _render_login() -> None:
    st.title("買い物アプリ — ログイン")
    st.caption("教員から共有されたパスワードを入力してください。")
    with st.form("login"):
        pw = st.text_input("パスワード", type="password", max_chars=40)
        submitted = st.form_submit_button("ログイン")
    if not submitted:
        return

    pw = (pw or "").strip()
    if not pw:
        st.error("パスワードを入力してください")
        return

    teacher_pw = _teacher_password()
    if teacher_pw and pw == teacher_pw:
        st.session_state.auth_role = "teacher"
        st.rerun()
        return

    try:
        user_pw = sheets.get_user_password()
    except Exception as e:
        st.error(f"認証情報の取得に失敗しました: {e}")
        return

    if pw == user_pw:
        st.session_state.auth_role = "user"
        st.rerun()
        return

    st.error("パスワードが違います")


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


def _render_user_sidebar() -> None:
    with st.sidebar:
        if st.session_state.handle:
            st.markdown(f"**参加者**: {st.session_state.handle}")
            if st.button("登録をやり直す"):
                for k in ("handle", "cart"):
                    st.session_state.pop(k, None)
                st.session_state.step = "register"
                st.rerun()
            st.divider()
        if st.button("ログアウト"):
            _logout()


def _render_teacher_sidebar() -> None:
    with st.sidebar:
        st.markdown("**役割**: 教員モード")
        if st.button("ログアウト"):
            _logout()


def _render_shop() -> None:
    _render_user_sidebar()
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


def _render_user_flow() -> None:
    if st.session_state.step == "register":
        _render_user_sidebar()
        _render_register()
    else:
        _render_shop()


def main() -> None:
    _init_state()
    role = st.session_state.auth_role
    if role is None:
        _render_login()
    elif role == "teacher":
        _render_teacher_sidebar()
        admin.render()
    else:
        _render_user_flow()


main()
