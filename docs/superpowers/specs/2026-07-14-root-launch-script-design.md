# Root Launch Script Design

## Goal

Provide a Windows `start.cmd` at the repository root that launches the local
API and web development servers from one double-clickable entry point.

## Scope

- Require the existing root `.venv` for the API process.
- Start the FastAPI application on port `8000` from `apps/api`.
- Start the Vite application on its default port `5173` from `apps/web`.
- Run each service in its own command window so its output remains visible and
  either service can be stopped independently.
- Check for `.venv\Scripts\python.exe` and `apps\web\node_modules` before
  starting processes, with actionable Chinese error messages when either is
  unavailable.

## Out Of Scope

- Installing Python or Node dependencies.
- Starting PostgreSQL or other Docker Compose services.
- Changing application ports, API configuration, or `.env` files.

## Behavior

The script resolves paths relative to its own location, so it works regardless
of the caller's current directory. After prerequisites pass, it uses `start`
to create an API window running `.venv\Scripts\python.exe -m uvicorn
app.main:app --host 0.0.0.0 --port 8000` and a web window running `npm.cmd run
dev`. The parent window reports both local URLs and returns after issuing the
two launch requests.

## Verification

Run `start.cmd`, confirm that two service windows open, then request
`http://localhost:8000/api/health` and load `http://localhost:5173`.
