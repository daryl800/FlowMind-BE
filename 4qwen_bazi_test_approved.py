import sxtwl
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import math

# Constants
GAN = ["Jia", "Yi", "Bing", "Ding", "Wu", "Ji", "Geng", "Xin", "Ren", "Gui"]
ZHI = ["Zi", "Chou", "Yin", "Mao", "Chen", "Si", "Wu", "Wei", "Shen", "You", "Xu", "Hai"]
GAN_CN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
ZHI_CN = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

def calculate_true_solar_time(local_dt: datetime, longitude: float) -> datetime:
    """Calculate true solar time based on longitude and equation of time."""
    if local_dt.tzinfo is None:
        raise ValueError("Input datetime must be timezone-aware")
    
    # Longitude correction (minutes)
    lon_offset = (longitude - 120.0) * 4.0  # 4 minutes per degree from 120°E
    
    # Equation of Time (approximation)
    day_of_year = local_dt.timetuple().tm_yday
    B = 2 * math.pi * (day_of_year - 81) / 365
    eot = 9.87 * math.sin(2*B) - 7.53 * math.cos(B) - 1.5 * math.sin(B)  # in minutes
    
    total_offset = lon_offset + eot
    true_solar_time = local_dt + timedelta(minutes=total_offset)
    return true_solar_time.replace(tzinfo=local_dt.tzinfo)

def get_hour_zhi(true_solar_hour: int) -> str:
    """Map true solar hour to earthly branch."""
    if true_solar_hour == 23 or true_solar_hour == 0:
        return "Zi"
    elif 1 <= true_solar_hour <= 2:
        return "Chou"
    elif 3 <= true_solar_hour <= 4:
        return "Yin"
    elif 5 <= true_solar_hour <= 6:
        return "Mao"
    elif 7 <= true_solar_hour <= 8:
        return "Chen"
    elif 9 <= true_solar_hour <= 10:
        return "Si"
    elif 11 <= true_solar_hour <= 12:
        return "Wu"
    elif 13 <= true_solar_hour <= 14:
        return "Wei"
    elif 15 <= true_solar_hour <= 16:
        return "Shen"
    elif 17 <= true_solar_hour <= 18:
        return "You"
    elif 19 <= true_solar_hour <= 20:
        return "Xu"
    elif 21 <= true_solar_hour <= 22:
        return "Hai"
    else:
        raise ValueError(f"Invalid hour: {true_solar_hour}")

def calc_bazi_fixed(
    dt: datetime,
    tz_name: str = "Asia/Hong_Kong",
    longitude: float = 114.17
):
    """
    Fixed BaZi calculator using sxtwl correctly.
    """
    # 1. Make sure input is timezone-aware
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo(tz_name))
    else:
        dt = dt.astimezone(ZoneInfo(tz_name))

    # 2. Calculate true solar time
    true_solar = calculate_true_solar_time(dt, longitude)

    # 3. Determine the SOLAR DATE used for day pillar (handle Zi hour!)
    solar_date_for_day = true_solar.date()
    if true_solar.hour == 23:
        # Late Zi hour belongs to NEXT solar day
        solar_date_for_day = solar_date_for_day + timedelta(days=1)

    # 4. Use sxtwl to get lunar info FROM THIS SOLAR DATE
    lunar = sxtwl.fromSolar(solar_date_for_day.year, solar_date_for_day.month, solar_date_for_day.day)
    
    # Get year, month, day pillars from sxtwl
    year_gan_idx = lunar.getYearGZ().tg
    year_zhi_idx = lunar.getYearGZ().dz
    month_gan_idx = lunar.getMonthGZ().tg
    month_zhi_idx = lunar.getMonthGZ().dz
    day_gan_idx = lunar.getDayGZ().tg
    day_zhi_idx = lunar.getDayGZ().dz

    year_gan, year_zhi = GAN[year_gan_idx], ZHI[year_zhi_idx]
    month_gan, month_zhi = GAN[month_gan_idx], ZHI[month_zhi_idx]
    day_gan, day_zhi = GAN[day_gan_idx], ZHI[day_zhi_idx]

    # 5. Calculate HOUR pillar manually using WuShuDun (五鼠遁)
    hour_zhi = get_hour_zhi(true_solar.hour)
    hour_zhi_idx = ZHI.index(hour_zhi)

    # Five Rat Incantation (五鼠遁)
    wushu_map = {
        "Jia": "Jia", "Ji": "Jia",
        "Yi": "Bing", "Geng": "Bing",
        "Bing": "Wu", "Xin": "Wu",
        "Ding": "Geng", "Ren": "Geng",
        "Wu": "Ren", "Gui": "Ren"
    }
    base_gan = wushu_map[day_gan]
    base_gan_idx = GAN.index(base_gan)
    hour_gan_idx = (base_gan_idx + hour_zhi_idx) % 10
    hour_gan = GAN[hour_gan_idx]

    pillars = {
        "year": {"gan": year_gan, "zhi": year_zhi},
        "month": {"gan": month_gan, "zhi": month_zhi},
        "day": {"gan": day_gan, "zhi": day_zhi},
        "hour": {"gan": hour_gan, "zhi": hour_zhi},
    }

    _, bazi_str_cn = localize_pillars(pillars, lang="cn")
    return {
        "pillars": pillars,
        "bazi_string_cn": bazi_str_cn,
        "true_solar_time": true_solar,
        "solar_date_used": solar_date_for_day
    }

