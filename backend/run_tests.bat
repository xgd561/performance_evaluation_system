@echo off
REM Backend test runner for Performance Evaluation System
REM Usage: run_tests.bat [module_name]
REM Examples:
REM   run_tests.bat          - Run all tests
REM   run_tests.bat auth     - Run only auth tests
REM   run_tests.bat employees - Run only employee tests

cd /d "%~dp0"

if "%~1"=="" (
    echo Running all tests...
    python -m pytest tests/ -v --tb=short
) else (
    echo Running tests for %~1...
    python -m pytest tests/test_%~1.py -v --tb=short
)

pause
