from datetime import datetime
from zoneinfo import ZoneInfo
from app.bazi.report import generate_full_report

# ------------------------------
# Test cases: (name, datetime, tz, gender, expected_day_master)
# ------------------------------
TEST_CASES = [
    ("Male Example", datetime(1991, 6, 12, 9, 0), "Asia/Hong_Kong", "Male"),
    ("Female Example", datetime(1992, 8, 22, 9, 15), "Asia/Hong_Kong", "Female"),
    ("Evening Birth", datetime(1988, 11, 3, 22, 0), "Asia/Hong_Kong", "Male"),
    ("Wood Test", datetime(1993, 4, 8, 10, 30), "Asia/Hong_Kong", "Male"),
    ("Fire Test", datetime(1989, 7, 15, 14, 45), "Asia/Hong_Kong", "Male"),
    ("Earth Test", datetime(1990, 2, 20, 8, 20), "Asia/Hong_Kong", "Male"),
    ("Metal Test", datetime(1994, 12, 5, 7, 10), "Asia/Hong_Kong", "Male"),
    ("Water Test", datetime(1966, 10, 9, 7, 0), "Asia/Hong_Kong", "Male"),
]

def test_bazi_pipeline(generate_report_fn, run_llm=False):
    """
    generate_report_fn: function to generate full report
    run_llm: True to also call LLM narrative (slower)
    """
    print("\n=== BaZi Pipeline Accuracy Test ===\n")

    for name, dt, tz_name, gender, expected_dm in TEST_CASES:
        try:
            report = generate_report_fn(dt, gender=gender, location=tz_name)
            calculated_dm = report["bazi_basic"]["day_master"]

            ok = "✅" if calculated_dm == expected_dm else "❌"

            print(f"{name}")
            print(f"  Input datetime: {dt} ({tz_name})")
            print(f"  Expected Day Master: {expected_dm}")
            print(f"  Calculated Day Master: {calculated_dm} {ok}")
            print(f"  Five Elements Strength: {report['bazi_basic']['five_elements_strength']}")
            
            if run_llm:
                if "error" in report:
                    print(f"  LLM error: {report['error']}")
                else:
                    print(f"  LLM narrative keys: {list(report.keys())}")
            print("-" * 50)

        except Exception as e:
            print(f"{name} - ERROR: {str(e)}")
            print("-" * 50)


# ------------------------------
# Example usage:
# ------------------------------
if __name__ == "__main__":
    # Replace generate_full_report with your function
    test_bazi_pipeline(generate_full_report, run_llm=False)
