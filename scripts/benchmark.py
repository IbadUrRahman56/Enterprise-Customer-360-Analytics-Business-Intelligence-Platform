"""Measure current hardware and warehouse. Does not claim enterprise capacity."""
import json
import platform
import statistics
import time
from datetime import date
from customer360.analytics import Analytics, Scope
from customer360.config import WAREHOUSE, OUTPUT

api=Analytics(WAREHOUSE)
meta=api.metadata()
scope=Scope(date.fromisoformat(meta["coverage_start"]),date.fromisoformat(meta["coverage_end"]))
timings={}
for name,query in {"metrics":lambda:api.metrics(scope),"segments":lambda:api.segments(scope),"cohorts":lambda:api.cohorts(scope)}.items():
    durations=[]
    for _ in range(5):
        start=time.perf_counter(); query(); durations.append((time.perf_counter()-start)*1000)
    timings[name]={"milliseconds":durations,"median_ms":statistics.median(durations),"max_ms":max(durations)}
record={"platform":platform.platform(),"python":platform.python_version(),"rows":int(api.query("SELECT count(*) n FROM fact_sales").iloc[0,0]),"run_id":meta["run_id"],"concurrent_users":1,"timings":timings,"note":"Five local sequential samples; not an enterprise load test or p95 estimate."}
OUTPUT.mkdir(exist_ok=True)
(OUTPUT/"benchmark.json").write_text(json.dumps(record,indent=2))
print(json.dumps(record,indent=2))
