"""Parameterized SQL measures shared by dashboard, reports and tests."""
from dataclasses import dataclass, replace
from datetime import date, timedelta
import json
from pathlib import Path
import duckdb
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.tsa.holtwinters import ExponentialSmoothing


@dataclass(frozen=True)
class Scope:
    start: date
    end: date
    country: str = "All"
    channel: str = "All"

    def __post_init__(self):
        if self.start > self.end: raise ValueError("Start must not be after end")

    def where(self, history=False):
        clauses=["order_date <= ?"]
        params=[self.end]
        if not history: clauses.append("order_date >= ?"); params.append(self.start)
        if self.country!="All": clauses.append("country = ?"); params.append(self.country)
        if self.channel!="All": clauses.append("channel = ?"); params.append(self.channel)
        return " AND ".join(clauses),params


def ratio(n,d): return float(n)/float(d) if d else None


class Analytics:
    def __init__(self, path: Path): self.path=Path(path)

    def query(self,sql,params=None):
        with duckdb.connect(str(self.path),read_only=True) as con:
            return con.execute(sql,params or []).fetchdf()

    def metadata(self): return json.loads(self.query("SELECT json FROM metadata").iloc[0,0])

    def metrics(self,scope):
        w,p=scope.where()
        row=self.query(f"SELECT coalesce(sum(revenue),0) revenue,coalesce(sum(revenue-cost),0) gross_profit,count(*) orders,count(DISTINCT customer_id) buyers FROM fact_sales WHERE {w}",p).iloc[0].to_dict()
        repeat=self.query(f"SELECT count(*) n FROM (SELECT customer_id FROM fact_sales WHERE {w} GROUP BY customer_id HAVING count(*)>=2)",p).iloc[0,0]
        row.update(aov=ratio(row["revenue"],row["orders"]),repeat_rate=ratio(repeat,row["buyers"]),margin=ratio(row["gross_profit"],row["revenue"]))
        return row

    def previous(self,scope):
        days=(scope.end-scope.start).days+1
        previous=replace(scope,start=scope.start-timedelta(days=days),end=scope.start-timedelta(days=1))
        if previous.start < date.fromisoformat(self.metadata()["coverage_start"]): return None,None
        return previous,self.metrics(previous)

    def retention(self,scope):
        prev,_=self.previous(scope)
        if prev is None: return {"rate":None,"retained":0,"eligible":0}
        w,p=scope.where(); pw,pp=prev.where()
        row=self.query(f"WITH prior AS (SELECT DISTINCT customer_id FROM fact_sales WHERE {pw}), current AS (SELECT DISTINCT customer_id FROM fact_sales WHERE {w}) SELECT count(c.customer_id) retained,count(*) eligible FROM prior a LEFT JOIN current c USING(customer_id)",pp+p).iloc[0]
        return {"rate":ratio(row.retained,row.eligible),"retained":int(row.retained),"eligible":int(row.eligible)}

    def trend(self,scope,grain="month"):
        if grain not in ("month","day"): raise ValueError("Unsupported grain")
        w,p=scope.where()
        df=self.query(f"SELECT date_trunc('{grain}',order_date)::DATE period,sum(revenue)::DOUBLE revenue,count(*) orders FROM fact_sales WHERE {w} GROUP BY 1 ORDER BY 1",p)
        start=pd.Timestamp(scope.start).to_period("M").start_time if grain=="month" else pd.Timestamp(scope.start)
        idx=pd.date_range(start,scope.end,freq="MS" if grain=="month" else "D")
        return df.set_index("period").reindex(idx,fill_value=0).rename_axis("period").reset_index()

    def breakdown(self,scope,dimension):
        if dimension not in {"country","category","product_name","store_name","channel","loyalty_tier"}: raise ValueError("Invalid dimension")
        w,p=scope.where()
        return self.query(f"SELECT {dimension},sum(revenue)::DOUBLE revenue,sum(revenue-cost)::DOUBLE gross_profit,count(*) orders,count(DISTINCT customer_id) buyers FROM fact_sales WHERE {w} GROUP BY 1 ORDER BY revenue DESC",p)

    def customer_cte(self,scope):
        w,p=scope.where(history=True)
        country="AND c.country=?" if scope.country!="All" else ""
        sql=f"""WITH agg AS (SELECT customer_id, count(*) frequency, sum(revenue)::DOUBLE monetary,
            sum(revenue-cost)::DOUBLE profit,min(order_date) first_order,max(order_date) last_order
            FROM fact_sales WHERE {w} GROUP BY 1), customers AS (
            SELECT c.*,coalesce(a.frequency,0) frequency,coalesce(a.monetary,0) monetary,
            coalesce(a.profit,0) profit,a.first_order,a.last_order,date_diff('day',a.last_order,?::DATE) recency,
            CASE WHEN a.customer_id IS NULL THEN 'No purchases' WHEN date_diff('day',a.last_order,?::DATE)>90 THEN 'At risk'
                WHEN a.frequency>=10 AND a.monetary>=3000 THEN 'Champions' WHEN a.frequency>=3 THEN 'Loyal' ELSE 'Developing' END segment,
            CASE WHEN a.last_order IS NULL THEN 0 WHEN date_diff('day',a.last_order,?::DATE)<=30 THEN 5
                WHEN date_diff('day',a.last_order,?::DATE)<=60 THEN 4 WHEN date_diff('day',a.last_order,?::DATE)<=90 THEN 3
                WHEN date_diff('day',a.last_order,?::DATE)<=180 THEN 2 ELSE 1 END r_score,
            CASE WHEN a.frequency>=20 THEN 5 WHEN a.frequency>=10 THEN 4 WHEN a.frequency>=5 THEN 3 WHEN a.frequency>=2 THEN 2 WHEN a.frequency=1 THEN 1 ELSE 0 END f_score,
            CASE WHEN a.monetary>=5000 THEN 5 WHEN a.monetary>=3000 THEN 4 WHEN a.monetary>=1000 THEN 3 WHEN a.monetary>=300 THEN 2 WHEN a.monetary>0 THEN 1 ELSE 0 END m_score,
            CASE WHEN a.customer_id IS NULL THEN 0 ELSE a.profit/greatest(date_diff('day',a.first_order,?::DATE)+1,90)*365 END annual_value_proxy
            FROM crm_customers c LEFT JOIN agg a USING(customer_id) WHERE c.signup_date<=?::DATE {country})"""
        params=p+[scope.end]*8+([scope.country] if scope.country!="All" else [])
        return sql,params

    def segments(self,scope):
        c,p=self.customer_cte(scope)
        return self.query(c+" SELECT segment,count(*) customers,sum(monetary) revenue,avg(recency) recency_days,avg(annual_value_proxy) annual_value_proxy FROM customers GROUP BY 1 ORDER BY revenue DESC",p)

    def customer_list(self,scope,segment="All",limit=1000):
        c,p=self.customer_cte(scope)
        cond="WHERE segment=?" if segment!="All" else ""
        return self.query(c+f" SELECT * FROM customers {cond} ORDER BY monetary DESC,customer_id LIMIT ?",p+([segment] if segment!="All" else [])+[min(int(limit),5000)])

    def profile(self,scope,customer_id):
        c,p=self.customer_cte(scope)
        profile=self.query(c+" SELECT * FROM customers WHERE customer_id=?",p+[int(customer_id)])
        w,params=scope.where(history=True)
        orders=self.query(f"SELECT order_id,order_date,product_name,channel,revenue FROM fact_sales WHERE {w} AND customer_id=? ORDER BY order_date DESC LIMIT 100",params+[int(customer_id)])
        tickets=self.query("SELECT count(*) tickets,avg(resolution_hours) resolution_hours,avg(csat) csat FROM support_tickets WHERE customer_id=? AND opened_date<=?",[int(customer_id),scope.end])
        activity=self.query("SELECT channel,count(*) sessions,sum(checkout) checkouts,sum(purchased) purchases FROM fact_sessions WHERE customer_id=? AND event_date<=? GROUP BY 1",[int(customer_id),scope.end])
        return profile,orders,tickets,activity

    def growth(self,scope):
        cond="AND country=?" if scope.country!="All" else ""
        return self.query(f"SELECT date_trunc('month',signup_date)::DATE AS signup_month,count(*) AS new_customers FROM crm_customers WHERE signup_date BETWEEN ? AND ? {cond} GROUP BY 1 ORDER BY 1",[scope.start,scope.end]+([scope.country] if scope.country!="All" else []))

    def cohorts(self,scope):
        # First observed purchase cohorts. Start filter chooses cohorts, never resets first purchase.
        w,p=scope.where(history=True)
        cutoff=pd.Timestamp(scope.end)
        if cutoff!=cutoff+pd.offsets.MonthEnd(0): cutoff=cutoff.replace(day=1)-pd.Timedelta(days=1)
        return self.query(f"""WITH scoped AS (SELECT * FROM fact_sales WHERE {w}), firsts AS (
          SELECT customer_id,min(month) cohort FROM scoped GROUP BY 1), sizes AS (
          SELECT cohort,count(*) cohort_size FROM firsts GROUP BY 1), active AS (
          SELECT f.cohort,date_diff('month',f.cohort,s.month) age,count(DISTINCT s.customer_id) active
          FROM firsts f JOIN scoped s USING(customer_id) WHERE s.order_date<=? GROUP BY 1,2), grid AS (
          SELECT s.cohort,s.cohort_size,age FROM sizes s CROSS JOIN range(0,36) r(age)
          WHERE s.cohort>=date_trunc('month',?::DATE) AND s.cohort + age * INTERVAL '1 month' <= date_trunc('month',?::DATE))
          SELECT g.*,coalesce(a.active,0) active,coalesce(a.active,0)::DOUBLE/g.cohort_size retention
          FROM grid g LEFT JOIN active a USING(cohort,age) ORDER BY cohort,age""",p+[cutoff.date(),scope.start,cutoff.date()])

    def marketing(self,scope):
        # Spend has only campaign-month grain: use complete months and all geographies/sales channels.
        start=pd.Timestamp(scope.start)
        if start.day!=1: start=start+pd.offsets.MonthBegin(1)
        end=pd.Timestamp(scope.end)
        if end!=end+pd.offsets.MonthEnd(0): end=end.replace(day=1)-pd.Timedelta(days=1)
        df=self.query("""WITH first_order AS (SELECT customer_id,min(order_id) FILTER (WHERE rn=1) first_id FROM
            (SELECT *,row_number() OVER (PARTITION BY customer_id ORDER BY order_date,order_id) rn FROM fact_sales) GROUP BY customer_id),
            attributed AS (SELECT s.campaign_id,sum(s.revenue)::DOUBLE attributed_revenue,sum(s.revenue-s.cost)::DOUBLE gross_profit,
            count(*) attributed_orders,count(f.first_id) acquired_customers FROM fact_sales s LEFT JOIN first_order f ON s.order_id=f.first_id
            WHERE s.order_date BETWEEN ? AND ? AND s.campaign_id!=0 GROUP BY 1)
            SELECT m.campaign_id,m.month,m.channel,m.spend_usd,coalesce(a.attributed_revenue,0) attributed_revenue,
            coalesce(a.gross_profit,0) gross_profit,coalesce(a.attributed_orders,0) attributed_orders,
            coalesce(a.acquired_customers,0) acquired_customers,
            e.sent,e.opened,e.clicked,so.impressions,so.engagements
            FROM marketing_campaigns m LEFT JOIN attributed a USING(campaign_id)
            LEFT JOIN email_campaigns e USING(campaign_id) LEFT JOIN social_campaigns so USING(campaign_id)
            WHERE m.month BETWEEN ? AND ? ORDER BY m.month,m.channel""",[start.date(),end.date(),start.date(),end.date()])
        for metric,num in [("roas","attributed_revenue"),("roi","gross_profit")]:
            df[metric]=df[num]/df.spend_usd.replace(0,np.nan)-(1 if metric=="roi" else 0)
        df["cac"]=df.spend_usd/df.acquired_customers.replace(0,np.nan)
        return df,start.date(),end.date()

    def funnel(self,scope):
        country="AND c.country=?" if scope.country!="All" else ""
        channel="AND s.channel=?" if scope.channel!="All" else ""
        return self.query(f"SELECT s.channel,count(*) sessions,sum(checkout) checkouts,sum(purchased) purchases FROM fact_sessions s JOIN crm_customers c USING(customer_id) WHERE event_date BETWEEN ? AND ? {country} {channel} GROUP BY 1",[scope.start,scope.end]+([scope.country] if scope.country!="All" else [])+([scope.channel] if scope.channel!="All" else []))

    def customer_statistics(self,scope):
        w,p=scope.where()
        return self.query(f"SELECT customer_id,country,count(*) frequency,sum(revenue)::DOUBLE monetary,avg(revenue)::DOUBLE aov FROM fact_sales WHERE {w} GROUP BY 1,2",p)


