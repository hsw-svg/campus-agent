# Campus Agent Project Scaffold Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a complete, empty monorepo directory scaffold that gives every documented delivery phase an explicit home while preserving anonymous-workspace isolation boundaries.

**Architecture:** The repository is separated into deployable applications, shared contracts/configuration, infrastructure, scripts, and documentation. The FastAPI application is organized by workspace-scoped business domains; the Vue application is organized by user-facing feature modules. `.gitkeep` files retain empty directory boundaries until implementation begins.

**Tech Stack:** Vue 3, Vite, TypeScript, Element Plus, Pinia, Vue Router, Python 3.11+, FastAPI, Pydantic, SQLAlchemy 2.0, Alembic, PostgreSQL 16 with pgvector, Docker Compose.

---

## File Structure

| Path | Responsibility |
| --- | --- |
| `apps/web/src/` | Vue client code, split into transport, shared UI, routing, state, views, and feature modules. |
| `apps/api/app/` | FastAPI code, split into HTTP, platform services, data access, business domains, and external adapters. |
| `apps/api/app/domains/` | Workspace-scoped domains: workspaces, conversations, attachments, RAG, agents, artifacts, and teacher interactions. |
| `packages/contracts/` | Shared API, SSE, and structured agent-result contracts. |
| `packages/config/` | Shared project conventions and quality configuration. |
| `infra/` | Docker, Nginx, PostgreSQL, and pgvector deployment assets. |
| `scripts/` | Non-production setup, migration, and demonstrator scripts. |
| `storage/` | Git-ignored runtime root for the local object-storage implementation. |
| `docs/architecture/` | Living architecture and workspace-isolation guidance. |

### Task 1: Create application and domain boundaries

**Files:**
- Create: `apps/web/src/{api,components,composables,modules/{workspace,conversation,attachment,agent,artifact},router,stores,views}/.gitkeep`
- Create: `apps/api/app/{api,core,db,integrations/{llm,embedding,storage,parsing},tests}/.gitkeep`
- Create: `apps/api/app/domains/{workspaces,conversations,attachments,rag,agents,artifacts,teacher_interactions}/.gitkeep`

- [ ] **Step 1: Create the web client placement directories**

Run:

```powershell
$web = 'apps/web/src'
@('api','components','composables','modules/workspace','modules/conversation','modules/attachment','modules/agent','modules/artifact','router','stores','views') | ForEach-Object {
  $path = Join-Path $web $_
  New-Item -ItemType Directory -Force $path | Out-Null
  New-Item -ItemType File -Force (Join-Path $path '.gitkeep') | Out-Null
}
```

Expected: Each web client responsibility has a retained empty directory.

- [ ] **Step 2: Create backend platform and adapter directories**

Run:

```powershell
$api = 'apps/api/app'
@('api','core','db','integrations/llm','integrations/embedding','integrations/storage','integrations/parsing','tests') | ForEach-Object {
  $path = Join-Path $api $_
  New-Item -ItemType Directory -Force $path | Out-Null
  New-Item -ItemType File -Force (Join-Path $path '.gitkeep') | Out-Null
}
```

Expected: All shared FastAPI concerns and external integration seams have retained directories.

- [ ] **Step 3: Create backend workspace-scoped domain directories**

Run:

```powershell
$domains = 'apps/api/app/domains'
@('workspaces','conversations','attachments','rag','agents','artifacts','teacher_interactions') | ForEach-Object {
  $path = Join-Path $domains $_
  New-Item -ItemType Directory -Force $path | Out-Null
  New-Item -ItemType File -Force (Join-Path $path '.gitkeep') | Out-Null
}
```

Expected: Each business domain named by the design has a separate home; no user, account, or cross-role domain exists.

### Task 2: Create shared, deployment, and documentation boundaries

**Files:**
- Create: `packages/{contracts,config}/.gitkeep`
- Create: `infra/{docker,postgres}/.gitkeep`
- Create: `scripts/.gitkeep`
- Create: `storage/.gitignore`
- Create: `docs/architecture/.gitkeep`

- [ ] **Step 1: Create shared-package directories**

Run:

```powershell
@('packages/contracts','packages/config') | ForEach-Object {
  New-Item -ItemType Directory -Force $_ | Out-Null
  New-Item -ItemType File -Force (Join-Path $_ '.gitkeep') | Out-Null
}
```

Expected: Contracts and configuration are distinct from deployable applications.

- [ ] **Step 2: Create infrastructure, script, storage, and architecture directories**

Run:

```powershell
@('infra/docker','infra/postgres','scripts','storage','docs/architecture') | ForEach-Object {
  New-Item -ItemType Directory -Force $_ | Out-Null
}
@('infra/docker','infra/postgres','scripts','docs/architecture') | ForEach-Object {
  New-Item -ItemType File -Force (Join-Path $_ '.gitkeep') | Out-Null
}
```

Expected: Deployment configuration, operational scripts, local storage, and architecture documentation have separate homes.

- [ ] **Step 3: Ignore all runtime object-storage content**

Create `storage/.gitignore` with:

```gitignore
*
!.gitignore
```

Expected: The local object-storage implementation can write runtime files without versioning them.

### Task 3: Add repository-level conventions and validate the tree

**Files:**
- Create: `.gitignore`
- Create: `README.md`

- [ ] **Step 1: Add root ignore rules**

Create `.gitignore` with:

```gitignore
.env
.env.*
!.env.example
node_modules/
dist/
coverage/
.pytest_cache/
__pycache__/
*.py[cod]
.mypy_cache/
.ruff_cache/
.venv/
venv/
storage/*
!storage/.gitignore
```

Expected: Secrets, package caches, build output, test output, Python bytecode, virtual environments, and runtime storage files are excluded.

- [ ] **Step 2: Add a concise repository map**

Create `README.md` with a title, a one-sentence statement that this is an anonymous-workspace campus AI assistant, and the top-level directory responsibilities from the File Structure table.

Expected: A new contributor can identify where client, service, contracts, infrastructure, documentation, scripts, and runtime storage belong.

- [ ] **Step 3: Validate expected directory markers and prohibited account modules**

Run:

```powershell
$required = @(
  'apps/web/src/modules/workspace/.gitkeep',
  'apps/web/src/modules/conversation/.gitkeep',
  'apps/api/app/domains/workspaces/.gitkeep',
  'apps/api/app/domains/rag/.gitkeep',
  'apps/api/app/domains/agents/.gitkeep',
  'apps/api/app/domains/teacher_interactions/.gitkeep',
  'packages/contracts/.gitkeep',
  'infra/docker/.gitkeep',
  'storage/.gitignore',
  'docs/architecture/.gitkeep'
)
$missing = $required | Where-Object { -not (Test-Path $_) }
if ($missing) { throw "Missing scaffold paths: $($missing -join ', ')" }
$prohibited = Get-ChildItem -Recurse -Directory apps | Where-Object { $_.Name -match '^(users?|accounts?|auth|login|jwt|classes?|enrollment)$' }
if ($prohibited) { throw "Prohibited scaffold paths: $($prohibited.FullName -join ', ')" }
Write-Output 'Scaffold validation passed.'
```

Expected: `Scaffold validation passed.`

- [ ] **Step 4: Inspect the final directory tree**

Run:

```powershell
Get-ChildItem -Recurse -Force | Select-Object FullName
```

Expected: The listing matches the File Structure table and retains all intentionally empty directories through `.gitkeep` files.
