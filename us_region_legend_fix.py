#!/usr/bin/env python3
from pathlib import Path
import shutil
import py_compile
import sys

ROOT = Path('/home/noagedevadmin/tutorcloud/tutorcloud-global-dashboard')
TARGET = ROOT / 'ui_styles.py'

OLD = """        _chosen = st.selectbox(
            label='🌍 Region',
            options=_VALID_REGIONS,
            index=_VALID_REGIONS.index(_cur),
            key='tc_region_selector',
            label_visibility='visible',
        )
"""

NEW = """        _chosen = st.selectbox(
            label='🌍 Region',
            options=_VALID_REGIONS,
            index=_VALID_REGIONS.index(_cur),
            key='tc_region_selector',
            label_visibility='collapsed',
        )
"""


def main() -> int:
    if not TARGET.exists():
        print(f'ERROR: File not found: {TARGET}')
        return 1

    text = TARGET.read_text(encoding='utf-8')

    if NEW in text:
        print('No change needed: duplicate region legend fix already present.')
        return 0

    if OLD not in text:
        print('ERROR: Expected selectbox block not found in ui_styles.py')
        return 2

    backup = TARGET.with_name(f"ui_styles.py.bak_region_legend_fix")
    shutil.copy2(TARGET, backup)
    TARGET.write_text(text.replace(OLD, NEW, 1), encoding='utf-8')

    try:
        py_compile.compile(str(TARGET), doraise=True)
    except Exception as exc:
        shutil.copy2(backup, TARGET)
        print('ERROR: Syntax validation failed after patch. Original restored.')
        print(exc)
        return 3

    print('SUCCESS: Removed duplicate region legend by collapsing the selectbox label.')
    print(f'Patched file: {TARGET}')
    print(f'Backup file:  {backup}')
    print('Next step: restart Streamlit to reflect the UI change.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
