# bazi_llm.py
import re
import json
import dashscope
from openai import OpenAI
from tencentcloud.hunyuan.v20230901 import hunyuan_client, models
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile

import concurrent.futures

from app.config.settings import QIANWEN_API_KEY, TENCENT_SECRET_ID, TENCENT_SECRET_KEY, OPENAI_API_KEY
from app.config.settings import QIANWEN_LLM_MODEL, HUNYUAN_LLM_MODEL, OPENAI_LLM_MODEL

from app.bazi.engine import GAN, GAN_MAP, localize_pillars

FALLBACK_LLM = "openai"
LLM_TIMEOUT = 800  # seconds

if not OPENAI_API_KEY:
    raise ValueError("Please set OPENAI_API_KEY in your environment")
client_oa = OpenAI(api_key=OPENAI_API_KEY)

# ---- Hunyuan ----
# Initialize Hunyuan client (singleton pattern)
_hunyuan_client = None

def get_hunyuan_client():
    global _hunyuan_client
    if _hunyuan_client is None:
        try:
            cred = credential.Credential(TENCENT_SECRET_ID, TENCENT_SECRET_KEY)
            http_profile = HttpProfile(
                endpoint="hunyuan.ap-hongkong.tencentcloudapi.com")
            client_profile = ClientProfile(httpProfile=http_profile)
            _hunyuan_client = hunyuan_client.HunyuanClient(
                cred, "ap-hongkong", client_profile)
        except Exception as e:
            print(f"初始化混元客户端失败: {e}")
            raise  # 或返回 None，根据业务需求处理
    return _hunyuan_client

# ---- Qianwen ----
# import dashscope
dashscope.api_key = QIANWEN_API_KEY

# -----------------------------
# Helper: safe JSON parsing
# -----------------------------
# def safe_parse_json(text: str):
#     text = re.sub(r"^```json", "", text, flags=re.IGNORECASE)
#     text = re.sub(r"^```", "", text)
#     text = re.sub(r"```$", "", text)
#     text = text.strip()
#     return json.loads(text)

def safe_parse_json(text: str):
    text = text.strip()

    # Extract first JSON object defensively
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise json.JSONDecodeError("No JSON object found", text, 0)

    json_text = text[start:end + 1]
    return json.loads(json_text)



