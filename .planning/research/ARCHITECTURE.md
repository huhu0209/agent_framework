# Architecture: Unified Config/Path System Integration

**Project:** Agent Framework v0.0.6
**Researched:** 2026-06-11
**Confidence:** HIGH (based on direct codebase analysis of all 8 integration points)

## Executive Summary

The unified config/path system introduces a new `config/` module into the framework core that acts as a centralized configuration and discovery layer. Currently, eight separate modules each manage their own configuration through different mechanisms (constructor parameters, directory scanning, Pydantic BaseSettings, JSON files). The new system does NOT replace these mechanisms -- it wraps them with a single entry point (`ConfigLoader`) that handles layered loading, merging, and path discovery across global (`~/.agent-framework/`) and project (`.agent-framework/`) scopes.

The integration is primarily an **adapter pattern**: each existing module gains a new factory method or constructor path that accepts `ConfigLoader` output, while the old APIs remain functional for backward compatibility. No internal logic changes in any existing module.

## Recommended Architecture

```text
                               ConfigLoader (new)
                                    |
                      +-------------+-------------+
                      |             |             |
                load_settings()  discover()   load_agents_md()
                      |             |             |
                      v             v             v
                Settings obj   list[Path]     str (concatenated)
                      |             |             |
          +-----------+    +--------+--------+   |
          |                |   |    |    |    |   |
          v                v   v    v    v    v   v
    backend Settings   skills agents hooks commands profiles
    (defaults source)  registry config.py manager dispatcher profiles.py
```

### New Module Structure

```text
framework/agent_framework/config/
  __init__.py       # Public API: ConfigLoader, Settings, discover_paths
  loader.py         # ConfigLoader class -- entry point for all config
  settings.py       # Settings Pydantic model (unified schema)
  discovery.py      # discover_paths() -- layered path resolution
  agents_md.py      # AGENTS.md chain loading + concatenation
```

### New Files (5)

| File | Responsibility | Lines (est.) |
|------|---------------|--------------|
| `config/__init__.py` | Barrel exports, `__all__` | ~15 |
| `config/loader.py` | `ConfigLoader` class: `load_settings()`, `discover()`, `load_agents_md()` | ~120 |
| `config/settings.py` | `Settings(BaseModel)` with merge logic for arrays/objects/scalars | ~80 |
| `config/discovery.py` | `discover_paths(module_name) -> list[Path]`, global + project resolution | ~50 |
| `config/agents_md.py` | `load_agents_md_chain() -> str`, file concatenation with parent traversal | ~60 |

### Modified Files (8 integration points)

| File | Change Type | What Changes |
|------|------------|--------------|
| `agents/config.py` | Add factory function | New `load_agent_configs_from_loader(loader)` that calls `loader.discover("agents")` to get path list, then scans each |
| `skills/registry.py` | Add class method | New `SkillRegistry.from_loader(loader)` that calls `loader.discover("skills")` |
| `hooks/manager.py` | Add class method | New `HookManager.from_loader(loader)` that calls `loader.discover("hooks")` for each hooks.json path |
| `prompts/profiles.py` | Add class method | New `AgentProfile.from_loader(loader, name)` that discovers profile via `loader.discover("profiles")` |
| `tools/mcp/config.py` | Add class method | New `McpManager.from_loader(loader)` that loads MCP servers from discovered `mcp/servers.json` |
| `commands/dispatcher.py` | Modify constructor | Accept optional `ConfigLoader` to discover skill/command paths |
| `tasks/manager.py` | Add default path | Constructor `tasks_dir` defaults to `.agent-framework/tasks/` when no path given |
| `backend/app/config/__init__.py` | Add defaults source | Import defaults from `ConfigLoader.load_settings()` as fallback values |

### Unchanged Files (backward compatibility)

All existing public APIs remain functional:
- `load_agent_configs(directory: Path)` -- still works with a single directory
- `SkillRegistry(skills_dirs: list[Path])` -- still works with explicit paths
- `HookManager.load_from_json(path: Path)` -- still works with explicit path
- `AgentProfile.from_directory(path: Path)` -- still works with explicit path
- `McpManager(configs: list[McpServerConfig])` -- still works with explicit configs
- `TaskManager(tasks_dir: Path)` -- still works with explicit path
- `PermissionPipeline(profile, critical_tools)` -- no signature change
- `backend/app/config/Settings(BaseSettings)` -- env var loading unchanged
- `AgentLoop.__init__(...)` -- all constructor params unchanged

## Component Boundaries

