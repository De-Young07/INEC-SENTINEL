@echo off
cd /d "%~dp0"
python -m uvicorn src.web_api:app --host 127.0.0.1 --port 8600
if errorlevel 1 pause
