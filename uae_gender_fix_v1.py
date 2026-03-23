#!/usr/bin/env python3
"""
uae_gender_fix_v1.py
--------------------
Permanent fix for UAE dashboard Gender filter semantics.

Root cause
~~~~~~~~~~
The sidebar Gender filter is sourced from student enrollment (Male/Female),
but the generic _where_clause() fuzzy-matches it into other tables such as:
- uae_fact_schools.school_gender  (Boys / Girls / Co Edu)
- uae_fact_teachers_emirate.gender or teacher_gender

That makes one student-gender filter incorrectly change school / teacher totals
across tabs and analytics.

Fix
~~~
1. Mark the Gender filter as student-domain only.
2. Extend _where_clause() with table_name-aware scoping.
3. Pass table_name at all UAE call sites so Gender applies only to student-domain tables:
   - uae_fact_enrollment
   - uae_fact_student_nationalities
   - uae_fact_student_scores
   - uae_fact_pass_fail
4. Keep backward compatibility for all other filters.
"""

from pathlib import Path
from datetime import datetime
import shutil
import ast
import sys

FILES = [
    Path("utils/uae_page_renderer.py"),
    Path("utils/uae_current.py"),
]

MARKER = "UAE_GENDER_SCOPE_FIX_v1"

OLD_WHERE = '''def _where_clause(filters: dict, table_alias: str = "", allowed_cols: list = None) -> tuple:
    """Build SQL WHERE additions from the filters dict.
    Supports op='in' for list-based IN clauses (curriculum cross-filter).
    For cross-table filtering, tries exact column match then root-word match."""
    parts, params = [], []
    prefix = f"{table_alias}." if table_alias else ""
    for _, finfo in filters.items():
        col = finfo["col"]
        val = finfo["val"]
        # ── IN-list operator (curriculum cross-filter) ───────────────────
        if finfo.get("op") == "in":
            if allowed_cols is not None and col not in allowed_cols:
                continue
            if isinstance(val, list) and val:
                placeholders = ",".join(["%s"] * len(val))
                parts.append(f"{prefix}{col} IN ({placeholders})")
                params.extend(val)
            continue
        # ── Standard equality filter ─────────────────────────────────────
        if val == "All":
            continue
        if allowed_cols is not None:
            if col not in allowed_cols:
                # Fuzzy root-word match (region_en ↔ region_en across tables)
                root_words = set(col.replace("_en", "").replace("_cat", "").split("_"))
                alt_col = next(
                    (c for c in (allowed_cols or [])
                     if any(w in c for w in root_words) and len(w) > 2),
                    None
                )
                if alt_col:
                    col = alt_col
                else:
                    continue
        parts.append(f"{prefix}{col} = %s")
        params.append(val)
    clause = (" AND " + " AND ".join(parts)) if parts else ""
    return clause, params
'''

NEW_WHERE = '''def _where_clause(filters: dict, table_alias: str = "", allowed_cols: list = None, table_name: str = "") -> tuple:
    """Build SQL WHERE additions from the filters dict.
    Supports op='in' for list-based IN clauses (curriculum cross-filter).
    For cross-table filtering, tries exact column match then root-word match.

    UAE_GENDER_SCOPE_FIX_v1:
    Some filters are semantically scoped to only certain fact tables. For example,
    the sidebar Gender filter is a *student gender* filter sourced from enrollment,
    so it must not silently map onto school_gender / teacher_gender in other tables.
    """
    parts, params = [], []
    prefix = f"{table_alias}." if table_alias else ""
    for _, finfo in filters.items():
        col = finfo["col"]
        val = finfo["val"]

        # Optional table scoping for semantically-sensitive filters
        apply_to = finfo.get("apply_to")
        if table_name and apply_to and table_name not in apply_to:
            continue

        # ── IN-list operator (curriculum cross-filter) ───────────────────
        if finfo.get("op") == "in":
            if allowed_cols is not None and col not in allowed_cols:
                continue
            if isinstance(val, list) and val:
                placeholders = ",".join(["%s"] * len(val))
                parts.append(f"{prefix}{col} IN ({placeholders})")
                params.extend(val)
            continue

        # ── Standard equality filter ─────────────────────────────────────
        if val == "All":
            continue
        if allowed_cols is not None:
            if col not in allowed_cols:
                # Fuzzy root-word match (region_en ↔ region_en across tables)
                root_words = set(col.replace("_en", "").replace("_cat", "").split("_"))
                alt_col = next(
                    (c for c in (allowed_cols or [])
                     if any(w in c for w in root_words) and len(w) > 2),
                    None
                )
                if alt_col:
                    col = alt_col
                else:
                    continue
        parts.append(f"{prefix}{col} = %s")
        params.append(val)
    clause = (" AND " + " AND ".join(parts)) if parts else ""
    return clause, params
'''

