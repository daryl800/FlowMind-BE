import os
import json
import concurrent.futures
from openai import OpenAI
from typing import Optional, Dict, Any

from app.config.settings import QIANWEN_LLM, HUNYUAN_LLM, OPENAI_LLM
from app.config.settings import OPENAI_API_KEY_ENV, QIANWEN_API_KEY_ENV, HUNYUAN_API_KEY_ENV
from app.config.settings import QIANWEN_BASE_URL, HUNYUAN_BASE_URL
from app.config.settings import QIANWEN_LLM_MODEL, HUNYUAN_LLM_MODEL, OPENAI_LLM_MODEL

from app.bazi.engine import GAN_MAP, ZHI_MAP, localize_pillars

FALLBACK_LLM = OPENAI_LLM
LLM_TIMEOUT = 800  # seconds

# -----------------------------
# Client configuration
# -----------------------------

_clients: Dict[str, Optional[OpenAI]] = {
    QIANWEN_LLM: None,
    HUNYUAN_LLM: None,
    OPENAI_LLM: None,
}

# Provider configurations: (api_key_env_var, base_url)
_PROVIDER_CONFIGS = {
    OPENAI_LLM: (OPENAI_API_KEY_ENV, None),  # None = use default OpenAI base URL
    QIANWEN_LLM: (QIANWEN_API_KEY_ENV, QIANWEN_BASE_URL),
    HUNYUAN_LLM: (HUNYUAN_API_KEY_ENV, HUNYUAN_BASE_URL),
}

# Model names for each provider
_LLM_MODELS = {
    OPENAI_LLM: OPENAI_LLM_MODEL,
    QIANWEN_LLM: QIANWEN_LLM_MODEL,
    HUNYUAN_LLM: HUNYUAN_LLM_MODEL,
}

def get_client(llm_provider: str = OPENAI_LLM) -> OpenAI:
    """
    Generic client getter that lazy-initializes and returns the client for any provider.
    
    Args:
        provider: Which provider to get client for (OPENAI_LLM, QIANWEN_LLM, HUNYUAN_LLM)
    
    Returns:
        OpenAI client instance configured for the specified provider
    """
    if llm_provider not in _clients:
        raise ValueError(f"Unsupported provider: {llm_provider}. Choose from {list(_clients.keys())}")
    
    if _clients[llm_provider] is None:
        try:
            api_key = os.environ.get(_PROVIDER_CONFIGS[llm_provider][0])
            if not api_key:
                raise ValueError(f"Environment variable {_PROVIDER_CONFIGS[llm_provider][0]} not set")
            
            base_url = _PROVIDER_CONFIGS[llm_provider][1]
            
            # Create client with appropriate configuration
            if base_url:
                _clients[llm_provider] = OpenAI(api_key=api_key, base_url=base_url)
            else:
                _clients[llm_provider] = OpenAI(api_key=api_key)
                
            print(f"Initialized {llm_provider} client successfully")
            
        except Exception as e:
            print(f"初始化{llm_provider}客户端失败: {e}")
            raise
    
    return _clients[llm_provider]

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

