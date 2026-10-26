"""Load the raw CSVs into one DuckDB file, then build the cleaned views.

Tables keep the source column names. Zip-code prefixes are forced to VARCHAR so
leading zeros survive (auto-detection would read "01037" as the integer 1037).
"""
import duckdb

from common import run_sql_file
from config import DB_PATH, RAW, SQL_DIR

OLIST = RAW / "olist"
FUNNEL = RAW / "olist_funnel"

TABLES = {
    "customers": (OLIST / "olist_customers_dataset.csv", {"customer_zip_code_prefix": "VARCHAR"}),
    "orders": (OLIST / "olist_orders_dataset.csv", {}),
    "order_items": (OLIST / "olist_order_items_dataset.csv", {}),
    "payments": (OLIST / "olist_order_payments_dataset.csv", {}),
    "reviews": (OLIST / "olist_order_reviews_dataset.csv", {}),
    "products": (OLIST / "olist_products_dataset.csv", {}),
    "sellers": (OLIST / "olist_sellers_dataset.csv", {"seller_zip_code_prefix": "VARCHAR"}),
    "category_translation": (OLIST / "product_category_name_translation.csv", {}),
    "mqls": (FUNNEL / "olist_marketing_qualified_leads_dataset.csv", {}),
    "closed_deals": (FUNNEL / "olist_closed_deals_dataset.csv", {}),
    "hillstrom": (RAW / "hillstrom.csv", {}),
}


def main():
    DB_PATH.unlink(missing_ok=True)
    con = duckdb.connect(str(DB_PATH))
    for name, (path, types) in TABLES.items():
        type_arg = ""
        if types:
            type_arg = ", types = {" + ", ".join(f"'{c}': '{t}'" for c, t in types.items()) + "}"
        con.execute(f"CREATE TABLE {name} AS SELECT * FROM read_csv(?, header = true{type_arg})",
                    [str(path)])
        n = con.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
        print(f"  {name:<22} {n:>9,} rows")

    print("\nColumn types (orders):")
    for col, typ in con.execute("SELECT column_name, data_type FROM information_schema.columns "
                                "WHERE table_name = 'orders'").fetchall():
        print(f"  {col:<32} {typ}")

    run_sql_file(con, SQL_DIR / "olist" / "01_views.sql")
    print("\nViews:", [r[0] for r in con.execute(
        "SELECT view_name FROM duckdb_views() WHERE NOT internal ORDER BY 1").fetchall()])
    con.close()


if __name__ == "__main__":
    main()