OLD_GENDER_PAGE = '            filters["gender"] = {"col": gender_col, "val": _sel("👤 Gender", opts, "uae_gender")}'
NEW_GENDER_PAGE = '''            filters["gender"] = {
                "col": gender_col,
                "val": _sel("👤 Gender", opts, "uae_gender"),
                "apply_to": [
                    "uae_fact_enrollment",
                    "uae_fact_student_nationalities",
                    "uae_fact_student_scores",
                    "uae_fact_pass_fail",
                ],
            }'''

OLD_GENDER_CURRENT = '            filters["gender"] = {"col": gender_col, "val": sel_gender}'
NEW_GENDER_CURRENT = '''            filters["gender"] = {
                "col": gender_col,
                "val": sel_gender,
                "apply_to": [
                    "uae_fact_enrollment",
                    "uae_fact_student_nationalities",
                    "uae_fact_student_scores",
                    "uae_fact_pass_fail",
                ],
            }'''

REPLACEMENTS = [
    ('_where_clause(filters, allowed_cols=enr_cols)', '_where_clause(filters, allowed_cols=enr_cols, table_name="uae_fact_enrollment")'),
    ('_where_clause(filters, allowed_cols=sch_cols)', '_where_clause(filters, allowed_cols=sch_cols, table_name="uae_fact_schools")'),
    ('_where_clause(filters, allowed_cols=tch_cols)', '_where_clause(filters, allowed_cols=tch_cols, table_name="uae_fact_teachers_emirate")'),
    ('_where_clause(filters, allowed_cols=pf_cols)', '_where_clause(filters, allowed_cols=pf_cols, table_name="uae_fact_pass_fail")'),
    ('_where_clause(filters, allowed_cols=sc_cols)', '_where_clause(filters, allowed_cols=sc_cols, table_name="uae_fact_student_scores")'),
    ('_where_clause(filters, allowed_cols=nat_cols)', '_where_clause(filters, allowed_cols=nat_cols, table_name="uae_fact_student_nationalities")'),
    ('_where_clause(filters, allowed_cols=_tbl_cols("uae_fact_teachers_emirate"))', '_where_clause(filters, allowed_cols=_tbl_cols("uae_fact_teachers_emirate"), table_name="uae_fact_teachers_emirate")'),
    ('_where_clause(filters, allowed_cols=_tbl_cols("uae_fact_enrollment"))', '_where_clause(filters, allowed_cols=_tbl_cols("uae_fact_enrollment"), table_name="uae_fact_enrollment")'),
]


def patch_file(path: Path) -> bool:
    if not path.exists():
        print(f"❌ File not found: {path}")
        return False

    src = path.read_text(encoding="utf-8")

    if MARKER in src:
        print(f"⚠️ Already patched: {path}")
        return True

    changed = False

    if OLD_WHERE in src:
        src = src.replace(OLD_WHERE, NEW_WHERE, 1)
        print(f"✅ {path.name}: _where_clause scoped by table_name")
        changed = True
    else:
        print(f"⚠️ {path.name}: _where_clause block not matched")

    if path.name == "uae_page_renderer.py":
        if OLD_GENDER_PAGE in src:
            src = src.replace(OLD_GENDER_PAGE, NEW_GENDER_PAGE, 1)
            print(f"✅ {path.name}: gender filter marked as student-domain")
            changed = True
        else:
            print(f"⚠️ {path.name}: gender filter block not matched")

    if path.name == "uae_current.py":
        if OLD_GENDER_CURRENT in src:
            src = src.replace(OLD_GENDER_CURRENT, NEW_GENDER_CURRENT, 1)
            print(f"✅ {path.name}: gender filter marked as student-domain")
            changed = True
        else:
            print(f"⚠️ {path.name}: gender filter block not matched")

    for old, new in REPLACEMENTS:
        count = src.count(old)
        if count:
            src = src.replace(old, new)
            print(f"✅ {path.name}: replaced {count} call(s) of {old}")
            changed = True

    if not changed:
        print(f"❌ No changes applied to {path}")
        return False

    src += f"\\n# {MARKER}\\n"

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = path.with_name(f"{path.name}.bak_gender_scope_{ts}")
    shutil.copy2(path, backup)
    print(f"✅ Backup created: {backup.name}")

    path.write_text(src, encoding="utf-8")

    try:
        ast.parse(src)
        print(f"✅ Syntax OK: {path}")
    except SyntaxError as e:
        print(f"❌ Syntax error in {path}: {e}")
        return False

    return True


def main():
    print("\\n" + "━" * 72)
    print("  UAE Gender Scope Fix v1  (student gender should not filter schools/teachers)")
    print("━" * 72 + "\\n")

    ok = True
    for f in FILES:
        print(f"--- Patching {f} ---")
        res = patch_file(f)
        ok = ok and res
        print()

    if not ok:
        print("❌ One or more files failed to patch.")
        sys.exit(1)

    print("✅ All patches applied successfully.\\n")
    print("What changes now:")
    print("1. Student Gender filters enrollment / student-demographic / student-performance tables only")
    print("2. School totals are no longer wrongly forced through school_gender")
    print("3. Teacher totals are no longer wrongly forced through teacher_gender")
    print("4. Analytics uses the same safer behavior across tabs\\n")


if __name__ == "__main__":
    main()
