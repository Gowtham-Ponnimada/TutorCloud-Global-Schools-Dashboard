#!/usr/bin/env python3
"""
UAE ETL Pipeline — TutorCloud Global Schools Dashboard
Loads all UAE Ministry of Education CSV files into PostgreSQL.

Usage:
    python3 uae_etl_pipeline.py

Pre-requisites:
    pip install pandas psycopg2-binary sqlalchemy python-dotenv
    Place all CSV files in DATA_DIR before running.
    Run uae_schema_ddl.sql first.
"""

import os
import sys
import time
import logging
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# ── Config ────────────────────────────────────────────────────────────────────
load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "tutorcloud_db")
DB_USER = os.getenv("DB_USER", "tutorcloud_admin")
DB_PASS = os.getenv("DB_PASSWORD", os.getenv("DB_PASS", ""))

DATA_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "data", "uae"
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("uae_etl")

# ── Region normalisation map ──────────────────────────────────────────────────
# Old 7-emirate names → New 10-zone names used in 2020+ datasets
REGION_NORM = {
    "abu dhabi":   "ABU DHABI",
    "ajman":       "AJMAN",
    "dubai":       "DUBAI",
    "fujairah":    "AL FUJAIRAH",
    "ras alkhaimah": "Ras Al Khaimah",
    "ras al khaimah": "Ras Al Khaimah",
    "sharjah":     "SHARJAH",
    "umm alquwain": "Umm Al Quwain",
    "umm al quwain": "Umm Al Quwain",
}

def norm_region(val):
    if pd.isna(val): return val
    return REGION_NORM.get(str(val).strip().lower(), str(val).strip())

# ── Utility helpers ───────────────────────────────────────────────────────────
def load_csv(fname, encoding="utf-8-sig"):
    """Load CSV with fallback encodings; strip all column names."""
    path = os.path.join(DATA_DIR, fname)
    if not os.path.exists(path):
        log.warning("FILE NOT FOUND — skipping: %s", path)
        return pd.DataFrame()
    for enc in [encoding, "utf-8", "latin-1", "cp1256"]:
        try:
            df = pd.read_csv(path, encoding=enc, low_memory=False)
            df.columns = df.columns.str.strip()
            log.info("  Loaded %-55s  %s rows", fname, f"{len(df):,}")
            return df
        except Exception:
            continue
    log.error("Could not read %s with any encoding", fname)
    return pd.DataFrame()

def parse_pct(val):
    """'87.45%' → 87.45  |  NaN → None"""
    if pd.isna(val): return None
    return float(str(val).replace("%", "").strip())

def parse_num(val):
    """' 84,852 ' → 84852"""
    if pd.isna(val): return 0
    return int(str(val).replace(",", "").strip() or 0)

def to_db(df, table, engine, chunksize=2000):
    """Truncate-and-reload a table."""
    with engine.connect() as conn:
        conn.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE"))
        conn.commit()
    df.to_sql(table, engine, if_exists="append", index=False, chunksize=chunksize)
    log.info("  ✅  %-50s  %s rows written", table, f"{len(df):,}")

# ── ETL functions ─────────────────────────────────────────────────────────────

def etl_enrollment(engine):
    """Students_Enrolled_Public_Private.csv → uae_fact_enrollment"""
    df = load_csv("Students_Enrolled_Public_Private.csv")
    if df.empty: return

    df.columns = [
        "academic_year", "edu_type_ar", "education_type",
        "region_ar",     "region_en",
        "cycle_ar",      "cycle",
        "grade_ar",      "grade",
        "gender_ar",     "gender",
        "nat_cat_ar",    "nationality_cat",
        "student_count",
    ]
    df = df[[
        "academic_year", "region_en", "education_type",
        "cycle", "grade", "gender", "nationality_cat", "student_count"
    ]].copy()
    df["region_en"]     = df["region_en"].apply(norm_region)
    df["student_count"] = pd.to_numeric(df["student_count"], errors="coerce").fillna(0).astype(int)
    df.dropna(subset=["academic_year", "region_en"], inplace=True)
    to_db(df, "uae_fact_enrollment", engine)