| Component | Responsibility | Depends On | Communicates With |
|-----------|---------------|------------|-------------------|
| `config/loader.py` | Entry point; coordinates settings, discovery, AGENTS.md | `config/settings.py`, `config/discovery.py`, `config/agents_md.py` | All modules (via their factory methods) |
| `config/settings.py` | Settings model with merge semantics | `pydantic` only | `config/loader.py`, `backend/app/config/` |
| `config/discovery.py` | Path resolution across global/project scopes | `pathlib` only | `config/loader.py` |
| `config/agents_md.py` | AGENTS.md chain loading and concatenation | `pathlib` only | `config/loader.py` |

**Key boundary rule:** The `config/` module depends on nothing else in the framework. It is a leaf dependency -- other modules depend on it, not the reverse.

## Data Flow

### 1. Settings Loading Flow

```text
Path.home() / ".agent-framework/settings.json"     --+
Path.cwd() / ".agent-framework/settings.json"       --+ merge (config/settings.py)
Path.cwd() / ".agent-framework/settings.local.json" --+
Environment variables (APP_* prefix)                 --+
                                                      |
                                                      v
                                              Settings (Pydantic model)
                                                      |
                                     +----------------+----------------+
                                     |                                 |
                                     v                                 v
                           backend Settings                 Framework internals
                           (defaults populated             (permissions, model,
                            from Settings)                  server config)
```

**Merge semantics (implemented in `config/settings.py`):**

| Field Type | Strategy | Example |
|------------|----------|---------|
| Arrays (`permissions.allow`, `mcp_servers`) | Union -- all layers contribute | `[A,B]` + `[B,C]` = `[A,B,C]` |
| Dicts (`llm`, `server`) | Shallow merge -- higher priority key overrides | `{a:1}` + `{a:2}` = `{a:2}` |
| Scalars (`model`, `log_level`) | Last-write-wins -- highest priority wins | `"gpt-5"` overrides `"sonnet"` |

### 2. Module Discovery Flow

```text
discover_paths("skills")
    |
    +-- Path.home() / ".agent-framework/skills"     -- exists? -- [global_path]
    +-- Path.cwd() / ".agent-framework/skills"       -- exists? -- [project_path]
                                                      |
                                                      v
                                             [global_path, project_path]
                                             (ordered low -> high priority)
                                                      |
                                                      v
                                         SkillRegistry.from_paths([...])
                                         (existing __init__ handles multi-dir)
```

**Name collision resolution by module:**

| Module | Collision Strategy | Rationale |
|--------|-------------------|-----------|
| Skills | Project overrides global | Existing `SkillRegistry` already does this (first-encountered wins; scan global before project) |
| Agents | Project overrides global (warn) | User expects project-level customization to take precedence |
| Hooks | Full merge (union) | All layers contribute hooks; `HookManager` already supports multiple `load_from_json` calls |
| Commands | Project overrides global | Same as skills |
| Rules | Full merge (conditional) | Rules have path matchers; all rules from all layers are evaluated |
| Profiles | Project overrides global | Project-specific agent personas override user defaults |
| Memory | Both paths available | Consumer decides priority; memory is additive by nature |

### 3. AGENTS.md Instruction Chain Flow

```text
load_agents_md()
    |
    +-- ~/.agent-framework/AGENTS.md              (global user instructions)
    +-- .agent-framework/AGENTS.md                (project team instructions)
    +-- .agent-framework/AGENTS.local.md          (personal project instructions)
    +-- Parent directory chain (root -> cwd)      (each directory's AGENTS.md)
    +-- ~/.agent-framework/user.md                (user profile)
    +-- rules/*.md from discover_paths("rules")   (conditional rules)
                                                      |
                                                      v
                                            Concatenated str
                                                      |
                                                      v
                                    Injected as <user-provided> block
                                    via PromptAssembler
```

This integrates with the existing `PromptAssembler.render()` flow. The AGENTS.md chain output becomes `profile.user_context`, which the assembler wraps in `<user-provided>` tags. The assembler already handles this field.

### 4. Integration with Backend Settings

```text
ConfigLoader.load_settings()
        |
        v
    Settings (framework model, plain BaseModel)
        |
        v
    backend/app/config/__init__.py
    class Settings(BaseSettings):
        llm_provider: str = "anthropic"       # default from ConfigLoader
        llm_api_key: SecretStr = ...          # default from ConfigLoader
        llm_model: str = "claude-sonnet-..."  # default from ConfigLoader
        ...
        model_config = {"env_prefix": "APP_", "env_file": ".env"}
```

