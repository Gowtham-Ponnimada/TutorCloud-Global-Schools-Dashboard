"""
uae_kpi_block_patch_v3b.py
===========================
Targeted fix: replaces ONLY the KPI metric block inside
render_uae_state_dashboard() in both utils files.

The _mv_curriculum_kpi helper is already injected by v3 patch.
This script only fixes the KPI display section that v3 missed.

Run from repo root:
    python3 uae_kpi_block_patch_v3b.py
"""

import ast, pathlib, shutil, time, sys

REPO_ROOT = pathlib.Path(".")

# ── Exact KPI blocks found in the live files (verbatim from GitHub) ──────────

# uae_page_renderer.py  ← em-dash "—", 4-metric layout, male/female second row
OLD_RENDERER = '''    # Display KPI row
    st.markdown('<div class="section-header">📊 Overview — UAE 2024-25</div>', unsafe_allow_html=True)
    k1, k2, k3, k4 = st.columns(4)
    with k1: st.metric("🏫 Total Schools",   _fmt(total_sch))
    with k2: st.metric("🎓 Total Students",  _fmt(total_enr))
    with k3: st.metric("👨\u200d🏫 Total Teachers", _fmt(total_tch))
    with k4: st.metric("📊 National PTR",    ptr_str)

    k5, k6 = st.columns(2)
    with k5: st.metric("👦 Male Students",   _fmt(male_enr))
    with k6: st.metric("👧 Female Students", _fmt(female_enr))

    st.markdown("---")'''

# uae_current.py  ← colon ":", 4-metric layout with Schools with Enrollment + Emirates
OLD_CURRENT = '''    st.markdown('<div class="section-header">📊 Overview: UAE 2024\u201325</div>', unsafe_allow_html=True)
    k1, k2, k3, k4 = st.columns(4)
    with k1: st.metric("🏫 Total Schools",          _fmt(total_sch))
    with k2: st.metric("🎓 Schools with Enrollment", _fmt(sch_with_enr))
    with k3: st.metric("🗺️ Emirates",               _fmt(em_cnt))
    with k4: st.metric(ptr_label,                    ptr_str)

    k5, k6 = st.columns(2)
    with k5: st.metric("👥 Total Students",  _fmt(total_enr))
    with k6: st.metric("👨\u200d🏫 Total Teachers", _fmt(total_tch))

    st.markdown("---")'''

# ── Curriculum-aware replacement (same logic for both files) ──────────────────
NEW_KPI_RENDERER = '''    # Display KPI row  [MV_KPI_BLOCK_v3b]
    _curr_active = (
        "curriculum" in filters
        and filters["curriculum"].get("val") not in ("All", "", None)
    )

    if _curr_active:
        _curr_val  = filters["curriculum"]["val"]
        _emir_raw  = filters.get("emirate", {}).get("val") if "emirate" in filters else None
        _edtyp_val = filters.get("education_type", {}).get("val") if "education_type" in filters else None
        _emir_val  = _emir_raw if _emir_raw and _emir_raw not in ("All", "") else None
        _scope_lbl = _emir_val.title() if _emir_val else "UAE"

        mv = _mv_curriculum_kpi(UAE_YEAR, _curr_val, _emir_val, _edtyp_val)

        if mv and mv["row_count"] > 0:
            _mv_schools  = mv["school_count"]
            _mv_enr_ok   = mv["has_enrollment_data"]
            _mv_tch_ok   = mv["has_teacher_data"]

            _mv_students = int(mv["student_count"]) if (_mv_enr_ok and mv["student_count"] is not None) else None
            _mv_male     = int(mv["male_students"]  or 0) if _mv_students is not None else None
            _mv_female   = int(mv["female_students"] or 0) if _mv_students is not None else None
            _mv_teachers = int(mv["teacher_count"]) if (_mv_tch_ok and mv["teacher_count"] is not None) else None
            _mv_ptr      = _fmt_ptr(_mv_students or 0, _mv_teachers or 0) if (_mv_students and _mv_teachers) else "N/A"

            st.markdown(
                f'<div class="section-header">📊 {_scope_lbl} · {_curr_val} · 2024-25</div>',
                unsafe_allow_html=True
            )
            k1, k2, k3, k4 = st.columns(4)
            with k1: st.metric("🏫 Total Schools",
                                _fmt(_mv_schools),
                                help=f"Schools offering {_curr_val} in {_scope_lbl}")
            with k2: st.metric(f"🎓 Students · {_scope_lbl}",
                                _fmt(_mv_students) if _mv_students is not None else "N/A",
                                help="Proportional estimate based on school-share within education type")
            with k3: st.metric(f"👨\u200d🏫 Teachers · {_scope_lbl}",
                                _fmt(_mv_teachers) if _mv_teachers is not None else "N/A",
                                help="Proportional estimate based on school-share within education type")
            with k4: st.metric("📊 PTR", _mv_ptr)

            if _mv_students is not None:
                k5, k6 = st.columns(2)
                with k5: st.metric("👦 Male Students",   _fmt(_mv_male))
                with k6: st.metric("👧 Female Students", _fmt(_mv_female))

            if _mv_enr_ok:
                st.info(
                    f"📌 **Curriculum filter: {_curr_val}  |  Scope: {_scope_lbl}**\\n\\n"
                    f"School count is **exact**. Student & teacher counts are **proportional estimates** "
                    f"(curriculum school-share × emirate/education-type total). "
                    f"Aggregate across all curricula equals the Home page total.",
                    icon="ℹ️"
                )
            else:
                st.warning(
                    f"⚠️ **{_curr_val}** is a private/specialist curriculum. "
                    f"Student enrollment data is not available at curriculum level. "
                    f"Only school count ({_fmt(_mv_schools)}) is accurate.",
                    icon="⚠️"
                )
        else:
            st.info("ℹ️ Curriculum KPI view not yet available — showing emirate-wide totals.", icon="ℹ️")
            mv = None  # fall through

    if not _curr_active or not (mv and mv["row_count"] > 0):
        st.markdown('<div class="section-header">📊 Overview — UAE 2024-25</div>', unsafe_allow_html=True)
        k1, k2, k3, k4 = st.columns(4)
        with k1: st.metric("🏫 Total Schools",   _fmt(total_sch))
        with k2: st.metric("🎓 Total Students",  _fmt(total_enr))
        with k3: st.metric("👨\u200d🏫 Total Teachers", _fmt(total_tch))
        with k4: st.metric("📊 National PTR",    ptr_str)
        k5, k6 = st.columns(2)
        with k5: st.metric("👦 Male Students",   _fmt(male_enr))
        with k6: st.metric("👧 Female Students", _fmt(female_enr))

    st.markdown("---")'''

