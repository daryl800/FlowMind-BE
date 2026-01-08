from datetime import datetime
from app.bazi.engine import calc_bazi
from app.llm.bazi_llm import generate_bazi_narrative_safe
from app.llm.bazi_llm import enrich_with_localized_pillars

def generate_full_report(dt: "datetime", gender="Male", location="Asia/Hong_Kong", year="2026", llm="openai", lang="en"):
    bazi = calc_bazi(dt, tz_name=location)
    narrative = generate_bazi_narrative_safe(bazi, llm=llm, lang=lang)
    report = {"bazi_basic": {**bazi, "datetime": dt.isoformat(), "gender": gender, "location": location}}
    report.update(narrative)

    # enrich pillars for requested language
    if "bazi_basic" in report:
        enrich_with_localized_pillars(report["bazi_basic"], lang=lang)
    
    return report
