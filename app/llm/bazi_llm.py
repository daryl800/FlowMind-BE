import re
import json
from click import prompt
import dashscope
from openai import OpenAI
from tencentcloud.hunyuan.v20230901 import hunyuan_client, models
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile

import concurrent.futures

from app.config.settings import QIANWEN_API_KEY, TENCENT_SECRET_ID, TENCENT_SECRET_KEY, OPENAI_API_KEY
from app.config.settings import QIANWEN_LLM_MODEL, HUNYUAN_LLM_MODEL, OPENAI_LLM_MODEL

from app.bazi.engine import GAN, GAN_MAP, ZHI_MAP, localize_pillars

FALLBACK_LLM = ""
LLM_TIMEOUT = 800  # seconds

if not OPENAI_API_KEY:
    raise ValueError("Please set OPENAI_API_KEY in your environment")
client_oa = OpenAI(api_key=OPENAI_API_KEY)

# ---- Hunyuan ----
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
            raise
    return _hunyuan_client

# ---- Qianwen ----
dashscope.api_key = QIANWEN_API_KEY

def safe_parse_json(text: str):
    text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise json.JSONDecodeError("No JSON object found", text, 0)
    json_text = text[start:end + 1]
    return json.loads(json_text)

def convert_gregorian_year_to_gan_zhi(year: int) -> str:
    base_year = 1984
    stems = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
    branches = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
    offset = year - base_year
    cycle_index = offset % 60
    stem = stems[cycle_index % 10]
    branch = branches[cycle_index % 12]
    return stem + branch

