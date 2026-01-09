from datetime import datetime
from app.bazi.report import generate_full_report
import json

dt_test = datetime(1977,7,7,7,0)
report = generate_full_report(dt_test, gender="Male", location="Asia/Hong_Kong", year="2026", llm="qw", lang="cn")

print(json.dumps(report, indent=2, ensure_ascii=False))
