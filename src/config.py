"""Paths, data sources and the analysis choices for the whole project.

Everything a reviewer might ask "why this value?" about is set here, once.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
DB_PATH = ROOT / "data" / "warehouse.duckdb"
SQL_DIR = ROOT / "sql"
RESULTS = ROOT / "results"
FIGURES = ROOT / "figures"

# ---------------------------------------------------------------- data sources
# Raw files are downloaded by 01_get_data.py and never committed (see .gitignore).
SOURCES = {
    # Olist Brazilian e-commerce, 9 tables, CC BY-NC-SA 4.0.
    "olist": "https://www.kaggle.com/api/v1/datasets/download/olistbr/brazilian-ecommerce",
    # Olist marketing funnel (leads -> closed deals), CC BY-NC-SA 4.0.
    "olist_funnel": "https://www.kaggle.com/api/v1/datasets/download/olistbr/marketing-funnel-olist",
    # Hillstrom (2008) MineThatData e-mail test; no license stated, so not redistributed.
    "hillstrom": "http://www.minethatdata.com/Kevin_Hillstrom_MineThatData_E-MailAnalytics_DataMiningChallenge_2008.03.20.csv",
}

# ------------------------------------------------------------ experiment design
# Fixed before looking at any outcome column (visit, conversion, spend).
CONTROL = "No E-Mail"
TREATMENTS = ["Mens E-Mail", "Womens E-Mail"]
DESIGN_SHARES = {"No E-Mail": 1 / 3, "Mens E-Mail": 1 / 3, "Womens E-Mail": 1 / 3}

PRIMARY_METRIC = "visit"              # visited the site within 2 weeks (0/1)
SECONDARY_METRICS = ["conversion", "spend"]
GUARDRAIL_METRIC = "spend"            # revenue per recipient must not drop
# Non-inferiority margin for the guardrail: a drop of more than 10% of the
# control mean spend per customer would block a launch.
GUARDRAIL_REL_MARGIN = -0.10

ALPHA = 0.05                          # two-sided, family-wise within each family
POWER = 0.80
SRM_ALPHA = 0.001                     # strict threshold, as commonly used for SRM alarms

# Pre-treatment covariates (measured over the 12 months before the e-mail).
CUPED_COVARIATE = "history"           # dollars spent in the past year
ADJUST_COVARIATES = ["recency", "history", "mens", "womens", "newbie"]

N_BOOT = 2000                         # bootstrap replicates for spend CIs
N_SIM = 2000                          # A/A and peeking simulations
N_LOOKS = 10                          # interim analyses in the peeking simulation
SEED = 20261026
