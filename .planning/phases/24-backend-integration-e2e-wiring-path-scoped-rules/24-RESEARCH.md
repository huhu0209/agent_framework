# Phase 24: Backend Integration + E2E Wiring + Path-Scoped Rules - Research

**Researched:** 2026-06-12
**Domain:** ConfigLoader integration / rules module / PromptAssembler / backend wiring
**Confidence:** HIGH

## Summary

Phase 24 是 v0.0.6 的最终集成阶段，将 Phase 20-23 构建的所有 ConfigLoader + from_loader() 组件连成端到端链路。核心工作分为三块：(1) Backend Config 集成 -- backend Settings 从 ConfigLoader 获取默认值，AgentFactory 新增 from_configloader() 一键初始化; (2) Path-Scoped Rules -- 新建 rules/ 模块，支持 frontmatter paths 条件匹配加载; (3) PromptAssembler 集成 -- 修改 assemble() 签名，按设计文档顺序构建完整 system prompt。

所有 from_loader() 工厂方法在 Phase 22-23 已完整建立，本 phase 不需要新增适配器模式，而是将已有适配器在应用层统一编排。现有测试基线：framework 1121 tests passing，backend 23 passed / 9 failed (pre-existing session tests)。

**Primary recommendation:** 严格遵循 Phase 22-23 的 from_loader() @classmethod 范式复制到 RuleLoader; PromptAssembler 签名变更直接影响 28 个现有测试，需逐一更新; backend 集成通过新增 from_configloader() 方法（不修改 from_settings()），保持零回归。

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** ConfigLoader 作为 fallback -- backend Settings (pydantic-settings BaseSettings) 保留 APP_ env vars + .env 文件机制，ConfigLoader.load_settings() 提供默认值，env var 仍为最高优先级
- **D-02:** 并行初始化 -- main.py lifespan 中 ConfigLoader 和 backend Settings 独立创建，AgentFactory 同时持有两者
- **D-03:** redis_url 留 backend Settings 独有 -- framework Settings 不感知 Redis，保持分离
- **D-04:** 叶依赖通过测试验证 -- 写测试确保 config/ 模块不导入框架其他模块
- **D-05:** Glob 模式（fnmatch）-- paths 使用 Python fnmatch 库，支持 `*` 和 `**` 通配符
- **D-06:** paths 相对于项目根目录（ConfigLoader.project_dir）解析 -- 与 discover() 路径一致
- **D-07:** 无 paths frontmatter 的 rules 始终加载 -- 用于全局规则
- **D-08:** 新建 `framework/agent_framework/rules/` 模块
- **D-09:** 直接修改 `assemble(profile)` 签名为 `assemble(loader, profile, context_path=None)`
- **D-10:** 严格按设计文档顺序构建 system prompt 块：`<user-provided>` -> `<rules>` -> `<soul>` -> `<instructions>` -> `<identity>` -> `<skills>` -> `<tool-guidance>`
- **D-11:** assemble() 内部调用 `loader.load_agents_md()` 获取指令链注入 `<user-provided>` 块，调用 RuleLoader 加载 rules 注入 `<rules>` 块
- **D-12:** `context_path` 参数过滤 rules -- 传当前文件/目录路径给 RuleLoader
- **D-13:** 扩展现有 AgentFactory -- 新增 `from_configloader(loader, backend_settings)` 工厂方法
- **D-14:** 单次调用全初始化 -- from_configloader() 内部调用所有模块的 from_loader()
- **D-15:** E2E 验证通过集成测试

