---
phase: 24-backend-integration-e2e-wiring-path-scoped-rules
plan: 03
subsystem: backend-integration
tags: [config-loader, agent-factory, e2e-test, fallback-wiring, regression]
dependency_graph:
  requires: [config/loader, rules/loader, prompts/assembler, skills/registry, hooks/manager, commands/dispatcher, agents/config, prompts/profiles]
  provides: [backend/config/create_settings, backend/agent_factory/from_configloader, backend/main/config-loader-init, tests/e2e_integration]
  affects: [backend/main.py, backend/app/config, backend/app/services/agent_factory]
tech_stack:
  added: []
  patterns: [ConfigLoader fallback with selective kwargs, from_configloader() factory, E2E integration test with tmp_path fixtures]
key_files:
  created:
    - framework/tests/test_e2e_integration.py
  modified:
    - backend/app/config/__init__.py
    - backend/app/services/agent_factory.py
    - backend/main.py
decisions:
  - pydantic-settings v2 init kwargs override env vars (not the reverse); create_settings() only passes non-default framework values as kwargs to preserve env var priority
  - from_configloader() stores all module registries as instance attributes for downstream use
  - AgentProfile.from_profile("default") wrapped in try/except ValueError — profile may not exist
metrics:
  duration: 454s
  completed: "2026-06-12"
  tasks: 3
  tests_added: 8
  files_created: 1
  files_modified: 3
---

# Phase 24 Plan 03: Backend Integration + E2E Wiring Summary

Wire backend to ConfigLoader with D-01 selective fallback, add from_configloader() to AgentFactory initializing all module registries, and create 8 E2E integration tests verifying the full pipeline.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add ConfigLoader fallback + from_configloader() + update main.py | a57d05b | backend/app/config/__init__.py, agent_factory.py, main.py |
| 2 | Create E2E integration test | b270a13 | framework/tests/test_e2e_integration.py |
| 3 | Full regression suite verification (INT-05) | N/A | No code changes — 103 tests pass |

## Commits

| Hash | Message |
|------|---------|
| a57d05b | feat(24-03): wire backend to ConfigLoader with D-01 fallback and from_configloader() |
| b270a13 | test(24-03): add E2E integration test for full ConfigLoader pipeline |

## What Was Built

### create_settings() helper (backend/app/config/__init__.py)
- `create_settings(framework_settings)` constructs backend Settings using framework Settings as selective fallback
- Only passes non-default framework values as kwargs to preserve env var priority (pydantic-settings v2: kwargs > env vars > env_file > defaults)
- TYPE_CHECKING guard prevents circular imports
- Existing Settings class and validator unchanged

### AgentFactory.from_configloader() (backend/app/services/agent_factory.py)
- `@classmethod from_configloader(cls, loader, backend_settings)` per D-13
- Creates LLM adapter from backend_settings (env vars already highest priority)
- Initializes all module registries per D-14: SkillRegistry, HookManager, CommandDispatcher, AgentConfig
- Loads default profile with try/except ValueError fallback
- Creates PromptAssembler with skill registry
- Stores loader and all registries as instance attributes
- Existing from_settings() and create_loop() unchanged

### Updated main.py lifespan
- Creates ConfigLoader first per D-02
- Calls config_loader.load_settings() for framework defaults
- Calls create_settings(framework_settings=fw_settings) for backend Settings with fallback
- Creates AgentFactory via from_configloader(config_loader, settings)

### E2E integration test (framework/tests/test_e2e_integration.py, 8 tests)
- test_configloader_loads_settings: ConfigLoader.load_settings() returns Settings from settings.json
- test_configloader_discovers_modules: discover() returns correct module paths
- test_skill_registry_from_loader: SkillRegistry.from_loader() contains test skill
- test_hook_manager_from_loader: HookManager.from_loader() loads hooks.json
- test_agent_profile_from_profile: AgentProfile.from_profile() returns profile with soul and agents
- test_rule_loader_with_scoped_rules: RuleLoader filters by context_path correctly
- test_prompt_assembler_full_pipeline: PromptAssembler produces all expected blocks with content
- test_render_produces_complete_system_prompt: render() produces XML tags in correct order

## Verification

- 8 new E2E tests pass
- 95 existing framework tests pass (103 total, zero regressions)
- Backend import check: create_settings imports without circular dependency
- ConfigLoader fallback wiring verified with env var APP_LLM_API_KEY

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed create_settings() env var priority — pydantic-settings v2 kwargs override env vars**
- **Found during:** Task 3 verification
- **Issue:** Plan claimed "pydantic-settings resolution: kwargs < env_file < env vars" but pydantic-settings v2 actually resolves as kwargs > env vars > env_file > defaults. Passing empty framework API key as kwarg would override the APP_LLM_API_KEY env var, breaking authentication.
- **Fix:** Changed create_settings() to only pass kwargs when framework Settings provides non-default values. Empty/default values are not passed, allowing pydantic-settings to resolve from env vars naturally.
- **Files modified:** backend/app/config/__init__.py
- **Commit:** a57d05b

**2. [Rule 1 - Bug] Fixed hooks.json format in E2E test**
- **Found during:** Task 2 test run
- **Issue:** Test used flat list format for hooks.json but HookManager.load_from_json() expects nested dict format: `{"hooks": {"event": [{"matcher": "...", "hooks": [{"command": "..."}]}]}}`
- **Fix:** Updated test fixture data to match HookManager's expected JSON schema.
- **Files modified:** framework/tests/test_e2e_integration.py
- **Commit:** b270a13

## Known Stubs

None.

## Threat Flags

None — no new security-relevant surface beyond what the threat model covers. ConfigLoader fallback uses selective kwargs to preserve env var priority (T-24-08 mitigated). Backend imports framework only one-way (T-24-07 mitigated via TYPE_CHECKING guard). Zero new packages (T-24-SC).

## Self-Check: PASSED

All 3 modified files verified in commits. All 2 commit hashes verified. All 103 framework tests pass.
