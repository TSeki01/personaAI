"""
Gemini APIクライアント with レート制限 & 使用量トラッキング
- gemini-2.0-flash 無料枠: 15 RPM / 1,500 RPD
"""
import asyncio, os, time
from google import genai
from google.genai import types
from models import Persona, PersonaProfile

_client: genai.Client | None = None

# ── 使用量トラッカー ────────────────────────────────────────────
class UsageTracker:
    RPM_LIMIT = int(os.getenv("GEMINI_RPM_LIMIT", "15"))
    RPD_LIMIT = int(os.getenv("GEMINI_RPD_LIMIT", "1500"))

    def __init__(self):
        self.requests_today = 0
        self.requests_this_minute: list[float] = []
        self.day_start = time.time()
        self._lock = asyncio.Lock()

    def _reset_day_if_needed(self):
        now = time.time()
        if now - self.day_start >= 86400:
            self.requests_today = 0
            self.day_start = now

    async def wait_if_needed(self):
        """RPM制限を守るためのスロットリング"""
        async with self._lock:
            now = time.time()
            # 1分以上前のリクエストを除去
            self.requests_this_minute = [t for t in self.requests_this_minute if now - t < 60]
            # RPM上限に達している場合は待機
            if len(self.requests_this_minute) >= self.RPM_LIMIT:
                oldest = self.requests_this_minute[0]
                wait_sec = 60 - (now - oldest) + 0.5
                if wait_sec > 0:
                    await asyncio.sleep(wait_sec)
            # 記録
            self.requests_this_minute.append(time.time())
            self._reset_day_if_needed()
            self.requests_today += 1

    def get_status(self) -> dict:
        now = time.time()
        self._reset_day_if_needed()
        rpm_current = len([t for t in self.requests_this_minute if now - t < 60])
        return {
            "requests_today": self.requests_today,
            "requests_remaining_today": max(0, self.RPD_LIMIT - self.requests_today),
            "rpm_current": rpm_current,
            "rpm_limit": self.RPM_LIMIT,
            "rpd_limit": self.RPD_LIMIT,
            "quota_pct_used": round(self.requests_today / self.RPD_LIMIT * 100, 1),
        }

usage_tracker = UsageTracker()

def init_gemini():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set")
    global _client
    _client = genai.Client(api_key=api_key)

def build_system_prompt(persona: Persona, profile: "PersonaProfile | None" = None) -> str:
    traits = "、".join(persona.personality_traits)
    brands_lines = "\n".join(
        f"  {cat}: {brand}" for cat, brand in persona.preferred_brands.items()
    )

    # ── ライフログセクション ──────────────────────────────────────
    lifelog_section = ""
    if profile and profile.lifelog:
        events_text = "\n".join(
            f"  {e.year}年（{e.age}歳）: {e.event}" for e in profile.lifelog
        )
        lifelog_section = f"""
=== あなたの経歴（ライフログ） ===
{events_text}
"""

    # ── 心理プロファイルセクション ───────────────────────────────
    psych_section = ""
    if profile and profile.psych:
        ps = profile.psych
        anxiety_text = "、".join(ps.future_anxiety)
        habits_text = "、".join(ps.lifestyle_habits)
        sns_text = "、".join(f"{k}（{v}）" for k, v in ps.sns_usage.items())
        sources_text = "、".join(ps.info_sources)
        psych_section = f"""
=== あなたの内面・悩み ===
生活満足度: {ps.life_satisfaction}
将来の不安: {anxiety_text}
仕事観: {ps.work_values}

=== あなたの習慣・変化 ===
ライフスタイル: {habits_text}
価値観の変遷: {ps.values_shift}

=== あなたの情報収集スタイル ===
SNS利用: {sns_text}
メディアへの信頼: {ps.media_trust}
主な情報源: {sources_text}
"""

    return f"""あなたは以下のプロフィールを持つ、{persona.prefecture}在住の{persona.age}歳{persona.gender}です。

【重要な設定】
あなたは今、リサーチャー（インタビュアー）から生活実態や価値観について話を聞かれている、ごく普通の日本人です。
あなたはAIでも相談窓口でもありません。インタビューに応じている一般市民として、自分の言葉で素直に答えてください。

=== あなたのプロフィール ===
居住地: {persona.prefecture}
年齢: {persona.age}歳
性別: {persona.gender}
職業: {persona.occupation}
年収: 約{persona.annual_income}万円
世帯構成: {persona.household_type}
住居: {persona.housing}
月の食費: 約{persona.monthly_food:,}円
月の住居費: 約{persona.monthly_housing:,}円
月の趣味・娯楽費: 約{persona.monthly_entertainment:,}円
通勤時間: 約{persona.commute_minutes}分
生活習慣: {persona.daily_routine}
政治的傾向: {persona.political_leaning}
性格: {traits}
主な関連産業: {persona.major_industry}

=== 普段使いのブランド・商品 ===
{brands_lines}
{lifelog_section}{psych_section}
=== 話し方・態度のルール ===
- インタビューに応じている普通の人として接する（「お手伝いします」「何かお話しますよ」は絶対に言わない）
- 挨拶には普通に挨拶を返す（例：「はい、よろしくお願いします」「どうも。何を聞かれるんですか？」）
- 質問には自分の経験・感情を交えて素直に答える
- 簡単な入力（「こんにちは」など）には短く自然に返す。長文で答えない
- 具体的な質問には、プロフィールに基づいた自分の経験で丁寧に答える（200〜400字）
- プロフィールの数字を直接読み上げず、自分の言葉で表現する
- ブランド名は「普段使いのブランド」に記載のものだけ使う。架空のブランド名は絶対に使わない
- 記載にないカテゴリは「特にこだわりない」「市販のもの」と答える
- 経歴に記載のある過去の出来事については、実体験として自然に語ることができる
"""


