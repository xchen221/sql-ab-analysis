-- Question: How concentrated is revenue among sellers? What share of sellers
--           accounts for 50% and 80% of item revenue?
-- Definition: item revenue (price, no freight) of sale orders in the window,
--           credited to the seller of each item.
-- Concepts: running total with SUM() OVER (ORDER BY ... ROWS UNBOUNDED PRECEDING),
--           grand total with an empty OVER (), NTILE for deciles, MIN ... FILTER to
--           find the first row that crosses a threshold.
WITH seller_revenue AS (
    SELECT i.seller_id, SUM(i.price) AS revenue
    FROM order_items i
    JOIN order_facts f USING (order_id)
    CROSS JOIN analysis_window w
    WHERE f.is_sale
      AND f.purchased_at >= w.start_date
      AND f.purchased_at <  w.end_date
    GROUP BY i.seller_id
),
ranked AS (
    SELECT seller_id,
           revenue,
           ROW_NUMBER() OVER (ORDER BY revenue DESC, seller_id)                AS seller_rank,
           COUNT(*) OVER ()                                                    AS n_sellers,
           SUM(revenue) OVER (ORDER BY revenue DESC, seller_id
                              ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
             / SUM(revenue) OVER ()                                            AS cum_share,
           NTILE(10) OVER (ORDER BY revenue DESC, seller_id)                   AS decile
    FROM seller_revenue
)
SELECT
    MAX(n_sellers)                                                  AS n_sellers,
    MIN(seller_rank) FILTER (WHERE cum_share >= 0.5)                AS sellers_for_50pct,
    ROUND(100.0 * MIN(seller_rank) FILTER (WHERE cum_share >= 0.5) / MAX(n_sellers), 1) AS pct_sellers_for_50pct,
    MIN(seller_rank) FILTER (WHERE cum_share >= 0.8)                AS sellers_for_80pct,
    ROUND(100.0 * MIN(seller_rank) FILTER (WHERE cum_share >= 0.8) / MAX(n_sellers), 1) AS pct_sellers_for_80pct,
    ROUND(100.0 * SUM(revenue) FILTER (WHERE decile = 1) / SUM(revenue), 1)            AS pct_revenue_top_decile,
    ROUND(100.0 * SUM(revenue) FILTER (WHERE decile >= 6) / SUM(revenue), 1)           AS pct_revenue_bottom_half,
    ROUND(QUANTILE_CONT(revenue, 0.5), 0)                           AS median_seller_revenue
FROM ranked;
