#!/usr/bin/env python3
"""
uae_filter_framework_fix_v1.py
------------------------------
Permanent UAE filter consistency fix.

Fixes:
1. Canonical filter key: education_type
2. Education Type options sourced from union across UAE fact tables
3. UAE Analytics uses same sidebar filters as State Dashboard
4. Internal helper filters (e.g. _curriculum_emirate) hidden from active filter summary
5. Backward-safe read path for old 'edu_type' references
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

MARKER = "UAE_FILTER_FRAMEWORK_FIX_v1"

OLD_TABLE_BLOCK = """        enr_cols = _tbl_cols("uae_fact_enrollment")
        sch_cols = _tbl_cols("uae_fact_schools")
        pf_cols  = _tbl_cols("uae_fact_pass_fail")
"""

NEW_TABLE_BLOCK = """        enr_cols = _tbl_cols("uae_fact_enrollment")
        sch_cols = _tbl_cols("uae_fact_schools")
        tch_cols = _tbl_cols("uae_fact_teachers_emirate")
        pf_cols  = _tbl_cols("uae_fact_pass_fail")
"""

OLD_PICK_BLOCK = """        emirate_col    = _pick_col(enr_cols, "region_en", "emirate", "emirate_en", "region")
        edu_type_col   = _pick_col(enr_cols, "education_type", "school_type", "edu_type", "type")
        gender_col     = _pick_col(enr_cols, "gender", "student_gender")
        nat_col        = _pick_col(enr_cols, "nationality_cat", "nationality_category", "nationality")
        cycle_col      = _pick_col(pf_cols,  "cycle", "education_cycle", "grade_level")
        curriculum_col = _pick_col(sch_cols, "curriculum_en", "curriculum", "curriculum_type")
"""

NEW_PICK_BLOCK = """        emirate_col    = _pick_col(enr_cols, "region_en", "emirate", "emirate_en", "region")
        edu_type_col   = _pick_col(enr_cols, "education_type", "school_type", "edu_type", "type")
        sch_edu_type_col = _pick_col(sch_cols, "education_type", "school_type", "edu_type", "type")
        tch_edu_type_col = _pick_col(tch_cols, "education_type", "school_type", "edu_type", "type")
        pf_edu_type_col  = _pick_col(pf_cols,  "education_type", "school_type", "edu_type", "type")
        gender_col     = _pick_col(enr_cols, "gender", "student_gender")
        nat_col        = _pick_col(enr_cols, "nationality_cat", "nationality_category", "nationality")
        cycle_col      = _pick_col(pf_cols,  "cycle", "education_cycle", "grade_level")
        curriculum_col = _pick_col(sch_cols, "curriculum_en", "curriculum", "curriculum_type")

        def _union_distinct_year(table_col_pairs):
            vals = []
            seen = set()
            for _tbl, _col in table_col_pairs:
                if not _col:
                    continue
                try:
                    for _v in _distinct(_tbl, _col):
                        _s = str(_v).strip() if _v is not None else ""
                        if _s and _s not in seen:
                            seen.add(_s)
                            vals.append(_s)
                except Exception:
                    pass
            return sorted(vals, key=lambda x: x.lower())
"""

OLD_EDU_OPTS_PAGE = """        if edu_type_col:
            opts = _distinct("uae_fact_enrollment", edu_type_col)
            filters["edu_type"] = {"col": edu_type_col, "val": _sel("📚 Education Type", opts, "uae_edu_type")}
"""

NEW_EDU_OPTS_PAGE = """        if edu_type_col:
            opts = _union_distinct_year([
                ("uae_fact_enrollment", edu_type_col),
                ("uae_fact_schools", sch_edu_type_col),
                ("uae_fact_teachers_emirate", tch_edu_type_col),
                ("uae_fact_pass_fail", pf_edu_type_col),
            ])
            filters["education_type"] = {"col": edu_type_col, "val": _sel("📚 Education Type", opts, "uae_edu_type")}
"""

OLD_EDU_OPTS_CURRENT = """        if edu_type_col:
            opts = _distinct("uae_fact_enrollment", edu_type_col)
            all_opts = ["All"] + [str(x) for x in opts if x]
            sel_edu = st.sidebar.selectbox(
                "📚 Education Type",
                all_opts,
                index=0,
                key=f"uae_edu_type_{sel_emirate}"
            )
            filters["edu_type"] = {"col": edu_type_col, "val": sel_edu}
