-- Question: In each of the five largest states (by number of customers), which three
--           product categories bring in the most item revenue, and what share of the
--           state's revenue do they take?
-- Definition: item revenue = item price (no freight) of sale orders in the window.
-- Concepts: four-table join (orders -> items -> products -> category names),
--           a ranking CTE used as a filter (semi-join with IN), ROW_NUMBER() OVER
--           (PARTITION BY ...) with QUALIFY to keep the top N per group, share of a
--           group total via SUM() OVER (PARTITION BY ...).
WITH sale_items AS (
    SELECT f.customer_state, p.category, i.price
    FROM order_facts f
    JOIN order_items i USING (order_id)
    JOIN products_en p USING (product_id)
    CROSS JOIN analysis_window w
    WHERE f.is_sale
      AND f.purchased_at >= w.start_date
      AND f.purchased_at <  w.end_date
),
top_states AS (
    SELECT customer_state
    FROM order_facts
    GROUP BY customer_state
    ORDER BY COUNT(DISTINCT customer_unique_id) DESC
    LIMIT 5
),
by_category AS (
    SELECT customer_state, category, SUM(price) AS revenue
    FROM sale_items
    WHERE customer_state IN (SELECT customer_state FROM top_states)
    GROUP BY customer_state, category
)
SELECT
    customer_state,
    ROW_NUMBER() OVER (PARTITION BY customer_state ORDER BY revenue DESC) AS rank_in_state,
    category,
    ROUND(revenue, 0)                                                     AS revenue,
    ROUND(100.0 * revenue / SUM(revenue) OVER (PARTITION BY customer_state), 1) AS pct_of_state
FROM by_category
QUALIFY rank_in_state <= 3
ORDER BY SUM(revenue) OVER (PARTITION BY customer_state) DESC, rank_in_state;
