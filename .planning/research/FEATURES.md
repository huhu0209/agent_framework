# Feature Landscape: Unified Config/Path Mechanism (v0.0.6)

**Domain:** CLI-grade configuration hierarchy + module auto-discovery for Python Agent Framework
**Researched:** 2026-06-11

## Reference System Analysis

Claude Code's configuration system establishes the definitive pattern for this domain. Key behaviors verified from official documentation:

1. **Scope hierarchy** (low to high): User (`~/.claude/`) -> Project (`.claude/`) -> Local (`.claude/settings.local.json`) -> CLI flags -> Managed (enterprise). Our framework skips managed/enterprise as it is a library, not a SaaS CLI.
2. **CLAUDE.md loading**: Walks up directory tree from CWD to root, concatenating all discovered files. No override -- everything is additive. Local variant appended after base at each level.
3. **Settings merge rules**: Scalars override (higher wins), arrays concatenate (union across all scopes), objects shallow-merge (higher keys overwrite lower). Deep merge is intentionally absent.
4. **Module discovery**: Subagents, skills, hooks, MCP servers each discovered independently from their respective subdirectories at user and project scope. Same-name items from project override user level.
5. **Path-scoped rules**: Rules in `.claude/rules/*.md` can conditionally load based on glob patterns matching active file paths. Unconditional rules always load.
6. **Settings file watching**: Claude Code watches settings files and reloads on change. Some keys (model) require restart; most apply immediately.

This project mirrors these patterns but adapts them: `AGENTS.md` instead of `CLAUDE.md`, 8 module types instead of 4, and the framework is a library (not a CLI), so the entry point is Python API rather than a binary invocation.

## Table Stakes

Features users expect. Missing = the config system feels incomplete or unusable.

| # | Feature | Why Expected | Complexity | Depends On (existing) | Notes |
|---|---------|--------------|------------|----------------------|-------|
| F1 | ConfigLoader with layered settings.json | Core value proposition. Without it, configs remain scattered across 10+ locations. | Medium | Pydantic v2, json stdlib | Loads global -> project -> local -> env. Merges by rule type (scalar/array/object). Single entry point for entire milestone. |
| F2 | Two-tier directory structure (`~/.agent-framework/` + `.agent-framework/`) | Standard pattern from Claude Code. Every similar tool uses user/project split. | Low | pathlib | User dir is personal + cross-project. Project dir is team-shared + committed. Path.home() and CWD resolution. |
| F3 | `settings.local.json` (gitignored personal override) | Developers need per-machine overrides without polluting team config. | Low | ConfigLoader | Highest file-based priority. Auto-gitignored. Claude Code does the same. |
| F4 | Environment variable override (`APP_*` prefix) | Standard 12-factor pattern. Existing `backend/app/config/` already uses `BaseSettings(env_prefix="APP_")`. | Low | pydantic-settings | Must not break existing `.env` + BaseSettings. ConfigLoader reads settings.json as defaults; env vars override via BaseSettings. |
| F5 | Merge engine: scalar override | Simplest merge rule. Higher-priority scalar wins. | Low | None | For `model`, `log_level`, etc. Trivial `{**lower, **higher}` for scalars. |
| F6 | Merge engine: array union | Required for `permissions.allow`, `permissions.deny`, MCP servers. All scopes contribute. | Low | None | Concatenate + deduplicate. Claude Code does exactly this. |
| F7 | Merge engine: object shallow merge | Required for `llm`, `server` dicts. Higher-priority keys overwrite specific keys within the object. | Low | None | One level of `{**lower, **higher}`. No deep merge. |
| F8 | Module `discover()` for 8 module types | The whole point of the discovery system. Each module needs path resolution from both scopes. | Medium | pathlib | Returns `[global_path, project_path]` ordered low-to-high. SkillRegistry already accepts `list[Path]`; others need thin adapters. |
| F9 | AGENTS.md instruction chain (framework layer) | Analogous to CLAUDE.md. Concatenate global + project + local + parent traversal. | Medium | pathlib, PromptAssembler | Must integrate with existing PromptAssembler's `<user-provided>` block. Parent directory traversal walks CWD to root. |
| F10 | Profile-based prompt assembly (agent layer) | Agent soul/instructions/identity from `profiles/<name>/` directory. | Low | `AgentProfile.from_directory` | Already implemented in `prompts/profiles.py`. ConfigLoader provides the path; no code change needed in profile loader. |

