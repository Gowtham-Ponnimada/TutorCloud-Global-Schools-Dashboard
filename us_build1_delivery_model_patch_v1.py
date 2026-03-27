from pathlib import Path
import py_compile

ROOT = Path.cwd()
LOADER = ROOT / 'us_phase1_final_1a_load.py'
RENDERER = ROOT / 'utils' / 'us_page_renderer.py'

loader = LOADER.read_text(encoding='utf-8')
renderer = RENDERER.read_text(encoding='utf-8')

old_loader = """        c.virtual,
        c.virtual_text,
        now() AS created_at
"""
new_loader = """        c.virtual,
        c.virtual_text,
        CASE
            WHEN c.virtual_text IS NULL OR BTRIM(c.virtual_text) = '' THEN 'Unknown'
            WHEN LOWER(c.virtual_text) LIKE '%not virtual%' THEN 'Brick & Mortar'
            WHEN LOWER(c.virtual_text) LIKE '%fully virtual%' THEN 'Virtual'
            WHEN LOWER(c.virtual_text) LIKE '%exclusively virtual%' THEN 'Virtual'
            WHEN LOWER(c.virtual_text) LIKE '%face-to-face%' THEN 'Both'
            WHEN LOWER(c.virtual_text) LIKE '%hybrid%' THEN 'Both'
            WHEN LOWER(c.virtual_text) LIKE '%both%' THEN 'Both'
            WHEN LOWER(c.virtual_text) LIKE '%virtual%' THEN 'Virtual'
            ELSE 'Unknown'
        END AS delivery_model,
        now() AS created_at
"""
if old_loader not in loader:
    raise SystemExit('Could not find loader insertion point for delivery_model')
loader = loader.replace(old_loader, new_loader, 1)

anchor = """def _school_types(state_name: str = "All", district_name: str = "All") -> list[str]:
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



"""
insert = anchor + """def _delivery_models(state_name: str = "All", district_name: str = "All") -> list[str]:
    clauses = ["school_year = %s", "delivery_model IS NOT NULL", "BTRIM(delivery_model) <> ''"]
    params: list = [DASHBOARD_YEAR]
    if state_name and state_name != "All":
        clauses.append("state_name = %s")
        params.append(state_name)
    if district_name and district_name != "All":
        clauses.append("district_name = %s")
        params.append(district_name)
    sql = f"SELECT DISTINCT delivery_model FROM {SCHEMA}.dim_schools WHERE {' AND '.join(clauses)} ORDER BY delivery_model"
    return _distinct_values(sql, params, "delivery_model")



"""
if "def _delivery_models(" not in renderer:
    if anchor not in renderer:
        raise SystemExit('Could not find _school_types anchor for _delivery_models insertion')
    renderer = renderer.replace(anchor, insert, 1)

old_sidebar = """        city_opts = _cities(state, district)
        cities = st.multiselect("Select City", city_opts, key="us_cities")

        school_type_opts = _school_types(state, district)
        school_types = st.multiselect("School Type", school_type_opts, key="us_school_types")

        district_type_opts = _district_types(state)
        district_types = st.multiselect("District Type", district_type_opts, key="us_district_types")

        level_opts = _school_levels(state, district)
        school_levels = st.multiselect("School Category", level_opts, key="us_levels")

        return {
            "state": state,
            "district": district,
            "districts": [district] if district != "All" else [],
            "cities": cities,
            "school_levels": school_levels,
            "school_types": school_types,
            "district_types": district_types,
        }
"""
new_sidebar = """        city_opts = _cities(state, district)
        cities = st.multiselect("Select City", city_opts, key="us_cities")

        delivery_opts = ["All"] + _delivery_models(state, district)
        delivery_model = st.selectbox("School Type", delivery_opts, index=0, key="us_delivery_model")

        school_type_opts = _school_types(state, district)
        school_types = st.multiselect("Institution Type", school_type_opts, key="us_school_types")

        district_type_opts = _district_types(state)
        district_types = st.multiselect("District Type", district_type_opts, key="us_district_types")

        level_opts = _school_levels(state, district)
        school_levels = st.multiselect("School Category", level_opts, key="us_levels")

        return {
            "state": state,
            "district": district,
            "districts": [district] if district != "All" else [],
            "cities": cities,
            "delivery_model": delivery_model,
            "school_levels": school_levels,
            "school_types": school_types,
            "district_types": district_types,
        }
"""
if old_sidebar not in renderer:
    raise SystemExit('Could not find sidebar block to patch')
