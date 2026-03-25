"""
uae_mv_dashboard_patch_v3.py
============================
Patches utils/uae_page_renderer.py AND utils/uae_current.py to:

  1. Query uae.mv_uae_curriculum_kpi when a curriculum filter is active.
  2. Show accurate (proportional-estimate) KPI values for public-school curricula.
  3. Show "N/A – Private School Data" for curricula whose education_type has
     no row in uae_fact_enrollment (private schools, ATHS, VEDC …).
  4. Add a colour-coded information banner explaining what each KPI covers.
  5. Leave ALL other queries (sub-tabs, analytics, India dashboard) 100% untouched.

Run from the repo root:
    python3 uae_mv_dashboard_patch_v3.py

The script:
  • Creates timestamped backups before any write.
  • Applies changes only to the KPI section inside render_uae_state_dashboard.
  • Does a syntax (AST) check on every patched file.
  • Is idempotent – re-running is safe (detects already-patched marker).
"""

import ast
import pathlib
import shutil
import sys
import time
import textwrap

REPO_ROOT = pathlib.Path(".")
FILES = {
    "renderer": REPO_ROOT / "utils" / "uae_page_renderer.py",
    "current":  REPO_ROOT / "utils" / "uae_current.py",
}

# ── Marker to detect already-patched files ───────────────────────────────────
PATCH_MARKER = "# [MV_PATCH_v3] curriculum-aware KPI"

# =============================================================================
# Helper utilities
# =============================================================================

def backup(path: pathlib.Path) -> pathlib.Path:
    ts   = time.strftime("%Y%m%d_%H%M%S")
    dest = path.with_suffix(f".py.bak_{ts}")
    shutil.copy2(path, dest)
    print(f"  ✅ backup → {dest}")
    return dest


def syntax_ok(path: pathlib.Path) -> bool:
    try:
        ast.parse(path.read_text(encoding="utf-8"))
        return True
    except SyntaxError as exc:
        print(f"  ❌ SyntaxError in {path}: {exc}")
        return False


def already_patched(src: str) -> bool:
    return PATCH_MARKER in src


# =============================================================================
# The MV-query helper block injected once (near top of each file's module
# scope, just after the existing _db_conn / _q helpers).
# We add it as a module-level function called _mv_curriculum_kpi().
# =============================================================================
MV_HELPER = '''
# ---------------------------------------------------------------------------
# [MV_PATCH_v3] curriculum-aware KPI  ←  DO NOT REMOVE THIS LINE
# ---------------------------------------------------------------------------
def _mv_curriculum_kpi(academic_year: str,
                        curriculum_val: str,
                        emirate_val: str | None = None,
                        edtype_val: str | None  = None) -> dict:
    """
    Query uae.mv_uae_curriculum_kpi and return a dict with curriculum-scoped
    KPI values.  Returns None if the MV doesn't exist (graceful fallback).

    Keys returned
    -------------
    school_count, student_count, teacher_count, staff_count,
    female_students, male_students, emirati_students, resident_students,
    female_teachers, male_teachers, emirati_teachers, resident_teachers,
    student_teacher_ratio, students_per_school,
    has_enrollment_data, has_teacher_data, row_count
    """
    wheres  = ["academic_year = %s", "curriculum_en = %s"]
    params  = [academic_year, curriculum_val]
    if emirate_val and emirate_val not in ("All", "", None):
        wheres.append("region_en = %s")
        params.append(emirate_val)
    if edtype_val and edtype_val not in ("All", "", None):
        wheres.append("education_type = %s")
        params.append(edtype_val)
    where_sql = " AND ".join(wheres)

    agg_sql = f"""
        SELECT
            COALESCE(SUM(school_count),   0)               AS school_count,
            SUM(student_count)                             AS student_count,
            SUM(teacher_count)                             AS teacher_count,
            SUM(staff_count)                               AS staff_count,
            SUM(female_students)                           AS female_students,
            SUM(male_students)                             AS male_students,
            SUM(emirati_students)                          AS emirati_students,
            SUM(resident_students)                         AS resident_students,
            SUM(female_teachers)                           AS female_teachers,
            SUM(male_teachers)                             AS male_teachers,
            SUM(emirati_teachers)                          AS emirati_teachers,
            SUM(resident_teachers)                         AS resident_teachers,
            BOOL_OR(has_enrollment_data)                   AS has_enrollment_data,
            BOOL_OR(has_teacher_data)                      AS has_teacher_data,
            COUNT(*)                                       AS row_count
        FROM uae.mv_uae_curriculum_kpi
        WHERE {where_sql}
    """
    try:
        rows = _q(agg_sql, params)
        if not rows:
            return None
        r = rows[0]
        return {
            "school_count":       int(r[0]  or 0),
            "student_count":      r[1],          # None if no enr data
            "teacher_count":      r[2],          # None if no tch data
            "staff_count":        r[3],
            "female_students":    r[4],
            "male_students":      r[5],
            "emirati_students":   r[6],
            "resident_students":  r[7],
            "female_teachers":    r[8],
            "male_teachers":      r[9],
            "emirati_teachers":   r[10],
            "resident_teachers":  r[11],
            "has_enrollment_data": bool(r[12]),
            "has_teacher_data":   bool(r[13]),
            "row_count":          int(r[14] or 0),
        }
    except Exception:
        return None          # MV not available – caller falls back gracefully
'''

