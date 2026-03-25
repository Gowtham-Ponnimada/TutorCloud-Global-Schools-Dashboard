#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime
from pathlib import Path

ROOT = Path('/home/noagedevadmin/tutorcloud/tutorcloud-global-dashboard')
TARGET = ROOT / 'utils' / 'us_page_renderer.py'


def replace_exact(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f'Expected block not found for: {label}')
    return text.replace(old, new, 1)


def main() -> int:
    if not TARGET.exists():
        print(f'ERROR: target file not found: {TARGET}')
        return 1

    original = TARGET.read_text(encoding='utf-8')
    updated = original

    # 1) Remove sidebar heading + caption on US pages
    updated = replace_exact(
        updated,
        '    with st.sidebar:\n        st.markdown("## 🇺🇸 US Filters")\n        st.caption("NCES CCD Final v1a · 2024–2025 only")\n',
        '    with st.sidebar:\n',
        'sidebar heading/caption removal',
    )

    # 2) Remove data quality notice text block entirely
    updated = replace_exact(
        updated,
        "def _render_data_quality_note():\n    st.markdown(\n        \"<div class='us-note'><strong>Data scope:</strong> US KPIs now use NCES CCD Final v1a for 2024–2025 only. Teacher and PTR coverage may vary in a few jurisdictions based on source submission quality, so state and district totals should be interpreted within NCES reporting limits.</div>\",\n        unsafe_allow_html=True,\n    )\n\n\n",
        "def _render_footer():\n    st.markdown(\"---\")\n    st.markdown(\n        \"\"\"\n        <div style='text-align: center; padding: 20px; margin-top: 40px; border-top: 1px solid #e0e0e0;'>\n        <p style='margin: 0; color: #666; font-size: 0.95rem;'>TutorCloud Global Dashboard</p>\n        <p style='margin: 5px 0 0 0; color: #666; font-size: 0.95rem;'>© 2026 TutorCloud. All rights reserved.</p>\n        </div>\n        \"\"\",\n        unsafe_allow_html=True,\n    )\n\n\n",
        'data scope note replacement with footer helper',
    )

    # 3) Remove calls to the deleted data note helper
    updated = updated.replace('    _render_data_quality_note()\n', '')

    # 4) Add footer to each US page renderer
    updated = replace_exact(
        updated,
        "        )\n\n\ndef render_us_state_dashboard():\n",
        "        )\n\n    _render_footer()\n\n\ndef render_us_state_dashboard():\n",
        'home footer insertion',
    )

    updated = replace_exact(
        updated,
        "        st.dataframe(directory_df, use_container_width=True, height=520, hide_index=True)\n        _export_buttons(directory_df, \"us_directory_extract_2024_2025\")\n\n\ndef render_us_analytics():\n",
        "        st.dataframe(directory_df, use_container_width=True, height=520, hide_index=True)\n        _export_buttons(directory_df, \"us_directory_extract_2024_2025\")\n\n    _render_footer()\n\n\ndef render_us_analytics():\n",
        'state dashboard footer insertion',
    )

    updated = replace_exact(
        updated,
        "        else:\n            st.info(\"Select at least one dimension and one metric to generate a custom report.\")\n",
        "        else:\n            st.info(\"Select at least one dimension and one metric to generate a custom report.\")\n\n    _render_footer()\n",
        'analytics footer insertion',
    )

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup = TARGET.with_name(TARGET.name + f'.bak_ui_cleanup_{ts}')
    backup.write_text(original, encoding='utf-8')
    TARGET.write_text(updated, encoding='utf-8')

    print(f'Backup created: {backup}')
    print(f'Patched: {TARGET}')
    print('Applied US UI copy cleanup: removed data-scope banner, removed US sidebar heading/caption, added TutorCloud footer to all US pages.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