def etl_teachers_emirate(engine):
    """Teachers_Admin_Gender_Nationality_Emirate.csv → uae_fact_teachers_emirate"""
    df = load_csv("Teachers_Admin_Gender_Nationality_Emirate.csv")
    if df.empty: return

    df.columns = [
        "academic_year", "edu_type_ar", "education_type",
        "region_ar", "region_en",
        "gender_ar", "gender",
        "nat_cat_ar", "nationality_cat",
        "staff_count", "teacher_count",
    ]
    df = df[[
        "academic_year", "region_en", "education_type",
        "gender", "nationality_cat", "staff_count", "teacher_count"
    ]].copy()
    df["region_en"]     = df["region_en"].apply(norm_region)
    df["staff_count"]   = pd.to_numeric(df["staff_count"],   errors="coerce").fillna(0).astype(int)
    df["teacher_count"] = pd.to_numeric(df["teacher_count"], errors="coerce").fillna(0).astype(int)
    df.dropna(subset=["academic_year", "region_en"], inplace=True)
    to_db(df, "uae_fact_teachers_emirate", engine)


def etl_teachers_subject(engine):
    """Number_of_Teachers_by_Subject.csv → uae_fact_teachers_subject"""
    df = load_csv("Number_of_Teachers_by_Subject.csv")
    if df.empty: return

    df.columns = [
        "academic_year", "edu_type_ar", "education_type",
        "region_ar", "region_en",
        "subject_ar", "subject_en",
        "teacher_count",
    ]
    df = df[[
        "academic_year", "region_en", "education_type",
        "subject_en", "teacher_count"
    ]].copy()
    df["region_en"]     = df["region_en"].apply(norm_region)
    df["teacher_count"] = pd.to_numeric(df["teacher_count"], errors="coerce").fillna(0).astype(int)
    df.dropna(subset=["academic_year", "region_en"], inplace=True)
    to_db(df, "uae_fact_teachers_subject", engine)


def etl_schools(engine):
    """Schools_by_Emirate_Curriculum_Gender.csv → uae_fact_schools"""
    df = load_csv("Schools_by_Emirate_Curriculum_Gender.csv")
    if df.empty: return

    df.columns = [
        "academic_year", "edu_type_ar", "education_type",
        "region_ar", "region_en",
        "curriculum_ar", "curriculum_en",
        "gender_ar", "student_gender",
        "school_count",
    ]
    df = df[[
        "academic_year", "region_en", "education_type",
        "curriculum_en", "student_gender", "school_count"
    ]].copy()
    df["region_en"]    = df["region_en"].apply(norm_region)
    df["school_count"] = pd.to_numeric(df["school_count"], errors="coerce").fillna(0).astype(int)
    df.dropna(subset=["academic_year", "region_en"], inplace=True)
    to_db(df, "uae_fact_schools", engine)


def etl_pass_fail(engine):
    """Pass_and_Fail_Rates.csv → uae_fact_pass_fail"""
    df = load_csv("Pass_and_Fail_Rates.csv")
    if df.empty: return

    df.columns = [
        "academic_year", "edu_type_ar", "education_type",
        "region_ar", "region_en",
        "cycle_ar", "cycle",
        "grade_ar", "grade",
        "gender_ar", "gender",
        "nat_cat_ar", "nationality_cat",
        "pass_percentage", "student_count",
    ]
    df = df[[
        "academic_year", "region_en", "education_type",
        "cycle", "grade", "gender", "nationality_cat",
        "pass_percentage", "student_count"
    ]].copy()
    df["region_en"]       = df["region_en"].apply(norm_region)
    df["pass_percentage"] = df["pass_percentage"].apply(parse_pct)
    df["student_count"]   = pd.to_numeric(df["student_count"], errors="coerce").fillna(0).astype(int)
    df.dropna(subset=["academic_year", "region_en"], inplace=True)
    to_db(df, "uae_fact_pass_fail", engine)


