from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd
from sqlalchemy import create_engine

REPO = Path(__file__).resolve().parents[2]
REPORT_DIR = REPO / "reports/us"

def load_db_config():
    cfg = {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "5432")),
        "dbname": os.getenv("DB_NAME", os.getenv("DB_DATABASE", "tutorcloud_db")),
        "user": os.getenv("DB_USER", "tutorcloud_admin"),
        "password": os.getenv("DB_PASSWORD", ""),
    }
    try:
        sys.path.insert(0, str(REPO))
        from utils.uae_page_renderer import _DB_PARAMS as UAE_DB_CONFIG  # type: ignore
        if isinstance(UAE_DB_CONFIG, dict):
            for k in ("host", "port", "dbname", "user", "password"):
                if UAE_DB_CONFIG.get(k) not in (None, ""):
                    cfg[k] = UAE_DB_CONFIG[k]
    except Exception:
        pass
    return cfg

DB = load_db_config()

def engine():
    url = (
        f"postgresql+psycopg2://{quote_plus(str(DB['user']))}:{quote_plus(str(DB['password']))}"
        f"@{DB['host']}:{DB['port']}/{DB['dbname']}"
    )
    return create_engine(url, future=True)

def q(sql: str):
    return pd.read_sql(sql, engine())

def main():
    checks = {}
    tables = [
        "us.dim_states",
        "us.dim_districts",
        "us.dim_schools",
        "us.fact_enrollment",
        "us.fact_staff",
        "us.fact_school_characteristics",
        "us.fact_performance_state",
        "us.vw_dashboard_readiness",
    ]
    for t in tables:
        try:
            df = q(f"SELECT COUNT(*) AS c FROM {t}")
            checks[t] = int(df.iloc[0]["c"])
        except Exception as e:
            checks[t] = f"ERROR: {e}"

    result = {
        "validated_at_utc": datetime.now().astimezone().isoformat(),
        "dashboard_year": "2024-2025",
        "mode": "directory_only",
        "checks": checks,
        "state_sample": q("SELECT * FROM us.dim_states ORDER BY school_count DESC, state_name LIMIT 10").to_dict("records"),
        "district_sample": q("SELECT * FROM us.dim_districts ORDER BY state_name, district_name LIMIT 10").to_dict("records"),
        "school_sample": q("SELECT * FROM us.dim_schools ORDER BY state_name, district_name, school_name LIMIT 10").to_dict("records"),
    }

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out = REPORT_DIR / f"us_directory_2024_2025_validate_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    out.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(json.dumps(result, indent=2, default=str))
    print(f"Validation report written to: {out}")

if __name__ == "__main__":
    main()
