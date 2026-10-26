-- Question: Per arm and metric, what are n, mean and variance? These sufficient
--           statistics are all a z-test or Welch t-test needs, which is how
--           experiment platforms usually work: aggregate in SQL, test in Python.
-- Metrics: visit (0/1), conversion (0/1), spend (dollars per customer, zeros kept,
--          i.e. revenue per recipient).
-- Concepts: UNPIVOT to long format, AVG / VAR_SAMP / SUM by group.
WITH long AS (
    UNPIVOT (SELECT segment AS arm, visit, conversion, spend FROM hillstrom)
    ON visit, conversion, spend
    INTO NAME metric VALUE value
)
SELECT
    arm,
    metric,
    COUNT(*)         AS n,
    SUM(value)       AS total,
    AVG(value)       AS mean,
    VAR_SAMP(value)  AS var
FROM long
GROUP BY arm, metric
ORDER BY metric, arm;