# def build_bazi_prompt(bazi_data, target_year=2026, lang="zh"):
    # """
    # Build a deterministic BaZi LLM prompt with support for unknown birth time.
    # """
    
    # # Check if this is a 3-pillar or 4-pillar chart
    # pillars_count = bazi_data.get("pillars_count", 4)
    # has_hour_pillar = "hour" in bazi_data.get("pillars", {})
    
    # # Create a clean copy for the prompt
    # prompt_data = {
    #     "pillars_count": pillars_count,
    #     "pillars": bazi_data["pillars"],
    #     "day_master": bazi_data["day_master"],
    #     "five_elements_strength": bazi_data["five_elements_strength"]
    # }
    
    # # Add disclaimer if time is unknown
    # if pillars_count == 3 or not has_hour_pillar:
    #     prompt_data["disclaimer"] = "出生时间不详，时柱未推算。分析基于年、月、日三柱。"
    #     prompt_data["disclaimer_en"] = "Birth time unknown. Hour pillar not calculated. Analysis based on year, month, and day pillars only."
    
    # return f"""
    #     You are a professional Chinese BaZi (八字) practitioner following the Ziping (子平) system.

    #     Your task is to generate a BaZi analysis report based STRICTLY on the provided data.
    #     You must reason carefully and avoid symbolic shortcuts.
    #     You are NOT writing a textbook; you are describing a real person.

    #     ━━━━━━━━━━━━━━━━━━━━━━
    #     INPUT (AUTHORITATIVE)
    #     ━━━━━━━━━━━━━━━━━━━━━━
    #     BaZi data (already calculated, DO NOT reinterpret):
    #     {json.dumps(prompt_data, ensure_ascii=False, indent=2)}

    #     Target year: {target_year}
    #     Language: {lang}

    #     ━━━━━━━━━━━━━━━━━━━━━━
    #     CRITICAL CONTEXT
    #     ━━━━━━━━━━━━━━━━━━━━━━
        
    #     {"⚠️ IMPORTANT: This client's birth time is UNKNOWN. The hour pillar is NOT calculated." if pillars_count == 3 else ""}
        
    #     {"Since the hour pillar is missing, your analysis should:" if pillars_count == 3 else ""}
    #     {"1. Focus primarily on year, month, and day pillars" if pillars_count == 3 else ""}
    #     {"2. Note that hour-related aspects (children, later life details) cannot be analyzed" if pillars_count == 3 else ""}
    #     {"3. Frame the analysis as comprehensive yet transparent about limitations" if pillars_count == 3 else ""}
    #     {"4. Emphasize what CAN be determined from the three pillars" if pillars_count == 3 else ""}

    #     ━━━━━━━━━━━━━━━━━━━━━━
    #     ABSOLUTE RULES (CRITICAL)
    #     ━━━━━━━━━━━━━━━━━━━━━━

    #     1. Five-Element Strengths Are Ground Truth
    #     - The numeric 五行 strength values are FINAL results from a deterministic engine.
    #     - Do NOT infer element strength from:
    #     - season
    #     - pillar names
    #     - element symbolism
    #     - All reasoning MUST be based on RELATIVE comparison of the given values only.
        
    #     {"- For 3-pillar charts, the element strengths reflect only year, month, and day pillars." if pillars_count == 3 else ""}

    #     2. Fire Interpretation Rule (NON-NEGOTIABLE)
    #     - Fire (火) represents:
    #     - external pressure
    #     - urgency
    #     - environmental push
    #     - Fire does NOT automatically mean:
    #     - decisiveness
    #     - fast action
    #     - impulsiveness

    #     3. Decision Style Inference Rule (MANDATORY)

    #     When describing personality—especially decision-making—always infer style from the functional roles of the elements, as follows:

    #     - Water: Deliberation, internal simulation, buffering against haste.  
    #     - Metal: Judgment precision, ability to cut through ambiguity and finalize.  
    #     - Earth: Stability orientation, risk containment, reliance on proven frameworks.  
    #     - Fire: External pressure or urgency—not decisiveness.  

    #     ⚠️ Wood is excluded from decision-style analysis; it governs initiative and direction, not evaluation or closure.

    #     Tone & Framing Requirement (MANDATORY):
    #     - All descriptions must be constructive, empowering, and strength-oriented.
    #     - Frame traits as adaptive strategies, not deficits.
    #     - Highlight where the person excels, and position limitations as contextual considerations—not flaws.
    #     - Avoid discouraging, pathologizing, or fatalistic language.

    #     Decision-style output requirements:
    #     - Describe how decisions are made: tempo, risk handling, internal process, and response to pressure.
    #     - Never use vague trait labels (e.g., “谨慎”, “果断”) unless directly grounded in elemental interactions.
    #     - Prefer precise terms: 慎重 / 反复思考 / 内在推演 / 风险控制 / 延迟决策（尤其在高压下） / 快速收尾 / 边界清晰.

    #     Key dynamics to reference:
    #     - Strong Water + Strong Metal → deep analysis followed by sharp conclusion.  
    #     - Strong Water + Weak Metal → over-analysis without closure.  
    #     - Weak Water + Strong Metal → quick judgment, possibly premature.  
    #     - Strong Earth → avoids novelty; prioritizes safety and consistency.  
    #     - High Fire + Weak Water → reactive decisions under pressure.  

    #     Prohibited:
    #     - Equating Fire with decisiveness.  
    #     - Using Western personality models (e.g., MBTI).  
    #     - Ignoring the absence of an element (e.g., missing Metal = no natural cutoff).  
    #     - Using discouraging phrasing like “lacks,” “deficient,” “unable,” “unsuitable,” or “should avoid.”  
    #     - Implying the person is “at risk” or “vulnerable” without offering a constructive reframing.  

    #     Instead, always:
    #     - Emphasize clarity, efficiency, reliability, and precision as strengths.  
    #     - Position preferences (e.g., for structure) as strategic advantages in the right context.  
    #     - Suggest optimal environments where their natural style thrives—rather than listing what to avoid.

    #     4. Ten Gods Usage Rule (STRICT & LIMITED)

    #     {"- For 3-pillar charts, Ten Gods are derived from year, month, and day pillars only." if pillars_count == 3 else ""}
    #     - Ten Gods (十神) may be derived internally.
    #     - They are used ONLY as a secondary explanatory layer.
    #     - Five-Element logic ALWAYS dominates reasoning priority.
    #     - The example Ten God names and descriptions shown in the output structure are PLACEHOLDERS only and MUST NOT be reused verbatim.

    #     Output constraints for Ten Gods:
    #     - Output EXACTLY THREE (3) Ten Gods only.
    #     - They must be the MOST INFLUENTIAL based on the chart structure.
    #     - Use CHINESE Ten God names ONLY (e.g., 正官, 七杀, 偏财).
    #     - Each Ten God:
    #         - One concise, practical sentence
    #         - Focus on behavioral manifestation, not theory
    #         - No classical jargon

    #     Prohibited:
    #     - Listing more than three Ten Gods
    #     - Explaining generation/control cycles
    #     - Repeating textbook definitions

    #     ━━━━━━━━━━━━━━━━━━━━━━
    #     STYLE & PERSONA REQUIREMENTS
    #     ━━━━━━━━━━━━━━━━━━━━━━

    #     You are describing a real person, not teaching BaZi.

    #     - Use natural, everyday Chinese (if lang == "zh") suitable for speaking to an educated layperson.
    #     - Avoid命理术语堆砌；把结论翻译成生活中的表现方式。
    #     - Wherever possible, anchor traits in concrete behaviors:
    #     - how they talk
    #     - how they work
    #     - how they handle conflict
    #     - how they show care
    #     - how they react under pressure
    #     - You may occasionally use轻微比喻（如“外柔内刚”、“像精细打磨过的金属”）来帮助理解，但不要过度诗化。

    #     ━━━━━━━━━━━━━━━━━━━━━━
    #     OUTPUT REQUIREMENTS
    #     ━━━━━━━━━━━━━━━━━━━━━━

    #     Return STRICTLY valid JSON.
    #     No markdown.
    #     No explanations outside JSON.

    #     Required structure:

    #     {{
    #     "five_elements_analysis": "Explain element distribution, flow, imbalance, and resolution using the provided numeric strengths. No theory dumping; focus on what this means for how this person actually operates in life.",
    #     "ten_gods_analysis": {{
    #         "<十神一>": "<一句基于命局结构的现实层面解释>",
    #         "<十神二>": "<一句基于行为或决策模式的解释>",
    #         "<十神三>": "<一句体现实际作用方式的解释>"
    #     }},
    #     "personality_portrait": "Use 3–6 short paragraphs to描写这个人的性格与气质，像在向第三者介绍一个真实存在的人。包括外在给人的感觉、内在动力、情绪处理方式、人际互动风格。避免空泛形容词，尽量用具体场景和行为描述。",
    #     "decision_style": "专门总结其决策节奏、信息处理方式、风险态度、在压力下的反应，严格基于前述决策规则与五行强弱。",
    #     "personality_and_career_logic": "Explain how the Five-Element balance and decision style translate into职业优势、适合的角色类型、典型工作风格。",
    #     "career_favorable": ["具体职业或角色类型，基于性格与五行逻辑，而不是随意罗列"],
    #     "career_unfavorable": ["在什么类型的环境或角色中会消耗较大，并说明原因（以偏好与能量匹配为角度，而非否定）。"],
    #     "age_phase_judgement": "Early / mid / late life analysis, focusing on心态变化、决策风格演变、资源与机会的使用方式。",
    #     "auspicious_elements": {{
    #         "colors": ["..."],
    #         "numbers": ["..."],
    #         "directions": ["..."],
    #         "regions": ["..."],
    #         "climate": ["..."],
    #         "terrain": ["..."],
    #         "usage_tips": "Explain how to practically use these preferences in生活与工作场景中。",
    #         "avoid": ["..."]
    #     }},
    #     "year_{target_year}_analysis": "Interaction between natal chart and target year, focusing on决策压力、机会类型、适合的节奏与策略。",
    #     "investment_strategy_{target_year}": "Risk and strategy guidance, tightly linked to其决策风格与当年环境，而不是空泛理财建议。",
    #     "amulet": {{
    #         "item": "...",
    #         "reason": "Why it balances this chart, explained in plain language, linked to五行失衡与心理感受。"
    #     }},
    #     "final_advice": "Concise, grounded summary: 2–4 sentences,回扣性格、决策风格与当年重点，给出可执行的态度与方向建议。"
    #     }}

    #     ━━━━━━━━━━━━━━━━━━━━━━
    #     DETERMINISM
    #     ━━━━━━━━━━━━━━━━━━━━━━
    #     - Produce ONE coherent result.
    #     - No alternatives.
    #     - No hedging language.
    #     - Reason step-by-step internally, but output conclusions only.
    #     """

