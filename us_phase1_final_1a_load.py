#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

import psycopg2
from psycopg2 import sql
import requests

ROOT = Path('/home/noagedevadmin/tutorcloud/tutorcloud-global-dashboard')
DASHBOARD_YEAR = '2024-2025'
YEAR_TAG = '2024_2025'
SCHEMA = 'us'

URLS: Dict[str, str] = {
    'sch_directory': 'https://nces.ed.gov/ccd/Data/zip/ccd_sch_029_2425_w_1a_073025.zip',
    'sch_membership': 'https://nces.ed.gov/ccd/Data/zip/ccd_sch_052_2425_l_1a_073025.zip',
    'sch_staff': 'https://nces.ed.gov/ccd/Data/zip/ccd_sch_059_2425_l_1a_073025.zip',
    'sch_characteristics': 'https://nces.ed.gov/ccd/Data/zip/ccd_sch_129_2425_w_1a_073025.zip',
    'sch_lunch': 'https://nces.ed.gov/ccd/Data/zip/ccd_sch_033_2425_l_1a_073025.zip',
    'lea_directory': 'https://nces.ed.gov/ccd/Data/zip/ccd_lea_029_2425_w_1a_073025.zip',
    'lea_membership': 'https://nces.ed.gov/ccd/Data/zip/ccd_lea_052_2425_l_1a_073025.zip',
    'lea_staff': 'https://nces.ed.gov/ccd/Data/zip/ccd_lea_059_2425_l_1a_073025.zip',
    'sea_directory': 'https://nces.ed.gov/ccd/Data/zip/ccd_sea_029_2425_w_1a_073025.zip',
    'sea_membership': 'https://nces.ed.gov/ccd/Data/zip/ccd_sea_052_2425_l_1a_073025.zip',
    'sea_staff': 'https://nces.ed.gov/ccd/Data/zip/ccd_sea_059_2425_l_1a_073025.zip',
    'release_notes': 'https://nces.ed.gov/ccd/doc/SY_2024-25_Universe_1a_CCD_Nonfiscal_Release_Notes.docx',
    'school_notes': 'https://nces.ed.gov/ccd/xls/SY_2024-25_CCD_Final_1a_Data_Notes.xlsx',
}

TABLE_MAP = {
    'sch_directory': f'stg_sch_directory_{YEAR_TAG}',
    'sch_membership': f'stg_sch_membership_raw_{YEAR_TAG}',
    'sch_staff': f'stg_sch_staff_raw_{YEAR_TAG}',
    'sch_characteristics': f'stg_sch_characteristics_{YEAR_TAG}',
    'sch_lunch': f'stg_sch_lunch_raw_{YEAR_TAG}',
    'lea_directory': f'stg_lea_directory_{YEAR_TAG}',
    'lea_membership': f'stg_lea_membership_raw_{YEAR_TAG}',
    'lea_staff': f'stg_lea_staff_raw_{YEAR_TAG}',
    'sea_directory': f'stg_sea_directory_{YEAR_TAG}',
    'sea_membership': f'stg_sea_membership_raw_{YEAR_TAG}',
    'sea_staff': f'stg_sea_staff_raw_{YEAR_TAG}',
}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def log(msg: str) -> None:
    print(msg, flush=True)


def load_db_config() -> dict:
    cfg = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'dbname': os.getenv('DB_NAME', os.getenv('DB_DATABASE', 'tutorcloud_db')),
        'user': os.getenv('DB_USER', 'tutorcloud_admin'),
        'password': os.getenv('DB_PASSWORD', ''),
        'port': int(os.getenv('DB_PORT', '5432')),
    }
    try:
        sys.path.insert(0, str(ROOT))
        from utils.uae_page_renderer import _DB_PARAMS  # type: ignore
        if isinstance(_DB_PARAMS, dict):
            for k, v in _DB_PARAMS.items():
                if k in cfg and v not in (None, ''):
                    cfg[k] = v
    except Exception:
        pass
    return cfg


def sanitize(col: str) -> str:
    col = col.strip().lower()
    col = re.sub(r'[^a-z0-9_]+', '_', col)
    col = re.sub(r'_+', '_', col).strip('_')
    if not col:
        col = 'col'
    if col[0].isdigit():
        col = f'c_{col}'
    return col


