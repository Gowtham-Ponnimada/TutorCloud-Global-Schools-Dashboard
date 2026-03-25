#!/usr/bin/env bash
set -Eeuo pipefail

# Usage:
#   chmod +x apply_validate_commit_push.sh
#   ./apply_validate_commit_push.sh us_india_parity_patch_v1.py "feat: align US dashboard with India layout"
#
# Defaults:
#   BRANCH=feature/us-dashboard-parity
#   REMOTE=origin
#   STREAMLIT_PORT=8501
#
# Optional env vars:
#   BRANCH=main
#   REMOTE=origin
#   STREAMLIT_PORT=8501

PATCH_FILE="${1:-}"
COMMIT_MSG="${2:-chore: apply dashboard patch}"
BRANCH="${BRANCH:-feature/us-dashboard-parity}"
REMOTE="${REMOTE:-origin}"
STREAMLIT_PORT="${STREAMLIT_PORT:-8501}"

if [[ -z "$PATCH_FILE" ]]; then
  echo "ERROR: Missing patch file argument."
  echo "Example: ./apply_validate_commit_push.sh us_india_parity_patch_v1.py \"feat: align US dashboard with India layout\""
  exit 1
fi

if [[ ! -f "$PATCH_FILE" ]]; then
  echo "ERROR: Patch file not found: $PATCH_FILE"
  exit 1
fi

if [[ ! -d .git ]]; then
  echo "ERROR: Current directory is not a git repository."
  exit 1
fi

echo "==> Repo root: $(pwd)"
echo "==> Patch file: $PATCH_FILE"
echo "==> Branch: $BRANCH"
echo "==> Remote: $REMOTE"

CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
echo "==> Current branch: $CURRENT_BRANCH"

if git show-ref --verify --quiet "refs/heads/$BRANCH"; then
  git checkout "$BRANCH"
else
  git checkout -b "$BRANCH"
fi

echo "==> Running patch"
python3 "$PATCH_FILE"

echo "==> Syntax checks"
python3 -m py_compile ui_styles.py
python3 -m py_compile utils/us_page_renderer.py
python3 -m py_compile pages/*.py || true

echo "==> Restarting Streamlit"
pkill -f 'streamlit run' 2>/dev/null || true
sleep 3
nohup venv/bin/streamlit run app.py --server.port "$STREAMLIT_PORT" --server.address 0.0.0.0 > /tmp/streamlit.log 2>&1 &
sleep 8

echo "==> Streamlit log tail"
tail -80 /tmp/streamlit.log || true

echo "==> Git status"
git status --short

echo "==> Staging changes"
git add utils/us_page_renderer.py ui_styles.py pages scripts sql data reports . || true

echo "==> Commit"
if git diff --cached --quiet; then
  echo "No staged changes to commit."
else
  git commit -m "$COMMIT_MSG"
fi

echo "==> Push"
git push -u "$REMOTE" "$BRANCH"

echo "==> Completed"
echo "Branch pushed: $BRANCH"
echo "Next: verify the GitHub branch and smoke test the app in browser."