renderer = renderer.replace(old_sidebar, new_sidebar, 1)

old_where = """    cities = [x for x in (filters.get("cities") or []) if x]
    if cities:
        clauses.append(f"{alias}.city = ANY(%s)")
        params.append(cities)
    levels = [x for x in (filters.get("school_levels") or []) if x]
"""
new_where = """    cities = [x for x in (filters.get("cities") or []) if x]
    if cities:
        clauses.append(f"{alias}.city = ANY(%s)")
        params.append(cities)
    delivery_model = filters.get("delivery_model")
    if delivery_model and delivery_model != "All":
        clauses.append(f"COALESCE({alias}.delivery_model, 'Unknown') = %s")
        params.append(delivery_model)
    levels = [x for x in (filters.get("school_levels") or []) if x]
"""
if old_where not in renderer:
    raise SystemExit('Could not find _base_where block to patch')
renderer = renderer.replace(old_where, new_where, 1)

old_perf = '        perf_filters = {"state": perf_state, "districts": [], "school_levels": [], "charter": "All", "virtual": "All"}\n'
new_perf = '        perf_delivery_model = st.selectbox("School Type", ["All"] + _delivery_models(perf_state), index=0, key="us_perf_delivery_model")\n        perf_filters = {"state": perf_state, "districts": [], "school_levels": [], "delivery_model": perf_delivery_model}\n'
if old_perf not in renderer:
    raise SystemExit('Could not find analytics performance filter block to patch')
renderer = renderer.replace(old_perf, new_perf, 1)

old_dims = '            ["State", "District", "Location (City)", "School Type", "District Type", "School Category"],\n'
new_dims = '            ["State", "District", "Location (City)", "School Type", "Institution Type", "District Type", "School Category"],\n'
if old_dims not in renderer:
    raise SystemExit('Could not find custom report dimensions list to patch')
renderer = renderer.replace(old_dims, new_dims, 1)

old_dim_map = '        "Location (City)": ("ds.city", "city"),\n        "School Type": ("ds.sch_type_text", "school_type"),\n        "District Type": ("dd.lea_type_text", "district_type"),\n'
new_dim_map = '        "Location (City)": ("ds.city", "city"),\n        "School Type": ("ds.delivery_model", "school_type"),\n        "Institution Type": ("ds.sch_type_text", "institution_type"),\n        "District Type": ("dd.lea_type_text", "district_type"),\n'
if old_dim_map not in renderer:
    raise SystemExit('Could not find custom report dim_map block to patch')
renderer = renderer.replace(old_dim_map, new_dim_map, 1)

old_report_filters = """        report_state = st.selectbox("Filter by State", ["All"] + _states(), index=0, key="us_report_state")
        report_districts = st.multiselect("Filter by District", _districts(report_state), key="us_report_districts")
        report_levels = st.multiselect("Filter by School Category", _school_levels(report_state), key="us_report_levels")
        report_filters = {
            "state": report_state,
            "districts": report_districts,
            "school_levels": report_levels,
        }
"""
new_report_filters = """        report_state = st.selectbox("Filter by State", ["All"] + _states(), index=0, key="us_report_state")
        report_delivery_model = st.selectbox("Filter by School Type", ["All"] + _delivery_models(report_state), index=0, key="us_report_delivery_model")
        report_districts = st.multiselect("Filter by District", _districts(report_state), key="us_report_districts")
        report_levels = st.multiselect("Filter by School Category", _school_levels(report_state), key="us_report_levels")
        report_filters = {
            "state": report_state,
            "delivery_model": report_delivery_model,
            "districts": report_districts,
            "school_levels": report_levels,
        }
"""
if old_report_filters not in renderer:
    raise SystemExit('Could not find custom report filter block to patch')
renderer = renderer.replace(old_report_filters, new_report_filters, 1)

LOADER.write_text(loader, encoding='utf-8')
RENDERER.write_text(renderer, encoding='utf-8')

py_compile.compile(str(LOADER), doraise=True)
py_compile.compile(str(RENDERER), doraise=True)

print('Patched loader and renderer successfully.')
