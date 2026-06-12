# Technology Stack: Unified Config/Path System

**Project:** Agent Framework v0.0.6
**Researched:** 2026-06-11
**Confidence:** HIGH

## Summary

The unified config/path system needs **zero new external dependencies**. All required capabilities are available from Python stdlib (`json`, `pathlib`) plus the two libraries already in the project: `pydantic >=2.0` and `pydantic-settings >=2.0` (both already installed -- pydantic 2.12.5 and pydantic-settings 2.14.1 confirmed).

The key technical decision: **do NOT use pydantic-settings' `JsonConfigSettingsSource` for the full config hierarchy.** While it supports multiple JSON files and a `deep_merge` flag, its merge semantics are wrong for this use case -- it replaces arrays entirely instead of union-merging them, and it merges at the flat field level rather than supporting per-field merge strategies (array union vs object shallow merge vs scalar override). Instead, build a custom `ConfigLoader` that reads and merges JSON files manually with the correct merge rules, then feeds the merged result into a plain Pydantic `BaseModel` for validation.

## Recommended Stack

### Settings Validation (existing)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `pydantic` BaseModel | >=2.0 (installed: 2.12.5) | Settings schema definition and validation | Already in framework. Used everywhere (AgentProfile, PromptBlock, LLM types). Provides type coercion, validation, `model_validate` for dict-to-model. |

### Settings Loading (existing libs, custom merge code)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `pydantic-settings` BaseSettings | >=2.0 (installed: 2.14.1) | Backend `Settings` class -- env var loading with `APP_` prefix | Already in backend (`backend/app/config/__init__.py`). `env_nested_delimiter='__'` supports nested field override (confirmed: `APP_LLM__PROVIDER` overrides `settings.llm.provider`). |
| `pydantic-settings` JsonConfigSettingsSource | 2.14.1 | **NOT USED** for framework ConfigLoader | Has `deep_merge=True` but uses `pydantic._internal._utils.deep_update` which replaces arrays entirely. The design requires 3 merge strategies per field type. `JsonConfigSettingsSource` only supports flat override or deep dict merge. |

### Config File Parsing (stdlib)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `json` (stdlib) | Python 3.11+ | Parse settings.json files | Design doc chose JSON over YAML/TOML. Zero dependencies. `json.load` sufficient for the moderate nesting in settings.json. |
| `pathlib.Path` (stdlib) | Python 3.11+ | Path resolution, directory scanning | Already used everywhere (`agents/config.py`, `prompts/profiles.py`, `hooks/manager.py`, `skills/registry.py`). `Path.home()`, `Path.cwd()`, `glob()`, `rglob()`, `is_file()`, `read_text()` cover all discovery needs. |
| `os.environ` (stdlib) | Python 3.11+ | `APP_*` env var override (highest priority) | Already used by pydantic-settings `BaseSettings` with `env_prefix='APP_'`. For framework ConfigLoader, read directly with `os.environ.get()`. |

### File Content Reading (existing)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `aiofiles` | >=24.1.0 (installed) | Async file I/O (if needed later) | Already a dependency. Config loading happens once at startup on small files, so sync `Path.read_text()` is acceptable. Start sync, add async wrapper later if needed. |

### Module Discovery (custom code, stdlib only)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `pathlib.Path.glob` / `rglob` | stdlib | Scan directories for `.md`, `.json` files | Already the pattern used by `load_agent_configs()` (`directory.glob("*.md")`), `SkillRegistry._scan_dir()` (`root.rglob("SKILL.md")`), and `HookManager.load_from_json()`. |

## What NOT to Add

| Library | Why Avoid | What to Do Instead |
|---------|-----------|-------------------|
| `pydantic-settings` JsonConfigSettingsSource for framework Settings | Wrong merge semantics for arrays (replaces, does not union). Cannot express per-field merge strategies. Would fight the design rather than help it. | Custom `ConfigLoader._merge_settings()` with explicit per-type merge logic (~12 lines). |
| `python-dotenv` | `pydantic-settings` already handles `.env` files natively. | Keep `pydantic-settings` `env_file='.env'` in backend Settings. |
| `watchdog` / file watchers | Config files change rarely. Mtime-based refresh (already in SkillRegistry) is sufficient. | Reuse the `SkillRegistry._maybe_refresh()` mtime-check pattern. |
| `jsonschema` (standalone) | Pydantic v2 already validates structure. Adding a separate JSON Schema validator is redundant. | Pydantic `BaseModel.model_validate()` validates the merged dict. |
| `dynaconf` / `python-box` / `hydra-omegaconf` | Heavyweight config frameworks adding significant dependency surface for marginal benefit. The design is specific enough that a ~100-line ConfigLoader is cleaner. | Custom ConfigLoader, no new deps. |
| `anyconfig` | General-purpose config merging library. Overkill for 4 JSON files with 3 merge rules. | Custom `_merge_settings()` function. |
| `tomllib` / TOML support | Design doc explicitly chose JSON. TOML adds complexity for no benefit. | JSON only, per design decision. |
| `pyyaml` | Frontmatter parser already exists in `memory/frontmatter.py` (flat key:value, no pyyaml dep). Agent `.md` files use the same pattern. | Reuse existing `parse_frontmatter()`. |

