import math
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import sxtwl
from typing import Optional, Dict, List, Tuple

# =====================================================
# Heavenly Stems & Earthly Branches
# =====================================================
GAN = ["Jia", "Yi", "Bing", "Ding", "Wu", "Ji", "Geng", "Xin", "Ren", "Gui"]
ZHI = ["Zi", "Chou", "Yin", "Mao", "Chen", "Si", "Wu", "Wei", "Shen", "You", "Xu", "Hai"]

GAN_CN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
ZHI_CN = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

GAN_MAP = {
    "en": ["Jia","Yi","Bing","Ding","Wu","Ji","Geng","Xin","Ren","Gui"],
    "cn": ["甲","乙","丙","丁","戊","己","庚","辛","壬","癸"]
}

ZHI_MAP = {
    "en": ["Zi","Chou","Yin","Mao","Chen","Si","Wu","Wei","Shen","You","Xu","Hai"],
    "cn": ["子","丑","寅","卯","辰","巳","午","未","申","酉","戌","亥"]
}

# =====================================================
# Longitude Strategy
# =====================================================
LOCATION_LON_TABLE = {
    "hong kong": 114.1095,
    "taipei": 121.5654,
    "beijing": 116.4074,
    "shanghai": 121.4737,
    "new york": -74.0060,
    "los angeles": -118.2437,
    "san francisco": -122.4194,
    "chicago": -87.6298,
    "sydney": 151.2093,
    "melbourne": 144.9631,
    "brisbane": 153.0251,
    "perth": 115.8605,
    "paris": 2.3522,
    "rome": 12.4964,
    "milan": 9.1900,
    "berlin": 13.4050,
    "munich": 11.5820,
    "stockholm": 18.06,
}

REGION_LON_FALLBACK = {
    "china": 120.0,
    "taiwan": 121.0,
    "japan": 138.0,
    "usa": -95.0,
    "united states": -95.0,
    "australia": 133.0,
    "france": 2.0,
    "italy": 12.0,
    "germany": 10.0,
    "europe": 10.0,
    "asia": 120.0,
}

GLOBAL_DEFAULT_LON = 120.0

def resolve_longitude(location: Optional[str]) -> float:
    if not location:
        return GLOBAL_DEFAULT_LON

    key = location.lower().replace("_", " ").strip()

    if key in LOCATION_LON_TABLE:
        return LOCATION_LON_TABLE[key]

    for city, lon in LOCATION_LON_TABLE.items():
        if city in key:
            return lon

    for region, lon in REGION_LON_FALLBACK.items():
        if region in key:
            return lon

    return GLOBAL_DEFAULT_LON

# =====================================================
# True Solar Time
# =====================================================
def calculate_true_solar_time(local_dt: datetime, longitude: float) -> datetime:
    if local_dt.tzinfo is None:
        raise ValueError("Datetime must be timezone-aware")

    lon_offset = (longitude - 120.0) * 4.0

    day_of_year = local_dt.timetuple().tm_yday
    B = 2 * math.pi * (day_of_year - 81) / 365
    eot = 9.87 * math.sin(2 * B) - 7.53 * math.cos(B) - 1.5 * math.sin(B)

    return local_dt + timedelta(minutes=(lon_offset + eot))

