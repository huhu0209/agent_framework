# Project Research Summary

**Project:** Agent Framework v0.0.6 -- Unified Config/Path Mechanism
**Domain:** CLI-grade configuration hierarchy + module auto-discovery for Python Agent Framework
**Researched:** 2026-06-11
**Confidence:** HIGH

## Executive Summary

This milestone adds a unified configuration and path-discovery system to the Agent Framework, modeled on Claude Code's layered config architecture. The system introduces a `ConfigLoader` that reads and merges settings from four priority layers (global user, project, local override, environment variables), plus a `discover()` function that resolves module directories across two scopes (`~/.agent-framework/` and `.agent-framework/`). The key insight from research: this requires zero new dependencies. Everything is built on Python stdlib (`json`, `pathlib`, `os`) plus Pydantic v2 already in the project. A custom merge function (~12 lines) is needed because pydantic-settings' built-in `deep_merge` replaces arrays instead of union-merging them.

The recommended approach is purely additive: a new `config/` module (5 files, ~325 lines) acts as a leaf dependency that existing modules consume via new `from_loader()` factory methods. No existing constructor signatures change. The 1002 existing tests continue passing without modification. Each existing module (skills, hooks, agents, profiles, MCP, tasks) gains a thin adapter that translates `ConfigLoader` output into the module's existing constructor parameters.

The primary risks are: (1) the merge semantics for nested dicts -- a shallow merge of a partial override can silently destroy sibling fields from lower-priority layers, and (2) module name collisions between global and project scopes -- the existing `SkillRegistry` scans in insertion order and keeps the first match, which is the opposite of the "project overrides global" intent. Both are preventable with targeted tests written before implementation.

## Key Findings

### Recommended Stack

Zero new external dependencies. The entire config system is built from capabilities already available in the project.

**Core technologies:**
- **Pydantic BaseModel** (v2.12.5): Settings schema definition and validation -- already used everywhere, provides type coercion and `model_validate`
- **json stdlib**: Parse settings.json files -- zero dependencies, sufficient for the moderate nesting in config files
- **pathlib stdlib**: Path resolution, directory scanning, glob -- already used in every module that does file discovery
- **os.environ stdlib**: APP_* env var override at highest priority -- consistent with existing backend `BaseSettings(env_prefix='APP_')`
- **aiofiles** (already installed): Available if async file I/O is needed later, but sync `Path.read_text()` is acceptable for startup-time loading

**Critical decision:** Do NOT use `pydantic-settings` `JsonConfigSettingsSource` for the framework-layer ConfigLoader. Verified by running code: `deep_update({'allow': ['a','b']}, {'allow': ['c']})` yields `{'allow': ['c']}` -- it replaces arrays entirely instead of union-merging. Build a custom `_merge_settings()` function instead.

### Expected Features

**Must have (table stakes):**
- ConfigLoader with layered settings.json merge (F1) -- core value proposition, single entry point for entire milestone
- Two-tier directory structure: `~/.agent-framework/` + `.agent-framework/` (F2) -- standard pattern from Claude Code
- `settings.local.json` gitignored override (F3) -- per-machine personal overrides without polluting team config
- Environment variable override with `APP_*` prefix (F4) -- standard 12-factor, already in backend
- Merge engine: scalar override + array union + object shallow merge (F5-F7) -- three strategies covering all field types
- Module `discover()` for 8 module types (F8) -- returns ordered `[global_path, project_path]` for each module
- AGENTS.md instruction chain (F9) -- concatenate global + project + local + parent traversal into system prompt
- Profile-based prompt assembly (F10) -- already implemented, ConfigLoader just provides the path

**Should have (differentiators):**
- Path-scoped rules with glob-based conditional loading (D1) -- reuses existing `SkillRegistry._glob_match` pattern
- `user.md` persona injection (D2) -- simple file read injected into every session
- Auto-detection of project root (D3) -- walk up from CWD until `.agent-framework/` or `.git/` found
- mtime-based hot-reload for settings (D4) -- proven pattern from SkillRegistry
- Validation with file-path error context (D5) -- wrap Pydantic ValidationError with source file location

**Defer (v2+):**
- Deep merge for nested objects -- causes unpredictable behavior, Claude Code does shallow merge only
- YAML/TOML settings format -- JSON is zero-dependency with stdlib
- Managed/enterprise scope -- framework library, not SaaS CLI
- Import syntax (`@path`) in AGENTS.md -- adds parsing complexity for marginal benefit
- Real-time file watching (inotify/fsevents) -- mtime polling is sufficient
- Subdirectory on-demand AGENTS.md loading -- complex lazy-loading, low immediate value

### Architecture Approach

The system follows an adapter pattern. A new `config/` module acts as a centralized configuration and discovery layer that is a leaf dependency -- it imports nothing from other framework modules, and other modules depend on it (not the reverse). Each existing module gains a `from_loader()` class method that accepts a `ConfigLoader` and delegates to the existing constructor. No internal logic changes in any existing module.