## Differentiators

Features that set the product apart from a naive config-ini approach. Not strictly expected, but highly valued.

| # | Feature | Value Proposition | Complexity | Depends On (existing) | Notes |
|---|---------|-------------------|------------|----------------------|-------|
| D1 | Path-scoped rules (`rules/*.md` with `paths:` frontmatter) | Rules only load when relevant files are active. Saves context window, reduces noise. | Medium | `SkillRegistry._glob_match`, `SkillRegistry.activate_for_paths` | SkillRegistry already has glob-based activation. Reuse the same engine for rules. High value for large projects. |
| D2 | `user.md` persona injection | Personal user profile loaded into every session. Claude Code has no direct equivalent. | Low | AGENTS.md chain | Simple file read from `~/.agent-framework/user.md`. Injected into `<user-provided>` block. |
| D3 | Auto-detection of project root | Walk up from CWD until `.agent-framework/` or `.git/` found. No manual configuration. | Low | pathlib | Common CLI pattern (git, npm, cargo). Prevents running from wrong directory. |
| D4 | Hot-reload on settings change (mtime-based) | Edit settings.json without restarting. | Medium | `SkillRegistry._maybe_refresh` pattern | SkillRegistry already has mtime-based refresh. Generalize the same pattern. Poll on access, not file-watch. |
| D5 | Validation with file-path error context | Invalid JSON or schema violations reported with exact file path + field name. | Medium | Pydantic v2 ValidationError | Claude Code rejects entire invalid files. Wrap Pydantic errors with file path context for clear diagnostics. |

## Anti-Features

Features to explicitly NOT build.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Deep merge for nested objects | Causes unpredictable behavior. Users cannot tell which nested key wins. Claude Code does shallow merge only. Design doc explicitly chose shallow merge. | Shallow merge only. If user needs nested control, they set the full object at higher priority level. |
| YAML or TOML settings format | Adds dependency (pyyaml/toml). Design doc explicitly chose JSON for zero-dependency parsing with `json` stdlib. | JSON only. Matches Claude Code. Python stdlib `json` is sufficient. |
| Managed/enterprise scope | This is a framework library, not a SaaS CLI. No MDM, no server-managed settings, no admin policy enforcement. | Two scopes only: user (`~`) and project (`./`). If enterprise needs arise later, add as a separate milestone. |
| Plugin marketplace system | Far out of scope. Claude Code's plugin system is massive (marketplaces, sources, installation, auto-update). | Skills and agents from directories only. No marketplace, no registry, no remote fetching. |
| Real-time file watching (inotify/fsevents) | Adds OS-specific complexity, platform dependencies, edge cases. | mtime polling on access (like existing SkillRegistry pattern). Good enough for a framework. |
| `$schema` enforcement or auto-download | Requires network access at config load time. Adds coupling to external schema store. | Optional `$schema` field for editor autocomplete only. No enforcement at framework level. |
| Import syntax (`@path`) in AGENTS.md | Claude Code supports `@path/to/import` in CLAUDE.md. Adds parsing complexity with marginal benefit for a framework. | Simple concatenation only. Users who want includes can use symlinks or write content directly. |
| Custom settings.json path via CLI flag | Premature for a library. Applications using this framework can add their own CLI parsing. | Fixed paths only (`~/.agent-framework/settings.json` and `.agent-framework/settings.json`). |
| Subdirectory on-demand AGENTS.md loading | Claude Code loads subdirectory CLAUDE.md lazily when reading files in those dirs. Complex lazy-loading behavior. | Load AGENTS.md chain at startup only (global + project + local + parent walk). No on-demand loading. |
| Settings migration tooling | Auto-migrating old config formats to new is brittle and rarely correct. | Document the new paths clearly. Users move configs manually. Backward compat via existing APIs. |

