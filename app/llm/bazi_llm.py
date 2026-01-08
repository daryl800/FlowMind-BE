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
LLM_TIMEOUT = 50  # seconds

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


# -----------------------------
# Prompt template (shared)
# -----------------------------
def build_bazi_prompt(bazi_data, lang="en"):
    """
    Build a BaZi LLM prompt that emphasizes the specific year
    and following 蘇民峰's philosophy.
    """
    import json

    year = bazi_data.get("year", 2026)
    
    return f"""
        You are a professional Chinese fortune-teller and life coach, following 蘇民峰's philosophy: always **balance the strongest elements** rather than enhancing them.

        Input BaZi data:
        {json.dumps(bazi_data, ensure_ascii=False)}

        Generate a **JSON report ONLY** with the following structure, focusing on **what is unique or different for the year {year}** compared to other years:

        {{
            "lucky_elements": {{
                "favorable_elements": [],
                "unfavorable_elements": []
            }},
            "lucky_colors_numbers": {{
                "colors": [],
                "numbers": []
            }},
            "regional_advice": {{
                "favorable_regions": [],
                "unfavorable_regions": [],
                "directions": "",
                "reasoning": ""
            }},
            "career_and_investment": {{
                "favorable_careers": [],
                "unfavorable_careers": [],
                "investment_tendency": ""
            }},
            "year_{year}_outlook": {{
                "theme": "",
                "health": "",
                "relationships": "",
                "career": "",
                "investment": "",
                "key_advice": ""
            }},
            "amulet": "" 
        }}

        Instructions for the LLM:

        1. Identify the strongest element(s) in the BaZi chart as the PRIMARY reference,
        and recommend regions, directions, colors, numbers, and careers that BALANCE
        these elements (do NOT reinforce them).

        2. Emphasize year-specific opportunities, challenges, and changes unique to {year}
        compared to previous years.

        3. Highlight seasonal, directional, and Five-Element interactions that are
        specific to {year} and this BaZi chart.

        4. For career, relationships, and health, describe what is NEW or DIFFERENT
        this year while maintaining Five-Element balance.

        5. Lucky elements, colors, numbers, regions, and directions must be derived
        from the interaction between the BaZi chart and the year {year},
        following balance-first principles.

        6. Regional advice must use ONLY broad global regions.
        Allowed regions are STRICTLY LIMITED to:
        East Asia, Southeast Asia, South Asia, Middle East,
        Europe, Africa, North America, South America, Oceania.
        Do NOT mention countries, cities, provinces, climates, or local features.

        7. For `amulet`, suggest ONE specific object beneficial for {year}
        that helps restore Five-Element balance.

        8. Output STRICTLY valid JSON only.
        No explanations, no markdown, no examples, no extra text.

        9. Only use the following 8 directions:
        North, Northeast, East, Southeast,
        South, Southwest, West, Northwest.

        10. Use language: {lang}.

        11. Deterministic reasoning ONLY:
            - no alternatives
            - no multiple options
            - no contradictory interpretations
            - one single coherent result set
    """

# -----------------------------
# OpenAI implementation
# -----------------------------
def _generate_oa(bazi_data, lang="en"):
    prompt = build_bazi_prompt(bazi_data, lang)
    resp = client_oa.chat.completions.create(
        model = OPENAI_LLM_MODEL,
        messages = [
            {"role":"system","content": "You are a professional Chinese fortune-teller and life coach"},
            {"role":"user","content":prompt}
        ],
        temperature = 0 , # ✅ 設定為0，減低隨機性，輸出會固定
        max_tokens = 1500
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
def _generate_hy(bazi_data, lang="en"):
    client = get_hunyuan_client()
    prompt = build_bazi_prompt(bazi_data, lang)

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
def _generate_qw(bazi_data, lang="en"):
    system_prompt = "You are a professional Chinese fortune-teller and life coach"
    prompt = build_bazi_prompt(bazi_data, lang)

    response = dashscope.Generation.call(
        model = QIANWEN_LLM_MODEL,
        prompt = system_prompt + "\n\n" + prompt,
        temperature = 0, # ✅ 設定為0，減低隨機性，輸出會固定
        max_tokens = 1500
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
def generate_bazi_narrative(bazi_data, llm="openai", lang="en"):
    """
    Generate BaZi narrative JSON using the specified LLM.
    llm: "openai", "hunyuan", "qianwen"
    lang: "en" or "cn"
    """
    if llm.lower() in ["openai", "oa"]:
        return _generate_oa(bazi_data, lang)
    elif llm.lower() in ["hunyuan", "hy"]:
        return _generate_hy(bazi_data, lang)
    elif llm.lower() in ["qianwen", "qw"]:
        return _generate_qw(bazi_data, lang)
    else:
        raise ValueError(f"Unknown LLM: {llm}")

def generate_bazi_narrative_safe(bazi_data, llm="openai", lang="en"):
    """
    Wrapper with timeout + fallback.
    Does NOT change JSON schema.
    """

    def _run():
        return generate_bazi_narrative(bazi_data, llm=llm, lang=lang)

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_run)
        try:
            llm_reflection = future.result(timeout=LLM_TIMEOUT)
            print(f"=== LLM SUCCESS： 【{llm}】 ===\n OUTPUT: {llm_reflection}\n{'-'*40}")
            return llm_reflection

        except Exception as e:
            print(f"[LLM ERROR] {llm} failed: {e}")

            if llm != FALLBACK_LLM:
                print(f"【LLM FALLBACK】Switching from 【{llm}】 to 【{FALLBACK_LLM}】")
                return generate_bazi_narrative_safe(
                    bazi_data,
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
    result = generate_bazi_narrative_safe(test_bazi, llm=llm_name, lang='cn')
    print(str(result))
    
