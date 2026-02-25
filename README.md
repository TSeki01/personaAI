# 仮想ペルソナシミュレータ

日本全国47都道府県・470人の仮想ペルソナにインタビューできるAIシミュレータ。

## 機能

- 🗾 **都道府県マップ** — 地域別にペルソナを表示
- 💬 **インタビュー** — 各ペルソナとチャット形式で会話（ライフログ自動注入）
- 📖 **経歴タイムライン** — 年齢・職業から生成されるライフログ
- 🧠 **心理プロファイル** — 生活満足度・将来の不安・SNS利用動向
- 📡 **一括質問** — 全ペルソナに同時に質問してSSEでリアルタイム集計

## 技術スタック

| レイヤー | 技術 |
|---------|------|
| Backend | FastAPI + uvicorn |
| AI | Google Gemini API |
| Frontend | 純粋なHTML/CSS/JavaScript |
| Deploy | Render (Web Service + Static Site) |

## ローカル起動

```bash
# 1. バックエンド
cd backend
python -m venv .venv
.venv\Scripts\activate       # Windows
pip install -r requirements.txt
cp .env.example .env         # APIキーを記入
uvicorn main:app --reload

# 2. フロントエンド
# frontend/index.html をブラウザで開く
```

## Renderへのデプロイ

### 1. GitHubにプッシュ
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/<username>/<repo>.git
git push -u origin main
```

### 2. Renderで環境変数を設定
Renderダッシュボード → `persona-api` → **Environment** に以下を追加:

| Key | Value |
|-----|-------|
| `GEMINI_API_KEY` | Gemini APIキー |
| `GEMINI_MODEL` | `gemini-2.0-flash` |
| `FRONTEND_ORIGIN` | `https://persona-frontend.onrender.com` |

### 3. フロントエンドHTMLのAPI URLを更新
デプロイ後、`frontend/index.html` / `interview.html` / `bulk.html` の
`<script src="api.js" data-api-url="">` の `data-api-url` にバックエンドURLを記入:

```html
<script src="api.js" data-api-url="https://persona-api.onrender.com"></script>
```

## 環境変数

`.env.example` を参照してください。

## ライセンス

MIT
