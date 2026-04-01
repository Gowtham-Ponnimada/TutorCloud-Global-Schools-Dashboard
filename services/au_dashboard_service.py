from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine


def _coerce_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    return value


def _coerce_row(row: Dict[str, Any]) -> Dict[str, Any]:
    return {k: _coerce_value(v) for k, v in row.items()}


class AUDashboardService:
    def __init__(self, engine: Engine, school_year: str = "2025") -> None:
        self.engine = engine
        self.school_year = school_year

    def _rows(self, sql: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        with self.engine.connect() as conn:
            result = conn.execute(text(sql), params or {})
            return [_coerce_row(dict(row._mapping)) for row in result]

    def _one(self, sql: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        rows = self._rows(sql, params)
        return rows[0] if rows else {}

    def get_national_summary(self) -> Dict[str, Any]:
        sql = """
        SELECT
            COUNT(DISTINCT ds.school_id) AS schools,
            COALESCE(SUM(fst.total_students), 0) AS total_students,
            COALESCE(SUM(fst.girls_students), 0) AS girls_students,
            COALESCE(SUM(fst.boys_students), 0) AS boys_students,
            COALESCE(SUM(fst.fte_teaching_staff), 0) AS fte_teaching_staff,
            CASE
                WHEN COALESCE(SUM(fst.fte_teaching_staff), 0) > 0
                    THEN ROUND(SUM(fst.total_students)::numeric / SUM(fst.fte_teaching_staff), 4)
                ELSE NULL
            END AS student_teacher_ratio
        FROM au.dim_schools ds
        LEFT JOIN au.fact_school_totals fst
          ON ds.school_year = fst.school_year
         AND ds.school_id = fst.school_id
        WHERE ds.school_year = :school_year
        """
        return self._one(sql, {"school_year": self.school_year})

    def get_state_kpis(self) -> List[Dict[str, Any]]:
        sql = """
        SELECT
            school_year,
            state_abbr,
            state_name,
            schools,
            total_students,
            girls_students,
            boys_students,
            fte_teaching_staff,
            student_teacher_ratio,
            weighted_avg_icsea,
            weighted_indigenous_pct,
            weighted_lbote_yes_pct
        FROM au.vw_state_kpis_2025
        WHERE school_year = :school_year
        ORDER BY total_students DESC NULLS LAST, state_name
        """
        return self._rows(sql, {"school_year": self.school_year})

    def get_district_kpis(self, state_name: Optional[str] = None) -> List[Dict[str, Any]]:
        sql = """
        SELECT *
        FROM au.vw_district_kpis_2025
        WHERE school_year = :school_year
          AND (:state_name IS NULL OR state_name = :state_name)
        ORDER BY total_students DESC NULLS LAST, district_name
        """
        return self._rows(sql, {"school_year": self.school_year, "state_name": state_name})

    def get_filter_options(self, state_name: Optional[str] = None) -> Dict[str, List[Any]]:
        sql = """
        SELECT
            ARRAY(
                SELECT DISTINCT state_name
                FROM au.dim_schools
                WHERE school_year = :school_year
                ORDER BY state_name
            ) AS states,
            ARRAY(
                SELECT DISTINCT district_name
                FROM au.dim_schools
                WHERE school_year = :school_year
                  AND (:state_name IS NULL OR state_name = :state_name)
                  AND district_name IS NOT NULL
                ORDER BY district_name
            ) AS districts,
            ARRAY(
                SELECT DISTINCT management_type
                FROM au.dim_schools
                WHERE school_year = :school_year
                  AND management_type IS NOT NULL
                ORDER BY management_type
            ) AS management_types,
            ARRAY(
                SELECT DISTINCT school_level
                FROM au.dim_schools
                WHERE school_year = :school_year
                  AND school_level IS NOT NULL
                ORDER BY school_level
            ) AS school_levels,
            ARRAY[]::text[] AS delivery_models
        """
        return self._one(sql, {"school_year": self.school_year, "state_name": state_name})

    def get_schools(
        self,
        state_name: Optional[str] = None,
        district_name: Optional[str] = None,
        management_type: Optional[str] = None,
        school_level: Optional[str] = None,
        delivery_model: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        sql = """
        SELECT
            ds.school_id,
            ds.school_name,
            ds.state_abbr,
            ds.state_name,
            ds.district_name,
            ds.suburb,
            ds.postcode,
            ds.management_type,
            ds.school_level,
            NULL::text AS delivery_model,
            fst.total_students,
            fst.girls_students,
            fst.boys_students
        FROM au.dim_schools ds
        LEFT JOIN au.fact_school_totals fst
          ON ds.school_year = fst.school_year
         AND ds.school_id = fst.school_id
        WHERE ds.school_year = :school_year
          AND (:state_name IS NULL OR ds.state_name = :state_name)
          AND (:district_name IS NULL OR ds.district_name = :district_name)
          AND (:management_type IS NULL OR ds.management_type = :management_type)
          AND (:school_level IS NULL OR ds.school_level = :school_level)
          AND (
                :search IS NULL
                OR ds.school_name ILIKE '%' || :search || '%'
                OR ds.school_id ILIKE '%' || :search || '%'
                OR ds.suburb ILIKE '%' || :search || '%'
              )
        ORDER BY fst.total_students DESC NULLS LAST, ds.school_name
        LIMIT :limit OFFSET :offset
        """
        params = {
            "school_year": self.school_year,
            "state_name": state_name,
            "district_name": district_name,
            "management_type": management_type,
            "school_level": school_level,
            "delivery_model": delivery_model,
            "search": search,
            "limit": limit,
            "offset": offset,
        }
        return self._rows(sql, params)

    def count_schools(
        self,
        state_name: Optional[str] = None,
        district_name: Optional[str] = None,
        management_type: Optional[str] = None,
        school_level: Optional[str] = None,
        delivery_model: Optional[str] = None,
        search: Optional[str] = None,
    ) -> int:
        sql = """
        SELECT COUNT(*) AS row_count
        FROM au.dim_schools ds
        WHERE ds.school_year = :school_year
          AND (:state_name IS NULL OR ds.state_name = :state_name)
          AND (:district_name IS NULL OR ds.district_name = :district_name)
          AND (:management_type IS NULL OR ds.management_type = :management_type)
          AND (:school_level IS NULL OR ds.school_level = :school_level)
          AND (
                :search IS NULL
                OR ds.school_name ILIKE '%' || :search || '%'
                OR ds.school_id ILIKE '%' || :search || '%'
                OR ds.suburb ILIKE '%' || :search || '%'
              )
        """
        row = self._one(
            sql,
            {
                "school_year": self.school_year,
                "state_name": state_name,
                "district_name": district_name,
                "management_type": management_type,
                "school_level": school_level,
                "delivery_model": delivery_model,
                "search": search,
            },
        )
        return int(row.get("row_count", 0) or 0)

    def get_school_detail(self, school_id: str) -> Dict[str, Any]:
        sql = """
        SELECT
            ds.school_year,
            ds.school_id,
            ds.school_name,
            ds.state_abbr,
            ds.state_name,
            ds.district_name,
            ds.suburb,
            ds.postcode,
            ds.management_type,
            ds.school_level,
            NULL::text AS delivery_model,
            fst.total_students,
            fst.girls_students,
            fst.boys_students,
            fst.fte_teaching_staff,
            fst.icsea,
            fst.indigenous_pct,
            fst.lbote_yes_pct
        FROM au.dim_schools ds
        LEFT JOIN au.fact_school_totals fst
          ON ds.school_year = fst.school_year
         AND ds.school_id = fst.school_id
        WHERE ds.school_year = :school_year
          AND ds.school_id = :school_id
        """
        return self._one(sql, {"school_year": self.school_year, "school_id": school_id})

    def get_grade_enrollment(self, school_id: str) -> List[Dict[str, Any]]:
        sql = """
        SELECT
            grade_code,
            grade_label,
            grade_sort_order,
            enrolled_students
        FROM au.fact_grade_enrollment
        WHERE school_year = :school_year
          AND school_id = :school_id
        ORDER BY grade_sort_order, grade_code
        """
        return self._rows(sql, {"school_year": self.school_year, "school_id": school_id})

    def build_home_context(self, state_name: Optional[str] = None) -> Dict[str, Any]:
        return {
            "country": "Australia",
            "school_year": self.school_year,
            "summary": self.get_national_summary(),
            "states": self.get_state_kpis(),
            "districts": self.get_district_kpis(state_name=state_name) if state_name else [],
            "filters": self.get_filter_options(state_name=state_name),
            "selected_state": state_name,
        }

    def build_state_context(self, state_name: str) -> Dict[str, Any]:
        states = self.get_state_kpis()
        state_row = next((row for row in states if row["state_name"] == state_name), {})
        return {
            "country": "Australia",
            "school_year": self.school_year,
            "state": state_row,
            "districts": self.get_district_kpis(state_name=state_name),
            "filters": self.get_filter_options(state_name=state_name),
            "selected_state": state_name,
        }

    def build_school_context(self, school_id: str) -> Dict[str, Any]:
        school = self.get_school_detail(school_id)
        grades = self.get_grade_enrollment(school_id)
        return {
            "country": "Australia",
            "school_year": self.school_year,
            "school": school,
            "grade_enrollment": grades,
            "total_students_display": "N/A" if school.get("total_students") is None else school.get("total_students"),
        }
