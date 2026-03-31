# test_bazi_llm.py
from datetime import datetime
from app.llm.bazi_llm import generate_bazi_narrative_safe
import json
import time

# -----------------------------
# Sample BaZi Inputs for Testing
# -----------------------------
sample_inputs = [
    {
        "gender": "Male",
        "pillars": {
            "year": {"gan": "Bing", "zhi": "Wu"},
            "month": {"gan": "Wu", "zhi": "Xu"},
            "day": {"gan": "Xin", "zhi": "Chou"},
            "hour": {"gan": "Xin", "zhi": "Mao"},
        },
        "day_master": "Xin",
        "five_elements_strength": {            
            "Wood": 1.0,
            "Fire": 3.3,
            "Earth": 1.0,
            "Metal": 2.4,
            "Water": 0.3
        },        
        "year": "2026"
    }
]

# -----------------------------
# Retry Wrapper
# -----------------------------
def generate_with_retry(bazi_data, target_year="2026", llm="openai", lang="en", retries=2, delay=1):
    for attempt in range(1, retries + 1):
        report = generate_bazi_narrative_safe(bazi_data, target_year=target_year, llm=llm, lang=lang)
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
    
    llm = "qianwen"  # Change as needed: "openai", "qianwen", "hunyuan"
    lang = "cn"

    print(f"\n=== Test Case LLM: #{llm} ===")

    report = generate_with_retry(bazi, target_year="2026", llm=llm, lang=lang, retries=3, delay=2)
    
    if "error" in report:
        print("❌ LLM JSON Parsing Error after retries")
        print(report["raw"])
    else:
        print("✅ LLM Output Parsed Successfully")
        print(json.dumps(report, indent=4, ensure_ascii=False))
