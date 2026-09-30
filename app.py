"""Streamlit Customer 360 application. Run: streamlit run app.py"""
import io
import json
import os
import time
from html import escape
from datetime import date, timedelta
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from customer360.analytics import Analytics, Scope, forecast, anomalies, hypothesis
from customer360.config import WAREHOUSE, COUNTRIES, OUTPUT
from customer360.security import authenticate, allowed

st.set_page_config(page_title="Customer 360",page_icon="◈",layout="wide",initial_sidebar_state="auto")
st.markdown('<style>'+Path(__file__).with_name('assets').joinpath('dashboard.css').read_text()+'</style>',unsafe_allow_html=True)

COUNTRY_NAMES={"All":"All countries","US":"United States","GB":"United Kingdom","DE":"Germany","FR":"France","CA":"Canada","AU":"Australia","AE":"United Arab Emirates","PK":"Pakistan"}
PAGE_COPY={
    "Overview":("Executive overview","Track sales, understand customer activity, and see where your business is growing."),
    "Customers":("Customer intelligence","Explore buying patterns, customer value, and the people behind your retention numbers."),
    "Sales & forecast":("Sales performance & outlook","Compare products and branches, then explore what the next six months could look like."),
    "Marketing":("Marketing performance","Connect campaign investment to attributed sales, acquisition, and digital conversion."),
    "Statistical lab":("Statistical exploration","Investigate unusual days, compare customer groups, and test your assumptions."),
    "Reports":("Executive reporting","Turn your selected business scope into a clear, downloadable executive report."),
    "Data quality":("Data health & provenance","Inspect source quality, rejected records, and the evidence behind every refresh.")}


def login():
    if os.environ.get("C360_AUTH_REQUIRED","0")=="0": return "admin"
    if not os.environ.get("C360_USERS_JSON"):
        st.error("Authentication is enabled but no accounts are configured."); st.stop()
    if "role" in st.session_state:
        if time.time()-st.session_state.get("login_time",0)<3600: return st.session_state.role
        st.session_state.pop("role")
    st.title("Customer 360")
    st.caption("Sign in to your analytics workspace")
    with st.form("login"):
        user=st.text_input("Username"); password=st.text_input("Password",type="password")
        submit=st.form_submit_button("Sign in",type="primary")
    if submit:
        if time.time()<st.session_state.get("blocked_until",0): st.error("Please wait before trying again.")
        else:
            try: role=authenticate(user,password)
            except (ValueError,TypeError): role=None
            if role:
                st.session_state.update(role=role,login_time=time.time(),attempts=0); st.rerun()
            else:
                st.session_state.attempts=st.session_state.get("attempts",0)+1
                if st.session_state.attempts>=5: st.session_state.blocked_until=time.time()+60
                st.error("Invalid credentials.")
    st.stop()


role=login()
if not WAREHOUSE.exists():
    st.title("Customer 360")
    st.info("Create the sample warehouse first: python -m customer360 demo")
    st.stop()
api=Analytics(WAREHOUSE)
meta=api.metadata()
if meta["classification"]=="real" and os.environ.get("C360_AUTH_REQUIRED","0")!="1":
    st.error("Real data requires C360_AUTH_REQUIRED=1 and configured accounts."); st.stop()

px.defaults.color_discrete_sequence=["#087f8c","#4477bb","#df9b45","#9464b4","#55a68c","#cb6574"]
px.defaults.template="plotly_white"


def chart(fig,key=None,height=350):
    fig.update_layout(height=height,margin=dict(l=15,r=20,t=30,b=25),font=dict(family="Arial",color="#566c80",size=12),
        paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",legend_title_text="",hovermode="closest",
        hoverlabel=dict(bgcolor="#142a43",font_color="white",font_size=13),
        legend=dict(orientation="h",yanchor="bottom",y=1.03,xanchor="left",x=0))
    fig.update_xaxes(showgrid=False,title_font_size=11,tickfont_size=11)
    fig.update_yaxes(gridcolor="#edf1f5",zeroline=False,title_font_size=11,tickfont_size=11)
    st.plotly_chart(fig,width="stretch",key=key,config={"displaylogo":False,"scrollZoom":False,"modeBarButtonsToRemove":["lasso2d","select2d"]})


