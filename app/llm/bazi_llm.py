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

def convert_gregorian_year_to_gan_zhi(year: int) -> str:
    """
    Convert a Gregorian year to its Chinese Gan-Zhi (Heavenly Stem + Earthly Branch).
    Valid for years >= 1900 (approx).
    Example: 2026 → '丙午'
    """
    # The first year of the current 60-year cycle is 1984 (Jia Zi / 甲子)
    base_year = 1984
    stems = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
    branches = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
    
    offset = year - base_year
    cycle_index = offset % 60
    
    stem = stems[cycle_index % 10]
    branch = branches[cycle_index % 12]
    
    return stem + branch

# def build_bazi_prompt(bazi_data, target_year=2026, lang="zh"):

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

def build_bazi_prompt(bazi_data, target_year=2026, lang="zh"):
    """
    Build a deterministic BaZi LLM prompt.
    Focus: correct Five-Element reasoning, especially decision style.
    """
    return f"""
        You are a professional Chinese BaZi (八字) practitioner following the Ziping (子平) system.

        Your task is to generate a BaZi analysis report based STRICTLY on the provided data.
        You must reason carefully and avoid symbolic shortcuts.

        ━━━━━━━━━━━━━━━━━━━━━━
        INPUT (AUTHORITATIVE)
        ━━━━━━━━━━━━━━━━━━━━━━
        BaZi data (already calculated, DO NOT reinterpret):
        {json.dumps(bazi_data, ensure_ascii=False)}

        Target year: {target_year}
        Language: {lang}

        ━━━━━━━━━━━━━━━━━━━━━━
        ABSOLUTE RULES (CRITICAL)
        ━━━━━━━━━━━━━━━━━━━━━━

        1. **Five-Element Strengths Are Ground Truth**
        - The numeric 五行 strength values are FINAL results from a deterministic engine.
        - Do NOT infer element strength from:
        - season
        - pillar names
        - element symbolism
        - All reasoning MUST be based on RELATIVE comparison of the given values only.

        2. **Fire Interpretation Rule (NON-NEGOTIABLE)**
        - Fire (火) represents:
        - external pressure
        - urgency
        - environmental push
        - Fire does NOT automatically mean:
        - decisiveness
        - fast action
        - impulsiveness

        3. **Decision Style Inference Rule (MANDATORY)**

        When describing personality—especially decision-making—always infer style from the functional roles of the elements, as follows:

        - Water: Deliberation, internal simulation, buffering against haste.  
        - Metal: Judgment precision, ability to cut through ambiguity and finalize.  
        - Earth: Stability orientation, risk containment, reliance on proven frameworks.  
        - Fire: External pressure or urgency—not decisiveness.  

        ⚠️ Wood is excluded from decision-style analysis; it governs initiative and direction, not evaluation or closure.

        **Tone & Framing Requirement (MANDATORY):**  
        > All descriptions must be **constructive, empowering, and strength-oriented**. Frame traits as **adaptive strategies**, not deficits. Highlight **where the person excels**, and position limitations as **contextual considerations**—not flaws. Avoid discouraging, pathologizing, or fatalistic language.

        **Output requirements:**  
        - Describe how decisions are made: tempo, risk handling, internal process, and response to pressure.  
        - Never use vague trait labels (e.g., “cautious,” “decisive”) unless directly grounded in elemental interactions.  
        - Prefer precise terms: 慎重 / 反复思考 / 内在推演 / 风险控制 / 延迟决策（尤其在高压下） / 快速收尾 / 边界清晰.  

        **Key dynamics to reference:**  
        - Strong Water + Strong Metal → deep analysis followed by sharp conclusion.  
        - Strong Water + Weak Metal → over-analysis without closure.  
        - Weak Water + Strong Metal → quick judgment, possibly premature.  
        - Strong Earth → avoids novelty; prioritizes safety and consistency.  
        - High Fire + Weak Water → reactive decisions under pressure.  

        **Prohibited:**  
        - Equating Fire with decisiveness.  
        - Using Western personality models (e.g., MBTI).  
        - Ignoring the absence of an element (e.g., missing Metal = no natural cutoff).  
        - Using discouraging phrasing like “lacks,” “deficient,” “unable,” “unsuitable,” or “should avoid.”  
        - Implying the person is “at risk” or “vulnerable” without offering a constructive reframing.  

        **Instead, always:**  
        ✅ Emphasize **clarity, efficiency, reliability, and precision** as strengths.  
        ✅ Position preferences (e.g., for structure) as **strategic advantages in the right context**.  
        ✅ Suggest **optimal environments** where their natural style thrives—rather than listing what to avoid.

        4. **Ten Gods Usage Rule (STRICT & LIMITED)**

        - Ten Gods (十神) may be derived internally.
        - They are used ONLY as a secondary explanatory layer.
        - Five-Element logic ALWAYS dominates reasoning priority.
        - The example Ten God names and descriptions shown in the output structure are PLACEHOLDERS only and MUST NOT be reused verbatim.


        Output constraints (MANDATORY):
        - Output EXACTLY THREE (3) Ten Gods only.
        - They must be the MOST INFLUENTIAL based on the chart structure.
        - Use CHINESE Ten God names ONLY (e.g., 正官, 七杀, 偏财).
        - Each Ten God:
            - One concise, practical sentence
            - Focus on behavioral manifestation, not theory
            - No classical jargon, no metaphors

        Prohibited:
        - Listing more than three Ten Gods
        - Explaining generation/control cycles
        - Repeating textbook definitions

        ━━━━━━━━━━━━━━━━━━━━━━
        OUTPUT REQUIREMENTS
        ━━━━━━━━━━━━━━━━━━━━━━

        Return STRICTLY valid JSON.
        No markdown.
        No explanations outside JSON.

        Required structure:

        {{
        "five_elements_analysis": "Explain element distribution, flow, imbalance, and resolution using the provided numeric strengths.",
        "ten_gods_analysis": {{
            "<十神一>": "<一句基于命局结构的现实层面解释>",
            "<十神二>": "<一句基于行为或决策模式的解释>",
            "<十神三>": "<一句体现实际作用方式的解释>"
        }},
        "personality_and_career_logic": "Personality and career reasoning derived from Five-Element balance and decision style rules.",
        "career_favorable": ["..."],
        "career_unfavorable": ["..."],
        "age_phase_judgement": "Early / mid / late life analysis.",
        "auspicious_elements": {{
            "colors": ["..."],
            "numbers": ["..."],
            "directions": ["..."],
            "regions": ["..."],
            "climate": ["..."],
            "terrain": ["..."],
            "usage_tips": "...",
            "avoid": ["..."]
        }},
        "year_{target_year}_analysis": "Interaction between natal chart and target year.",
        "investment_strategy_{target_year}": "Risk and strategy guidance.",
        "amulet": {{
            "item": "...",
            "reason": "Why it balances this chart"
        }},
        "final_advice": "Concise, grounded summary."
        }}

        ━━━━━━━━━━━━━━━━━━━━━━
        DETERMINISM
        ━━━━━━━━━━━━━━━━━━━━━━
        - Produce ONE coherent result.
        - No alternatives.
        - No hedging language.
        - Reason step-by-step internally, but output conclusions only.
        """



