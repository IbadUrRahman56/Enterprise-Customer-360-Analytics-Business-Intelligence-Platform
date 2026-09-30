"""CSV/Parquet batch ingestion with streaming cleaning and an atomic warehouse build."""
import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
import duckdb
import polars as pl
from .config import COUNTRIES

SCHEMAS = {
 "crm_customers":{"customer_id":"int","country":"str","signup_date":"date","loyalty_tier":"str"},
 "erp_products":{"product_id":"int","product_name":"str","category":"str","unit_price_usd":"float","unit_cost_usd":"float"},
 "erp_stores":{"store_id":"int","country":"str","store_name":"str"},
 "pos_orders":{"order_id":"int","customer_id":"int","product_id":"int","store_id":"int","order_date":"date","quantity":"int","revenue_usd":"float","cost_usd":"float","channel":"str","campaign_id":"int","status":"str"},
 "payment_orders":{"order_id":"int","amount_usd":"float","payment_status":"str"},
 "marketing_campaigns":{"campaign_id":"int","month":"date","channel":"str","spend_usd":"float"},
 "website_sessions":{"session_id":"str","customer_id":"int","event_date":"date","viewed":"int","checkout":"int","purchased":"int"},
 "mobile_sessions":{"session_id":"str","customer_id":"int","event_date":"date","viewed":"int","checkout":"int","purchased":"int"},
 "email_campaigns":{"campaign_id":"int","sent":"int","opened":"int","clicked":"int"},
 "social_campaigns":{"campaign_id":"int","impressions":"int","engagements":"int"},
 "support_tickets":{"ticket_id":"int","customer_id":"int","opened_date":"date","resolution_hours":"float","csat":"int"},
}


def quote(path):
    return "'" + str(path).replace("'", "''") + "'"


def fingerprint(path):
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024*1024), b""): digest.update(block)
    return digest.hexdigest()


def clean_source(name, path, target):
    schema=SCHEMAS[name]
    df=pl.scan_parquet(path) if path.suffix==".parquet" else pl.scan_csv(path,infer_schema=False)
    missing=set(schema)-set(df.collect_schema().names())
    if missing: raise ValueError(f"{name}: missing columns {sorted(missing)}")
    expr=[]
    for col,kind in schema.items():
        value=pl.col(col).cast(pl.String).str.strip_chars()
        if kind=="int": value=value.cast(pl.Int64,strict=False)
        elif kind=="float": value=value.cast(pl.Float64,strict=False)
        elif kind=="date": value=value.str.slice(0,10).str.to_date("%Y-%m-%d",strict=False)
        expr.append(value.alias(col))
    df=df.select(expr)
    if "country" in schema: df=df.with_columns(pl.col("country").str.to_uppercase())
    if name=="crm_customers": df=df.with_columns(pl.col("loyalty_tier").fill_null("Unknown"))
    key=next(iter(schema))
    rules=[pl.any_horizontal([pl.col(c).is_null() for c in schema])]
    rules += [pl.col(c)<0 for c,k in schema.items() if k in ("int","float")]
    rules += [~pl.col(c).is_finite() for c,k in schema.items() if k=="float"]
    rules += [pl.col(c).str.len_chars()==0 for c,k in schema.items() if k=="str"]
    if schema[key]=="int": rules.append(pl.col(key)<=0)
    if "country" in schema: rules.append(~pl.col("country").is_in(COUNTRIES))
    if name=="pos_orders": rules += [pl.col("quantity")<=0,~pl.col("status").is_in(["Completed","Refunded","Cancelled"]),~pl.col("channel").is_in(["Store","Web","App"])]
    if name=="payment_orders": rules.append(~pl.col("payment_status").is_in(["Settled","Refunded","Voided"]))
    if name=="marketing_campaigns": rules += [pl.col("month").dt.day()!=1, ~pl.col("channel").is_in(["Email","Paid search","Social"])]
    if name.endswith("sessions"): rules += [pl.col("viewed")!=1,pl.col("checkout")>pl.col("viewed"),pl.col("purchased")>pl.col("checkout")]
    if name=="email_campaigns": rules += [pl.col("opened")>pl.col("sent"),pl.col("clicked")>pl.col("opened")]
    if name=="social_campaigns": rules += [pl.col("engagements")>pl.col("impressions")]
    if name=="support_tickets": rules += [pl.col("csat")<1,pl.col("csat")>5]
    invalid=pl.any_horizontal(rules).fill_null(True)
    total=df.select(pl.len()).collect().item()
    rejected=df.filter(invalid)
    n_invalid=rejected.select(pl.len()).collect().item()
    rejected.with_columns(pl.lit("schema_or_value").alias("rejection_reason")).sink_parquet(target/f"{name}_rejected.parquet")
    valid=df.filter(~invalid)
    # Conflicting versions cannot be resolved without a source update timestamp.
    # Identical duplicates are safe to collapse; conflicting keys fail the build.
    unique=valid.unique(maintain_order=False)
    conflicts=unique.group_by(key).len().filter(pl.col("len")>1).limit(1).collect()
    if len(conflicts): raise ValueError(f"{name}: conflicting records for key {conflicts[key][0]}; supply a resolved snapshot")
    unique.sink_parquet(target/f"{name}.parquet")
    retained=pl.scan_parquet(target/f"{name}.parquet").select(pl.len()).collect().item()
    return {"source":name,"input_rows":total,"invalid_rows":n_invalid,"duplicate_rows":total-n_invalid-retained,"clean_rows":retained,"sha256":fingerprint(path)}


