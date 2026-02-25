"""
ペルソナ生成エンジン: 都道府県別統計データから470人のペルソナを確率的に生成
"""
import json, random, os
from models import Persona

GENDERS = ["男性", "女性"]

OCCUPATIONS = {
    "自動車産業": ["自動車メーカー社員", "部品メーカー技術者"],
    "製造業": ["工場勤務（正社員）", "製造業エンジニア", "品質管理担当"],
    "農業": ["専業農家", "兼業農家"],
    "観光": ["ホテルスタッフ", "観光案内員", "旅館経営者"],
    "IT": ["システムエンジニア", "Webデザイナー", "データアナリスト"],
    "金融": ["銀行員", "保険外交員", "証券会社社員"],
    "サービス業": ["飲食店員", "小売店員", "介護士"],
    "公務": ["地方公務員", "教員", "警察官"],
    "医療": ["看護師", "事務職（病院）", "薬剤師"],
    "商業": ["営業職", "経営者（中小企業）", "フリーランス"],
    "水産業": ["漁師", "水産加工業"],
    "造船": ["造船技術者", "溶接工"],
    "半導体": ["半導体エンジニア", "製造オペレーター"],
    "教育": ["大学研究者", "塾講師", "教員"],
    "伝統産業": ["職人", "伝統工芸士"],
    "伝統工芸": ["漆芸職人", "和菓子職人"],
    "化学工業": ["化学プラント技術者", "研究員"],
    "眼鏡産業": ["眼鏡職人", "販売員"],
    "薬品": ["製薬会社社員", "MR（医薬情報担当者）"],
    "繊維": ["繊維メーカー社員", "アパレル販売員"],
    "石油化学": ["プラント運転員", "化学技術者"],
    "精密機械": ["精密機器技術者", "計測器メーカー社員"],
    "宇宙産業": ["宇宙関連企業社員", "研究補助員"],
    "陶磁器": ["陶磁器職人", "窯元従業員"],
    "基地関連": ["米軍基地勤務（日本人）", "通訳・翻訳業"],
    "食品加工": ["食品加工工場社員", "品質検査員"],
    "物流": ["トラック運転手", "倉庫作業員"],
    "研究機関": ["研究員", "大学教員"],
    "メディア": ["放送局員", "ライター"],
    "空港関連": ["グランドスタッフ", "航空会社社員"],
    "エネルギー": ["電力会社社員", "再生可能エネルギー技術者"],
    "窯業": ["陶芸家", "タイルメーカー社員"],
    "自動車関連": ["ディーラー営業", "整備士"],
}

HOUSEHOLD_LABELS = {
    "single": "一人暮らし",
    "couple_no_kids": "夫婦二人暮らし（子なし）",
    "couple_with_kids": "夫婦と子供",
    "single_parent": "ひとり親世帯",
    "multi_gen": "三世代同居",
}

POLITICAL_MAP = {
    (0.45, 1.0): "自民党支持",
    (0.35, 0.45): "自民党寄り無党派",
    (0.20, 0.35): "野党支持",
    (0.0, 0.20): "無党派・政治無関心",
}

TRAITS_POOL = [
    ["堅実", "真面目", "地元愛が強い"],
    ["楽観的", "社交的", "行動力がある"],
    ["慎重", "節約家", "家族思い"],
    ["向上心が強い", "競争好き", "都会的"],
    ["保守的", "義理堅い", "穏やか"],
    ["革新的", "情報感度が高い", "グローバル志向"],
    ["のんびり屋", "自然好き", "地域コミュニティ重視"],
    ["ストイック", "仕事熱心", "責任感が強い"],
]

