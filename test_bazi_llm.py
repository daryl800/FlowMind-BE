# test_bazi_llm.py
from datetime import datetime
from bazi_llm import generate_bazi_narrative_safe
import json
import time

# -----------------------------
# Sample BaZi Inputs for Testing
# -----------------------------
sample_inputs = [
    {
        "datetime": "1991-06-12T09:00:00",
        "gender": "Male",
        "location": "Europe/London",
        "year": "2027",
        "pillars": {
            "year": {"gan": "Xin", "zhi": "Si"},
            "month": {"gan": "Bing", "zhi": "Wu"},
            "day": {"gan": "Gui", "zhi": "Wu"},
            "hour": {"gan": "Ding", "zhi": "You"},
        },
        "day_master": "Gui",
        "five_elements_strength": {"Wood": 0, "Fire": 2, "Earth": 1, "Metal": 2, "Water": 1}
    },
    {
        "datetime": "1993-04-08T10:30:00",
        "gender": "Female",
        "location": "Asia/Hong_Kong",
        "year": "2027",
        "pillars": {
            "year": {"gan": "Gui", "zhi": "Mao"},
            "month": {"gan": "Bing", "zhi": "Chen"},
            "day": {"gan": "Ji", "zhi": "Wei"},
            "hour": {"gan": "Ding", "zhi": "Mao"},
        },
        "day_master": "Ji",
        "five_elements_strength": {"Wood": 1, "Fire": 2, "Earth": 2, "Metal": 0, "Water": 1}
    },
    {
        "datetime": "1966-10-09T07:00:00",
        "gender": "Male",
        "location": "Asia/Hong_Kong",
        "year": "2027",
        "pillars": {
            "year": {"gan": "Bing", "zhi": "Wu"},
            "month": {"gan": "Wu", "zhi": "Xu"},
            "day": {"gan": "Xin", "zhi": "Chou"},
            "hour": {"gan": "Ren", "zhi": "Chen"},
        },
        "day_master": "Xin",
        "five_elements_strength": {"Wood": 0, "Fire": 3, "Earth": 3, "Metal": 1, "Water": 1}
    }
]

# -----------------------------
# Retry Wrapper
# -----------------------------
def generate_with_retry(bazi_data, lang="en", retries=2, delay=1):
    for attempt in range(1, retries + 1):
        report = generate_bazi_narrative_safe(bazi_data, llm="hunyuan", lang=lang)
        if "error" not in report:
            return report
        print(f"⚠ Attempt {attempt} failed, retrying in {delay}s...")
        time.sleep(delay)
    # Return last attempt even if it failed
    return report

# -----------------------------
# Run LLM on Each Sample
# -----------------------------
for i, bazi in enumerate(sample_inputs, 1):
    print(f"\n=== Test Case #{i} ===")
    print(f"DateTime: {bazi['datetime']}, Gender: {bazi['gender']}, Location: {bazi['location']}")
    
    report = generate_with_retry(bazi, lang="en", retries=3, delay=2)
    
    if "error" in report:
        print("❌ LLM JSON Parsing Error after retries")
        print(report["raw"])
    else:
        print("✅ LLM Output Parsed Successfully")
        print(json.dumps(report, indent=4, ensure_ascii=False))
