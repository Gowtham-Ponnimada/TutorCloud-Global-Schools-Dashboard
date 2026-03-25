#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime
from pathlib import Path

ROOT = Path('/home/noagedevadmin/tutorcloud/tutorcloud-global-dashboard')
TARGET = ROOT / 'us_phase1_final_1a_load.py'

OLD_STATE = """    state_staff AS (\n        SELECT statename, st,\n               MAX(CASE WHEN total_indicator = 'Education Unit Total' THEN NULLIF(teachers,'')::numeric END) AS total_teachers\n        FROM {SCHEMA}.{TABLE_MAP['sea_staff']}\n        WHERE school_year = '{DASHBOARD_YEAR}'\n        GROUP BY statename, st\n    )\n"""

NEW_STATE = """    state_staff AS (\n        SELECT statename, st,\n               MAX(CASE\n                   WHEN staff = 'Teachers, Prekindergarten through Grade 12'\n                    AND total_indicator = 'Category Set A'\n                   THEN NULLIF(staff_count,'')::numeric\n               END) AS total_teachers\n        FROM {SCHEMA}.{TABLE_MAP['sea_staff']}\n        WHERE school_year = '{DASHBOARD_YEAR}'\n        GROUP BY statename, st\n    )\n"""

OLD_LEA = """    lea_staff AS (\n        SELECT leaid,\n               MAX(CASE WHEN total_indicator = 'Education Unit Total' THEN NULLIF(teachers,'')::numeric END) AS total_teachers\n        FROM {SCHEMA}.{TABLE_MAP['lea_staff']}\n        WHERE school_year = '{DASHBOARD_YEAR}'\n        GROUP BY leaid\n    )\n"""

NEW_LEA = """    lea_staff AS (\n        SELECT leaid,\n               MAX(CASE\n                   WHEN staff = 'Teachers, Prekindergarten through Grade 12'\n                    AND total_indicator = 'Category Set A'\n                   THEN NULLIF(staff_count,'')::numeric\n               END) AS total_teachers\n        FROM {SCHEMA}.{TABLE_MAP['lea_staff']}\n        WHERE school_year = '{DASHBOARD_YEAR}'\n        GROUP BY leaid\n    )\n"""


def main() -> int:
    if not TARGET.exists():
        print(f'ERROR: target file not found: {TARGET}')
        return 1
    text = TARGET.read_text(encoding='utf-8')
    if OLD_STATE not in text:
        print('ERROR: expected state staff block not found; no changes applied')
        return 1
    if OLD_LEA not in text:
        print('ERROR: expected LEA staff block not found; no changes applied')
        return 1
    updated = text.replace(OLD_STATE, NEW_STATE).replace(OLD_LEA, NEW_LEA)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup = TARGET.with_name(TARGET.name + f'.bak_{ts}')
    backup.write_text(text, encoding='utf-8')
    TARGET.write_text(updated, encoding='utf-8')
    print(f'Backup created: {backup}')
    print(f'Patched: {TARGET}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