## Architecture: How the Pieces Fit

```
ConfigLoader (new: framework/agent_framework/config/)
    |
    |-- _merge_settings(low, high) -> dict   # Custom: arrays union, dicts shallow, scalars override
    |
    |-- load_settings() -> Settings          # Read 4 JSON files, merge, validate with Pydantic
    |       |
    |       |-- ~/.agent-framework/settings.json      (lowest priority)
    |       |-- .agent-framework/settings.json
    |       |-- .agent-framework/settings.local.json
    |       |-- os.environ[APP_*]                     (highest priority)
    |
    |-- discover(module_name) -> list[Path]  # Return [global_dir, project_dir]
    |
    |-- load_agents_md() -> str              # Concatenate AGENTS.md chain
```

### Integration with Existing Code

| Existing Module | Current Pattern | Integration Point |
|-----------------|----------------|-------------------|
| `backend/app/config/__init__.py` Settings | `pydantic_settings.BaseSettings` with `env_prefix='APP_'` | Keep as-is for backend. ConfigLoader provides default values; Settings still handles env var override. No change needed. |
| `agents/config.py` `load_agent_configs()` | Takes single `Path`, scans `*.md` | Accept `list[Path]` from `discover("agents")`, merge results (project overrides global). |
| `skills/registry.py` `SkillRegistry` | Takes `list[Path]` in constructor, already does multi-directory scan | Already compatible. Feed `discover("skills")` directly. |
| `hooks/manager.py` `HookManager.load_from_json()` | Takes single `Path`, loads hooks.json | Add `load_from_paths(paths: list[Path])` that merges hook configs from multiple JSON files. |
| `prompts/profiles.py` `AgentProfile.from_directory()` | Takes single `Path`, reads soul.md etc. | Call with path from `discover("profiles")`. Profile lookup by name across directories. |
| `prompts/assembler.py` `PromptAssembler` | Takes `AgentProfile`, renders system prompt | No change needed. AGENTS.md chain feeds into `profile.user_context`. |
| `memory/frontmatter.py` `parse_frontmatter()` | Custom flat YAML parser (no pyyaml dep) | No change. Used for agent `.md` files. |

### Settings Pydantic Model (new)

```python
# framework/agent_framework/config/settings.py
from pydantic import BaseModel, SecretStr

class LlmSettings(BaseModel):
    provider: str = "anthropic"
    api_key: SecretStr = SecretStr("")
    base_url: str | None = None

class ServerSettings(BaseModel):
    host: str = "0.0.0.0"
    port: int = 30002
    cors_origins: list[str] = ["http://localhost:30001"]

class LoggingSettings(BaseModel):
    level: str = "info"

class PermissionsSettings(BaseModel):
    allow: list[str] = []
    deny: list[str] = []
    ask: list[str] = []

class Settings(BaseModel):
    model: str = "claude-sonnet-4-6-20250514"
    llm: LlmSettings = LlmSettings()
    server: ServerSettings = ServerSettings()
    logging: LoggingSettings = LoggingSettings()
    permissions: PermissionsSettings = PermissionsSettings()
```

Key: Use plain `BaseModel` (not `BaseSettings`) for the framework-layer Settings model. The framework does not read env vars directly -- that is the backend's job via `pydantic-settings`. The framework ConfigLoader merges JSON files, then the backend's `BaseSettings` class can use `ConfigLoader.load_settings()` as its default values source.

### Merge Function (core logic, ~12 lines)

```python
def _merge_settings(base: dict, override: dict) -> dict:
    """Merge override into base with per-type strategies.

    - list: union (combine, deduplicate by position)
    - dict: shallow merge (override keys)
    - scalar: override
    """
    result = {**base}
    for key, value in override.items():
        if key not in result:
            result[key] = value
        elif isinstance(value, dict) and isinstance(result[key], dict):
            result[key] = {**result[key], **value}  # shallow merge
        elif isinstance(value, list) and isinstance(result[key], list):
            result[key] = list(dict.fromkeys(result[key] + value))  # union, preserve order
        else:
            result[key] = value  # scalar override
    return result
```