# def build_bazi_prompt(bazi_data, target_year, gan_zhi_year, lang="en"):
#     return f"""
#         You are a professional Chinese BaZi (八字) master in the classical Ziping (子平) tradition, with deep expertise in seasonal energy, hidden stems, and structural balance.

#         Your task is to generate a **complete, deterministic BaZi report** in **classical narrative style** for the given chart and target year {target_year}.

#         ━━━━━━━━━━━━━━━━━━━━━━
#         INPUT
#         ━━━━━━━━━━━━━━━━━━━━━━
#         BaZi data: {json.dumps(bazi_data, ensure_ascii=False)}
#         Language: {lang}

#         ━━━━━━━━━━━━━━━━━━━━━━
#         ANALYSIS RULES (MUST FOLLOW STRICTLY)
#         ━━━━━━━━━━━━━━━━━━━━━━
#         0. **Foundational Judgment (DO THIS FIRST)**
#         - Identify the Day Master (日主).
#         - Determine if the Day Master is **Strong, Balanced, or Weak** based on:
#                 a) Seasonal power (Month Branch),
#                 b) Support from印 (Seal/Resource) and比劫 (Competition/Self),
#                 c) Drain from財 (Wealth) and consumption by食傷 (Output).
#         - Identify the core imbalance: excess/deficiency, dryness/moisture, clarity/turbidity.
#         → This judgment anchors ALL subsequent analysis.

#         1. **Four Pillars & Hidden Stems**
#         - Present pillars as: "年柱/月柱/日柱/时柱".
#         - Analyze **both visible stems and hidden stems in Earthly Branches** (e.g., 午 = 丁+己).