def money(x): return "N/A" if x is None else f"${x:,.0f}"
def pct(x): return "N/A" if x is None else f"{x:.1%}"
def delta(current,previous): return None if previous is None or not previous else f"{(current/previous-1):+.1%}"


def download(df,name):
    if allowed(role,"export"):
        # Formula-safe CSV for spreadsheet clients, bounded to the displayed query.
        safe=df.copy()
        for col in safe.select_dtypes(include=["object","str"]).columns:
            safe[col]=safe[col].map(lambda x: "'"+x if isinstance(x,str) and x.startswith(("=","+","-","@","\t","\r")) else x)
        st.download_button("Download this view · CSV",safe.to_csv(index=False).encode(),file_name=name,mime="text/csv")


with st.sidebar:
    st.markdown('<div class="brand"><div class="brand-symbol">◈</div><div><div class="brand-name">Customer 360</div><div class="brand-sub">RETAIL INTELLIGENCE</div></div></div><div class="nav-label">WORKSPACE</div>',unsafe_allow_html=True)
    pages=["Overview","Customers","Sales & forecast","Marketing","Statistical lab","Reports"]
    if allowed(role,"quality"): pages.append("Data quality")
    page=st.radio("Workspace",pages,label_visibility="collapsed")
    st.divider()
    st.markdown('<div class="nav-label">REFINE YOUR VIEW</div>',unsafe_allow_html=True)
    minimum=date.fromisoformat(meta["coverage_start"]); maximum=date.fromisoformat(meta["coverage_end"])
    dates=st.date_input("Reporting period",value=(max(minimum,maximum-timedelta(days=364)),maximum),min_value=minimum,max_value=maximum)
    if len(dates)!=2: st.info("Select both a start and end date."); st.stop()
    country=st.selectbox("Customer country",["All"]+COUNTRIES,format_func=lambda code:COUNTRY_NAMES[code])
    channel=st.selectbox("Sales channel",["All","Store","Web","App"],format_func=lambda name:"All channels" if name=="All" else name)
    st.caption("Filters apply to sales-based views. Exceptions are labeled in each view.")
    st.divider()
    st.caption(f"Data through {maximum:%d %b %Y}\n\nRole: {role}")
    if os.environ.get("C360_AUTH_REQUIRED","0")=="0": st.caption("Local demo · authentication disabled")
    elif st.button("Sign out"):
        st.session_state.clear(); st.rerun()

scope=Scope(dates[0],dates[1],country,channel)
title,description=PAGE_COPY[page]
st.markdown(f'<section class="hero"><div class="hero-overline">CUSTOMER 360 / {escape(page.upper())}</div><h1>{title}</h1><p>{description}</p></section>',unsafe_allow_html=True)
chips=[f"{scope.start:%d %b %Y} – {scope.end:%d %b %Y}",COUNTRY_NAMES[country],"All channels" if channel=="All" else channel,"USD"]
st.markdown('<div class="scope-strip">'+''.join(f'<span class="scope-chip">{escape(value)}</span>' for value in chips)+'</div>',unsafe_allow_html=True)
if meta["classification"]=="synthetic": st.markdown('<div class="demo-note"><strong>Demo workspace</strong> · Synthetic data for exploration. These figures do not describe a real company.</div>',unsafe_allow_html=True)