def build_bazi_prompt(bazi_data, target_year=2026, lang="zh"):

    # TODO: Left this commented for reference
    # return f"""
    #     ROLE:
    #     You are a master of classical BaZi (子平術), strictly trained in the Ziping (子平) tradition.

    #     Input BaZi data:
    #         {json.dumps(bazi_data, ensure_ascii=False)}

    #     LANGUAGE:
    #         Use language: {lang}

    #     SCOPE & SOURCE RULES (ABSOLUTE):
    #     - Analyze ONLY the provided BaZi chart data and the specified year {target_year}.
    #     - Do NOT use modern psychology, generic life advice, or non-Ziping metaphysics.
    #     - All conclusions must be derived from Day Master strength, Month Branch priority, Five-Element balance, and seasonal 調候.
    #     - Do NOT use or copy example wording from wthin (e.g.) but use your reasoning to generate original text.

    #     ANALYSIS ORDER (MUST FOLLOW):
    #     1. Use the provided Four Pillars (Year, Month, Day, Hour) and Day Master.
    #     2. Determine Day Master strength and seasonal 調候.
    #     3. Quantify Five-Element distribution across the entire chart.
    #     4. Describe overall structure, dominant forces, and key conflicts.
    #     5. Apply balance-first resolution logic.
    #     6. Integrate year {target_year} and explain what is ACTIVATED or CHANGED.

    #     DETERMINISM RULES:
    #     - Provide ONE single coherent interpretation.
    #     - No alternatives, no conditional branches, no contradictions.

    #     OUTPUT RULES:
    #     - Output STRICTLY valid JSON only.
    #     - No markdown, no extra text.

    #     VERBOSITY REQUIREMENTS:
    #     - Explanatory fields must use full classical-style reasoning sentences.
    #     - Avoid single-phrase explanations where narrative is requested.
    #     - Example of careers can be (but not limited to): Technology, SW development, Finance, Healthcare, Education, Arts, Engineering, Sales, Management.

    #     OUTPUT JSON SCHEMA (MUST MATCH EXACTLY):

    #     {{
    #     "core_analysis": {{
    #         "overall_structure": "Detailed narrative explanation of the chart’s elemental structure and seasonal condition.",
    #         "key_conflict": {{
    #         "summary": "Short classical phrase",
    #         "explanation": "Full explanation of why this conflict forms and how it affects the chart."
    #         }},
    #         "day_master": {{
    #         "element": "string",
    #         "strength": "string",
    #         "seasonal_analysis": "Detailed explanation of 調候 needs."
    #         }},
    #         "contradictions": [
    #         {{
    #             "pattern": "string",
    #             "impact": "Detailed explanation of the life implication."
    #         }},
    #         {{
    #             "pattern": "string",
    #             "impact": "Detailed explanation of the life implication."
    #         }},
    #         {{
    #             "pattern": "string",
    #             "impact": "Detailed explanation of the life implication."
    #         }}
    #         ]
    #     }},
    #     "five_elements_analysis": {{
    #         "pillar_analysis": "Detailed analysis of how each pillar (Year, Month, Day, Hour) contributes to Five-Element balance.",
    #         "element_flow": "Explain how elements generate, control, or weaken each other across the chart.",
    #         "overall_judgement": "Classical concluding judgement phrase with explanation."
    #         }},
    #     "personality_and_traits": {{
    #         "strengths": "Narrative explanation of personality advantages derived from the chart.",
    #         "weaknesses": "Narrative explanation of personality limitations or risks.",
    #         "suitable_fields": "Explain suitable industries or roles with BaZi reasoning.",
    #         "avoid_fields": "Explain unsuitable industries or roles with BaZi reasoning."
    #     }},
    #     "auspicious_elements": {{
    #         "favorable_elements": ["string"],
    #         "reasoning": "Explain why these elements restore balance.",
    #         "colors": ["string"],
    #         "numbers": ["string"],
    #         "directions": ["string"],
    #         "climate": ["string"],
    #         "terrain": ["string"],
    #         "usage_tips": "Concrete daily-life or professional usage suggestions.",
    #         "avoid": ["string"]
    #     }},
    #     "career_and_investment": {{
    #         "suitable_paths": "Narrative explanation of suitable career and wealth paths.",
    #         "avoidance_paths": "Narrative explanation of unsuitable paths.",
    #         "investment_tendency": "Narrative wealth strategy description."
    #     }},
    #     "year_{target_year}_insight": {{
    #         "theme": "string",
    #         "yearly_explanation": "Detailed explanation of how the year interacts with the natal chart.",
    #         "investment_risk": "Specific risk timing or pattern explanation.",
    #         # "key_advice": "Concrete, actionable advice grounded in Five-Element logic."
    #     }},
    #     "conclusion": "Classical-style closing summary (1–2 paragraphs).",
    #     "amulet": {{
    #         "item": "string",
    #         "reason": "Why this amulet helps restore balance in this chart and year."
    #     }}
    #     }}
    #     """


    """
    Build a Gold Prompt v2.0 for LLM BaZi analysis.
    Fully dynamic, classical narrative, Ten Gods and Five-Element reasoning are derived from chart.
    """
    return f"""
        You are a professional Chinese BaZi (八字) master and life consultant with decades of experience in the Ziping (子平) tradition. 

        Your goal is to generate a **full BaZi report** in **classical narrative style**, for the given birth chart and target year {target_year}. Include:

        - Four Pillars overview
        - Ten Gods (十神) derived dynamically from the Day Master
        - Five-Element (五行) balance and flow
        - Personality, career, and age-phase judgement
        - Auspicious elements and practical advice
        - Yearly analysis and investment strategy for {target_year}
        - One amulet recommendation
        - Final concise advice summary

        ━━━━━━━━━━━━━━━━━━━━━━
        INPUT
        ━━━━━━━━━━━━━━━━━━━━━━
        BaZi data: {json.dumps(bazi_data, ensure_ascii=False)}
        Target year: {target_year}
        Language: {lang}

        ━━━━━━━━━━━━━━━━━━━━━━
        ANALYSIS RULES
        ━━━━━━━━━━━━━━━━━━━━━━
        1. **Four Pillars & Day Master**
        - Identify Day Master (日主) first.
        - Include all four pillars as a single string: "年柱/月柱/日柱/时柱".

        2. **Ten Gods Derivation**
        - Dynamically derive all Ten Gods (印星, 官杀, 财星, 比肩, 劫财, 食神, 伤官, 正印, 正财, etc.) from the Day Master and chart interactions.
        - Only include stars that actually appear in the chart.
        - For each derived star, provide:
            - Name (e.g., 印星)
            - Classical narrative explanation of its effect on personality, career, wealth
            - Interaction with Day Master and other stars
            - Metaphors if applicable (e.g.,「火炎土燥，金脆木枯」)

        3. **Five-Element Analysis**
        - Quantify element strength numerically (0–5 per element).
        - Analyze element flow, seasonal influence, and overall balance.
        - Identify core conflicts and which elements resolve them.
        - Provide long-form narrative explaining element distribution, pillar contributions, flow, conflicts, and resolution.

        4. **Personality & Career**
        - Explain personality strengths and weaknesses derived from Ten Gods and Five-Element interactions.
        - Suggest favorable and unfavorable career paths using BaZi logic.
        - Include age-phase judgement: early life (≤45), mid-life (45–55), late life (55+).

        5. **Auspicious Elements & Practical Advice**
        - Suggest favorable colors, numbers, directions, regions, climate, terrain based on element balance.
        - Include reasoning in classical narrative.
        - Provide concrete usage tips (daily life, work, or investment).

        6. **Target Year {target_year} Analysis**
        - Explain how the year {target_year} interacts with the natal chart.
        - Highlight new activations, changes, risks, and opportunities.
        - Provide year-specific investment and wealth strategy.

        7. **Amulet Recommendation**
        - Suggest exactly one amulet and explain why it restores balance for this chart and year.

        ━━━━━━━━━━━━━━━━━━━━━━
        OUTPUT RULES
        ━━━━━━━━━━━━━━━━━━━━━━
        - Return **STRICTLY valid JSON**, no markdown, no extra text.
        - Each narrative field can be long-form classical style.
        - Do NOT predefine any Ten God keys; they must be dynamically derived.
        - Include all derived stars in the "ten_gods_analysis" object with the star name as the key.

        Required JSON schema:

        {{
        "five_elements_analysis": "Long classical narrative explaining pillar contributions, flow, balance, conflicts, and resolution.",
        "ten_gods_analysis": {{
            "Each key is a dynamically derived Ten God": "Long classical narrative explaining this star's effect and interactions."
        }},
        "personality_and_career_logic": "Long narrative integrating Ten Gods, element balance, seasonal context, and age-phase.",
        "career_favorable": ["string", "..."],
        "career_unfavorable": ["string", "..."],
        "age_phase_judgement": "Narrative explaining early/mid/late life phases and fortune shifts.",
        "auspicious_elements": {{
            "colors": ["string"],
            "numbers": ["string"],
            "directions": ["string"],
            "regions": ["string"],
            "climate": ["string"],
            "terrain": ["string"],
            "usage_tips": "Concrete daily-life or professional usage suggestions",
            "avoid": ["string"]
        }},
        "year_{target_year}_analysis": "Long classical narrative for {target_year}, highlighting new dynamics, activated elements, and conflicts.",
        "investment_strategy_{target_year}": "Narrative describing wealth/investment approach for {target_year}.",
        "amulet": {{
            "item": "string",
            "reason": "Why it restores balance"
        }},
        "final_advice": "Concise classical-style summary (1–2 paragraphs)."
        }}

        ━━━━━━━━━━━━━━━━━━━━━━
        DETERMINISM
        ━━━━━━━━━━━━━━━━━━━━━━
        - Only one coherent result set.
        - No alternatives or conditional branches.
        - Apply deterministic BaZi reasoning, integrating Ten Gods, Five-Element balance, and seasonal influences.
    """


