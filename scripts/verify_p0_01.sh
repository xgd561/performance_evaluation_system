#!/usr/bin/env bash
set -euo pipefail

ERRORS=0

echo "[P0-01] Verifying project directory structure..."
echo ""

# Define required directories
DIRS=(
  "backend/app/api"
  "backend/app/core"
  "backend/app/db"
  "backend/app/models"
  "backend/app/schemas"
  "backend/app/crud"
  "backend/app/services"
  "backend/app/utils"
  "backend/.venv"
  "frontend/src/views"
  "frontend/src/components"
  "frontend/src/api"
  "frontend/src/stores"
  "frontend/src/router"
  "frontend/src/composables"
  "frontend/src/types"
  "frontend/src/assets"
  "scripts"
  "tests"
  "data/db"
  "logs"
  "uploads"
)

# Check directories
for dir in "${DIRS[@]}"; do
  if [ -d "$dir" ]; then
    echo "[OK]   Directory exists: $dir"
  else
    echo "[FAIL] Directory missing: $dir"
    ((ERRORS++))
  fi
done

echo ""

# Check marker files
if [ -f "backend/__init__.py" ]; then
  echo "[OK]   File exists: backend/__init__.py"
else
  echo "[FAIL] File missing: backend/__init__.py"
  ((ERRORS++))
fi

if [ -f "frontend/package.json" ]; then
  echo "[OK]   File exists: frontend/package.json"
else
  echo "[FAIL] File missing: frontend/package.json"
  ((ERRORS++))
fi

echo ""

if [ "$ERRORS" -eq 0 ]; then
  echo "========================================"
  echo "[PASS] All directories and files verified."
  echo "========================================"
  exit 0
else
  echo "========================================"
  echo "[FAIL] $ERRORS check(s) failed."
  echo "========================================"
  exit 1
fi
