---
phase: 24-backend-integration-e2e-wiring-path-scoped-rules
reviewed: 2026-06-12T12:00:00Z
depth: standard
files_reviewed: 10
files_reviewed_list:
  - framework/agent_framework/rules/__init__.py
  - framework/agent_framework/rules/loader.py
  - framework/agent_framework/prompts/assembler.py
  - framework/tests/test_rules.py
  - framework/tests/test_config_leaf.py
  - framework/tests/test_prompt_assembler.py
  - framework/tests/test_e2e_integration.py
  - backend/app/config/__init__.py
  - backend/app/services/agent_factory.py
  - backend/main.py
findings:
  critical: 2
  warning: 3
  info: 2
  total: 7
status: fixed
fix_commit: 889ff9f
---

# Phase 24: Code Review Report

**Reviewed:** 2026-06-12T12:00:00Z
**Depth:** standard
**Files Reviewed:** 10
**Status:** issues_found

## Summary

Reviewed 10 files spanning the framework rules module, prompt assembler, backend config, agent factory, and FastAPI main entry point. The framework-side code (rules loader, assembler, tests) is well-structured and correct. The critical defects are concentrated in the backend integration layer where `AgentFactory.from_configloader()` loads and stores multiple rich components (profile, skill registry, hook manager, assembler) but `create_loop()` completely ignores them, producing bare AgentLoop instances that bypass all the wiring this phase was supposed to deliver. Additionally, `main.py` creates `ConfigLoader()` with default CWD arguments that will silently resolve to the wrong directory when the backend is launched from a different working directory.

## Critical Issues

### CR-01: `create_loop()` ignores all loaded components from `from_configloader()`

**File:** `backend/app/services/agent_factory.py:85-94`
**Issue:** `create_loop()` constructs a bare `AgentLoop` passing only `adapter`, `model`, `router`, and `ctx`. It does NOT pass `profile`, `hook_manager`, `skill_dirs`, or any of the components painstakingly loaded in `from_configloader()`. The fields `_default_profile`, `_hook_manager`, `_skill_registry`, `_assembler`, `_command_dispatcher`, and `_agent_configs` are set on the factory instance but never consumed. Every chat request via `POST /chat` (in `chat.py:132,138`) calls `factory.create_loop()`, which means the entire `from_configloader` wiring path produces AgentLoops that operate without profiles, hooks, skills, or the assembled system prompt. This is the core deliverable of this phase and it is non-functional.

**Fix:**
```python
def create_loop(self, context_path: str | None = None) -> AgentLoop:
    ctx = ToolUseContext()
    if self._storage_dir is not None:
        ctx.working_dir = str(self._storage_dir / "shared_workspace")

    # Build system prompt from assembled blocks if assembler is available
    system_prompt = "你是一个有用的助手。可以使用工具来完成任务。"
    profile = getattr(self, "_default_profile", None)
    assembler = getattr(self, "_assembler", None)
    loader = getattr(self, "_loader", None)

    if profile is not None and assembler is not None and loader is not None:
        rendered = assembler.render(loader, profile, context_path=context_path)
        if rendered:
            system_prompt = rendered

    hook_manager = getattr(self, "_hook_manager", None)

    return AgentLoop(
        adapter=self._adapter,
        model=self._model,
        router=self._router,
        ctx=ctx,
        system_prompt=system_prompt,
        profile=profile,
        hook_manager=hook_manager,
    )
```

### CR-02: `ConfigLoader()` in `main.py` uses CWD-relative defaults silently

**File:** `backend/main.py:28`
**Issue:** `ConfigLoader()` is instantiated with no arguments, which means `project_dir` defaults to `Path.cwd() / ".agent-framework"`. When the backend server is started from any directory other than the project root, it will look for `.agent-framework/` in the wrong location. This is a silent misconfiguration -- no error is raised, it simply loads no configuration. In production deployments where the working directory is unpredictable (systemd, Docker, etc.), this will silently produce a factory with empty settings and no profiles/skills/rules.

**Fix:**
```python
from pathlib import Path

# Explicitly resolve project root relative to this file
PROJECT_ROOT = Path(__file__).resolve().parent.parent

@asynccontextmanager
async def lifespan(app: FastAPI):
    config_loader = ConfigLoader(
        project_dir=PROJECT_ROOT,
    )
    # ... rest of lifespan
```

## Warnings

