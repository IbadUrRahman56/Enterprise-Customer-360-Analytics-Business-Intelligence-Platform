# Metric contract

All sales measures use completed, settled, reconciled orders. Global filters intersect: inclusive order-date range, customer residence country and order sales channel. Amounts are USD. A blank/undefined ratio is not zero.

| Metric | Formula / population |
| --- | --- |
| Net sales | Sum of completed order revenue after discounts, excluding fully refunded/cancelled orders |
| Gross profit | Sum of revenue minus historical order cost |
| Gross margin | Gross profit / net sales |
| Orders | Count of valid completed orders |
| Purchasing customers | Distinct customers with a completed order in the selected period |
| AOV | Net sales / orders |
| Repeat purchase rate | Buyers with at least two period orders / all period buyers |
| Period retention | Buyers in both current and immediately previous equal-length period / buyers in previous period |
| Revenue delta | Current / previous revenue - 1; undefined when prior is zero or outside coverage |
| Acquisition | CRM signup count during selected period; country applies, sales channel does not |
| Inactivity proxy | Historical buyers with no order in past 90 days / all historical buyers in the selected country/channel |
| Observed value | Customer historical sales through selected end date |
| Annual value proxy | Customer historical gross profit / max(days since first observed order + 1, 90) * 365 |
| ROAS | Campaign-attributed sales / campaign spend |
| Marketing ROI | (Campaign-attributed gross profit - campaign spend) / campaign spend |
| Attributed CAC | Spend / buyers whose first observed order is attributed to a campaign |
| Funnel conversion | Purchase-indicated sessions / sessions; separate from POS conversion |

## RFM and personas

Snapshot history runs from source coverage start through the selected end date. The sidebar start date does not truncate customer history. In a channel-filtered snapshot, all registered customers in country scope remain eligible, and nonbuyers means no purchases in that selected sales channel.

- Recency scores 5/4/3/2/1 for <=30/60/90/180/>180 days. Nonbuyers score 0.
- Frequency scores 5/4/3/2/1 for >=20/10/5/2/1 purchases. Nonbuyers score 0.
- Monetary scores 5/4/3/2/1 for >=5000/3000/1000/300/>0 USD. Zero revenue scores 0.
- Segment precedence: No purchases, At risk (>90 days), Champions (10+ orders and $3,000+ sales), Loyal (3+), Developing.

These fixed thresholds are transparent demo policy, not learned clusters. Profiles combine CRM, purchasing, support and digital session activity. Support/digital profile summaries use all channels through the end date and explicitly say so.

## Retention and cohorts

The immediately previous period contains the same number of days. If any of that period lies before source coverage, period retention and comparisons are unavailable. This avoids using a partial baseline as a complete denominator.

Cohorts use the first observed purchase month within the selected country/channel. The start-date filter chooses which cohorts to display, rather than resetting first purchase. Month N retention = distinct cohort members purchasing in N / cohort members. Mature months without purchases are 0; future months remain absent. Partial final months are excluded. A maximum of 36 ages is returned to bound the visualization. Historic data can be left-censored; this is not an acquisition-at-birth model.

## Marketing scope

Campaign spend has no country or POS channel dimension. Campaign views therefore use global complete months inside the selected range, independently of country/channel filters. First and last partial months are removed. The UI and report/export names state this scope. Campaign metrics are recomputed from summed numerators and denominators rather than averaging row-level ratios.

Source campaign tags implement single-touch attribution. Organic orders have campaign 0. First acquisition orders are selected by date and then order ID to resolve same-day ties. Spend excludes no campaigns solely because they have no sales. CAC is unavailable when acquired-customer count is zero. ROAS/ROI are unavailable for zero spend. None of these metrics is a causal estimate of incremental return.

## Statistical methods

EDA includes distributions and summary statistics at buyer grain. Spearman correlation measures monotonic association between frequency, total sales and AOV. Some associations are mechanical because these metrics share inputs.

Welch's independent two-sample t-test compares **buyer mean order value** between two distinct residence countries. Each customer contributes once. It reports the difference, sample sizes, two-sided p-value and 95% confidence interval. At least three buyers per group are required. Normal-approximation and observational-selection limitations remain. Exploration across many country pairs is not adjusted for multiplicity.

Daily anomaly flags use `(revenue - median) / (1.4826 * median absolute deviation)` with absolute score above 3.5. Zero MAD yields no flags. This rule does not model holiday, growth or weekly seasonality.

Forecasting requires 12 complete months. The final three historical months form a chronological holdout. A damped additive Holt trend competes with a last-month baseline using MAE. The lower-error model refits on all complete months and projects six months. Approximate bands use 1.96 times residual standard deviation times square root of horizon, clipped at zero. They assume independent residuals, are uncalibrated and do not guarantee 95% future coverage. Seasonality is displayed descriptively but not included in the selected forecast model. No forecast uses a partial boundary month.

