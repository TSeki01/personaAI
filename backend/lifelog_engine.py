"""
ライフログ + 心理プロファイル生成エンジン
ペルソナ属性から以下の4要素をルールベースで即時生成（API消費なし）:
  1. ライフログ（経歴）: 出生〜現在のライフイベント時系列
  2. 内面・悩み: 生活満足度、将来の不安、仕事観（国民生活世論調査ベース）
  3. 習慣・変化: ライフスタイル、価値観の変遷（生活定点ベース）
  4. 情報収集: SNS利用率、メディア信頼度（SNS利用動向調査ベース）
"""
import random
from models import Persona, LifeLogEvent, PsychProfile, PersonaProfile

CURRENT_YEAR = 2026

# ── ライフログ生成 ──────────────────────────────────────────────────

# 学歴ルール: 雇用形態・職業・年収から最終学歴を推定
def _estimate_education(occupation: str, employment_type: str, annual_income: int) -> str:
    occ_lower = occupation.lower()
    high_edu_keywords = ["エンジニア", "研究員", "教員", "大学", "薬剤師", "看護師", "医師", "アナリスト", "MR"]
    if any(k in occupation for k in high_edu_keywords) or annual_income >= 600:
        return "university"
    if employment_type in ("part_time", "unemployed") or annual_income < 250:
        return "highschool"
    if any(k in occupation for k in ["職人", "漁師", "農家", "溶接工", "運転手", "工場"]):
        return "vocational"  # 専門・工業高校
    return random.choice(["highschool", "university", "vocational"])

def generate_lifelog_events(persona: Persona) -> list[LifeLogEvent]:
    birth_year = CURRENT_YEAR - persona.age
    events: list[LifeLogEvent] = []
    edu = _estimate_education(persona.occupation, persona.employment_type, persona.annual_income)

    def add(age: int, event: str, category: str):
        events.append(LifeLogEvent(
            year=birth_year + age,
            age=age,
            event=event,
            category=category,
        ))

    # 出生
    add(0, f"{persona.prefecture}に生まれる", "residence")

    # 幼稚園 (年齢が足りる場合のみ)
    if persona.age >= 6:
        add(3, "幼稚園・保育園に入園", "education")
    if persona.age >= 7:
        add(6, "小学校に入学", "education")
    if persona.age >= 13:
        add(12, "中学校に入学", "education")

    # 高校
    if persona.age >= 16:
        if edu == "vocational":
            add(15, "工業高校・農業高校などに入学", "education")
        else:
            add(15, "高校に入学", "education")

    # 高校卒業 / 進学
    if persona.age >= 18:
        if edu == "university":
            add(18, "大学（または短期大学）に進学", "education")
        elif edu == "vocational":
            add(18, "専門学校に進学", "education")
        else:
            add(18, "高校を卒業", "education")

    # 就職
    work_start_age = 22 if edu == "university" else 20 if edu == "vocational" else 18
    if persona.age >= work_start_age:
        if persona.employment_type == "unemployed":
            add(work_start_age, "就職活動を開始（現在求職中）", "work")
        elif persona.employment_type == "self_employed":
            add(work_start_age + random.randint(0, 5), f"{persona.major_industry}分野で独立・開業", "work")
        else:
            add(work_start_age, f"{persona.major_industry}関連の企業に就職", "work")

    # 転職 (20代後半〜30代で低確率)
    if persona.age >= 28 and persona.employment_type == "full_time":
        if random.random() < 0.45:
            t_age = random.randint(26, min(35, persona.age - 1))
            add(t_age, "転職。現在の職場に就く", "work")

    # 結婚 (世帯構成から判断)
    marriage_types = {"夫婦二人暮らし（子なし）", "夫婦と子供", "三世代同居"}
    if persona.household_type in marriage_types and persona.age >= 25:
        m_age = random.randint(24, min(35, persona.age - 1)) if persona.age > 25 else 25
        add(m_age, "結婚。新生活を開始", "family")

    # 第一子誕生
    if "子供" in persona.household_type and persona.age >= 28:
        c_age = random.randint(26, min(38, persona.age - 3))
        add(c_age, "第一子が誕生", "family")

    # 住宅購入
    if persona.housing == "持ち家" and persona.age >= 30:
        buy_age = random.randint(29, min(45, persona.age - 1))
        add(buy_age, "マイホームを購入。現在の住居へ移転", "residence")

    # 昇進・転機
    if persona.age >= 35 and persona.employment_type == "full_time" and persona.annual_income >= 450:
        if random.random() < 0.5:
            senior_age = random.randint(32, min(45, persona.age - 1))
            add(senior_age, "チームリーダー・主任に昇進", "work")

    # 子供の独立（60代以上）
    if persona.age >= 60 and "子供" in persona.household_type:
        add(persona.age - random.randint(3, 8), "子供が独立・巣立ちしていく", "family")

    # 退職（65歳以上）
    if persona.age >= 65 and persona.employment_type not in ("part_time",):
        add(65, "定年退職。セカンドライフを開始", "work")

    # 現在（直近の活動）
    if persona.employment_type == "part_time":
        add(persona.age, f"現在: パート・アルバイトとして{persona.occupation}に従事", "work")
    elif persona.employment_type == "unemployed":
        add(persona.age, "現在: 求職活動中", "work")
    else:
        add(persona.age, f"現在: {persona.occupation}として働く（{persona.prefecture}在住）", "work")

    # 年齢順にソート
    events.sort(key=lambda e: (e.year, e.age))
    return events