if page=="Overview":
    m=api.metrics(scope); previous,pm=api.previous(scope); r=api.retention(scope)
    columns=st.columns(4)
    for col,label,key,fmt in zip(columns,["Net sales","Purchasing customers","Average order value","Gross margin"],["revenue","buyers","aov","margin"],[money,lambda x:f"{x:,.0f}",money,pct]):
        change=delta(m[key],pm[key]) if pm and m[key] is not None else None
        help_text={"revenue":"Completed, payment-reconciled sales after discounts. Fully refunded and cancelled orders are excluded.","buyers":"Distinct customers with at least one completed order in the selected period.","aov":"Selected-period sales divided by completed orders.","margin":"Gross profit divided by sales. The delta is relative percentage change, not percentage points."}[key]
        col.metric(label,fmt(m[key]),change,help=help_text)
    st.caption(f"Changes compare with {previous.start:%d %b %Y} – {previous.end:%d %b %Y}." if previous else "Comparison unavailable: the previous equal-length period begins before source coverage.")
    left,right=st.columns([2,1])
    with left:
        st.subheader("Revenue over time")
        st.markdown('<div class="section-intro">Monthly sales within your selected reporting period</div>',unsafe_allow_html=True)
        trend=api.trend(scope)
        fig=px.area(trend,x="period",y="revenue",labels={"period":"","revenue":"Revenue · USD"})
        fig.update_traces(line=dict(width=3),fillcolor="rgba(8,127,140,.10)"); chart(fig)
    with right:
        st.subheader("Revenue by category")
        st.markdown('<div class="section-intro">Compare the contribution of each product category</div>',unsafe_allow_html=True)
        cats=api.breakdown(scope,"category")
        chart(px.bar(cats.sort_values("revenue"),y="category",x="revenue",orientation="h",labels={"category":"","revenue":"USD"}))
    a,b,c=st.columns(3)
    a.metric("Repeat purchase rate",pct(m["repeat_rate"])); b.metric("Period retention",pct(r["rate"])); c.metric("Completed orders",f"{m['orders']:,.0f}")
    st.caption(f"Repeat rate: buyers with 2+ orders in the selected period / all period buyers. Retention: {r['retained']:,} returning buyers / {r['eligible']:,} buyers in the previous equal-length period. Fully refunded and cancelled orders are excluded from net sales.")
    st.subheader("Country performance")
    regional=api.breakdown(scope,"country")
    regional_plot=regional.assign(market=regional.country.map(COUNTRY_NAMES))
    fig=px.bar(regional_plot,x="market",y="revenue",labels={"market":"","revenue":"Revenue · USD"})
    chart(fig,height=300)
    download(regional,f"country-sales_{scope.start}_{scope.end}_{country}_{channel}.csv")

elif page=="Customers":
    st.caption("Customer profiles, segmentation and value use all available purchases through the end date, within country and sales-channel filters. The start date applies to acquisition and cohort views below.")
    segments=api.segments(scope)
    total=int(segments.customers.sum()); risk=int(segments.loc[segments.segment=="At risk","customers"].sum())
    a,b,c=st.columns(3)
    a.metric("Registered customers",f"{total:,}"); b.metric("Inactive buyers · >90 days",f"{risk:,}")
    buyers=segments.loc[segments.segment!="No purchases","customers"].sum()
    c.metric("Inactivity proxy",pct(risk/buyers if buyers else None))
    st.caption("Inactivity is a rule-based churn proxy, not an observed cancellation or a predicted churn probability.")
    left,right=st.columns(2)
    with left:
        st.subheader("Customer segments")
        chart(px.bar(segments,x="customers",y="segment",orientation="h",color="segment",labels={"customers":"Customers","segment":""}))
    with right:
        st.subheader("New customer registrations")
        growth=api.growth(scope)
        chart(px.bar(growth,x="signup_month",y="new_customers",labels={"signup_month":"","new_customers":"Registrations"}))
        st.caption("Registration counts use customer country; sales-channel filter does not apply.")
    with st.expander("Segment definitions and customer value"):
        st.write("At risk: last purchase more than 90 days ago. Champions: active, 10+ purchases and at least $3,000 historical sales. Loyal: active with 3+ purchases. Developing: remaining buyers. No purchases: registered without a purchase in this scope.")
        st.write("RFM scores use documented fixed thresholds for recency, frequency and monetary value. Historical revenue is observed value. The annual gross-profit value proxy annualizes historical gross profit using at least 90 exposure days. It is an illustrative CLV input, not a calibrated lifetime forecast.")
    st.subheader("Customer explorer")
    segment=st.selectbox("Segment",["All"]+segments.segment.tolist())
    customers=api.customer_list(scope,segment)
    st.dataframe(customers,width="stretch",hide_index=True,height=280)
    st.caption("Top 1,000 customers by historical revenue. IDs are pseudonymous.")
    download(customers,f"customer-snapshot_{scope.end}_{country}_{channel}_{segment}.csv")
    if not customers.empty:
        customer=st.selectbox("Open customer profile",customers.customer_id.tolist())
        profile,orders,tickets,activity=api.profile(scope,customer)
        with st.expander(f"Customer {customer} · unified profile",expanded=True):
            cols=st.columns(4); item=profile.iloc[0]
            for col,label,value in zip(cols,["Historical sales","Purchases","Days since purchase","Annual value proxy"],[money(item.monetary),str(item.frequency),"N/A" if pd.isna(item.recency) else str(int(item.recency)),money(item.annual_value_proxy)]): col.metric(label,value)
            st.dataframe(orders,hide_index=True,width="stretch")
            st.caption("Most recent 100 completed orders in the profile scope. Support and digital activity show all channels through the end date.")
            l,r=st.columns(2)
            l.dataframe(tickets,hide_index=True); r.dataframe(activity,hide_index=True)
    st.subheader("Monthly purchase cohorts")
    co=api.cohorts(scope)
    if len(co):
        matrix=co.pivot(index="cohort",columns="age",values="retention"); matrix.index=matrix.index.strftime("%b %Y")
        chart(px.imshow(matrix,aspect="auto",color_continuous_scale=["#eff7f7","#087f8c"],zmin=0,zmax=1,labels=dict(x="Months since first observed purchase",y="First-purchase cohort",color="Retention")),height=430)
        st.caption("Blank cells are immature cohorts. Zero is an observed month with no returning buyers. Partial final months are excluded. First purchase means first observed in this dataset.")
        download(co,f"cohorts_{scope.start}_{scope.end}_{country}_{channel}.csv")
    else: st.info("No completed cohort months for these filters.")