#         2. **Ten Gods Derivation**
#         - Derive Ten Gods **dynamically from the Day Master**.
#         - **Only include stars that actually appear** (in stems or hidden stems).
#         - For each, explain:
#                 - Classical effect on personality, career, wealth,
#                 - Interaction with Day Master and other stars,
#                 - Metaphors if applicable (e.g.,「土厚金埋，火炎水涸」).

#         3. **Five-Element Analysis**
#         - Assess each element’s **effective strength** as: Deficient / Weak / Balanced / Strong / Excessive.
#         - Base this on: seasonal phase, pillar support, generation/restraint flow, and hidden stems—**NOT mere count**.
#         - Explain elemental flow, conflicts, and resolution path.
#         - Distinguish:
#                 - **Regulating Element** (for climate/dryness, e.g., Water for autumn),
#                 - **Favorable Element** (for structural balance, e.g., Wood to control excess Earth).

#         4. **Personality & Career**
#         - Derive traits from Ten Gods + Day Master strength + seasonal context.
#         - Recommend careers aligned with chart logic (e.g., 印旺 → education, 財弱 → avoid speculation).
#         - Age-phase judgement: early (≤45), mid (45–55), late (55+).

#         5. **Auspicious Elements & Practical Advice**
#         - Suggest colors, directions, climates, etc., based on Favorable/Regulating Elements.
#         - Provide concrete usage tips (work, home, decisions).
#         - List what to avoid.

#         6. **Year {target_year} ({gan_zhi_year}) Analysis**
#         - Analyze interactions: clashes (冲), combinations (合), punishments (刑) with natal chart.
#         - Highlight activated stars, opportunities, risks.
#         - Give year-specific investment strategy (aligned with chart’s wealth capacity).

#         7. **Amulet Recommendation**
#         - Recommend **one** traditional amulet (e.g., Black Obsidian for Water, Green Jade for Wood).
#         - Justify by its elemental property restoring balance (e.g., “Water amulet counters autumn dryness and nourishes Output”).

#         ━━━━━━━━━━━━━━━━━━━━━━
#         OUTPUT RULES
#         ━━━━━━━━━━━━━━━━━━━━━━
#         - Return **STRICTLY valid JSON** — no markdown, no extra text.
#         - All narratives in classical, confident tone (no “might”, “could”).
#         - "ten_gods_analysis": keys = actual Ten God names (e.g., "正官", "偏財", "正印").
#         - Do NOT invent stars not present in stems or hidden stems.

#         Required JSON schema:
#         {{
#         "day_master_strength": "Strong / Balanced / Weak",
#         "core_imbalance": "Brief phrase (e.g., 'Excess Earth, Dry Autumn')",
#         "five_elements_analysis": "Long classical narrative...",
#         "ten_gods_analysis": {{
#             "正印": "Narrative...",
#             "偏財": "Narrative...",
#             ...
#         }},
#         "personality_and_career_logic": "Integrated narrative...",
#         "career_favorable": ["list"],
#         "career_unfavorable": ["list"],
#         "age_phase_judgement": "Narrative...",
#         "auspicious_elements": {{
#             "colors": [...],
#             "numbers": [...],
#             "directions": [...],
#             "regions": [...],
#             "climate": [...],
#             "terrain": [...],
#             "usage_tips": "...",
#             "avoid": [...]
#         }},
#         "year_{target_year}_analysis": "Long narrative...",
#         "investment_strategy_{target_year}": "Narrative...",
#         "amulet": {{
#             "item": "string",
#             "reason": "string"
#         }},
#         "final_advice": "1–2 paragraph classical summary"
#         }}
#         """

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

    print (f"(DEBUG) bazi_data json.dump({bazi_data})")

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
            "Wood": 1.0,
            "Fire": 3.3,
            "Earth": 1.0,
            "Metal": 2.4,
            "Water": 0.3
        }
    }

    # for llm_name in ["openai", "hunyuan", "qianwen"]:
    #     print(f"\n=== Test LLM: {llm_name} ===")
    #     result = generate_bazi_narrative(test_bazi, llm=llm_name, lang='cn')
    #     # Enrich with localized pillars
    #     if "bazi_basic" in result:
    #         enrich_with_localized_pillars(result["bazi_basic"], lang='cn')
    #     print(result)


    llm_name="openai"
    print(f"\n=== Querying LLM: {llm_name} ===")
    result = generate_bazi_narrative_safe(test_bazi, target_year="2026", llm=llm_name, lang='cn')
    print(str(result))
    