import json

def build_bazi_prompt(bazi_data, target_year=2026, lang="zh"):
    pillars_count = len(bazi_data.get("pillars", {}))
    has_hour_pillar = "hour" in bazi_data.get("pillars", {})

    prompt_data = {
        "pillars_count": pillars_count,
        "pillars": bazi_data["pillars"],
        "day_master": bazi_data["day_master"],
        "five_elements_strength": bazi_data["five_elements_strength"]
    }

    if pillars_count == 3 or not has_hour_pillar:
        prompt_data["disclaimer"] = "出生时间不详，时柱未推算。分析基于年、月、日三柱。"

    return f"""
你是一位专业的八字命理师，擅长子平法。
你的任务是根据给定的命盘数据，写一份面向真实人物的分析报告。

你不是在描述"这个人是什么性格"，而是在描述"这个人天生对什么有亲和力、什么样的环境让ta自然发挥、什么样的情况让ta消耗过度"。

人的性格受成长环境、文化、经历影响极大，命盘无法精确预测性格。
但命盘可以揭示：天然倾向、能量亲和力、生命节奏模式。

━━━━━━━━━━━━━━━━━━━━━━
输入数据（已计算完成，直接使用）
━━━━━━━━━━━━━━━━━━━━━━
{json.dumps(prompt_data, ensure_ascii=False, indent=2)}

目标年份：{target_year}
语言：{lang}

{"⚠️ 注意：出生时间不详，无时柱。分析基于年、月、日三柱。" if pillars_count == 3 else ""}

━━━━━━━━━━━━━━━━━━━━━━
第一步：判断日主身强 / 身弱（必须先做，所有解读基于此）
━━━━━━━━━━━━━━━━━━━━━━

日主 = {prompt_data["day_master"]}

判断逻辑：
- 生日主的五行（印星、比劫）合计数值 vs 克泄日主的五行合计数值
- 身强：日主得助多，能驾驭旺神
- 身弱：日主受困，被旺神带着走

【铁律】旺神对日主的影响方向取决于身强/身弱：

日主五行    旺神      身强表现              身弱表现
─────────────────────────────────────────────────
土          水旺      深思后务实落地        思绪泛滥、难以收束、话多停不下来
土          木旺      有方向感、主动进取    被外界拉着走、难以坚守立场
金          火旺      压力下展现精准执行    焦虑耗散、高压下快速消耗
木          金旺      有原则有边界          感受到压迫、容易退缩
火          水旺      情绪有深度、直觉准    情绪不稳、容易被外界冷却热情
水          土旺      稳中有深度            被压制、流动性受阻

━━━━━━━━━━━━━━━━━━━━━━
核心规则
━━━━━━━━━━━━━━━━━━━━━━

1. 日主定基调（铁律）
每一段描述的第一句必须从日主五行的本质出发：
- 甲乙木：生长、方向感、主动开拓
- 丙丁火：表达、连接、感染力
- 戊己土：包容、承载、务实扎根
- 庚辛金：精准、原则、有边界
- 壬癸水：流动、适应、思虑深

禁止：以五行分布最强项替代日主定基调。

2. 五行含义（固定）
- 火 = 外部压力、紧迫感、环境推力（不是决断力或冲动）
- 水 = 思虑、内在推演、信息沉淀
- 金 = 收尾力、切割、做出结论
- 土 = 稳健、风险控制、依赖经验
- 木 = 方向感、行动力（不参与决策风格分析）

3. 决策风格推断（固定）
- 水强 + 金强 → 深思后有清晰结论
- 水强 + 金弱 → 反复推演，收尾慢
- 水弱 + 金强 → 判断快，但可能信息不足
- 土强 → 偏好已知路径，稳定优先
- 火强 + 水弱 → 压力下容易仓促反应

4. 用倾向代替定性（铁律）
禁止说："ta是个内向的人"、"ta很谨慎"、"ta性格X"
必须说："ta天生对X类型的事物有亲和力"、"ta在X环境下容易找到节奏"、"ta的生命轨迹中X模式往往比同龄人更明显"

示例转换：
❌ "她安静内敛，习惯最后发言"
✅ "她天生对需要耐心积累的场景有亲和力——不是不愿开口，而是在信息沉淀之后说出的话更有分量"

❌ "他执行力强"
✅ "他的生命轨迹中，外部压力往往是启动高效状态的触发点——截止日期、突发要求，反而让他进入最佳节奏"

━━━━━━━━━━━━━━━━━━━━━━
语气要求
━━━━━━━━━━━━━━━━━━━━━━

用自然的中文，像在向朋友介绍另一个人的"天然倾向"。

避免：
- 命理术语堆砌（劫财、七杀少用）
- 空泛形容词（"谨慎的人"、"聪明的人"）
- 负面定性（改用"在X情况下容易消耗过度"）
- 直接断言性格（改用倾向、亲和力、生命模式）

必须做到：
- 每个倾向描述都有具体的生活场景或行为举例
- 把命理结论翻译成"生命中容易出现的模式"

━━━━━━━━━━━━━━━━━━━━━━
输出格式
━━━━━━━━━━━━━━━━━━━━━━

只返回 JSON，无 markdown，无额外解释。

{{
  "tendency_portrait": "3-5段。不描述性格，而是描述：ta天生对什么有亲和力、什么样的环境让ta自然发挥、什么样的互动模式在ta生命中反复出现。必须包含至少2个具体生活场景。开头必须从日主五行本质出发。",

  "decision_tendency": "描述决策节奏与信息处理方式：ta在做重要决定时的天然节奏、对风险的本能态度、压力下的典型反应模式。必须包含至少1个具体场景。用'倾向于'、'容易'、'往往'等表述，不做性格定性。",

  "environment_affinities": {{
    "energizing": ["2-3种让ta自然发挥的环境或场景，说明为什么这类环境与ta的天然倾向吻合"],
    "draining": ["2-3种容易让ta过度消耗的环境，用'需要长期…的环境'表述，说明消耗机制"]
  }},

  "life_pattern_summary": "1-2句话。用比喻描述这个命盘的整体能量格局和生命节奏。不罗列数值，不用命理术语。例如：'像一条有方向感的河，水量充沛但需要找到合适的河床才能稳定流淌。'",

  "life_rhythm": "早期/中年/晚期的节奏演变：每个阶段ta对机会的处理方式、能量状态、典型挑战会怎样变化。2-3段，用'往往'、'容易'等表述。",

  "year_{target_year}_tendency": "流年与命局的互动。这一年ta的天然倾向会被如何激活或压制？外部环境会带来什么类型的机会或压力？什么节奏最适合这一年？不做好坏判断，只说'怎么顺势而为'。",

  "investment_hint": "基于ta的决策倾向和当年能量，给1-2句具体建议。要落地，比如'今年适合做认知型投入，把资源放在真正理解的领域，而非追热点'。",

  "subtle_suggestion": {{
    "item": "一件小物（颜色/材质/形态），比如'一枚温润的黄玉印章'",
    "why": "用日常语言解释它如何平衡ta的能量倾向，比如'土弱的人容易在高压下失去重心，一点厚实的质感能帮ta找回落地感'"
  }},

  "final_thought": "2-3句收尾。扣回核心倾向、当年重点、一个可执行的小建议。像朋友给的叮嘱，不做命理总结。"
}}
"""