### Claude's Discretion
- `from_configloader()` 内部各 from_loader() 的具体调用顺序和错误处理策略
- RuleLoader 类的具体 API 设计（类方法 vs 实例方法，是否接受 loader 参数）
- rules/*.md 文件解析的具体 frontmatter 格式（是否复用现有 parse_frontmatter()）
- 集成测试文件组织和测试用例设计
- 叶依赖测试的具体实现方式（AST 分析 vs import 尝试）
- PromptAssembler 新增块的 PromptBlock name/stability/cache_breakpoint 属性值

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INS-03 | rules/*.md 收集全局 + 项目路径，支持 paths 前言条件匹配 | New rules/ module with RuleLoader, discover("rules"), fnmatch matching |
| INS-06 | PromptAssembler 集成 -- 指令链注入 <user-provided> 块 | Modify assemble() signature, call loader.load_agents_md() + RuleLoader |
| INT-01 | backend/app/config/ 从 ConfigLoader.load_settings() 获取默认值 | Parallel init in lifespan, ConfigLoader as fallback for backend Settings |
| INT-02 | backend AgentFactory 使用 ConfigLoader 初始化模块注册表 | New from_configloader() factory method on AgentFactory |
| INT-03 | config/ 模块作为叶依赖 | AST-based test already exists in test_loader.py, extend to all config/ files |
| INT-04 | 端到端验证 -- ConfigLoader -> discover -> adapters -> registries | New integration test file |
| INT-05 | 全部 1121+ 现有测试通过 | Baseline verified: 1121 passing in framework |
| INT-06 | Path-scoped rules -- rules/*.md 支持 frontmatter paths 条件匹配 | Same as INS-03, fnmatch-based matching with context_path filter |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| ConfigLoader (config/) | API / Backend | -- | Leaf dependency, no knowledge of other framework modules |
| RuleLoader (rules/) | API / Backend | -- | New framework module, depends only on config/ and memory/frontmatter |
| PromptAssembler (prompts/) | API / Backend | -- | Modified to accept ConfigLoader, orchestrates all prompt sources |
| Backend Settings (backend/app/config/) | API / Backend | -- | pydantic-settings, reads APP_ env vars, uses ConfigLoader as fallback |
| AgentFactory (backend/app/services/) | API / Backend | -- | Application layer bridge, calls framework from_loader() methods |
| E2E Integration Tests | Test | -- | Cross-module validation |

## Standard Stack

### Core (No new packages needed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| fnmatch (stdlib) | Python 3.11+ | Glob pattern matching for rule paths | Decision D-05, no installation needed |
| parse_frontmatter() | existing | YAML frontmatter parsing for rules | Already in agent_framework.memory.frontmatter, supports flat key:value |
| ConfigLoader | existing | Central loader for all config | Phase 21 implementation, discover("rules") already in MODULE_DIRS |
| pydantic-settings | >=2.0.0 | Backend Settings (BaseSettings) | Already in backend dependencies |

**Installation:**
```bash
# No new packages required for this phase
# All dependencies are existing stdlib or already-installed packages
```

**Version verification:**
```bash
python3 -c "import fnmatch; print('fnmatch: stdlib')"
python3 -c "from agent_framework.memory.frontmatter import parse_frontmatter; print('parse_frontmatter: OK')"
python3 -c "from agent_framework.config.loader import ConfigLoader; print('ConfigLoader: OK')"
```

## Package Legitimacy Audit

This phase installs **zero new external packages**. All functionality is built from:
- Python stdlib (`fnmatch`, `ast`, `pathlib`)
- Existing framework modules (`config/`, `memory/frontmatter.py`)
- Already-installed dependencies (`pydantic`, `pydantic-settings`)

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
                    main.py lifespan
                         |
            +------------+------------+
            |                         |
     ConfigLoader()            backend Settings()
     (framework)               (pydantic-settings)
            |                         |
            v                         v
   AgentFactory.from_configloader(loader, settings)
            |
            +-- SkillRegistry.from_loader(loader)
            +-- HookManager.from_loader(loader)
            +-- CommandDispatcher.from_loader(loader)
            +-- AgentConfig.from_loader(loader)       -> dict[str, AgentConfig]
            +-- AgentProfile.from_profile(loader, name) -> AgentProfile
            +-- McpManager.from_loader(loader)
            +-- PermissionPipeline.from_loader(loader, name)
            +-- RuleLoader.load_rules(loader, context_path)  [NEW]
            |
            v
     PromptAssembler.assemble(loader, profile, context_path)
            |
            +-- loader.load_agents_md()        -> <user-provided>
            +-- RuleLoader.load_rules(...)      -> <rules>
            +-- profile.soul                    -> <soul>
            +-- profile.agents_rules            -> <instructions>
            +-- profile.identity                -> <identity>
            +-- skill_registry.describe_available() -> <skills>
            +-- profile.tool_guidance           -> <tool-guidance>
            |
            v
     Complete system prompt -> AgentLoop
```

### Recommended Project Structure
```
framework/agent_framework/
├── rules/                          # NEW module directory
│   ├── __init__.py                 # barrel export with __all__
│   └── loader.py                   # RuleLoader class
├── config/                         # EXISTING - no changes needed
├── prompts/
│   ├── assembler.py                # MODIFY - new assemble() signature
│   └── profiles.py                 # EXISTING - no changes needed
├── agents/
│   └── config.py                   # EXISTING - no changes needed

backend/app/
├── main.py                         # MODIFY - parallel ConfigLoader init
├── config/__init__.py              # POTENTIALLY MODIFY - ConfigLoader fallback
└── services/
    └── agent_factory.py            # MODIFY - add from_configloader()

framework/tests/
├── test_prompt_assembler.py        # UPDATE - new assemble() signature
├── test_rules.py                   # NEW - RuleLoader tests
├── test_config_leaf.py             # NEW - comprehensive leaf dependency test
└── test_e2e_integration.py         # NEW - full pipeline integration test
```

### Pattern 1: from_loader() @classmethod (Phase 22-23 established)

**What:** Class method that accepts ConfigLoader, calls discover(), iterates paths, returns fully initialized instance.
**When to use:** Every module adapter that needs ConfigLoader-based initialization.
**Example:**
```python
# Source: framework/agent_framework/skills/registry.py [VERIFIED: codebase]
@classmethod
def from_loader(cls, loader: ConfigLoader) -> SkillRegistry:
    paths = loader.discover("skills")
    return cls(skills_dirs=list(reversed(paths)))
```

**Key conventions observed across all 7 from_loader() implementations:**
1. Always `@classmethod`, first param is `loader: ConfigLoader`
2. Call `loader.discover(<module_name>)` to get paths
3. Natural-order iteration [global, project] with last-write-wins (except SkillRegistry which reverses for first-found-wins)
4. `logger.warning()` on name collisions
5. Silent skip on invalid entries, no crashes

### Pattern 2: RuleLoader (NEW -- following established conventions)

**What:** Static/class method to load and filter rules from discover("rules") paths.
**When to use:** PromptAssembler integration and direct rule loading.
**Example:**
```python
# Proposed design following established patterns
from fnmatch import fnmatch
from pathlib import Path
from agent_framework.config.loader import ConfigLoader
from agent_framework.memory.frontmatter import parse_frontmatter

class RuleLoader:
    @staticmethod
    def load_rules(loader: ConfigLoader, context_path: str | None = None) -> str:
        """Load matching rules content."""
        paths = loader.discover("rules")
        all_rules: list[str] = []
        for rules_dir in paths:
            for md_file in sorted(rules_dir.glob("*.md")):
                raw = md_file.read_text(encoding="utf-8")
                meta, body = _parse_rule_document(raw)
                rule_paths = meta.get("paths")
                # D-07: rules without paths always loaded
                if rule_paths is None:
                    all_rules.append(body)
                elif context_path is not None:
                    # D-06: paths relative to project_dir
                    if any(fnmatch(context_path, p) for p in _parse_paths(rule_paths)):
                        all_rules.append(body)
        return "\n\n".join(all_rules)
```

### Anti-Patterns to Avoid
- **Don't modify existing from_settings() or constructor signatures** -- purely additive API (ADP-09 principle)
- **Don't put redis_url in framework Settings** -- D-03 explicitly keeps it backend-only
- **Don't use PurePosixPath.match for rule matching** -- D-05 specifies fnmatch; PurePosixPath.match has different semantics
- **Don't skip the leaf dependency test** -- INT-03 is an explicit requirement

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Frontmatter parsing | Custom YAML parser | `parse_frontmatter()` from memory/frontmatter.py | Already exists, handles edge cases (no YAML lib needed) |
| Skill document parsing | Custom split("---") | `_parse_skill_document()` pattern | Proven in skills/parser.py, handles missing/unclosed frontmatter |
| Path glob matching | Custom glob implementation | `fnmatch` from stdlib | D-05 decision, stdlib, no edge cases to handle |
| Module path discovery | Direct Path manipulation | `ConfigLoader.discover("rules")` | Already in MODULE_DIRS, handles global/project correctly |
| Settings merge | Custom dict merge | `merge_settings()` from config/merge.py | Three-strategy merge (scalar override, dict shallow, list union) |

**Key insight:** Every piece of infrastructure needed for this phase already exists. The work is integration, not invention.

## Common Pitfalls

### Pitfall 1: fnmatch * matches path separators
**What goes wrong:** `fnmatch` treats `*` as matching `/` in paths, so `src/*.py` matches `src/deep/main.py`. This differs from shell glob and PurePosixPath.match semantics.
**Why it happens:** fnmatch was designed for filename matching, not path matching. It does not treat `/` as special.
**How to avoid:** This is actually the D-05 decision (use fnmatch). If path-separator-aware matching is needed later, switch to PurePosixPath.match like SkillRegistry uses. For now, fnmatch behavior is acceptable per the locked decision.
**Warning signs:** Rules matching more files than expected due to `*` crossing directory boundaries.

### Pitfall 2: PromptAssembler test breakage from signature change
**What goes wrong:** D-09 changes `assemble(profile)` to `assemble(loader, profile, context_path=None)`. Every existing test calls `assembler.assemble(profile=profile)` which will fail with TypeError.
**Why it happens:** 28 test methods in test_prompt_assembler.py all call assemble() with old signature.
**How to avoid:** Update all test methods to pass a ConfigLoader instance (or mock). Create a test helper that provides a no-op ConfigLoader.
**Warning signs:** `TypeError: assemble() missing 1 required positional argument: 'loader'`

### Pitfall 3: Backend Settings field name mismatch
**What goes wrong:** Backend Settings uses `llm_provider`, `llm_api_key`, `llm_model`, `llm_base_url` while framework Settings uses `model`, `llm.provider`, `llm.api_key`, `llm.base_url`. Direct mapping requires explicit field translation.
**Why it happens:** Backend was designed independently before the framework config system.
**How to avoid:** from_configloader() must explicitly map between the two schemas. Consider a helper method `_settings_to_adapter_params()`.
**Warning signs:** AgentFactory creating adapters with None api_key or wrong model name.

### Pitfall 4: Circular import between backend and framework config
**What goes wrong:** If backend/app/config/__init__.py imports from agent_framework.config at module level, and main.py imports both, a circular import chain could form.
**Why it happens:** Python resolves imports at module load time.
**How to avoid:** Backend config module already uses pydantic-settings independently. ConfigLoader fallback should be done at runtime in main.py lifespan, not at import time. The import chain is: main.py -> app.config (no framework imports) AND main.py -> agent_framework.config. These are independent at import time.
**Warning signs:** `ImportError: cannot import name 'ConfigLoader' from partially initialized module`

### Pitfall 5: RuleLoader paths field is a list, parse_frontmatter returns strings
**What goes wrong:** `parse_frontmatter()` returns `dict[str, str]` -- the `paths` field will be a single string like `"src/**/*.py, tests/**/*.py"`. Needs splitting into a list.
**Why it happens:** parse_frontmatter is intentionally simple (no YAML lib). It cannot parse YAML lists.
**How to avoid:** Reuse the `_parse_list()` pattern from skills/parser.py -- split by comma, strip whitespace. The RuleLoader should call a helper like `_parse_paths(meta.get("paths"))`.
**Warning signs:** `fnmatch` receiving the full comma-separated string as a single pattern.