# ── ブランドデータベース ────────────────────────────────────────────
# 収入帯: low(<300万), mid(300〜600万), high(>600万)
BRAND_DB: dict[str, dict] = {
    "シャンプー": {
        "low":  ["メリット", "ツバキ", "h&s", "クリア"],
        "mid":  ["パンテーン", "エッセンシャル", "LUX", "アジエンス"],
        "high": ["TSUBAKI プレミアム", "ケラスターゼ", "ミルボン"],
    },
    "服ブランド": {
        "low":  ["ユニクロ", "しまむら", "GU", "ワークマン"],
        "mid":  ["ユニクロ", "ZARA", "H&M", "無印良品"],
        "high": ["ビームス", "ユナイテッドアローズ", "ナノユニバース", "トゥモローランド"],
    },
    "タバコ": {
        "all": ["マイルドセブン（メビウス）", "セブンスター", "キャスター", "ラーク", "ウィンストン"],
        "not_smoker": "（非喫煙者）",
    },
    "車": {
        "low":  ["軽自動車（ダイハツ・スズキ）", "中古のトヨタ"],
        "mid":  ["トヨタ カローラ", "ホンダ フィット", "日産 ノート"],
        "high": ["トヨタ クラウン", "レクサス", "BMW"],
    },
    "スーパー・食料品店": {
        "low":  ["業務スーパー", "ドンキホーテ", "西友"],
        "mid":  ["イオン", "ライフ", "マルエツ"],
        "high": ["成城石井", "紀伊國屋", "クイーンズ伊勢丹"],
    },
    "コンビニ": {
        "all": ["セブン-イレブン", "ファミリーマート", "ローソン"],
    },
    "外食チェーン": {
        "low":  ["マクドナルド", "吉野家", "すき家", "サイゼリヤ"],
        "mid":  ["ガスト", "デニーズ", "丸亀製麺", "くら寿司"],
        "high": ["和食さと", "しゃぶ葉", "個人経営の和食店"],
    },
    "洗剤": {
        "low":  ["アタック", "トップ"],
        "mid":  ["アリエール", "ボールド"],
        "high": ["アリエール プラチナスポーツ", "ファーファ"],
    },
    "化粧品": {
        "low":  ["キャンメイク", "セザンヌ", "ちふれ"],
        "mid":  ["資生堂 マキアージュ", "カネボウ", "コーセー"],
        "high": ["SK-II", "クレ・ド・ポー ボーテ", "ランコム"],
        "male": "（化粧品は使わない）",
    },
    "スマートフォン": {
        "low":  ["Android（格安スマホ）"],
        "mid":  ["iPhone（ミドルモデル）", "Galaxy"],
        "high": ["iPhone（最新モデル）", "Xperia"],
    },
}

def _income_tier(annual_income: int) -> str:
    if annual_income < 300:
        return "low"
    elif annual_income < 600:
        return "mid"
    else:
        return "high"

def assign_brands(age: int, gender: str, annual_income: int) -> dict[str, str]:
    """属性に応じて実在ブランドを割り当てる"""
    tier = _income_tier(annual_income)
    brands: dict[str, str] = {}

    for category, options in BRAND_DB.items():
        if category == "タバコ":
            # 高齢男性ほど喫煙率高め
            smoke_prob = 0.35 if gender == "男性" and age >= 40 else \
                         0.20 if gender == "男性" else 0.08
            if random.random() < smoke_prob:
                brands[category] = random.choice(options["all"])
            else:
                brands[category] = options["not_smoker"]
        elif category == "化粧品":
            if gender == "男性":
                brands[category] = options["male"]
            else:
                choices = options.get(tier) or options.get("mid") or ["（特になし）"]
                brands[category] = random.choice(choices)
        elif category == "コンビニ":
            brands[category] = random.choice(options["all"])
        else:
            choices = options.get(tier) or options.get("mid") or ["（特になし）"]
            brands[category] = random.choice(choices)

    return brands

def weighted_choice(distribution: dict) -> str:
    keys = list(distribution.keys())
    weights = list(distribution.values())
    return random.choices(keys, weights=weights, k=1)[0]

def get_political_leaning(ldp_share: float) -> str:
    r = random.random()
    if r < ldp_share:
        return "自民党支持"
    elif r < ldp_share + 0.15:
        return "公明党支持"
    elif r < ldp_share + 0.15 + (1 - ldp_share - 0.15) * 0.6:
        return random.choice(["立憲民主党支持", "維新支持", "共産党支持", "国民民主党支持"])
    else:
        return "無党派・政治無関心"