# ── 心理プロファイル生成 ───────────────────────────────────────────

# 年収帯
def _income_tier(income: int) -> str:
    if income < 250: return "low"
    if income < 450: return "mid_low"
    if income < 650: return "mid_high"
    return "high"

# 内面・悩み（国民生活に関する世論調査ベース）
SATISFACTION_MAP = {
    "low":      ["生活に不満がある。節約しながら毎日を乗り越えている感覚", "将来への見通しが立たず、漠然とした不安を感じることが多い"],
    "mid_low":  ["生活は普通だが余裕はない。節約を心がけている", "現状維持はできているが、もう少し豊かになりたいという気持ちがある"],
    "mid_high": ["生活にはある程度満足している。たまに贅沢もできる", "安定しているが、将来の老後資金や子供の教育費が気になる"],
    "high":     ["生活には満足している。仕事も充実している", "社会全体への不満や格差に対する複雑な感情がある"],
}
ANXIETY_MAP = {
    "low":      ["老後の生活費", "健康・医療費", "雇用・仕事の安定"],
    "mid_low":  ["老後の生活費", "物価上昇", "子供の教育費"],
    "mid_high": ["老後の資産形成", "子供の将来", "社会保障制度への不信"],
    "high":     ["経済の先行き", "社会格差の拡大", "仕事と家庭のバランス"],
}
WORK_VALUES_MAP = {
    "full_time":    ["安定した雇用に価値を見出している。職場の人間関係を大切にするタイプ",
                     "仕事に誇りを持っており、スキルアップに積極的"],
    "part_time":    ["働く時間と生活のバランスを重視している。無理せず続けられることが大切",
                     "収入は少ないが、自分のペースで働けることを好む"],
    "self_employed":["自分のペースで働けることを何より大切にしている。リスクは取るが自由も得る",
                     "顧客との関係を大切にし、信頼で仕事を積み上げてきた"],
    "unemployed":   ["できれば安定した仕事に就きたいと思っているが、なかなか踏み出せない",
                     "仕事への意欲はあるが、自分に合う職場を探している段階"],
}

