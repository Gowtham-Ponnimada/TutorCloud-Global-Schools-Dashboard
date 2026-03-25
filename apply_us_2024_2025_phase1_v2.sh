#!/usr/bin/env bash
set -euo pipefail

REPO=/home/noagedevadmin/tutorcloud/tutorcloud-global-dashboard
cd "$REPO"

if [[ -x "venv/bin/python" ]]; then
  PY="venv/bin/python"
elif [[ -x ".venv/bin/python" ]]; then
  PY=".venv/bin/python"
else
  PY="python3"
fi

if [[ -x "venv/bin/pip" ]]; then
  PIP="venv/bin/pip"
elif [[ -x ".venv/bin/pip" ]]; then
  PIP=".venv/bin/pip"
else
  PIP="python3 -m pip"
fi

if [[ ! -f us_phase1_final_1a_load.py ]]; then
  echo "ERROR: us_phase1_final_1a_load.py not found in repo root"
  exit 1
fi

if [[ ! -f us_real_data_renderer_patch_v1.py ]]; then
  echo "ERROR: us_real_data_renderer_patch_v1.py not found in repo root"
  exit 1
fi

echo "[0/8] Ensuring Python dependencies in active app environment..."
$PIP install --quiet --disable-pip-version-check psycopg2-binary requests xlsxwriter openpyxl

if ! command -v unzip >/dev/null 2>&1; then
  echo "ERROR: unzip is required but not installed"
  echo "Run: sudo apt-get update && sudo apt-get install -y unzip"
  exit 1
fi

echo "[1/8] Loading NCES CCD Final v1a 2024-2025 data..."
$PY us_phase1_final_1a_load.py

echo "[2/8] Applying US real-data renderer patch..."
$PY us_real_data_renderer_patch_v1.py

echo "[3/8] Validating syntax..."
$PY -m py_compile utils/us_page_renderer.py

echo "[4/8] Quick database validation..."
$PY - <<'PY'
import os
import psycopg2

cfg = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'dbname': os.getenv('DB_NAME', os.getenv('DB_DATABASE', 'tutorcloud_db')),
    'user': os.getenv('DB_USER', 'tutorcloud_admin'),
    'password': os.getenv('DB_PASSWORD', ''),
    'port': int(os.getenv('DB_PORT', '5432')),
}
try:
    from utils.uae_page_renderer import _DB_PARAMS
    if isinstance(_DB_PARAMS, dict):
        for k, v in _DB_PARAMS.items():
            if k in cfg and v not in (None, ''):
                cfg[k] = v
except Exception:
    pass

queries = {
    'dim_states': "select count(*) from us.dim_states where school_year = '2024-2025'",
    'dim_districts': "select count(*) from us.dim_districts where school_year = '2024-2025'",
    'dim_schools': "select count(*) from us.dim_schools where school_year = '2024-2025'",
    'top_states': "select state_name, total_schools, total_students, total_teachers, ptr from us.vw_state_kpis_2024_2025 order by total_schools desc nulls last limit 5",
}

with psycopg2.connect(**cfg) as conn:
    with conn.cursor() as cur:
        for name, q in queries.items():
            cur.execute(q)
            rows = cur.fetchall()
            print(f'--- {name} ---')
            for row in rows:
                print(row)
PY

echo "[5/8] Restarting Streamlit..."
pkill -f 'streamlit run' || true
sleep 3
nohup venv/bin/streamlit run app.py --server.port 8501 --server.address 0.0.0.0 > /tmp/streamlit.log 2>&1 &
sleep 12

echo "[6/8] Git status..."
git status --short

echo "[7/8] Tail log..."
tail -120 /tmp/streamlit.log

echo "[8/8] Suggested next commands..."
echo "git add utils/us_page_renderer.py us_phase1_final_1a_load.py us_real_data_renderer_patch_v1.py apply_us_2024_2025_phase1_v2.sh"
echo "git commit -m 'feat: load 2024-2025 NCES final data for US dashboard'"
echo "git push"

echo "DONE"
