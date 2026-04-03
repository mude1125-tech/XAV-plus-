@echo off
cd /d "%~dp0"
pip install -r requirements.txt --quiet
start http://localhost:7860
python app.py
