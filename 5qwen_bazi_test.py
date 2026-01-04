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
# City → Timezone Mapping
# =====================================================
CITY_TO_TZ = {
    "hong kong": "Asia/Hong_Kong",
    "taipei": "Asia/Taipei",
    "beijing": "Asia/Shanghai",
    "shanghai": "Asia/Shanghai",
    "paris": "Europe/Paris",
    "rome": "Europe/Rome",
    "milan": "Europe/Rome",
    "berlin": "Europe/Berlin",
    "munich": "Europe/Berlin",
    "stockholm": "Europe/Stockholm",
    "sydney": "Australia/Sydney",
    "melbourne": "Australia/Melbourne",
    "brisbane": "Australia/Brisbane",
    "perth": "Australia/Perth",
    "new york": "America/New_York",
    "los angeles": "America/Los_Angeles",
    "chicago": "America/Chicago",
    "san francisco": "America/Los_Angeles",
}

def resolve_timezone(tz_name: str) -> str:
    key = tz_name.lower().replace("_", " ").strip()
    if "/" in tz_name:
        return tz_name  # already valid tz string
    if key in CITY_TO_TZ:
        return CITY_TO_TZ[key]
    return "Asia/Hong_Kong"  # default fallback

# =====================================================
# True Solar Time
# =====================================================
def calculate_true_solar_time(local_dt: datetime, longitude: float) -> datetime:
    if local_dt.tzinfo is None:
        raise ValueError("Datetime must be timezone-aware")
    lon_offset = (longitude - 120.0) * 4.0  # minutes
    day_of_year = local_dt.timetuple().tm_yday
    B = 2 * math.pi * (day_of_year - 81) / 365
    eot = 9.87 * math.sin(2*B) - 7.53 * math.cos(B) - 1.5 * math.sin(B)
    return local_dt + timedelta(minutes=(lon_offset + eot))

def get_hour_zhi(hour: int) -> str:
    return ZHI[((hour + 1) // 2) % 12]

# =====================================================
# Core Engine
# =====================================================
def calc_bazi_fixed(dt: datetime, tz_name: str, longitude: float):
    # timezone normalize
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo(tz_name))
    else:
        dt = dt.astimezone(ZoneInfo(tz_name))
    true_solar = calculate_true_solar_time(dt, longitude)

    # Zi-hour day switch (local time)
    solar_date = true_solar.date()
    if true_solar.hour == 23:
        solar_date += timedelta(days=1)
    
    # Convert to UTC for sxtwl (critical fix)
    true_solar_utc = true_solar.astimezone(ZoneInfo("UTC"))
    solar_date_utc = true_solar_utc.date()
    
    lunar = sxtwl.fromSolar(solar_date_utc.year, solar_date_utc.month, solar_date_utc.day)
    year_gz, month_gz, day_gz = lunar.getYearGZ(), lunar.getMonthGZ(), lunar.getDayGZ()

    year_gan, year_zhi = GAN[year_gz.tg], ZHI[year_gz.dz]
    month_gan, month_zhi = GAN[month_gz.tg], ZHI[month_gz.dz]
    day_gan, day_zhi = GAN[day_gz.tg], ZHI[day_gz.dz]

    # Hour pillar
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
    }

# =====================================================
# ✅ PUBLIC ADAPTER
# =====================================================
def calc_bazi(dt: datetime, tz_name: str = "Hong_Kong"):
    """
    Adapter: call with dt + city/country/timezone name
    """
    longitude = resolve_longitude(tz_name)
    tz_for_calc = resolve_timezone(tz_name)
    return calc_bazi_fixed(dt=dt, tz_name=tz_for_calc, longitude=longitude)

# =====================================================
# Localization Helper
# =====================================================
def enrich_with_localized_pillars(bazi: dict, lang="en"):
    gan_map = GAN_CN if lang == "cn" else GAN
    zhi_map = ZHI_CN if lang == "cn" else ZHI
    for key in ["year", "month", "day", "hour"]:
        g = bazi[key]["gan"]
        z = bazi[key]["zhi"]
        bazi[key]["label"] = gan_map[GAN.index(g)] + zhi_map[ZHI.index(z)]

# =====================================================
# === Test Cases ===
# =====================================================
def test_cases():
    cases = [
        {"name":"HK 1966-10-09 07:00", "dt":datetime(1966,10,9,7,0,0), "tz":"Hong_Kong", "expected":"丙午 戊戌 丁卯 癸卯"},
        {"name":"Paris 2024-01-01 12:00", "dt":datetime(2024,1,1,12,0,0), "tz":"Paris", "expected":"癸卯 甲子 乙丑 丙午"},
        {"name":"Stockholm 2023-02-04 15:30", "dt":datetime(2023,2,4,15,30,0), "tz":"Stockholm", "expected":"癸卯 甲寅 癸巳 丙辰"},
        {"name":"Sydney 2000-05-05 20:00", "dt":datetime(2000,5,5,20,0,0), "tz":"Sydney", "expected":"庚辰 丙辰 壬午 丁酉"},
    ]
    print("="*70)
    for case in cases:
        result = calc_bazi(case["dt"], case["tz"])
        # make bazi_string_cn
        bazi_str_cn = " ".join(
            GAN_CN[GAN.index(result[k]["gan"])] + ZHI_CN[ZHI.index(result[k]["zhi"])] 
            for k in ["year","month","day","hour"]
        )
        match = bazi_str_cn == case["expected"]
        status = "✅ PASS" if match else "❌ FAIL"
        print(f"{case['name']:30} {status}")
        print(f"  Got:     {bazi_str_cn}")
        print(f"  Expected:{case['expected']}")
        print(f"  TZ used:  {resolve_timezone(case['tz'])}")
        print(f"  Lon used: {resolve_longitude(case['tz'])}")
        print(f"  True Solar: {result['true_solar_time']}")
        print(f"  Solar Date Used: {result['true_solar_time'].date()}")
        print("-"*50)

if __name__ == "__main__":
    test_cases()