# def build_personality_prompt(bazi_data):
#     return f"""
#         你是一位资深的八字命理师。你的任务是根据以下命盘数据，描绘这个人的**性格**。

#         你不是在写命理报告，而是在向一位熟悉的朋友介绍“这个人到底是谁”。

#         ━━━━━━━━━━━━━━━━━━━━━━
#         输入数据
#         ━━━━━━━━━━━━━━━━━━━━━━
#         八字：{bazi_data["pillar_string"]}
#         日主：{bazi_data["day_master_local"]}
#         五行力量：{json.dumps(bazi_data["five_elements_strength"], ensure_ascii=False)}
#         十神：
#         - 年柱：{bazi_data["ten_gods"]["year"]}
#         - 月柱：{bazi_data["ten_gods"]["month"]}
#         - 日柱：{bazi_data["ten_gods"]["day"]}
#         - 时柱：{bazi_data["ten_gods"]["hour"]}

#         ━━━━━━━━━━━━━━━━━━━━━━
#         核心规则
#         ━━━━━━━━━━━━━━━━━━━━━━

#         1. 五行是底色，十神是具体的“人设”
#         - 五行决定能量状态（水主智/流动，木主方向/行动，土主承载/稳定，火主热情/外部压力，金主决断/边界）
#         - 十神决定具体行为（财旺的人务实、在意得失、善于社交；官杀旺的人有责任感、直接、不怯场；印旺的人沉稳、爱学习；食伤旺的人表达欲强、口才好）

