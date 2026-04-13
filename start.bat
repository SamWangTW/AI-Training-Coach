@echo off
echo Starting Garmin Training Coach...

start "Backend" cmd /k ".venv\Scripts\uvicorn api.main:app --reload"
timeout /t 2 /nobreak >nul
start "Frontend" cmd /k ".venv\Scripts\streamlit run ui/app.py"

echo Backend: http://localhost:8000
echo Frontend: http://localhost:8501
