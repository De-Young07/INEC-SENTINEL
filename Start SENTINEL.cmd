@echo off
cd /d "%~dp0"
python -m streamlit run src/app.py
if errorlevel 1 pause