The backend `Settings(BaseSettings)` retains its `APP_` prefix and env var loading. `ConfigLoader.load_settings()` provides default values that the backend Settings can use as fallback. This is a one-way data flow: framework config feeds backend defaults. The backend's pydantic-settings layer (with `APP_*` env var prefix) remains the highest-priority override.

### 5. End-to-End: Application Startup with ConfigLoader

```text
Application Entry Point (backend/main.py or CLI)
    |
    v
ConfigLoader()                                     # Create loader
    |
    +-- loader.load_settings()                     # -> Settings
    |       |
    |       v
    |   Create LLM adapter from settings.llm
    |
    +-- loader.discover("skills")                  # -> [global_skills, project_skills]
    |       |
    |       v
    |   SkillRegistry.from_loader(loader)          # -> SkillRegistry
    |
    +-- loader.discover("agents")                  # -> [global_agents, project_agents]
    |       |
    |       v
    |   load_agent_configs_from_loader(loader)     # -> dict[str, AgentConfig]
    |
    +-- loader.discover("hooks")                   # -> [global_hooks.json, project_hooks.json]
    |       |
    |       v
    |   HookManager.from_loader(loader)            # -> HookManager
    |
    +-- loader.discover("profiles")                # -> [global_profiles, project_profiles]
    |       |
    |       v
    |   AgentProfile.from_loader(loader, "default") # -> AgentProfile
    |
    +-- loader.load_agents_md()                    # -> str (instruction chain)
    |       |
    |       v
    |   Inject into profile.user_context
    |
    v
Create AgentLoop with all discovered components
```

## Patterns to Follow

### Pattern 1: Factory Method on Existing Classes

**What:** Add `from_loader()` class methods to existing classes that accept a `ConfigLoader` and configure themselves.
**When:** Every module that currently takes explicit paths/config in its constructor.
**Example:**

```python
# In skills/registry.py -- ADD alongside existing __init__, do NOT replace
class SkillRegistry:
    def __init__(self, skills_dirs: list[Path]) -> None:
        # existing code unchanged
        ...

    @classmethod
    def from_loader(cls, loader: "ConfigLoader") -> "SkillRegistry":
        """Create registry from ConfigLoader-discovered paths."""
        from agent_framework.config import ConfigLoader
        paths = loader.discover("skills")
        return cls(skills_dirs=paths)
```

**Why this pattern:** It preserves the existing constructor API (1002 tests use it directly) while adding the new ConfigLoader integration path. The `from_loader` method is a thin adapter that calls the existing constructor.

### Pattern 2: Immutable Settings Model (Plain BaseModel)

**What:** `Settings` as a Pydantic `BaseModel` (not `BaseSettings`) in the framework layer. Environment variable loading stays in the backend.
**When:** Always. Framework must remain environment-agnostic.
**Example:**

```python
# config/settings.py -- framework layer, NO pydantic-settings dependency
from pydantic import BaseModel

class LlmSettings(BaseModel):
    provider: str = "anthropic"
    api_key: str = ""
    base_url: str | None = None

class PermissionSettings(BaseModel):
    allow: list[str] = []
    deny: list[str] = []
    ask: list[str] = []

class Settings(BaseModel):
    model: str = "claude-sonnet-4-6-20250514"
    llm: LlmSettings = LlmSettings()
    server: ServerSettings = ServerSettings()
    permissions: PermissionSettings = PermissionSettings()
```

**Why:** The framework `pyproject.toml` has no `pydantic-settings` dependency. Adding it would be a new dependency for the core package. The backend already has `pydantic-settings` and handles env var loading. Framework provides data models; backend provides environment binding.

### Pattern 3: Type-Aware Layered JSON Merge

**What:** Load multiple JSON files, merge with type-aware strategy per field.
**When:** All `settings.json` and `hooks.json` loading.
**Example:**

```python
def merge_settings(layers: list[dict]) -> dict:
    """Merge settings dicts from lowest to highest priority.

    Arrays: union (extend). Dicts: shallow merge. Scalars: override.
    """
    result: dict = {}
    for layer in layers:
        for key, value in layer.items():
            if isinstance(value, list) and key in result and isinstance(result[key], list):
                result[key].extend(value)
            elif isinstance(value, dict) and key in result and isinstance(result[key], dict):
                result[key] = {**result[key], **value}
            else:
                result[key] = value
    return result
```

### Pattern 4: Lazy Discovery (only existing paths returned)

