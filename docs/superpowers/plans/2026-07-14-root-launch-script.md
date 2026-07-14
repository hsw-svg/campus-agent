# Root Launch Script Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a root `start.cmd` that starts the API with the project virtual
environment and the Vite web application in separate visible consoles.

**Architecture:** A single Windows batch file derives the repository root from
its own path and performs prerequisite checks before opening one command window
per service. The API command uses `start /d` to run Uvicorn from `apps\api`;
the web command uses the same mechanism to run the existing npm script from
`apps\web`.

**Tech Stack:** Windows Command Processor, Python virtual environment,
Uvicorn, npm, Vite.

---

### Task 1: Create the root launch script

**Files:**
- Create: `start.cmd`
- Test: Manual launch and HTTP health check

- [ ] **Step 1: Confirm the script does not already exist**

Run: `Test-Path start.cmd`

Expected: `False`.

- [ ] **Step 2: Create `start.cmd` with prerequisite checks and launch commands**

```bat
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
```

- [ ] **Step 3: Verify batch syntax and prerequisite behavior**

Run: `cmd.exe /d /c start.cmd`

Expected: the script opens an API console and a web console, each retaining
its own logs. The parent console reports both URLs and exits successfully.

- [ ] **Step 4: Verify both local services**

Run: `Invoke-RestMethod http://localhost:8000/api/health`

Expected: a JSON health report. Load `http://localhost:5173` in a browser and
confirm the Vite application is served.

- [ ] **Step 5: Commit the implementation**

```powershell
git add start.cmd docs/superpowers/plans/2026-07-14-root-launch-script.md
git commit -m "feat: add root development launcher"
```
