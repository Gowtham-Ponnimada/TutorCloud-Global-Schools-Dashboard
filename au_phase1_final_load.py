#!/usr/bin/env python3
"""
Australia 2025 Phase 1 loader scaffold.

Purpose:
- Download ACARA 2025 source workbooks
- Load staging tables in schema `au`
- Build cleaned temp tables, dims, facts, and views
- Emit a JSON load report

This scaffold is designed to be adapted into the TutorCloud repo with minimal edits.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

import pandas as pd
import requests
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

REPO_ROOT = Path(__file__).resolve().parent
RAW_DIR = REPO_ROOT / "data" / "au" / "final_2025" / "raw"
REPORT_DIR = REPO_ROOT / "reports" / "au"
SQL_DIR = REPO_ROOT / "sql"
SCHOOL_YEAR = "2025"
SCHEMA = "au"
COUNTRY = "Australia"

SOURCE_FILES = {
    "school_profile": {
        "file_name": "School Profile 2025.xlsx",
        "url": "https://dataandreporting.blob.core.windows.net/anrdataportal/Data-Access-Program/School%20Profile%202025.xlsx",
        "sheet": "SchoolProfile 2025",
    },
    "school_location": {
        "file_name": "School Location 2025.xlsx",
        "url": "https://dataandreporting.blob.core.windows.net/anrdataportal/Data-Access-Program/School%20Location%202025.xlsx",
        "sheet": "SchoolLocations 2025",
    },
    "enrolments_by_grade": {
        "file_name": "Enrolments by Grade 2025.xlsx",
        "url": "https://dataandreporting.blob.core.windows.net/anrdataportal/Data-Access-Program/Enrolments%20by%20Grade%202025.xlsx",
        "sheet": "EnrolmentsByGrade 2025",
    },
}

PROFILE_COL_MAP = {
    "Calendar Year": "calendar_year",
    "ACARA SML ID": "acara_sml_id",
    "Location AGE ID": "location_age_id",
    "School AGE ID": "school_age_id",
    "School Name": "school_name",
    "Suburb": "suburb",
    "State": "state",
    "Postcode": "postcode",
    "School Sector": "school_sector",
    "School Type": "school_type",
    "Campus Type": "campus_type",
    "Rolled Reporting Description": "rolled_reporting_description",
    "School URL": "school_url",
    "Governing Body": "governing_body",
    "Governing Body URL": "governing_body_url",
    "Year Range": "year_range",
    "Geolocation": "geolocation",
    "ICSEA": "icsea",
    "ICSEA Percentile": "icsea_percentile",
    "Bottom SEA Quarter (%)": "sea_bottom_pct",
    "Lower Middle SEA Quarter (%)": "sea_lower_middle_pct",
    "Upper Middle SEA Quarter (%)": "sea_upper_middle_pct",
    "Top SEA Quarter (%)": "sea_top_pct",
    "Teaching Staff": "teaching_staff",
    "Full Time Equivalent Teaching Staff": "fte_teaching_staff",
    "Non-Teaching Staff": "non_teaching_staff",
    "Full Time Equivalent Non-Teaching Staff": "fte_non_teaching_staff",
    "Total Enrolments": "total_enrolments",
    "Girls Enrolments": "girls_enrolments",
    "Boys Enrolments": "boys_enrolments",
    "Full Time Equivalent Enrolments": "fte_enrolments",
    "Indigenous Enrolments (%)": "indigenous_enrolments_pct",
    "Language Background Other Than English - Yes (%)": "lbote_yes_pct",
    "Language Background Other Than English - No (%)": "lbote_no_pct",
    "Language Background Other Than English - Not Stated (%)": "lbote_not_stated_pct",
}

LOCATION_COL_MAP = {
    "Calendar Year": "calendar_year",
    "ACARA SML ID": "acara_sml_id",
    "Location AGE ID": "location_age_id",
    "School AGE ID": "school_age_id",
    "Rolled School ID": "rolled_school_id",
    "School Name": "school_name",
    "School Sector": "school_sector",
    "School Type": "school_type",
    "Special school": "special_school",
    "Campus Type": "campus_type",
    "Suburb": "suburb",
    "State": "state",
    "Postcode": "postcode",
    "Latitude": "latitude",
    "Longitude": "longitude",
    "ABS Remoteness Area": "abs_remoteness_area",
    "ABS Remoteness Area Name": "abs_remoteness_area_name",
    "Meshblock": "meshblock",
    "Statistical Area 1": "sa1_code",
    "Statistical Area 2": "sa2_code",
    "Statistical Area 2 Name": "sa2_name",
    "Statistical Area 3": "sa3_code",
    "Statistical Area 3 Name": "sa3_name",
    "Statistical Area 4": "sa4_code",
    "Statistical Area 4 Name": "sa4_name",
    "Local Government Area": "lga_code",
    "Local Government Area Name": "lga_name",
    "State Electoral Divisions": "state_electoral_division_code",
    "State Electoral Divisions Name": "state_electoral_division_name",
    "Commonwealth Electoral Divisions": "commonwealth_electoral_division_code",
    "Commonwealth Electoral Divisions Name": "commonwealth_electoral_division_name",
}

GRADE_COL_MAP = {
    "Calendar Year": "calendar_year",
    "ACARA SML ID": "acara_sml_id",
    "Location AGE ID": "location_age_id",
    "School AGE ID": "school_age_id",
    "School Name": "school_name",
    "Suburb": "suburb",
    "State": "state",
    "Postcode": "postcode",
    "School Sector": "school_sector",
    "School Type": "school_type",
    "Campus Type": "campus_type",
    "Rolled Reporting Description": "rolled_reporting_description",
    "Two years before Year 1 Offered": "pre_year1_2_offered",
    "Two years before Year 1 Enrolments": "pre_year1_2_enrolments",
    "One year before Year 1 Offered": "pre_year1_1_offered",
    "One year before Year 1 Enrolments": "pre_year1_1_enrolments",
    "Year 1 Offered": "year_1_offered",
    "Year 1 Enrolments": "year_1_enrolments",
    "Year 2 Offered": "year_2_offered",
    "Year 2 Enrolments": "year_2_enrolments",
    "Year 3 Offered": "year_3_offered",
    "Year 3 Enrolments": "year_3_enrolments",
    "Year 4 Offered": "year_4_offered",
    "Year 4 Enrolments": "year_4_enrolments",
    "Year 5 Offered": "year_5_offered",
    "Year 5 Enrolments": "year_5_enrolments",
    "Year 6 Offered": "year_6_offered",
    "Year 6 Enrolments": "year_6_enrolments",
    "Year 7 Offered": "year_7_offered",
    "Year 7 Enrolments": "year_7_enrolments",
    "Year 8 Offered": "year_8_offered",
    "Year 8 Enrolments": "year_8_enrolments",
    "Year 9 Offered": "year_9_offered",
    "Year 9 Enrolments": "year_9_enrolments",
    "Year 10 Offered": "year_10_offered",
    "Year 10 Enrolments": "year_10_enrolments",
    "Year 11 Offered": "year_11_offered",
    "Year 11 Enrolments": "year_11_enrolments",
    "Year 12 Offered": "year_12_offered",
    "Year 12 Enrolments": "year_12_enrolments",
    "Primary Ungraded Offered": "primary_ungraded_offered",
    "Primary Ungraded Enrolments": "primary_ungraded_enrolments",
    "Secondary Ungraded Offered": "secondary_ungraded_offered",
    "Secondary Ungraded Enrolments": "secondary_ungraded_enrolments",
    "Total Enrolments": "total_enrolments",
}

GRADE_SPECS = [
    ("PRE2", "Two years before Year 1", 0, "pre_year1_2_offered", "pre_year1_2_enrolments"),
    ("PRE1", "One year before Year 1", 1, "pre_year1_1_offered", "pre_year1_1_enrolments"),
    ("Y1", "Year 1", 2, "year_1_offered", "year_1_enrolments"),
    ("Y2", "Year 2", 3, "year_2_offered", "year_2_enrolments"),
    ("Y3", "Year 3", 4, "year_3_offered", "year_3_enrolments"),
    ("Y4", "Year 4", 5, "year_4_offered", "year_4_enrolments"),
    ("Y5", "Year 5", 6, "year_5_offered", "year_5_enrolments"),
    ("Y6", "Year 6", 7, "year_6_offered", "year_6_enrolments"),
    ("Y7", "Year 7", 8, "year_7_offered", "year_7_enrolments"),
    ("Y8", "Year 8", 9, "year_8_offered", "year_8_enrolments"),
    ("Y9", "Year 9", 10, "year_9_offered", "year_9_enrolments"),
    ("Y10", "Year 10", 11, "year_10_offered", "year_10_enrolments"),
    ("Y11", "Year 11", 12, "year_11_offered", "year_11_enrolments"),
    ("Y12", "Year 12", 13, "year_12_offered", "year_12_enrolments"),
    ("PUG", "Primary Ungraded", 14, "primary_ungraded_offered", "primary_ungraded_enrolments"),
    ("SUG", "Secondary Ungraded", 15, "secondary_ungraded_offered", "secondary_ungraded_enrolments"),
]


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def ensure_dirs() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)


def read_env_file(env_path: Path) -> Dict[str, str]:
    env = {}
    if not env_path.exists():
        return env
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def db_engine() -> Engine:
    env = read_env_file(REPO_ROOT / ".env")
    host = os.getenv("DB_HOST") or env.get("DB_HOST")
    port = os.getenv("DB_PORT") or env.get("DB_PORT", "5432")
    name = os.getenv("DB_NAME") or env.get("DB_NAME")
    user = os.getenv("DB_USER") or env.get("DB_USER")
    password = os.getenv("DB_PASSWORD") or env.get("DB_PASSWORD")
    if not all([host, port, name, user, password]):
        raise RuntimeError("Missing DB credentials. Expected DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD.")
    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}"
    return create_engine(url, future=True)


def sha256sum(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, dest: Path) -> None:
    r = requests.get(url, stream=True, timeout=120)
    r.raise_for_status()
    with dest.open("wb") as f:
        for chunk in r.iter_content(1024 * 1024):
            if chunk:
                f.write(chunk)


def normalize_strings(df: pd.DataFrame) -> pd.DataFrame:
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].map(lambda x: x.strip() if isinstance(x, str) else x)
            df[col] = df[col].replace({"": None})
    return df


def normalize_headers(df: pd.DataFrame, col_map: Dict[str, str]) -> pd.DataFrame:
    df = df.rename(columns=col_map)
    return df[[c for c in col_map.values() if c in df.columns]].copy()


def add_metadata(df: pd.DataFrame, load_id: str, meta: Dict[str, str]) -> pd.DataFrame:
    df = df.copy()
    df.insert(0, "load_id", load_id)
    df.insert(1, "source_file_name", meta["file_name"])
    df.insert(2, "source_file_url", meta["url"])
    df.insert(3, "source_sheet_name", meta["sheet"])
    df.insert(4, "source_row_num", range(2, len(df) + 2))
    return df


def audit_source(conn, load_id: str, meta: Dict[str, str], file_path: Path, row_count: int | None = None) -> None:
    conn.execute(text(
        """
        INSERT INTO au.audit_source_files (
            load_id, source_system, source_file_name, source_file_url, source_sheet_name,
            source_file_size_bytes, source_checksum, row_count_loaded
        ) VALUES (
            :load_id, 'ACARA_2025', :source_file_name, :source_file_url, :source_sheet_name,
            :source_file_size_bytes, :source_checksum, :row_count_loaded
        )
        """
    ), {
        "load_id": load_id,
        "source_file_name": meta["file_name"],
        "source_file_url": meta["url"],
        "source_sheet_name": meta["sheet"],
        "source_file_size_bytes": file_path.stat().st_size,
        "source_checksum": sha256sum(file_path),
        "row_count_loaded": row_count,
    })


def load_stage_table(conn, table_name: str, df: pd.DataFrame) -> int:
    df.to_sql(table_name.split(".")[-1], conn, schema=SCHEMA, if_exists="append", index=False, method="multi", chunksize=2000)
    return len(df)


def reset_stage_rows(conn, load_id: str) -> None:
    # These staging tables are dedicated to AU 2025 loads, so truncate fully to avoid duplicates
    # from prior failed / partial runs with different load_ids.
    conn.execute(text("TRUNCATE TABLE au.stg_school_profile_2025 RESTART IDENTITY"))
    conn.execute(text("TRUNCATE TABLE au.stg_school_location_2025 RESTART IDENTITY"))
    conn.execute(text("TRUNCATE TABLE au.stg_enrolments_by_grade_2025 RESTART IDENTITY"))


def build_tmp_profile_clean(conn) -> None:
    conn.execute(text((SQL_DIR / "au_build_templates.sql").read_text(encoding="utf-8").split("-- 2) Clean location")[0]))


def build_tmp_location_clean_and_canonical(conn) -> None:
    full = (SQL_DIR / "au_build_templates.sql").read_text(encoding="utf-8")
    loc_part = "-- 2) Clean location\n" + full.split("-- 2) Clean location\n", 1)[1]
    conn.execute(text(loc_part))


def boolify(v):
    if pd.isna(v):
        return None
    s = str(v).strip().lower()
    if s in {"1", "y", "yes", "true"}:
        return True
    if s in {"0", "n", "no", "false"}:
        return False
    return None


def int_or_none(v):
    if pd.isna(v) or v in (None, ""):
        return None
    try:
        return int(float(str(v).replace(",", "")))
    except Exception:
        return None


def build_tmp_grade_long(conn) -> None:
    conn.execute(text("DROP TABLE IF EXISTS au.tmp_grade_wide_clean"))
    conn.execute(text("DROP TABLE IF EXISTS au.tmp_grade_long"))
    conn.execute(text("CREATE TABLE au.tmp_grade_wide_clean AS SELECT * FROM au.stg_enrolments_by_grade_2025"))
    conn.execute(text(
        """
        CREATE TABLE au.tmp_grade_long (
            acara_sml_id TEXT,
            school_age_id TEXT,
            grade_code TEXT,
            grade_label TEXT,
            grade_sort_order INTEGER,
            offered_flag BOOLEAN,
            enrolled_students INTEGER
        )
        """
    ))
    df = pd.read_sql("SELECT * FROM au.stg_enrolments_by_grade_2025", conn)
    out_rows: List[dict] = []
    for _, row in df.iterrows():
        for grade_code, grade_label, sort_order, offered_col, enrol_col in GRADE_SPECS:
            out_rows.append({
                "acara_sml_id": row.get("acara_sml_id"),
                "school_age_id": row.get("school_age_id"),
                "grade_code": grade_code,
                "grade_label": grade_label,
                "grade_sort_order": sort_order,
                "offered_flag": boolify(row.get(offered_col)),
                "enrolled_students": int_or_none(row.get(enrol_col)),
            })
    out = pd.DataFrame(out_rows)
    # IMPORTANT: use the same transactional connection, not conn, to avoid
    # cross-connection locks on the just-created table.
    out.to_sql("tmp_grade_long", conn, schema=SCHEMA, if_exists="append", index=False, method="multi", chunksize=5000)


def build_dims_and_facts(conn) -> None:
    conn.execute(text("DELETE FROM au.dim_states WHERE school_year = '2025'"))
    conn.execute(text(
        """
        INSERT INTO au.dim_states (country_name, school_year, state_abbr, state_name, display_order, is_active)
        SELECT 'Australia', '2025', state_abbr, state_name, display_order, TRUE
        FROM au.map_state_codes
        ON CONFLICT (school_year, state_abbr) DO UPDATE
        SET state_name = EXCLUDED.state_name,
            display_order = EXCLUDED.display_order,
            is_active = EXCLUDED.is_active
        """
    ))

    conn.execute(text("DELETE FROM au.dim_districts WHERE school_year = '2025'"))
    conn.execute(text(
        """
        INSERT INTO au.dim_districts (
            country_name, school_year, state_abbr, state_name,
            district_id, district_name, district_type, lga_code, source_system, school_count
        )
        SELECT
            'Australia', '2025', lc.state_abbr, sc.state_name,
            lc.state_abbr || ':' || COALESCE(NULLIF(lc.lga_code, ''), md5(lc.state_abbr || '|' || COALESCE(lc.lga_name, 'Unknown LGA'))),
            COALESCE(NULLIF(lc.lga_name, ''), 'Unknown LGA'),
            'LGA', lc.lga_code, 'ACARA_School_Location_2025', COUNT(*)
        FROM au.tmp_location_rolled_canonical lc
        LEFT JOIN au.map_state_codes sc ON lc.state_abbr = sc.state_abbr
        GROUP BY 1,2,3,4,5,6,7,8,9
        """
    ))

    conn.execute(text("DELETE FROM au.dim_schools WHERE school_year = '2025'"))
    conn.execute(text(
        """
        INSERT INTO au.dim_schools (
            country_name, school_year, source_system, source_school_year,
            school_id, acara_sml_id, rolled_school_id, location_age_id, school_age_id,
            school_name, state_abbr, state_name, district_id, district_name, district_type,
            city_name, suburb, postcode, lga_code, lga_name, abs_remoteness_area_code,
            abs_remoteness_area_name, sa1_code, sa2_code, sa2_name, sa3_code, sa3_name,
            sa4_code, sa4_name, latitude, longitude, management_type, management_group,
            school_level, school_type_raw, campus_type, reporting_model, special_school_flag,
            governing_body, governing_body_url, school_url, year_range, geolocation_label,
            icsea, icsea_percentile, sea_bottom_pct, sea_lower_middle_pct, sea_upper_middle_pct,
            sea_top_pct, teaching_staff, fte_teaching_staff, non_teaching_staff,
            fte_non_teaching_staff, total_students, girls_students, boys_students, fte_students,
            indigenous_pct, lbote_yes_pct, lbote_no_pct, lbote_not_stated_pct,
            student_teacher_ratio, data_quality_flag, is_reportable
        )
        SELECT
            'Australia', '2025', 'ACARA_2025', '2025',
            COALESCE(NULLIF(lc.rolled_school_id, ''), NULLIF(pc.acara_sml_id, ''), NULLIF(pc.school_age_id, '')) AS school_id,
            pc.acara_sml_id, lc.rolled_school_id, COALESCE(pc.location_age_id, lc.location_age_id),
            COALESCE(pc.school_age_id, lc.school_age_id), COALESCE(pc.school_name, lc.school_name),
            COALESCE(pc.state_abbr, lc.state_abbr), sc.state_name,
            COALESCE(pc.state_abbr, lc.state_abbr) || ':' || COALESCE(NULLIF(lc.lga_code, ''), md5(COALESCE(pc.state_abbr, lc.state_abbr) || '|' || COALESCE(lc.lga_name, 'Unknown LGA'))),
            COALESCE(NULLIF(lc.lga_name, ''), 'Unknown LGA'), 'LGA',
            lc.suburb, lc.suburb, COALESCE(pc.postcode, lc.postcode), lc.lga_code, lc.lga_name,
            lc.abs_remoteness_area, lc.abs_remoteness_area_name, lc.sa1_code, lc.sa2_code,
            lc.sa2_name, lc.sa3_code, lc.sa3_name, lc.sa4_code, lc.sa4_name, lc.latitude,
            lc.longitude,
            COALESCE(pc.management_type,
                CASE
                    WHEN lc.school_sector_raw IN ('Government', 'G') THEN 'Government'
                    WHEN lc.school_sector_raw IN ('Catholic', 'C') THEN 'Catholic'
                    WHEN lc.school_sector_raw IN ('Independent', 'I') THEN 'Independent'
                END),
            COALESCE(pc.management_type,
                CASE
                    WHEN lc.school_sector_raw IN ('Government', 'G') THEN 'Government'
                    WHEN lc.school_sector_raw IN ('Catholic', 'C') THEN 'Catholic'
                    WHEN lc.school_sector_raw IN ('Independent', 'I') THEN 'Independent'
                END),
            COALESCE(pc.school_level,
                CASE
                    WHEN lc.school_type_raw = 'Primary' THEN 'Primary'
                    WHEN lc.school_type_raw = 'Secondary' THEN 'Secondary'
                    WHEN lc.school_type_raw = 'Combined' THEN 'Combined'
                    WHEN lc.school_type_raw = 'Special' THEN 'Special'
                END),
            COALESCE(pc.school_type_raw, lc.school_type_raw), COALESCE(pc.campus_type, lc.campus_type),
            pc.reporting_model,
            CASE
                WHEN LOWER(COALESCE(lc.special_school, '')) IN ('yes', 'y', '1', 'true') THEN TRUE
                WHEN COALESCE(pc.school_level, lc.school_type_raw) = 'Special' THEN TRUE
                ELSE FALSE
            END,
            pc.governing_body, pc.governing_body_url, pc.school_url, pc.year_range, pc.geolocation_label,
            pc.icsea, pc.icsea_percentile, pc.sea_bottom_pct, pc.sea_lower_middle_pct,
            pc.sea_upper_middle_pct, pc.sea_top_pct, pc.teaching_staff, pc.fte_teaching_staff,
            pc.non_teaching_staff, pc.fte_non_teaching_staff, pc.total_students, pc.girls_students,
            pc.boys_students, pc.fte_students, pc.indigenous_pct, pc.lbote_yes_pct, pc.lbote_no_pct,
            pc.lbote_not_stated_pct,
            CASE WHEN COALESCE(pc.fte_teaching_staff, 0) > 0 THEN ROUND(pc.total_students::NUMERIC / pc.fte_teaching_staff, 4) END,
            CASE
                WHEN lc.latitude IS NULL OR lc.longitude IS NULL THEN 'MISSING_COORDINATES'
                WHEN lc.lga_name IS NULL OR BTRIM(lc.lga_name) = '' THEN 'MISSING_LGA'
                ELSE 'OK'
            END,
            TRUE
        FROM au.tmp_profile_clean pc
        LEFT JOIN au.tmp_location_rolled_canonical lc
          ON COALESCE(NULLIF(lc.rolled_school_id, ''), NULLIF(lc.acara_sml_id, ''), NULLIF(lc.school_age_id, ''))
           = COALESCE(NULLIF(pc.acara_sml_id, ''), NULLIF(pc.school_age_id, ''))
        LEFT JOIN au.map_state_codes sc
          ON COALESCE(pc.state_abbr, lc.state_abbr) = sc.state_abbr
        """
    ))

    conn.execute(text("DELETE FROM au.fact_school_totals WHERE school_year = '2025'"))
    conn.execute(text(
        """
        INSERT INTO au.fact_school_totals (
            country_name, school_year, school_id, source_system, state_abbr, district_id,
            management_type, school_level, total_students, girls_students, boys_students,
            fte_students, teaching_staff, fte_teaching_staff, non_teaching_staff,
            fte_non_teaching_staff, student_teacher_ratio, indigenous_pct, lbote_yes_pct,
            lbote_no_pct, lbote_not_stated_pct, icsea, icsea_percentile,
            sea_bottom_pct, sea_lower_middle_pct, sea_upper_middle_pct, sea_top_pct
        )
        SELECT
            country_name, school_year, school_id, source_system, state_abbr, district_id,
            management_type, school_level, total_students, girls_students, boys_students,
            fte_students, teaching_staff, fte_teaching_staff, non_teaching_staff,
            fte_non_teaching_staff, student_teacher_ratio, indigenous_pct, lbote_yes_pct,
            lbote_no_pct, lbote_not_stated_pct, icsea, icsea_percentile,
            sea_bottom_pct, sea_lower_middle_pct, sea_upper_middle_pct, sea_top_pct
        FROM au.dim_schools
        WHERE school_year = '2025'
        """
    ))

    conn.execute(text("DELETE FROM au.fact_grade_enrollment WHERE school_year = '2025'"))
    conn.execute(text(
        """
        INSERT INTO au.fact_grade_enrollment (
            country_name, school_year, school_id, state_abbr, district_id,
            management_type, school_level, source_system,
            grade_code, grade_label, grade_sort_order,
            offered_flag, enrolled_students, suppressed_flag
        )
        SELECT
            'Australia', '2025', ds.school_id, ds.state_abbr, ds.district_id,
            ds.management_type, ds.school_level, 'ACARA_2025',
            gl.grade_code, gl.grade_label, gl.grade_sort_order,
            gl.offered_flag, gl.enrolled_students,
            CASE WHEN gl.enrolled_students IS NULL AND gc.total_enrolments::text ~ '^[0-9]+$' AND gc.total_enrolments::int < 5 THEN TRUE ELSE FALSE END
        FROM au.tmp_grade_long gl
        JOIN au.dim_schools ds
          ON ds.school_year = '2025'
         AND ds.school_id = COALESCE(NULLIF(gl.acara_sml_id, ''), NULLIF(gl.school_age_id, ''))
        LEFT JOIN au.stg_enrolments_by_grade_2025 gc
          ON COALESCE(NULLIF(gl.acara_sml_id, ''), NULLIF(gl.school_age_id, '')) = COALESCE(NULLIF(gc.acara_sml_id, ''), NULLIF(gc.school_age_id, ''))
        """
    ))


def run_qa(conn) -> dict:
    out = {}
    out["dim_schools"] = conn.execute(text("SELECT COUNT(*) FROM au.dim_schools WHERE school_year='2025'" )).scalar_one()
    out["fact_school_totals"] = conn.execute(text("SELECT COUNT(*) FROM au.fact_school_totals WHERE school_year='2025'" )).scalar_one()
    out["fact_grade_enrollment"] = conn.execute(text("SELECT COUNT(*) FROM au.fact_grade_enrollment WHERE school_year='2025'" )).scalar_one()
    out["states"] = conn.execute(text("SELECT COUNT(*) FROM au.dim_states WHERE school_year='2025'" )).scalar_one()
    return out


def main() -> int:
    ensure_dirs()
    load_id = f"au_2025_{now_utc()}_{uuid.uuid4().hex[:8]}"
    report = {"load_id": load_id, "country": COUNTRY, "school_year": SCHOOL_YEAR, "downloads": {}, "staging": {}, "qa": {}}

    for meta in SOURCE_FILES.values():
        target = RAW_DIR / meta["file_name"]
        if not target.exists():
            print(f"Downloading {meta['file_name']}...")
            download(meta["url"], target)
        report["downloads"][meta["file_name"]] = {"path": str(target), "size": target.stat().st_size, "sha256": sha256sum(target)}

    engine = db_engine()
    with engine.begin() as conn:
        reset_stage_rows(conn, load_id)

        profile = add_metadata(normalize_strings(normalize_headers(pd.read_excel(RAW_DIR / SOURCE_FILES["school_profile"]["file_name"], sheet_name=SOURCE_FILES["school_profile"]["sheet"]), PROFILE_COL_MAP)), load_id, SOURCE_FILES["school_profile"])
        location = add_metadata(normalize_strings(normalize_headers(pd.read_excel(RAW_DIR / SOURCE_FILES["school_location"]["file_name"], sheet_name=SOURCE_FILES["school_location"]["sheet"]), LOCATION_COL_MAP)), load_id, SOURCE_FILES["school_location"])
        grade = add_metadata(normalize_strings(normalize_headers(pd.read_excel(RAW_DIR / SOURCE_FILES["enrolments_by_grade"]["file_name"], sheet_name=SOURCE_FILES["enrolments_by_grade"]["sheet"]), GRADE_COL_MAP)), load_id, SOURCE_FILES["enrolments_by_grade"])

        report["staging"]["stg_school_profile_2025"] = load_stage_table(conn, "au.stg_school_profile_2025", profile)
        report["staging"]["stg_school_location_2025"] = load_stage_table(conn, "au.stg_school_location_2025", location)
        report["staging"]["stg_enrolments_by_grade_2025"] = load_stage_table(conn, "au.stg_enrolments_by_grade_2025", grade)

        for meta in SOURCE_FILES.values():
            audit_source(conn, load_id, meta, RAW_DIR / meta["file_name"], None)

        build_tmp_profile_clean(conn)
        build_tmp_location_clean_and_canonical(conn)
        build_tmp_grade_long(conn)
        build_dims_and_facts(conn)
        report["qa"] = run_qa(conn)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / f"au_phase1_final_load_report_{now_utc()}.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"Report written to {report_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
