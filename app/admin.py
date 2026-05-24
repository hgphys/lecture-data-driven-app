"""Teacher dashboard.

Rendered only when ``st.session_state.auth_role == "teacher"``.

Provides:

- live metrics (participants, orders, items)
- recent orders table
- product / grade-by-category breakdowns
- user password reset
- data reset (wipes ``users`` / ``orders`` rows below header)
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app import sheets


def _metrics() -> None:
    try:
        counts = sheets.summary_counts()
    except Exception as e:
        st.warning(f"集計取得に失敗: {e}")
        return
    c1, c2, c3 = st.columns(3)
    c1.metric("参加者数", counts["users"])
    c2.metric("注文件数", counts["orders"])
    c3.metric("購入アイテム数", counts["items"])


def _recent_orders(orders_df: pd.DataFrame, n: int = 10) -> None:
    st.subheader(f"最近の注文（末尾 {n} 件）")
    if orders_df.empty:
        st.info("まだ注文はありません")
        return
    df = orders_df.tail(n).iloc[::-1].copy()
    df = df[["timestamp", "order_id", "handle", "product", "category", "price", "quantity"]]
    df.columns = ["時刻", "注文番号", "ハンドル", "商品", "カテゴリ", "単価", "数量"]
    st.dataframe(df, hide_index=True, use_container_width=True)


def _product_ranking(orders_df: pd.DataFrame) -> None:
    st.subheader("商品別 売れ筋（数量）")
    if orders_df.empty:
        st.info("注文データが無いため表示できません")
        return
    qty = (
        orders_df.groupby("product")["quantity"].sum()
        .sort_values(ascending=False)
    )
    st.bar_chart(qty)


def _grade_category(orders_df: pd.DataFrame, users_df: pd.DataFrame) -> None:
    st.subheader("学年 × カテゴリ 購買傾向")
    if orders_df.empty or users_df.empty:
        st.info("登録・注文データが揃っていないため表示できません")
        return
    merged = orders_df.merge(users_df[["handle", "grade"]], on="handle", how="left")
    pivot = (
        merged.groupby(["grade", "category"])["quantity"].sum()
        .unstack(fill_value=0)
    )
    st.dataframe(pivot, use_container_width=True)


def _password_section() -> None:
    st.subheader("ユーザパスワードの管理")
    current = sheets.get_user_password()
    st.write(f"現在のパスワード: `{current}`")
    st.caption("ユーザが買い物アプリにログインするときに入力するパスワードです。生徒には授業開始時に共有してください。")
    with st.form("change_pw", clear_on_submit=True):
        new_pw = st.text_input("新しいパスワード", type="password", max_chars=40)
        confirm = st.form_submit_button("更新する")
    if confirm:
        new_pw = (new_pw or "").strip()
        if not new_pw:
            st.error("空のパスワードは設定できません")
            return
        sheets.set_user_password(new_pw)
        st.success("ユーザパスワードを更新しました")
        st.rerun()


def _reset_section() -> None:
    st.subheader("データのリセット")
    st.caption(
        "users / orders ワークシートのヘッダ以外の行を全削除します。**取り消せません**。"
        "授業前にクリーンな状態から始めたいときに使ってください。"
    )
    if "_reset_armed" not in st.session_state:
        st.session_state._reset_armed = False

    if not st.session_state._reset_armed:
        if st.button("リセット準備", type="secondary"):
            st.session_state._reset_armed = True
            st.rerun()
        return

    st.warning("本当にリセットしますか？ 全ての参加者・注文データが消えます。")
    c1, c2 = st.columns(2)
    if c1.button("はい、リセットする", type="primary"):
        try:
            sheets.reset_data()
        except Exception as e:
            st.error(f"リセットに失敗: {e}")
            st.session_state._reset_armed = False
            return
        st.session_state._reset_armed = False
        st.success("users / orders をリセットしました")
        st.rerun()
    if c2.button("キャンセル"):
        st.session_state._reset_armed = False
        st.rerun()


def render() -> None:
    st.title("教員ダッシュボード")
    st.caption("管理者専用画面。ログアウトはサイドバーから。")

    _metrics()

    try:
        orders = pd.DataFrame(sheets.all_orders())
        users = pd.DataFrame(sheets.all_users())
    except Exception as e:
        st.error(f"データ取得に失敗: {e}")
        orders = pd.DataFrame()
        users = pd.DataFrame()

    st.divider()
    _recent_orders(orders)

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        _product_ranking(orders)
    with col2:
        _grade_category(orders, users)

    st.divider()
    _password_section()

    st.divider()
    _reset_section()