def build_bazi_prompt(bazi_data, target_year=2026, lang="zh", personality_profile=None):
    pillars_count = len(bazi_data.get("pillars", {}))
    has_hour_pillar = "hour" in bazi_data.get("pillars", {})

    prompt_data = {
        "pillars_count": pillars_count,
        "pillars": bazi_data["pillars"],
        "day_master": bazi_data["day_master"],
        "five_elements_strength": bazi_data["five_elements_strength"]
    }

    # if pillars_count == 3 or not has_hour_pillar:
    #     prompt_data["disclaimer"] = "出生时间不详，时柱未推算。分析基于年、月、日三柱。"

    # personality_section = ""
    # if personality_profile:
    #     personality_section = f"""
    #     ━━━━━━━━━━━━━━━━━━━━━━
    #     后天人格画像（来自问卷分析）
    #     ━━━━━━━━━━━━━━━━━━━━━━
    #     人格类型：{personality_profile.get('type', '')}
    #     能量维度：{json.dumps(personality_profile.get('dimensions', {}), ensure_ascii=False)}
    #     人格叙述：{personality_profile.get('summary', '')}

    #     ⚠️ 请在分析中对比先天命盘与后天人格：
    #     - 若两者一致，说明此人活在天赋之中
    #     - 若两者有差异，差异本身即是最重要的洞察
    #     """

    # prompt =  f"""
    #     你是一位专业的八字命理师，擅长子平法。
    #     你的任务是根据给定的命盘数据，写一份面向真实人物的分析报告。

    #     {personality_section} 

    #     你不是在描述"这个人是什么性格"，而是在描述"这个人天生对什么有亲和力、什么样的环境让ta自然发挥、什么样的情况让ta消耗过度"。

    #     人的性格受成长环境、文化、经历影响极大，命盘无法精确预测性格。
    #     但命盘可以揭示：天然倾向、能量亲和力、生命节奏模式。

    #     ━━━━━━━━━━━━━━━━━━━━━━
    #     输入数据（已计算完成，直接使用）
    #     ━━━━━━━━━━━━━━━━━━━━━━
    #     {json.dumps(prompt_data, ensure_ascii=False, indent=2)}

    #     目标年份：{target_year}
    #     语言：{lang}

    #     {"⚠️ 注意：出生时间不详，无时柱。分析基于年、月、日三柱。" if pillars_count == 3 else ""}

    #     ━━━━━━━━━━━━━━━━━━━━━━
    #     第一步：判断日主身强 / 身弱（必须先做，所有解读基于此）
    #     ━━━━━━━━━━━━━━━━━━━━━━

    #     日主 = {prompt_data["day_master"]}

    #     判断逻辑：
    #     - 生日主的五行（印星、比劫）合计数值 vs 克泄日主的五行合计数值
    #     - 身强：日主得助多，能驾驭旺神
    #     - 身弱：日主受困，被旺神带着走

    #     【铁律】旺神对日主的影响方向取决于身强/身弱：

    #     日主五行    旺神      身强表现              身弱表现
    #     ─────────────────────────────────────────────────
    #     土          水旺      深思后务实落地        思绪泛滥、难以收束、话多停不下来
    #     土          木旺      有方向感、主动进取    被外界拉着走、难以坚守立场
    #     金          火旺      压力下展现精准执行    焦虑耗散、高压下快速消耗
    #     木          金旺      有原则有边界          感受到压迫、容易退缩
    #     火          水旺      情绪有深度、直觉准    情绪不稳、容易被外界冷却热情
    #     水          土旺      稳中有深度            被压制、流动性受阻

    #     ━━━━━━━━━━━━━━━━━━━━━━
    #     核心规则
    #     ━━━━━━━━━━━━━━━━━━━━━━

    #     1. 日主定基调（铁律）
    #     每一段描述的第一句必须从日主五行的本质出发：
    #     - 甲乙木：生长、方向感、主动开拓
    #     - 丙丁火：表达、连接、感染力
    #     - 戊己土：包容、承载、务实扎根
    #     - 庚辛金：精准、原则、有边界
    #     - 壬癸水：流动、适应、思虑深

    #     禁止：以五行分布最强项替代日主定基调。

    #     2. 五行含义（固定）
    #     - 火 = 外部压力、紧迫感、环境推力（不是决断力或冲动）
    #     - 水 = 思虑、内在推演、信息沉淀
    #     - 金 = 收尾力、切割、做出结论
    #     - 土 = 稳健、风险控制、依赖经验
    #     - 木 = 方向感、行动力（不参与决策风格分析）

    #     3. 决策风格推断（固定）
    #     - 水强 + 金强 → 深思后有清晰结论
    #     - 水强 + 金弱 → 反复推演，收尾慢
    #     - 水弱 + 金强 → 判断快，但可能信息不足
    #     - 土强 → 偏好已知路径，稳定优先
    #     - 火强 + 水弱 → 压力下容易仓促反应

    #     4. 用倾向代替定性（铁律）
    #     禁止说："ta是个内向的人"、"ta很谨慎"、"ta性格X"
    #     必须说："ta天生对X类型的事物有亲和力"、"ta在X环境下容易找到节奏"、"ta的生命轨迹中X模式往往比同龄人更明显"

    #     示例转换：
    #     ❌ "她安静内敛，习惯最后发言"
    #     ✅ "她天生对需要耐心积累的场景有亲和力——不是不愿开口，而是在信息沉淀之后说出的话更有分量"

    #     ❌ "他执行力强"
    #     ✅ "他的生命轨迹中，外部压力往往是启动高效状态的触发点——截止日期、突发要求，反而让他进入最佳节奏"

    #     ━━━━━━━━━━━━━━━━━━━━━━
    #     语气要求
    #     ━━━━━━━━━━━━━━━━━━━━━━

    #     用自然的中文，像在向朋友介绍另一个人的"天然倾向"。

    #     避免：
    #     - 命理术语堆砌（劫财、七杀少用）
    #     - 空泛形容词（"谨慎的人"、"聪明的人"）
    #     - 负面定性（改用"在X情况下容易消耗过度"）
    #     - 直接断言性格（改用倾向、亲和力、生命模式）

    #     必须做到：
    #     - 每个倾向描述都有具体的生活场景或行为举例
    #     - 把命理结论翻译成"生命中容易出现的模式"

    #     ━━━━━━━━━━━━━━━━━━━━━━
    #     输出格式
    #     ━━━━━━━━━━━━━━━━━━━━━━

    #     只返回 JSON，无 markdown，无额外解释。

    #     {{
    #         "tendency_portrait": "3-5段。不描述性格，而是描述：ta天生对什么有亲和力、什么样的环境让ta自然发挥、什么样的互动模式在ta生命中反复出现。必须包含至少2个具体生活场景。开头必须从日主五行本质出发。",

    #         "decision_tendency": "描述决策节奏与信息处理方式：ta在做重要决定时的天然节奏、对风险的本能态度、压力下的典型反应模式。必须包含至少1个具体场景。用'倾向于'、'容易'、'往往'等表述，不做性格定性。",

    #         "environment_affinities": {{
    #             "energizing": ["2-3种让ta自然发挥的环境或场景，说明为什么这类环境与ta的天然倾向吻合"],
    #             "draining": ["2-3种容易让ta过度消耗的环境，用'需要长期…的环境'表述，说明消耗机制"]
    #         }},

    #         "life_pattern_summary": "1-2句话。用比喻描述这个命盘的整体能量格局和生命节奏。不罗列数值，不用命理术语。例如：'像一条有方向感的河，水量充沛但需要找到合适的河床才能稳定流淌。'",

    #         "life_rhythm": "早期/中年/晚期的节奏演变：每个阶段ta对机会的处理方式、能量状态、典型挑战会怎样变化。2-3段，用'往往'、'容易'等表述。",

    #         "year_{target_year}_tendency": "流年与命局的互动。这一年ta的天然倾向会被如何激活或压制？外部环境会带来什么类型的机会或压力？什么节奏最适合这一年？不做好坏判断，只说'怎么顺势而为'。",

    #         "investment_hint": "基于ta的决策倾向和当年能量，给1-2句具体建议。要落地，比如'今年适合做认知型投入，把资源放在真正理解的领域，而非追热点'。",

    #         "subtle_suggestion": {{
    #             "item": "一件小物（颜色/材质/形态），比如'一枚温润的黄玉印章'",
    #             "why": "用日常语言解释它如何平衡ta的能量倾向，比如'土弱的人容易在高压下失去重心，一点厚实的质感能帮ta找回落地感'"
    #         }},

    #         "bazi_vs_personality": {{
    #             "alignment": "哪些维度先天后天一致？说明此人活在天赋中",
    #             "tension": "哪些维度存在明显差异？这个张力如何解释ta现在的状态",
    #             "insight": "综合两者，给出一个普通命盘分析或问卷都无法单独给出的洞察"
    #         }}

    #         "final_thought": "2-3句收尾。扣回核心倾向、当年重点、一个可执行的小建议。像朋友给的叮嘱，不做命理总结。"
    #     }}
        
    #     """

    # Pre-compute all conditional blocks before the f-string
    no_hour_pillar_note = "⚠️ 无时柱，分析基于年月日三柱。" if pillars_count == 3 else ""

    if personality_profile:
        personality_section = f"""━━━━━━━━━━━━━━━━━━━━━━
    后天人格数据（问卷）
    ━━━━━━━━━━━━━━━━━━━━━━
    {json.dumps(personality_profile, ensure_ascii=False, indent=2)}"""
    else:
        personality_section = ""

    if personality_profile:
        step_four = """第四步：对比先天与后天
    命盘反映天然倾向，问卷反映后天养成的模式。
    两者一致的地方，说明ta活在自己的天赋里。
    两者有张力的地方，往往是ta当下最真实的内耗来源。
    这个对比本身就是最有价值的洞察。"""
    else:
        step_four = ""

    year_key = f"year_{target_year}"

    if personality_profile:
        bazi_vs_self_field = f'    "bazi_vs_self": "先天命盘与后天问卷的对比洞察。一致处说明天赋，张力处说明内耗来源。给出一个两者单独都无法给出的洞察。",'
    else:
        bazi_vs_self_field = ""

    # Now the f-string is clean
    prompt = f"""
        你是一位专业八字命理师，正在为一位真实的人做当面分析。
        用"你"来称呼对方，语气像在对话，不像在写报告。

        ━━━━━━━━━━━━━━━━━━━━━━
        命盘数据
        ━━━━━━━━━━━━━━━━━━━━━━
        {json.dumps(prompt_data, ensure_ascii=False, indent=2)}

        目标年份：{target_year}
        语言：{lang}
        {no_hour_pillar_note}

        {personality_section}

        ━━━━━━━━━━━━━━━━━━━━━━
        分析框架（内部使用）
        ━━━━━━━━━━━━━━━━━━━━━━

        先判断身强/身弱，再找命局核心张力，所有解读从这两个基础出发。
        不要平均描述每根柱子，只说最重要的。

        ━━━━━━━━━━━━━━━━━━━━━━
        输出格式（严格遵守）
        ━━━━━━━━━━━━━━━━━━━━━━

        用 Markdown 输出，结构如下：

        ---

        ## 一、八字排盘

        **乾造 / 坤造：**
        - 年柱：[天干地支]（[纳音]）
        - 月柱：[天干地支]（[纳音]）
        - 日柱：[天干地支]（[纳音]）
        - 时柱：[天干地支]（[纳音]）{" / 时辰不详，以下分析基于三柱" if pillars_count == 3 else ""}

        **五行能量：**
        - 日主（你）：[天干]（1句话说清这个五行的本质气质）
        - 月令：[地支]，[格局名]
        - 环境：1句话描述整体五行格局的氛围

        ---

        ## 二、命理特征分析

        ### 1. [最核心的性格特质]：[4-6字小标题]

        2-3句说清核心，可引用一句古典命理口诀（用**加粗**）。

        - **[十神或格局名]：** 1句话说它对这个人意味着什么
        - **[另一个关键配置]：** 1句话说它对这个人意味着什么

        ### 2. [事业/财运/某个最重要的主题]：[4-6字小标题]

        1句话点出这个命盘在这个主题上的核心矛盾或特征（可用**加粗**强调关键词）。

        - **困境：** 1句
        - **解药：** 1句，具体说明怎么破局
        - **[其他关键点]：** 1句

        ### 3. [感情/家庭/人际——如命盘有明显信号则写，否则跳过]

        - [关键配置]：1-2句
        - [另一个配置]：1-2句

        ---

        ## 三、大运简析（当前阶段）

        1-2句交代目前处于哪个大运，年龄段。

        - **[大运名]：** 1-2句说这段时期的核心能量与机遇
        - **{target_year}年：** 1-2句说流年与命局的互动，什么被激活，什么受压

        ---

        ## 四、给你的建议

        1. **[第一条建议标题]：** 1-2句，具体可操作
        2. **[第二条建议标题]：** 1-2句，具体可操作
        3. **[第三条建议标题]：** 1-2句，具体可操作

        ---

        最后用1句话说明分析的局限（如无时辰），然后用**一个真实的问题**结尾，引导对方说出他/她目前最关心的事。

        ---

        写作要求：
        - 每个要点说完就停，不展开，不重复
        - 古典口诀或术语用**加粗**，但每节最多用一次
        - 语气是"我在跟你说话"，不是"本报告显示"
        - 全文没有"综合来看"、"总体而言"、"值得注意的是"
        """
    
    # Now you can debug AFTER prompt is built
    print(f"[DEBUG] personality_section empty: {personality_section == ''}")
    print(f"[DEBUG] prompt contains 后天人格: {'后天人格' in prompt}")

    return prompt

