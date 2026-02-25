from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class Persona(BaseModel):
    id: str
    prefecture: str
    region: str
    age: int
    gender: str
    occupation: str
    employment_type: str
    annual_income: int
    household_type: str
    housing: str
    monthly_food: int
    monthly_housing: int
    monthly_entertainment: int
    commute_minutes: int
    sleep_hours: float
    daily_routine: str
    political_leaning: str
    personality_traits: List[str]
    major_industry: str
    preferred_brands: Dict[str, str] = {}

# ── ライフログ ─────────────────────────────────────────────────────
class LifeLogEvent(BaseModel):
    year: int
    age: int
    event: str
    category: str  # "education" | "work" | "family" | "residence"

# ── 心理プロファイル ────────────────────────────────────────────────
class PsychProfile(BaseModel):
    life_satisfaction: str        # 内面・悩み: 生活満足度
    future_anxiety: List[str]     # 内面・悩み: 将来の不安
    work_values: str              # 内面・悩み: 仕事観
    lifestyle_habits: List[str]   # 習慣・変化: ライフスタイル
    values_shift: str             # 習慣・変化: 価値観の変遷
    sns_usage: Dict[str, str]     # 情報収集: SNS利用率
    media_trust: str              # 情報収集: メディア信頼度
    info_sources: List[str]       # 情報収集: 主な情報源

class PersonaProfile(BaseModel):
    lifelog: List[LifeLogEvent]
    psych: PsychProfile

# ── リクエスト/レスポンス ──────────────────────────────────────────
class BulkQuestionRequest(BaseModel):
    question: str
    prefecture_filter: Optional[str] = None

class InterviewRequest(BaseModel):
    message: str
    history: List[Dict[str, str]] = []

class BulkResultItem(BaseModel):
    persona_id: str
    prefecture: str
    persona_name: str
    age: int
    gender: str
    occupation: str
    answer: str

class PersonaListResponse(BaseModel):
    personas: List[Persona]
    total: int