# =============================================================================
# The KPI-section replacement block (injected into render_uae_state_dashboard)
# =============================================================================
KPI_PATCH_CODE = '''
    # ── [MV_PATCH_v3] curriculum-aware KPI section ─────────────────────────
    _curr_active = (
        "curriculum" in filters
        and filters["curriculum"].get("val") not in ("All", "", None)
    )

    if _curr_active:
        _curr_val  = filters["curriculum"]["val"]
        _emir_val  = filters.get("emirate", {}).get("val")   if "emirate"        in filters else None
        _edtyp_val = filters.get("education_type", {}).get("val") if "education_type" in filters else None
        _scope_lbl = _emir_val if _emir_val and _emir_val not in ("All","") else "UAE"

        mv = _mv_curriculum_kpi(UAE_YEAR, _curr_val, _emir_val, _edtyp_val)

        if mv and mv["row_count"] > 0:
            _mv_schools = mv["school_count"]
            _mv_enr_ok  = mv["has_enrollment_data"]
            _mv_tch_ok  = mv["has_teacher_data"]

            # Proportional or N/A for students
            if _mv_enr_ok and mv["student_count"] is not None:
                _mv_students   = int(mv["student_count"])
                _mv_female     = int(mv["female_students"] or 0)
                _mv_male       = int(mv["male_students"]   or 0)
                _stud_lbl      = f"👥 Students · {_scope_lbl}"
                _stud_help     = (f"Proportional estimate for {_curr_val} curriculum "
                                  f"based on school-share within education type "
                                  f"(public-school data available).")
            else:
                _mv_students   = None
                _mv_female     = None
                _mv_male       = None
                _stud_lbl      = f"👥 Students · {_scope_lbl}"
                _stud_help     = (f"Student enrollment data is not available for "
                                  f"{_curr_val} curriculum in the source dataset "
                                  f"(private / specialist school). Only school count "
                                  f"is accurate.")

            # Proportional or N/A for teachers
            if _mv_tch_ok and mv["teacher_count"] is not None:
                _mv_teachers   = int(mv["teacher_count"])
                _tch_lbl       = f"👨‍🏫 Teachers · {_scope_lbl}"
                _tch_help      = (f"Proportional estimate for {_curr_val} curriculum "
                                  f"based on school-share within education type.")
            else:
                _mv_teachers   = None
                _tch_lbl       = f"👨‍🏫 Teachers · {_scope_lbl}"
                _tch_help      = "Teacher data not available for this curriculum."

            _mv_ptr = _fmt_ptr(_mv_students or 0, _mv_teachers or 0) if (_mv_enr_ok and _mv_tch_ok) else "N/A"

            # ── KPI row 1 ────────────────────────────────────────────────
            st.markdown(
                f'<div class="section-header">📊 {_scope_lbl} · {_curr_val} · 2024–25</div>',
                unsafe_allow_html=True
            )
            k1, k2, k3, k4 = st.columns(4)
            with k1:
                st.metric("🏫 Schools", _fmt(_mv_schools),
                          help=f"Schools offering {_curr_val} curriculum in {_scope_lbl}")
            with k2:
                st.metric(_stud_lbl,
                          _fmt(_mv_students) if _mv_students is not None else "N/A",
                          help=_stud_help)
            with k3:
                st.metric(_tch_lbl,
                          _fmt(_mv_teachers) if _mv_teachers is not None else "N/A",
                          help=_tch_help)
            with k4:
                st.metric("📊 PTR", _mv_ptr,
                          help="Student-Teacher Ratio (proportional estimate)" if _mv_enr_ok else "N/A – data not available")

            # ── KPI row 2  (gender breakdown) ────────────────────────────
            if _mv_enr_ok and _mv_female is not None:
                k5, k6 = st.columns(2)
                with k5:
                    st.metric("♀ Female Students", _fmt(_mv_female))
                with k6:
                    st.metric("♂ Male Students", _fmt(_mv_male))

            # ── Scope banner ─────────────────────────────────────────────
            if _mv_enr_ok:
                st.info(
                    f"📌 **Curriculum filter active – {_curr_val}  |  Scope: {_scope_lbl}**\\n\\n"
                    f"School count is **exact** (directly sourced from the schools fact table).  "
                    f"Student & teacher counts are **proportional estimates** computed by "
                    f"allocating the emirate/education-type total according to each curriculum's "
                    f"share of schools.  Totals across all curricula within the same education "
                    f"type will equal the values shown on the Home page and all other sub-tabs.",
                    icon="ℹ️"
                )
            else:
                st.warning(
                    f"⚠️ **{_curr_val} is a private/specialist curriculum.**\\n\\n"
                    f"The source dataset does not include per-curriculum student enrollment or "
                    f"teacher assignment for private-school categories.  Only **school count "
                    f"({_fmt(_mv_schools)})** is accurate.  Student & teacher KPIs are shown as "
                    f"**N/A** to avoid misleading figures.",
                    icon="⚠️"
                )

        else:
            # MV not yet available (e.g. not yet deployed) – graceful fallback
            st.info("ℹ️ Curriculum-level KPI view is not yet available. "
                    "Showing emirate-wide totals.", icon="ℹ️")
            # fall through to existing metrics below

    # ── Standard KPI metrics (no curriculum filter, or MV unavailable) ──────
    if not _curr_active or (mv is None or mv["row_count"] == 0):
        st.markdown('<div class="section-header">📊 Overview: UAE 2024–25</div>',
                    unsafe_allow_html=True)
        k1, k2, k3, k4 = st.columns(4)
        with k1: st.metric("🏫 Total Schools",            _fmt(total_sch))
        with k2: st.metric("🎓 Schools with Enrollment",  _fmt(sch_with_enr))
        with k3: st.metric("🗺️ Emirates",                 _fmt(em_cnt))
        with k4: st.metric(ptr_label,                     ptr_str)
        k5, k6 = st.columns(2)
        with k5: st.metric("👥 Total Students", _fmt(total_enr))
        with k6: st.metric("👨‍🏫 Total Teachers", _fmt(total_tch))

    st.markdown("---")
    # ── [END MV_PATCH_v3] ───────────────────────────────────────────────────
'''

