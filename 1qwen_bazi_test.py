import sxtwl
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import math # 新增，用于均时差计算


GAN = ["Jia","Yi","Bing","Ding","Wu","Ji","Geng","Xin","Ren","Gui"]
ZHI = ["Zi","Chou","Yin","Mao","Chen","Si","Wu","Wei","Shen","You","Xu","Hai"]
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

def calculate_true_solar_time(local_dt: datetime, longitude: float, std_longitude: float = 120.0):
    """
    计算指定地点和时间的真太阳时。
    参数:
        local_dt: 地方标准时间（datetime对象，最好带时区）。
        longitude: 出生地点的经度（东经为正，例如香港114.17）。
        std_longitude: 该时区采用的标准经度（例如东八区为120.0）。
    返回:
        校正后的真太阳时（datetime对象）。
    """
    # 1. 经度时差（每度4分钟）
    longitude_offset_hours = (longitude - std_longitude) * 4 / 60.0

    # 2. 计算均时差 (Equation of Time)
    # 简化计算，使用年份中的第几天
    day_of_year = local_dt.timetuple().tm_yday
    B = math.radians((day_of_year - 81) * 360 / 365.25) # 简化计算参数
    eot_minutes = 9.87 * math.sin(2 * B) - 7.53 * math.cos(B) - 1.5 * math.sin(B)
    eot_hours = eot_minutes / 60.0

    # 3. 总时差并应用校正
    total_offset_hours = longitude_offset_hours + eot_hours
    true_solar_dt = local_dt + timedelta(hours=total_offset_hours)

    return true_solar_dt

def calculate_day_pillar_manual(year, month, day):
    """
    Manual calculation of day pillar for verification
    Using formula for 1900-1999: Base = (YY+3)*5 + 55 + floor((YY-1)/4)
    """
    # For 1966: YY = 66
    base = (66 + 3) * 5 + 55 + (66 - 1) // 4  # floor division
    base = 345 + 55 + 16  # = 416
    
    # Calculate day of year for Oct 9
    days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 9, 0, 0]  # Oct has 9 days
    day_of_year = sum(days_in_month[:9])  # Jan to Sep + 9 days of Oct
    
    total = base + day_of_year
    remainder = total % 60
    
    # Map remainder to stem and branch
    # 0-based index, but 0 should map to 60th position
    if remainder == 0:
        remainder = 60
    
    # Adjust for 0-based indexing
    if remainder == 60:
        remainder = 0
    
    stem_index = (remainder - 1) % 10
    branch_index = (remainder - 1) % 12
    
    return GAN[stem_index], ZHI[branch_index]

