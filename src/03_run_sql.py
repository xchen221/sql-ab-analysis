"""Run the data checks and every product-analytics query; save each result as CSV."""
import pandas as pd

from common import connect, run_sql_file, sql_header
from config import RESULTS, SQL_DIR

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)


def main():
    out = RESULTS / "olist"
    out.mkdir(parents=True, exist_ok=True)
    con = connect()
    files = [SQL_DIR / "olist" / "02_checks.sql"] + sorted((SQL_DIR / "olist").glob("q*.sql"))
    for path in files:
        df = run_sql_file(con, path)
        df.to_csv(out / f"{path.stem}.csv", index=False)
        print(f"\n=== {path.name}: {sql_header(path)}")
        if path.stem.startswith("q03"):       # long cohort table: show the first months only
            wide = df.pivot(index="cohort_month", columns="months_since", values="pct_retained")
            print(wide.iloc[:, :7].to_string())
        else:
            print(df.to_string(index=False))
    con.close()


if __name__ == "__main__":
    main()
