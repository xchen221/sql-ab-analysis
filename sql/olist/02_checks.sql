-- Question: Is the data consistent enough to trust the queries that follow?
-- Output: one row per check; n_rows counts the offending rows (0 is ideal, but a
--         non-zero count is fine as long as later queries handle it).
-- Concepts: anti-join (LEFT JOIN ... WHERE right.key IS NULL), GROUP BY ... HAVING,
--           scalar subqueries, reconciling totals across two tables.
WITH pay AS (
    SELECT order_id, SUM(payment_value) AS paid
    FROM payments
    GROUP BY order_id
)
SELECT 'duplicate order_id in orders' AS check_name,
       (SELECT COUNT(*) - COUNT(DISTINCT order_id) FROM orders) AS n_rows
UNION ALL
SELECT 'order_items rows with no matching order',
       (SELECT COUNT(*) FROM order_items i
        LEFT JOIN orders o USING (order_id) WHERE o.order_id IS NULL)
UNION ALL
SELECT 'orders with no items',
       (SELECT COUNT(*) FROM order_facts WHERE n_items = 0)
UNION ALL
SELECT 'orders with no payment record',
       (SELECT COUNT(*) FROM orders o
        LEFT JOIN pay p USING (order_id) WHERE p.order_id IS NULL)
UNION ALL
SELECT 'payments differ from items + freight by > 1 BRL',
       (SELECT COUNT(*) FROM order_facts f
        JOIN pay p USING (order_id) WHERE ABS(p.paid - f.gmv) > 1)
UNION ALL
SELECT 'status delivered but no delivery timestamp',
       (SELECT COUNT(*) FROM orders
        WHERE order_status = 'delivered' AND order_delivered_customer_date IS NULL)
UNION ALL
SELECT 'delivered timestamp but status not delivered',
       (SELECT COUNT(*) FROM orders
        WHERE order_status <> 'delivered' AND order_delivered_customer_date IS NOT NULL)
UNION ALL
SELECT 'delivery timestamp earlier than purchase',
       (SELECT COUNT(*) FROM orders
        WHERE order_delivered_customer_date < order_purchase_timestamp)
UNION ALL
SELECT 'orders with more than one review',
       (SELECT COUNT(*) FROM (SELECT order_id FROM reviews
                              GROUP BY order_id HAVING COUNT(*) > 1))
UNION ALL
SELECT 'people (customer_unique_id) with more than one customer_id',
       (SELECT COUNT(*) FROM (SELECT customer_unique_id FROM customers
                              GROUP BY customer_unique_id HAVING COUNT(*) > 1))
UNION ALL
SELECT 'products with no category',
       (SELECT COUNT(*) FROM products WHERE product_category_name IS NULL)
UNION ALL
SELECT 'categories with no English translation',
       (SELECT COUNT(DISTINCT p.product_category_name) FROM products p
        LEFT JOIN category_translation t USING (product_category_name)
        WHERE p.product_category_name IS NOT NULL
          AND t.product_category_name IS NULL);
