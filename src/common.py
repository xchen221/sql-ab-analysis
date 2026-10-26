"""Small helpers shared by the scripts."""
import re

import duckdb

from config import DB_PATH


def connect(read_only=True):
    return duckdb.connect(str(DB_PATH), read_only=read_only)


def run_sql_file(con, path):
    """Execute every statement in a .sql file; return the last result as a DataFrame
    (or None if the last statement returns no rows, e.g. CREATE VIEW)."""
    rel = con.execute(path.read_text())
    try:
        return rel.df()
    except duckdb.InvalidInputException:
        return None


def sql_header(path):
    """The '-- Question:' line(s) at the top of a query file."""
    text = path.read_text()
    m = re.search(r"-- Question:(.*?)(?=\n-- [A-Z][a-z]+:|\n[^-])", text, flags=re.S)
    if not m:
        return ""
    return " ".join(line.strip(" -") for line in m.group(1).splitlines()).strip()