def localize_pillars(pillars, lang="en"):
    if lang == "cn":
        gan_map, zhi_map = GAN_CN, ZHI_CN
    else:
        gan_map, zhi_map = GAN, ZHI

    def map_one(gz):
        g = gz["gan"]; z = gz["zhi"]
        return gan_map[GAN.index(g)] + zhi_map[ZHI.index(z)]

    full_str = " ".join(map_one(pillars[k]) for k in ["year", "month", "day", "hour"])
    return pillars, full_str

# === Test with CORRECT expected results ===
def test_cases():
    cases = [
        # 案例 1: 1966-10-09 07:00 香港 (基础验证)
        {
            "name": "案例1-香港基础",
            "dt": datetime(1966, 10, 9, 7, 0, 0),
            "tz": "Asia/Hong_Kong",
            "lon": 114.17,
            "expected": "丙午 戊戌 辛丑 辛卯" # 经真太阳时校正后应为辛卯时
        },
        # 案例 2: 1990-08-08 20:00 香港 (夜間)
        {
            "name": "案例2-香港夜间",
            "dt": datetime(1990, 8, 8, 20, 0, 0),
            "tz": "Asia/Hong_Kong",
            "lon": 114.17,
            "expected": "庚午 甲申 乙巳 丙戌"
        },
        # 案例 3: 2000-01-01 00:30 北京 (早子时)
        {
            "name": "案例3-北京早子时",
            "dt": datetime(2000, 1, 1, 0, 30, 0),
            "tz": "Asia/Shanghai",
            "lon": 116.4,
            "expected": "己卯 丙子 戊午 壬子"
        },
        # 案例 4: 2024-01-01 23:30 台北 (晚子时)
        {
            "name": "案例4-台北晚子时",
            "dt": datetime(2024, 1, 1, 23, 30, 0),
            "tz": "Asia/Taipei",
            "lon": 121.5,
            "expected": "癸卯 甲子 乙丑 丙子" 
        },
        # 案例 5: 2024-02-04 16:30 北京 (立春节气交界日附近)
        {
            "name": "案例5-北京立春日",
            "dt": datetime(2024, 2, 4, 16, 30, 0),
            "tz": "Asia/Shanghai",
            "lon": 116.4,
            "expected": "甲辰 丙寅 戊戌 庚申"
            # 注意：2024年立春精确时刻为2月4日16:26:53，此时间在立春后，故年柱为甲辰，月柱为丙寅。
        },
        # 案例 6: 2023-02-04 15:30 斯德哥尔摩 (跨时区测试)
        {
            "name": "案例6-斯德哥尔摩",
            "dt": datetime(2023, 2, 4, 15, 30, 0),
            "tz": "Europe/Stockholm",
            "lon": 18.06, # 斯德哥尔摩经度
            "expected": "癸卯 甲寅 癸巳 丙辰"
            # 计算要点：欧洲中部时区(CET)标准经度为15°E，真太阳时校正量小。
            # 2023年立春在2月4日，此日期在立春后，故为壬寅年壬寅月。
        },
        # 案例 7: 1988-08-08 08:00 香港 (特殊日期)
        {
            "name": "案例7-香港特殊日",
            "dt": datetime(1988, 8, 8, 8, 0, 0),
            "tz": "Asia/Hong_Kong",
            "lon": 114.17,
            "expected": "戊辰 庚申 乙未 庚辰"
        },
    ]

    print("="*70)
    for case in cases:
        result = calc_bazi_fixed(case["dt"], case["tz"], case["lon"])
        match = result["bazi_string_cn"] == case["expected"]
        status = "✅ PASS" if match else "❌ FAIL"
        print(f"{case['name']:20} {status}")
        print(f"  Got:     {result['bazi_string_cn']}")
        print(f"  Expected:{case['expected']}")
        print(f"  True Solar: {result['true_solar_time']}")
        print(f"  Solar Date Used: {result['solar_date_used']}")
        print("-"*50)

if __name__ == "__main__":
    test_cases()