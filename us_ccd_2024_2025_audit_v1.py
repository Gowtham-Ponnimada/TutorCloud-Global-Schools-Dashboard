from __future__ import annotations
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd
import psycopg2

ROOT = Path('/home/noagedevadmin/tutorcloud/tutorcloud-global-dashboard')
sys.path.insert(0, str(ROOT))

DASHBOARD_YEAR = '2024-2025'
SCHEMA = 'us'
YEAR_TAG = '2024_2025'

def load_db_config():
    cfg = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'dbname': os.getenv('DB_NAME', os.getenv('DB_DATABASE', 'tutorcloud_db')),
        'user': os.getenv('DB_USER', 'tutorcloud_admin'),
        'password': os.getenv('DB_PASSWORD', ''),
        'port': int(os.getenv('DB_PORT', '5432')),
    }
    try:
        from utils.uae_page_renderer import _DB_PARAMS  # type: ignore
        if isinstance(_DB_PARAMS, dict):
            for k, v in _DB_PARAMS.items():
                if k in cfg and v not in (None, ''):
                    cfg[k] = v
    except Exception:
        pass
    return cfg

DB = load_db_config()

def q(sql: str, params=None) -> pd.DataFrame:
    with psycopg2.connect(**DB) as conn:
        return pd.read_sql_query(sql, conn, params=params)

def scalar(sql: str, params=None):
    df = q(sql, params)
    if df.empty:
        return None
    return df.iloc[0, 0]

def to_records(df: pd.DataFrame):
    if df is None or df.empty:
        return []
    out = df.copy()
    for c in out.columns:
        out[c] = out[c].map(lambda v: None if pd.isna(v) else (float(v) if hasattr(v, 'as_tuple') else v))
    return out.to_dict(orient='records')

