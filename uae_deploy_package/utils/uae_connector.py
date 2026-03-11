"""
utils/uae_connector.py
UAE Database Connector — TutorCloud Global Schools Dashboard

All UAE-specific SQL queries live here.
India connector is untouched. This is a standalone UAE module.

Import pattern (same as India connector):
    from utils.uae_connector import (
        get_uae_kpi_summary, get_uae_enrollment_by_emirate, ...
    )
"""

import os
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

# ── Shared engine (cached at app level, same DB as India) ─────────────────────
# UAE uses same PostgreSQL server, different table prefix (uae_*)
# India tables are NEVER touched by this module.

@st.cache_resource
def _get_engine():
    url = (
        f"postgresql://{os.getenv('DB_USER','tutorcloud_admin')}:"
        f"{os.getenv('DB_PASSWORD', os.getenv('DB_PASS',''))}@"
        f"{os.getenv('DB_HOST','localhost')}:"
        f"{os.getenv('DB_PORT','5432')}/"
        f"{os.getenv('DB_NAME','tutorcloud_db')}?options=-c%20search_path%3Duae%2Cpublic"
    )
    return create_engine(url, pool_pre_ping=True)


def _query(sql: str, params: dict = None) -> pd.DataFrame:
    """Execute a read-only SQL query and return DataFrame."""
    try:
        with _get_engine().connect() as conn:
            return pd.read_sql(text(sql), conn, params=params)
    except Exception as e:
        st.error(f"UAE DB query error: {e}")
        return pd.DataFrame()


# ── Available filters ─────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def get_uae_available_years() -> list:
    df = _query(
        "SELECT DISTINCT academic_year FROM uae_fact_enrollment "
        "ORDER BY academic_year DESC"
    )
    return df["academic_year"].tolist() if not df.empty else ["2024-2025"]


@st.cache_data(ttl=3600)
def get_uae_available_regions() -> list:
    df = _query(
        "SELECT DISTINCT region_en FROM uae_fact_enrollment "
        "ORDER BY region_en"
    )
    return ["All Emirates"] + df["region_en"].tolist() if not df.empty else ["All Emirates"]


@st.cache_data(ttl=3600)
def get_uae_available_edu_types() -> list:
    df = _query(
        "SELECT DISTINCT education_type FROM uae_fact_enrollment "
        "WHERE education_type IS NOT NULL ORDER BY education_type"
    )
    return ["All Types"] + df["education_type"].tolist() if not df.empty else ["All Types"]


# ── KPI Summary (top-row cards) ───────────────────────────────────────────────

@st.cache_data(ttl=3600)
def get_uae_kpi_summary() -> pd.DataFrame:
    return _query(
        "SELECT * FROM mv_uae_kpi_summary ORDER BY academic_year DESC"
    )


# ── Enrollment ────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def get_uae_enrollment_by_emirate() -> pd.DataFrame:
    return _query(
        "SELECT * FROM mv_uae_enrollment_by_emirate "
        "ORDER BY academic_year DESC, total_students DESC"
    )


@st.cache_data(ttl=3600)
def get_uae_enrollment_trend() -> pd.DataFrame:
    return _query("""
        SELECT academic_year,
               SUM(student_count)                                                 AS total_students,
               SUM(CASE WHEN gender='Female'          THEN student_count ELSE 0 END) AS female,
               SUM(CASE WHEN gender='Male'            THEN student_count ELSE 0 END) AS male,
               SUM(CASE WHEN nationality_cat='Emirati'THEN student_count ELSE 0 END) AS emirati,
               SUM(CASE WHEN nationality_cat='Resident'THEN student_count ELSE 0 END) AS resident,
               SUM(CASE WHEN education_type='Public'  THEN student_count ELSE 0 END) AS public_sector
        FROM uae_fact_enrollment
        GROUP BY academic_year
        ORDER BY academic_year
    """)


@st.cache_data(ttl=3600)
def get_uae_enrollment_by_edu_type(year: str) -> pd.DataFrame:
    return _query("""
        SELECT education_type,
               SUM(student_count) AS total_students
        FROM uae_fact_enrollment
        WHERE academic_year = :yr
        GROUP BY education_type
        ORDER BY total_students DESC
    """, {"yr": year})


# ── Schools ───────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def get_uae_schools_by_emirate(year: str) -> pd.DataFrame:
    return _query("""
        SELECT region_en,
               SUM(school_count)                                                       AS total_schools,
               SUM(CASE WHEN student_gender='Girls'  THEN school_count ELSE 0 END)    AS girls_schools,
               SUM(CASE WHEN student_gender='Boys'   THEN school_count ELSE 0 END)    AS boys_schools,
               SUM(CASE WHEN student_gender='Co Edu' THEN school_count ELSE 0 END)    AS coedu_schools
        FROM uae_fact_schools
        WHERE academic_year = :yr
        GROUP BY region_en
        ORDER BY total_schools DESC
    """, {"yr": year})


@st.cache_data(ttl=3600)
def get_uae_schools_by_curriculum(year: str) -> pd.DataFrame:
    return _query("""
        SELECT curriculum_en,
               SUM(school_count) AS total_schools
        FROM uae_fact_schools
        WHERE academic_year = :yr
          AND curriculum_en IS NOT NULL
        GROUP BY curriculum_en
        ORDER BY total_schools DESC
    """, {"yr": year})


@st.cache_data(ttl=3600)
def get_uae_schools_curriculum_detail() -> pd.DataFrame:
    return _query(
        "SELECT * FROM mv_uae_schools_curriculum ORDER BY academic_year DESC, total_schools DESC"
    )


