-- Question: How many customers ever come back, and how long until their second
--           purchase?
-- Definition: a repeat purchase is a sale on a later calendar day than the
--           customer's first sale (same-day orders are usually one basket split
--           into several orders). To give everyone the same chance to return, the
--           repeat rate counts only customers whose first sale was at least 180 days
--           before the end of the window, and asks whether they returned within
--           180 days.
-- Concepts: MIN() OVER (PARTITION BY ...) to attach each person's first purchase
--           to every row, MIN ... FILTER for "first order after day one",
--           COUNT(DISTINCT), QUANTILE_CONT (median) of a date difference.
WITH sales AS (
    SELECT customer_unique_id, purchased_at
    FROM order_facts, analysis_window w
    WHERE is_sale
      AND purchased_at >= w.start_date
      AND purchased_at <  w.end_date
),
with_first AS (
    SELECT customer_unique_id,
           purchased_at,
           MIN(purchased_at) OVER (PARTITION BY customer_unique_id) AS first_at
    FROM sales
),
per_customer AS (
    SELECT customer_unique_id,
           MIN(first_at)                                                        AS first_at,
           COUNT(*)                                                             AS n_orders,
           COUNT(DISTINCT purchased_at::DATE)                                   AS n_purchase_days,
           MIN(purchased_at) FILTER (WHERE purchased_at::DATE > first_at::DATE) AS second_at
    FROM with_first
    GROUP BY customer_unique_id
)
SELECT
    COUNT(*)                                                                AS n_customers,
    ROUND(100.0 * AVG(CASE WHEN n_orders > 1 THEN 1 ELSE 0 END), 2)         AS pct_more_than_one_order,
    ROUND(100.0 * AVG(CASE WHEN n_purchase_days > 1 THEN 1 ELSE 0 END), 2)  AS pct_more_than_one_day,
    ROUND(100.0 * AVG(CASE WHEN n_purchase_days >= 3 THEN 1 ELSE 0 END), 2) AS pct_three_plus_days,
    -- Why repeats are counted by day: share of multi-order customers whose orders
    -- all fall on a single day (split baskets, not returning customers).
    ROUND(100.0 * AVG(CASE WHEN n_purchase_days = 1 THEN 1 ELSE 0 END)
          FILTER (WHERE n_orders > 1), 1)                                   AS pct_multi_order_single_day,
    COUNT(*) FILTER (WHERE first_at < w.end_date - INTERVAL 180 DAY)        AS n_eligible_180d,
    ROUND(100.0 * AVG(CASE WHEN second_at < first_at + INTERVAL 180 DAY THEN 1 ELSE 0 END)
          FILTER (WHERE first_at < w.end_date - INTERVAL 180 DAY), 2)       AS pct_repeat_within_180d,
    ROUND(QUANTILE_CONT(DATE_DIFF('day', first_at::DATE, second_at::DATE), 0.5), 0) AS median_days_to_second,
    ROUND(QUANTILE_CONT(DATE_DIFF('day', first_at::DATE, second_at::DATE), 0.25), 0) AS p25_days_to_second,
    ROUND(QUANTILE_CONT(DATE_DIFF('day', first_at::DATE, second_at::DATE), 0.75), 0) AS p75_days_to_second
FROM per_customer, analysis_window w;
