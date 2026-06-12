# Domain Pitfalls: Unified Config/Path Mechanism for Agent Framework

**Domain:** Adding unified configuration hierarchy to existing modular Python framework
**Researched:** 2026-06-11
**Context:** v0.0.6 milestone -- dual-level directory structure, JSON settings merge, module auto-discovery, AGENTS.md instruction chain

## Critical Pitfalls

Mistakes that cause rewrites or major issues.

### Pitfall 1: Shallow Merge Destroys Nested Config

**What goes wrong:** When merging `settings.json` across 4 priority levels (env > local > project > global), a nested dict like `llm` at a higher priority level completely replaces the lower-priority version instead of merging keys. A project-level `settings.json` with `{"llm": {"base_url": "http://proxy"}}` wipes out the global `{"llm": {"provider": "anthropic", "api_key": ""}}`, losing `provider` and `api_key`.

**Why it happens:** Python's `dict.update()` is shallow by default. Pydantic-settings has the same problem -- [Issue #590](https://github.com/pydantic/pydantic-settings/issues/590) confirms that file merging in pydantic-settings is shallow: "if you have two files that both specify the same header key, the second one wipes everything else out." The design doc specifies "shallow merge for objects/dicts" which will hit this exact issue.

**Consequences:** Users set one nested field in their local override and lose all sibling fields from the base config. Silent data loss that only manifests at runtime when the missing field is accessed.

**Prevention:** Implement a dedicated `_deep_merge(base, override)` function that recursively merges dicts, with explicit per-field-type strategies (union for arrays, deep-merge for dicts, override for scalars). Do NOT use `dict.update()` for nested objects. Write tests for every combination: override-one-nested-field, override-all-nested-fields, add-new-nested-field.

**Detection:** Test with a global `settings.json` that has a full `llm` config, then override only `llm.base_url` in `settings.local.json`. Assert all other `llm.*` keys survive. This should be the FIRST test written.

### Pitfall 2: Backward Compatibility Breakage via Constructor Signature Changes

**What goes wrong:** Changing `SkillRegistry.__init__(skills_dirs: list[Path])` to accept `ConfigLoader.discover("skills")` output, or changing `TaskManager.__init__(tasks_dir: Path)` to expect a different path resolution, breaks the 1002 existing tests and any external code using the framework as a pip package.

**Why it happens:** The design doc says "all existing APIs remain unchanged, ConfigLoader is a new entry point." But the temptation to "just change the default parameter" is strong during implementation. A single parameter rename or type change in `AgentLoop.__init__` (which already has 15 parameters) cascades to every test fixture and instantiation site.

**Consequences:** 1002 tests break. External consumers of the framework package cannot upgrade without code changes. Violates the explicit backward-compatibility requirement.

**Prevention:** ConfigLoader must be purely additive. Existing modules receive their inputs exactly as before; the application layer (not the framework modules) is where ConfigLoader feeds discovered paths into existing constructors. Pattern:
```python
# DO NOT change SkillRegistry.__init__
# DO this in the application wiring layer:
loader = ConfigLoader()
registry = SkillRegistry(loader.discover("skills"))  # new wiring uses old API
```
The existing `skills_dirs: list[Path]` parameter stays; ConfigLoader just becomes the source of that list.

**Detection:** Run the full test suite (`cd framework && pytest tests/ -v`) after every ConfigLoader change. Zero test failures is the gate.

### Pitfall 3: Path.home() + Symlink + Mounted Volume Confusion

**What goes wrong:** `Path.home() / ".agent-framework/"` resolves differently on systems where `$HOME` is a symlink (macOS `/var/users/...` -> `/Users/...`), or on network-mounted home directories. Config files written to the unresolved path are invisible when read from the resolved path, or vice versa.

**Why it happens:** `Path.home()` does not call `.resolve()`. If `~` is `/var/users/alice` symlinked to `/Users/alice`, and code uses `Path.home()` without resolving, file writes and reads may hit different physical locations depending on whether other tools (git, editors) resolve the path or not.

**Consequences:** Config appears to "disappear" -- user creates `~/.agent-framework/settings.json` via the CLI, but the framework reads from a different resolved path. Extremely hard to debug because it depends on the user's filesystem setup.

**Prevention:** Call `.resolve()` on both `Path.home()` and `Path.cwd()` before constructing config paths. Do this once in ConfigLoader initialization and cache the resolved paths. Document that the framework resolves symlinks.

**Detection:** Test with a temporary directory that is symlinked, verify reads and writes hit the same physical path.

### Pitfall 4: AGENTS.md Chain Loading Order Semantics Diverge from Claude Code

**What goes wrong:** The design specifies a 10-step loading chain for system prompt assembly. If the ordering or concatenation semantics diverge from Claude Code's actual behavior (which users will compare against), the resulting prompts will be subtly wrong -- missing instructions, duplicated content, or wrong priority.