# ── Teachers ──────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def get_uae_teachers_by_emirate() -> pd.DataFrame:
    return _query(
        "SELECT * FROM mv_uae_teachers_by_emirate ORDER BY academic_year DESC, total_teachers DESC"
    )


@st.cache_data(ttl=3600)
def get_uae_student_teacher_ratio() -> pd.DataFrame:
    return _query(
        "SELECT * FROM mv_uae_student_teacher_ratio ORDER BY academic_year DESC, ratio DESC"
    )


@st.cache_data(ttl=3600)
def get_uae_teachers_by_subject(year: str, region: str = None) -> pd.DataFrame:
    if region and region != "All Emirates":
        return _query("""
            SELECT subject_en, SUM(total_teachers) AS total_teachers
            FROM mv_uae_teachers_by_subject
            WHERE academic_year = :yr AND region_en = :reg
              AND subject_en IS NOT NULL
            GROUP BY subject_en ORDER BY total_teachers DESC
        """, {"yr": year, "reg": region})
    return _query("""
        SELECT subject_en, SUM(total_teachers) AS total_teachers
        FROM mv_uae_teachers_by_subject
        WHERE academic_year = :yr AND subject_en IS NOT NULL
        GROUP BY subject_en ORDER BY total_teachers DESC
    """, {"yr": year})


@st.cache_data(ttl=3600)
def get_uae_teacher_trend() -> pd.DataFrame:
    return _query("""
        SELECT academic_year,
               SUM(teacher_count)  AS total_teachers,
               SUM(staff_count)    AS total_staff,
               SUM(CASE WHEN nationality_cat='Emirati'  THEN teacher_count ELSE 0 END) AS emirati_teachers,
               SUM(CASE WHEN nationality_cat='Resident' THEN teacher_count ELSE 0 END) AS resident_teachers
        FROM uae_fact_teachers_emirate
        GROUP BY academic_year ORDER BY academic_year
    """)


# ── Academic Performance ──────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def get_uae_pass_rates_by_emirate(year: str) -> pd.DataFrame:
    return _query("""
        SELECT region_en,
               ROUND(AVG(pass_percentage), 2) AS avg_pass_rate,
               SUM(student_count)              AS total_students
        FROM uae_fact_pass_fail
        WHERE academic_year = :yr
        GROUP BY region_en ORDER BY avg_pass_rate DESC
    """, {"yr": year})


@st.cache_data(ttl=3600)
def get_uae_pass_rates_trend() -> pd.DataFrame:
    return _query("""
        SELECT academic_year,
               nationality_cat,
               gender,
               ROUND(AVG(pass_percentage), 2) AS avg_pass_rate,
               SUM(student_count)              AS total_students
        FROM uae_fact_pass_fail
        GROUP BY academic_year, nationality_cat, gender
        ORDER BY academic_year
    """)


@st.cache_data(ttl=3600)
def get_uae_pass_rates_by_cycle(year: str) -> pd.DataFrame:
    return _query("""
        SELECT cycle,
               gender,
               nationality_cat,
               ROUND(AVG(pass_percentage), 2) AS avg_pass_rate,
               SUM(student_count)              AS total_students
        FROM uae_fact_pass_fail
        WHERE academic_year = :yr
        GROUP BY cycle, gender, nationality_cat
        ORDER BY cycle, gender
    """, {"yr": year})


@st.cache_data(ttl=3600)
def get_uae_scores_by_subject(year: str, region: str = None) -> pd.DataFrame:
    if region and region != "All Emirates":
        return _query("""
            SELECT subject_en,
                   ROUND(AVG(pass_percentage), 2) AS avg_pass_rate,
                   SUM(student_count)              AS total_students
            FROM uae_fact_student_scores
            WHERE academic_year = :yr AND region_en = :reg
              AND subject_en IS NOT NULL
            GROUP BY subject_en ORDER BY avg_pass_rate DESC
        """, {"yr": year, "reg": region})
    return _query("""
        SELECT subject_en,
               ROUND(AVG(pass_percentage), 2) AS avg_pass_rate,
               SUM(student_count)              AS total_students
        FROM uae_fact_student_scores
        WHERE academic_year = :yr AND subject_en IS NOT NULL
        GROUP BY subject_en ORDER BY avg_pass_rate DESC
    """, {"yr": year})


# ── Demographics ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def get_uae_nationality_diversity() -> pd.DataFrame:
    return _query(
        "SELECT * FROM mv_uae_nationality_diversity ORDER BY academic_year DESC, student_count DESC"
    )


@st.cache_data(ttl=3600)
def get_uae_nationality_trend(nationality: str = "United Arab Emirates") -> pd.DataFrame:
    return _query("""
        SELECT academic_year, student_count
        FROM uae_fact_student_nationalities
        WHERE nationality_en = :nat
        ORDER BY academic_year
    """, {"nat": nationality})


# ── Health check ─────────────────────────────────────────────────────────────

def uae_db_health_check() -> dict:
    """Returns dict with table row counts — used on first load to confirm ETL ran."""
    tables = [
        "uae_fact_enrollment", "uae_fact_teachers_emirate",
        "uae_fact_schools",    "uae_fact_pass_fail",
        "uae_fact_student_scores", "uae_fact_student_nationalities",
    ]
    result = {}
    try:
        with _get_engine().connect() as conn:
            for tbl in tables:
                row = conn.execute(text(f"SELECT COUNT(*) FROM {tbl}")).fetchone()
                result[tbl] = int(row[0]) if row else 0
        result["status"] = "ok"
    except Exception as e:
        result["status"] = f"error: {e}"
    return result
