@echo off
cd /d "%~dp0"
python -m claudepad_host install %*
pause