def generate_daily_routine(commute: int, age: int, household: str, occupation: str) -> str:
    wake = 6 if commute > 40 else 7
    sleep_time = 23 if commute > 40 else 22
    weekend = "週末は家族と過ごすことが多い" if "子供" in household else \
              "週末は趣味や地域活動に参加" if age > 50 else "週末は友人と外出したり趣味を楽しむ"
    return f"平日は{wake}時起床、{commute}分かけて通勤し、{sleep_time}時頃就寝。{weekend}。"

def generate_personas_for_prefecture(pref_name: str, stats: dict, num: int = 10) -> list[Persona]:
    personas = []
    industries = stats["major_industries"]

    for i in range(num):
        gender = random.choice(GENDERS)
        age_group = weighted_choice(stats["age_distribution"])
        age = {
            "20s": random.randint(20, 29),
            "30s": random.randint(30, 39),
            "40s": random.randint(40, 49),
            "50s": random.randint(50, 59),
            "60s": random.randint(60, 69),
            "70plus": random.randint(70, 80),
        }[age_group]

        emp_type = weighted_choice(stats["employment_type"])
        industry = random.choice(industries)
        occ_list = OCCUPATIONS.get(industry, ["会社員", "自営業"])
        occupation = random.choice(occ_list)
        if emp_type == "part_time":
            occupation = f"{occupation}（パート・アルバイト）"
        elif emp_type == "self_employed":
            occupation = f"自営業（{industry}関連）"
        elif emp_type == "unemployed":
            occupation = "無職・求職中"

        income_band = weighted_choice(stats["income_distribution"])
        income = {
            "under_200": random.randint(80, 199),
            "200_400": random.randint(200, 399),
            "400_600": random.randint(400, 599),
            "600_800": random.randint(600, 799),
            "over_800": random.randint(800, 1200),
        }[income_band]

        household_key = weighted_choice(stats["household_type"])
        household = HOUSEHOLD_LABELS[household_key]
        housing = "持ち家" if random.random() < stats["homeownership_rate"] else "賃貸"

        food_var = int(stats["avg_monthly_food"] * random.uniform(0.8, 1.2))
        house_var = int(stats["avg_monthly_housing"] * random.uniform(0.7, 1.3))
        ent_var = int(stats["avg_monthly_entertainment"] * random.uniform(0.6, 1.4))

        political = get_political_leaning(stats["ldp_vote_share"])
        traits = random.choice(TRAITS_POOL)
        routine = generate_daily_routine(stats["avg_commute_minutes"], age, household, occupation)

        pref_id = pref_name.replace("都", "").replace("道", "").replace("府", "").replace("県", "")
        persona_id = f"{pref_id}_{i+1:02d}"

        preferred_brands = assign_brands(age, gender, income)

        personas.append(Persona(
            id=persona_id,
            prefecture=pref_name,
            region=stats["region"],
            age=age,
            gender=gender,
            occupation=occupation,
            employment_type=emp_type,
            annual_income=income,
            household_type=household,
            housing=housing,
            monthly_food=food_var,
            monthly_housing=house_var,
            monthly_entertainment=ent_var,
            commute_minutes=stats["avg_commute_minutes"] + random.randint(-10, 15),
            sleep_hours=stats["avg_sleep_hours"],
            daily_routine=routine,
            political_leaning=political,
            personality_traits=traits,
            major_industry=industry,
            preferred_brands=preferred_brands,
        ))
    return personas

def load_all_personas(stats_path: str) -> list[Persona]:
    with open(stats_path, "r", encoding="utf-8") as f:
        stats = json.load(f)
    all_personas = []
    for pref_name, pref_stats in stats.items():
        all_personas.extend(generate_personas_for_prefecture(pref_name, pref_stats, num=10))
    return all_personas
