# Business documentation

## Decision context

The case study describes a retailer whose customer records are fragmented across transactional, engagement and service systems. The platform brings consistent customer IDs and reconciled order facts into one measurement surface. The intended audiences are executives monitoring commercial performance, analysts investigating behavior and operators checking source quality.

The delivered implementation is a synthetic case-study demonstration. The demo population and its random data patterns do not support recommendations about a real company. The report generator instead demonstrates how findings, denominators, comparison periods and proposed investigations can be communicated responsibly.

## Operating decisions

| Question | Evidence | Next business action |
| --- | --- | --- |
| Where is sales performance concentrated? | Country, product and branch sales with gross profit | Review assortment, inventory and fulfillment with business owners |
| Which customers merit investigation? | Historical value, RFM scores, inactive buyers and service history | Design consented customer interviews or a holdout-based win-back test |
| Are customers returning? | Equal-period retention, repeat buying and mature cohorts | Investigate acquisition mix and purchase cycles before changing retention policy |
| Is marketing economically attractive? | Attributed gross profit, spend, ROI and acquisition count | Validate attribution, then test incremental profit with a randomized holdout |
| What might sales look like next? | Forecast, chronological holdout error and uncertainty bands | Use an operating range; review model suitability with longer history |
| Can reporting be trusted? | Reconciliation, quarantine, manifests and file fingerprints | Fix upstream definitions and completeness before accepting headline changes |

## Ownership and cadence

Finance owns order revenue, cost, refund and FX definitions. Marketing owns campaign tags, spend and acquisition policy. Customer operations owns identity and service definitions. Data engineering owns source contracts, freshness, referential integrity and recovery. Analytics owns metric definitions, validation and model review. A production product owner should approve metric version changes and access policy.

Weekly reviews focus on revenue, exceptions and returning customers. Monthly reviews add product/branch comparisons and campaign economics. Quarterly reviews examine cohorts and planning scenarios. The application can generate each report, but recurring schedules and recipients remain deployment configuration.

## Known gaps before production

Live vendor connectors, source identity resolution, line-item accounting, partial refunds, historical FX, slowly changing dimensions, incremental updates, probabilistic CLV, validated churn models, SSO/MFA, region-level authorization and enterprise load validation need additional implementation and organization-specific data. See the requirements matrix for delivered and unverified scope.