def main():
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "school_year": DASHBOARD_YEAR,
        "schema": SCHEMA,
        "db_target": {k: v for k, v in DB.items() if k != "password"},
    }

    # 1) Row counts
    count_queries = {
        "stg_sch_directory": f"SELECT COUNT(*) FROM {SCHEMA}.stg_sch_directory_{YEAR_TAG}",
        "stg_sch_membership_raw": f"SELECT COUNT(*) FROM {SCHEMA}.stg_sch_membership_raw_{YEAR_TAG}",
        "stg_sch_staff_raw": f"SELECT COUNT(*) FROM {SCHEMA}.stg_sch_staff_raw_{YEAR_TAG}",
        "stg_sch_characteristics": f"SELECT COUNT(*) FROM {SCHEMA}.stg_sch_characteristics_{YEAR_TAG}",
        "stg_sch_lunch_raw": f"SELECT COUNT(*) FROM {SCHEMA}.stg_sch_lunch_raw_{YEAR_TAG}",
        "stg_lea_directory": f"SELECT COUNT(*) FROM {SCHEMA}.stg_lea_directory_{YEAR_TAG}",
        "stg_lea_membership_raw": f"SELECT COUNT(*) FROM {SCHEMA}.stg_lea_membership_raw_{YEAR_TAG}",
        "stg_lea_staff_raw": f"SELECT COUNT(*) FROM {SCHEMA}.stg_lea_staff_raw_{YEAR_TAG}",
        "stg_sea_directory": f"SELECT COUNT(*) FROM {SCHEMA}.stg_sea_directory_{YEAR_TAG}",
        "stg_sea_membership_raw": f"SELECT COUNT(*) FROM {SCHEMA}.stg_sea_membership_raw_{YEAR_TAG}",
        "stg_sea_staff_raw": f"SELECT COUNT(*) FROM {SCHEMA}.stg_sea_staff_raw_{YEAR_TAG}",
        "dim_states": f"SELECT COUNT(*) FROM {SCHEMA}.dim_states WHERE school_year = %s",
        "dim_districts": f"SELECT COUNT(*) FROM {SCHEMA}.dim_districts WHERE school_year = %s",
        "dim_schools": f"SELECT COUNT(*) FROM {SCHEMA}.dim_schools WHERE school_year = %s",
        "fact_school_totals": f"SELECT COUNT(*) FROM {SCHEMA}.fact_school_totals WHERE school_year = %s",
        "fact_grade_gender_enrollment": f"SELECT COUNT(*) FROM {SCHEMA}.fact_grade_gender_enrollment WHERE school_year = %s",
        "vw_state_kpis_2024_2025": f"SELECT COUNT(*) FROM {SCHEMA}.vw_state_kpis_2024_2025 WHERE school_year = %s",
        "vw_district_kpis_2024_2025": f"SELECT COUNT(*) FROM {SCHEMA}.vw_district_kpis_2024_2025 WHERE school_year = %s",
    }

    row_counts = {}
    for name, sql in count_queries.items():
        try:
            row_counts[name] = int(scalar(sql, [DASHBOARD_YEAR]) if "%s" in sql else scalar(sql))
        except Exception as e:
            row_counts[name] = f"ERROR: {e}"
    report["row_counts"] = row_counts

    # 2) Missing districts audit
    missing = {}

    missing["schools_missing_district_id_or_name"] = to_records(q(f"""
        SELECT
            COUNT(*) AS school_rows_missing_district,
            COUNT(*) FILTER (WHERE district_id IS NULL OR BTRIM(COALESCE(district_id::text, '')) = '') AS missing_district_id,
            COUNT(*) FILTER (WHERE district_name IS NULL OR BTRIM(COALESCE(district_name::text, '')) = '') AS missing_district_name
        FROM {SCHEMA}.dim_schools
        WHERE school_year = %s
    """, [DASHBOARD_YEAR]))

    missing["schools_with_district_id_not_in_dim_districts"] = to_records(q(f"""
        SELECT
            COUNT(*) AS orphan_school_rows
        FROM {SCHEMA}.dim_schools s
        LEFT JOIN {SCHEMA}.dim_districts d
          ON d.school_year = s.school_year
         AND d.district_id = s.district_id
        WHERE s.school_year = %s
          AND s.district_id IS NOT NULL
          AND BTRIM(COALESCE(s.district_id::text, '')) <> ''
          AND d.district_id IS NULL
    """, [DASHBOARD_YEAR]))

    missing["top_orphan_district_refs"] = to_records(q(f"""
        SELECT
            s.state_name,
            s.district_id,
            s.district_name,
            COUNT(*) AS school_rows
        FROM {SCHEMA}.dim_schools s
        LEFT JOIN {SCHEMA}.dim_districts d
          ON d.school_year = s.school_year
         AND d.district_id = s.district_id
        WHERE s.school_year = %s
          AND s.district_id IS NOT NULL
          AND BTRIM(COALESCE(s.district_id::text, '')) <> ''
          AND d.district_id IS NULL
        GROUP BY 1,2,3
        ORDER BY school_rows DESC, s.state_name, s.district_name
        LIMIT 25
    """, [DASHBOARD_YEAR]))

    missing["districts_with_zero_schools_in_dim_schools"] = to_records(q(f"""
        SELECT
            d.state_name,
            d.district_id,
            d.district_name
        FROM {SCHEMA}.dim_districts d
        LEFT JOIN {SCHEMA}.dim_schools s
          ON s.school_year = d.school_year
         AND s.district_id = d.district_id
        WHERE d.school_year = %s
        GROUP BY 1,2,3
        HAVING COUNT(s.school_id) = 0
        ORDER BY d.state_name, d.district_name
        LIMIT 25
    """, [DASHBOARD_YEAR]))

    report["missing_districts_audit"] = missing

    # 3) delivery_model audit
    delivery = {}
    delivery["distribution"] = to_records(q(f"""
        SELECT
            COALESCE(delivery_model, '<<NULL>>') AS delivery_model,
            COUNT(*) AS schools
        FROM {SCHEMA}.dim_schools
        WHERE school_year = %s
        GROUP BY 1
        ORDER BY schools DESC, delivery_model
    """, [DASHBOARD_YEAR]))

    delivery["by_virtual_text"] = to_records(q(f"""
        SELECT
            COALESCE(virtual_text, '<<NULL>>') AS virtual_text,
            COALESCE(delivery_model, '<<NULL>>') AS delivery_model,
            COUNT(*) AS schools
        FROM {SCHEMA}.dim_schools
        WHERE school_year = %s
        GROUP BY 1,2
        ORDER BY schools DESC, virtual_text, delivery_model
        LIMIT 50
    """, [DASHBOARD_YEAR]))

    delivery["unknown_with_nonblank_virtual_text"] = to_records(q(f"""
        SELECT
            COALESCE(virtual_text, '<<NULL>>') AS virtual_text,
            COUNT(*) AS schools
        FROM {SCHEMA}.dim_schools
        WHERE school_year = %s
          AND COALESCE(delivery_model, 'Unknown') = 'Unknown'
          AND virtual_text IS NOT NULL
          AND BTRIM(virtual_text) <> ''
        GROUP BY 1
        ORDER BY schools DESC, virtual_text
        LIMIT 50
    """, [DASHBOARD_YEAR]))

    delivery["sample_rows"] = to_records(q(f"""
        SELECT
            state_name,
            district_name,
            school_name,
            virtual_text,
            delivery_model
        FROM {SCHEMA}.dim_schools
        WHERE school_year = %s
        ORDER BY state_name, district_name, school_name
        LIMIT 25
    """, [DASHBOARD_YEAR]))

    report["delivery_model_audit"] = delivery

    # 4) institution_type audit (backed by sch_type_text)
    institution = {}
    institution["distribution"] = to_records(q(f"""
        SELECT
            COALESCE(sch_type_text, '<<NULL>>') AS institution_type,
            COUNT(*) AS schools
        FROM {SCHEMA}.dim_schools
        WHERE school_year = %s
        GROUP BY 1
        ORDER BY schools DESC, institution_type
    """, [DASHBOARD_YEAR]))

    institution["null_or_blank_count"] = to_records(q(f"""
        SELECT
            COUNT(*) AS null_or_blank_institution_type
        FROM {SCHEMA}.dim_schools
        WHERE school_year = %s
          AND (sch_type_text IS NULL OR BTRIM(sch_type_text) = '')
    """, [DASHBOARD_YEAR]))

    institution["sample_rows"] = to_records(q(f"""
        SELECT
            state_name,
            district_name,
            school_name,
            sch_type_text AS institution_type,
            delivery_model
        FROM {SCHEMA}.dim_schools
        WHERE school_year = %s
        ORDER BY state_name, district_name, school_name
        LIMIT 25
    """, [DASHBOARD_YEAR]))

    report["institution_type_audit"] = institution

    # 5) quick summary metrics
    report["summary_checks"] = to_records(q(f"""
        SELECT
            COUNT(*) AS total_school_rows,
            COUNT(*) FILTER (WHERE delivery_model IS NOT NULL AND BTRIM(delivery_model) <> '') AS populated_delivery_model_rows,
            COUNT(*) FILTER (WHERE sch_type_text IS NOT NULL AND BTRIM(sch_type_text) <> '') AS populated_institution_type_rows,
            COUNT(*) FILTER (WHERE district_id IS NULL OR BTRIM(COALESCE(district_id::text, '')) = '') AS schools_missing_district_id,
            COUNT(*) FILTER (WHERE district_name IS NULL OR BTRIM(COALESCE(district_name::text, '')) = '') AS schools_missing_district_name
        FROM {SCHEMA}.dim_schools
        WHERE school_year = %s
    """, [DASHBOARD_YEAR]))

    out_dir = ROOT / 'reports' / 'us'
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f'us_ccd_2024_2025_audit_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    out_path.write_text(json.dumps(report, indent=2, default=str), encoding='utf-8')

    print("\\n=== US CCD 2024-2025 PRODUCTION AUDIT ===")
    print(json.dumps(report["row_counts"], indent=2))
    print("\\n=== SUMMARY CHECKS ===")
    print(json.dumps(report["summary_checks"], indent=2))
    print("\\n=== DELIVERY MODEL DISTRIBUTION ===")
    print(json.dumps(report["delivery_model_audit"]["distribution"], indent=2))
    print("\\n=== INSTITUTION TYPE DISTRIBUTION ===")
    print(json.dumps(report["institution_type_audit"]["distribution"], indent=2))
    print("\\n=== MISSING DISTRICTS ===")
    print(json.dumps(report["missing_districts_audit"]["schools_missing_district_id_or_name"], indent=2))
    print(json.dumps(report["missing_districts_audit"]["schools_with_district_id_not_in_dim_districts"], indent=2))
    print(f\"\\nReport written to: {out_path}\")

if __name__ == '__main__':
    main()