def _generate_llm(bazi_data, target_year="2026", lang="en", llm_provider=OPENAI_LLM, personality_profile=None):
    """
    Generate fortune-telling analysis using the specified LLM provider.
    
    Args:
        bazi_data: The Bazi data to analyze
        target_year: The year to focus on (default 2026)
        lang: Language for output ("en" or "zh")
        provider: Which LLM to use ("openai", "qianwen", "hunyuan")
    
    Returns:
        Parsed JSON response or error dict
    """
    if llm_provider not in _LLM_MODELS:
        raise ValueError(f"Unsupported provider: {llm_provider}. Choose from {list(_LLM_MODELS.keys())}")
    
    # Build prompt and get client
    prompt = build_bazi_prompt(bazi_data, target_year=target_year, lang=lang, personality_profile=personality_profile)
    client = get_client(llm_provider)
    
    # Make API call
    completion = client.chat.completions.create(
        model=_LLM_MODELS[llm_provider],
        messages=[
            {"role": "system", "content": "You are a professional Chinese fortune-teller and life coach"},
            {"role": "user", "content": prompt}
        ],
        temperature=0,
        max_tokens=2000
    )
    
    # Validate response
    if not completion.choices or not completion.choices[0].message:
        raise RuntimeError(f"No response from {llm_provider.upper()}")
    
    # Parse and return
    output_text = completion.choices[0].message.content.strip()
    try:
        return safe_parse_json(output_text)
    except json.JSONDecodeError:
        return {"error": f"{llm_provider.upper()} LLM output not valid JSON", "raw": output_text}
    

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
def generate_bazi_narrative(bazi_data, target_year="2026", llm_provider=OPENAI_LLM, lang="en", personality_profile=None):
    """
    Generate BaZi narrative JSON using the specified LLM.
    bazi_data should already have pillars localized if needed.
    llm: "openai", "hunyuan", "qianwen"
    lang: "en" or "cn"
    """
    print(f"(DEBUG) bazi_data keys: {bazi_data.keys()}")
    print(f"(DEBUG) pillars_count: {bazi_data.get('pillars_count', 'N/A')}")
    
    if llm_provider not in _LLM_MODELS:
        raise ValueError(f"Unsupported provider: {llm_provider}. Choose from {list(_LLM_MODELS.keys())}")
    
    return _generate_llm(bazi_data, target_year=target_year, lang=lang, llm_provider=llm_provider, personality_profile=personality_profile)

