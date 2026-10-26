-- Question: How many customers landed in each arm? (Input to the sample-ratio check.)
-- Concepts: GROUP BY, share of total with SUM() OVER ().
SELECT
    segment                                       AS arm,
    COUNT(*)                                      AS n,
    ROUND(COUNT(*) / SUM(COUNT(*)) OVER (), 5)    AS share
FROM hillstrom
GROUP BY segment
ORDER BY segment;
