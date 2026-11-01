@echo off
cd /d "%~dp0"
python -m claudepad_host run
if errorlevel 1 pause
