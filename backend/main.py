"""
FastAPI メインアプリ
エンドポイント:
  GET  /api/personas          - ペルソナ一覧
  GET  /api/personas/{id}     - ペルソナ詳細
  POST /api/bulk-question     - 一括質問（SSEストリーミング）
  POST /api/interview/{id}    - 個別インタビュー（会話履歴付き）
"""
import json, os, asyncio
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from models import Persona, BulkQuestionRequest, InterviewRequest
from persona_engine import load_all_personas
from lifelog_engine import generate_persona_profile
from gemini_client import init_gemini, bulk_ask_stream, ask_persona_with_history, enhance_persona_profile, usage_tracker

# ── グローバルストア ──────────────────────────────────────────────
PERSONAS: dict[str, Persona] = {}
STATS_PATH = os.path.join(os.path.dirname(__file__), "data", "stats_by_prefecture.json")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 起動時: 統計データを生成 → ペルソナをロード
    if not os.path.exists(STATS_PATH):
        import subprocess, sys
        subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "data", "generate_stats.py")])

    init_gemini()
    personas = load_all_personas(STATS_PATH)
    for p in personas:
        PERSONAS[p.id] = p
    print(f"[OK] {len(PERSONAS)} personas loaded.")
    yield

app = FastAPI(title="仮想ペルソナシミュレータ API", lifespan=lifespan)

# CORS: 開発時は全許可、本番はFRONTEND_ORIGIN環境変数で指定されたオリジンのみ
_frontend_origin = os.getenv("FRONTEND_ORIGIN", "")
_allow_origins = ["*"] if not _frontend_origin else [_frontend_origin]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── エンドポイント ────────────────────────────────────────────────

@app.get("/api/personas")
def get_personas(prefecture: str | None = None, region: str | None = None):
    personas = list(PERSONAS.values())
    if prefecture:
        personas = [p for p in personas if p.prefecture == prefecture]
    if region:
        personas = [p for p in personas if p.region == region]
    return {"personas": [p.model_dump() for p in personas], "total": len(personas)}

@app.get("/api/personas/{persona_id}")
def get_persona(persona_id: str):
    p = PERSONAS.get(persona_id)
    if not p:
        raise HTTPException(status_code=404, detail="Persona not found")
    return p.model_dump()

@app.get("/api/prefectures")
def get_prefectures():
    """都道府県一覧とペルソナ数を返す"""
    from collections import Counter
    counts = Counter(p.prefecture for p in PERSONAS.values())
    regions: dict[str, list] = {}
    for p in PERSONAS.values():
        if p.region not in regions:
            regions[p.region] = []
        if p.prefecture not in regions[p.region]:
            regions[p.region].append(p.prefecture)
    return {"prefectures": dict(counts), "regions": regions}

@app.get("/api/usage")
def get_usage():
    """Gemini API使用量と残量を返す"""
    return usage_tracker.get_status()

@app.get("/api/personas/{persona_id}/profile")
def get_persona_profile(persona_id: str):
    """ライフログ + 心理プロファイルをルールベースで即時生成して返す（API消費なし）"""
    p = PERSONAS.get(persona_id)
    if not p:
        raise HTTPException(status_code=404, detail="Persona not found")
    profile = generate_persona_profile(p)
    return profile.model_dump()

@app.post("/api/personas/{persona_id}/profile/enhance")
async def enhance_profile(persona_id: str):
    """Gemini APIを使ってライフログを拡充し、自己紹介コメントを生成する（API消費あり）"""
    p = PERSONAS.get(persona_id)
    if not p:
        raise HTTPException(status_code=404, detail="Persona not found")
    profile = generate_persona_profile(p)
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    try:
        narrative = await enhance_persona_profile(p, profile, model_name)
    except Exception as e:
        msg = str(e)
        if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
            raise HTTPException(status_code=429, detail="APIの無料枠上限に達しました。")
        raise HTTPException(status_code=500, detail=f"Gemini APIエラー: {msg}")
    return {**profile.model_dump(), "narrative": narrative}

@app.post("/api/bulk-question")
async def bulk_question(req: BulkQuestionRequest):
    """
    SSEで進捗をストリーミングしながら一括質問。
    各ペルソナの回答が完了するたびに data: JSON を送信。
    """
    personas = list(PERSONAS.values())
    if req.prefecture_filter:
        personas = [p for p in personas if p.prefecture == req.prefecture_filter]

    model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    concurrency = int(os.getenv("BULK_CONCURRENCY", "5"))

    async def event_generator():
        try:
            async for result in bulk_ask_stream(personas, req.question, concurrency, model_name):
                # Attach region for frontend filtering
                p_obj = PERSONAS.get(result["persona_id"])
                result["region"] = p_obj.region if p_obj else ""
                yield {
                    "event": "progress",
                    "data": json.dumps(result, ensure_ascii=False),
                }
            yield {"event": "done", "data": json.dumps({"message": "完了"}, ensure_ascii=False)}
        except Exception as e:
            yield {"event": "error", "data": json.dumps({"error": str(e)}, ensure_ascii=False)}

    return EventSourceResponse(event_generator())

@app.post("/api/interview/{persona_id}")
async def interview(persona_id: str, req: InterviewRequest):
    """個別インタビュー: 会話履歴を受け取り、ペルソナが返答する（プロファイル自動注入）"""
    p = PERSONAS.get(persona_id)
    if not p:
        raise HTTPException(status_code=404, detail="Persona not found")

    # ライフログ+心理プロファイルを自動生成してシステムプロンプトに注入
    profile = generate_persona_profile(p)

    model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    try:
        answer = await ask_persona_with_history(p, req.message, req.history, model_name, profile)
    except Exception as e:
        msg = str(e)
        if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
            raise HTTPException(
                status_code=429,
                detail="APIの無料枠の上限に達しました。しばらく待ってから再試行してください。"
            )
        raise HTTPException(status_code=500, detail=f"Gemini APIエラー: {msg}")
    return {"answer": answer, "persona_id": persona_id}