#         2. 不要刻板联想
#         - 水旺 ≠ 内向、话少。水旺可能是健谈的（水主沟通）、善于表达的（水主智）、社交活跃的（水主交际）。
#         - 火弱 ≠ 行动力弱。火是外部推力，不是内在驱动力。
#         - 所有推断必须基于“五行 + 十神”的组合，而不是单一元素。

#         3. 必须写出具体行为
#         - 不要只写“她是个外向的人”
#         - 要写“她会在聚餐时主动张罗话题，但聊到深入话题时会停下来听别人怎么说”

#         4. 语气要求
#         - 像在介绍一个真实存在的人
#         - 用日常语言，不要堆砌命理术语
#         - 可以轻微比喻，但不要过度诗化
#         - 避免负面定性（不说“缺乏”“不足”），说“她习惯…”“她倾向于…”

#         ━━━━━━━━━━━━━━━━━━━━━━
#         输出格式（仅 JSON）
#         ━━━━━━━━━━━━━━━━━━━━━━

#         {{
#         "first_impression": "别人第一次见到她时，会注意到什么？她给人的整体感觉是怎样的？用1-2句话。",
        
#         "talk_style": "她怎么说话？话多话少？节奏快慢？喜欢主导话题还是配合？在什么场合话多、什么场合话少？必须有具体场景。",
        
