# RepoForge AI — Code Repository Intelligence

A full-stack, recruiter-ready **working MVP** for analyzing **public GitHub repositories**. React dashboard + FastAPI backend, live GitHub API integration, code file statistics, and transparent heuristic findings.

## Features
- Public GitHub URL / `owner/repo` import (read-only)
- File and line counts, extension breakdown, severity breakdown
- Heuristic detection: possible hardcoded credentials, `eval`/`exec`, `shell=True`, debug statements, TODO/FIXME
- Score derived from findings (clearly labeled heuristic; **not** a validated code-quality rating)
- Responsive dashboard, loading/error states, severity filtering
- GitHub API rate limit and partial scan notices
- Docker Compose, API docs, backend unit tests

## Quick start (Docker)
```bash
cp .env.example .env
# Optional: put GITHUB_TOKEN in .env to avoid GitHub unauthenticated API rate limits
docker compose up --build
```
Open **http://localhost:8080**. API docs: **http://localhost:8000/docs**.

## Local development
Requires Python 3.12+ and Node 20+.

Backend:
```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Frontend (second terminal):
```bash
cd frontend
npm install
npm run dev
```
Open **http://localhost:5173**.

## Tests
```bash
cd backend
python -m pytest -q
```

## API
- `GET /api/health`
- `POST /api/analyze` body: `{"repository":"https://github.com/tiangolo/fastapi"}`

## Architecture
```
Browser (React + Vite)
       | POST /api/analyze
FastAPI input validation
       | GitHub REST API (public repositories)
Metadata -> Recursive git tree -> Limited code blobs
       | Pure Python heuristic scanner
JSON metrics + findings -> React dashboard
```

## Scope and security
This is an **MVP**, not an AI-powered LLM reviewer or enterprise security scanner. The project name is a brand; it currently implements deterministic code heuristics only. No database, OAuth, RAG, pull-request review, or real coverage measurement is implemented. No repository code is executed. GitHub hosts are strictly validated and only GitHub API endpoints are requested. Scans are limited to 120 code files and 100 KB per file. Findings can be false positives and must be verified. GitHub API limits apply (especially without `GITHUB_TOKEN`); partial scans are explicitly indicated. Never paste private credentials into the app.

## Next milestones
1. Persist scan history in PostgreSQL with migrations.
2. Add AST parsing via Tree-sitter, language-aware rules, and richer tests.
3. Add background workers, caching, and rate limiting.
4. Add optional AI-assisted explanations with citation to source file/line.
5. Add GitHub Actions CI, test fixtures, and safe deployment hardening.

## Portfolio demo suggestion
Record a 60–90 second walkthrough: import a small public repository, explain findings and limitations, then show tests and API docs. Include a screenshot and deployed link in your GitHub README once hosted.

## License
MIT — see LICENSE.
"# RepoForge-AI-Code-Intelligence" 
"# RepoForge-AI-Code-Intelligence" 