def etl_student_scores(engine):
    """Average_Student_Scores.csv → uae_fact_student_scores  (34,501 rows)"""
    df = load_csv("Average_Student_Scores.csv")
    if df.empty: return

    df.columns = [
        "academic_year", "edu_type_ar", "education_type",
        "region_ar", "region_en",
        "cycle_ar", "cycle",
        "grade_ar", "grade",
        "gender_ar", "gender",
        "nat_cat_ar", "nationality_cat",
        "subject_ar", "subject_en",
        "assessment_ar", "assessment_type",
        "student_count", "pass_percentage", "avg_score_band",
    ]
    df = df[[
        "academic_year", "region_en", "education_type",
        "cycle", "grade", "gender", "nationality_cat",
        "subject_en", "assessment_type",
        "student_count", "pass_percentage", "avg_score_band"
    ]].copy()
    df["region_en"]       = df["region_en"].apply(norm_region)
    df["pass_percentage"] = df["pass_percentage"].apply(parse_pct)
    df["student_count"]   = pd.to_numeric(df["student_count"], errors="coerce").fillna(0).astype(int)
    df.dropna(subset=["academic_year", "region_en"], inplace=True)
    to_db(df, "uae_fact_student_scores", engine, chunksize=5000)


def etl_student_nationalities(engine):
    """GE_Students_Nationalities.csv → uae_fact_student_nationalities"""
    df = load_csv("GE_Students_Nationalities.csv")
    if df.empty: return

    df.columns = ["academic_year", "nationality_en", "student_count"]
    df = df[["academic_year", "nationality_en", "student_count"]].copy()
    df["student_count"] = pd.to_numeric(df["student_count"], errors="coerce").fillna(0).astype(int)
    df.dropna(subset=["academic_year"], inplace=True)
    to_db(df, "uae_fact_student_nationalities", engine)


def etl_ge_teachers(engine):
    """GE_Teachers.csv → uae_fact_ge_teachers  (national-level summary)"""
    df = load_csv("GE_Teachers.csv")
    if df.empty: return

    df.columns = ["academic_year", "gender", "job_category", "nationality", "total_teachers"]
    df = df[["academic_year", "gender", "nationality", "total_teachers"]].copy()
    df["total_teachers"] = pd.to_numeric(df["total_teachers"], errors="coerce").fillna(0).astype(int)
    df.dropna(subset=["academic_year"], inplace=True)
    to_db(df, "uae_fact_ge_teachers", engine)


def etl_ge_staff(engine):
    """GE_Staff.csv → uae_fact_ge_staff  (national-level summary)"""
    df = load_csv("GE_Staff.csv")
    if df.empty: return

    df.columns = ["academic_year", "gender", "job_category", "nationality", "total_staff"]
    df = df[["academic_year", "gender", "job_category", "nationality", "total_staff"]].copy()
    df["total_staff"] = pd.to_numeric(df["total_staff"], errors="coerce").fillna(0).astype(int)
    df.dropna(subset=["academic_year"], inplace=True)
    to_db(df, "uae_fact_ge_staff", engine)


def etl_ge_schools(engine):
    """GE_Public_Schools.csv + GE_Private_Schools.csv → uae_fact_ge_schools (UNION)"""
    pub  = load_csv("GE_Public_Schools.csv")
    priv = load_csv("GE_Private_Schools.csv")

    def shape(df, sector_label):
        if df.empty: return pd.DataFrame()
        df.columns = [
            "academic_year", "inst_type_en", "inst_type_ar",
            "emirate_en", "emirate_ar",
            "sector_ar", "sector_en",
            "edu_cat_ar", "edu_cat_en",
            "school_count",
        ]
        df = df[["academic_year", "emirate_en", "edu_cat_en", "school_count"]].copy()
        df["sector"]           = sector_label
        df["emirate_en"]       = df["emirate_en"].apply(norm_region)
        df["school_count"]     = pd.to_numeric(df["school_count"], errors="coerce").fillna(0).astype(int)
        df.rename(columns={"edu_cat_en": "education_category"}, inplace=True)
        return df

    combined = pd.concat([
        shape(pub,  "Government"),
        shape(priv, "Non Government"),
    ], ignore_index=True)
    combined.dropna(subset=["academic_year", "emirate_en"], inplace=True)
    to_db(combined, "uae_fact_ge_schools", engine)


