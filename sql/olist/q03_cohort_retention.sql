-- Question: Of the customers who first bought in a given month, what share buys
--           again 1, 2, ..., 12 months later?
-- Definition: customer = customer_unique_id (a person; customer_id changes with
--           every order). Cohort = month of the first sale. A customer is retained
--           in month k if they have any sale in calendar month cohort + k.
--           Cells that fall after the last complete month are NULL rather than 0
--           (right-censoring: we cannot see those months yet).
-- Concepts: MIN() OVER (PARTITION BY ...) to find each person's first order,
--           DATE_DIFF in months, COUNT(DISTINCT), cross join with a generated
--           month index so empty cells appear as 0 instead of disappearing.
WITH sales AS (
    SELECT customer_unique_id,
           DATE_TRUNC('month', purchased_at)::DATE AS order_month
    FROM order_facts, analysis_window w
    WHERE is_sale
      AND purchased_at >= w.start_date
      AND purchased_at <  w.end_date
),
with_cohort AS (
    SELECT customer_unique_id,
           order_month,
           MIN(order_month) OVER (PARTITION BY customer_unique_id) AS cohort_month
    FROM sales
),
activity AS (
    SELECT cohort_month,
           DATE_DIFF('month', cohort_month, order_month) AS months_since,
           COUNT(DISTINCT customer_unique_id)            AS n_active
    FROM with_cohort
    GROUP BY 1, 2
),
cohort_size AS (
    SELECT cohort_month, n_active AS n_customers
    FROM activity
    WHERE months_since = 0
),
grid AS (
    SELECT c.cohort_month, c.n_customers, k.months_since
    FROM cohort_size c
    CROSS JOIN range(0, 13) AS k(months_since)
)
SELECT
    g.cohort_month,
    g.n_customers,
    g.months_since,
    CASE WHEN g.cohort_month + TO_MONTHS(CAST(g.months_since AS INTEGER)) < w.end_date
         THEN COALESCE(a.n_active, 0) END                                   AS n_active,
    CASE WHEN g.cohort_month + TO_MONTHS(CAST(g.months_since AS INTEGER)) < w.end_date
         THEN ROUND(100.0 * COALESCE(a.n_active, 0) / g.n_customers, 2) END AS pct_retained
FROM grid g
CROSS JOIN analysis_window w
LEFT JOIN activity a
       ON a.cohort_month = g.cohort_month
      AND a.months_since = g.months_since
ORDER BY g.cohort_month, g.months_since;