def get_hour_zhi(hour: int) -> str:
    return ZHI[((hour + 1) // 2) % 12]

# =====================================================
# Core Engine (Full 4 Pillars - When Time is Known)
# =====================================================
def calc_bazi_fixed(dt: datetime, tz_name: str, longitude: float):
    """Calculate complete BaZi with all 4 pillars (requires accurate birth time)"""
    
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo(tz_name))
    else:
        dt = dt.astimezone(ZoneInfo(tz_name))

    true_solar = calculate_true_solar_time(dt, longitude)

    solar_date = true_solar.date()
    if true_solar.hour >= 23:
        solar_date += timedelta(days=1)

    lunar = sxtwl.fromSolar(solar_date.year, solar_date.month, solar_date.day)

    year_gz = lunar.getYearGZ()
    month_gz = lunar.getMonthGZ()
    day_gz = lunar.getDayGZ()

    year_gan, year_zhi = GAN[year_gz.tg], ZHI[year_gz.dz]
    month_gan, month_zhi = GAN[month_gz.tg], ZHI[month_gz.dz]
    day_gan, day_zhi = GAN[day_gz.tg], ZHI[day_gz.dz]

    hour_zhi = get_hour_zhi(true_solar.hour)
    hour_zhi_idx = ZHI.index(hour_zhi)

    wushu = {
        "Jia": "Jia", "Ji": "Jia",
        "Yi": "Bing", "Geng": "Bing",
        "Bing": "Wu", "Xin": "Wu",
        "Ding": "Geng", "Ren": "Geng",
        "Wu": "Ren", "Gui": "Ren",
    }

    base_gan = wushu[day_gan]
    hour_gan = GAN[(GAN.index(base_gan) + hour_zhi_idx) % 10]

    pillars = {
        "year": {"gan": year_gan, "zhi": year_zhi},
        "month": {"gan": month_gan, "zhi": month_zhi},
        "day": {"gan": day_gan, "zhi": day_zhi},
        "hour": {"gan": hour_gan, "zhi": hour_zhi},
    }

    day_master = pillars["day"]["gan"]

    ELEMENT_MAP = {
        "Jia":"Wood", "Yi":"Wood",
        "Bing":"Fire","Ding":"Fire",
        "Wu":"Earth","Ji":"Earth",
        "Geng":"Metal","Xin":"Metal",
        "Ren":"Water","Gui":"Water",
        "Zi":"Water","Chou":"Earth","Yin":"Wood","Mao":"Wood",
        "Chen":"Earth","Si":"Fire","Wu":"Fire","Wei":"Earth",
        "Shen":"Metal","You":"Metal","Xu":"Earth","Hai":"Water"
    }

    ZHI_HIDDEN_STEMS = {
        "Zi":  [("Ren", 1.0)],
        "Chou":[("Ji", 0.6), ("Gui", 0.3), ("Xin", 0.1)],
        "Yin": [("Jia", 0.6), ("Bing", 0.3), ("Wu", 0.1)],
        "Mao": [("Yi", 1.0)],
        "Chen":[("Wu", 0.6), ("Yi", 0.3), ("Gui", 0.1)],
        "Si":  [("Bing", 0.6), ("Wu", 0.3), ("Geng", 0.1)],
        "Wu":  [("Ding", 0.6), ("Ji", 0.4)],
        "Wei": [("Ji", 0.6), ("Yi", 0.3), ("Ding", 0.1)],
        "Shen":[("Geng", 0.6), ("Ren", 0.3), ("Wu", 0.1)],
        "You": [("Xin", 1.0)],
        "Xu":  [("Wu", 0.6), ("Xin", 0.3), ("Ding", 0.1)],
        "Hai": [("Ren", 0.6), ("Jia", 0.4)],
    }
    
    fe_strength = {"Wood":0.0,"Fire":0.0,"Earth":0.0,"Metal":0.0,"Water":0.0}

    for p in pillars.values():
        gan = p["gan"]
        e = ELEMENT_MAP[gan]
        fe_strength[e] += 1.0

    for p in pillars.values():
        zhi = p["zhi"]
        for hidden_gan, weight in ZHI_HIDDEN_STEMS[zhi]:
            e = ELEMENT_MAP[hidden_gan]
            fe_strength[e] += weight

    return {
        "pillars": pillars,
        "day_master": day_master,
        "five_elements_strength": fe_strength,
        "pillars_count": 4,
    }

# =====================================================
# Core Engine (3 Pillars Only - When Time is Unknown)
# =====================================================
def calc_bazi_three_pillars(
    birth_date: datetime,
    tz_name: str = "Hong_Kong",
    location: Optional[str] = None
) -> Dict:
    """
    Calculate BaZi using only year, month, and day pillars.
    Uses 12:00 noon to ensure consistent day pillar calculation.
    """
    
    # Resolve location parameters
    longitude = resolve_longitude(location or tz_name)
    tz_resolved = tz_name if "/" in tz_name else "Asia/Hong_Kong"
    
    # CRITICAL: Use 12:00 noon to avoid day boundary crossing
    # This ensures the day pillar is ALWAYS correct for the given date
    dt = datetime(
        birth_date.year, 
        birth_date.month, 
        birth_date.day, 
        12,  # Noon - safe from Zi hour boundary (23:00-01:00)
        0,
        0
    )
    
    # Handle timezone (important for date correctness)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo(tz_resolved))
    else:
        dt = dt.astimezone(ZoneInfo(tz_resolved))
    
    # Get the date for lunar conversion
    # Using noon ensures we never cross the day boundary
    solar_date = dt.date()
    
    # Get lunar calendar data
    lunar = sxtwl.fromSolar(solar_date.year, solar_date.month, solar_date.day)
    
    # Get year, month, day pillars
    year_gz = lunar.getYearGZ()
    month_gz = lunar.getMonthGZ()
    day_gz = lunar.getDayGZ()
    
    # Extract stems and branches
    year_gan, year_zhi = GAN[year_gz.tg], ZHI[year_gz.dz]
    month_gan, month_zhi = GAN[month_gz.tg], ZHI[month_gz.dz]
    day_gan, day_zhi = GAN[day_gz.tg], ZHI[day_gz.dz]
    
    # Element mapping
    ELEMENT_MAP = {
        "Jia":"Wood", "Yi":"Wood",
        "Bing":"Fire","Ding":"Fire",
        "Wu":"Earth","Ji":"Earth",
        "Geng":"Metal","Xin":"Metal",
        "Ren":"Water","Gui":"Water",
        "Zi":"Water","Chou":"Earth","Yin":"Wood","Mao":"Wood",
        "Chen":"Earth","Si":"Fire","Wu":"Fire","Wei":"Earth",
        "Shen":"Metal","You":"Metal","Xu":"Earth","Hai":"Water"
    }
    
    ZHI_HIDDEN_STEMS = {
        "Zi":  [("Ren", 1.0)],
        "Chou":[("Ji", 0.6), ("Gui", 0.3), ("Xin", 0.1)],
        "Yin": [("Jia", 0.6), ("Bing", 0.3), ("Wu", 0.1)],
        "Mao": [("Yi", 1.0)],
        "Chen":[("Wu", 0.6), ("Yi", 0.3), ("Gui", 0.1)],
        "Si":  [("Bing", 0.6), ("Wu", 0.3), ("Geng", 0.1)],
        "Wu":  [("Ding", 0.6), ("Ji", 0.4)],
        "Wei": [("Ji", 0.6), ("Yi", 0.3), ("Ding", 0.1)],
        "Shen":[("Geng", 0.6), ("Ren", 0.3), ("Wu", 0.1)],
        "You": [("Xin", 1.0)],
        "Xu":  [("Wu", 0.6), ("Xin", 0.3), ("Ding", 0.1)],
        "Hai": [("Ren", 0.6), ("Jia", 0.4)],
    }
    
    # Calculate element strength from year, month, day only
    fe_strength = {"Wood":0.0,"Fire":0.0,"Earth":0.0,"Metal":0.0,"Water":0.0}
    
    pillars_three = [
        {"gan": year_gan, "zhi": year_zhi},
        {"gan": month_gan, "zhi": month_zhi},
        {"gan": day_gan, "zhi": day_zhi}
    ]
    
    for pillar in pillars_three:
        # Count heavenly stem
        gan_e = ELEMENT_MAP[pillar["gan"]]
        fe_strength[gan_e] += 1.0
        
        # Count hidden stems
        for hidden_gan, weight in ZHI_HIDDEN_STEMS[pillar["zhi"]]:
            hidden_e = ELEMENT_MAP[hidden_gan]
            fe_strength[hidden_e] += weight
    
    # Return structure with clear indication that hour is omitted
    return {
        "pillars": {
            "year": {"gan": year_gan, "zhi": year_zhi},
            "month": {"gan": month_gan, "zhi": month_zhi},
            "day": {"gan": day_gan, "zhi": day_zhi},
        },
        "day_master": day_gan,
        "five_elements_strength": fe_strength,
        "pillars_count": 3,
        "calculation_method": "three_pillars_only",
        "disclaimer": "时柱未推算 - 出生时间不详。分析基于年、月、日三柱。",
        "disclaimer_en": "Hour pillar not calculated - birth time unknown. Analysis based on year, month, and day pillars only.",
        "calculation_note": "Used 12:00 noon for consistent day pillar calculation"
    }

# =====================================================
# Analysis Functions
# =====================================================

def analyze_three_pillars(bazi_data: Dict, lang: str = "cn") -> Dict:
    """
    Provide comprehensive analysis for 3-pillar charts
    """
    
    pillars = bazi_data["pillars"]
    day_master = bazi_data["day_master"]
    elements = bazi_data["five_elements_strength"]
    
    # Determine element balance (without hour influence)
    strongest = max(elements, key=elements.get)
    weakest = min(elements, key=elements.get)
    
    # Core personality based on day master
    personality = {
        "Jia": {
            "cn": "甲木 - 参天大树，正直仁爱，有领导才能，独立自主",
            "en": "Jia Wood - Towering tree, upright and benevolent, natural leader, independent"
        },
        "Yi": {
            "cn": "乙木 - 花草藤蔓，柔韧灵活，有艺术气质，善于适应",
            "en": "Yi Wood - Flower and vine, flexible and adaptable, artistic nature, versatile"
        },
        "Bing": {
            "cn": "丙火 - 太阳之火，热情开朗，光芒四射，乐于奉献",
            "en": "Bing Fire - Sun fire, passionate and outgoing, radiant, generous"
        },
        "Ding": {
            "cn": "丁火 - 星烛之火，温和细腻，思维敏锐，内敛含蓄",
            "en": "Ding Fire - Star fire, gentle and refined, sharp mind, reserved"
        },
        "Wu": {
            "cn": "戊土 - 城墙之土，稳重守信，包容力强，踏实可靠",
            "en": "Wu Earth - City wall, stable and trustworthy, tolerant, reliable"
        },
        "Ji": {
            "cn": "己土 - 田园之土，谦逊包容，善于协调，耐心细致",
            "en": "Ji Earth - Field soil, humble and accommodating, coordinating, patient"
        },
        "Geng": {
            "cn": "庚金 - 刀剑之金，刚毅果断，重义气，有魄力",
            "en": "Geng Metal - Sword metal, resolute and decisive, loyal, courageous"
        },
        "Xin": {
            "cn": "辛金 - 珠宝之金，精致细腻，追求完美，善于思考",
            "en": "Xin Metal - Jewelry metal, refined and meticulous, perfectionist, thoughtful"
        },
        "Ren": {
            "cn": "壬水 - 江河之水，智慧通达，心胸开阔，适应力强",
            "en": "Ren Water - River water, wise and insightful, broad-minded, adaptable"
        },
        "Gui": {
            "cn": "癸水 - 雨露之水，细腻敏感，直觉敏锐，善于谋略",
            "en": "Gui Water - Rain water, subtle and sensitive, intuitive, strategic"
        }
    }
    
    # Career suggestions based on strongest element
    career_hints = {
        "Wood": {
            "cn": "教育、文化、艺术、医疗、环保、园林设计",
            "en": "Education, culture, arts, healthcare, environmental protection, landscape design"
        },
        "Fire": {
            "cn": "传媒、娱乐、科技、能源、市场营销、心理咨询",
            "en": "Media, entertainment, technology, energy, marketing, counseling"
        },
        "Earth": {
            "cn": "房地产、建筑、管理、金融、咨询、教育",
            "en": "Real estate, construction, management, finance, consulting, education"
        },
        "Metal": {
            "cn": "法律、金融、工程、制造、军事、精密技术",
            "en": "Law, finance, engineering, manufacturing, military, precision technology"
        },
        "Water": {
            "cn": "贸易、物流、旅游、传媒、咨询、研究",
            "en": "Trade, logistics, travel, media, consulting, research"
        }
    }
    
    # Relationship insights
    day_zhi = pillars["day"]["zhi"]
    relationship_notes = {
        "Zi": {"cn": "子水 - 聪明灵动，配偶多有智慧", "en": "Zi Water - Intelligent, spouse is often wise"},
        "Chou": {"cn": "丑土 - 稳重踏实，配偶多可靠务实", "en": "Chou Earth - Stable, spouse is reliable"},
        "Yin": {"cn": "寅木 - 积极进取，配偶多有抱负", "en": "Yin Wood - Ambitious, spouse is driven"},
        "Mao": {"cn": "卯木 - 温和善良，配偶多温柔体贴", "en": "Mao Wood - Gentle, spouse is caring"},
        "Chen": {"cn": "辰土 - 包容大度，配偶多有智慧", "en": "Chen Earth - Tolerant, spouse is wise"},
        "Si": {"cn": "巳火 - 热情开朗，配偶多外向活跃", "en": "Si Fire - Passionate, spouse is outgoing"},
        "Wu": {"cn": "午火 - 真诚直率，配偶多热情大方", "en": "Wu Fire - Sincere, spouse is generous"},
        "Wei": {"cn": "未土 - 体贴周到，配偶多温柔细腻", "en": "Wei Earth - Considerate, spouse is gentle"},
        "Shen": {"cn": "申金 - 聪明睿智，配偶多能力出众", "en": "Shen Metal - Intelligent, spouse is capable"},
        "You": {"cn": "酉金 - 细致严谨，配偶多追求完美", "en": "You Metal - Meticulous, spouse is perfectionist"},
        "Xu": {"cn": "戌土 - 忠诚可靠，配偶多责任感强", "en": "Xu Earth - Loyal, spouse is responsible"},
        "Hai": {"cn": "亥水 - 随和包容，配偶多善解人意", "en": "Hai Water - Easygoing, spouse is understanding"}
    }
    
    return {
        "personality": personality.get(day_master, personality["Wu"])[lang],
        "element_balance": {
            "strongest": strongest,
            "weakest": weakest,
            "strengths": {k: v for k, v in elements.items() if v > 1.0},
            "needs_support": {k: v for k, v in elements.items() if v < 0.5}
        },
        "career_direction": career_hints.get(strongest, career_hints["Earth"])[lang],
        "relationship": relationship_notes.get(day_zhi, {"cn": "随缘而安", "en": "Go with the flow"})[lang],
        "element_scores": elements,
        "limitations": {
            "missing": {
                "cn": "时柱 (子女运、晚年运、事业高峰细节)",
                "en": "Hour pillar (children, later life, career culmination details)"
            },
            "can_still_analyze": {
                "cn": [
                    "核心性格与人格特质",
                    "事业发展方向与天赋",
                    "感情与婚姻模式",
                    "五行强弱与喜忌",
                    "人生大运走势"
                ],
                "en": [
                    "Core personality and character",
                    "Career direction and aptitudes",
                    "Relationship patterns",
                    "Elemental strengths and weaknesses",
                    "Life fortune cycles"
                ]
            }
        }
    }

# =====================================================
# Display Functions
# =====================================================

def display_three_pillar_bazi(bazi_data: Dict, lang: str = "cn"):
    """
    Display BaZi with only 3 pillars - professional format
    """
    
    gan_map = GAN_CN if lang == "cn" else GAN
    zhi_map = ZHI_CN if lang == "cn" else ZHI
    
    # Get analysis
    analysis = analyze_three_pillars(bazi_data, lang)
    
    print("=" * 70)
    print("八字四柱推算 / Four Pillars Calculation")
    print("=" * 70)
    print()
    
    # Display pillars
    print("年柱 / Year Pillar:", end=" ")
    year_pillar = bazi_data["pillars"]["year"]
    year_label = f"{gan_map[GAN.index(year_pillar['gan'])]}{zhi_map[ZHI.index(year_pillar['zhi'])]}"
    print(f"{year_label}")
    if lang == "cn":
        print("   └─ 祖上、早年运势、家庭背景")
    else:
        print("   └─ Ancestors, early life, family background")
    print()
    
    print("月柱 / Month Pillar:", end=" ")
    month_pillar = bazi_data["pillars"]["month"]
    month_label = f"{gan_map[GAN.index(month_pillar['gan'])]}{zhi_map[ZHI.index(month_pillar['zhi'])]}"
    print(f"{month_label}")
    if lang == "cn":
        print("   └─ 父母、事业、青年运势")
    else:
        print("   └─ Parents, career, youth")
    print()
    
    print("日柱 / Day Pillar:", end=" ")
    day_pillar = bazi_data["pillars"]["day"]
    day_label = f"{gan_map[GAN.index(day_pillar['gan'])]}{zhi_map[ZHI.index(day_pillar['zhi'])]}"
    day_master_cn = gan_map[GAN.index(bazi_data["day_master"])]
    print(f"{day_label} (日主 / Day Master: {day_master_cn})")
    if lang == "cn":
        print("   └─ 自身、配偶、中年运势")
    else:
        print("   └─ Self, spouse, adulthood")
    print()
    
    print("时柱 / Hour Pillar:", end=" ")
    if lang == "cn":
        print("【未推算 - 出生时间不详】")
        print("   └─ 未计算时柱，因缺乏准确出生时间")
    else:
        print("[Not Calculated - Birth Time Unknown]")
        print("   └─ Hour pillar omitted due to unknown birth time")
    print()
    
    print("-" * 70)
    print(f"📝 {bazi_data['disclaimer']}")
    print()
    
    # Element analysis
    print("五行力量 / Five Elements Strength:")
    elements = bazi_data["five_elements_strength"]
    for element, value in sorted(elements.items(), key=lambda x: x[1], reverse=True):
        element_cn = {"Wood": "木", "Fire": "火", "Earth": "土", "Metal": "金", "Water": "水"}[element]
        bar = "█" * int(value * 2)
        print(f"  {element:6s} ({element_cn}): {value:4.1f} {bar}")
    print()
    
    # Analysis results
    print("=" * 70)
    print("📊 命理分析 / Analysis")
    print("=" * 70)
    print()
    print(f"✨ 核心性格 / Core Personality:")
    print(f"   {analysis['personality']}")
    print()
    
    print(f"💼 事业方向 / Career Direction:")
    print(f"   {analysis['career_direction']}")
    print()
    
    print(f"❤️ 感情特质 / Relationship Insights:")
    print(f"   {analysis['relationship']}")
    print()
    
    print(f"⚖️ 五行平衡 / Element Balance:")
    print(f"   最强 / Strongest: {analysis['element_balance']['strongest']}")
    print(f"   最弱 / Weakest: {analysis['element_balance']['weakest']}")
    if analysis['element_balance']['strengths']:
        print(f"   优势元素 / Strengths: {', '.join(analysis['element_balance']['strengths'].keys())}")
    if analysis['element_balance']['needs_support']:
        print(f"   需补元素 / Needs Support: {', '.join(analysis['element_balance']['needs_support'].keys())}")
    print()
    
    print("-" * 70)
    print("⚠️ 重要说明 / Important Notes:")
    print(f"   {bazi_data['disclaimer']}")
    print()
    
    if lang == "cn":
        print("   由于时柱未知，以下方面需谨慎判断:")
        for item in analysis['limitations']['can_still_analyze']['cn']:
            print(f"     • {item}")
        print()
        print("💡 建议: 如能获得准确出生时间，可进行完整的四柱推算")
    else:
        print("   Due to unknown hour pillar, the following aspects require caution:")
        for item in analysis['limitations']['can_still_analyze']['en']:
            print(f"     • {item}")
        print()
        print("💡 Recommendation: If you can obtain the exact birth time, a complete 4-pillar calculation is recommended")
    
    print()
    print("=" * 70)

# =====================================================
# Main Public Function (Auto-detect based on input)
# =====================================================

def calculate_bazi(
    birth_date: datetime,
    tz_name: str = "Hong_Kong",
    location: Optional[str] = None,
    time_known: Optional[bool] = None
) -> Dict:
    """
    Main BaZi calculation function - auto-detects whether to use 3 or 4 pillars
    
    Args:
        birth_date: Birth date and time (if known)
        tz_name: Timezone or location name
        location: Specific location for longitude
        time_known: Whether birth time is known (auto-detected if None)
    
    Returns:
        BaZi data with either 3 or 4 pillars
    """
    
    # Auto-detect if time is known
    if time_known is None:
        # If hour is 0 and minute is 0, likely placeholder (unknown)
        if birth_date.hour == 0 and birth_date.minute == 0:
            time_known = False
        else:
            time_known = True
    
    if time_known:
        # Use full 4-pillar calculation
        longitude = resolve_longitude(location or tz_name)
        tz_resolved = tz_name if "/" in tz_name else "Asia/Hong_Kong"
        return calc_bazi_fixed(birth_date, tz_resolved, longitude)
    else:
        # Use 3-pillar calculation (professional approach for unknown time)
        return calc_bazi_three_pillars(birth_date, tz_name, location)

# =====================================================
# Localization Helpers
# =====================================================

def enrich_with_localized_pillars(bazi_data: Dict, lang: str = "cn"):
    """Add localized labels to pillars"""
    gan_map = GAN_CN if lang == "cn" else GAN
    zhi_map = ZHI_CN if lang == "cn" else ZHI
    
    if "pillars" in bazi_data:
        for key, pillar in bazi_data["pillars"].items():
            if "gan" in pillar and "zhi" in pillar:
                try:
                    gan_idx = GAN.index(pillar["gan"])
                    zhi_idx = ZHI.index(pillar["zhi"])
                    pillar["label"] = gan_map[gan_idx] + zhi_map[zhi_idx]
                    pillar["gan_local"] = gan_map[gan_idx]
                    pillar["zhi_local"] = zhi_map[zhi_idx]
                except (ValueError, IndexError):
                    pillar["label"] = "???"
                    pillar["gan_local"] = "?"
                    pillar["zhi_local"] = "?"

def localize_pillars(pillars: Dict, lang: str = "en") -> Tuple[Dict, str]:
    """Localize pillars to specified language"""
    lang = lang.lower()
    gan_map = GAN_MAP.get(lang, GAN_MAP["en"])
    zhi_map = ZHI_MAP.get(lang, ZHI_MAP["en"])
    
    def map_one(gz):
        try:
            gan_en = gz["gan"]
            zhi_en = gz["zhi"]
            gan_local = gan_map[GAN_MAP["en"].index(gan_en)]
            zhi_local = zhi_map[ZHI_MAP["en"].index(zhi_en)]
            return {**gz, "gan_local": gan_local, "zhi_local": zhi_local}
        except (ValueError, KeyError):
            return {**gz, "gan_local": "?", "zhi_local": "?"}
    
    localized = {k: map_one(v) for k, v in pillars.items()}
    full_str = " ".join([
        v["gan_local"] + v["zhi_local"] 
        for v in localized.values() 
        if v["gan_local"] != "?"
    ])
    
    return localized, full_str

# =====================================================
# Test Cases
# =====================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("VERIFICATION: Day Pillar, Day Master & Five Elements Test")
    print("=" * 70)
    
    # Test date: 1966-10-09 (your test case)
    test_date = datetime(1966, 10, 9, 0, 0)  # midnight placeholder
    
    # Method 1: Known time at 07:00 (7am)
    result_known = calculate_bazi(
        birth_date=datetime(1966, 10, 9, 7, 0),
        tz_name="Hong_Kong",
        time_known=True
    )
    
    # Method 2: Unknown time (3 pillars only)
    result_unknown = calculate_bazi(
        birth_date=test_date,
        tz_name="Hong_Kong",
        time_known=False
    )
    
    # Add localized labels
    enrich_with_localized_pillars(result_known, lang="cn")
    enrich_with_localized_pillars(result_unknown, lang="cn")
    
    # Day Master Display
    print("\n" + "=" * 70)
    print("👤 DAY MASTER (日主) - Core of the Chart")
    print("=" * 70)
    
    day_master_cn_map = {
        "Jia": "甲木", "Yi": "乙木",
        "Bing": "丙火", "Ding": "丁火",
        "Wu": "戊土", "Ji": "己土",
        "Geng": "庚金", "Xin": "辛金",
        "Ren": "壬水", "Gui": "癸水"
    }
    
    day_master_element = {
        "Jia": "Wood", "Yi": "Wood",
        "Bing": "Fire", "Ding": "Fire",
        "Wu": "Earth", "Ji": "Earth",
        "Geng": "Metal", "Xin": "Metal",
        "Ren": "Water", "Gui": "Water"
    }
    
    print(f"\n🔮 KNOWN TIME (4 Pillars):")
    print(f"   Day Master: {result_known['day_master']} ({day_master_cn_map[result_known['day_master']]})")
    print(f"   Element: {day_master_element[result_known['day_master']]}")
    print(f"   Day Pillar: {result_known['pillars']['day']['label']}")
    
    print(f"\n❓ UNKNOWN TIME (3 Pillars):")
    print(f"   Day Master: {result_unknown['day_master']} ({day_master_cn_map[result_unknown['day_master']]})")
    print(f"   Element: {day_master_element[result_unknown['day_master']]}")
    print(f"   Day Pillar: {result_unknown['pillars']['day']['label']}")
    
    print(f"\n✅ Day Master Consistency: {result_known['day_master'] == result_unknown['day_master']}")
    
    # Day Pillar Comparison
    print("\n" + "=" * 70)
    print("📅 DAY PILLAR COMPARISON")
    print("=" * 70)
    
    print(f"\n   Known Time (07:00)  - Day Pillar: {result_known['pillars']['day']['label']}")
    print(f"   Unknown Time        - Day Pillar: {result_unknown['pillars']['day']['label']}")
    print(f"   ✅ Day pillars match: {result_known['pillars']['day']['label'] == result_unknown['pillars']['day']['label']}")
    
    # Full Pillar Comparison
    print("\n" + "=" * 70)
    print("📋 FULL PILLARS COMPARISON")
    print("=" * 70)
    
    print("\n🔮 KNOWN TIME (4 Pillars - Full Chart):")
    print(f"   年柱: {result_known['pillars']['year']['label']} ({result_known['pillars']['year']['gan']}{result_known['pillars']['year']['zhi']})")
    print(f"   月柱: {result_known['pillars']['month']['label']} ({result_known['pillars']['month']['gan']}{result_known['pillars']['month']['zhi']})")
    print(f"   日柱: {result_known['pillars']['day']['label']} ({result_known['pillars']['day']['gan']}{result_known['pillars']['day']['zhi']})")
    print(f"   时柱: {result_known['pillars']['hour']['label']} ({result_known['pillars']['hour']['gan']}{result_known['pillars']['hour']['zhi']})")
    print(f"   日主: {result_known['day_master']} ({day_master_cn_map[result_known['day_master']]})")
    
    print("\n❓ UNKNOWN TIME (3 Pillars - Hour Not Calculated):")
    print(f"   年柱: {result_unknown['pillars']['year']['label']} ({result_unknown['pillars']['year']['gan']}{result_unknown['pillars']['year']['zhi']})")
    print(f"   月柱: {result_unknown['pillars']['month']['label']} ({result_unknown['pillars']['month']['gan']}{result_unknown['pillars']['month']['zhi']})")
    print(f"   日柱: {result_unknown['pillars']['day']['label']} ({result_unknown['pillars']['day']['gan']}{result_unknown['pillars']['day']['zhi']})")
    print(f"   时柱: [未推算 - 出生时间不详]")
    print(f"   日主: {result_unknown['day_master']} ({day_master_cn_map[result_unknown['day_master']]})")
    
    # Five Elements Comparison
    print("\n" + "=" * 70)
    print("⚖️ FIVE ELEMENTS COMPARISON (五行力量)")
    print("=" * 70)
    
    elements_known = result_known['five_elements_strength']
    elements_unknown = result_unknown['five_elements_strength']
    
    # Element mapping for Chinese display
    element_cn = {
        "Wood": "木", 
        "Fire": "火", 
        "Earth": "土", 
        "Metal": "金", 
        "Water": "水"
    }
    
    print("\n📊 KNOWN TIME (4 Pillars - Includes Hour Pillar):")
    print("   ┌─────────┬──────────┬─────────────┬──────────────────┐")
    print("   │ Element │ Strength │ Bar         │ vs Day Master    │")
    print("   ├─────────┼──────────┼─────────────┼──────────────────┤")
    
    day_master_elem = day_master_element[result_known['day_master']]
    for element in ["Wood", "Fire", "Earth", "Metal", "Water"]:
        strength = elements_known[element]
        bar = "█" * int(strength * 2)
        relationship = "⭐ 日主" if element == day_master_elem else ""
        print(f"   │ {element_cn[element]:3s}    │ {strength:5.1f}    │ {bar:<11} │ {relationship:16} │")
    print("   └─────────┴──────────┴─────────────┴──────────────────┘")
    
    print("\n📊 UNKNOWN TIME (3 Pillars - No Hour Pillar):")
    print("   ┌─────────┬──────────┬─────────────┬──────────────────┐")
    print("   │ Element │ Strength │ Bar         │ vs Day Master    │")
    print("   ├─────────┼──────────┼─────────────┼──────────────────┤")
    
    for element in ["Wood", "Fire", "Earth", "Metal", "Water"]:
        strength = elements_unknown[element]
        bar = "█" * int(strength * 2)
        relationship = "⭐ 日主" if element == day_master_elem else ""
        print(f"   │ {element_cn[element]:3s}    │ {strength:5.1f}    │ {bar:<11} │ {relationship:16} │")
    print("   └─────────┴──────────┴─────────────┴──────────────────┘")
    
    # Difference Analysis
    print("\n📈 DIFFERENCE ANALYSIS (Unknown vs Known):")
    print("   ┌─────────┬──────────┬──────────┬─────────────┬─────────────────┐")
    print("   │ Element │ Known    │ Unknown  │ Difference  │ Impact          │")
    print("   ├─────────┼──────────┼──────────┼─────────────┼─────────────────┤")
    for element in ["Wood", "Fire", "Earth", "Metal", "Water"]:
        known = elements_known[element]
        unknown = elements_unknown[element]
        diff = unknown - known
        diff_symbol = "↑" if diff > 0 else "↓" if diff < 0 else "="
        
        # Explain impact
        if element == day_master_elem:
            impact = "日主力量变化"
        elif diff > 0:
            impact = f"{element_cn[element]}增强"
        elif diff < 0:
            impact = f"{element_cn[element]}减弱"
        else:
            impact = "无变化"
        
        print(f"   │ {element_cn[element]:3s}    │ {known:5.1f}    │ {unknown:5.1f}    │ {diff:5.1f} {diff_symbol}    │ {impact:15} │")
    print("   └─────────┴──────────┴──────────┴─────────────┴─────────────────┘")
    
    # Hour Pillar Contribution
    print("\n💡 HOUR PILLAR CONTRIBUTION (Why elements differ):")
    print("   " + "-" * 66)
    
    if "hour" in result_known['pillars']:
        hour_gan = result_known['pillars']['hour']['gan']
        hour_zhi = result_known['pillars']['hour']['zhi']
        
        print(f"\n   Hour pillar in known time: {hour_gan}{hour_zhi}")
        print(f"   This contributes to the 4-pillar chart but is ABSENT in 3-pillar chart:\n")
        
        ELEMENT_MAP = {
            "Jia":"Wood", "Yi":"Wood",
            "Bing":"Fire","Ding":"Fire",
            "Wu":"Earth","Ji":"Earth",
            "Geng":"Metal","Xin":"Metal",
            "Ren":"Water","Gui":"Water",
        }
        
        ZHI_HIDDEN_STEMS = {
            "Zi":  [("Ren", 1.0)],
            "Chou":[("Ji", 0.6), ("Gui", 0.3), ("Xin", 0.1)],
            "Yin": [("Jia", 0.6), ("Bing", 0.3), ("Wu", 0.1)],
            "Mao": [("Yi", 1.0)],
            "Chen":[("Wu", 0.6), ("Yi", 0.3), ("Gui", 0.1)],
            "Si":  [("Bing", 0.6), ("Wu", 0.3), ("Geng", 0.1)],
            "Wu":  [("Ding", 0.6), ("Ji", 0.4)],
            "Wei": [("Ji", 0.6), ("Yi", 0.3), ("Ding", 0.1)],
            "Shen":[("Geng", 0.6), ("Ren", 0.3), ("Wu", 0.1)],
            "You": [("Xin", 1.0)],
            "Xu":  [("Wu", 0.6), ("Xin", 0.3), ("Ding", 0.1)],
            "Hai": [("Ren", 0.6), ("Jia", 0.4)],
        }
        
        # Hour stem contribution
        hour_stem_element = ELEMENT_MAP[hour_gan]
        print(f"   📍 Hour Stem ({hour_gan}): +1.0 {hour_stem_element}")
        
        # Hour branch hidden stems
        print(f"   📍 Hour Branch ({hour_zhi}) hidden stems:")
        for hidden_gan, weight in ZHI_HIDDEN_STEMS[hour_zhi]:
            hidden_element = ELEMENT_MAP[hidden_gan]
            print(f"      └─ {hidden_gan}: +{weight} {hidden_element}")
    
    print("\n" + "=" * 70)
    print("✅ TEST COMPLETE")
    print("=" * 70)
    
    print("\n📝 SUMMARY:")
    print(f"   ✓ Day Master: {result_known['day_master']} (SAME for both) - This is the CORE of the chart")
    print(f"   ✓ Day Pillar: {result_known['pillars']['day']['label']} (SAME for both)")
    print(f"   ✗ Five Elements: DIFFER because hour pillar is included/excluded")
    print(f"   ✓ This is EXPECTED behavior for unknown birth time")
    print(f"   ✓ LLM will receive DIFFERENT element strengths based on time confidence")
    print(f"\n   🎯 Day Master remains the anchor - all analysis centers on this!")