def refresh_mvs(engine):
    """Refresh all 8 Materialized Views after data load."""
    mvs = [
        "mv_uae_kpi_summary",
        "mv_uae_enrollment_by_emirate",
        "mv_uae_teachers_by_emirate",
        "mv_uae_student_teacher_ratio",
        "mv_uae_pass_rates",
        "mv_uae_schools_curriculum",
        "mv_uae_teachers_by_subject",
        "mv_uae_nationality_diversity",
    ]
    with engine.connect() as conn:
        for mv in mvs:
            try:
                conn.execute(text(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {mv}"))
                conn.commit()
                log.info("  🔄  Refreshed: %s", mv)
            except Exception as e:
                log.warning("  ⚠️   Could not refresh %s: %s", mv, e)
                conn.rollback()


def verify_load(engine):
    """Print row counts for all loaded tables."""
    tables = [
        "uae_fact_enrollment",
        "uae_fact_teachers_emirate",
        "uae_fact_teachers_subject",
        "uae_fact_schools",
        "uae_fact_pass_fail",
        "uae_fact_student_scores",
        "uae_fact_student_nationalities",
        "uae_fact_ge_teachers",
        "uae_fact_ge_staff",
        "uae_fact_ge_schools",
    ]
    print("\n" + "=" * 55)
    print("  VERIFICATION — Row Counts")
    print("=" * 55)
    with engine.connect() as conn:
        for tbl in tables:
            try:
                row = conn.execute(text(f"SELECT COUNT(*) FROM {tbl}")).fetchone()
                count = row[0] if row else 0
                status = "✅" if count > 0 else "❌ EMPTY"
                print(f"  {status}  {tbl:<45}  {count:>8,}")
            except Exception as e:
                print(f"  ❌  {tbl:<45}  ERROR: {e}")

    # Spot-check: total enrollment 2024-2025 should be 559,743
    try:
        with engine.connect() as conn:
            row = conn.execute(text(
                "SELECT SUM(student_count) FROM uae_fact_enrollment "
                "WHERE academic_year = '2024-2025'"
            )).fetchone()
            total = row[0] if row else 0
            match = "✅ MATCH" if total == 559743 else f"⚠️  EXPECTED 559,743 — got {total:,}"
            print(f"\n  SPOT-CHECK  Total students 2024-2025: {total:,}  {match}")
    except Exception as e:
        print(f"  Spot-check error: {e}")
    print("=" * 55)


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("\n" + "=" * 60)
    print("  UAE ETL PIPELINE — TutorCloud Global Schools Dashboard")
    print("=" * 60)

    # Validate DATA_DIR
    if not os.path.isdir(DATA_DIR):
        log.error("DATA_DIR not found: %s", DATA_DIR)
        log.error("Create the folder and place all UAE CSV files there.")
        sys.exit(1)

    # Build DB connection
    db_url = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}?options=-c%20search_path%3Duae%2Cpublic"
    try:
        engine = create_engine(db_url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        log.info("✅ DB connection OK — %s@%s/%s", DB_USER, DB_HOST, DB_NAME)
    except Exception as e:
        log.error("❌ DB connection failed: %s", e)
        log.error("Check DB_HOST/DB_NAME/DB_USER/DB_PASS in your .env file")
        sys.exit(1)

    t0 = time.time()

    # ── Phase 1: Core tables (highest priority) ───────────────────
    print("\n─── Phase 1: Core Fact Tables ───────────────────────────")
    etl_enrollment(engine)
    etl_teachers_emirate(engine)
    etl_schools(engine)
    etl_pass_fail(engine)

    # ── Phase 2: Supplementary tables ────────────────────────────
    print("\n─── Phase 2: Supplementary Tables ──────────────────────")
    etl_teachers_subject(engine)
    etl_student_scores(engine)
    etl_student_nationalities(engine)
    etl_ge_teachers(engine)
    etl_ge_staff(engine)
    etl_ge_schools(engine)

    # ── Phase 3: Refresh MVs ──────────────────────────────────────
    print("\n─── Phase 3: Refreshing Materialized Views ──────────────")
    refresh_mvs(engine)

    # ── Phase 4: Verify ───────────────────────────────────────────
    print("\n─── Phase 4: Verification ───────────────────────────────")
    verify_load(engine)

    elapsed = time.time() - t0
    print(f"\n✅  ETL complete in {elapsed:.1f}s\n")


if __name__ == "__main__":
    main()
