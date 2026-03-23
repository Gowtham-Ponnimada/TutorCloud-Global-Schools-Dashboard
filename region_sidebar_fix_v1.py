#!/usr/bin/env python3
"""
region_sidebar_fix_v1.py
------------------------
Permanent fix for missing Region selector in sidebar.

Root cause:
- render_region_badge() returns early when _badge_rendered=True
- that prevents the sidebar Region selector from rendering
- result: pages show Apply Filters but no Region dropdown

Fix:
- do NOT return early
- only dedupe the floating top-right badge
- always render the sidebar Region selector
- make label visible for robustness
"""

from pathlib import Path
from datetime import datetime
import shutil
import ast
import sys

FILE = Path("ui_styles.py")

OLD_TOP = """    if st.session_state.get("_badge_rendered", False):
        return st.session_state.get("selected_region",
               st.session_state.get("tc_region_selector", "India"))
    st.session_state["_badge_rendered"] = True
"""

NEW_TOP = """    # REGION_SIDEBAR_FIX_v1:
    # Never return early here. The old global guard hid the sidebar Region
    # selector on later page renders. We only dedupe the floating badge.
    _badge_already_rendered = st.session_state.get("_badge_rendered", False)
"""

OLD_BADGE = """    st.markdown(
        '<div style="'
        'position:fixed;top:0.38rem;right:4.8rem;z-index:1000001;'
        'background:linear-gradient(135deg,#FF9933 0%,#f5f5f5 50%,#138808 100%);'
        'padding:5px 16px;border-radius:20px;'
        'font-size:0.75rem;font-weight:700;color:#1a1a1a;'
        'border:1px solid rgba(0,0,0,.12);'
        'display:flex;align-items:center;gap:6px;'
        'box-shadow:0 2px 10px rgba(0,0,0,.20);'
        'pointer-events:none;user-select:none;white-space:nowrap;'
        f'">&#127757;&nbsp;Region:&nbsp;<strong>{_cur}</strong></div>',
        unsafe_allow_html=True,
    )
"""

NEW_BADGE = """    if not _badge_already_rendered:
        st.markdown(
            '<div style="'
            'position:fixed;top:0.38rem;right:4.8rem;z-index:1000001;'
            'background:linear-gradient(135deg,#FF9933 0%,#f5f5f5 50%,#138808 100%);'
            'padding:5px 16px;border-radius:20px;'
            'font-size:0.75rem;font-weight:700;color:#1a1a1a;'
            'border:1px solid rgba(0,0,0,.12);'
            'display:flex;align-items:center;gap:6px;'
            'box-shadow:0 2px 10px rgba(0,0,0,.20);'
            'pointer-events:none;user-select:none;white-space:nowrap;'
            f'">&#127757;&nbsp;Region:&nbsp;<strong>{_cur}</strong></div>',
            unsafe_allow_html=True,
        )
        st.session_state["_badge_rendered"] = True
"""

OLD_LABEL = """        _chosen = st.selectbox(
            label='Region',
            options=_VALID_REGIONS,
            index=_VALID_REGIONS.index(_cur),
            key='tc_region_selector',
            label_visibility='collapsed',
        )
"""

NEW_LABEL = """        _chosen = st.selectbox(
            label='🌍 Region',
            options=_VALID_REGIONS,
            index=_VALID_REGIONS.index(_cur),
            key='tc_region_selector',
            label_visibility='visible',
        )
"""

def main():
    print("\n" + "━" * 62)
    print("  Region Sidebar Fix v1  (restore Region dropdown permanently)")
    print("━" * 62 + "\n")

    if not FILE.exists():
        print(f"❌ File not found: {FILE}")
        sys.exit(1)

    src = FILE.read_text(encoding="utf-8")

    if "REGION_SIDEBAR_FIX_v1" in src:
        print("⚠️ ui_styles.py already patched with REGION_SIDEBAR_FIX_v1.")
        return

    changed = False

    if OLD_TOP in src:
        src = src.replace(OLD_TOP, NEW_TOP, 1)
        print("✅ Removed early return that hid the Region selector.")
        changed = True
    else:
        print("❌ Could not find OLD_TOP block.")

    if OLD_BADGE in src:
        src = src.replace(OLD_BADGE, NEW_BADGE, 1)
        print("✅ Floating badge dedupe logic updated.")
        changed = True
    else:
        print("❌ Could not find OLD_BADGE block.")

    if OLD_LABEL in src:
        src = src.replace(OLD_LABEL, NEW_LABEL, 1)
        print("✅ Region dropdown label made visible.")
        changed = True
    else:
        print("❌ Could not find OLD_LABEL block.")

    if not changed:
        print("\n❌ No changes applied.")
        sys.exit(1)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = FILE.with_name(f"{FILE.name}.bak_regionfix_{ts}")
    shutil.copy2(FILE, backup)
    print(f"✅ Backup created: {backup.name}")

    FILE.write_text(src, encoding="utf-8")

    try:
        ast.parse(src)
        print("✅ ui_styles.py syntax OK")
    except SyntaxError as e:
        print(f"❌ Syntax error after patch: {e}")
        sys.exit(1)

    print("\n✅ Patch applied successfully.")
    print("\nNext steps:")
    print("1. Restart Streamlit")
    print("2. Verify Region dropdown appears above Apply Filters")
    print("3. Commit and push\n")

if __name__ == "__main__":
    main()
