@echo off
echo === 仮想ペルソナシミュレータ バックエンド起動 ===
cd /d "%~dp0backend"

if not exist ".venv" (
    echo Python仮想環境を作成中...
    python -m venv .venv
)

echo 依存パッケージをインストール中...
call .venv\Scripts\activate.bat
pip install -r requirements.txt -q

echo.
echo 統計データを生成中...
python data\generate_stats.py

echo.
echo バックエンドを起動中 (http://localhost:8000)
echo Ctrl+C で停止
echo.
uvicorn main:app --reload --host 0.0.0.0 --port 8000
