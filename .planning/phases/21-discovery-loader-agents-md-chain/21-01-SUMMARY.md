---
phase: 21-discovery-loader-agents-md-chain
plan: 01
subsystem: config
tags: [config, loader, discovery, override-chain, tdd]
dependency_graph:
  requires:
    - "Phase 20: Settings model + merge_settings() + apply_env_vars()"
  provides:
    - "ConfigLoader class with load_settings() and discover()"
    - "MODULE_DIRS constant for 8 module types"
  affects:
    - "framework/agent_framework/config/__init__.py (barrel export)"
    - "Phase 22-24 downstream consumers of ConfigLoader"
tech_stack:
  added: []
  patterns: [constructor-injection, leaf-dependency, barrel-export]
key_files:
  created:
    - framework/agent_framework/config/loader.py
    - framework/tests/test_loader.py
  modified:
    - framework/agent_framework/config/__init__.py
    - framework/tests/test_settings.py
decisions:
  - "load_settings() has no caching, reloads on every call (D-01)"
  - "discover() returns pure list[Path], caller iterates (D-02)"
  - "settings.local.json auto-attempted in project dir (D-03)"
  - "ConfigLoader constructor uses optional Path params with defaults (D-04)"
  - "Unknown module type raises ValueError via MODULE_DIRS whitelist (D-12, D-13)"
  - "JSON format errors raise ValueError with file path (Claude's Discretion)"
  - "load_profile() is placeholder stub for Phase 21-02"
metrics:
  duration: "2 minutes"
  completed_date: "2026-06-11"
  task_count: 1
  file_count: 4
  test_count: 17 new (55 total config tests)
---

# Phase 21 Plan 01: ConfigLoader + Discovery Summary

ConfigLoader 统一入口类，实现四级覆盖链 load_settings() 和 8 种模块类型 discover() 路径发现。

## What Was Built

### ConfigLoader (loader.py)
- **`load_settings()`**: 四级覆盖链 (global -> project -> local -> env) 加载 settings.json，通过 merge_settings() 合并、apply_env_vars() 注入环境变量、Settings.model_validate() 创建实例
- **`discover(module_name)`**: 从 MODULE_DIRS 查找子目录名，返回 [global_dir, project_dir] 中存在的目录路径列表，按低到高优先级排列
- **`_read_json(path)`**: 文件不存在返回 {}，JSON 格式错误 raise ValueError 含文件路径
- **`load_profile(name)`**: 占位 stub，Phase 21-02 实现
- **`MODULE_DIRS`**: 8 种模块类型映射 (skills/agents/commands/hooks/rules/profiles/memory/mcp)

### Barrel Export Update (__init__.py)
- 添加 ConfigLoader 到 __all__ 导出列表

## Test Coverage

| Test Class | Tests | Coverage |
|------------|-------|----------|
| TestConfigLoaderConstruction | 3 | Default and custom path construction |
| TestLoadSettings | 5 | No-config defaults, global override, 4-level chain, env var override, JSON error |
| TestDiscover | 6 | Both/one/none exist, unknown type, all 8 types, file-not-dir skip |
| TestLeafDependency | 1 | No non-config framework imports |
| TestBarrelExport | 2 | ConfigLoader in __all__, importable from barrel |

## TDD Gate Compliance

- RED: `e5c8aae` - test(21-01): add failing tests for ConfigLoader, discover, load_settings
- GREEN: `5b3eaa7` - feat(21-01): implement ConfigLoader with 4-level override chain and module discovery

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] test_settings.py barrel export test needed update**
- **Found during:** GREEN verification
- **Issue:** test_settings.py::TestLeafDependency::test_barrel_exports_all_symbols expected exact set of symbols without ConfigLoader
- **Fix:** Added ConfigLoader to the expected set in test_settings.py
- **Files modified:** framework/tests/test_settings.py
- **Commit:** 5b3eaa7

**2. [Rule 3 - Blocking] framework/tests/ directory not in worktree**
- **Found during:** Task 1 setup
- **Issue:** .gitignore excludes framework/tests/ from git tracking; worktree had no test infrastructure
- **Fix:** Copied existing test files (test_settings.py, test_merge.py, conftest.py, helpers.py, __init__.py) to worktree for test execution. Only new test_loader.py force-added to git.
- **Files modified:** N/A (local worktree files, not committed)
- **Commit:** e5c8aae (test_loader.py only)

None of the deviations alter the public API or behavior specified in the plan.

## Verification Results

1. `pytest tests/test_loader.py -v` -- 17/17 passed
2. `pytest tests/test_settings.py tests/test_merge.py tests/test_loader.py -v` -- 55/55 passed
3. `python -c "from agent_framework.config import ConfigLoader; print('import OK')"` -- OK
4. `grep -r "from agent_framework\." loader.py | grep -v "from agent_framework\.config\."` -- no output (leaf dependency OK)

## Threat Flags

No new threat surface beyond plan's threat_model. All mitigations implemented:
- T-21-01: JSONDecodeError caught and re-raised as ValueError with file path
- T-21-03: discover() uses MODULE_DIRS whitelist, only operates within _global_dir/_project_dir subdirectories

## Self-Check: PASSED

- FOUND: framework/agent_framework/config/loader.py
- FOUND: framework/tests/test_loader.py
- FOUND: .planning/phases/21-discovery-loader-agents-md-chain/21-01-SUMMARY.md
- FOUND: e5c8aae (RED commit)
- FOUND: 5b3eaa7 (GREEN commit)