# 習慣・変化（生活定点ベース）
LIFESTYLE_HABITS_MAP = {
    "low":      [["節約レシピを調べてから買い物をする", "外食は月数回のご馳走", "テレビかスマホで夜を過ごす"]],
    "mid_low":  [["週末はスーパーで特売品をまとめ買い", "趣味は安価に楽しめるものが中心（読書・散歩など）", "SNSで情報収集することが増えた"]],
    "mid_high": [["週末に外食や旅行を楽しむ余裕がある", "フィットネスや健康意識が高まっている", "サブスクサービスを複数利用している"]],
    "high":     [["国内外の旅行を年数回楽しむ", "食や体験に積極的にお金をかける", "情報感度が高く新サービスをいち早く試す"]],
}
VALUES_SHIFT_MAP = {
    ("20s", "low"):      "コロナ禍・物価高を社会人として経験し、将来への不安から節約・堅実志向になった",
    ("20s", "mid_low"):  "就職後に理想と現実のギャップを感じ、ワークライフバランスを重視するようになった",
    ("20s", "mid_high"): "仕事にやりがいを感じつつ、副業や自己投資にも興味を持ち始めている",
    ("20s", "high"):     "キャリア形成に積極的で、スキルアップや自己成長を最優先している",
    ("30s", "low"):      "子育てや生活費の負担が重く、将来よりも今の生活を安定させることに必死",
    ("30s", "mid_low"):  "家族のためにコツコツ貯蓄しており、無駄遣いを減らす意識が強くなった",
    ("30s", "mid_high"): "仕事でも家庭でも責任が増し、時間の使い方を見直している",
    ("30s", "high"):     "ある程度の成功を感じているが、子供の教育や将来設計への関心が高まっている",
    ("40s", "low"):      "先行きに不安を抱えながらも現状を維持することで精一杯",
    ("40s", "mid_low"):  "老後に向けた備えを少しずつ意識し始め、健康への投資も気になっている",
    ("40s", "mid_high"): "仕事・家庭・趣味のバランスを意識。健康や自己実現にも投資するようになった",
    ("40s", "high"):     "人生後半を見据えて生活の質を高めることに価値を感じている",
    ("50s", "low"):      "定年後の生活費が心配で、少しでも長く働こうと考えている",
    ("50s", "mid_low"):  "子供が独立し、老後の準備を本格的に始めようとしている",
    ("50s", "mid_high"): "子育てが一段落し、自分の時間ができてきた。趣味に時間をかけている",
    ("50s", "high"):     "社会的に安定した立場になり、社会貢献や地域活動に関心が高まっている",
    ("60s+", "low"):     "年金だけでは不安で、体が動く限りは働き続けたいと思っている",
    ("60s+", "mid_low"): "年金と貯蓄でなんとかやっていけるが、医療費が心配",
    ("60s+", "mid_high"):"退職後の生活を楽しんでいる。旅行や趣味の時間が増えた",
    ("60s+", "high"):    "豊かなセカンドライフを満喫しており、次世代への貢献を考えている",
}
def _age_bracket(age: int) -> str:
    if age < 30: return "20s"
    if age < 40: return "30s"
    if age < 50: return "40s"
    if age < 60: return "50s"
    return "60s+"

# 情報収集（SNS利用動向調査ベース）
SNS_USAGE_BY_AGE = {
    "20s": {"LINE": "毎日", "X (Twitter)": "頻繁に", "Instagram": "毎日", "YouTube": "毎日", "TikTok": "よく見る"},
    "30s": {"LINE": "毎日", "X (Twitter)": "ときどき", "Instagram": "よく見る", "YouTube": "毎日", "Facebook": "たまに確認"},
    "40s": {"LINE": "毎日", "Facebook": "ときどき", "YouTube": "よく見る", "X (Twitter)": "たまに"},
    "50s": {"LINE": "毎日", "Facebook": "ときどき", "YouTube": "ときどき"},
    "60s+": {"LINE": "ときどき使う"},
}
MEDIA_TRUST_BY_AGE = {
    "20s":  "テレビや新聞への信頼は低めで、SNSやYouTubeで情報を収集することが多い",
    "30s":  "テレビのニュースも見るが、SNSの情報も積極的に活用している",
    "40s":  "テレビ・新聞を信頼しているが、Webニュースも合わせて確認することが増えた",
    "50s":  "テレビのニュースを主な情報源としており、新聞も定期的に読む",
    "60s+": "テレビと新聞を主な情報源として信頼しており、SNSにはあまり慣れていない",
}
INFO_SOURCES_BY_AGE = {
    "20s":  ["YouTube", "X (Twitter)", "Instagram", "まとめサイト・ニュースアプリ"],
    "30s":  ["Yahoo!ニュース", "YouTube", "LINE NEWS", "X (Twitter)"],
    "40s":  ["テレビ", "Yahoo!ニュース", "Facebook", "新聞"],
    "50s":  ["テレビ", "新聞", "Yahoo!ニュース", "ラジオ"],
    "60s+": ["テレビ", "新聞", "ラジオ", "口コミ・近所との会話"],
}

