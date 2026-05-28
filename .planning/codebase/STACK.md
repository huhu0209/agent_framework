# Technology Stack

**Analysis Date:** 2026-05-28

## Languages

**Primary:**
- Python 3.11 — Framework core (`framework/agent_framework/`) and backend (`backend/`)

**Secondary:**
- TypeScript ~6.0 — Frontend (`frontend/src/`)
- TypeScript is compiled with `tsc -b` and bundled via Vite 8

## Runtime

**Environment:**
- Python 3.11.14 (enforced via `requires-python = ">=3.11"` in both `framework/pyproject.toml` and `backend/pyproject.toml`)
- Node.js v22.22.0 (frontend dev/build)

**Package Manager:**
- Python: `uv` 0.9.24 — manages virtual environments and pip-installable packages
  - `framework/pyproject.toml` defines the core package `agent-framework-core`
  - `backend/pyproject.toml` depends on local framework via `tool.uv.sources` path reference
- Frontend: npm 10.9.4
  - Lockfile: `frontend/package-lock.json` (present)

## Frameworks

**Core (Python):**
- Pydantic >=2.0.0 — All data models: `framework/agent_framework/llm/types.py`, `framework/agent_framework/tools/mcp/config.py`, `framework/agent_framework/teams/types.py`, etc.
- httpx >=0.27.0 — Async HTTP client for all LLM provider communication (`framework/agent_framework/llm/providers/`)

**Backend (Python):**
- FastAPI >=0.115.0 — Application HTTP layer (`backend/app/api/`)
- Uvicorn >=0.34.0 — ASGI server

**Frontend:**
- React 19.2.6 — UI library (`frontend/package.json`)
- React DOM 19.2.6
- Vite 8.0.12 — Build tool and dev server (`frontend/vite.config.ts`)
- Tailwind CSS 4.3.0 — Utility-first CSS (via `@tailwindcss/vite` plugin)
- TypeScript ~6.0.2 — Type checking

**Testing (Python):**
- pytest >=8.0.0 — Test runner
- pytest-asyncio >=0.24.0 — Async test support (`asyncio_mode = "auto"`)
- 59 test files in `framework/tests/`

**Frontend Dev Tools:**
- ESLint 10.3.0 + typescript-eslint 8.59.2 — Linting
- `@vitejs/plugin-react` 6.0.1 — Vite React plugin

## Key Dependencies

**Critical (Python):**
- `pydantic` >=2.0.0 — Foundation for all type definitions; used extensively in LLM types, tool definitions, team messages, memory types, MCP config
- `httpx` >=0.27.0 — Async HTTP client; sole HTTP transport for LLM providers; supports streaming via `httpx.AsyncClient.stream()`

**Critical (Frontend):**
- `react` ^19.2.6 — UI framework
- `tailwindcss` ^4.3.0 — Styling

**Infrastructure (Python stdlib):**
- `asyncio` — Core async runtime; used throughout for agent loops, streaming, MCP transport, tool execution
- `json` — JSON-RPC protocol for MCP, JSONL file inbox for teams
- `pathlib` — File-based storage (memory logs, team inboxes)

## Configuration

**Python (pyproject.toml):**
- `framework/pyproject.toml` — Core framework package (`agent-framework-core` v0.1.0)
- `backend/pyproject.toml` — Application package (`agent-framework-app` v0.1.0), depends on local framework via path
- `tool.pytest.ini_options.asyncio_mode = "auto"` — All async tests auto-detected
- `tool.pytest.ini_options.pythonpath = ["tests"]` — Test imports resolve correctly

**Frontend:**
- `frontend/vite.config.ts` — Vite config with React + Tailwind plugins
- `frontend/tsconfig.json` — Project references (app + node configs)
- `frontend/tsconfig.app.json` — ES2023 target, bundler module resolution, React JSX
- `frontend/tsconfig.node.json` — Node-specific TS config for tooling

**Environment Variables (existence only, not read):**
- `ANTHROPIC_API_KEY` — Required by `AnthropicProvider`
- `OPENAI_API_KEY` — Required by `OpenAIProvider`
- `DEEPSEEK_API_KEY` — Required by `DeepSeekProvider`
- MCP server env vars — Passed through `McpServerConfig.env` dict

## Platform Requirements

**Development:**
- Python >=3.11 with `uv` package manager
- Node.js v22+ with npm for frontend
- LLM provider API keys (at least one of Anthropic/OpenAI/DeepSeek)

**Production:**
- Python ASGI runtime (Uvicorn) for backend
- Static file serving for frontend build output (`frontend/dist/`)
- Filesystem access for memory store (JSONL logs, semantic markdown files)
- Network access to LLM provider APIs and MCP server processes

## Build & Run Commands

```bash
# Framework (install with test deps)
cd framework && uv pip install -e ".[test]"

# Framework tests
cd framework && pytest tests/ -v

# Backend (installs framework as local dep)
cd backend && uv pip install -e ".[test]"

# Frontend dev
cd frontend && npm run dev

# Frontend build (runs tsc type check + vite build)
cd frontend && npm run build

# Frontend lint
cd frontend && npm run lint
```

---

*Stack analysis: 2026-05-28*
