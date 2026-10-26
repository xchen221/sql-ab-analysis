-- Question: How does delivery timing relative to the promised date relate to the
--           review score?
-- Definition: days_vs_promise = delivery date minus estimated delivery date
--           (negative = early). Delivered orders with a review only; one review
--           per order (view order_reviews). This is an association, not a causal
--           effect: late orders may differ in region, product size or seller.
-- Concepts: JOIN to a de-duplicated view, CASE bucketing with an explicit sort key,
--           AVG of a boolean expression as a rate, share of total via SUM() OVER ().
WITH delivered AS (
    SELECT f.order_id,
           DATE_DIFF('day', f.estimated_at::DATE, f.delivered_at::DATE) AS days_vs_promise,
           r.review_score
    FROM order_facts f
    JOIN order_reviews r USING (order_id)
    CROSS JOIN analysis_window w
    WHERE f.order_status = 'delivered'
      AND f.delivered_at IS NOT NULL
      AND f.purchased_at >= w.start_date
      AND f.purchased_at <  w.end_date
),
bucketed AS (
    SELECT *,
           CASE WHEN days_vs_promise <= -14 THEN 1
                WHEN days_vs_promise <= -7  THEN 2
                WHEN days_vs_promise <= 0   THEN 3
                WHEN days_vs_promise <= 3   THEN 4
                WHEN days_vs_promise <= 7   THEN 5
                WHEN days_vs_promise <= 14  THEN 6
                ELSE 7 END AS bucket_order,
           CASE WHEN days_vs_promise <= -14 THEN '14+ days early'
                WHEN days_vs_promise <= -7  THEN '7-13 days early'
                WHEN days_vs_promise <= 0   THEN '0-6 days early'
                WHEN days_vs_promise <= 3   THEN '1-3 days late'
                WHEN days_vs_promise <= 7   THEN '4-7 days late'
                WHEN days_vs_promise <= 14  THEN '8-14 days late'
                ELSE '15+ days late' END AS delivery_bucket
    FROM delivered
)
SELECT
    bucket_order,
    delivery_bucket,
    COUNT(*)                                                    AS n_orders,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)          AS pct_of_orders,
    ROUND(AVG(review_score), 2)                                 AS avg_score,
    ROUND(100.0 * AVG(CASE WHEN review_score = 1 THEN 1 ELSE 0 END), 1)  AS pct_1_star,
    ROUND(100.0 * AVG(CASE WHEN review_score = 5 THEN 1 ELSE 0 END), 1)  AS pct_5_star
FROM bucketed
GROUP BY bucket_order, delivery_bucket
ORDER BY bucket_order;
