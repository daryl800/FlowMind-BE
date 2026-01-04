def precise_julian_day_calc(year, month, day):
    """
    More precise Julian Day calculation following astronomical standards
    """
    # For dates in the Gregorian calendar (after Oct 15, 1582)
    if month <= 2:
        year -= 1
        month += 12
    
    a = year // 100
    b = 2 - a + (a // 4)
    
    # Make sure the entire calculation results in an integer
    jd = int(365.25 * (year + 4716)) + int(30.6001 * (month + 1)) + day + b - 1524
    # Subtract 0.5 separately to maintain precision
    jd = jd - 1 if (365.25 * (year + 4716) + 30.6001 * (month + 1) + day + b - 1524.5) < 0 else jd
    # Actually, let's just use the standard formula properly
    jd = int(365.25 * (year + 4716)) + int(30.6001 * (month + 1)) + day + b - 1524
    jd = jd + int(-0.5)  # -0.5 -> -1, so jd = jd - 1
    # Better to just do the calculation properly:
    jd = int(365.25 * (year + 4716)) + int(30.6001 * (month + 1)) + day + b - 1525
    return jd

def verify_day_pillar_1966():
    """
    Let's verify using a known reference point and counting forward
    """
    # Known reference: Jan 1, 1900 was Geng Xu (47th in cycle)
    # Julian Day for Jan 1, 1900 = 2415021
    ref_jd = 2415021  # Jan 1, 1900
    ref_index = 47    # Geng Xu is 47th in 60-cycle
    
    # Calculate JD for Oct 9, 1966
    target_jd = precise_julian_day_calc(1966, 10, 9)
    
    # Calculate days difference
    days_diff = target_jd - ref_jd  # This should now be an integer
    day_index = (ref_index + days_diff) % 60
    if day_index == 0:
        day_index = 60
    
    # Convert to stem and branch
    gan = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
    zhi = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
    
    stem_idx = (day_index - 1) % 10
    branch_idx = (day_index - 1) % 12
    
    print(f"Reference: Jan 1, 1900 = Geng Xu (47th day)")
    print(f"Reference JD: {ref_jd}")
    print(f"Target date: Oct 9, 1966")
    print(f"Target JD: {target_jd}")
    print(f"Days difference: {days_diff}")
    print(f"Calculated day index: {day_index}")
    print(f"Result: {gan[stem_idx]}{zhi[branch_idx]}")
    
    # Let's also calculate it using the traditional formula more carefully
    print("\n--- Traditional Formula Verification ---")
    # For 1966: YY = 66
    base = (66 + 3) * 5 + 55 + (65 // 4)  # (66-1)//4 = 65//4 = 16
    print(f"Base calculation: (66+3)*5 + 55 + floor(65/4) = {(66+3)*5} + 55 + {65//4} = {base}")
    
    # Days in year calculation
    # Jan(31) + Feb(28) + Mar(31) + Apr(30) + May(31) + Jun(30) + 
    # Jul(31) + Aug(31) + Sep(30) + Oct(9) = 282
    days_to_date = 31 + 28 + 31 + 30 + 31 + 30 + 31 + 31 + 30 + 9
    print(f"Days to Oct 9: {days_to_date}")
    
    total = base + days_to_date
    print(f"Total: {base} + {days_to_date} = {total}")
    
    remainder = total % 60
    if remainder == 0:
        remainder = 60
        
    print(f"Remainder (mod 60): {remainder}")
    
    stem_idx_trad = (remainder - 1) % 10
    branch_idx_trad = (remainder - 1) % 12
    
    print(f"Traditional result: {gan[stem_idx_trad]}{zhi[branch_idx_trad]}")
    
    return (gan[stem_idx], zhi[branch_idx], day_index), (gan[stem_idx_trad], zhi[branch_idx_trad], remainder)

def calculate_hour_pillar_correctly(day_stem, hour):
    """
    Calculate hour pillar correctly using the 5 Rat Escape method
    """
    gan = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
    zhi = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
    
    # Determine the starting stem for the Zi hour based on day stem
    day_stem_idx = gan.index(day_stem)
    
    # Five Rat Escape (五鼠遁) rules:
    # 甲己日起甲子, 乙庚日起丙子, 丙辛日起戊子, 丁壬日起庚子, 戊癸日起壬子
    if day_stem_idx % 5 == 0:  # 甲/己 days (0, 5) - start with 甲
        zi_stem_idx = 0
    elif day_stem_idx % 5 == 1:  # 乙/庚 days (1, 6) - start with 丙
        zi_stem_idx = 2
    elif day_stem_idx % 5 == 2:  # 丙/辛 days (2, 7) - start with 戊
        zi_stem_idx = 4
    elif day_stem_idx % 5 == 3:  # 丁/壬 days (3, 8) - start with 庚
        zi_stem_idx = 6
    else:  # 戊/癸 days (4, 9) - start with 壬
        zi_stem_idx = 8
    
    # Map the hour (0-23) to the 2-hour Earthly Branch periods
    # 23-01=Zi(0), 01-03=Chou(1), 03-05=Yin(2), 05-07=Mao(3), 07-09=Chen(4), etc.
    if hour == 23:
        hour_index = 0  # 23:00-23:59 is Zi hour
    else:
        # For hours 0-22: 00-02=Zi(0), 02-04=Chou(1), 04-06=Yin(2), etc.
        # So: 00/01 -> Zi(0), 02/03 -> Chou(1), 04/05 -> Yin(2), 06/07 -> Mao(3), 08/09 -> Chen(4), etc.
        hour_index = hour // 2
        if hour % 2 == 1:  # If odd hour, it belongs to the same 2-hour period as the previous even hour
            hour_index = (hour - 1) // 2
    
    # Calculate the stem for the specific hour
    hour_stem_idx = (zi_stem_idx + hour_index) % 10
    hour_branch_idx = hour_index % 12
    
    return gan[hour_stem_idx], zhi[hour_branch_idx]

# Run verification
print("=== DETAILED VERIFICATION FOR OCTOBER 9, 1966 ===")
astron_result, trad_result = verify_day_pillar_1966()

print(f"\nAstronomical result: {astron_result[0]}{astron_result[1]} (index {astron_result[2]})")
print(f"Traditional result:  {trad_result[0]}{trad_result[1]} (index {trad_result[2]})")

# Calculate hour pillar for 7 AM with traditional day
day_stem = trad_result[0]
hour_stem, hour_branch = calculate_hour_pillar_correctly(day_stem, 7)
print(f"\nHour pillar for {day_stem} day at 07:00: {hour_stem}{hour_branch}")

print(f"\nFinal calculated BaZi: 丙午 戊戌 {trad_result[0]}{trad_result[1]} {hour_stem}{hour_branch}")
print(f"Claimed authoritative:  丙午 戊戌 丁卯 癸卯")

print(f"\nNote: Historical calendar calculations can vary due to:")
print(f"1. Different astronomical models used historically")
print(f"2. Regional variations in calendar systems")
print(f"3. Different methods for handling leap years")
print(f"4. Corrections made to calendars over time")
print(f"5. Potential errors in various sources")