#         "inner_world": "她心里在想什么？情绪来得快还是慢？压力下会怎样？有什么别人不太知道的一面？",
        
#         "social_style": "她怎么和人相处？喜欢什么样的朋友？在群体中是什么角色？怎么对待亲密的人？",
        
#         "energy_pattern": "她是那种需要独处充电的人，还是从人群中获得能量的人？做事是冲劲型还是稳扎稳打型？",
        
#         "one_thing_people_misunderstand": "别人最容易误会她什么？（比如：以为她___，但其实她___）",
        
#         "final_line": "用一句话总结她性格里最核心的那个东西，像朋友之间的一句评价。"
#         }}
#     """


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
        temperature = 0,
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
    req.Temperature = 0
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
    client = OpenAI(
        api_key=QIANWEN_API_KEY,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    prompt = build_bazi_prompt(bazi_data, target_year=target_year, lang=lang)
    # prompt = build_personality_prompt(bazi_data)  # For testing, focus on personality output first

    completion = client.chat.completions.create(
        model=QIANWEN_LLM_MODEL,
        messages = [
            {"role": "system", "content": "You are a professional Chinese fortune-teller and life coach"},
            {"role": "user", "content": prompt}
        ],
        temperature=0,
        max_tokens=2000
    )

    if not completion.choices or not completion.choices[0].message:
        raise RuntimeError("No response from DeepSeek")

    output_text = completion.choices[0].message.content.strip()
    try:
        return safe_parse_json(output_text)
    except json.JSONDecodeError:
        return {"error": "Qianwen LLM output not valid JSON", "raw": output_text}

# -----------------------------
# Different language pillar localization
# -----------------------------
def enrich_with_localized_pillars(bazi_basic, lang="en"):
    """Enhanced version that handles both 3 and 4 pillar structures"""
    pillars = bazi_basic.get("pillars", {})
    
    # Check if this is a 3-pillar chart
    if len(pillars) == 3 and "hour" not in pillars:
        # For 3-pillar charts, create localized versions without hour
        localized_pillars = {}
        for key, pillar in pillars.items():
            if pillar.get("gan") and pillar.get("zhi"):
                gan_map = GAN_MAP.get(lang, GAN_MAP["en"])
                zhi_map = ZHI_MAP.get(lang, ZHI_MAP["en"])
                try:
                    gan_local = gan_map[GAN_MAP["en"].index(pillar["gan"])]
                    zhi_local = zhi_map[ZHI_MAP["en"].index(pillar["zhi"])]
                    localized_pillars[key] = {
                        **pillar,
                        "gan_local": gan_local,
                        "zhi_local": zhi_local,
                        "label": gan_local + zhi_local
                    }
                except (ValueError, IndexError):
                    localized_pillars[key] = pillar
            else:
                localized_pillars[key] = pillar
        
        bazi_basic["pillars"] = localized_pillars
        
        # Create pillar string (3 pillars only)
        pillar_string = " ".join([
            localized_pillars.get(key, {}).get("label", "")
            for key in ["year", "month", "day"]
            if key in localized_pillars
        ])
        bazi_basic["pillar_string"] = pillar_string
        
    else:
        # Original 4-pillar logic
        localized_pillars, pillar_string = localize_pillars(pillars, lang=lang)
        bazi_basic["pillars"] = localized_pillars
        bazi_basic["pillar_string"] = pillar_string

    # Localize day master
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
    bazi_data should already have pillars localized if needed.
    llm: "openai", "hunyuan", "qianwen"
    lang: "en" or "cn"
    """
    print(f"(DEBUG) bazi_data keys: {bazi_data.keys()}")
    print(f"(DEBUG) pillars_count: {bazi_data.get('pillars_count', 'N/A')}")
    
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
# Helper function to prepare bazi data for LLM
# -----------------------------
def prepare_bazi_for_llm(bazi_result, lang="en"):
    """
    Prepare BaZi data for LLM consumption.
    Handles both 3-pillar and 4-pillar results.
    """
    # Make a copy to avoid modifying original
    bazi_for_llm = bazi_result.copy()
    
    # Ensure pillars are localized
    enrich_with_localized_pillars(bazi_for_llm, lang=lang)
    
    # Add metadata
    bazi_for_llm["lang"] = lang
    
    return bazi_for_llm

# -----------------------------
# Test runs
# -----------------------------
# -----------------------------
# Complete test with actual LLM calls
# -----------------------------
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    # Load environment variables
    load_dotenv()
    
    print("\n" + "="*70)
    print("BAZI LLM TEST SUITE")
    print("="*70)
    
    # Test data 1: 4-Pillar Chart
    print("\n📊 TEST 1: 4-Pillar Chart (Time Known)")
    print("-" * 50)
    
    test_bazi_4 = {
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
        },
        "pillars_count": 4
    }
    
    print("Input Data:")
    print(f"  Pillars: 年柱:丙午 月柱:戊戌 日柱:辛丑 时柱:辛卯")
    print(f"  Day Master: 辛 (Metal)")
    print(f"  Elements: {test_bazi_4['five_elements_strength']}")
    
    # Test data 2: 3-Pillar Chart
    print("\n📊 TEST 2: 3-Pillar Chart (Time Unknown)")
    print("-" * 50)
    
    test_bazi_3 = {
        "pillars": {
            "year": {"gan": "Bing", "zhi": "Wu"},
            "month": {"gan": "Wu", "zhi": "Xu"},
            "day": {"gan": "Xin", "zhi": "Chou"},
        },
        "day_master": "Xin",
        "five_elements_strength": {
            "Wood": 0.0,
            "Fire": 3.3,
            "Earth": 1.0,
            "Metal": 1.4,
            "Water": 0.3
        },
        "pillars_count": 3,
        "disclaimer": "出生时间不详，时柱未推算"
    }
    
    print("Input Data:")
    print(f"  Pillars: 年柱:庚午 月柱:辛巳 日柱:庚辰 [时柱:未知]")
    print(f"  Day Master: 庚 (Metal)")
    print(f"  Elements: {test_bazi_3['five_elements_strength']}")
    print(f"  Note: {test_bazi_3['disclaimer']}")
    
    # Test LLM with 3-Pillar Chart
    print("\n🤖 TEST 3: LLM Generation (3-Pillar Chart)")
    print("-" * 50)
    
    # Check if API keys are set
    has_api_key = False
    llm_to_test = None
    
    if os.getenv("QIANWEN_API_KEY"):
        has_api_key = True
        llm_to_test = "qianwen"
        print("✅ Qianwen API key found")
    elif os.getenv("OPENAI_API_KEY"):
        has_api_key = True
        llm_to_test = "openai"
        print("✅ OpenAI API key found")
    elif os.getenv("TENCENT_SECRET_ID") and os.getenv("TENCENT_SECRET_KEY"):
        has_api_key = True
        llm_to_test = "hunyuan"
        print("✅ Hunyuan API key found")
    else:
        print("⚠️  No API keys found. Set one of:")
        print("   - QIANWEN_API_KEY")
        print("   - OPENAI_API_KEY")
        print("   - TENCENT_SECRET_ID + TENCENT_SECRET_KEY")
    
    if has_api_key:
        try:
            print(f"\n📡 Calling {llm_to_test}...")
            print("   (This may take 10-30 seconds)")
            
            # Prepare data for LLM
            prepared_data = prepare_bazi_for_llm(test_bazi_3, lang="cn")
            
            # Generate narrative
            result = generate_bazi_narrative_safe(
                prepared_data, 
                target_year="2026", 
                llm=llm_to_test, 
                lang="cn"
            )
            
            print("\n✅ LLM Response Received!")
            print("\n" + "="*70)
            print("LLM OUTPUT")
            print("="*70)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            
        except Exception as e:
            print(f"\n❌ Error calling LLM: {e}")
            import traceback
            traceback.print_exc()
    
    # Optional: Test 4-Pillar Chart
    print("\n🤖 TEST 4: LLM Generation (4-Pillar Chart)")
    print("-" * 50)
    print("To test 4-pillar chart, modify the code above to use test_bazi_4")
    
    print("\n" + "="*70)
    print("TEST COMPLETE")
    print("="*70)