async def ask_persona(persona: Persona, question: str, model_name: str = "gemini-2.0-flash", profile: "PersonaProfile | None" = None) -> str:
    await usage_tracker.wait_if_needed()
    response = await asyncio.to_thread(
        _client.models.generate_content,
        model=model_name,
        contents=question,
        config=types.GenerateContentConfig(system_instruction=build_system_prompt(persona, profile)),
    )
    return response.text

async def ask_persona_with_history(
    persona: Persona,
    message: str,
    history: list[dict],
    model_name: str = "gemini-2.0-flash",
    profile: "PersonaProfile | None" = None,
) -> str:
    await usage_tracker.wait_if_needed()
    system_prompt = build_system_prompt(persona, profile)
    contents = []
    for h in history:
        role = "user" if h["role"] == "user" else "model"
        contents.append(types.Content(role=role, parts=[types.Part(text=h["content"])]))
    contents.append(types.Content(role="user", parts=[types.Part(text=message)]))
    response = await asyncio.to_thread(
        _client.models.generate_content,
        model=model_name,
        contents=contents,
        config=types.GenerateContentConfig(system_instruction=system_prompt),
    )
    return response.text

async def enhance_persona_profile(
    persona: Persona,
    profile: "PersonaProfile",
    model_name: str = "gemini-2.0-flash",
) -> str:
    """ルールベースで生成したプロファイルをGeminiが自然な文章に拡充する（オプション機能）"""
    await usage_tracker.wait_if_needed()
    events_text = "\n".join(
        f"{e.year}年（{e.age}歳）: {e.event}" for e in profile.lifelog
    )
    prompt = f"""以下は{persona.prefecture}在住の{persona.age}歳{persona.gender}（職業：{persona.occupation}、年収：{persona.annual_income}万円）のライフログです。

{events_text}

上記の経歴に基づき、この人物の人生を簡潔に振り返る「自己紹介コメント」を150〜200字で作成してください。
一人称（「私は〜」）で書いてください。AIらしくなく、普通の日本人の話し言葉で。"""
    response = await asyncio.to_thread(
        _client.models.generate_content,
        model=model_name,
        contents=prompt,
    )
    return response.text

async def bulk_ask_stream(
    personas: list[Persona],
    question: str,
    concurrency: int = 5,
    model_name: str = "gemini-2.0-flash",
):
    # バルク質問時は並列度を低く（レート制限を守るため）
    effective_concurrency = min(concurrency, max(1, UsageTracker.RPM_LIMIT // 2))
    semaphore = asyncio.Semaphore(effective_concurrency)

    async def ask_one(persona: Persona) -> tuple[Persona, str]:
        async with semaphore:
            try:
                answer = await ask_persona(persona, question, model_name)
            except Exception as e:
                err = str(e)
                if "429" in err or "RESOURCE_EXHAUSTED" in err:
                    answer = "（APIクォータ超過のため回答できませんでした）"
                else:
                    answer = f"（エラー: {err[:80]}）"
            return persona, answer

    tasks = [asyncio.create_task(ask_one(p)) for p in personas]
    total = len(personas)
    completed = 0

    for coro in asyncio.as_completed(tasks):
        persona, answer = await coro
        completed += 1
        yield {
            "completed": completed,
            "total": total,
            "persona_id": persona.id,
            "persona_name": f"{persona.prefecture}の{persona.age}歳{persona.gender}",
            "prefecture": persona.prefecture,
            "age": persona.age,
            "gender": persona.gender,
            "occupation": persona.occupation,
            "answer": answer,
            "usage": usage_tracker.get_status(),
        }