## Code Examples

### Rule document parsing (following SkillRegistry pattern)
```python
# Source: Adapted from framework/agent_framework/skills/parser.py [VERIFIED: codebase]
def _parse_rule_document(text: str) -> tuple[dict[str, str], str]:
    """Parse rule .md file, return (meta_dict, body_string)."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return {}, text
    end_idx = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end_idx = i
            break
    if end_idx is None:
        return {}, text
    body = "\n".join(lines[end_idx + 1:]).strip()
    meta = parse_frontmatter_lines(lines[1:end_idx])
    return meta, body
```

### Existing leaf dependency test pattern (already in test_loader.py)
```python
# Source: framework/tests/test_loader.py [VERIFIED: codebase]
class TestLeafDependency:
    def test_loader_does_not_import_non_config_modules(self) -> None:
        import ast
        config_dir = Path(__file__).resolve().parent.parent / "agent_framework" / "config"
        loader_file = config_dir / "loader.py"
        if not loader_file.exists():
            pytest.skip("loader.py not yet created")
        tree = ast.parse(loader_file.read_text(encoding="utf-8"))
        forbidden_prefixes = ("agent_framework.",)
        allowed_imports = ("agent_framework.config",)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if any(node.module.startswith(p) for p in forbidden_prefixes):
                    if not any(node.module.startswith(a) for a in allowed_imports):
                        pytest.fail(...)
```

