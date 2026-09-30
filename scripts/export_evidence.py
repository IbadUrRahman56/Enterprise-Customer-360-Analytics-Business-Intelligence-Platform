"""Export bounded analytics for the technical presentation and reproducibility receipt."""
import json
from datetime import date
from customer360.analytics import Analytics, Scope, forecast
from customer360.config import WAREHOUSE, OUTPUT

api=Analytics(WAREHOUSE)
meta=api.metadata()
scope=Scope(date(2025,9,1),date(2026,8,31))
trend=api.trend(scope)
future,diagnostics=forecast(trend,scope)
def records(df): return json.loads(df.to_json(orient="records",date_format="iso"))
evidence={"metadata":{k:v for k,v in meta.items() if k!="source_directory"},
 "scope":{"start":str(scope.start),"end":str(scope.end)},"metrics":api.metrics(scope),
 "retention":api.retention(scope),"segments":records(api.segments(scope)),"monthly":records(trend),
 "countries":records(api.breakdown(scope,"country")),"forecast":records(future),"diagnostics":diagnostics,
 "quality":records(api.query("SELECT * FROM data_quality"))}
OUTPUT.mkdir(exist_ok=True)
(OUTPUT/"demo-evidence.json").write_text(json.dumps(evidence,indent=2))
print("Saved output/demo-evidence.json")