NEW_KPI_CURRENT = '''    # Display KPI row  [MV_KPI_BLOCK_v3b]
    _curr_active = (
        "curriculum" in filters
        and filters["curriculum"].get("val") not in ("All", "", None)
    )

    if _curr_active:
        _curr_val  = filters["curriculum"]["val"]
        _emir_raw  = filters.get("emirate", {}).get("val") if "emirate" in filters else None
        _edtyp_val = filters.get("education_type", {}).get("val") if "education_type" in filters else None
        _emir_val  = _emir_raw if _emir_raw and _emir_raw not in ("All", "") else None
        _scope_lbl = _emir_val.title() if _emir_val else "UAE"

        mv = _mv_curriculum_kpi(UAE_YEAR, _curr_val, _emir_val, _edtyp_val)

        if mv and mv["row_count"] > 0:
            _mv_schools  = mv["school_count"]
            _mv_enr_ok   = mv["has_enrollment_data"]
            _mv_tch_ok   = mv["has_teacher_data"]

            _mv_students = int(mv["student_count"]) if (_mv_enr_ok and mv["student_count"] is not None) else None
            _mv_teachers = int(mv["teacher_count"]) if (_mv_tch_ok and mv["teacher_count"] is not None) else None
            _mv_ptr      = _fmt_ptr(_mv_students or 0, _mv_teachers or 0) if (_mv_students and _mv_teachers) else "N/A"
            _ptr_lbl     = f"📊 {_scope_lbl} PTR"

            st.markdown(
                f'<div class="section-header">📊 {_scope_lbl} · {_curr_val} · 2024\u201325</div>',
                unsafe_allow_html=True
            )
            k1, k2, k3, k4 = st.columns(4)
            with k1: st.metric("🏫 Total Schools",
                                _fmt(_mv_schools),
                                help=f"Schools offering {_curr_val} in {_scope_lbl}")
            with k2: st.metric("🎓 Schools with Enrollment",
                                _fmt(_mv_schools))
            with k3: st.metric(f"🗺️ Emirate",
                                _scope_lbl)
            with k4: st.metric(_ptr_lbl, _mv_ptr)

            k5, k6 = st.columns(2)
            with k5: st.metric(f"👥 Students · {_scope_lbl}",
                                _fmt(_mv_students) if _mv_students is not None else "N/A",
                                help="Proportional estimate based on school-share within education type")
            with k6: st.metric(f"👨\u200d🏫 Teachers · {_scope_lbl}",
                                _fmt(_mv_teachers) if _mv_teachers is not None else "N/A",
                                help="Proportional estimate based on school-share within education type")

            if _mv_enr_ok:
                st.info(
                    f"📌 **Curriculum filter: {_curr_val}  |  Scope: {_scope_lbl}**\\n\\n"
                    f"School count is **exact**. Student & teacher counts are **proportional estimates** "
                    f"(curriculum school-share × emirate/education-type total). "
                    f"Aggregate across all curricula equals the Home page total.",
                    icon="ℹ️"
                )
            else:
                st.warning(
                    f"⚠️ **{_curr_val}** is a private/specialist curriculum. "
                    f"Student enrollment data is not available at curriculum level. "
                    f"Only school count ({_fmt(_mv_schools)}) is accurate.",
                    icon="⚠️"
                )
        else:
            st.info("ℹ️ Curriculum KPI view not yet available — showing emirate-wide totals.", icon="ℹ️")
            mv = None

    if not _curr_active or not (mv and mv["row_count"] > 0):
        st.markdown('<div class="section-header">📊 Overview: UAE 2024\u201325</div>', unsafe_allow_html=True)
        k1, k2, k3, k4 = st.columns(4)
        with k1: st.metric("🏫 Total Schools",          _fmt(total_sch))
        with k2: st.metric("🎓 Schools with Enrollment", _fmt(sch_with_enr))
        with k3: st.metric("🗺️ Emirates",               _fmt(em_cnt))
        with k4: st.metric(ptr_label,                    ptr_str)
        k5, k6 = st.columns(2)
        with k5: st.metric("👥 Total Students",  _fmt(total_enr))
        with k6: st.metric("👨\u200d🏫 Total Teachers", _fmt(total_tch))

    st.markdown("---")'''