**What:** `discover_paths()` only returns paths that exist on disk. Callers never need to check existence.
**When:** All module discovery.
**Example:**

```python
def discover_paths(module_name: str, cwd: Path | None = None) -> list[Path]:
    """Return existing paths for a module, ordered low -> high priority."""
    paths = []
    user_dir = Path.home() / ".agent-framework" / module_name
    if user_dir.exists():
        paths.append(user_dir)
    project_dir = (cwd or Path.cwd()) / ".agent-framework" / module_name
    if project_dir.exists():
        paths.append(project_dir)
    return paths
```

### Pattern 5: ConfigLoader as Instance, Not Global

**What:** `ConfigLoader` is instantiated by application code and passed via constructor injection.
**When:** Always.
**Example:**

```python
# Application entry point creates the loader
loader = ConfigLoader(cwd=Path.cwd())

# Pass to components via constructor/factory
skill_registry = SkillRegistry.from_loader(loader)
hook_manager = HookManager.from_loader(loader)
```

**Why:** Matches existing framework patterns. `AgentLoop` receives all dependencies via constructor. No global state, no singletons. Testable by creating `ConfigLoader` with a temp directory.

## Anti-Patterns to Avoid

### Anti-Pattern 1: ConfigLoader as Singleton/Global State

**What:** Making `ConfigLoader` a module-level global or singleton.
**Why bad:** Framework is designed for testability with constructor injection. All 1002 existing tests create components explicitly. Globals make testing harder and violate the established pattern where all state is instance-scoped.
**Instead:** Pass `ConfigLoader` instances via constructor parameters, just like `SkillRegistry` and `HookManager` are passed today.

### Anti-Pattern 2: Config Module Importing Other Framework Modules

**What:** `config/` importing from `skills/`, `hooks/`, `agents/`, etc.
**Why bad:** Creates circular or deep dependency chains. The framework has explicit `TYPE_CHECKING` guards to prevent circular imports already. Adding `config/` as a reverse dependency would compound the problem.
**Instead:** `config/` returns raw data types (`Settings`, `list[Path]`, `str`). Consumers interpret the data. `config/` imports only `pydantic`, `pathlib`, `json`, and `os`.

### Anti-Pattern 3: Replacing Existing APIs

**What:** Changing `load_agent_configs(directory)` to require a `ConfigLoader`.
**Why bad:** Breaks backward compatibility. 1002 tests use the old APIs directly. Every test that creates a `SkillRegistry` passes explicit `list[Path]`.
**Instead:** Add new methods alongside old ones. Old APIs continue to work. New APIs delegate to old ones internally. Old methods are the implementation; new methods are the integration adapter.

### Anti-Pattern 4: Framework Loading Environment Variables

**What:** Using `pydantic-settings` `BaseSettings` with `env_prefix` in the framework layer.
**Why bad:** Framework has no `pydantic-settings` dependency (it lives only in backend). Adding it to the core package would pull in a transitive dependency chain. Environment variable loading is an application-layer concern.
**Instead:** Framework `Settings` uses plain `BaseModel`. Backend wraps it with `BaseSettings` for env var overlay.

### Anti-Pattern 5: Eager Loading at Import Time

**What:** Loading settings.json at module import time (module-level code).
**Why bad:** Fails silently in test environments, CI, or when `.agent-framework/` does not exist. Makes tests non-deterministic. Every import would trigger filesystem I/O.
**Instead:** All loading happens inside `ConfigLoader` methods, triggered explicitly by application code. Importing `from agent_framework.config import ConfigLoader` does zero I/O.

## Build Order (Dependency-Respecting)

The build order ensures each phase can be fully tested independently before the next begins. No phase breaks existing tests.

### Phase 1: Foundation -- `config/` Module (zero dependencies on existing code)

**New files:**
- `config/__init__.py`
- `config/settings.py` -- Settings model + merge logic
- `config/discovery.py` -- `discover_paths()` function
- `config/loader.py` -- `ConfigLoader` class
- `config/agents_md.py` -- AGENTS.md chain loading

**Tests (new):**
- `tests/test_config_settings.py` -- merge semantics (arrays union, dicts shallow, scalars override)
- `tests/test_config_discovery.py` -- path resolution with mocked home/cwd
- `tests/test_config_loader.py` -- end-to-end load_settings() + discover()
- `tests/test_config_agents_md.py` -- file concatenation + parent traversal

**Why first:** Pure new code, zero risk of breaking existing 1002 tests. Establishes the public API that all subsequent phases depend on. Can be developed and validated in complete isolation.