**Why it happens:** Claude Code's exact CLAUDE.md/AGENTS.md loading behavior is not formally documented as a spec; it evolves. The design doc specifies "full concatenation (not override)" but the ordering within each layer (global AGENTS.md before project AGENTS.md) affects which instructions the LLM prioritizes (LLMs weight earlier content differently from later content in long prompts).

**Consequences:** Agent behavior differs from user expectations set by Claude Code. Subtle prompt ordering issues cause agents to follow wrong rules, ignore constraints, or produce inconsistent output. Hard to trace back to prompt assembly order.

**Prevention:** (a) Implement the exact order from the design doc as written, but make it configurable via a `PromptChainConfig` dataclass so order can be adjusted without code changes. (b) Add integration tests that verify the assembled prompt contains all fragments in the documented order. (c) Log the assembled prompt at DEBUG level so users can inspect it.

**Detection:** Write a test that creates AGENTS.md files at every level (global, project, local, parent-dir chain) with unique markers, then assert the markers appear in the correct order in the assembled prompt.

### Pitfall 5: Module Auto-Discovery Name Collision with Silent Override

**What goes wrong:** When `discover("skills")` returns paths from both `~/.agent-framework/skills/` and `.agent-framework/skills/`, and both contain a skill named "search", the project-level one silently overrides the global one. The existing `SkillRegistry` already handles this ("same name keeps first scanned"), but the priority order reverses depending on scan direction.

**Why it happens:** The design says "project overrides global (same name: project version takes priority)" but the existing `SkillRegistry._full_refresh` iterates dirs in order and uses `if name in self._documents: continue` -- the first dir wins, not the last. If `discover_paths()` returns `[global, project]` (low-to-high priority), the global is scanned first, and the project-level duplicate is silently skipped.

**Consequences:** Project-level overrides don't work. User puts a customized "search" skill in `.agent-framework/skills/` but the global version is used instead. Silent, confusing, and contradicts the design doc.

**Prevention:** Reverse the scan order for name-collision modules: scan project-level FIRST, then global. Or better, collect all items first, then apply name-collision resolution with explicit priority. This requires changing the `SkillRegistry` scan behavior or the order of paths passed to it.

**Detection:** Create a skill with the same name in both global and project directories. Assert the project version is used. This test MUST pass before the feature is considered complete.

## Moderate Pitfalls

### Pitfall 6: JSON Parsing Errors Crash ConfigLoader Silently

**What goes wrong:** A malformed `settings.json` (trailing comma, single-quoted strings, BOM marker) raises `json.JSONDecodeError`. If ConfigLoader catches and silently returns defaults, the user's configuration is ignored without any indication.

**Why it happens:** JSON is strict. Users often write trailing commas or comments (not valid JSON). The existing `HookManager.load_from_json` already handles this pattern (logs warning, returns early), but for ConfigLoader the stakes are higher -- it's the single source of truth for all config.

**Prevention:** (a) Validate JSON strictly but produce clear error messages with file path and line number. (b) Never silently fall back to defaults -- log at WARNING level with the full file path. (c) Consider using `json.JSONDecodeError` attributes (`lineno`, `colno`) to produce actionable error messages. (d) Do NOT attempt to parse with `json5` or comment-stripping -- that creates ambiguity about what the format actually is.

### Pitfall 7: File Encoding Assumptions on AGENTS.md

**What goes wrong:** `Path.read_text()` defaults to UTF-8 on modern Python, but if an AGENTS.md file is saved with a BOM (Byte Order Mark) or in a legacy encoding (Shift-JIS, Latin-1 on Windows), the read fails or produces garbled text in the system prompt.

**Why it happens:** The design crosses platform boundaries -- developers on different OSes with different locale settings may create AGENTS.md files. The existing `_read_file` in `profiles.py` uses `encoding="utf-8"` explicitly, which is correct but will raise `UnicodeDecodeError` on non-UTF8 files.

**Prevention:** (a) Always use `encoding="utf-8"` explicitly (matching existing pattern). (b) Catch `UnicodeDecodeError` and log a clear message with the file path. (c) Do NOT try to detect encoding -- that way lies mojibake. (d) Document that all config files must be UTF-8.

### Pitfall 8: Async Mismatch -- ConfigLoader is Sync but Consumers are Async

**What goes wrong:** ConfigLoader reads files synchronously (`Path.read_text()`, `json.loads()`) but is called from async code in `AgentLoop`, `McpManager.start()`, and other async entry points. Each file read blocks the event loop.

**Why it happens:** The design does not mention async for ConfigLoader. The existing codebase has this exact problem documented in CONCERNS.md: "Synchronous file I/O in async context -- Memory subsystem uses synchronous `Path.read_text()` calls. These block the event loop." ConfigLoader would add more blocking I/O at initialization.

