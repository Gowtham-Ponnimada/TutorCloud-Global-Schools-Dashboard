# India-to-Australia Filter Binding Matrix

This matrix keeps India as the UI/UX contract while swapping the data binding to Australia fields.

## 1. Sidebar / top filter order
```text
1. School Year
2. State/Territory
3. District / LGA
4. Suburb / Locality
5. School Management
6. School Level
7. Remoteness
8. Governing Body
9. Postcode
10. School Name
```

## 2. India-to-Australia binding table

| India UI concept | Australia UI label | AU data field | SQL alias recommendation |
|---|---|---|---|
| Year | School Year | school_year | ds.school_year |
| State | State/Territory | state_name / state_abbr | ds.state_name |
| District | District / LGA | district_name | ds.district_name |
| Block / City | Suburb / Locality | suburb | ds.suburb |
| Management | School Management | management_type | ds.management_type |
| Category / School Type | School Level | school_level | ds.school_level |
| Area / Rural-Urban | Remoteness | abs_remoteness_area_name | ds.abs_remoteness_area_name |
| Authority / Board | Governing Body | governing_body | ds.governing_body |
| Pincode / Postal | Postcode | postcode | ds.postcode |
| School Search | School Name | school_name | ds.school_name |

## 3. Copy-paste filter dictionary
```python
AU_FILTER_BINDINGS = {
    'school_year': {
        'label': 'School Year',
        'field': 'ds.school_year',
        'default': '2025',
        'all_value': 'All'
    },
    'state_name': {
        'label': 'State/Territory',
        'field': 'ds.state_name',
        'default': 'All',
        'all_value': 'All'
    },
    'district_name': {
        'label': 'District / LGA',
        'field': 'ds.district_name',
        'default': 'All',
        'all_value': 'All'
    },
    'suburb': {
        'label': 'Suburb / Locality',
        'field': 'ds.suburb',
        'default': 'All',
        'all_value': 'All'
    },
    'management_type': {
        'label': 'School Management',
        'field': "COALESCE(ds.management_type, 'Unknown')",
        'default': 'All',
        'all_value': 'All'
    },
    'school_level': {
        'label': 'School Level',
        'field': "COALESCE(ds.school_level, 'Unknown')",
        'default': 'All',
        'all_value': 'All'
    },
    'remoteness': {
        'label': 'Remoteness',
        'field': "COALESCE(ds.abs_remoteness_area_name, 'Unknown')",
        'default': 'All',
        'all_value': 'All'
    },
    'governing_body': {
        'label': 'Governing Body',
        'field': "COALESCE(ds.governing_body, 'Unknown')",
        'default': 'All',
        'all_value': 'All'
    },
    'postcode': {
        'label': 'Postcode',
        'field': "COALESCE(ds.postcode, 'Unknown')",
        'default': 'All',
        'all_value': 'All'
    },
    'school_name': {
        'label': 'School Name',
        'field': 'ds.school_name',
        'default': '',
        'all_value': ''
    }
}
```

## 4. Copy-paste cascade rules
```python
AU_FILTER_CASCADE = {
    'state_name': ['district_name', 'suburb', 'governing_body', 'postcode', 'school_name'],
    'district_name': ['suburb', 'postcode', 'school_name'],
    'management_type': ['school_level', 'remoteness', 'governing_body', 'school_name'],
    'school_level': ['remoteness', 'governing_body', 'school_name']
}
```

## 5. Copy-paste WHERE-clause builder
```python
def _base_where_au(filters: dict | None = None, alias: str = 'ds'):
    filters = filters or {}
    clauses = [f"{alias}.school_year = %s"]
    params = [filters.get('school_year', '2025')]

    state_name = filters.get('state_name')
    if state_name and state_name != 'All':
        clauses.append(f"{alias}.state_name = %s")
        params.append(state_name)

    district_name = filters.get('district_name')
    if district_name and district_name != 'All':
        clauses.append(f"{alias}.district_name = %s")
        params.append(district_name)

    suburb = filters.get('suburb')
    if suburb and suburb != 'All':
        clauses.append(f"{alias}.suburb = %s")
        params.append(suburb)

    management_type = filters.get('management_type')
    if management_type and management_type != 'All':
        clauses.append(f"COALESCE({alias}.management_type, 'Unknown') = %s")
        params.append(management_type)

    school_level = filters.get('school_level')
    if school_level and school_level != 'All':
        clauses.append(f"COALESCE({alias}.school_level, 'Unknown') = %s")
        params.append(school_level)

    remoteness = filters.get('remoteness')
    if remoteness and remoteness != 'All':
        clauses.append(f"COALESCE({alias}.abs_remoteness_area_name, 'Unknown') = %s")
        params.append(remoteness)

    governing_body = filters.get('governing_body')
    if governing_body and governing_body != 'All':
        clauses.append(f"COALESCE({alias}.governing_body, 'Unknown') = %s")
        params.append(governing_body)

    postcode = filters.get('postcode')
    if postcode and postcode != 'All':
        clauses.append(f"COALESCE({alias}.postcode, 'Unknown') = %s")
        params.append(postcode)

    school_name = (filters.get('school_name') or '').strip()
    if school_name:
        clauses.append(f"{alias}.school_name ILIKE %s")
        params.append(f"%{school_name}%")

    return ' AND '.join(clauses), params
```

## 6. India-parity tab mapping

| India tab | Australia tab label | Primary AU grain |
|---|---|---|
| National Overview / Home | National Overview | state |
| State Dashboard | State Dashboard | LGA |
| District Dashboard | District Dashboard | suburb / school |
| Analytics | Analytics | state/LGA/management/level |
| School Directory | School Directory | school |
| Custom Reports / Exports | Custom Reports / Exports | filtered result set |

## 7. KPI definitions
```python
AU_KPI_DEFINITIONS = {
    'total_schools': 'COUNT(DISTINCT ds.school_id)',
    'total_students': 'COALESCE(SUM(fs.total_students), 0)',
    'girls_students': 'COALESCE(SUM(fs.girls_students), 0)',
    'boys_students': 'COALESCE(SUM(fs.boys_students), 0)',
    'fte_teaching_staff': 'COALESCE(SUM(fs.fte_teaching_staff), 0)',
    'student_teacher_ratio': "CASE WHEN COALESCE(SUM(fs.fte_teaching_staff),0) > 0 THEN ROUND(SUM(fs.total_students)::numeric / SUM(fs.fte_teaching_staff), 4) END"
}
```