def build(source: Path, data: Path):
    manifest=json.loads((source/"manifest.json").read_text())
    if manifest.get("currency")!="USD" or manifest.get("timezone")!="UTC":
        raise ValueError("Input contract requires USD-normalized values and UTC dates")
    if manifest.get("classification") not in ("synthetic","real"):
        raise ValueError("Manifest classification must be synthetic or real")
    start,end=manifest["coverage_start"],manifest["coverage_end"]
    from datetime import date
    if date.fromisoformat(start)>date.fromisoformat(end): raise ValueError("Invalid coverage window")
    run=uuid.uuid4().hex[:12]
    staging=data/"runs"/run
    staging.mkdir(parents=True)
    quality=[]
    for name in SCHEMAS:
        path=source/f"{name}.parquet"
        if not path.exists(): path=source/f"{name}.csv"
        if not path.exists(): raise ValueError(f"Missing source: {name}.csv or .parquet")
        quality.append(clean_source(name,path,staging))
    db=staging/"warehouse.duckdb"
    con=duckdb.connect(str(db))
    try:
        con.execute("SET memory_limit='1GB'")
        con.execute(f"SET temp_directory={quote(staging/'spill')}")
        con.execute("SET threads=4")
        for name in SCHEMAS:
            con.execute(f"CREATE TABLE {name} AS SELECT * FROM read_parquet({quote(staging/f'{name}.parquet')})")
        # Reject orphan auxiliary facts so joins cannot manufacture or lose totals silently.
        for name in ["website_sessions","mobile_sessions","support_tickets"]:
            datecol="opened_date" if name=="support_tickets" else "event_date"
            con.execute(f"CREATE TABLE rejected_{name} AS SELECT a.* FROM {name} a LEFT JOIN crm_customers c USING(customer_id) WHERE c.customer_id IS NULL OR a.{datecol} < c.signup_date OR a.{datecol} NOT BETWEEN ?::DATE AND ?::DATE",[start,end])
            key=next(iter(SCHEMAS[name]))
            con.execute(f"DELETE FROM {name} WHERE {key} IN (SELECT {key} FROM rejected_{name})")
        for name in ["email_campaigns","social_campaigns"]:
            expected="Email" if name.startswith("email") else "Social"
            con.execute(f"CREATE TABLE rejected_{name} AS SELECT a.* FROM {name} a LEFT JOIN marketing_campaigns m USING(campaign_id) WHERE m.campaign_id IS NULL OR m.channel != ?",[expected])
            con.execute(f"DELETE FROM {name} WHERE campaign_id IN (SELECT campaign_id FROM rejected_{name})")
        con.execute("CREATE TABLE rejected_payment_orders AS SELECT p.* FROM payment_orders p LEFT JOIN pos_orders o USING(order_id) WHERE o.order_id IS NULL")
        con.execute("DELETE FROM payment_orders WHERE order_id IN (SELECT order_id FROM rejected_payment_orders)")
        con.execute("""CREATE TABLE order_validation AS
            SELECT o.*, CASE WHEN c.customer_id IS NULL OR p.product_id IS NULL OR s.store_id IS NULL THEN 'orphan_dimension'
            WHEN o.order_date < c.signup_date THEN 'before_signup'
            WHEN o.order_date NOT BETWEEN ?::DATE AND ?::DATE THEN 'outside_coverage'
            WHEN o.campaign_id != 0 AND (m.campaign_id IS NULL OR date_trunc('month',o.order_date)!=m.month) THEN 'invalid_campaign'
            WHEN pay.order_id IS NULL OR abs(pay.amount_usd-o.revenue_usd)>.01 THEN 'payment_mismatch'
            WHEN (o.status='Completed' AND pay.payment_status!='Settled') OR (o.status='Refunded' AND pay.payment_status!='Refunded')
                OR (o.status='Cancelled' AND pay.payment_status!='Voided') THEN 'payment_status'
            ELSE NULL END AS rejection_reason
            FROM pos_orders o LEFT JOIN crm_customers c USING(customer_id)
            LEFT JOIN erp_products p USING(product_id) LEFT JOIN erp_stores s USING(store_id)
            LEFT JOIN marketing_campaigns m USING(campaign_id) LEFT JOIN payment_orders pay USING(order_id)""",[start,end])
        con.execute("CREATE TABLE rejected_orders AS SELECT * FROM order_validation WHERE rejection_reason IS NOT NULL")
        con.execute("""CREATE TABLE fact_sales AS SELECT o.* EXCLUDE(rejection_reason),
            CAST(o.revenue_usd AS DECIMAL(18,2)) AS revenue,
            CAST(o.cost_usd AS DECIMAL(18,2)) AS cost,
            c.country, c.loyalty_tier, p.category, p.product_name, s.store_name,
            s.country AS store_country, date_trunc('month',o.order_date)::DATE AS month
            FROM order_validation o JOIN crm_customers c USING(customer_id)
            JOIN erp_products p USING(product_id) JOIN erp_stores s USING(store_id)
            WHERE o.rejection_reason IS NULL AND o.status='Completed'""")
        con.execute("CREATE TABLE fact_sessions AS SELECT *, 'Web' AS channel FROM website_sessions UNION ALL SELECT *, 'App' AS channel FROM mobile_sessions")
        con.execute("CREATE TABLE daily_sales AS SELECT order_date,country,channel,category,count(*) AS orders,sum(revenue) AS revenue,sum(cost) AS cost FROM fact_sales GROUP BY ALL")
        con.execute("CREATE INDEX sales_date ON fact_sales(order_date)")
        con.execute("CREATE INDEX sales_customer ON fact_sales(customer_id)")
        for q in quality:
            rejected=f"rejected_{q['source']}"
            exists=con.execute("SELECT count(*) FROM information_schema.tables WHERE table_name=?",[rejected]).fetchone()[0]
            q["integration_rejected"]=con.execute(f"SELECT count(*) FROM {rejected}").fetchone()[0] if exists else 0
        next(q for q in quality if q["source"]=="pos_orders")["integration_rejected"]=con.execute("SELECT count(*) FROM rejected_orders").fetchone()[0]
        import pandas as pd
        quality_df=pd.DataFrame(quality)
        con.register("quality_df",quality_df)
        con.execute("CREATE TABLE data_quality AS SELECT * FROM quality_df")
        manifest.update({"run_id":run,"built_at":datetime.now(timezone.utc).isoformat(),"sources":quality,
            "source_directory":str(source.resolve()),"pipeline_version":"1.0.0"})
        con.execute("CREATE TABLE metadata (json VARCHAR)")
        con.execute("INSERT INTO metadata VALUES (?)",[json.dumps(manifest)])
        con.execute("DROP TABLE order_validation")
        con.execute("CHECKPOINT")
    finally: con.close()
    # A failed build never replaces the last successful warehouse.
    os.replace(db,data/"warehouse.duckdb")
    (staging/"manifest.json").write_text(json.dumps(manifest,indent=2))
    return manifest