MARKER = "MV_KPI_BLOCK_v3b"


def backup(path):
    ts   = time.strftime("%Y%m%d_%H%M%S")
    dest = path.with_suffix(f".py.bak_v3b_{ts}")
    shutil.copy2(path, dest)
    print(f"  ✅ backup → {dest.name}")


def syntax_ok(path):
    try:
        ast.parse(path.read_text(encoding="utf-8"))
        return True
    except SyntaxError as e:
        print(f"  ❌ SyntaxError: {e}")
        return False


def patch_file(path, old_block, new_block):
    src = path.read_text(encoding="utf-8")

    if MARKER in src:
        print(f"  ℹ️  {path.name}: KPI block already patched (v3b) — skipping.")
        return True

    # Try exact match first
    if old_block in src:
        backup(path)
        path.write_text(src.replace(old_block, new_block, 1), encoding="utf-8")
        if syntax_ok(path):
            print(f"  ✅ {path.name}: KPI block patched OK.")
            return True
        else:
            # Restore backup
            baks = sorted(path.parent.glob(f"{path.stem}.py.bak_v3b_*"))
            if baks:
                shutil.copy2(baks[-1], path)
            print(f"  ❌ {path.name}: Syntax error after patch — backup restored.")
            return False

    # Exact match failed — try stripping trailing spaces on each line
    print(f"  ⚠️  {path.name}: exact match failed, trying normalised match…")
    def norm(s):
        return "\n".join(ln.rstrip() for ln in s.splitlines())

    src_norm  = norm(src)
    old_norm  = norm(old_block)
    if old_norm in src_norm:
        backup(path)
        patched = src_norm.replace(old_norm, norm(new_block), 1)
        path.write_text(patched, encoding="utf-8")
        if syntax_ok(path):
            print(f"  ✅ {path.name}: KPI block patched OK (normalised).")
            return True
        else:
            baks = sorted(path.parent.glob(f"{path.stem}.py.bak_v3b_*"))
            if baks:
                shutil.copy2(baks[-1], path)
            print(f"  ❌ {path.name}: Syntax error — backup restored.")
            return False

    # Still not found — print diagnostic
    print(f"  ❌ {path.name}: KPI block NOT found even after normalisation.")
    print(f"     Search for this line in the file and paste surrounding 15 lines:")
    print(f"     grep -n 'section-header' {path}")
    return False


def main():
    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  UAE KPI Block Patch v3b  (targeted KPI section fix)")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

    r1 = patch_file(
        REPO_ROOT / "utils" / "uae_page_renderer.py",
        OLD_RENDERER,
        NEW_KPI_RENDERER,
    )
    r2 = patch_file(
        REPO_ROOT / "utils" / "uae_current.py",
        OLD_CURRENT,
        NEW_KPI_CURRENT,
    )

    print("\n── Summary ─────────────────────────────────────────────")
    print(f"  uae_page_renderer.py   {'✅ OK' if r1 else '❌ FAILED'}")
    print(f"  uae_current.py         {'✅ OK' if r2 else '❌ FAILED'}")

    if r1 and r2:
        print("\n✅ Both files patched. Next:")
        print("  pkill -f 'streamlit run' && sleep 2")
        print("  nohup venv/bin/streamlit run app.py \\")
        print("    --server.port 8501 --server.address 0.0.0.0 \\")
        print("    > /tmp/streamlit.log 2>&1 &")
        print("  sleep 10 && grep -iE 'error|started' /tmp/streamlit.log | tail -5")
    else:
        print("\n⚠️  One or more files need manual inspection.")
        print("  Run: grep -n 'section-header' utils/uae_page_renderer.py utils/uae_current.py")
        sys.exit(1)


if __name__ == "__main__":
    main()
