# lecture-data-driven-app

高校生向け出張授業教材：「買い物アプリ」を題材にした
データ駆動アプリ体験。

- **Live URL**: https://lecture-shopping-app.streamlit.app/
  （Streamlit Community Cloud 無料枠。一定時間アクセスがないとスリープするので、授業前に起こす必要あり）

- 1 つの Streamlit アプリの 3 タブで L1（動作代替）/ L2（記憶あり）/ L3（データ駆動）
  の段階モデルを内包
- バックエンド：Google Sheets（gspread）
- ホスティング：Streamlit Community Cloud

## ローカル開発

```bash
uv sync
uv run streamlit run streamlit_app.py
```

サービスアカウント鍵は `.streamlit/secrets.toml`（`.gitignore` 済み）から
読み込む（`app/sheets.py`）。雛形は `.streamlit/secrets.toml.example` を参照。

## Streamlit Community Cloud デプロイ

1. share.streamlit.io でこのリポジトリを選び `streamlit_app.py` を entry point に指定
2. アプリ設定の Secrets パネルに `.streamlit/secrets.toml.example`
   の内容（実値を埋めたもの）を貼る
3. Google Sheets 側で対象シートにサービスアカウントの client_email を
   編集者として共有

## ライセンス

教材コードは CC BY-NC-SA 4.0。