**Prevention:** ConfigLoader is fundamentally a startup-time operation (load once, cache results). This is acceptable for sync I/O IF (a) it only runs at startup, not per-request, and (b) the total file count is bounded. Document that `ConfigLoader.load_settings()` should be called once at application startup, not inside the request loop. Cache the result. For hot-reload scenarios, use `asyncio.to_thread()`.

### Pitfall 9: Circular Import Between ConfigLoader and Module Registries

**What goes wrong:** ConfigLoader needs to import module types (SkillManifest, HookConfig, McpServerConfig) to validate discovered configs. Meanwhile, those modules might need ConfigLoader to resolve their own config paths. This creates circular imports at the framework layer.

**Why it happens:** The existing codebase already uses `TYPE_CHECKING` guards extensively (agent_loop.py imports HookManager, TaskRunner, TeamManager under TYPE_CHECKING). Adding ConfigLoader as a cross-cutting dependency increases the risk.

**Prevention:** ConfigLoader should NOT import module-specific types. It returns raw paths and raw dicts. Module-specific validation happens in each module's own code. ConfigLoader's `discover()` returns `list[Path]`, not parsed/validated objects. The merge/parse pipeline is: ConfigLoader returns paths -> module code reads and validates using its own types. This keeps ConfigLoader as a pure path-resolution and settings-merge utility with zero module dependencies.

### Pitfall 10: settings.json Schema Drift Between Framework Versions

**What goes wrong:** As the framework evolves, new fields are added to `settings.json`. Old `settings.json` files (from previous framework versions) are missing these fields. If validation is strict, startup fails. If validation is lenient, new features silently use defaults the user didn't intend.

**Why it happens:** The design does not mention schema versioning. Pydantic models provide default values, so missing fields are filled in -- but this is a behavior, not a documented contract. Over time, users accumulate settings files with unknown combinations of present/absent fields.

**Prevention:** (a) Use Pydantic BaseModel with default values for ALL settings fields (never required fields in settings.json). (b) Log at INFO level which fields were filled with defaults vs loaded from file. (c) Do NOT add a `version` field to settings.json -- that creates migration complexity. Instead, make every field optional with sensible defaults. (d) Write a test that validates an empty `{}` settings.json loads without error.

### Pitfall 11: discover_paths() Returns Empty List When No Config Exists

**What goes wrong:** On a fresh install, neither `~/.agent-framework/` nor `.agent-framework/` exist. `discover_paths()` returns `[]`. Downstream code that iterates over discovered paths silently does nothing, and the system starts with no configuration, no skills, no agents, no permissions.

**Why it happens:** The design assumes directories will exist. But a first-time user has nothing. The existing `SkillRegistry.__init__` handles this (empty dirs list produces empty registry), but `HookManager` and `PermissionPipeline` may not handle empty config gracefully.

**Prevention:** (a) ConfigLoader should have well-documented defaults for every settings field. (b) `discover()` returning empty should be a documented, tested case. (c) The system must be fully functional with zero config files -- all modules must work with sensible built-in defaults. (d) Test the "no config files exist" scenario explicitly.

### Pitfall 12: Parent Directory AGENTS.md Traversal Hits Git Boundary or Root

**What goes wrong:** Step 4 of the instruction chain traverses "from root to working directory, loading AGENTS.md from each directory." If the working directory is `/Users/alice/projects/myapp/src/`, this traverses `/Users/`, `/Users/alice/`, `/Users/alice/projects/`, `/Users/alice/projects/myapp/`, `/Users/alice/projects/myapp/src/`. This loads AGENTS.md from home directory, which is the same as step 1 (global AGENTS.md), causing duplication.

**Why it happens:** The traversal has no stop condition except "reached root." It doesn't respect git repository boundaries (`.git/`), which is how Claude Code actually scopes its CLAUDE.md loading.

**Prevention:** (a) Stop traversal at the first `.git/` directory found (the git root). Do not traverse above it. (b) Deduplicate against already-loaded global AGENTS.md to avoid double-loading the same file. (c) Document the stop condition clearly.

## Minor Pitfalls

### Pitfall 13: Windows Path Separators in settings.json

**What goes wrong:** `settings.json` paths written on Windows use backslashes. The framework uses `pathlib.Path` which handles this, but if any code does string manipulation on paths instead of using Path objects, it breaks cross-platform.

**Prevention:** Always use `pathlib.Path` for all path operations. Never join paths with `+` or f-strings.

### Pitfall 14: AGENTS.local.md Committed to Git by Accident

**What goes wrong:** `.agent-framework/settings.local.json` and `AGENTS.local.md` are personal overrides that should be gitignored. If `.gitignore` is not set up, these files get committed, and team members see each other's local overrides.