# -----------------------------
# OpenAI implementation
# -----------------------------
def _generate_oa(bazi_data, target_year="2026", lang="en"):
    prompt = build_bazi_prompt(bazi_data, target_year=target_year, lang=lang)
    resp = client_oa.chat.completions.create(
        model = OPENAI_LLM_MODEL,
        messages = [
            {"role":"system","content": "You are a professional Chinese fortune-teller and life coach"},
            {"role":"user","content":prompt}
        ],
        temperature = 0 , # ✅ 設定為0，減低隨機性，輸出會固定
        max_tokens = 2000
    )

    if not resp.choices or not resp.choices[0].message:
        raise RuntimeError("No response from OPENAI")
    
    output_text = resp.choices[0].message.content
    try:
        return safe_parse_json(output_text)
    except json.JSONDecodeError:
        return {"error": "OPENAI LLM output not valid JSON", "raw": output_text}

# -----------------------------
# Hunyuan implementation
# -----------------------------
def _generate_hy(bazi_data, target_year="2026", lang="en"):
    client = get_hunyuan_client()
    prompt = build_bazi_prompt(bazi_data, target_year=target_year, lang=lang)

    messages = [
        {"Role": "system", "Content": "You are a professional Chinese fortune-teller and life coach"},
        {"Role": "user", "Content": prompt}
    ]

    req = models.ChatCompletionsRequest()
    req.Model = HUNYUAN_LLM_MODEL
    req.Temperature = 0  # ✅ 設定為0，減低隨機性，輸出會固定
    req.Messages = messages

    resp = client.ChatCompletions(req)

    if not resp.Choices or not resp.Choices[0].Message:
        raise RuntimeError("No response from Hunyuan")

    output_text = resp.Choices[0].Message.Content.strip()
    try:
        return safe_parse_json(output_text)
    except json.JSONDecodeError:
        return {"error": "Hunyan LLM output not valid JSON", "raw": output_text}