## Feature Dependencies

```
F2: Two-tier directory structure (foundational, no deps)
  |
  +-- F8: discover_paths() module discovery
  |     |-- Depends on: F2
  |     |-- Depends on: D3 (project root auto-detection)
  |
  +-- F1: ConfigLoader
  |     |-- Depends on: F2
  |     |-- Depends on: F5 + F6 + F7 (merge engine, no further deps)
  |     |-- Depends on: F4 (env var override via pydantic-settings)
  |     |-- Depends on: F3 (local override, just another layer)
  |
  +-- F9: AGENTS.md instruction chain
  |     |-- Depends on: F2
  |     |-- Depends on: F8 (discover paths for rules)
  |     |-- Feeds into: PromptAssembler (<user-provided> block)
  |
  +-- F10: Profile-based prompt assembly
        |-- Depends on: F8 (discover("profiles"))
        |-- Feeds into: PromptAssembler (existing blocks)
        |-- No code change to AgentProfile.from_directory

Integration adapters (thin wrappers over existing APIs):
  agents/config.py load_agent_configs()  <-- F8 discover("agents")
  skills/registry.py SkillRegistry       <-- F8 discover("skills")  [already accepts list[Path]]
  hooks/manager.py HookManager           <-- F8 discover("hooks")   [needs from_paths() adapter]
  prompts/profiles.py AgentProfile       <-- F8 discover("profiles") [already has from_directory()]
  safety/permissions.py PermissionPipeline <-- F1 settings.permissions [needs injection adapter]
  tools/mcp/config.py McpManager         <-- F1 settings + F8 discover("mcp") [needs merge adapter]
  tasks/manager.py TaskManager           <-- F8 discover("tasks")   [needs default dir adapter]

Differentiators (can build after core):
  D1: Path-scoped rules  <-- depends on SkillRegistry._glob_match pattern + F8
  D2: user.md persona    <-- depends on F9 (AGENTS.md chain), trivial add
  D3: Project root auto-detect <-- depends on F2, trivial pathlib walk
  D4: Hot-reload         <-- depends on F1, reuses SkillRegistry mtime pattern
  D5: Validation         <-- depends on F1, wraps Pydantic ValidationError
```

## Existing Code Integration Points

Each existing module needs only a thin adapter. No internal logic changes required.

| Module | File | Current Pattern | Needed Change | Effort |
|--------|------|----------------|---------------|--------|
| Backend Settings | `backend/app/config/__init__.py` | `BaseSettings(env_prefix="APP_")` | ConfigLoader provides defaults from settings.json; BaseSettings handles env vars. No change to BaseSettings class. | Minimal |
| Agent Config | `agents/config.py` `load_agent_configs()` | Takes single `directory: Path` | Extend to accept `list[Path]`. Iterate paths low-to-high, project names override global on collision (with warning). | Low |
| Skill Registry | `skills/registry.py` `SkillRegistry` | Already takes `list[Path]` in constructor | Pass `discover("skills")` output. No internal change. Already has mtime refresh. | Minimal |
| Hook Manager | `hooks/manager.py` `HookManager` | `load_from_json(path: Path)` for single file | Add `load_from_paths(paths: list[Path])` that iterates and calls `register()` for each. Hooks merge (all scopes active). | Low |
| Agent Profile | `prompts/profiles.py` `AgentProfile` | `from_directory(path: Path)` for single profile | Call with path from `discover("profiles")`. No AgentProfile change. | Minimal |
| Prompt Assembler | `prompts/assembler.py` `PromptAssembler` | Assembles profile blocks into system prompt | Inject AGENTS.md chain as `profile.user_context`. No assembler change. | Minimal |
| Permission Pipeline | `safety/permissions.py` | Reads `AgentProfile.allowed_tools` / `disallowed_tools` | Settings.permissions injected into profile construction. Pipeline unchanged. | Minimal |
| MCP Manager | `tools/mcp/config.py` `McpManager` | Takes `list[McpServerConfig]` in constructor | Build config list from `discover("mcp")` + settings merge. No McpManager change. | Low |
| Task Manager | `tasks/manager.py` `TaskManager` | Takes `tasks_dir: Path` in constructor | Default to `.agent-framework/tasks/` via discover. No TaskManager change. | Minimal |
| Agent Loop | `agents/agent_loop.py` `AgentLoop` | 15-param constructor | Callers construct deps via ConfigLoader, pass as before. AgentLoop unchanged. | None |

