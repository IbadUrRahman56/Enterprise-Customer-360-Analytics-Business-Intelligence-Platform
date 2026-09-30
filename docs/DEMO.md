# Live demonstration script

Run `start.ps1`, or `python -m streamlit run app.py` in the project environment. Open http://127.0.0.1:8501. Allow about 8 minutes for this walkthrough.

1. **Overview, 1 minute.** Point out the synthetic classification. Explain revenue, buyer count and weighted ratios. Change country to US and sales channel to Web, then show that the headline and country/category charts move together. Reset both to All.
2. **Customers, 2 minutes.** Show inactivity versus confirmed churn. Choose an At risk customer and open the unified profile. Inspect historical orders, support and digital activity. Explain fixed RFM thresholds and the annual-value proxy. Scroll to cohorts and distinguish zeros from immature blank cells.
3. **Sales & forecast, 1 minute.** Compare categories, then branches. Show six forecast months, holdout MAE and the selected baseline or trend model. Explain the complete-month rule and approximate interval.
4. **Marketing, 1 minute.** Explain the full-month/global campaign scope before quoting ROAS. Compare spend and attributed sales. Show the digital funnel as a separate session measurement.
5. **Statistical lab, 1 minute.** Show flagged days, correlations and the US/GB buyer-level Welch test. Explain the unit of analysis and why the result is observational.
6. **Data quality, 1 minute.** Show the intentionally duplicated orders, invalid order, orphan ID and auxiliary integration rejects. Demonstrate source fingerprints and coverage metadata.
7. **Reports, 1 minute.** Generate a quarterly PDF. Explain period-to-date dates, consistent formulas and the CLI used by a scheduler. Finish with the architecture/capacity slide: enterprise scale remains an acceptance test, not a measured claim.

For a repeatable clean demo, run `python -m customer360 demo --seed 42` and then `python -m customer360 report --cadence all`.