**Major components:**
1. **`config/settings.py`** -- Pydantic Settings model with custom merge logic (arrays union, dicts shallow merge, scalars override)
2. **`config/discovery.py`** -- `discover_paths(module_name) -> list[Path]` resolving global + project directories
3. **`config/loader.py`** -- `ConfigLoader` class: the single entry point coordinating settings, discovery, and AGENTS.md loading
4. **`config/agents_md.py`** -- AGENTS.md chain loader with parent directory traversal, stopping at `.git/` boundary

**Integration points (8 modules, all additive):**
- `SkillRegistry.from_loader(loader)` -- already accepts `list[Path]`, trivial adapter
- `HookManager.from_loader(loader)` -- add `load_from_paths()` for multiple JSON files
- `load_agent_configs_from_loader(loader)` -- multi-directory agent scanning with collision warnings
- `AgentProfile.from_loader(loader, name)` -- discover profile across scopes
- `McpManager.from_loader(loader)` -- build config from discovered paths + settings
- `TaskManager` -- default path from discovery
- Backend Settings -- import ConfigLoader defaults as fallback values
- PromptAssembler -- AGENTS.md chain injected as `profile.user_context` (assembler unchanged)

### Critical Pitfalls

1. **Shallow merge destroys nested config** -- A project-level `{"llm": {"base_url": "..."}}` replaces the entire global `llm` object, losing `provider` and `api_key`. Prevention: custom merge function with per-type strategies, tested first before any other code.

2. **Backward compatibility breakage** -- Changing existing constructor signatures breaks 1002 tests and any external consumers. Prevention: purely additive API -- new `from_loader()` methods alongside untouched constructors.

3. **Module name collision silent override reversal** -- `SkillRegistry` keeps first-encountered name, but `discover()` returns `[global, project]` (low-to-high). Global gets scanned first, so project duplicates are silently skipped -- the opposite of "project overrides global." Prevention: reverse scan order or collect-then-resolve strategy for name collisions.

4. **AGENTS.md parent traversal goes past git root** -- Walking from CWD to filesystem root loads home-directory AGENTS.md twice (once in global step, once in traversal). Prevention: stop at `.git/` boundary, deduplicate against global.

5. **Circular imports between ConfigLoader and module registries** -- ConfigLoader importing module types creates circular dependency chains. Prevention: ConfigLoader returns raw `list[Path]` and raw `dict` -- never imports module-specific types. Validation happens in each module's own code.

## Implications for Roadmap

Based on research, the recommended phase structure follows the dependency graph: build the leaf module first, then add adapters from simplest to most complex, finish with the application-layer integration.

### Phase 1: Config Foundation -- Settings Model + Merge Engine
**Rationale:** Pure new code with zero risk of breaking existing tests. Establishes the public API all subsequent phases depend on. The merge function is the highest-risk piece and must be validated first.
**Delivers:** `config/settings.py` with Settings Pydantic model, `_merge_settings()` with type-aware strategies, exhaustive merge tests
**Addresses:** F1 (partial), F5, F6, F7 from FEATURES.md
**Avoids:** Pitfall #1 (shallow merge destroying nested config), Pitfall #10 (schema drift -- all fields optional with defaults)

### Phase 2: Config Foundation -- Discovery + Loader + AGENTS.md
**Rationale:** Builds on the settings model from Phase 1. Discovery and loader are the remaining infrastructure needed before any integration can start. AGENTS.md chain loading is included here because it has no module dependencies.
**Delivers:** `config/discovery.py`, `config/loader.py`, `config/agents_md.py`, `config/__init__.py` -- complete `config/` module
**Uses:** pathlib for path resolution, json for file parsing, Settings model from Phase 1
**Addresses:** F2, F8, F9, D3 from FEATURES.md
**Avoids:** Pitfall #3 (symlink path confusion -- resolve paths at init), Pitfall #4 (AGENTS.md order divergence), Pitfall #12 (parent traversal past git root)

### Phase 3: Simple Module Adapters -- Skills, Hooks, Commands
**Rationale:** These modules already accept `list[Path]` in constructors. The adapter is trivial -- call existing constructor with `loader.discover()` output. Validates the `from_loader()` pattern before applying it to more complex modules.
**Delivers:** `SkillRegistry.from_loader()`, `HookManager.from_loader()`, command dispatcher integration
**Uses:** ConfigLoader.discover() from Phase 2
**Addresses:** Integration for skills, hooks, commands
**Avoids:** Pitfall #2 (backward compat -- additive only), Pitfall #5 (name collision -- test same-name items)

### Phase 4: Complex Module Adapters -- Agents, Profiles, MCP, Tasks
**Rationale:** Multi-directory agent scanning needs collision detection. Profile discovery crosses scopes by name. MCP has the most complex config (per-server settings). Tasks is simplest (default path).
**Delivers:** `load_agent_configs_from_loader()`, `AgentProfile.from_loader()`, `McpManager.from_loader()`, TaskManager default path
**Uses:** ConfigLoader from Phase 2
**Addresses:** Integration for agents, profiles, MCP, tasks
**Avoids:** Pitfall #9 (circular imports -- ConfigLoader returns raw paths), Pitfall #11 (empty config on fresh install)