def ensure_dirs() -> dict:
    base = ROOT / 'data' / 'us' / 'final_1a_2024_2025'
    raw = base / 'raw'
    extracted = base / 'extracted'
    docs = base / 'docs'
    reports = ROOT / 'reports' / 'us'
    scripts = ROOT / 'scripts' / 'us'
    sql_dir = ROOT / 'sql' / 'us'
    for p in [base, raw, extracted, docs, reports, scripts, sql_dir]:
        p.mkdir(parents=True, exist_ok=True)
    return {'base': base, 'raw': raw, 'extracted': extracted, 'docs': docs, 'reports': reports, 'scripts': scripts, 'sql': sql_dir}


def download(url: str, target: Path) -> None:
    if target.exists() and target.stat().st_size > 0:
        log(f'Using existing file: {target.name}')
        return
    log(f'Downloading {target.name} ...')
    with requests.get(url, stream=True, timeout=180) as r:
        r.raise_for_status()
        with open(target, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)


def unzip_file(zip_path: Path, out_dir: Path) -> List[Path]:
    if shutil.which('unzip') is None:
        raise RuntimeError('unzip command is required on the server for NCES zip extraction.')
    out_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(['unzip', '-o', str(zip_path), '-d', str(out_dir)], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return sorted(out_dir.glob('*'))


def find_csv(paths: List[Path]) -> Path:
    csvs = [p for p in paths if p.suffix.lower() == '.csv']
    if not csvs:
        raise FileNotFoundError('No CSV found after extraction')
    return csvs[0]


def csv_header(csv_path: Path) -> List[str]:
    with open(csv_path, 'r', encoding='utf-8-sig', newline='') as f:
        reader = csv.reader(f)
        return next(reader)


def create_text_table(cur, schema: str, table: str, cols: List[str]) -> List[str]:
    safe_cols = []
    seen = {}
    for raw in cols:
        base = sanitize(raw)
        idx = seen.get(base, 0)
        seen[base] = idx + 1
        safe = base if idx == 0 else f'{base}_{idx+1}'
        safe_cols.append(safe)
    cur.execute(sql.SQL('DROP TABLE IF EXISTS {}.{} CASCADE').format(sql.Identifier(schema), sql.Identifier(table)))
    ddl_cols = sql.SQL(', ').join(sql.SQL('{} TEXT').format(sql.Identifier(c)) for c in safe_cols)
    cur.execute(sql.SQL('CREATE TABLE {}.{} ({})').format(sql.Identifier(schema), sql.Identifier(table), ddl_cols))
    return safe_cols


def copy_csv(cur, schema: str, table: str, csv_path: Path, cols: List[str]) -> None:
    col_sql = sql.SQL(', ').join(sql.Identifier(c) for c in cols)
    q = sql.SQL('COPY {}.{} ({}) FROM STDIN WITH (FORMAT CSV, HEADER TRUE, ENCODING \'UTF8\')').format(
        sql.Identifier(schema), sql.Identifier(table), col_sql
    )
    with open(csv_path, 'r', encoding='utf-8-sig', newline='') as f:
        cur.copy_expert(q.as_string(cur.connection), f)


def load_stage_table(cur, key: str, csv_path: Path) -> dict:
    headers = csv_header(csv_path)
    cols = create_text_table(cur, SCHEMA, TABLE_MAP[key], headers)
    copy_csv(cur, SCHEMA, TABLE_MAP[key], csv_path, cols)
    cur.execute(sql.SQL('SELECT COUNT(*) FROM {}.{}').format(sql.Identifier(SCHEMA), sql.Identifier(TABLE_MAP[key])))
    count = cur.fetchone()[0]
    return {'table': f'{SCHEMA}.{TABLE_MAP[key]}', 'rows': int(count), 'csv': str(csv_path), 'columns': cols}


def build_marts(cur) -> None:
    sql_text = f"""
    DROP VIEW IF EXISTS {SCHEMA}.vw_dashboard_readiness CASCADE;
    DROP VIEW IF EXISTS {SCHEMA}.vw_state_kpis_2024_2025 CASCADE;
    DROP VIEW IF EXISTS {SCHEMA}.vw_district_kpis_2024_2025 CASCADE;
    DROP TABLE IF EXISTS {SCHEMA}.fact_grade_gender_enrollment CASCADE;
    DROP TABLE IF EXISTS {SCHEMA}.fact_school_totals CASCADE;
    DROP TABLE IF EXISTS {SCHEMA}.dim_schools CASCADE;
    DROP TABLE IF EXISTS {SCHEMA}.dim_districts CASCADE;
    DROP TABLE IF EXISTS {SCHEMA}.dim_states CASCADE;

    CREATE TABLE {SCHEMA}.dim_states AS
    WITH school_counts AS (
        SELECT statename, st,
               COUNT(DISTINCT ncessch) FILTER (WHERE sy_status = '1') AS school_count,
               COUNT(DISTINCT leaid) FILTER (WHERE sy_status = '1') AS district_count
        FROM {SCHEMA}.{TABLE_MAP['sch_directory']}
        WHERE school_year = '{DASHBOARD_YEAR}'
        GROUP BY statename, st
    ),
    state_students AS (
        SELECT statename, st,
               MAX(CASE WHEN total_indicator = 'Education Unit Total' THEN NULLIF(student_count,'')::numeric END) AS total_students
        FROM {SCHEMA}.{TABLE_MAP['sea_membership']}
        WHERE school_year = '{DASHBOARD_YEAR}'
        GROUP BY statename, st
    ),
    state_staff AS (
        SELECT statename, st,
               MAX(CASE
                   WHEN staff = 'Teachers'
                    AND total_indicator = 'Derived - Major Staffing Category'
                   THEN NULLIF(staff_count,'')::numeric
               END) AS total_teachers
        FROM {SCHEMA}.{TABLE_MAP['sea_staff']}
        WHERE school_year = '{DASHBOARD_YEAR}'
        GROUP BY statename, st
    )
    SELECT
        '{DASHBOARD_YEAR}'::text AS school_year,
        d.fipst AS state_fips,
        d.statename AS state_name,
        d.st AS state_abbr,
        COALESCE(sc.school_count, 0)::bigint AS school_count,
        COALESCE(sc.district_count, 0)::bigint AS district_count,
        ss.total_students::numeric AS total_students,
        stf.total_teachers::numeric AS total_teachers,
        CASE WHEN COALESCE(stf.total_teachers,0) > 0 THEN ROUND(ss.total_students / stf.total_teachers, 2) END AS ptr,
        now() AS created_at
    FROM {SCHEMA}.{TABLE_MAP['sea_directory']} d
    LEFT JOIN school_counts sc ON sc.statename = d.statename AND sc.st = d.st
    LEFT JOIN state_students ss ON ss.statename = d.statename AND ss.st = d.st
    LEFT JOIN state_staff stf ON stf.statename = d.statename AND stf.st = d.st
    WHERE d.school_year = '{DASHBOARD_YEAR}';

    CREATE TABLE {SCHEMA}.dim_districts AS
    WITH lea_students AS (
        SELECT leaid,
               MAX(CASE WHEN total_indicator = 'Education Unit Total' THEN NULLIF(student_count,'')::numeric END) AS total_students
        FROM {SCHEMA}.{TABLE_MAP['lea_membership']}
        WHERE school_year = '{DASHBOARD_YEAR}'
        GROUP BY leaid
    ),
    lea_staff AS (
        SELECT leaid,
               MAX(CASE
                   WHEN staff = 'Teachers'
                    AND total_indicator = 'Derived - Major Staffing Category'
                   THEN NULLIF(staff_count,'')::numeric
               END) AS total_teachers
        FROM {SCHEMA}.{TABLE_MAP['lea_staff']}
        WHERE school_year = '{DASHBOARD_YEAR}'
        GROUP BY leaid
    )
    SELECT
        d.school_year,
        d.fipst AS state_fips,
        d.statename AS state_name,
        d.st AS state_abbr,
        d.leaid AS district_id,
        d.st_leaid AS state_district_id,
        d.lea_name AS district_name,
        d.lea_type,
        d.lea_type_text,
        d.sy_status,
        d.sy_status_text,
        d.level,
        d.gslo AS low_grade,
        d.gshi AS high_grade,
        NULLIF(d.operational_schools,'')::bigint AS operational_schools,
        ls.total_students::numeric AS total_students,
        lf.total_teachers::numeric AS total_teachers,
        CASE WHEN COALESCE(lf.total_teachers,0) > 0 THEN ROUND(ls.total_students / lf.total_teachers, 2) END AS ptr,
        now() AS created_at
    FROM {SCHEMA}.{TABLE_MAP['lea_directory']} d
    LEFT JOIN lea_students ls ON ls.leaid = d.leaid
    LEFT JOIN lea_staff lf ON lf.leaid = d.leaid
    WHERE d.school_year = '{DASHBOARD_YEAR}';

    CREATE TABLE {SCHEMA}.dim_schools AS
    SELECT
        d.school_year,
        d.fipst AS state_fips,
        d.statename AS state_name,
        d.st AS state_abbr,
        d.leaid AS district_id,
        d.st_leaid AS state_district_id,
        d.lea_name AS district_name,
        d.ncessch AS school_id,
        d.st_schid AS state_school_id,
        d.schid,
        d.sch_name AS school_name,
        d.mcity AS city,
        d.mstate AS mailing_state,
        d.mzip AS zip_code,
        d.phone,
        d.website,
        d.sy_status,
        d.sy_status_text,
        d.sch_type,
        d.sch_type_text,
        d.charter_text,
        d.level AS school_level,
        d.gslo AS low_grade,
        d.gshi AS high_grade,
        d.igoffered,
        c.shared_time,
        c.nslp_status,
        c.nslp_status_text,
        c.virtual,
        c.virtual_text,
        CASE
            WHEN c.virtual_text IS NULL OR BTRIM(c.virtual_text) = '' THEN 'Unknown'
            WHEN LOWER(BTRIM(c.virtual_text)) = 'no virtual instruction' THEN 'Brick & Mortar'
            WHEN LOWER(BTRIM(c.virtual_text)) = 'supplemental virtual' THEN 'Both'
            WHEN LOWER(BTRIM(c.virtual_text)) IN ('exclusively virtual', 'primarily virtual') THEN 'Virtual'
            WHEN LOWER(BTRIM(c.virtual_text)) IN ('missing', 'not reported') THEN 'Unknown'
            ELSE 'Unknown'
        END AS delivery_model,
        'Govt'::text AS management_type,
        'CCD'::text AS source_system,
        '2024-2025'::text AS source_school_year,
        now() AS created_at
    FROM {SCHEMA}.{TABLE_MAP['sch_directory']} d
    LEFT JOIN {SCHEMA}.{TABLE_MAP['sch_characteristics']} c
      ON c.school_year = d.school_year AND c.ncessch = d.ncessch
    WHERE d.school_year = '{DASHBOARD_YEAR}';

    CREATE TABLE {SCHEMA}.fact_school_totals AS
    WITH mem AS (
        SELECT ncessch,
               MAX(CASE WHEN total_indicator = 'Education Unit Total' THEN NULLIF(student_count,'')::numeric END) AS total_students
        FROM {SCHEMA}.{TABLE_MAP['sch_membership']}
        WHERE school_year = '{DASHBOARD_YEAR}'
        GROUP BY ncessch
    ),
    staff AS (
        SELECT ncessch,
               MAX(CASE WHEN total_indicator = 'Education Unit Total' THEN NULLIF(teachers,'')::numeric END) AS total_teachers
        FROM {SCHEMA}.{TABLE_MAP['sch_staff']}
        WHERE school_year = '{DASHBOARD_YEAR}'
        GROUP BY ncessch
    ),
    lunch AS (
        SELECT ncessch,
               MAX(CASE WHEN lower(data_group) = 'free and reduced-price lunch table' AND total_indicator = 'Education Unit Total' THEN NULLIF(student_count,'')::numeric END) AS lunch_total,
               MAX(CASE WHEN lower(lunch_program) LIKE 'free lunch qualified%' THEN NULLIF(student_count,'')::numeric END) AS free_lunch_qualified,
               MAX(CASE WHEN lower(lunch_program) LIKE 'reduced-price lunch qualified%' THEN NULLIF(student_count,'')::numeric END) AS reduced_price_qualified,
               MAX(CASE WHEN lower(data_group) = 'direct certification' AND total_indicator = 'Education Unit Total' THEN NULLIF(student_count,'')::numeric END) AS direct_certification
        FROM {SCHEMA}.{TABLE_MAP['sch_lunch']}
        WHERE school_year = '{DASHBOARD_YEAR}'
        GROUP BY ncessch
    )
    SELECT
        s.school_year,
        s.state_name,
        s.state_abbr,
        s.district_id,
        s.district_name,
        s.school_id,
        s.school_name,
        m.total_students::numeric AS total_students,
        stf.total_teachers::numeric AS total_teachers,
        CASE WHEN COALESCE(stf.total_teachers,0) > 0 THEN ROUND(m.total_students / stf.total_teachers, 2) END AS ptr,
        l.lunch_total::numeric AS lunch_total,
        l.free_lunch_qualified::numeric AS free_lunch_qualified,
        l.reduced_price_qualified::numeric AS reduced_price_qualified,
        l.direct_certification::numeric AS direct_certification,
        now() AS created_at
    FROM {SCHEMA}.dim_schools s
    LEFT JOIN mem m ON m.ncessch = s.school_id
    LEFT JOIN staff stf ON stf.ncessch = s.school_id
    LEFT JOIN lunch l ON l.ncessch = s.school_id;

    CREATE TABLE {SCHEMA}.fact_grade_gender_enrollment AS
    SELECT
        d.school_year,
        d.state_name,
        d.state_abbr,
        d.district_id,
        d.district_name,
        d.school_id,
        d.school_name,
        m.grade,
        m.sex,
        m.race_ethnicity,
        NULLIF(m.student_count,'')::numeric AS student_count,
        m.total_indicator,
        m.dms_flag,
        now() AS created_at
    FROM {SCHEMA}.{TABLE_MAP['sch_membership']} m
    JOIN {SCHEMA}.dim_schools d
      ON d.school_id = m.ncessch AND d.school_year = m.school_year
    WHERE m.school_year = '{DASHBOARD_YEAR}';

    CREATE INDEX IF NOT EXISTS idx_us_dim_states_{YEAR_TAG}_abbr ON {SCHEMA}.dim_states(state_abbr);
    CREATE INDEX IF NOT EXISTS idx_us_dim_districts_{YEAR_TAG}_state ON {SCHEMA}.dim_districts(state_name, district_name);
    CREATE INDEX IF NOT EXISTS idx_us_dim_schools_{YEAR_TAG}_state ON {SCHEMA}.dim_schools(state_name, district_name, school_level);
    CREATE INDEX IF NOT EXISTS idx_us_fact_school_totals_{YEAR_TAG}_school ON {SCHEMA}.fact_school_totals(school_id);
    CREATE INDEX IF NOT EXISTS idx_us_fact_grade_gender_{YEAR_TAG}_keys ON {SCHEMA}.fact_grade_gender_enrollment(state_name, district_name, grade, sex);

    CREATE VIEW {SCHEMA}.vw_state_kpis_2024_2025 AS
    SELECT
        s.school_year,
        s.state_name,
        s.state_abbr,
        s.school_count AS total_schools,
        s.district_count AS total_districts,
        s.total_students,
        s.total_teachers,
        s.ptr,
        COUNT(*) FILTER (WHERE ds.charter_text = 'Yes') AS charter_schools,
        COUNT(*) FILTER (WHERE ds.virtual_text ILIKE '%%virtual%%') AS virtual_schools,
        SUM(f.free_lunch_qualified) AS free_lunch_qualified,
        SUM(f.reduced_price_qualified) AS reduced_price_qualified,
        SUM(f.direct_certification) AS direct_certification,
        COUNT(*) FILTER (WHERE f.total_students IS NOT NULL) AS schools_with_enrollment
    FROM {SCHEMA}.dim_states s
    LEFT JOIN {SCHEMA}.dim_schools ds ON ds.state_name = s.state_name AND ds.school_year = s.school_year
    LEFT JOIN {SCHEMA}.fact_school_totals f ON f.school_id = ds.school_id AND f.school_year = ds.school_year
    GROUP BY s.school_year, s.state_name, s.state_abbr, s.school_count, s.district_count, s.total_students, s.total_teachers, s.ptr;

    CREATE VIEW {SCHEMA}.vw_district_kpis_2024_2025 AS
    SELECT
        d.school_year,
        d.state_name,
        d.state_abbr,
        d.district_id,
        d.district_name,
        d.operational_schools AS total_schools,
        d.total_students,
        d.total_teachers,
        d.ptr,
        COUNT(*) FILTER (WHERE s.charter_text = 'Yes') AS charter_schools,
        COUNT(*) FILTER (WHERE s.virtual_text ILIKE '%%virtual%%') AS virtual_schools,
        SUM(f.free_lunch_qualified) AS free_lunch_qualified,
        SUM(f.reduced_price_qualified) AS reduced_price_qualified,
        SUM(f.direct_certification) AS direct_certification,
        COUNT(*) FILTER (WHERE f.total_students IS NOT NULL) AS schools_with_enrollment
    FROM {SCHEMA}.dim_districts d
    LEFT JOIN {SCHEMA}.dim_schools s ON s.district_id = d.district_id AND s.school_year = d.school_year
    LEFT JOIN {SCHEMA}.fact_school_totals f ON f.school_id = s.school_id AND f.school_year = s.school_year
    GROUP BY d.school_year, d.state_name, d.state_abbr, d.district_id, d.district_name, d.operational_schools, d.total_students, d.total_teachers, d.ptr;

    CREATE VIEW {SCHEMA}.vw_dashboard_readiness AS
    SELECT 'dim_states' AS table_name, COUNT(*)::bigint AS row_count FROM {SCHEMA}.dim_states
    UNION ALL SELECT 'dim_districts', COUNT(*)::bigint FROM {SCHEMA}.dim_districts
    UNION ALL SELECT 'dim_schools', COUNT(*)::bigint FROM {SCHEMA}.dim_schools
    UNION ALL SELECT 'fact_school_totals', COUNT(*)::bigint FROM {SCHEMA}.fact_school_totals
    UNION ALL SELECT 'fact_grade_gender_enrollment', COUNT(*)::bigint FROM {SCHEMA}.fact_grade_gender_enrollment
    UNION ALL SELECT '{TABLE_MAP['sch_membership']}', COUNT(*)::bigint FROM {SCHEMA}.{TABLE_MAP['sch_membership']}
    UNION ALL SELECT '{TABLE_MAP['sch_staff']}', COUNT(*)::bigint FROM {SCHEMA}.{TABLE_MAP['sch_staff']}
    UNION ALL SELECT '{TABLE_MAP['sch_lunch']}', COUNT(*)::bigint FROM {SCHEMA}.{TABLE_MAP['sch_lunch']};
    """
    cur.execute(sql_text)


def main() -> int:
    if not ROOT.exists():
        print(f'ERROR: repo root not found: {ROOT}')
        return 1
    dirs = ensure_dirs()
    db = load_db_config()
    manifest = {}

    log('Preparing NCES 2024-25 Final 1a US load ...')
    for key, url in URLS.items():
        folder = dirs['docs'] if key in ('release_notes', 'school_notes') else dirs['raw']
        target = folder / url.split('/')[-1]
        download(url, target)
        manifest[key] = {'url': url, 'path': str(target), 'size_bytes': target.stat().st_size}

    extracted_csvs = {}
    for key in TABLE_MAP:
        zip_path = Path(manifest[key]['path'])
        out_dir = dirs['extracted'] / key
        files = unzip_file(zip_path, out_dir)
        csv_path = find_csv(files)
        extracted_csvs[key] = csv_path
        log(f'Extracted {key}: {csv_path.name}')

    report = {
        'run_started_at': now_utc(),
        'dashboard_year': DASHBOARD_YEAR,
        'schema': SCHEMA,
        'manifest': manifest,
        'staging': {},
        'marts': {},
    }

    with psycopg2.connect(**db) as conn:
        conn.autocommit = False
        with conn.cursor() as cur:
            cur.execute(sql.SQL('CREATE SCHEMA IF NOT EXISTS {}').format(sql.Identifier(SCHEMA)))
            for key, csv_path in extracted_csvs.items():
                log(f'Loading staging table for {key} ...')
                report['staging'][key] = load_stage_table(cur, key, csv_path)
                conn.commit()
            log('Building marts and views ...')
            build_marts(cur)
            conn.commit()

            for table in ['dim_states', 'dim_districts', 'dim_schools', 'fact_school_totals', 'fact_grade_gender_enrollment']:
                cur.execute(sql.SQL('SELECT COUNT(*) FROM {}.{}').format(sql.Identifier(SCHEMA), sql.Identifier(table)))
                report['marts'][table] = int(cur.fetchone()[0])

            cur.execute(f"SELECT state_name, total_schools, total_students, total_teachers, ptr FROM {SCHEMA}.vw_state_kpis_2024_2025 ORDER BY total_schools DESC NULLS LAST LIMIT 10")
            rows = cur.fetchall()
            report['sample_top_states'] = rows

    report['run_finished_at'] = now_utc()
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    out = dirs['reports'] / f'us_phase1_final_1a_load_report_{ts}.json'
    out.write_text(json.dumps(report, indent=2, default=str), encoding='utf-8')
    print(f'SUCCESS: US Phase 1 2024-25 Final 1a load completed.')
    print(f'Report: {out}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
