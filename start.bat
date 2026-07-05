@echo off
echo ===================================================
echo Starting AYUSH AI Platform (Frontend + Backend)
echo ===================================================

:: Check if backend has a virtual env, if not instruct user or run without it
cd backend
set PYTHONIOENCODING=utf-8
echo Starting FastAPI Backend on port 8080...
start cmd /k "python web_app.py || echo Failed to start python, make sure dependencies are installed! && pause"

cd ..
echo Starting React Frontend on port 5173...
start cmd /k "npm run dev"

echo.
echo Both servers are starting in new windows.
echo Frontend: http://localhost:5173
echo Backend:  http://localhost:8080
echo ===================================================
pause
