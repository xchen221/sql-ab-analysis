#!/usr/bin/env bash
# Run the whole project end to end. Override the interpreter with PYTHON=...
set -euo pipefail
cd "$(dirname "$0")"
PYTHON=${PYTHON:-python}
mkdir -p logs
for step in 00_selfcheck 01_get_data 02_build_db 03_run_sql 04_experiment 05_figures; do
    echo "== $step"
    (cd src && "$PYTHON" "$step.py") > "logs/$step.log" 2>&1
    tail -n 1 "logs/$step.log"
done
