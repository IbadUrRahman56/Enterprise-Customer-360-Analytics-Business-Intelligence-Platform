"""Deterministic, source-backed PDF reporting shared by CLI and dashboard."""
import io
import os
import tempfile
from datetime import date, timedelta
from pathlib import Path
from xml.sax.saxutils import escape
os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir())/"customer360-matplotlib"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from .analytics import Analytics, Scope


def reporting_scope(end,cadence,country="All",channel="All"):
    if cadence=="weekly": start=end-timedelta(days=6)
    elif cadence=="monthly": start=end.replace(day=1)
    elif cadence=="quarterly": start=end.replace(month=((end.month-1)//3)*3+1,day=1)
    else: raise ValueError("Unknown cadence")
    return Scope(start,end,country,channel)


def report_bytes(api,scope,cadence):
    meta=api.metadata()
    if scope.start<date.fromisoformat(meta["coverage_start"]) or scope.end>date.fromisoformat(meta["coverage_end"]):
        raise ValueError("Report period exceeds source coverage")
    data=api.metrics(scope); previous,pm=api.previous(scope); retention=api.retention(scope)
    segments=api.segments(scope); regions=api.breakdown(scope,"country"); products=api.breakdown(scope,"category")
    out=io.BytesIO()
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name="TitleC360",fontName="Helvetica-Bold",fontSize=28,leading=32,textColor=colors.HexColor("#142A43"),spaceAfter=12))
    styles.add(ParagraphStyle(name="SubC360",fontName="Helvetica",fontSize=10,leading=15,textColor=colors.HexColor("#51627A"),spaceAfter=10))
    styles["BodyText"].fontSize=10; styles["BodyText"].leading=15; styles["BodyText"].spaceAfter=10
    styles["Heading2"].textColor=colors.HexColor("#087F8C"); styles["Heading2"].spaceBefore=14
    elements=[]
    def p(text,style="BodyText"): return Paragraph(escape(str(text)),styles[style])
    def table(rows,widths):
        t=Table([[p(c,"BodyText") for c in row] for row in rows],colWidths=widths,repeatRows=1)
        t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#E7F2F3")),("VALIGN",(0,0),(-1,-1),"TOP"),
            ("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),6),
            ("LINEBELOW",(0,0),(-1,-1),.4,colors.HexColor("#DDE5ED"))]))
        return t
    money=lambda x:"N/A" if x is None else f"${x:,.0f}"
    percent=lambda x:"N/A" if x is None else f"{x:.1%}"
    label="SYNTHETIC DEMONSTRATION" if meta["classification"]=="synthetic" else "CUSTOMER 360 ANALYTICS"
    elements += [p(label,"SubC360"),p(f"{cadence.title()} executive report","TitleC360"),
        p(f"{scope.start:%d %b %Y} - {scope.end:%d %b %Y} | Country: {scope.country} | Sales channel: {scope.channel} | USD","SubC360")]
    if meta["classification"]=="synthetic": elements.append(p("All figures come from fictional, reproducible data. These findings demonstrate the platform and are not recommendations about a real business."))
    rows=[["Measure","Current period","Previous equal-length period"]]
    for name,key,fmt in [("Net sales","revenue",money),("Purchasing customers","buyers",lambda x:f"{x:,.0f}"),("Orders","orders",lambda x:f"{x:,.0f}"),("Average order value","aov",money),("Gross margin","margin",percent),("Repeat purchase rate","repeat_rate",percent)]:
        rows.append([name,fmt(data[key]),fmt(pm[key]) if pm else "Unavailable"])
    elements.append(table(rows,[185,150,160]))
    elements.append(p(f"Comparison: {previous.start} to {previous.end}." if previous else "The previous equal-length period is outside source coverage.","SubC360"))
    elements.append(p("Operating readout","Heading2"))
    if len(regions) and data["revenue"]:
        top=regions.iloc[0]
        elements.append(p(f"{top.country} contributes {money(top.revenue)}, or {top.revenue/data['revenue']:.1%} of sales in this scope. Review assortment and branch capacity before attributing this concentration to campaign effectiveness."))
    else: elements.append(p("No completed sales match the selected period and filters. No regional conclusion is available."))
    elements.append(p(f"Period retention is {percent(retention['rate'])}: {retention['retained']:,} of {retention['eligible']:,} prior-period buyers purchased again. This measures observed return purchasing, not contractual churn."))
    trend=api.trend(scope,"day")
    fig,ax=plt.subplots(figsize=(8.2,2.15)); fig.patch.set_facecolor("white")
    ax.plot(trend.period,trend.revenue,color="#087F8C",linewidth=2.5,marker="o",markersize=3)
    ax.fill_between(trend.period,trend.revenue,alpha=.08,color="#087F8C")
    ax.set_ylabel("Revenue (USD)"); ax.grid(axis="y",alpha=.15); ax.spines[["top","right"]].set_visible(False)
    fig.autofmt_xdate(); fig.tight_layout()
    image=io.BytesIO(); fig.savefig(image,format="png",dpi=160); plt.close(fig); image.seek(0)
    elements += [p("Revenue during the reporting period","Heading2"),Image(image,width=495,height=130),PageBreak()]
    elements += [p("Customer priorities & measurement","TitleC360"),p("Snapshot through the report end date. Customer values use all observed purchase history in the selected country and sales channel.","SubC360")]
    rows=[["Segment","Customers","Historical sales"]]
    for row in segments.itertuples(): rows.append([row.segment,f"{row.customers:,}",money(row.revenue)])
    elements += [table(rows,[230,100,165]),p("Suggested investigations","Heading2")]
    risk=int(segments.loc[segments.segment=="At risk","customers"].sum())
    elements.append(p(f"Review the {risk:,} buyers inactive for more than 90 days. A win-back experiment should use a randomized holdout, consented audiences and incremental gross profit as its outcome. The threshold alone does not prove churn."))
    if len(products):
        best=products.iloc[0]
        elements.append(p(f"{best.category} is the largest category by revenue ({money(best.revenue)}). Check its gross profit ({money(best.gross_profit)}) alongside stock availability before changing the assortment."))
    elements += [p("Metric definitions","Heading2"),p("Net sales: sum of completed, reconciled order amounts after discounts. Fully refunded and cancelled orders are excluded. The source contract does not support partial refunds or taxes. Gross margin: (sales minus product cost) / sales. Average order value: sales / completed orders. Repeat rate: buyers with two or more period orders / period buyers."),
        p("At risk: last observed purchase more than 90 days before the report end. Champions: active buyers with 10+ orders and $3,000+ observed sales. Loyal: active buyers with 3+ orders. Annual value proxy: historical gross profit / max(observed exposure days, 90) x 365. This proxy is not a calibrated lifetime estimate."),
        p("Source lineage & limitations","Heading2"),p(f"Run {meta['run_id']}. Built {meta['built_at']}. Source coverage: {meta['coverage_start']} to {meta['coverage_end']}. Canonical source extracts, cleaning rules and warehouse SQL are reproducible with the supplied project. SHA-256 source fingerprints are stored in the data_quality table."),
        p("Dates use UTC and amounts are already normalized to USD. Monthly and quarterly reports are period-to-date when the end date precedes period end. A period comparison uses equal calendar-day counts, not matched weekdays. Source coverage must be complete before missing dates can be interpreted as zero. Enterprise volume and production identity integration require separate deployment testing.","SubC360")]
    def footer(canvas,doc):
        canvas.setStrokeColor(colors.HexColor("#DDE5ED")); canvas.line(50,45,545,45)
        canvas.setFont("Helvetica",8); canvas.setFillColor(colors.HexColor("#51627A"))
        canvas.drawString(50,31,f"Customer 360 | {label} | {scope.end}"); canvas.drawRightString(545,31,str(doc.page))
    doc=SimpleDocTemplate(out,pagesize=(595,842),rightMargin=50,leftMargin=50,topMargin=42,bottomMargin=60,title=f"Customer 360 {cadence} report",author="Customer 360")
    doc.build(elements,onFirstPage=footer,onLaterPages=footer)
    return out.getvalue()


def generate_reports(warehouse,output,cadence="all",as_of=None):
    api=Analytics(warehouse); meta=api.metadata()
    end=date.fromisoformat(as_of or meta["coverage_end"])
    output.mkdir(parents=True,exist_ok=True)
    result=[]
    for period in (["weekly","monthly","quarterly"] if cadence=="all" else [cadence]):
        scope=reporting_scope(end,period)
        path=output/f"executive-{period}-{end}.pdf"
        payload=report_bytes(api,scope,period)
        temp=path.with_suffix(".tmp"); temp.write_bytes(payload); temp.replace(path)
        result.append(path)
    return result
