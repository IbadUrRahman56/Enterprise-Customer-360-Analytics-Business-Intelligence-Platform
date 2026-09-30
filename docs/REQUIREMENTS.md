# DS-001 requirement coverage

Source: user-supplied `Case Study – DS-001.pdf`. Its technical requirements define the project brief; its four-week/team-size description is context, not a record of actual effort or staffing.

| Brief requirement | Delivered implementation | Boundary |
| --- | --- | --- |
| CRM/ERP/POS/web/mobile/support/email/payment/social | Canonical extracts, synthetic generation and integrated warehouse | File adapters, no live vendor connections |
| Cleaning, missing values, duplicates, standardization | Polars typed validation, country normalization, Unknown loyalty, rejects, conflict failure | Input snapshot must resolve versions |
| Validation and integration | IDs, dates, campaign matching, payment amounts/status, row accounting | No fuzzy identity matching |
| Warehouse design | DuckDB dimensions, order/session facts, daily aggregate, provenance | Full rebuild, current dimensions |
| RFM, personas, geography, loyalty, high-value | RFM scores, profiles, segment and dimensional views | Fixed thresholds, synthetic data |
| Sales, products, categories, regions, branches | Interactive charts and scoped exports | One product per order |
| Seasonality and forecasting | Year/month view, baseline-vs-Holt holdout, six-month projection | Approximate bands, no validated seasonal model |
| CLV | Observed revenue and annual gross-profit value proxy | Not a full probabilistic lifetime model |
| Churn | 90-day inactivity view | Not a trained probability or confirmed churn |
| Retention, repeat, AOV, growth | Shared SQL formulas, comparisons and registration counts | History begins at coverage boundary |
| Campaigns, funnel, CAC, ROAS, ROI, attribution | Campaign and session views | Single source campaign tag, not causal attribution |
| Executive KPI/customer/revenue/marketing/product/branch views | Seven Streamlit workspace pages | Local deployment |
| Weekly/monthly/quarterly/executive/PDF reports | CLI and dashboard PDF generation | Scheduler command documented, no schedule installed |
| EDA/statistics/hypothesis/correlation/anomalies | Statistical lab and tests | Exploratory, unadjusted repeated testing |
| Python/Pandas/NumPy/Polars/Plotly/Matplotlib/SciPy/Statsmodels/DuckDB | Used in source and locked environment | Power BI/Tableau optional and not included |
| 500 million records/scalable/fast | Lazy import, spill limits, aggregate design and acceptance plan | Not benchmarked at enterprise scale |
| Secure access | Password hashing, local roles, guarded real-data mode | Requires production SSO, TLS, rate limiting and audit integration |
| Source code, pipeline, dashboard, reports, docs, dictionary, README | Included in repository | Synthetic demonstration |
| Technical presentation/live demonstration | PPTX and running local dashboard with demo script | No public deployment |
| Bonus | Monthly cohort analysis | Other optional bonuses omitted |