### Phase 5: Safety + Backend Integration + End-to-End Wiring
**Rationale:** Safety/permissions is fed by profile data, not config directly -- this phase is mostly validation. Backend integration is the application layer. End-to-end wiring connects everything.
**Delivers:** Backend Settings defaults from ConfigLoader, AGENTS.md injection into PromptAssembler, full application startup flow, permissions from Settings-backed profiles
**Uses:** All phases
**Addresses:** F3, F4, F10, backend integration
**Avoids:** Pitfall #8 (async mismatch -- ConfigLoader runs at startup only, not per-request)

### Phase 6: Polish -- Path-Scoped Rules, Validation, Hot-Reload
**Rationale:** Differentiators that add value but are not required for the core config system to function. Can be done in any order.
**Delivers:** Path-scoped rules (D1), validation with file-path context (D5), mtime hot-reload (D4), user.md persona (D2)
**Addresses:** D1, D2, D4, D5 from FEATURES.md
**Avoids:** Pitfall #6 (JSON parse errors -- clear error messages with line numbers), Pitfall #7 (encoding -- enforce UTF-8)

### Phase Ordering Rationale

- Phases 1-2 build the `config/` module in isolation with no existing code changes -- zero risk to 1002 tests
- Phases 3-4 add adapters from simplest to most complex -- validates pattern on easy modules first
- Phase 5 connects everything at the application layer -- done last when all infrastructure is validated
- Phase 6 is optional polish -- can be deferred if time-constrained
- Within each phase, the merge function and name-collision resolution are tested first

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2:** AGENTS.md parent traversal edge cases (git boundary detection, symlinked directories, `.git/` in submodules)
- **Phase 4:** MCP server config merge semantics across scopes -- MCP has the most complex per-server config structure
- **Phase 5:** Backend Settings integration -- how ConfigLoader defaults interact with existing `BaseSettings(env_prefix='APP_')` needs a working proof-of-concept

Phases with standard patterns (skip research-phase):
- **Phase 1:** Merge logic is a pure function with well-defined rules, heavily testable
- **Phase 3:** Trivial adapters on modules that already accept `list[Path]`
- **Phase 6:** Reuses proven patterns from existing code (SkillRegistry mtime refresh, glob matching)

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Zero new deps verified by reading pyproject.toml + running code. Pydantic-settings merge behavior verified locally. |
| Features | HIGH | Claude Code's official documentation provides a clear reference model. Design doc specifies exact behaviors. |
| Architecture | HIGH | Based on direct codebase analysis of all 8 integration points. Every existing constructor signature verified. |
| Pitfalls | HIGH | Top 5 pitfalls sourced from verified code behavior (pydantic-settings Issue #590, SkillRegistry source, CONCERNS.md). |

**Overall confidence:** HIGH

### Gaps to Address

- **Name collision resolution strategy:** The design says "project overrides global" but `SkillRegistry` keeps first-encountered. Need to decide: reverse scan order, collect-then-resolve, or change SkillRegistry internals. Resolve during Phase 3 planning.
- **Backend Settings integration proof-of-concept:** How ConfigLoader defaults feed into `BaseSettings` without creating circular imports between framework and backend packages. A small spike during Phase 5 planning.
- **AGENTS.md ordering semantics for LLM context:** Earlier instructions in the prompt may be weighted differently than later ones. The exact concatenation order affects agent behavior. Needs experimentation during Phase 2 planning.
- **Fresh-install experience:** System must be fully functional with zero config files. Every module must degrade gracefully to built-in defaults. Test explicitly during each phase.

## Sources

### Primary (HIGH confidence)
- Claude Code Settings Documentation (code.claude.com/docs/en/settings) -- scope hierarchy, merge rules, permission behavior
- Claude Code Memory/CLAUDE.md Documentation (code.claude.com/docs/en/memory) -- instruction chain loading, directory traversal
- Pydantic v2 via Context7 (/pydantic/pydantic) -- BaseModel.model_validate, validation patterns
- pydantic-settings via Context7 (/pydantic/pydantic-settings, v2.14.1) -- JsonConfigSettingsSource, deep_merge behavior, env_prefix
- Direct codebase analysis -- all 8 integration point source files, pyproject.toml dependencies, 1002 existing tests
- Design doc (docs/plans/2026-06-11-config-path-mechanism-design.md) -- target specification

### Secondary (MEDIUM confidence)
- pydantic-settings Issue #590 -- confirmed shallow merge behavior in file-based config loading
- Codebase CONCERNS.md -- sync I/O in async context, existing known issues
- Codebase ARCHITECTURE.md, CONVENTIONS.md -- integration patterns, coding standards

### Tertiary (LOW confidence)
- agents.md Issue #135 -- progressive loading proposal (community discussion, not authoritative)

---
*Research completed: 2026-06-11*
*Ready for roadmap: yes*
