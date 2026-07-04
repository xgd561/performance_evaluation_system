@echo off
setlocal enabledelayedexpansion

set "ERRORS=0"

echo [P0-01] Verifying project directory structure...
echo.

REM Define required directories
set "DIRS=backend\app\api backend\app\core backend\app\db backend\app\models backend\app\schemas backend\app\crud backend\app\services backend\app\utils backend\.venv frontend\src\views frontend\src\components frontend\src\api frontend\src\stores frontend\src\router frontend\src\composables frontend\src\types frontend\src\assets scripts tests data\db logs uploads"

REM Check directories
for %%D in (%DIRS%) do (
    if exist "%%D\" (
        echo [OK]   Directory exists: %%D
    ) else (
        echo [FAIL] Directory missing: %%D
        set /a ERRORS+=1
    )
)

echo.

REM Check marker files
if exist "backend\__init__.py" (
    echo [OK]   File exists: backend\__init__.py
) else (
    echo [FAIL] File missing: backend\__init__.py
    set /a ERRORS+=1
)

if exist "frontend\package.json" (
    echo [OK]   File exists: frontend\package.json
) else (
    echo [FAIL] File missing: frontend\package.json
    set /a ERRORS+=1
)

echo.

if %ERRORS%==0 (
    echo ========================================
    echo [PASS] All directories and files verified.
    echo ========================================
    exit /b 0
) else (
    echo ========================================
    echo [FAIL] %ERRORS% check(s) failed.
    echo ========================================
    exit /b 1
)
