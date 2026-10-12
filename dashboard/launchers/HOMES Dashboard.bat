@echo off
REM Windows: double-click to open the HOMES dashboard.
cd /d "%~dp0..\.."
where pythonw >nul 2>nul && (start "" pythonw dashboard\homes_dashboard.py) || (python dashboard\homes_dashboard.py)
