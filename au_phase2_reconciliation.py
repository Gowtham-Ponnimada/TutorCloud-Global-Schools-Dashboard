#!/usr/bin/env python3
"""Australia reconciliation scaffold against ABS 2025 benchmarks."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine, text

REPO_ROOT = Path(__file__).resolve().parent
REPORT_DIR = REPO_ROOT / "reports" / "au"
ABS_BENCHMARKS = {
    "total_students": 4160918,
    "government_students": 2613404,
    "catholic_students": 831692,
    "independent_students": 715822,
}


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def read_env_file(env_path: Path):
    env = {}
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def db_engine():
    env = read_env_file(REPO_ROOT / ".env")
    host = os.getenv("DB_HOST") or env.get("DB_HOST")
    port = os.getenv("DB_PORT") or env.get("DB_PORT", "5432")
    name = os.getenv("DB_NAME") or env.get("DB_NAME")
    user = os.getenv("DB_USER") or env.get("DB_USER")
    password = os.getenv("DB_PASSWORD") or env.get("DB_PASSWORD")
    return create_engine(f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}", future=True)


def metric(conn, sql: str):
    return conn.execute(text(sql)).scalar_one() or 0


def main():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    engine = db_engine()
    with engine.begin() as conn:
        actual = {
            "total_students": metric(conn, "SELECT COALESCE(SUM(total_students),0) FROM au.fact_school_totals WHERE school_year='2025'"),
            "government_students": metric(conn, "SELECT COALESCE(SUM(total_students),0) FROM au.fact_school_totals WHERE school_year='2025' AND management_type='Government'"),
            "catholic_students": metric(conn, "SELECT COALESCE(SUM(total_students),0) FROM au.fact_school_totals WHERE school_year='2025' AND management_type='Catholic'"),
            "independent_students": metric(conn, "SELECT COALESCE(SUM(total_students),0) FROM au.fact_school_totals WHERE school_year='2025' AND management_type='Independent'"),
        }
        rows = []
        for name, abs_value in ABS_BENCHMARKS.items():
            actual_value = actual[name]
            delta = actual_value - abs_value
            pct_delta = (delta / abs_value) if abs_value else None
            rows.append({
                "metric_name": name,
                "acara_derived": actual_value,
                "abs_2025": abs_value,
                "absolute_delta": delta,
                "pct_delta": pct_delta,
                "status": "MATCH" if delta == 0 else "REVIEW",
                "note": "ABS is benchmark only; ACARA row-level totals may differ due to scope differences.",
            })
        report = {"generated_at_utc": now_utc(), "benchmarks": rows}
    report_path = REPORT_DIR / f"au_reconciliation_report_{now_utc()}.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"Report written to {report_path}")


if __name__ == "__main__":
    main()
