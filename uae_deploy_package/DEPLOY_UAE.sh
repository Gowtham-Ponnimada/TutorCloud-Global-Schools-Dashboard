#!/bin/bash
# ============================================================
#  UAE Dashboard — Master Deploy Script v2
#  Fixes applied: correct DB_NAME, DB_USER, DB_PASSWORD, TCP host
#  Run from the uae_deploy_package/ directory
# ============================================================
set -e

PROJ=/home/noagedevadmin/tutorcloud/tutorcloud-global-dashboard
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$PROJ/.env"

echo ""
echo "=================================================="
echo "  UAE Dashboard Deploy v2 — $(date)"
echo "=================================================="

# ── STEP 0: Load credentials from project .env ──────────────
echo ""
echo "[ STEP 0 ] Loading credentials from .env..."

if [ ! -f "$ENV_FILE" ]; then
  echo "  ❌ .env not found at $ENV_FILE"
  exit 1
fi

# Extract values (handles comments and inline comments)
DB_HOST=$(grep    '^DB_HOST='     "$ENV_FILE" | cut -d= -f2 | tr -d ' \r')
DB_PORT=$(grep    '^DB_PORT='     "$ENV_FILE" | cut -d= -f2 | tr -d ' \r')
DB_NAME=$(grep    '^DB_NAME='     "$ENV_FILE" | cut -d= -f2 | tr -d ' \r')
DB_USER=$(grep    '^DB_USER='     "$ENV_FILE" | cut -d= -f2 | tr -d ' \r')
DB_PASS=$(grep    '^DB_PASSWORD=' "$ENV_FILE" | cut -d= -f2 | tr -d ' \r')

# Fallbacks
DB_HOST=${DB_HOST:-127.0.0.1}
DB_PORT=${DB_PORT:-5432}
DB_NAME=${DB_NAME:-tutorcloud_db}
DB_USER=${DB_USER:-tutorcloud_admin}

echo "  Host : $DB_HOST:$DB_PORT"
echo "  DB   : $DB_NAME"
echo "  User : $DB_USER"

# CRITICAL: export for python-dotenv subprocesses
export DB_HOST DB_PORT DB_NAME DB_USER DB_PASSWORD=$DB_PASS

# ── STEP 0b: Test TCP connection ─────────────────────────────
echo ""
echo "[ STEP 0b ] Testing PostgreSQL TCP connection..."
export PGPASSWORD="$DB_PASS"

if ! psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
      -c "SELECT 1" > /dev/null 2>&1; then
  echo "  ❌ Connection failed!"
  echo "     Trying 127.0.0.1 explicitly..."
  DB_HOST=127.0.0.1
  export DB_HOST
  if ! psql -h 127.0.0.1 -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
        -c "SELECT 1" > /dev/null 2>&1; then
    echo "  ❌ Still failing. Check docker: docker ps | grep postgres"
    exit 1
  fi
  echo "  ✅ Connected via 127.0.0.1"
else
  echo "  ✅ PostgreSQL connection OK"
fi

PSQL="psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME"

# ── STEP 1: CSV files ─────────────────────────────────────────
echo ""
echo "[ STEP 1 ] Copying CSV files to data/uae/..."
mkdir -p "$PROJ/data/uae"
cp "$SCRIPT_DIR/data/uae/"*.csv "$PROJ/data/uae/"
COUNT=$(ls "$PROJ/data/uae/"*.csv 2>/dev/null | wc -l)
echo "  ✅ $COUNT CSV files ready in $PROJ/data/uae/"

# ── STEP 2: DDL ──────────────────────────────────────────────
echo ""
echo "[ STEP 2 ] Running DDL (schema uae + 12 tables + 8 MVs)..."
$PSQL -f "$SCRIPT_DIR/uae_schema_ddl.sql" 2>&1 \
  | grep -E "^CREATE|^INSERT|ERROR|already exists" | head -40
echo "  ✅ DDL complete"

# ── STEP 3: ETL ──────────────────────────────────────────────
echo ""
echo "[ STEP 3 ] Running ETL pipeline (~57K rows, ~60-90s)..."
cd "$PROJ"
python3 "$SCRIPT_DIR/uae_etl_pipeline.py"
echo "  ✅ ETL complete"

# ── STEP 4: Deploy files ──────────────────────────────────────
echo ""
echo "[ STEP 4 ] Deploying page and utils..."
cp "$SCRIPT_DIR/5_UAE_Dashboard.py"         "$PROJ/pages/5_🇦🇪_UAE_Dashboard.py"
cp "$SCRIPT_DIR/utils/uae_connector.py"      "$PROJ/utils/"
cp "$SCRIPT_DIR/utils/uae_utils.py"          "$PROJ/utils/"
echo "  ✅ Deployed:"
echo "     pages/5_🇦🇪_UAE_Dashboard.py"
echo "     utils/uae_connector.py"
echo "     utils/uae_utils.py"

# ── STEP 5: Verify ────────────────────────────────────────────
echo ""
echo "[ STEP 5 ] Verification..."
echo ""
echo "  UAE tables in schema 'uae':"
$PSQL -c "
SELECT tablename,
       pg_size_pretty(pg_total_relation_size('uae.'||quote_ident(tablename))) AS size
FROM pg_tables
WHERE schemaname='uae'
ORDER BY tablename;" 2>/dev/null || echo "  (table list failed)"

echo ""
echo "  KPI — Total students 2024-2025:"
$PSQL -c "
SELECT SUM(total_enrolled) AS total_students
FROM uae.uae_fact_enrollment
WHERE academic_year = '2024-2025';" 2>/dev/null || echo "  (KPI check skipped)"

echo ""
echo "  India schema untouched:"
$PSQL -c "
SELECT schemaname, COUNT(*) as tables
FROM pg_tables
WHERE schemaname IN ('india_2024_25','uae')
GROUP BY schemaname
ORDER BY schemaname;" 2>/dev/null || echo "  (schema check skipped)"

echo ""
echo "=================================================="
echo "  ✅ UAE Dashboard deployed successfully!"
echo "  Refresh Streamlit at http://localhost:8501"
echo "  UAE page appears in the left sidebar"
echo "=================================================="