### WR-01: `ALLOWED_ORIGINS` parsing does not strip whitespace

**File:** `backend/main.py:22`
**Issue:** `os.getenv("APP_CORS_ORIGINS", "http://localhost:30001").split(",")` does not strip whitespace from individual origins. If a user configures `APP_CORS_ORIGINS=http://localhost:30001, http://localhost:5173`, the second origin becomes `" http://localhost:5173"` (with leading space), which will not match browser Origin headers, causing silent CORS failures.

**Fix:**
```python
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("APP_CORS_ORIGINS", "http://localhost:30001").split(",") if o.strip()]
```

### WR-02: `_classify_error` maps `asyncio.TimeoutError` to `TOOL_ERROR`

**File:** `backend/app/api/v1/chat.py:63`
**Issue:** `asyncio.TimeoutError` is classified as `ErrorCategory.TOOL_ERROR` with user message "工具执行出错，请检查输入。" This is misleading -- `asyncio.TimeoutError` can occur from any awaitable, not just tool execution (e.g., the LLM call itself might timeout at the asyncio level). The error message blames the user's input when the cause could be infrastructure. This could also mask LLM timeout issues from monitoring since they'd be categorized as tool errors.

**Fix:**
```python
if isinstance(exc, asyncio.TimeoutError):
    return ErrorCategory.LLM_TIMEOUT  # More accurate default
```

### WR-03: `create_settings` hardcodes default model string for comparison

**File:** `backend/app/config/__init__.py:46`
**Issue:** The comparison `framework_settings.model != "claude-sonnet-4-20250514"` uses a hardcoded string to decide whether to pass the framework model as a kwarg. If the framework's default model changes in `Settings`, this comparison will incorrectly skip forwarding the framework value (because it matches the hardcoded string even though it's still a default). The same pattern applies to provider comparison on line 49. This is fragile coupling.

**Fix:** Extract the defaults from the `Settings` class or use a sentinel value rather than duplicating default strings:
```python
_DEFAULTS = Settings.model_fields

def create_settings(framework_settings: FrameworkSettings | None = None) -> Settings:
    if framework_settings is None:
        return Settings()
    kwargs: dict = {}
    # Compare against actual Settings defaults
    if framework_settings.model != Settings.model_fields["llm_model"].default:
        kwargs["llm_model"] = framework_settings.model
    # ... etc
```

## Info

### IN-01: `from_settings` classmethod ignores `storage_dir` wiring for rich initialization

**File:** `backend/app/services/agent_factory.py:37-44`
**Issue:** `from_settings()` only creates a bare factory with LLM adapter. When `storage_dir` is provided, it is stored but `_loader`, `_assembler`, `_default_profile`, `_hook_manager`, etc. are never set as attributes. Code paths that call `create_loop()` after `from_settings()` will hit `AttributeError` if any downstream code tries to access `self._loader` or `self._assembler` (once CR-01 fix is applied). The two factory constructors produce objects with different attribute sets -- a maintenance trap.

**Fix:** Initialize all attributes to `None` in `__init__` so both construction paths produce structurally consistent objects.

### IN-02: E2E test does not verify context_path forwarding through assembler

**File:** `framework/tests/test_e2e_integration.py`
**Issue:** The E2E test (`test_prompt_assembler_full_pipeline`, line 142) calls `assembler.assemble(loader, profile)` without passing `context_path`, so the scoped rule (`Python 文件规则` with `paths: src/**.py`) is excluded. The test asserts `RULES` block contains only `"全局安全规则"` which is correct for `context_path=None`, but there is no E2E test that exercises the full pipeline with a context_path. The unit tests in `test_prompt_assembler.py` cover this (lines 325-369), but the E2E layer has a gap for this critical path-scoped rules feature.

**Fix:** Add an E2E test:
```python
def test_prompt_assembler_with_context_path(self, tmp_path: Path) -> None:
    loader = _setup_framework(tmp_path)
    registry = SkillRegistry.from_loader(loader)
    profile = AgentProfile.from_profile(loader, "default")
    assembler = PromptAssembler(skill_registry=registry)

    blocks = assembler.assemble(loader, profile, context_path="src/main.py")
    rules_block = next(b for b in blocks if b.name == "RULES")
    assert "全局安全规则" in rules_block.content
    assert "Python 文件规则" in rules_block.content
```

---

_Reviewed: 2026-06-12T12:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