def forecast(monthly,scope,horizon=6):
    frame=monthly.copy()
    frame=frame[(frame.period.dt.date>=scope.start)&((frame.period+pd.offsets.MonthEnd(0)).dt.date<=scope.end)]
    y=frame.revenue.astype(float).to_numpy()
    if len(y)<12: return pd.DataFrame(),{"reason":"At least 12 complete months are required."}
    train,test=y[:-3],y[-3:]
    def fit(values):
        return ExponentialSmoothing(values,trend="add",damped_trend=True,initialization_method="estimated").fit(optimized=True)
    model=fit(train)
    predicted=np.maximum(model.forecast(3),0)
    baseline=np.repeat(train[-1],3)
    model_mae=float(np.mean(abs(test-predicted))); baseline_mae=float(np.mean(abs(test-baseline)))
    use_ets=model_mae<baseline_mae
    final=fit(y) if use_ets else None
    point=np.maximum(final.forecast(horizon),0) if use_ets else np.repeat(y[-1],horizon)
    residual=y-np.asarray(final.fittedvalues) if use_ets else np.diff(y)
    sigma=float(np.std(residual,ddof=1))
    width=1.96*sigma*np.sqrt(np.arange(1,horizon+1))
    future=pd.date_range(frame.period.max()+pd.offsets.MonthBegin(1),periods=horizon,freq="MS")
    result=pd.DataFrame({"period":future,"forecast":point,"lower":np.maximum(0,point-width),"upper":point+width})
    return result,{"model":"Damped Holt trend" if use_ets else "Last-month baseline","holdout_months":3,
        "model_mae":model_mae,"baseline_mae":baseline_mae,"training_months":len(y),
        "interval":"Approximate 95% residual bands; uncalibrated, independent-error assumption. Not seasonal."}


def anomalies(daily):
    df=daily.copy(); values=df.revenue.to_numpy()
    median=float(np.median(values)); mad=float(np.median(abs(values-median)))
    df["robust_z"]=(values-median)/(1.4826*mad) if mad>0 else np.zeros(len(values))
    df["anomaly"]=abs(df.robust_z)>3.5
    return df


def hypothesis(customer_stats,country_a="US",country_b="GB"):
    a=customer_stats.loc[customer_stats.country==country_a,"aov"].to_numpy()
    b=customer_stats.loc[customer_stats.country==country_b,"aov"].to_numpy()
    if len(a)<3 or len(b)<3: return {"available":False,"reason":"Each group needs at least three buyers."}
    test=stats.ttest_ind(a,b,equal_var=False)
    ci=test.confidence_interval(.95)
    return {"available":True,"group_a":country_a,"group_b":country_b,"n_a":len(a),"n_b":len(b),
        "mean_a":float(a.mean()),"mean_b":float(b.mean()),"difference":float(a.mean()-b.mean()),
        "p_value":float(test.pvalue),"lower":float(ci.low),"upper":float(ci.high)}