## MVP Recommendation

**Phase 1 -- Core infrastructure (F2, F5-F7, F1, F3, F4)**
1. Two-tier directory structure -- `~/.agent-framework/` + `.agent-framework/`
2. Merge engine -- scalar override, array union, object shallow merge (pure functions, heavily tested)
3. Settings Pydantic model -- documented schema with all cross-module fields
4. ConfigLoader -- layered loading with merge + env var override

**Phase 2 -- Module discovery (F8, D3)**
5. `discover_paths()` with project root auto-detection
6. Adapt each of 8 modules to accept `discover()` output
7. Integration tests: end-to-end config -> module loading

**Phase 3 -- Instruction chain (F9, F10, D2)**
8. AGENTS.md chain loader (global + project + local + parent traversal)
9. Profile loading via discover("profiles")
10. Wire into PromptAssembler
11. user.md persona injection

**Phase 4 -- Polish (D1, D4, D5)**
12. Path-scoped rules (reuse SkillRegistry glob pattern)
13. Validation with file-path error context
14. mtime-based hot-reload for settings

**Defer:**
- Managed/enterprise scope: Not applicable to framework use case
- Import syntax (`@path`): Adds parsing complexity with marginal benefit
- Subdirectory on-demand loading: Complex, low immediate value
- Custom CLI flags for config path: Application concern, not framework

## Complexity Assessment

| Feature | Lines of Code (est.) | Test Cases (est.) | Risk Level |
|---------|---------------------|-------------------|------------|
| Settings Pydantic model (F1 partial) | ~80 | ~15 | Low |
| Merge engine (F5+F6+F7) | ~60 | ~25 | Low |
| ConfigLoader (F1 core) | ~120 | ~20 | Medium -- file I/O, path resolution |
| discover_paths() (F8) | ~40 | ~10 | Low |
| Project root auto-detect (D3) | ~25 | ~8 | Low |
| AGENTS.md chain loader (F9) | ~80 | ~15 | Medium -- parent traversal edge cases |
| Module adapters (8x, F8 integration) | ~40 each, ~320 total | ~5 each, ~40 total | Low -- thin wrappers |
| Path-scoped rules (D1) | ~60 | ~10 | Medium -- new integration point |
| Validation (D5) | ~40 | ~10 | Low |
| Hot-reload (D4) | ~30 | ~8 | Low -- proven pattern |
| **Total** | **~855** | **~161** | |

## Sources

- [Claude Code Settings Documentation](https://code.claude.com/docs/en/settings) -- Official docs for scope hierarchy, merge rules, permission behavior. HIGH confidence.
- [Claude Code Memory/CLAUDE.md Documentation](https://code.claude.com/docs/en/memory) -- Official docs for instruction chain loading, directory traversal, additive behavior. HIGH confidence.
- [pydantic-settings Context7 docs](/pydantic/pydantic-settings) -- Layered .env file loading, env_prefix behavior, multiple env_file priority. HIGH confidence.
- [Design doc: config-path-mechanism-design.md](../../docs/plans/2026-06-11-config-path-mechanism-design.md) -- Project-specific design decisions and directory structure. HIGH confidence.
- [Codebase Architecture](../codebase/ARCHITECTURE.md) -- Existing module structure, integration points, component responsibilities. HIGH confidence.
- [Codebase Concerns](../codebase/CONCERNS.md) -- Known issues that the config system should not worsen. HIGH confidence.