def generate_bazi_narrative_safe(bazi_data, target_year="2026", llm_provider=OPENAI_LLM, lang="en", personality_profile=None):
    """
    Wrapper with timeout + fallback.
    Does NOT change JSON schema.
    """
    print(f"[DEBUG] narrative_safe received personality_profile type: {type(personality_profile)}")
    print(f"[DEBUG] narrative_safe received personality_profile: {personality_profile}")

    def _run():
        return generate_bazi_narrative(bazi_data, target_year=target_year, llm_provider=llm_provider, lang=lang, personality_profile=personality_profile)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_run)
        try:
            llm_reflection = future.result(timeout=LLM_TIMEOUT)
            # print(f"=== LLM SUCCESS： 【{llm_provider}】 ===\nOUTPUT:\n{llm_reflection}\n{'-'*40}")
            return llm_reflection
        except Exception as e:
            print(f"[LLM ERROR] {llm_provider} failed: {e}")
            if llm_provider != FALLBACK_LLM:
                print(f"【LLM FALLBACK】Switching from 【{llm_provider}】 to 【{FALLBACK_LLM}】")
                return generate_bazi_narrative_safe(
                    bazi_data,
                    target_year=target_year,
                    llm_provider=FALLBACK_LLM,
                    lang=lang,
                    personality_profile=personality_profile  # ← don't lose it on fallback
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
# Test runs - Complete test with actual LLM calls
# -----------------------------
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    print("\n" + "="*70)
    print("BAZI LLM TEST SUITE")
    print("="*70)

    # ── Mock personality profile (simulates OutputA result) ──
    test_personality_profile = {
        "type": "探索者",
        "dimensions": {
            "creativity": 8,
            "structure": 3,
            "empathy": 7,
            "ambition": 6,
            "resilience": 5
        },
        "summary": "你天生对新事物有强烈的亲和力，容易在开放、多元的环境中找到节奏。"
                   "你的决策往往从感受出发，先有直觉，再找逻辑支撑。"
                   "在高度结构化或重复性的环境中，你容易感到能量流失。"
    }

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

    llm_to_test = QIANWEN_LLM

    # ── TEST 3: WITHOUT personality_profile (baseline) ──
    print("\n🤖 TEST 3: LLM Generation — Bazi only (no personality profile)")
    print("-" * 50)
    try:
        print(f"\n📡 Calling {llm_to_test}...")
        prepared_data = prepare_bazi_for_llm(test_bazi_3, lang="cn")
        result = generate_bazi_narrative_safe(
            prepared_data,
            target_year="2026",
            llm_provider=llm_to_test,
            lang="cn",
            personality_profile=None      # ← no profile, original behaviour
        )
        print("\n✅ LLM Response Received!")
        print("="*70)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

    # ── TEST 4: WITH personality_profile (combined) ──
    print("\n🤖 TEST 4: LLM Generation — Combined (Bazi + personality profile)")
    print("-" * 50)
    print("Personality Profile:")
    print(json.dumps(test_personality_profile, ensure_ascii=False, indent=2))
    try:
        print(f"\n📡 Calling {llm_to_test}...")
        prepared_data = prepare_bazi_for_llm(test_bazi_3, lang="cn")
        result = generate_bazi_narrative_safe(
            prepared_data,
            target_year="2026",
            llm_provider=llm_to_test,
            lang="cn",
            personality_profile=test_personality_profile   # ← combined mode
        )
        print("\n✅ Combined LLM Response Received!")
        print("="*70)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*70)
    print("TEST COMPLETE")
    print("="*70)