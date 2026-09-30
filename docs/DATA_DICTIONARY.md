# Source and warehouse data dictionary

All files are UTF-8 CSV with headers or Parquet. Prefer Parquet when both exist. IDs are stable positive integers except session IDs, which are nonempty strings. `campaign_id=0` on orders denotes organic/unattributed traffic. All dates use ISO `YYYY-MM-DD` in UTC. Amounts are already normalized to USD. Each source file is mandatory for a complete snapshot, but may contain only its header when the domain has no records. Unknown critical keys, amounts or dates are quarantined rather than imputed.

`manifest.json` is mandatory:

```json
{
  "classification": "synthetic",
  "coverage_start": "2024-01-01",
  "coverage_end": "2026-08-31",
  "currency": "USD",
  "timezone": "UTC"
}
```

Set `classification` to `real` for real extracts. Coverage means complete source availability on all dates in the interval, not merely min/max observed order dates. A zero-filled day is interpretable only under this contract.

## Canonical extracts

| File | Fields | Contract |
| --- | --- | --- |
| `crm_customers` | `customer_id` int; `country` string; `signup_date` date; `loyalty_tier` string | One identity. Country: US, GB, DE, FR, CA, AU, AE, PK. Missing loyalty becomes Unknown. |
| `erp_products` | `product_id` int; `product_name`, `category` strings; `unit_price_usd`, `unit_cost_usd` numbers | Current product dimension. Prices/costs nonnegative. Historical order cost is authoritative for margin. |
| `erp_stores` | `store_id` int; `country`, `store_name` strings | One fulfilling branch. Store country can differ from customer residence. |
| `pos_orders` | `order_id`, `customer_id`, `product_id`, `store_id` ints; `order_date` date; `quantity` int; `revenue_usd`, `cost_usd` numbers; `channel` string; `campaign_id` int; `status` string | One order / one product. Quantity >0. Status Completed/Refunded/Cancelled. Channel Store/Web/App. Amounts are order totals after discount, before taxes. |
| `payment_orders` | `order_id` int; `amount_usd` number; `payment_status` string | Settled/Refunded/Voided. One summary per order, matching amount within one cent and status. |
| `marketing_campaigns` | `campaign_id` int; `month` date; `channel` string; `spend_usd` number | First day of month. Email/Paid search/Social. One campaign has exactly one month. |
| `website_sessions` | `session_id` string; `customer_id` int; `event_date` date; `viewed`, `checkout`, `purchased` ints | Session indicators, `viewed=1`, `0 <= purchased <= checkout <= viewed`. |
| `mobile_sessions` | Same fields as website sessions | Session IDs use a source namespace; the warehouse retains Web/App channel. |
| `email_campaigns` | `campaign_id`, `sent`, `opened`, `clicked` ints | Nonnegative campaign counts, clicked <= opened <= sent. Must reference an Email campaign. |
| `social_campaigns` | `campaign_id`, `impressions`, `engagements` ints | Nonnegative; engagements <= impressions. Must reference a Social campaign. |
| `support_tickets` | `ticket_id`, `customer_id` ints; `opened_date` date; `resolution_hours` number; `csat` int | Resolution hours >=0, CSAT 1..5. Dates must follow signup and lie in coverage. |

Every extract uses its first listed field as primary key. An identical full row is a duplicate; conflicting records sharing a key stop publication. CRM signup dates may precede the coverage window, but customer snapshots exclude signups after the selected end date.

## Derived fields

`fact_sales.revenue` and `cost` are DECIMAL(18,2) versions of source amounts. `country` is CRM residence, `store_country` is fulfilling branch country. Product, category, loyalty and branch labels are current dimension attributes. `month` is the order month start. Current dimensions are not historical slowly changing dimensions.

Customer snapshot fields: `frequency` completed order count; `monetary` observed sales; `profit` observed sales minus cost; `first_order`, `last_order`; `recency` days since last purchase; `segment`; `r_score`, `f_score`, `m_score`; `annual_value_proxy` annualized gross profit. Nonbuyers have zero frequency/value and null purchase dates/recency.

`data_quality`: `input_rows`, `invalid_rows` (schema/value rejects), `duplicate_rows` (identical valid duplicates), `clean_rows` (after cleaning), `integration_rejected` (later relationship/time/payment rejects), `sha256` (raw file bytes). For each source, input = invalid + duplicate + clean. Accepted integration rows = clean - integration_rejected. Valid refunded/cancelled orders are neither rejects nor sales.

Schema rejects remain at `data/runs/<run-id>/<source>_rejected.parquet`. Integration rejects are `rejected_orders` and `rejected_<source>` warehouse tables. Treat raw, cleaned and rejected data as equally sensitive in real deployments.

