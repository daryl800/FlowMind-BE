from datetime import datetime
from bazi_report import generate_full_report
import json

dt_test = datetime(1966,10,9,7,0)
report = generate_full_report(dt_test, gender="Male", location="Asia/Hong_Kong")

print(json.dumps(report, indent=2, ensure_ascii=False))