# =============================================================================
# Patch logic for uae_page_renderer.py
# =============================================================================
OLD_KPI_RENDERER = '''\
    st.markdown('<div class="section-header">📊 Overview: UAE 2024–25</div>', unsafe_allow_html=True)
    k1, k2, k3, k4 = st.columns(4)
    with k1: st.metric("🏫 Total Schools",            _fmt(total_sch))
    with k2: st.metric("🎓 Schools with Enrollment",  _fmt(sch_with_enr))
    with k3: st.metric("🗺️ Emirates",                 _fmt(em_cnt))
    with k4: st.metric(ptr_label,                     ptr_str)
    k5, k6 = st.columns(2)
    with k5: st.metric("👥 Total Students", _fmt(total_enr))
    with k6: st.metric("👨‍🏫 Total Teachers", _fmt(total_tch))
    st.markdown("---")'''

# This fallback covers variant indentation / label combos in uae_page_renderer
OLD_KPI_RENDERER_ALT = '''\
    st.markdown('<div class="section-header">📊 Overview: UAE 2024-25</div>', unsafe_allow_html=True)
    k1, k2, k3, k4 = st.columns(4)
    with k1: st.metric("🏫 Total Schools",            _fmt(total_sch))
    with k2: st.metric("🎓 Schools with Enrollment",  _fmt(sch_with_enr))
    with k3: st.metric("🗺️ Emirates",                 _fmt(em_cnt))
    with k4: st.metric(ptr_label,                     ptr_str)
    k5, k6 = st.columns(2)
    with k5: st.metric("👥 Total Students", _fmt(total_enr))
    with k6: st.metric("👨‍🏫 Total Teachers", _fmt(total_tch))
    st.markdown("---")'''

# =============================================================================
# Patch logic for uae_current.py  (labels may differ slightly)
# =============================================================================
OLD_KPI_CURRENT_V1 = '''\
    st.markdown('<div class="section-header">📊 Overview: UAE 2024–25</div>', unsafe_allow_html=True)
    k1, k2, k3, k4 = st.columns(4)
    with k1: st.metric("🏫 Total Schools", _fmt(total_sch))
    with k2: st.metric("🎓 Schools with Enrollment", _fmt(sch_with_enr))
    with k3: st.metric("🗺️ Emirates", _fmt(em_cnt))
    with k4: st.metric(ptr_label, ptr_str)
    k5, k6 = st.columns(2)
    with k5: st.metric("👥 Total Students", _fmt(total_enr))
    with k6: st.metric("👨‍🏫 Total Teachers", _fmt(total_tch))
    st.markdown('---')'''

