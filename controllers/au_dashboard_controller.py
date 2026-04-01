from __future__ import annotations

from flask import Blueprint, abort, jsonify, render_template, request

# Adjust this import if your repo has a shared DB helper elsewhere.
from au_phase1_final_load import db_engine
from services.au_dashboard_service import AUDashboardService

au_dashboard_bp = Blueprint("au_dashboard", __name__, url_prefix="/au")
au_service = AUDashboardService(db_engine(), school_year="2025")


def _int_arg(name: str, default: int) -> int:
    try:
        return int(request.args.get(name, default))
    except (TypeError, ValueError):
        return default


@au_dashboard_bp.get("/api/summary")
def au_api_summary():
    return jsonify(au_service.get_national_summary())


@au_dashboard_bp.get("/api/states")
def au_api_states():
    return jsonify(au_service.get_state_kpis())


@au_dashboard_bp.get("/api/districts")
def au_api_districts():
    state_name = request.args.get("state_name")
    return jsonify(au_service.get_district_kpis(state_name=state_name))


@au_dashboard_bp.get("/api/filters")
def au_api_filters():
    state_name = request.args.get("state_name")
    return jsonify(au_service.get_filter_options(state_name=state_name))


@au_dashboard_bp.get("/api/schools")
def au_api_schools():
    state_name = request.args.get("state_name")
    district_name = request.args.get("district_name")
    management_type = request.args.get("management_type")
    school_level = request.args.get("school_level")
    delivery_model = request.args.get("delivery_model")
    search = request.args.get("search")

    limit = _int_arg("limit", 100)
    offset = _int_arg("offset", 0)

    rows = au_service.get_schools(
        state_name=state_name,
        district_name=district_name,
        management_type=management_type,
        school_level=school_level,
        delivery_model=delivery_model,
        search=search,
        limit=limit,
        offset=offset,
    )
    total = au_service.count_schools(
        state_name=state_name,
        district_name=district_name,
        management_type=management_type,
        school_level=school_level,
        delivery_model=delivery_model,
        search=search,
    )

    return jsonify(
        {
            "rows": rows,
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    )


@au_dashboard_bp.get("/api/schools/<school_id>")
def au_api_school_detail(school_id: str):
    school = au_service.get_school_detail(school_id)
    if not school:
        abort(404, description=f"School not found for school_id={school_id}")

    grades = au_service.get_grade_enrollment(school_id)
    return jsonify(
        {
            "school": school,
            "grade_enrollment": grades,
            "total_students_display": "N/A" if school.get("total_students") is None else school.get("total_students"),
        }
    )


@au_dashboard_bp.get("/")
def au_home():
    state_name = request.args.get("state_name")
    context = au_service.build_home_context(state_name=state_name)
    return render_template("au/home.html", **context)


@au_dashboard_bp.get("/state/<path:state_name>")
def au_state_dashboard(state_name: str):
    context = au_service.build_state_context(state_name=state_name)

    if not context.get("state"):
        abort(404, description=f"State not found: {state_name}")

    return render_template("au/state_dashboard.html", **context)


@au_dashboard_bp.get("/school/<school_id>")
def au_school_detail(school_id: str):
    context = au_service.build_school_context(school_id)

    if not context.get("school"):
        abort(404, description=f"School not found for school_id={school_id}")

    return render_template("au/school_detail.html", **context)
