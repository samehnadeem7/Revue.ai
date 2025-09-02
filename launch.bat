@echo off
echo Starting Revue.ai Application...
echo.

echo Step 1: Activating virtual environment...
call ..\.venv\Scripts\activate

echo.
echo Step 2: Starting FastAPI Backend...
echo Backend will be available at: http://127.0.0.1:8001
echo API Documentation: http://127.0.0.1:8001/docs
echo.
start "Revue.ai Backend" cmd /k "python -m uvicorn main:app --host 127.0.0.1 --port 8001"

echo.YOU RUINED BOTH FRO
echo Step 3: Starting React Frontend...
echo Frontend will be available at:n
echo.
cd frontend
start "Revue.ai Frontend" cmd /k "npm start"

echo.
echo Application is starting...
echo.
echo Backend: http://127.0.0.1:8001
echo Frontend: http://localhost:3000
echo.
echo Press any key to exit this launcher...
pause > nul