### Phase 2: Low-Risk Adapters -- Skills, Hooks, Commands

**Modified files:**
- `skills/registry.py` -- add `from_loader()` classmethod
- `hooks/manager.py` -- add `from_loader()` classmethod
- `commands/dispatcher.py` -- accept optional `ConfigLoader`

**Tests (extend existing):**
- `tests/test_skills_registry.py` -- add tests for `from_loader()` path
- `tests/test_hook_manager.py` -- add tests for `from_loader()` path

**Why second:** These modules already accept `list[Path]` in their constructors. The adapter is trivial: `cls(skills_dirs=loader.discover("skills"))`. Low risk, validates the factory method pattern before applying it to more complex modules.

### Phase 3: Profile and Agent Config Adapters

**Modified files:**
- `prompts/profiles.py` -- add `from_loader()` classmethod for profile discovery
- `agents/config.py` -- add `load_agent_configs_from_loader()` for multi-path scanning

**Tests (extend existing):**
- `tests/test_agent_profile.py` -- add tests for loader-based discovery
- `tests/test_agents_config.py` -- add tests for multi-directory loading

**Why third:** Depends on `discover("agents")` and `discover("profiles")` working correctly, which is validated in Phase 1. Multi-directory agent scanning is slightly more complex because it needs collision detection (warn on duplicate names).

### Phase 4: MCP and Tasks Integration

**Modified files:**
- `tools/mcp/config.py` -- add `from_loader()` for MCP server discovery
- `tasks/manager.py` -- default `tasks_dir` to `.agent-framework/tasks/`

**Tests (extend existing):**
- `tests/test_mcp_manager.py` -- add tests for loader-based config
- `tests/test_task_manager.py` -- add tests for default path behavior

**Why fourth:** MCP has the most complex config (per-server settings, env var validation, sensitive key rejection). Tasks integration is simpler (just a default path change).

### Phase 5: Safety/Permissions Integration

**Modified files:**
- `safety/permissions.py` -- no code change to the class itself. `PermissionPipeline` gets richer `allowed_tools`/`disallowed_tools` from Settings-backed profiles.

**Tests (extend existing):**
- `tests/test_permissions.py` -- verify permissions from Settings-derived profiles

**Why fifth:** Permissions already gets tool lists from `AgentProfile`. The change is upstream (how profiles are populated from Settings), not in `PermissionPipeline` itself. This phase is validation-only.

### Phase 6: Backend Integration + AGENTS.md Chain

**Modified files:**
- `backend/app/config/__init__.py` -- import defaults from `ConfigLoader.load_settings()`
- `agents/agent_loop.py` -- integrate AGENTS.md chain into system prompt assembly (via profile.user_context)

**Tests (extend existing + new):**
- `backend/tests/test_config_integration.py` -- verify backend Settings uses ConfigLoader defaults
- `tests/test_agent_loop.py` -- add tests for AGENTS.md chain injection into system prompt

**Why last:** Backend is the application layer. AGENTS.md integration touches `AgentLoop` which is the most complex file (406 lines) and the heart of the system. Do this last when all supporting infrastructure is validated.

## Dependency Graph

```text
config/settings.py ----------------------------------+
config/discovery.py ---------------------------------+
config/agents_md.py ---------------------------------+
                                                     |
config/loader.py -- (imports settings,              <+ 
                      discovery, agents_md)
       |
       |  (used by -- factory methods)
       v
+------+------------+-------------+-----------+
|       |           |             |           |
v       v           v             v           v
agents/   skills/     hooks/      commands/   prompts/
config.py  registry.py manager.py  dispatcher.py profiles.py
       |           |             |           |
       |           v             v           |
       |       CommandDispatcher             |
       |                                       |
       +-------+-------------------------------+
               |
               v
       agents/agent_loop.py  (consumes profile + skills + hooks)
               |
               v
       backend/app/config/  (application layer)
```

No circular dependencies. `config/` is a clean leaf module that nothing else in the framework imports from except the adapter layer.

## Scalability Considerations

| Concern | At 1 config dir | At 10 config dirs | At 100 config dirs |
|---------|-----------------|-------------------|---------------------|
| Settings merge | Single dict, instant | 10 dicts shallow-merged, instant | 100 dicts merged, still instant |
| Path discovery | 2 stat() calls (home + cwd) | 2 stat() calls (unchanged) | 2 stat() calls (unchanged) |
| AGENTS.md loading | 6-8 file reads | 6-8 file reads + parent chain | 6-8 reads + deeper parent chain |
| Skill scanning | rglob on 1-2 dirs | rglob on 1-2 dirs (discovery is scoped) | rglob on 1-2 dirs (unchanged) |

