import math
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import sxtwl
from typing import Optional

# =====================================================
# Heavenly Stems & Earthly Branches
# =====================================================
GAN = ["Jia", "Yi", "Bing", "Ding", "Wu", "Ji", "Geng", "Xin", "Ren", "Gui"]
ZHI = ["Zi", "Chou", "Yin", "Mao", "Chen", "Si", "Wu", "Wei", "Shen", "You", "Xu", "Hai"]

GAN_CN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
ZHI_CN = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

GAN = ["Jia","Yi","Bing","Ding","Wu","Ji","Geng","Xin","Ren","Gui"]
ZHI = ["Zi","Chou","Yin","Mao","Chen","Si","Wu","Wei","Shen","You","Xu","Hai"]

GAN_MAP = {
    "en": ["Jia","Yi","Bing","Ding","Wu","Ji","Geng","Xin","Ren","Gui"],
    "cn": ["甲","乙","丙","丁","戊","己","庚","辛","壬","癸"]
}

ZHI_MAP = {
    "en": ["Zi","Chou","Yin","Mao","Chen","Si","Wu","Wei","Shen","You","Xu","Hai"],
    "cn": ["子","丑","寅","卯","辰","巳","午","未","申","酉","戌","亥"]
}

# =====================================================
# Longitude Strategy (FlowMind Standard)
# =====================================================
LOCATION_LON_TABLE = {
    # Asia
    "hong kong": 114.1095,
    "taipei": 121.5654,
    "beijing": 116.4074,
    "shanghai": 121.4737,

    # USA
    "new york": -74.0060,
    "los angeles": -118.2437,
    "san francisco": -122.4194,
    "chicago": -87.6298,

    # Australia
    "sydney": 151.2093,
    "melbourne": 144.9631,
    "brisbane": 153.0251,
    "perth": 115.8605,

    # Europe
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

    # exact match
    if key in LOCATION_LON_TABLE:
        return LOCATION_LON_TABLE[key]

    # partial city match
    for city, lon in LOCATION_LON_TABLE.items():
        if city in key:
            return lon

    # region fallback
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

    # longitude correction (minutes)
    lon_offset = (longitude - 120.0) * 4.0

    # equation of time (approx)
    day_of_year = local_dt.timetuple().tm_yday
    B = 2 * math.pi * (day_of_year - 81) / 365
    eot = 9.87 * math.sin(2 * B) - 7.53 * math.cos(B) - 1.5 * math.sin(B)

    return local_dt + timedelta(minutes=(lon_offset + eot))

def get_hour_zhi(hour: int) -> str:
    return ZHI[((hour + 1) // 2) % 12]

# =====================================================
# Core Engine (DO NOT CALL DIRECTLY)
# =====================================================
def calc_bazi_fixed(dt: datetime, tz_name: str, longitude: float):
    # timezone normalize
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo(tz_name))
    else:
        dt = dt.astimezone(ZoneInfo(tz_name))

    true_solar = calculate_true_solar_time(dt, longitude)

    # Zi-hour day switch
    solar_date = true_solar.date()
    if true_solar.hour == 23:
        solar_date += timedelta(days=1)

    lunar = sxtwl.fromSolar(solar_date.year, solar_date.month, solar_date.day)

    year_gz = lunar.getYearGZ()
    month_gz = lunar.getMonthGZ()
    day_gz = lunar.getDayGZ()

    year_gan, year_zhi = GAN[year_gz.tg], ZHI[year_gz.dz]
    month_gan, month_zhi = GAN[month_gz.tg], ZHI[month_gz.dz]
    day_gan, day_zhi = GAN[day_gz.tg], ZHI[day_gz.dz]

    # Hour pillar (五鼠遁)
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

    return {
        "year": {"gan": year_gan, "zhi": year_zhi},
        "month": {"gan": month_gan, "zhi": month_zhi},
        "day": {"gan": day_gan, "zhi": day_zhi},
        "hour": {"gan": hour_gan, "zhi": hour_zhi},
        "true_solar_time": true_solar,
        "longitude_used": longitude,
        "solar_date_used": solar_date,
    }

# =====================================================
# Public Adapter
# =====================================================
def calc_bazi(dt: datetime, tz_name: str = "Hong_Kong"):
    longitude = resolve_longitude(tz_name)
    tz_resolved = tz_name if "/" in tz_name else "Asia/Hong_Kong"
    return calc_bazi_fixed(dt=dt, tz_name=tz_resolved, longitude=longitude)

# =====================================================
# Localization Helper
# =====================================================
def enrich_with_localized_pillars(bazi: dict, lang="cn"):
    gan_map = GAN_CN if lang == "cn" else GAN
    zhi_map = ZHI_CN if lang == "cn" else ZHI
    for key in ["year","month","day","hour"]:
        g = bazi[key]["gan"]
        z = bazi[key]["zhi"]
        bazi[key]["label"] = gan_map[GAN.index(g)] + zhi_map[ZHI.index(z)]


def localize_pillars(pillars, lang="en"):
    """
    pillars: {
        "year": {"gan": "Bing", "zhi": "Wu"},
        "month": {...},
        ...
    }
    Returns the same dict with extra fields: gan_local, zhi_local, and a full string.
    """
    lang = lang.lower()
    gan_map = GAN_MAP.get(lang, GAN_MAP["en"])
    zhi_map = ZHI_MAP.get(lang, ZHI_MAP["en"])

    def map_one(gz):
        gan_en = gz["gan"]
        zhi_en = gz["zhi"]
        gan_local = gan_map[GAN_MAP["en"].index(gan_en)]
        zhi_local = zhi_map[ZHI_MAP["en"].index(zhi_en)]
        return {**gz, "gan_local": gan_local, "zhi_local": zhi_local}

    localized = {k: map_one(v) for k,v in pillars.items()}

    # Generate a single string
    full_str = " ".join([v["gan_local"] + v["zhi_local"] for k,v in localized.items()])

    return localized, full_str

# =====================================================
# === Test Cases ===
# =====================================================
if __name__ == "__main__":
    test_cases = [
        {"name":"HK 1966-10-09 07:00","dt":datetime(1966,10,9,7,0),"tz":"Hong_Kong","expected":"丙午 戊戌 辛丑 辛卯"},
        {"name":"HK 1990-08-08 20:00","dt":datetime(1990,8,8,20,0),"tz":"Hong_Kong","expected":"庚午 甲申 乙巳 丙戌"},
        {"name":"Beijing 2000-01-01 00:30","dt":datetime(2000,1,1,0,30),"tz":"Beijing","expected":"己卯 丙子 戊午 壬子"},
        {"name":"Taipei 2024-01-01 23:30","dt":datetime(2024,1,1,23,30),"tz":"Taipei","expected":"癸卯 甲子 乙丑 丙子"},
        {"name":"Beijing 2024-02-04 16:30","dt":datetime(2024,2,4,16,30),"tz":"Beijing","expected":"甲辰 丙寅 戊戌 庚申"},
        {"name":"Stockholm 2023-02-04 15:30","dt":datetime(2023,2,4,15,30),"tz":"Stockholm","expected":"癸卯 甲寅 癸巳 丙辰"},
        {"name":"Sydney 2000-05-05 20:00","dt":datetime(2000,5,5,20,0),"tz":"Sydney","expected":"庚辰 辛巳 癸亥 癸亥"},
        {"name":"Paris 2024-01-01 12:00","dt":datetime(2024,1,1,12,0),"tz":"Paris","expected":"癸卯 甲子 甲子 丙寅"},
    ]

    print("="*70)
    for case in test_cases:
        result = calc_bazi(case["dt"], case["tz"])
        enrich_with_localized_pillars(result, lang="cn")
        bazi_str_cn = f"{result['year']['label']} {result['month']['label']} {result['day']['label']} {result['hour']['label']}"
        match = bazi_str_cn == case["expected"]
        status = "✅ PASS" if match else "❌ FAIL"
        print(f"{case['name']:30} {status}")
        print(f"  Got:     {bazi_str_cn}")
        print(f"  Expected:{case['expected']}")
        print(f"  TZ used: {case['tz']}")
        print(f"  Lon used:{result['longitude_used']}")
        print(f"  True Solar:{result['true_solar_time']}")
        print(f"  Solar Date Used:{result['solar_date_used']}")
        print("-"*50)