No library needed. The `dict.fromkeys()` trick preserves insertion order while deduplicating (Python 3.7+ dicts are ordered).

### Environment Variable Override

The ConfigLoader reads `APP_*` environment variables and applies them as the highest-priority layer:

```python
def _env_overrides() -> dict:
    """Collect APP_* env vars, strip prefix, convert to nested dict."""
    result = {}
    for key, value in os.environ.items():
        if key.startswith("APP_"):
            path = key[4:].lower().split("__")  # APP_LLM__PROVIDER -> ["llm", "provider"]
            _deep_set(result, path, value)
    return result
```

This keeps the `APP_` prefix convention consistent with the existing backend Settings class.

## Dependency Summary

**New dependencies: ZERO**

| Category | Before v0.0.6 | After v0.0.6 |
|----------|--------------|--------------|
| Framework dependencies | pydantic, httpx, tavily-python, websockets, aiofiles | **No change** |
| Backend dependencies | fastapi, uvicorn, pydantic-settings, redis, aiofiles | **No change** |
| New files | -- | `framework/agent_framework/config/` (4 files: `__init__.py`, `loader.py`, `settings.py`, `discovery.py`) |

## Key Technical Findings

### 1. pydantic-settings `deep_merge` does NOT support array union

**Verified by running code locally.** `pydantic._internal._utils.deep_update` replaces arrays entirely:
```python
deep_update({'allow': ['a', 'b']}, {'allow': ['c']})
# Result: {'allow': ['c']}  -- NOT ['a', 'b', 'c']
```
This is why we need a custom merge function. The design requires array union for fields like `permissions.allow`.

### 2. pydantic-settings `JsonConfigSettingsSource` accepts `json_file` as a list

**Verified via Context7** (`/pydantic/pydantic-settings`, v2.14.1). `JsonConfigSettingsSource(settings_cls, json_file=['a.json', 'b.json'])` loads multiple files. Later files override earlier ones. With `deep_merge=True`, it uses `deep_update` for nested dicts. Still wrong for arrays. Use custom code.

### 3. Nested env var override works with `env_nested_delimiter`

**Verified by running code locally.** `Settings` with `env_nested_delimiter='__'` correctly maps `APP_LLM__PROVIDER=openai` to `settings.llm.provider = "openai"`. Already how the backend works.

### 4. SkillRegistry already accepts `list[Path]`

**Verified by reading source.** `SkillRegistry.__init__(self, skills_dirs: list[Path])` already handles multiple directories with priority (first match wins). Directly compatible with `discover("skills")` returning `[global_dir, project_dir]`.

### 5. Frontmatter parser is custom, no pyyaml dependency

**Verified by reading source.** `memory/frontmatter.py` has its own flat YAML parser. The design uses the same pattern for agent `.md` files.

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Settings merge | Custom `_merge_settings()` | `pydantic-settings` `JsonConfigSettingsSource(deep_merge=True)` | Wrong array semantics (replaces vs union). Cannot express per-field strategies. |
| Settings merge | Custom `_merge_settings()` | `anyconfig` library | Overkill for 4 files. Adds external dependency for trivial logic. |
| Settings schema | Pydantic `BaseModel` | `pydantic-settings` `BaseSettings` in framework | Framework should not read env vars directly. Backend handles env vars. Framework provides merged defaults. |
| File watching | Mtime-based refresh | `watchdog` library | Config changes are rare. Mtime check (already proven in SkillRegistry) is sufficient. |

## Sources

- Pydantic v2 `BaseModel.model_validate()`: Verified via Context7 (`/pydantic/pydantic`)
- pydantic-settings `JsonConfigSettingsSource` with `deep_merge` parameter: Verified via Context7 (`/pydantic/pydantic-settings`, v2.14.1)
- pydantic-settings `settings_customise_sources` source ordering: Verified via Context7
- `pydantic._internal._utils.deep_update` array replacement behavior: Verified by running code locally
- `env_nested_delimiter='__'` nested env var override: Verified by running code locally
- Existing codebase patterns (`agents/config.py`, `skills/registry.py`, `hooks/manager.py`, `prompts/profiles.py`, `backend/app/config/__init__.py`): Read from local files
- Design doc (`docs/plans/2026-06-11-config-path-mechanism-design.md`): Read from local file
