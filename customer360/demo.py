"""Deterministic fictional source extracts. No personal or business records."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from .config import COUNTRIES


def generate(target: Path, customers=1800, orders=36000, seed=42):
    target.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    start, end = pd.Timestamp("2024-01-01"), pd.Timestamp("2026-08-31")
    ids = np.arange(1, customers + 1)
    signup = start + pd.to_timedelta(rng.integers(0, 870, customers), unit="D")
    crm = pd.DataFrame({"customer_id": ids, "country": rng.choice(COUNTRIES, customers),
                        "signup_date": signup, "loyalty_tier": rng.choice(["Standard", "Silver", "Gold"], customers, p=[.65,.25,.1])})
    products = pd.DataFrame({"product_id": np.arange(1, 81),
        "product_name": [f"{cat} {i:02d}" for i, cat in enumerate(np.tile(["Home", "Fashion", "Electronics", "Beauty"], 20), 1)],
        "category": np.tile(["Home", "Fashion", "Electronics", "Beauty"], 20),
        "unit_price_usd": rng.uniform(15, 220, 80).round(2)})
    products["unit_cost_usd"] = (products.unit_price_usd * rng.uniform(.35,.7,80)).round(2)
    stores = pd.DataFrame({"store_id": np.arange(1,49), "country": np.repeat(COUNTRIES,6)})
    stores["store_name"] = [f"{c} · Store {i:02d}" for i,c in zip(stores.store_id,stores.country)]
    campaign = pd.DataFrame({"campaign_id": np.arange(1,97),
        "month": np.repeat(pd.date_range(start, end, freq="MS"),3),
        "channel": np.tile(["Email","Paid search","Social"],32),
        "spend_usd": rng.uniform(1500,5000,96).round(2)})
    weights = rng.pareto(2.5,customers)+.3
    customer = rng.choice(ids, orders, p=weights/weights.sum())
    signup_ord = (signup-start).days.to_numpy()[customer-1]
    days = signup_ord + (rng.random(orders) * ((end-start).days-signup_ord+1)).astype(int)
    dates = start + pd.to_timedelta(days,unit="D")
    prod = rng.integers(1,81,orders)
    qty = rng.integers(1,4,orders)
    net = (products.unit_price_usd.to_numpy()[prod-1]*qty*rng.uniform(.8,1,orders)).round(2)
    country = crm.country.to_numpy()[customer-1]
    country_idx = np.array([COUNTRIES.index(c) for c in country])
    month_idx = (dates.year-2024)*12+dates.month-1
    camp = month_idx*3+rng.integers(1,4,orders)
    camp = np.where(rng.random(orders)<.62,camp,0)
    sales = pd.DataFrame({"order_id": np.arange(1,orders+1),"customer_id":customer,
        "product_id":prod,"store_id": country_idx*6+rng.integers(1,7,orders),"order_date":dates,
        "quantity":qty,"revenue_usd":net,"cost_usd":(products.unit_cost_usd.to_numpy()[prod-1]*qty).round(2),
        "channel":rng.choice(["Store","Web","App"],orders,p=[.52,.30,.18]),
        "campaign_id":camp, "status":rng.choice(["Completed","Refunded","Cancelled"],orders,p=[.94,.04,.02])})
    payments = sales[["order_id","revenue_usd"]].rename(columns={"revenue_usd":"amount_usd"}).copy()
    payments["payment_status"] = np.where(sales.status=="Completed","Settled",np.where(sales.status=="Refunded","Refunded","Voided"))
    sessions=[]
    for source in ["Web","App"]:
        count=orders//2
        cust=rng.choice(ids,count)
        d=(signup-start).days.to_numpy()[cust-1]
        ed=start+pd.to_timedelta(d+(rng.random(count)*((end-start).days-d+1)).astype(int),unit="D")
        checkout=rng.random(count)<.28
        purchase=checkout & (rng.random(count)<.58)
        sessions.append(pd.DataFrame({"session_id":[f"{source}-{i}" for i in range(count)],"customer_id":cust,
            "event_date":ed,"viewed":np.ones(count,int),"checkout":checkout.astype(int),"purchased":purchase.astype(int)}))
    email=campaign[campaign.channel=="Email"][["campaign_id"]].copy()
    email["sent"]=rng.integers(15000,30000,len(email)); email["opened"]=(email.sent*rng.uniform(.2,.4,len(email))).astype(int)
    email["clicked"]=(email.opened*rng.uniform(.1,.3,len(email))).astype(int)
    social=campaign[campaign.channel=="Social"][["campaign_id"]].copy()
    social["impressions"]=rng.integers(70000,160000,len(social)); social["engagements"]=(social.impressions*rng.uniform(.01,.05,len(social))).astype(int)
    n=orders//10
    support=pd.DataFrame({"ticket_id":np.arange(1,n+1),"customer_id":rng.choice(ids,n),
        "opened_date":start+pd.to_timedelta(rng.integers(0,(end-start).days+1,n),unit="D"),
        "resolution_hours":rng.gamma(2,12,n).round(1),"csat":rng.integers(1,6,n)})
    # Intentional recoverable defects demonstrate quarantine and duplicate handling.
    crm.loc[0,"loyalty_tier"]=None
    crm.loc[1,"country"]=" us "
    sales=pd.concat([sales,sales.head(20)],ignore_index=True)
    sales.loc[len(sales)] = [orders+1,999999,1,1,"2026-08-01",1,100,50,"Web",0,"Completed"]
    sales.loc[len(sales)] = [orders+2,1,1,1,"invalid",1,-10,5,"Web",0,"Completed"]
    files={"crm_customers":crm,"erp_products":products,"erp_stores":stores,"pos_orders":sales,
        "payment_orders":payments,"marketing_campaigns":campaign,"website_sessions":sessions[0],
        "mobile_sessions":sessions[1],"email_campaigns":email,"social_campaigns":social,"support_tickets":support}
    for name,df in files.items(): df.to_csv(target/f"{name}.csv",index=False)
    (target/"manifest.json").write_text(json.dumps({"classification":"synthetic", "seed":seed,
        "coverage_start":str(start.date()),"coverage_end":str(end.date()),"currency":"USD",
        "timezone":"UTC","note":"Fictional demo. USD-normalized amounts; no real exchange rates."},indent=2))
    return {name:len(df) for name,df in files.items()}