elif page=="Sales & forecast":
    dim=st.selectbox("Compare performance by",["product_name","category","store_name","country","channel"],format_func=lambda x:x.replace("_"," ").title())
    breakdown=api.breakdown(scope,dim)
    st.subheader("Performance comparison")
    chart(px.bar(breakdown.head(15).sort_values("revenue"),x="revenue",y=dim,orientation="h",labels={"revenue":"Revenue · USD",dim:""}),height=450)
    st.caption("Chart shows the top 15. All groups are included in the table and export. Country reflects customer residence; store names identify the fulfilling branch.")
    st.dataframe(breakdown,hide_index=True,width="stretch"); download(breakdown,f"sales-{dim}_{scope.start}_{scope.end}_{country}_{channel}.csv")
    st.subheader("Six-month revenue forecast")
    trend=api.trend(scope); future,diagnostics=forecast(trend,scope)
    if future.empty: st.info(diagnostics["reason"])
    else:
        fig=go.Figure()
        fig.add_scatter(x=trend.period,y=trend.revenue,name="Observed",line=dict(color="#087f8c",width=3))
        fig.add_scatter(x=future.period,y=future.upper,name="Approx. upper band",line=dict(width=0),showlegend=False)
        fig.add_scatter(x=future.period,y=future.lower,name="Approx. 95% band",fill="tonexty",fillcolor="rgba(68,119,187,.15)",line=dict(width=0))
        fig.add_scatter(x=future.period,y=future.forecast,name="Forecast",line=dict(color="#4477bb",dash="dash",width=3))
        chart(fig)
        st.caption(f"Selected model: {diagnostics['model']}. Three-month holdout MAE: Holt {money(diagnostics['model_mae'])}, baseline {money(diagnostics['baseline_mae'])}. Only complete months enter training. {diagnostics['interval']}")
        download(future,f"forecast_{scope.start}_{scope.end}_{country}_{channel}.csv")
    st.subheader("Seasonal pattern")
    season=trend.copy(); season["Year"]=season.period.dt.year.astype(str); season["Month"]=season.period.dt.month
    chart(px.line(season,x="Month",y="revenue",color="Year",markers=True,labels={"revenue":"Revenue · USD"}))
    st.caption("Partial boundary months reflect only selected days. Comparisons show descriptive seasonality, not a seasonally adjusted trend.")