"""

NEW_EDU_OPTS_CURRENT = """        if edu_type_col:
            opts = _union_distinct_year([
                ("uae_fact_enrollment", edu_type_col),
                ("uae_fact_schools", sch_edu_type_col),
                ("uae_fact_teachers_emirate", tch_edu_type_col),
                ("uae_fact_pass_fail", pf_edu_type_col),
            ])
            all_opts = ["All"] + [str(x) for x in opts if x]
            sel_edu = st.sidebar.selectbox(
                "📚 Education Type",
                all_opts,
                index=0,
                key=f"uae_edu_type_{sel_emirate}"
            )
            filters["education_type"] = {"col": edu_type_col, "val": sel_edu}
"""

OLD_EDTYPE_READ = """_edtyp_val = filters.get("education_type", {}).get("val") if "education_type" in filters else None"""

NEW_EDTYPE_READ = """_edtyp_val = (
            filters.get("education_type", {}).get("val")
            if "education_type" in filters
            else (filters.get("edu_type", {}).get("val") if "edu_type" in filters else None)
        )"""

OLD_ACTIVE = """        active = [v["val"] for v in filters.values() if v["val"] != "All"]"""

NEW_ACTIVE = """        active = [
            v["val"]
            for k, v in filters.items()
            if not str(k).startswith("_") and v["val"] != "All"
        ]"""

OLD_ANALYTICS = """    # UAE Analytics: no extra sidebar filters — only global Region selector
    # (render_region_badge in ui_styles.py handles India/UAE switching)
    filters = {}
"""

NEW_ANALYTICS = """    # UAE_FILTER_FRAMEWORK_FIX_v1:
    # Use the same UAE sidebar filters here as State Dashboard so
    # analytics respects emirate / education type / curriculum selections.
    filters = _build_sidebar_filters()
"""

def patch_file(path: Path) -> bool:
    if not path.exists():
        print(f"❌ File not found: {path}")
        return False

    src = path.read_text(encoding="utf-8")

    if MARKER in src:
        print(f"⚠️ Already patched: {path}")
        return True

    changed = False

    replacements = [
        ("table block", OLD_TABLE_BLOCK, NEW_TABLE_BLOCK),
        ("pick block + union helper", OLD_PICK_BLOCK, NEW_PICK_BLOCK),
        ("edtype read fallback", OLD_EDTYPE_READ, NEW_EDTYPE_READ),
        ("active filter cleanup", OLD_ACTIVE, NEW_ACTIVE),
        ("analytics filter hookup", OLD_ANALYTICS, NEW_ANALYTICS),
    ]

    for label, old, new in replacements:
        if old in src:
            src = src.replace(old, new, 1)
            print(f"✅ {path.name}: {label}")
            changed = True
        else:
            print(f"⚠️ {path.name}: {label} not matched")

    if path.name == "uae_page_renderer.py":
        if OLD_EDU_OPTS_PAGE in src:
            src = src.replace(OLD_EDU_OPTS_PAGE, NEW_EDU_OPTS_PAGE, 1)
            print(f"✅ {path.name}: canonical education_type + union options")
            changed = True
        else:
            print(f"⚠️ {path.name}: education type block not matched")

    if path.name == "uae_current.py":
        if OLD_EDU_OPTS_CURRENT in src:
            src = src.replace(OLD_EDU_OPTS_CURRENT, NEW_EDU_OPTS_CURRENT, 1)
            print(f"✅ {path.name}: canonical education_type + union options")
            changed = True
        else:
            print(f"⚠️ {path.name}: education type block not matched")

    if not changed:
        print(f"❌ No changes applied to {path}")
        return False

    src += f"\n# {MARKER}\n"

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = path.with_name(f"{path.name}.bak_filterfix_{ts}")
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
    print("\n" + "━" * 68)
    print("  UAE Filter Framework Fix v1  (sidebar + grouping + analytics)")
    print("━" * 68 + "\n")

    ok = True
    for f in FILES:
        print(f"--- Patching {f} ---")
        res = patch_file(f)
        ok = ok and res
        print()

    if not ok:
        print("❌ One or more files failed to patch.")
        sys.exit(1)

    print("✅ All UAE filter framework patches applied successfully.\n")
    print("Next steps:")
    print("1. Restart Streamlit")
    print("2. Verify Education Type dropdown now includes union of UAE values")
    print("3. Verify Analytics follows same UAE filters")
    print("4. Commit and push\n")

if __name__ == "__main__":
    main()