**Prevention:** ConfigLoader or its initialization routine should verify `.gitignore` entries. Better: the framework's template/init command should generate a `.gitignore` file. At minimum, document the required gitignore entries.

### Pitfall 15: Concurrent Access to settings.json from Multiple Processes

**What goes wrong:** Two agent processes running simultaneously read and write `settings.json`. One process's write overwrites the other's changes.

**Why it happens:** The framework is async single-threaded, but nothing prevents multiple framework instances from running against the same project directory.

**Prevention:** For v0.0.6, document that settings.json is read-only at runtime (loaded once at startup). If hot-reload is needed later, use file-watching with atomic read (read-then-stat-to-verify-freshness).

### Pitfall 16: Memory Bloat from Caching All Discovered Module Content

**What goes wrong:** If `discover()` not only returns paths but loads all content (skill texts, agent definitions, rule files) into memory at startup, and a user has hundreds of skills or large AGENTS.md files, memory usage balloons.

**Prevention:** ConfigLoader should return paths, not loaded content. Each module loads content lazily on demand (the existing `SkillRegistry` already does this pattern well with its mtime-based refresh).

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| ConfigLoader core (loader.py, settings.py) | Shallow merge destroys nested config (#1) | Write deep_merge with per-type strategies first, test exhaustively |
| Discovery module (discovery.py) | Path.home() symlink issues (#3) | Resolve all paths at init, test with symlinked temp dirs |
| Settings model (settings.py) | Schema drift across versions (#10) | All fields optional with defaults, test empty JSON loads |
| Module integration wiring | Backward compatibility breakage (#2) | Zero changes to existing module APIs, wire in application layer only |
| AGENTS.md chain loading | Traversal above git root (#12) | Stop at .git/ boundary, deduplicate against global |
| Skill/Agent discovery | Name collision silent override (#5) | Test same-name items in global+project, verify project wins |
| Hook/MCP config loading | Circular imports (#9) | ConfigLoader returns raw paths/dicts, modules validate their own types |
| End-to-end integration | Empty config on fresh install (#11) | Test "no files exist" scenario, verify defaults work |

## Confidence Assessment

| Pitfall | Confidence | Source |
|---------|------------|--------|
| Shallow merge (#1) | HIGH | [pydantic-settings Issue #590](https://github.com/pydantic/pydantic-settings/issues/590) + verified against design doc |
| Backward compat (#2) | HIGH | Direct codebase analysis of existing constructors + test count |
| Symlink paths (#3) | MEDIUM | General Python path behavior, not verified against this specific framework |
| Prompt chain order (#4) | MEDIUM | Design doc analysis + community discussion of AGENTS.md patterns |
| Name collision (#5) | HIGH | Direct code reading of `SkillRegistry._full_refresh` line 167 |
| JSON parsing (#6) | HIGH | Standard JSON behavior + existing `HookManager.load_from_json` pattern |
| Async mismatch (#8) | HIGH | Directly from CONCERNS.md "synchronous file I/O in async context" finding |
| Circular imports (#9) | HIGH | Existing `TYPE_CHECKING` pattern in codebase + architectural analysis |
| Schema drift (#10) | MEDIUM | Pydantic BaseModel default behavior, not a bug but a design consideration |
| Empty config (#11) | HIGH | Standard fresh-install scenario |
| Git boundary (#12) | HIGH | Claude Code documented behavior + common directory-traversal pattern |

## Sources

- [pydantic-settings Issue #590 -- Shallow merge](https://github.com/pydantic/pydantic-settings/issues/590): Confirmed that pydantic-settings does shallow dict merging, not deep merge. HIGH confidence.
- [pydantic-settings custom sources](https://github.com/pydantic/pydantic-settings): Source priority ordering and `settings_customise_sources` documentation. HIGH confidence.
- [Pydantic v2 model_copy/deepcopy discussion #9313](https://github.com/pydantic/pydantic/discussions/9313): Shallow copy by default in Pydantic v2. HIGH confidence.
- [CPython importlib race condition #30891](https://bugs.python.org/issue30891): Race condition in module loading. MEDIUM relevance.
- [agents.md Issue #135 -- progressive loading proposal](https://github.com/agentsmd/agents.md/issues/135): Directory traversal and progressive loading discussion. MEDIUM confidence.
- Codebase analysis: Direct reading of `SkillRegistry`, `HookManager`, `AgentProfile`, `PermissionPipeline`, `McpManager`, `PromptAssembler`, `TaskManager` source code. HIGH confidence.
- `.planning/codebase/CONCERNS.md`: Existing known issues including sync I/O in async context. HIGH confidence.
- Design doc `docs/plans/2026-06-11-config-path-mechanism-design.md`: The target design specification. HIGH confidence.

---

*Pitfall analysis: 2026-06-11*
