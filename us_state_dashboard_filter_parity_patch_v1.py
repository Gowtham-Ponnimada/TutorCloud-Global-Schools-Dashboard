from pathlib import Path

TARGET = Path("utils/us_page_renderer.py")

old_districts = '''def _districts(state_name: str = "All") -> list[str]:
    if state_name and state_name != "All":
        return _distinct_values(
            f"SELECT DISTINCT district_name FROM {SCHEMA}.dim_districts WHERE school_year = %s AND state_name = %s AND district_name IS NOT NULL ORDER BY district_name",
            [DASHBOARD_YEAR, state_name],
            "district_name",
        )
    return _distinct_values(
        f"SELECT DISTINCT district_name FROM {SCHEMA}.dim_districts WHERE school_year = %s AND district_name IS NOT NULL ORDER BY district_name",
        [DASHBOARD_YEAR],
        "district_name",
    )


def _school_levels(state_name: str = "All") -> list[str]:
    if state_name and state_name != "All":
        return _distinct_values(
            f"SELECT DISTINCT school_level FROM {SCHEMA}.dim_schools WHERE school_year = %s AND state_name = %s AND school_level IS NOT NULL ORDER BY school_level",
            [DASHBOARD_YEAR, state_name],
            "school_level",
        )
    return _distinct_values(
        f"SELECT DISTINCT school_level FROM {SCHEMA}.dim_schools WHERE school_year = %s AND school_level IS NOT NULL ORDER BY school_level",
        [DASHBOARD_YEAR],
        "school_level",
    )
'''

new_districts = '''def _districts(state_name: str = "All") -> list[str]:
    if state_name and state_name != "All":
        return _distinct_values(
            f"SELECT DISTINCT district_name FROM {SCHEMA}.dim_districts WHERE school_year = %s AND state_name = %s AND district_name IS NOT NULL ORDER BY district_name",
            [DASHBOARD_YEAR, state_name],
            "district_name",
        )
    return _distinct_values(
        f"SELECT DISTINCT district_name FROM {SCHEMA}.dim_districts WHERE school_year = %s AND district_name IS NOT NULL ORDER BY district_name",
        [DASHBOARD_YEAR],
        "district_name",
    )


def _cities(state_name: str = "All", district_name: str = "All") -> list[str]:
    clauses = ["school_year = %s", "city IS NOT NULL", "BTRIM(city) <> ''"]
    params: list = [DASHBOARD_YEAR]
    if state_name and state_name != "All":
        clauses.append("state_name = %s")
        params.append(state_name)
    if district_name and district_name != "All":
        clauses.append("district_name = %s")
        params.append(district_name)
    sql = f"SELECT DISTINCT city FROM {SCHEMA}.dim_schools WHERE {' AND '.join(clauses)} ORDER BY city"
    return _distinct_values(sql, params, "city")



def _school_levels(state_name: str = "All", district_name: str = "All") -> list[str]:
    clauses = ["school_year = %s", "school_level IS NOT NULL", "BTRIM(school_level) <> ''"]
    params: list = [DASHBOARD_YEAR]
    if state_name and state_name != "All":
        clauses.append("state_name = %s")
        params.append(state_name)
    if district_name and district_name != "All":
        clauses.append("district_name = %s")
        params.append(district_name)
    sql = f"SELECT DISTINCT school_level FROM {SCHEMA}.dim_schools WHERE {' AND '.join(clauses)} ORDER BY school_level"
    return _distinct_values(sql, params, "school_level")



def _school_types(state_name: str = "All", district_name: str = "All") -> list[str]:
    clauses = ["school_year = %s", "sch_type_text IS NOT NULL", "BTRIM(sch_type_text) <> ''"]
    params: list = [DASHBOARD_YEAR]
    if state_name and state_name != "All":
        clauses.append("state_name = %s")
        params.append(state_name)
    if district_name and district_name != "All":
        clauses.append("district_name = %s")
        params.append(district_name)
    sql = f"SELECT DISTINCT sch_type_text FROM {SCHEMA}.dim_schools WHERE {' AND '.join(clauses)} ORDER BY sch_type_text"
    return _distinct_values(sql, params, "sch_type_text")



def _district_types(state_name: str = "All") -> list[str]:
    clauses = ["school_year = %s", "lea_type_text IS NOT NULL", "BTRIM(lea_type_text) <> ''"]
    params: list = [DASHBOARD_YEAR]
    if state_name and state_name != "All":
        clauses.append("state_name = %s")
        params.append(state_name)
    sql = f"SELECT DISTINCT lea_type_text FROM {SCHEMA}.dim_districts WHERE {' AND '.join(clauses)} ORDER BY lea_type_text"
    return _distinct_values(sql, params, "lea_type_text")
'''

