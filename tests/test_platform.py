from datetime import date
import json
import os
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from customer360.demo import generate
from customer360.pipeline import build, clean_source
from customer360.analytics import Analytics, Scope, forecast, hypothesis, anomalies
from customer360.security import hash_password, verify, allowed, authenticate
from customer360.reports import reporting_scope, report_bytes


@pytest.fixture(scope="module")
def warehouse(tmp_path_factory):
    root=tmp_path_factory.mktemp("warehouse")
    generate(root/"raw",120,3000)
    build(root/"raw",root)
    return root


@pytest.fixture
def api(warehouse): return Analytics(warehouse/"warehouse.duckdb")


def test_sales_reconcile_to_independent_source(warehouse,api):
    raw=pd.read_csv(warehouse/"raw"/"pos_orders.csv").drop_duplicates("order_id")
    expected=raw[(raw.status=="Completed")&(raw.customer_id<=120)&(raw.revenue_usd>=0)]
    scope=Scope(date(2024,1,1),date(2026,8,31))
    m=api.metrics(scope)
    assert m["revenue"]==pytest.approx(expected.revenue_usd.sum(),abs=.01)
    assert m["orders"]==len(expected)
    assert m["buyers"]==expected.customer_id.nunique()
    assert sum(api.breakdown(scope,"category").revenue)==pytest.approx(m["revenue"])
    assert api.trend(scope).revenue.sum()==pytest.approx(m["revenue"])


def test_quality_quarantine_and_duplicate_counts(api):
    q=api.query("SELECT * FROM data_quality WHERE source='pos_orders'").iloc[0]
    assert q.duplicate_rows==20
    assert q.invalid_rows==1
    assert q.integration_rejected==1
    assert api.query("SELECT rejection_reason FROM rejected_orders").iloc[0,0]=="orphan_dimension"


def test_filter_consistency_and_sql_injection(api):
    scope=Scope(date(2026,1,1),date(2026,8,31),"GB","Web")
    m=api.metrics(scope)
    assert api.breakdown(scope,"category").revenue.sum()==pytest.approx(m["revenue"])
    assert api.metrics(Scope(scope.start,scope.end,"US' OR 1=1 --"))["orders"]==0
    with pytest.raises(ValueError): api.breakdown(scope,"revenue; DROP TABLE fact_sales")


def test_retention_matches_customer_sets(api):
    scope=Scope(date(2026,6,1),date(2026,6,30))
    prior,_=api.previous(scope)
    w,p=scope.where(); pw,pp=prior.where()
    current=set(api.query(f"SELECT customer_id FROM fact_sales WHERE {w}",p).customer_id)
    old=set(api.query(f"SELECT customer_id FROM fact_sales WHERE {pw}",pp).customer_id)
    r=api.retention(scope)
    assert r["retained"]==len(current&old)
    assert r["eligible"]==len(old)
    assert api.retention(Scope(date(2024,1,1),date(2024,1,31)))["rate"] is None


def test_snapshot_has_no_future_leakage(api):
    scope=Scope(date(2024,1,1),date(2024,6,30))
    customers=api.customer_list(scope)
    assert (customers.signup_date.dt.date<=scope.end).all()
    assert (customers.last_order.dropna().dt.date<=scope.end).all()
    assert api.segments(scope).revenue.sum()==pytest.approx(api.metrics(scope)["revenue"])
    assert customers.r_score.between(0,5).all()


def test_customer_growth_query_returns_registration_months(api):
    growth=api.growth(Scope(date(2025,1,1),date(2026,8,31)))
    assert {"signup_month","new_customers"}.issubset(growth.columns)
    assert len(growth)>0


def test_cohort_maturity_and_month_zero(api):
    scope=Scope(date(2025,1,1),date(2026,8,15))
    cohorts=api.cohorts(scope)
    assert (cohorts.loc[cohorts.age==0,"retention"]==1).all()
    assert cohorts.retention.between(0,1).all()
    for row in cohorts.itertuples():
        assert row.cohort+pd.DateOffset(months=int(row.age))<=pd.Timestamp("2026-07-01")


def test_marketing_reconciliation_and_partial_months(api):
    scope=Scope(date(2026,1,15),date(2026,8,15),"US","Web")
    df,start,end=api.marketing(scope)
    assert start==date(2026,2,1) and end==date(2026,7,31)
    expected=api.query("SELECT sum(revenue) n FROM fact_sales WHERE campaign_id!=0 AND order_date BETWEEN ? AND ?",[start,end]).iloc[0,0]
    assert df.attributed_revenue.sum()==pytest.approx(expected)
    assert len(df)==18
    empty,_,_=api.marketing(Scope(date(2026,8,5),date(2026,8,8)))
    assert empty.empty


def test_forecast_excludes_partial_month_and_bounds(api):
    scope=Scope(date(2024,1,1),date(2026,8,15))
    future,diag=forecast(api.trend(scope),scope)
    assert diag["training_months"]==31
    assert future.period.min()==pd.Timestamp("2026-08-01")
    assert len(future)==6
    assert (future.lower<=future.forecast).all() and (future.forecast<=future.upper).all()
    assert (future.lower>=0).all()
    short=Scope(date(2026,1,1),date(2026,8,31))
    assert forecast(api.trend(short),short)[0].empty


def test_empty_scope_and_zero_denominators(api):
    scope=Scope(date(2026,1,1),date(2026,1,1),"not-a-country")
    m=api.metrics(scope)
    assert m["orders"]==0 and m["aov"] is None and m["repeat_rate"] is None
    assert api.segments(scope).empty
    assert not anomalies(api.trend(scope,"day")).anomaly.any()


def test_reports_and_cadence(api):
    scope=reporting_scope(date(2026,8,31),"quarterly")
    assert scope.start==date(2026,7,1)
    data=report_bytes(api,scope,"quarterly")
    assert data.startswith(b"%PDF")
    from pypdf import PdfReader
    import io
    reader=PdfReader(io.BytesIO(data))
    assert len(reader.pages)==2
    assert "SYNTHETIC" in reader.pages[0].extract_text()


def test_security(monkeypatch):
    hashed=hash_password("correct horse")
    assert verify("correct horse",hashed) and not verify("wrong",hashed)
    assert not verify("x","broken")
    monkeypatch.setenv("C360_USERS_JSON",json.dumps({"alice":{"role":"viewer","password_hash":hashed}}))
    assert authenticate("alice","correct horse")=="viewer"
    assert authenticate("unknown","x") is None
    assert not allowed("viewer","export") and not allowed("analyst","quality")


def test_conflicting_keys_fail_without_replacing(warehouse,api):
    root=warehouse/"conflict"; root.mkdir(exist_ok=True)
    path=root/"customers.csv"
    path.write_text("customer_id,country,signup_date,loyalty_tier\n1,US,2024-01-01,Gold\n1,GB,2024-01-01,Gold\n")
    with pytest.raises(ValueError,match="conflicting"):
        clean_source("crm_customers",path,root)


def test_idempotent_build(warehouse,api):
    before=api.query("SELECT sum(revenue) revenue,count(*) n FROM fact_sales")
    build(warehouse/"raw",warehouse)
    after=api.query("SELECT sum(revenue) revenue,count(*) n FROM fact_sales")
    pd.testing.assert_frame_equal(before,after)


def test_hypothesis_uses_customer_units(api):
    data=api.customer_statistics(Scope(date(2024,1,1),date(2026,8,31)))
    assert data.customer_id.is_unique
    result=hypothesis(data)
    assert result["available"]
    assert 0<=result["p_value"]<=1
    assert result["lower"]<=result["difference"]<=result["upper"]