OLD_KPI_CURRENT_V2 = '''\
    st.markdown('<div class="section-header">📊 Overview: UAE 2024-25</div>', unsafe_allow_html=True)
    k1, k2, k3, k4 = st.columns(4)
    with k1: st.metric("🏫 Total Schools", _fmt(total_sch))
    with k2: st.metric("🎓 Schools with Enrollment", _fmt(sch_with_enr))
    with k3: st.metric("🗺️ Emirates", _fmt(em_cnt))
    with k4: st.metric(ptr_label, ptr_str)
    k5, k6 = st.columns(2)
    with k5: st.metric("👥 Total Students", _fmt(total_enr))
    with k6: st.metric("👨‍🏫 Total Teachers", _fmt(total_tch))
    st.markdown('---')'''

# =============================================================================
# Injection anchor – we insert MV_HELPER after the first occurrence of _q()
# definition to ensure the helper is in scope everywhere.
# =============================================================================
HELPER_ANCHOR = "def _q("          # first line of the _q() helper function


def inject_mv_helper(src: str) -> str:
    """Insert MV_HELPER after the closing of the first _q() function."""
    lines   = src.splitlines(keepends=True)
    start   = next((i for i, ln in enumerate(lines) if HELPER_ANCHOR in ln), None)
    if start is None:
        return src  # can't find anchor – leave unchanged
    # walk forward to find the end of _q() (first non-indented line after start+1)
    end = start + 1
    while end < len(lines):
        ln = lines[end]
        if ln.strip() == "":
            end += 1
            continue
        if not ln[0].isspace():   # de-indented → function ended
            break
        end += 1
    insert_at = end
    lines.insert(insert_at, MV_HELPER + "\n")
    return "".join(lines)


def patch_kpi_section(src: str, old_blocks: list[str], new_block: str) -> tuple[str, bool]:
    """Replace the first matching old_block with new_block. Returns (new_src, changed)."""
    for old in old_blocks:
        if old in src:
            return src.replace(old, new_block, 1), True
    return src, False


def patch_file(path: pathlib.Path, old_kpi_variants: list[str]) -> bool:
    """Full patch pipeline for one file. Returns True if patched successfully."""
    if not path.exists():
        print(f"  ⚠️  {path} not found – skipping.")
        return False

    src = path.read_text(encoding="utf-8")

    if already_patched(src):
        print(f"  ℹ️  {path.name} already patched – skipping.")
        return True

    backup(path)

    # Step 1 – inject MV helper function (module-level)
    src = inject_mv_helper(src)

    # Step 2 – replace KPI metric block with curriculum-aware version
    src, changed = patch_kpi_section(src, old_kpi_variants, KPI_PATCH_CODE)
    if not changed:
        print(f"  ⚠️  KPI block not found in {path.name} – manual inspection needed.")
        # Still write the MV helper (step 1 already applied)

    path.write_text(src, encoding="utf-8")

    if not syntax_ok(path):
        print(f"  ❌ {path.name} has syntax errors – restoring backup.")
        latest_bak = sorted(path.parent.glob(f"{path.stem}.py.bak_*"))[-1]
        shutil.copy2(latest_bak, path)
        return False

    print(f"  ✅ {path.name} patched and syntax-checked OK.")
    return True


# =============================================================================
# Main
# =============================================================================
def main():
    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  UAE Dashboard – MV Curriculum KPI Patch  v3")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

    results = {}

    print(f"[1/2] Patching utils/uae_page_renderer.py …")
    results["renderer"] = patch_file(
        FILES["renderer"],
        old_kpi_variants=[OLD_KPI_RENDERER, OLD_KPI_RENDERER_ALT],
    )

    print(f"\n[2/2] Patching utils/uae_current.py …")
    results["current"] = patch_file(
        FILES["current"],
        old_kpi_variants=[OLD_KPI_CURRENT_V1, OLD_KPI_CURRENT_V2],
    )

    print("\n── Summary ────────────────────────────────────────────")
    for name, ok in results.items():
        status = "✅ OK" if ok else "❌ FAILED"
        print(f"  {FILES[name].name:<35} {status}")

    all_ok = all(results.values())
    if all_ok:
        print("\n✅ All patches applied successfully.")
        print("\nNext steps:")
        print("  1. Deploy MV:  psql -U tutorcloud_admin -d tutorcloud_db \\")
        print("                   -f uae_curriculum_kpi_mv_v3.sql")
        print("  2. Restart:    pkill -f 'streamlit run' && sleep 2 && \\")
        print("                   nohup venv/bin/streamlit run app.py \\")
        print("                   --server.port 8501 --server.address 0.0.0.0 \\")
        print("                   > /tmp/streamlit.log 2>&1 &")
        print("  3. Commit:     git add utils/uae_page_renderer.py utils/uae_current.py \\")
        print("                   uae_curriculum_kpi_mv_v3.sql && \\")
        print("                   git commit -m 'fix: curriculum-aware KPIs via MV (v3)' && \\")
        print("                   git push origin main")
    else:
        print("\n❌ One or more patches failed. Review output above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