# -----------------------------
# Qianwen implementation
# -----------------------------
def _generate_qw(bazi_data, target_year="2026", lang="en"):
    system_prompt = "You are a professional Chinese fortune-teller and life coach"
    prompt = build_bazi_prompt(bazi_data, target_year=target_year, lang=lang)

    response = dashscope.Generation.call(
        model = QIANWEN_LLM_MODEL,
        prompt = system_prompt + "\n\n" + prompt,
        temperature = 0, # ✅ 設定為0，減低隨機性，輸出會固定
        max_tokens = 2000
    )

    output_text = None
    if hasattr(response.output, "text"):
        output_text = response.output.text
    elif hasattr(response.output, "choices"):
        output_text = response.output.choices[0].text

    if not output_text:
        raise RuntimeError("No response from Qianwen")

    try:
        return safe_parse_json(output_text)
    except json.JSONDecodeError:
        return {"error": "Qianwen LLM output not valid JSON", "raw": output_text}


# -----------------------------
# Different langauge pillar
# -----------------------------
def enrich_with_localized_pillars(bazi_basic, lang="en"):
    pillars = bazi_basic.get("pillars", {})
    localized_pillars, pillar_string = localize_pillars(pillars, lang=lang)
    bazi_basic["pillars"] = localized_pillars
    bazi_basic["pillar_string"] = pillar_string

    # Optional: day master localized
    day_master = bazi_basic.get("day_master")
    if day_master:
        gan_map = GAN_MAP.get(lang, GAN_MAP["en"])
        day_master_local = gan_map[GAN_MAP["en"].index(day_master)]
        bazi_basic["day_master_local"] = day_master_local


# -----------------------------
# Unified interface
# -----------------------------    
def generate_bazi_narrative(bazi_data, target_year="2026", llm="openai", lang="en"):
    """
    Generate BaZi narrative JSON using the specified LLM.
    llm: "openai", "hunyuan", "qianwen"
    lang: "en" or "cn"
    """
    if llm.lower() in ["openai", "oa"]:
        return _generate_oa(bazi_data, target_year=target_year, lang=lang)
    elif llm.lower() in ["hunyuan", "hy"]:
        return _generate_hy(bazi_data, target_year=target_year, lang=lang)
    elif llm.lower() in ["qianwen", "qw"]:
        return _generate_qw(bazi_data, target_year=target_year, lang=lang)
    else:
        raise ValueError(f"Unknown LLM: {llm}")

def generate_bazi_narrative_safe(bazi_data, target_year="2026", llm="openai", lang="en"):
    """
    Wrapper with timeout + fallback.
    Does NOT change JSON schema.
    """

    def _run():
        return generate_bazi_narrative(bazi_data, target_year=target_year, llm=llm, lang=lang)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_run)
        try:
            llm_reflection = future.result(timeout=LLM_TIMEOUT)
            print(f"=== LLM SUCCESS： 【{llm}】 ===\nOUTPUT:\n{llm_reflection}\n{'-'*40}")
            return llm_reflection

        except Exception as e:
            print(f"[LLM ERROR] {llm} failed: {e}")

            if llm != FALLBACK_LLM:
                print(f"【LLM FALLBACK】Switching from 【{llm}】 to 【{FALLBACK_LLM}】")
                return generate_bazi_narrative_safe(
                    bazi_data,
                    target_year=target_year,
                    llm=FALLBACK_LLM,
                    lang=lang
                )

            raise



# -----------------------------
# Test run
# -----------------------------
if __name__ == "__main__":
    test_bazi = {
        "pillars": {
            "year": {"gan": "Bing", "zhi": "Wu"},
            "month": {"gan": "Wu", "zhi": "Xu"},
            "day": {"gan": "Xin", "zhi": "Chou"},
            "hour": {"gan": "Xin", "zhi": "Mao"}
        },
        "day_master": "Xin",
        "five_elements_strength": {
            "Wood": 1,
            "Fire": 3,
            "Earth": 2,
            "Metal": 2,
            "Water": 0
        }
    }

    # for llm_name in ["openai", "hunyuan", "qianwen"]:
    #     print(f"\n=== Test LLM: {llm_name} ===")
    #     result = generate_bazi_narrative(test_bazi, llm=llm_name, lang='cn')
    #     # Enrich with localized pillars
    #     if "bazi_basic" in result:
    #         enrich_with_localized_pillars(result["bazi_basic"], lang='cn')
    #     print(result)


    llm_name="qw"
    print(f"\n=== Querying LLM: {llm_name} ===")
    result = generate_bazi_narrative_safe(test_bazi, target_year="2026", llm=llm_name, lang='cn')
    print(str(result))
    