def generate_psych_profile(persona: Persona) -> PsychProfile:
    tier = _income_tier(persona.annual_income)
    age_br = _age_bracket(persona.age)

    satisfaction_opts = SATISFACTION_MAP.get(tier, SATISFACTION_MAP["mid_low"])
    life_satisfaction = random.choice(satisfaction_opts)

    anxieties = list(ANXIETY_MAP.get(tier, ANXIETY_MAP["mid_low"]))
    # 子育て世帯は教育費不安を追加
    if "子供" in persona.household_type and "子供の教育費" not in anxieties:
        anxieties.append("子供の教育費")
    # ひとり親は孤立不安追加
    if "ひとり親" in persona.household_type:
        anxieties.append("育児と仕事の両立")
    random.shuffle(anxieties)

    work_opts = WORK_VALUES_MAP.get(persona.employment_type, WORK_VALUES_MAP["full_time"])
    work_values = random.choice(work_opts)

    lifestyle_opts = LIFESTYLE_HABITS_MAP.get(tier, LIFESTYLE_HABITS_MAP["mid_low"])
    lifestyle_habits = list(random.choice(lifestyle_opts))

    # 性格特性から習慣を1つ追加
    trait_habit_map = {
        "節約家": "家計簿をつけて支出を管理している",
        "健康志向": "毎朝ウォーキングや体操を習慣にしている",
        "地元愛が強い": "地域のイベントや祭りに積極的に参加する",
        "情報感度が高い": "新しいアプリやサービスをすぐに試してみる",
        "自然好き": "週末はハイキングやガーデニングを楽しむ",
        "仕事熱心": "平日は仕事中心の生活で、休日もスキルアップに充てることが多い",
        "社交的": "友人や地域の人との交流を大切にしている",
        "のんびり屋": "週末はゆっくり自宅でドラマや映画を観て過ごすことが多い",
    }
    for trait in persona.personality_traits:
        if trait in trait_habit_map:
            lifestyle_habits.append(trait_habit_map[trait])
            break

    # 価値観の変遷
    vs_key = (age_br, tier)
    values_shift = VALUES_SHIFT_MAP.get(vs_key,
        VALUES_SHIFT_MAP.get((age_br, "mid_low"),
        "時代の変化とともに価値観も少しずつ変化してきた"))

    sns_raw = dict(SNS_USAGE_BY_AGE.get(age_br, SNS_USAGE_BY_AGE["40s"]))
    # 低収入の若年層はTikTok/X利用が高い
    if tier == "low" and age_br in ("20s", "30s"):
        sns_raw["TikTok"] = "よく見る"

    media_trust = MEDIA_TRUST_BY_AGE.get(age_br, MEDIA_TRUST_BY_AGE["40s"])
    info_sources = list(INFO_SOURCES_BY_AGE.get(age_br, INFO_SOURCES_BY_AGE["40s"]))

    return PsychProfile(
        life_satisfaction=life_satisfaction,
        future_anxiety=anxieties,
        work_values=work_values,
        lifestyle_habits=lifestyle_habits,
        values_shift=values_shift,
        sns_usage=sns_raw,
        media_trust=media_trust,
        info_sources=info_sources,
    )


def generate_persona_profile(persona: Persona) -> PersonaProfile:
    """ライフログ + 心理プロファイルを一括生成"""
    return PersonaProfile(
        lifelog=generate_lifelog_events(persona),
        psych=generate_psych_profile(persona),
    )