Performance is not a concern. All operations are bounded I/O (stat, read, glob) on at most 2 directory trees. The merge logic is pure dict operations. No hot-path impact on the ReAct loop.

## Backward Compatibility Verification

| Existing API | Status | How Compatible |
|-------------|--------|----------------|
| `SkillRegistry(skills_dirs: list[Path])` | UNCHANGED | Constructor still accepts explicit paths |
| `HookManager(trusted: bool)` + `load_from_json(path)` | UNCHANGED | JSON loading still works |
| `load_agent_configs(directory: Path)` | UNCHANGED | Single-directory scanning still works |
| `AgentProfile.from_directory(path: Path)` | UNCHANGED | Directory-based loading still works |
| `McpManager(configs: list[McpServerConfig])` | UNCHANGED | Explicit config list still works |
| `TaskManager(tasks_dir: Path)` | UNCHANGED | Explicit path still works |
| `PermissionPipeline(profile, critical_tools)` | UNCHANGED | No signature change |
| `backend/app/config/Settings(BaseSettings)` | UNCHANGED | Env var loading unchanged, gains optional defaults |
| `AgentLoop.__init__(...)` | UNCHANGED | All 20+ constructor params unchanged; ConfigLoader used upstream |

Net new APIs only. Zero breaking changes. All 1002 existing tests continue passing without modification.

## New Dependency Analysis

| Dependency | Already in framework? | Action |
|------------|----------------------|--------|
| `pydantic` (for Settings model) | YES (v2+) | Use existing |
| `pathlib` (for path handling) | YES (stdlib) | Use existing |
| `json` (for settings.json parsing) | YES (stdlib) | Use existing |
| `os` (for Path.home()) | YES (stdlib) | Use existing |
| `pydantic-settings` | NO (backend only) | Do NOT add to framework |
| `toml` / `yaml` | NO | Do NOT add (design uses JSON) |

Zero new external dependencies for the framework package. This is a key advantage of using JSON for settings (stdlib `json` module) rather than YAML or TOML.

## File Structure After v0.0.6

```text
framework/agent_framework/
+-- config/                   # NEW MODULE
|   +-- __init__.py           # NEW: barrel exports
|   +-- loader.py             # NEW: ConfigLoader class
|   +-- settings.py           # NEW: Settings + merge logic
|   +-- discovery.py          # NEW: discover_paths()
|   +-- agents_md.py          # NEW: AGENTS.md chain loading
+-- agents/
|   +-- config.py             # MODIFIED: add load_agent_configs_from_loader()
|   +-- agent_loop.py         # UNCHANGED (AGENTS.md consumed via profile.user_context)
|   +-- ...
+-- skills/
|   +-- registry.py           # MODIFIED: add SkillRegistry.from_loader()
|   +-- ...
+-- hooks/
|   +-- manager.py            # MODIFIED: add HookManager.from_loader()
|   +-- ...
+-- prompts/
|   +-- profiles.py           # MODIFIED: add AgentProfile.from_loader()
|   +-- assembler.py          # UNCHANGED
|   +-- ...
+-- tools/mcp/
|   +-- config.py             # MODIFIED: add McpManager.from_loader()
|   +-- ...
+-- commands/
|   +-- dispatcher.py         # MODIFIED: accept optional ConfigLoader
|   +-- ...
+-- tasks/
|   +-- manager.py            # MODIFIED: default tasks_dir
|   +-- ...
+-- safety/
|   +-- permissions.py        # UNCHANGED (fed by profile, not config directly)
|   +-- ...
... (all other modules UNCHANGED)

backend/app/config/
+-- __init__.py               # MODIFIED: import defaults from ConfigLoader
```

New files: 5
Modified files: 8
Unchanged files: ~60

## Sources

- Direct codebase analysis of all 8 integration point source files
- Design document: `docs/plans/2026-06-11-config-path-mechanism-design.md`
- Existing architecture: `.planning/codebase/ARCHITECTURE.md`
- Dependency structure: `.planning/codebase/INTEGRATIONS.md`
- Coding conventions: `.planning/codebase/CONVENTIONS.md`
- File structure: `.planning/codebase/STRUCTURE.md`
- Framework dependencies: `framework/pyproject.toml`, `backend/pyproject.toml`