elif page=="Marketing":
    st.warning("Campaign spend is available only by campaign and month. Campaign metrics use complete months in the selected range and all countries and sales channels. Digital funnel below follows the sidebar filters.")
    campaigns,ms,me=api.marketing(scope)
    st.caption(f"Campaign reporting window: {ms} to {me}" if ms<=me else "No complete campaign month in this date range.")
    spend=campaigns.spend_usd.sum(); rev=campaigns.attributed_revenue.sum(); profit=campaigns.gross_profit.sum(); acquired=campaigns.acquired_customers.sum()
    a,b,c,d=st.columns(4)
    a.metric("Campaign spend",money(spend)); b.metric("ROAS",f"{rev/spend:.2f}×" if spend else "N/A"); c.metric("Marketing ROI",pct((profit-spend)/spend if spend else None)); d.metric("Attributed CAC",money(spend/acquired if acquired else None))
    st.caption("ROAS = attributed sales / spend. ROI = (attributed gross profit − spend) / spend. CAC = spend / customers whose first observed order has a campaign tag. Attribution uses one source-provided campaign tag per order; it does not establish incrementality.")
    if len(campaigns):
        grouped=campaigns.groupby("channel",as_index=False)[["spend_usd","attributed_revenue"]].sum()
        chart(px.bar(grouped,x="channel",y=["spend_usd","attributed_revenue"],barmode="group",labels={"value":"USD","channel":""}))
        st.dataframe(campaigns,hide_index=True,width="stretch"); download(campaigns,f"campaigns_{ms}_{me}_global.csv")
    st.subheader("Digital conversion funnel")
    funnel=api.funnel(scope)
    if funnel.empty: st.info("No digital sessions match this scope. Store traffic is not collected.")
    else:
        totals=funnel[["sessions","checkouts","purchases"]].sum()
        chart(go.Figure(go.Funnel(y=["Sessions","Reached checkout","Purchased"],x=totals.to_list(),marker_color=["#087f8c","#4477bb","#55a68c"])),height=300)
        st.caption("Session-level conversion. Digital purchase events are a separate measurement source and are not deduplicated into POS orders.")

elif page=="Statistical lab":
    st.subheader("Daily revenue anomalies")
    daily=anomalies(api.trend(scope,"day"))
    fig=px.line(daily,x="period",y="revenue",labels={"period":"","revenue":"Revenue · USD"})
    outliers=daily[daily.anomaly]
    fig.add_scatter(x=outliers.period,y=outliers.revenue,mode="markers",name="Flagged",marker=dict(size=9,color="#cb6574")); chart(fig)
    st.caption("Absolute median/MAD score >3.5 across the selected days. Descriptive flags require investigation; growth and seasonality can trigger them. Zero MAD produces no flags.")
    download(outliers,f"anomalies_{scope.start}_{scope.end}_{country}_{channel}.csv")
    data=api.customer_statistics(scope)
    left,right=st.columns(2)
    with left:
        st.subheader("Buyer-level purchase distribution")
        chart(px.histogram(data,x="monetary",nbins=40,labels={"monetary":"Customer sales · USD"}))
    with right:
        st.subheader("Correlation analysis")
        corr=data[["frequency","monetary","aov"]].corr(method="spearman")
        chart(px.imshow(corr,zmin=-1,zmax=1,color_continuous_scale="RdBu",text_auto=".2f"))
        st.caption("Spearman rank correlation, one row per buyer. Frequency and monetary value are mechanically related; correlation is not causation.")
    st.subheader("Country comparison · Welch's t-test")
    st.caption("Outcome: each buyer's mean order value. Disjoint country groups avoid counting repeated purchases as independent customers. Country selection above constrains the available groups.")
    a,b=st.columns(2)
    group_a=a.selectbox("Country A",COUNTRIES,index=0); group_b=b.selectbox("Country B",[x for x in COUNTRIES if x!=group_a],index=0)
    result=hypothesis(data,group_a,group_b)
    if result["available"]:
        a,b,c=st.columns(3)
        a.metric("Mean difference · A − B",money(result["difference"])); b.metric("p-value",f"{result['p_value']:.4f}"); c.metric("Sample sizes",f"{result['n_a']} / {result['n_b']}")
        st.write(f"95% confidence interval: {money(result['lower'])} to {money(result['upper'])}.")
        st.caption("Two-sided exploratory test, no multiple-comparison correction. An observational comparison cannot establish a marketing or regional causal effect.")
    else: st.info(result["reason"])
    with st.expander("Descriptive statistics"):
        st.dataframe(data[["frequency","monetary","aov"]].describe(),width="stretch")