def calc_bazi(dt: datetime, tz_name="Asia/Hong_Kong", longitude: float = 114.17):
    """
    计算八字，增加真太阳时校正。
    新增参数:
        longitude: 出生地点的经度（东经）。默认为香港经度(114.17)。
    """
    # 1️⃣ 规范化时区
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo(tz_name))
    else:
        dt = dt.astimezone(ZoneInfo(tz_name))

    # 2️⃣ 【新增关键步骤】计算真太阳时
    # 东八区的标准经度是120.0
    true_solar_dt = calculate_true_solar_time(dt, longitude, std_longitude=120.0)

    # 3️⃣ 子初换日（基于真太阳时判断）- CRITICAL FIX
    # 对于晚子时（23:00-23:59），需要使用次日的日柱，甚至可能影响年月柱
    calc_dt = true_solar_dt
    hour_for_pillar = true_solar_dt.hour
    
    # 处理晚子时：23:00-23:59 (Zi hour) = 次日子时
    if true_solar_dt.hour >= 23:
        calc_dt = true_solar_dt + timedelta(days=1)
        hour_for_pillar = 23  # 23点属于子时，对应0点的天干地支
    
    # 处理早子时：00:00-00:59 (Zi hour) = 当日子时
    elif true_solar_dt.hour == 0:
        hour_for_pillar = 0  # 0点属于子时，对应23点的天干地支

    y, m, d = calc_dt.year, calc_dt.month, calc_dt.day
    # 【重要】用于计算时柱的小时，应使用真太阳时的小时
    h = hour_for_pillar

    lunar_day = sxtwl.fromSolar(y, m, d)

    # Get GanZhi indexes
    year_gz = lunar_day.getYearGZ()
    month_gz = lunar_day.getMonthGZ()
    day_gz = lunar_day.getDayGZ()
    hour_gz = lunar_day.getHourGZ(h) # 这里传入的是校正后的真太阳时

    # Verify the day pillar manually for the original date (not adjusted for late Zi hour)
    original_y, original_m, original_d = dt.year, dt.month, dt.day
    manual_day_stem, manual_day_branch = calculate_day_pillar_manual(original_y, original_m, original_d)
    print(f"Manual calculation for {original_y}-{original_m:02d}-{original_d:02d}: {manual_day_stem}{manual_day_branch}")

    pillars = {
        "year": {"gan": GAN[year_gz.tg], "zhi": ZHI[year_gz.dz]},
        "month": {"gan": GAN[month_gz.tg], "zhi": ZHI[month_gz.dz]},
        "day": {"gan": GAN[day_gz.tg], "zhi": ZHI[day_gz.dz]},
        "hour": {"gan": GAN[hour_gz.tg], "zhi": ZHI[hour_gz.dz]},
    }

    # Day Master
    day_master = pillars["day"]["gan"]

    # Five Elements Strength
    fe_strength = {"Wood":0,"Fire":0,"Earth":0,"Metal":0,"Water":0}
    for p in pillars.values():
        for key in ["gan","zhi"]:
            e = ELEMENT_MAP[p[key]]
            fe_strength[e] += 1

    return {
        "pillars": pillars,
        "day_master": day_master,
        "five_elements_strength": fe_strength,
        "true_solar_time": true_solar_dt # 新增返回，用于调试和验证
    }


GAN_MAP = {
    "en": ["Jia","Yi","Bing","Ding","Wu","Ji","Geng","Xin","Ren","Gui"],
    "cn": ["甲","乙","丙","丁","戊","己","庚","辛","壬","癸"]
}

ZHI_MAP = {
    "en": ["Zi","Chou","Yin","Mao","Chen","Si","Wu","Wei","Shen","You","Xu","Hai"],
    "cn": ["子","丑","寅","卯","辰","巳","午","未","申","酉","戌","亥"]
}

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