old_sidebar = '''def _build_sidebar_filters() -> dict:
    with st.sidebar:
        state_opts = ["All"] + _states()
        state = st.selectbox("State", state_opts, index=0, key="us_state")
        district_opts = _districts(state)
        districts = st.multiselect("District", district_opts, key="us_districts")
        level_opts = _school_levels(state)
        school_levels = st.multiselect("School Level", level_opts, key="us_levels")
        charter = st.selectbox("Charter", ["All", "Yes", "No"], index=0, key="us_charter")
        virtual = st.selectbox("Virtual", ["All"] + _distinct_values(
            f"SELECT DISTINCT virtual_text FROM {SCHEMA}.dim_schools WHERE school_year = %s AND virtual_text IS NOT NULL ORDER BY virtual_text",
            [DASHBOARD_YEAR],
            "virtual_text",
        ), index=0, key="us_virtual")
        return {
            "state": state,
            "districts": districts,
            "school_levels": school_levels,
            "charter": charter,
            "virtual": virtual,
        }
'''

new_sidebar = '''def _build_sidebar_filters() -> dict:
    with st.sidebar:
        st.markdown("### US Filters")
        state_opts = ["All"] + _states()
        state = st.selectbox("Select State", state_opts, index=0, key="us_state")

        district_opts = ["All"] + _districts(state)
        district = st.selectbox("Select District", district_opts, index=0, key="us_district")

        city_opts = _cities(state, district)
        cities = st.multiselect("Select City", city_opts, key="us_cities")

        school_type_opts = _school_types(state, district)
        school_types = st.multiselect("School Type", school_type_opts, key="us_school_types")

        district_type_opts = _district_types(state)
        district_types = st.multiselect("District Type", district_type_opts, key="us_district_types")

        level_opts = _school_levels(state, district)
        school_levels = st.multiselect("School Category", level_opts, key="us_levels")

        charter = st.selectbox("Charter", ["All", "Yes", "No"], index=0, key="us_charter")
        virtual = st.selectbox(
            "Virtual",
            ["All"] + _distinct_values(
                f"SELECT DISTINCT virtual_text FROM {SCHEMA}.dim_schools WHERE school_year = %s AND virtual_text IS NOT NULL ORDER BY virtual_text",
                [DASHBOARD_YEAR],
                "virtual_text",
            ),
            index=0,
            key="us_virtual",
        )

        return {
            "state": state,
            "district": district,
            "districts": [district] if district != "All" else [],
            "cities": cities,
            "school_levels": school_levels,
            "school_types": school_types,
            "district_types": district_types,
            "charter": charter,
            "virtual": virtual,
        }
'''

old_base_where = '''def _base_where(filters: dict | None = None, alias: str = "ds"):
    filters = filters or {}
    clauses = [f"{alias}.school_year = %s"]
    params: list = [DASHBOARD_YEAR]
    if filters.get("state") and filters["state"] != "All":
        clauses.append(f"{alias}.state_name = %s")
        params.append(filters["state"])
    districts = [x for x in (filters.get("districts") or []) if x]
    if districts:
        clauses.append(f"{alias}.district_name = ANY(%s)")
        params.append(districts)
    levels = [x for x in (filters.get("school_levels") or []) if x]
    if levels:
        clauses.append(f"{alias}.school_level = ANY(%s)")
        params.append(levels)
    charter = filters.get("charter")
    if charter and charter != "All":
        clauses.append(f"COALESCE({alias}.charter_text, 'No') = %s")
        params.append(charter)
    virtual = filters.get("virtual")
    if virtual and virtual != "All":
        clauses.append(f"COALESCE({alias}.virtual_text, 'Not reported') = %s")
        params.append(virtual)
    return " WHERE " + " AND ".join(clauses), params
'''

