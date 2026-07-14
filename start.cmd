@echo off
setlocal

set "ROOT=%~dp0"
set "PYTHON=%ROOT%.venv\Scripts\python.exe"
set "API_DIR=%ROOT%apps\api"
set "WEB_DIR=%ROOT%apps\web"

if not exist "%PYTHON%" (
  echo [ERROR] Missing Python virtual environment: %PYTHON%
  echo Create it and install API dependencies before starting the project.
  exit /b 1
)

if not exist "%WEB_DIR%\node_modules" (
  echo [ERROR] Missing web dependencies: %WEB_DIR%\node_modules
  echo Run "npm.cmd install" from apps\web before starting the project.
  exit /b 1
)

echo Starting Campus Agent API: http://localhost:8000
start "Campus Agent API" /d "%API_DIR%" cmd /k ""%PYTHON%" -m uvicorn app.main:app --host 0.0.0.0 --port 8000"

echo Starting Campus Agent Web: http://localhost:5173
start "Campus Agent Web" /d "%WEB_DIR%" cmd /k "npm.cmd run dev"

echo Launch requests sent. Close an individual service window to stop that service.
endlocal