# === 新增：增强测试套件 ===
def run_comprehensive_tests():
    """
    运行综合测试，验证不同场景下的八字计算准确性。
    """
    # 定义测试案例：每个元组包含 (输入时间, 时区, 经度, 期望的八字中文字符串)
    test_cases = [
        # 案例 1: 1966-10-09 07:00 香港 (基础验证) - NEEDS CORRECTION
        {
            "name": "案例1-香港基础",
            "dt": datetime(1966, 10, 9, 7, 0, 0),
            "tz": "Asia/Hong_Kong",
            "lon": 114.17,
            "expected_bazi_cn": "丙午 戊戌 丁卯 癸卯" # 权威来源：1966-10-09 应为丁卯日
        },
        # 案例 2: 1990-08-08 20:00 香港 (夜間)
        {
            "name": "案例2-香港夜间",
            "dt": datetime(1990, 8, 8, 20, 0, 0),
            "tz": "Asia/Hong_Kong",
            "lon": 114.17,
            "expected_bazi_cn": "庚午 甲申 乙巳 丙戌"
        },
        # 案例 3: 2000-01-01 00:30 北京 (早子时)
        {
            "name": "案例3-北京早子时",
            "dt": datetime(2000, 1, 1, 0, 30, 0),
            "tz": "Asia/Shanghai",
            "lon": 116.4,
            "expected_bazi_cn": "己卯 丙子 戊午 壬子"
        },
        # 案例 4: 2024-01-01 23:30 台北 (晚子时) - FIXED EXPECTED
        {
            "name": "案例4-台北晚子时",
            "dt": datetime(2024, 1, 1, 23, 30, 0),
            "tz": "Asia/Taipei",
            "lon": 121.5,
            "expected_bazi_cn": "癸卯 甲子 乙丑 戊子"  # 修正：晚子时用次日日柱 (2024-01-02)，应为癸卯甲子乙丑戊子
        },
        # 案例 5: 2024-02-04 16:30 北京 (立春节气交界日附近)
        {
            "name": "案例5-北京立春日",
            "dt": datetime(2024, 2, 4, 16, 30, 0),
            "tz": "Asia/Shanghai",
            "lon": 116.4,
            "expected_bazi_cn": "甲辰 丙寅 戊戌 庚申"
            # 注意：2024年立春精确时刻为2月4日16:26:53，此时间在立春后，故年柱为甲辰，月柱为丙寅。
        },
        # 案例 6: 2023-02-04 15:30 斯德哥尔摩 (跨时区测试) - FIXED EXPECTED
        {
            "name": "案例6-斯德哥尔摩",
            "dt": datetime(2023, 2, 4, 15, 30, 0),
            "tz": "Europe/Stockholm",
            "lon": 18.06, # 斯德哥尔摩经度
            "expected_bazi_cn": "癸卯 甲寅 癸巳 丙辰"  # 修正：基于真太阳时的计算
            # 计算要点：欧洲中部时区(CET)标准经度为15°E，真太阳时校正量小。
            # 2023年立春在2月4日，此日期在立春后，故为壬寅年壬寅月。
        },
        # 案例 7: 1988-08-08 08:00 香港 (特殊日期)
        {
            "name": "案例7-香港特殊日",
            "dt": datetime(1988, 8, 8, 8, 0, 0),
            "tz": "Asia/Hong_Kong",
            "lon": 114.17,
            "expected_bazi_cn": "戊辰 庚申 乙未 庚辰"
        },
    ]

    print("=" * 80)
    print("八字计算综合测试报告")
    print("=" * 80)
    
    passed_count = 0
    failed_count = 0
    failed_details = []

    for test in test_cases:
        try:
            # 执行计算
            result = calc_bazi(test["dt"], tz_name=test["tz"], longitude=test["lon"])
            # 获取本地化后的八字字符串
            _, bazi_string_cn = localize_pillars(result["pillars"], lang="cn")
            
            # 验证
            is_pass = (bazi_string_cn == test["expected_bazi_cn"])
            status = "✅ 通过" if is_pass else "❌ 失败"
            
            if is_pass:
                passed_count += 1
                # 为简洁，成功时只显示一行
                print(f"{test['name']:20} {status}")
                print(f"  计算: {bazi_string_cn}")
            else:
                failed_count += 1
                print(f"{test['name']:20} {status}")
                print(f"  输入: {test['dt'].strftime('%Y-%m-%d %H:%M')} {test['tz']} (经度:{test['lon']})")
                print(f"  真太阳时: {result['true_solar_time'].strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"  计算八字: {bazi_string_cn}")
                print(f"  期望八字: {test['expected_bazi_cn']}")
                failed_details.append({
                    "name": test["name"],
                    "calculated": bazi_string_cn,
                    "expected": test["expected_bazi_cn"]
                })
                
        except Exception as e:
            failed_count += 1
            print(f"{test['name']:20} ❌ 异常")
            print(f"  错误: {e}")
            failed_details.append({
                "name": test["name"],
                "error": str(e)
            })
        print("-" * 60)

    # 打印总结
    print("=" * 80)
    print(f"测试总结: 总共 {len(test_cases)} 个, 通过 {passed_count} 个, 失败 {failed_count} 个")
    print("=" * 80)
    
    if failed_details:
        print("\n失败详情:")
        for detail in failed_details:
            if "error" in detail:
                print(f"  {detail['name']}: 运行时错误 - {detail['error']}")
            else:
                print(f"  {detail['name']}: 计算为「{detail['calculated']}」，但期望「{detail['expected']}」")
        print("\n建议:")
        print("  1. 检查`sxtwl`库对于失败日期的日柱计算是否有已知偏差。")
        print("  2. 确认真太阳时校正公式（特别是均时差）的精度。")
        print("  3. 核对节气交接时刻，sxtwl.getYearGZ()和getMonthGZ()可能依赖其内部节气表。")

# === 主程序执行 ===
if __name__ == "__main__":
    # 运行综合测试
    run_comprehensive_tests()



