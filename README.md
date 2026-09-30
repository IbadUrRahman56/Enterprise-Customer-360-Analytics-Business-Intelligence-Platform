# Customer 360 Analytics

A runnable implementation of the DS-001 case study: canonical source ingestion, a validated DuckDB warehouse, a Streamlit dashboard, statistical analysis and automated executive PDFs.

**Data classification: synthetic.** The default demo contains 1,800 fictional customers, 36,000 generated orders (plus deliberate defects), 48 branches, 80 products and eight countries, covering January 2024 through August 2026. The case study's 12 million customers, 450 branches and 500 million record capacity are target context, not measured demo capacity.

## Run locally

Python 3.12 is the tested interpreter. From this directory on Windows:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m customer360 demo
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Open http://127.0.0.1:8501. The delivered workspace already contains a local environment and generated warehouse. Use `start.ps1` to launch that installation. The app binds to loopback by default. It never uploads the source extracts.

For a containerized run, use `docker compose up --build` and open the same URL. The Compose service stores the warehouse and generated outputs in named volumes and creates the synthetic demo on first start. See [Docker deployment](docs/DOCKER.md) for configuration, real-data imports, health checks and production boundaries.

On macOS/Linux, substitute `python3` and `.venv/bin/python`. `requirements-lock.txt` records the exact tested package versions; `requirements.txt` contains the supported direct dependency ranges.

## Included

| Area | Implementation |
| --- | --- |
| Data collection | Eleven canonical CSV/Parquet extract contracts representing CRM, ERP, POS, payments, web, mobile, support, email, social and campaign spend |
| Engineering | Typed Polars cleaning, null handling, normalization, duplicate detection, value checks, referential checks, payment reconciliation, quarantine, hashes, atomic warehouse publication |
| Executive dashboard | Revenue, customers, order value, margin, repeat purchases, retention, category and country comparisons |
| Customer analytics | Unified profiles, RFM scores, personas, loyalty, inactivity proxy, historical value, annual gross-profit value proxy, acquisition and cohort retention |
| Sales | Product, category and branch performance, seasonality, six-month forecast with holdout comparison and uncertainty bands |
| Marketing | Campaign attribution, spend, CAC, ROAS, gross-profit ROI, email/social metrics and digital funnel |
| Data science | EDA, descriptive statistics, Spearman correlations, buyer-level Welch tests, robust daily anomaly flags, time-series forecasting |
| Reports | Reproducible weekly, monthly and quarterly PDFs via UI or CLI |
| Access | Viewer/analyst/admin capabilities with PBKDF2-backed local authentication, fail-closed real-data mode |
| Delivery | Source, tests, business/technical documentation, dictionary, presentation and demo script |

## Commands

```powershell
# Generate deterministic source extracts and build the warehouse
.\.venv\Scripts\python.exe -m customer360 demo --seed 42 --customers 1800 --orders 36000

# Import a resolved source snapshot using the documented schemas
.\.venv\Scripts\python.exe -m customer360 ingest path/to/extracts

# Produce the report suite using the last date in the source coverage manifest
.\.venv\Scripts\python.exe -m customer360 report --cadence all

# Historical monthly report
.\.venv\Scripts\python.exe -m customer360 report --cadence monthly --as-of 2026-07-31

# Core tests plus all dashboard pages, filters and exports
.\.venv\Scripts\python.exe -m pytest -q
```

`C360_DATA_DIR` overrides the data directory. For isolated pipelines, `demo` and `ingest` also accept `--data-dir`. Set the same environment variable before starting the app for a nondefault warehouse. `report --warehouse` selects a particular warehouse explicitly.

## Project map

```text
app.py                       Streamlit application
customer360/demo.py          Reproducible source generator
customer360/pipeline.py      Cleaning, quarantine and atomic build
customer360/analytics.py     Shared SQL measures and statistical functions
customer360/reports.py       PDF report generator
customer360/security.py      Password verification and capabilities
tests/                       Calculation, pipeline, access and UI checks
docs/                        Contracts, architecture and operating guidance
scripts/                     Evidence export and presentation builder
output/reports/              Generated executive PDFs
output/presentation/         Technical slide deck
data/raw/                    Generated input extracts (git ignored)
data/runs/<run-id>/           Cleaned Parquet, quarantine and manifest
data/warehouse.duckdb        Last successfully published warehouse
```

## Important interpretation limits

- No real enterprise systems are connected. CSV/Parquet files implement the ingestion interface; vendor-specific API extraction remains a deployment integration.
- Data is normalized to USD before import. No live FX conversion is implied.
- One order contains one product in this case-study contract. Partial refunds and line-item orders need an extended schema.
- First purchase means first observed purchase. Left-censored source history can overstate new-customer acquisition.
- Customer inactivity and annual value are transparent proxies, not trained churn or probabilistic lifetime-value models.
- Forecast intervals are approximate residual bands. The demo does not establish production forecasting accuracy.
- No 500-million-record benchmark, multi-user load test, OIDC integration or production deployment has been completed. See [architecture](docs/ARCHITECTURE.md) for the capacity path and acceptance plan.

Read [metrics](docs/METRICS.md), [data dictionary](docs/DATA_DICTIONARY.md), [operations](docs/OPERATIONS.md), [business documentation](docs/BUSINESS.md), [requirements coverage](docs/REQUIREMENTS.md) and the [live demonstration script](docs/DEMO.md).