### New assemble() signature
```python
# Source: Design doc + CONTEXT.md D-09, D-10, D-11 [VERIFIED: codebase design]
def assemble(
    self,
    loader: ConfigLoader,
    profile: AgentProfile,
    context_path: str | None = None,
) -> list[PromptBlock]:
    """Assemble profile + loader data into ordered PromptBlock list."""
    blocks: list[PromptBlock] = []

    # 1. <user-provided> -- AGENTS.md chain
    user_provided = loader.load_agents_md()
    if user_provided:
        blocks.append(PromptBlock(
            name="USER_PROVIDED",
            content=user_provided,
            source="auto_generated",
            stability="semi_static",
            cache_breakpoint=True,
        ))

    # 2. <rules> -- path-scoped rules
    rules = RuleLoader.load_rules(loader, context_path)
    if rules:
        blocks.append(PromptBlock(
            name="RULES",
            content=rules,
            source="auto_generated",
            stability="semi_static",
            cache_breakpoint=True,
        ))

    # 3-7. Profile blocks (soul, instructions, identity, skills, tool-guidance)
    # ... existing profile block logic, reordered per D-10
```

### AgentFactory.from_configloader()
```python
# Source: CONTEXT.md D-13, D-14 [VERIFIED: codebase design]
@classmethod
def from_configloader(
    cls,
    loader: ConfigLoader,
    backend_settings: BackendSettings,
) -> AgentFactory:
    """Single-call full initialization via ConfigLoader."""
    from agent_framework.skills.registry import SkillRegistry
    from agent_framework.hooks.manager import HookManager
    from agent_framework.commands.dispatcher import CommandDispatcher
    # ... etc
    adapter = create_adapter(
        provider=backend_settings.llm_provider,
        api_key=backend_settings.llm_api_key.get_secret_value(),
        model=backend_settings.llm_model,
        base_url=backend_settings.llm_base_url,
    )
    factory = cls(adapter=adapter, model=backend_settings.llm_model)
    # Store loader for PromptAssembler access
    factory._loader = loader
    return factory
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| PromptAssembler(profile) | PromptAssembler().assemble(loader, profile, context_path) | Phase 24 | All assemble() callers need loader |
| AgentFactory.from_settings() only | + from_configloader() | Phase 24 | New entry point for config-driven init |
| No rules module | rules/ with RuleLoader | Phase 24 | New capability: path-scoped rules |
| Backend Settings standalone | Backend Settings + ConfigLoader fallback | Phase 24 | Config hierarchy unification |

**Deprecated/outdated:**
- `PromptAssembler.assemble(profile)` -- replaced by `assemble(loader, profile, context_path)` per D-09 (no backward compatibility needed per CONTEXT.md)

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | fnmatch `*` crossing directory boundaries is acceptable for rule matching | Architecture Patterns | Rules may match more paths than intended; mitigable with more specific patterns |
| A2 | Backend Settings `llm_provider` maps to `create_adapter(provider=...)` directly | Code Examples | If create_adapter expects different provider strings, mapping fails |
| A3 | rules/*.md frontmatter uses flat `paths: src/**/*.py, tests/**` format (not YAML list) | Common Pitfalls | parse_frontmatter returns str, not list; needs comma-split |
| A4 | PromptAssembler constructor `__init__(skill_registry)` stays unchanged | Architecture Patterns | If constructor changes, more tests break |
| A5 | render() method delegates to assemble(), so only assemble() needs signature change | Code Examples | If render() is called independently, it also needs updating |

**If this table is empty:** N/A -- 5 assumptions identified, all LOW risk and mitigable.

## Open Questions

1. **fnmatch vs PurePosixPath.match for rules**
   - What we know: D-05 locks fnmatch. fnmatch `*` matches `/`. PurePosixPath.match does not.
   - What's unclear: Whether the user wants shell-glob semantics (PurePosixPath.match) or fnmatch semantics for `**` patterns
   - Recommendation: Use fnmatch per D-05. If `**` support is needed, adopt the SkillRegistry._glob_match helper pattern (tries both `**` and flat variants)

2. **RuleLoader API shape: @staticmethod vs @classmethod vs standalone function**
   - What we know: CONTEXT.md says "Claude's discretion"
   - What's unclear: Whether it should be a class with state or a pure function
   - Recommendation: `@staticmethod` on a `RuleLoader` class, matching the CONTEXT.md specific idea. No state needed.

3. **PromptBlock name values for new blocks**
   - What we know: Existing names are "SOUL", "AGENTS_RULES", "IDENTITY", "USER", "SKILLS", "TOOL_GUIDANCE"
   - What's unclear: Exact names for "USER_PROVIDED" and "RULES" blocks
   - Recommendation: Use "USER_PROVIDED" and "RULES" (matching _BLOCK_TAGS mapping to "user-provided" and "rules")

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | Framework | YES | 3.13 | -- |
| pytest | Testing | YES | 8.0+ | -- |
| pydantic | Framework | YES | 2.x | -- |
| pydantic-settings | Backend | YES | 2.x | -- |
| fnmatch (stdlib) | RuleLoader | YES | stdlib | -- |
| fastapi | Backend | YES | 0.115+ | -- |
| redis | Backend | YES | 5.x | -- |

**Missing dependencies with no fallback:** None

**Missing dependencies with fallback:** None

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ |
| Config file | framework/pyproject.toml [tool.pytest.ini_options] |
| Quick run command | `cd framework && pytest tests/test_rules.py tests/test_prompt_assembler.py -v` |
| Full suite command | `cd framework && pytest tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INS-03 | RuleLoader loads rules with path filtering | unit | `pytest tests/test_rules.py -v` | NO - Wave 0 |
| INS-06 | PromptAssembler integrates AGENTS.md + rules + profile | unit | `pytest tests/test_prompt_assembler.py -v` | EXISTS - needs update |
| INT-01 | Backend config uses ConfigLoader fallback | integration | `pytest tests/test_e2e_integration.py -v` | NO - Wave 0 |
| INT-02 | AgentFactory.from_configloader creates full AgentLoop | integration | `pytest tests/test_e2e_integration.py -v` | NO - Wave 0 |
| INT-03 | config/ is leaf dependency (no framework imports) | unit | `pytest tests/test_config_leaf.py -v` | PARTIAL - exists in test_loader.py |
| INT-04 | E2E: ConfigLoader -> discover -> adapters -> registries | integration | `pytest tests/test_e2e_integration.py -v` | NO - Wave 0 |
| INT-05 | 1121+ existing tests pass (zero regression) | regression | `cd framework && pytest tests/ -q` | N/A |
| INT-06 | Path-scoped rules match context_path correctly | unit | `pytest tests/test_rules.py -v` | NO - Wave 0 |

### Sampling Rate
- **Per task commit:** `cd framework && pytest tests/test_rules.py tests/test_prompt_assembler.py -x -v`
- **Per wave merge:** `cd framework && pytest tests/ -v`
- **Phase gate:** `cd framework && pytest tests/ -q` (all 1121+ passing)

### Wave 0 Gaps
- [ ] `framework/tests/test_rules.py` -- RuleLoader unit tests (INS-03, INT-06)
- [ ] `framework/tests/test_config_leaf.py` -- comprehensive leaf dependency test for all config/ files (INT-03)
- [ ] `framework/tests/test_e2e_integration.py` -- full pipeline integration test (INT-01, INT-02, INT-04)
- [ ] Update `framework/tests/test_prompt_assembler.py` -- all 28 test methods need new assemble() signature (INS-06)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | N/A for this phase |
| V3 Session Management | no | N/A for this phase |
| V4 Access Control | no | N/A for this phase |
| V5 Input Validation | yes | Pydantic BaseModel validation on Settings, path traversal check in _validate_profile_name |
| V6 Cryptography | no | N/A for this phase |

### Known Threat Patterns for Python/Config Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal in profile names | Tampering | _validate_profile_name() rejects `..`, `/`, `\` |
| Arbitrary code execution via rule files | Elevation | Rules are Markdown (not executed), parsed as text only |
| Config file injection | Tampering | JSON validation with graceful error handling, no eval() |

## Sources

### Primary (HIGH confidence)
- Codebase: framework/agent_framework/config/loader.py -- ConfigLoader, discover(), load_agents_md(), load_profile() [VERIFIED: codebase]
- Codebase: framework/agent_framework/prompts/assembler.py -- PromptAssembler, _BLOCK_TAGS, assemble(), render() [VERIFIED: codebase]
- Codebase: framework/agent_framework/skills/registry.py -- from_loader() pattern, _glob_match() [VERIFIED: codebase]
- Codebase: framework/agent_framework/memory/frontmatter.py -- parse_frontmatter(), parse_frontmatter_lines() [VERIFIED: codebase]
- Codebase: framework/agent_framework/skills/parser.py -- _parse_skill_document(), _parse_paths() [VERIFIED: codebase]
- Codebase: framework/agent_framework/agents/config.py -- AgentConfig.from_loader() [VERIFIED: codebase]
- Codebase: framework/agent_framework/prompts/profiles.py -- AgentProfile.from_profile(), PromptBlock [VERIFIED: codebase]
- Codebase: framework/agent_framework/safety/permissions.py -- PermissionPipeline.from_loader() [VERIFIED: codebase]
- Codebase: framework/agent_framework/tools/mcp/config.py -- McpManager.from_loader() [VERIFIED: codebase]
- Codebase: framework/agent_framework/hooks/manager.py -- HookManager.from_loader() [VERIFIED: codebase]
- Codebase: framework/agent_framework/commands/dispatcher.py -- CommandDispatcher.from_loader() [VERIFIED: codebase]
- Codebase: backend/app/services/agent_factory.py -- AgentFactory, from_settings() [VERIFIED: codebase]
- Codebase: backend/app/config/__init__.py -- backend Settings [VERIFIED: codebase]
- Codebase: backend/main.py -- lifespan, current initialization flow [VERIFIED: codebase]
- Design doc: docs/plans/2026-06-11-config-path-mechanism-design.md -- full path mechanism design [VERIFIED: codebase]
- Phase 23-01-SUMMARY.md -- AgentConfig.from_loader + AgentProfile.from_profile [VERIFIED: codebase]
- Phase 23-02-SUMMARY.md -- McpManager.from_loader + TaskManager + PermissionPipeline.from_loader [VERIFIED: codebase]

### Secondary (MEDIUM confidence)
- Python stdlib fnmatch behavior verified via runtime test in this session

### Tertiary (LOW confidence)
- None -- all findings verified against codebase

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- zero new packages, all existing code thoroughly verified
- Architecture: HIGH -- all from_loader() patterns read from codebase, backend init flow traced
- Pitfalls: HIGH -- all pitfalls discovered from actual codebase patterns, not assumed

**Research date:** 2026-06-12
**Valid until:** 2026-07-12 (stable -- no external dependencies)