new_base_where = '''def _base_where(filters: dict | None = None, alias: str = "ds"):
    filters = filters or {}
    clauses = [f"{alias}.school_year = %s"]
    params: list = [DASHBOARD_YEAR]
    if filters.get("state") and filters["state"] != "All":
        clauses.append(f"{alias}.state_name = %s")
        params.append(filters["state"])
    districts = [x for x in (filters.get("districts") or []) if x]
    if districts:
        clauses.append(f"{alias}.district_name = ANY(%s)")
        params.append(districts)
    cities = [x for x in (filters.get("cities") or []) if x]
    if cities:
        clauses.append(f"{alias}.city = ANY(%s)")
        params.append(cities)
    levels = [x for x in (filters.get("school_levels") or []) if x]
    if levels:
        clauses.append(f"{alias}.school_level = ANY(%s)")
        params.append(levels)
    school_types = [x for x in (filters.get("school_types") or []) if x]
    if school_types:
        clauses.append(f"COALESCE({alias}.sch_type_text, 'Unknown') = ANY(%s)")
        params.append(school_types)
    district_types = [x for x in (filters.get("district_types") or []) if x]
    if district_types:
        clauses.append(
            f"EXISTS (SELECT 1 FROM {SCHEMA}.dim_districts dd WHERE dd.school_year = {alias}.school_year AND dd.district_id = {alias}.district_id AND COALESCE(dd.lea_type_text, 'Unknown') = ANY(%s))"
        )
        params.append(district_types)
    charter = filters.get("charter")
    if charter and charter != "All":
        clauses.append(f"COALESCE({alias}.charter_text, 'No') = %s")
        params.append(charter)
    virtual = filters.get("virtual")
    if virtual and virtual != "All":
        clauses.append(f"COALESCE({alias}.virtual_text, 'Not reported') = %s")
        params.append(virtual)
    return " WHERE " + " AND ".join(clauses), params
'''

old_title = '''    filters = _build_sidebar_filters()
    title_state = filters.get("state") if filters.get("state") and filters.get("state") != "All" else "All States"
    st.markdown(f"<div class='us-title'>📊 US State Dashboard — {title_state}</div>", unsafe_allow_html=True)
    st.markdown("<div class='us-subtitle'>State and district analysis using NCES CCD Final v1a · 2024–2025 only.</div>", unsafe_allow_html=True)
'''

new_title = '''    filters = _build_sidebar_filters()
    title_state = filters.get("state") if filters.get("state") and filters.get("state") != "All" else "All States"
    if filters.get("district") and filters.get("district") != "All":
        title_state = f"{title_state} / {filters.get('district')}"
    st.markdown(f"<div class='us-title'>📊 US State Dashboard — {title_state}</div>", unsafe_allow_html=True)
    st.markdown("<div class='us-subtitle'>State and district analysis using NCES CCD Final v1a with US-equivalent filter depth.</div>", unsafe_allow_html=True)
'''


def main():
    if not TARGET.exists():
        raise SystemExit(f"Target file not found: {TARGET}")
    original = TARGET.read_text(encoding="utf-8")
    text = original

    replacements = [
        (old_districts, new_districts, "district helper block"),
        (old_sidebar, new_sidebar, "sidebar filter block"),
        (old_base_where, new_base_where, "base where block"),
        (old_title, new_title, "state dashboard title block"),
    ]

    for old, new, label in replacements:
        if old not in text:
            raise SystemExit(f"Could not find {label} to replace.")
        text = text.replace(old, new, 1)

    backup = TARGET.with_name(TARGET.name + ".bak_state_filter_parity_v1")
    backup.write_text(original, encoding="utf-8")
    TARGET.write_text(text, encoding="utf-8")
    print(f"Backup created: {backup}")
    print(f"Updated: {TARGET}")


if __name__ == "__main__":
    main()