elif page=="Reports":
    st.write("Generate a weekly, monthly or quarterly executive PDF with reconciled metrics, comparisons, trend and operating considerations.")
    st.caption("Reports use the sidebar country and channel, and end on the selected end date. The cadence determines the start date; the sidebar start date is ignored. Each file records its actual scope and synthetic classification.")
    cadence=st.selectbox("Report cadence",["weekly","monthly","quarterly"])
    report_key=(cadence,scope.end,country,channel,meta["run_id"])
    if allowed(role,"export") and st.button("Generate executive PDF",type="primary"):
        from customer360.reports import report_bytes, reporting_scope
        report_scope=reporting_scope(scope.end,cadence,country,channel)
        if report_scope.start<minimum: st.error("Insufficient source coverage for this reporting period.")
        else:
            with st.spinner("Preparing your report..."):
                payload=report_bytes(api,report_scope,cadence)
                st.session_state.generated_report=(report_key,payload)
    elif not allowed(role,"export"): st.info("Report exports require the analyst or admin role.")
    saved=st.session_state.get("generated_report")
    if allowed(role,"export") and saved and saved[0]==report_key:
        st.download_button("Download executive report",saved[1],file_name=f"executive-{cadence}_{scope.end}_{country}_{channel}.pdf",mime="application/pdf",on_click="ignore")
    st.subheader("Automation")
    st.code("python -m customer360 report --cadence all",language="bash")
    st.caption("The CLI is idempotent for a given cadence and as-of date. Scheduler setup and deployment instructions are in docs/OPERATIONS.md.")

elif page=="Data quality":
    q=api.query("SELECT * FROM data_quality ORDER BY source")
    a,b,c=st.columns(3)
    a.metric("Source extracts",str(len(q))); b.metric("Duplicates removed",f"{q.duplicate_rows.sum():,}"); c.metric("Rejected rows",f"{q.invalid_rows.sum()+q.integration_rejected.sum():,}")
    st.caption("Clean rows are after schema cleaning. Integration rejects are removed later. Refunded/cancelled orders are valid records but excluded from sales measures.")
    st.dataframe(q.drop(columns="sha256"),width="stretch",hide_index=True)
    st.subheader("Order quarantine")
    rejects=api.query("SELECT rejection_reason,count(*) AS rejected_rows FROM rejected_orders GROUP BY 1")
    st.dataframe(rejects,hide_index=True,width="stretch")
    st.subheader("Build provenance")
    st.json({k:v for k,v in meta.items() if k not in ["sources","source_directory"]})
    with st.expander("Source fingerprints"):
        st.dataframe(q[["source","sha256"]],hide_index=True,width="stretch")
    download(q,f"data-quality_{meta['run_id']}.csv")

with st.expander("Measurement notes & provenance"):
    st.write("Source: canonical CRM, ERP, POS, website, mobile, support, email, payment and social extracts. See docs/DATA_DICTIONARY.md and docs/METRICS.md for field contracts, formulas and limitations.")
    st.write(f"Warehouse run: {meta['run_id']} · Built: {meta['built_at']} · Classification: {meta['classification']} · Dates: UTC · Amounts: USD")
    st.caption("The source coverage manifest defines dates for zero-filled trends. Partial boundary months contain only selected days. Missing data coverage must be corrected in the manifest before interpreting gaps as zero.")
st.markdown('<div class="workspace-footer">CUSTOMER 360 &nbsp; / &nbsp; Retail analytics workspace &nbsp; / &nbsp; Explore with context. Decide with evidence.</div>',unsafe_allow_html=True)
