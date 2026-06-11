---
phase: 21-discovery-loader-agents-md-chain
reviewed: 2026-06-11T19:45:00Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - framework/agent_framework/config/__init__.py
  - framework/agent_framework/config/loader.py
  - framework/tests/test_loader.py
  - framework/tests/test_settings.py
findings:
  critical: 1
  warning: 2
  info: 1
  total: 4
status: issues_found
---

# Phase 21: Code Review Report

**Reviewed:** 2026-06-11T19:45:00Z
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found

## Summary

Reviewed 4 files: the config barrel export, the ConfigLoader with discover/load_settings/load_agents_md/load_profile implementations, and two test files. The code is well-structured with thorough test coverage. Found one security vulnerability (path traversal in `load_profile`), one missing error handling gap, and minor quality issues.

## Critical Issues

### CR-01: Path Traversal in `load_profile`

**File:** `framework/agent_framework/config/loader.py:178-189`
**Issue:** The `name` parameter in `load_profile(name)` is used directly in path construction without sanitization. A caller passing `name="../../../../../../../etc"` would cause `_read_text_file` to read arbitrary files on the filesystem. The resolved path becomes:
```
/home/user/.agent-framework/profiles/../../../../../../../etc/passwd
```
This resolves to `/etc/passwd` (or any other file reachable by path traversal).

While the current callers may use trusted values, `load_profile` is a public method on a public class. Any future caller, plugin, or API endpoint that passes user-controlled input to this method introduces a file read vulnerability.

**Fix:**
```python
def load_profile(self, name: str) -> dict[str, str]:
    # Reject path traversal characters in profile name
    if "/" in name or "\\" in name or ".." in name:
        raise ValueError(f"Invalid profile name: {name}")

    result: dict[str, str] = {}
    global_profile_dir = self._global_dir / "profiles" / name
    # ... rest of method
```

Alternatively, validate that the resolved path stays within the profiles directory:
```python
import os

def _safe_profile_dir(self, base: Path, name: str) -> Path:
    resolved = (base / "profiles" / name).resolve()
    profiles_root = (base / "profiles").resolve()
    if not resolved.is_relative_to(profiles_root):
        raise ValueError(f"Invalid profile name: {name}")
    return resolved
```

## Warnings

### WR-01: `load_settings` Does Not Handle Pydantic `ValidationError`

**File:** `framework/agent_framework/config/loader.py:76-87`
**Issue:** `load_settings` calls `Settings.model_validate(final)` at line 87, but does not catch `pydantic.ValidationError`. If a user provides an invalid configuration value (e.g., `APP_SERVER__PORT=abc` as an environment variable), the raw Pydantic validation error propagates to the caller with no context about which config file or environment variable caused the problem. The method already wraps `JSONDecodeError` into a user-friendly `ValueError` (lines 71-74), but leaves `ValidationError` unwrapped.

**Fix:**
```python
from pydantic import ValidationError

def load_settings(self) -> Settings:
    global_cfg = self._read_json(self._global_dir / "settings.json")
    project_cfg = self._read_json(self._project_dir / "settings.json")
    local_cfg = self._read_json(self._project_dir / "settings.local.json")
    merged = merge_settings(global_cfg, project_cfg, local_cfg)
    final = apply_env_vars(merged, dict(os.environ))
    try:
        return Settings.model_validate(final)
    except ValidationError as exc:
        raise ValueError(
            f"配置校验失败: {exc}"
        ) from exc
```

### WR-02: `_read_json` Does Not Handle Non-JSON File Errors

**File:** `framework/agent_framework/config/loader.py:61-74`
**Issue:** `_read_json` catches `json.JSONDecodeError` but lets other I/O errors (e.g., `PermissionError`, `UnicodeDecodeError`) propagate unhandled. While this is arguably acceptable (unexpected errors should propagate), `PermissionError` is a plausible scenario when config files exist but are not readable by the current user. The caller `load_settings` does not catch these either, so a permission-denied error on a config file would bubble up as a raw `PermissionError` with no context about which config loading step failed.

**Fix:** Either catch `OSError` in `_read_json` and wrap it with a contextual error message, or document that callers must handle I/O errors.

```python
def _read_json(self, path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        text = path.read_text(encoding="utf-8")
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"配置文件格式错误: {path}") from exc
    except OSError as exc:
        raise ValueError(f"无法读取配置文件: {path}") from exc
```

## Info

### IN-01: Duplicate `_make_loader` Helper in Test File

**File:** `framework/tests/test_loader.py:41-47,129-135,240-247`
**Issue:** The `_make_loader` helper method is defined identically in three separate test classes (`TestLoadSettings`, `TestDiscover`, `TestLoadAgentsMd`). The implementations in `TestLoadSettings` and `TestDiscover` are character-for-character identical. `TestLoadAgentsMd` has a slightly different signature (accepting optional `global_dir`/`project_dir` overrides). Consider extracting a shared `pytest.fixture` or base class to reduce duplication.

**Fix:** Extract a module-level fixture:
```python
@pytest.fixture
def make_loader(tmp_path: Path):
    global_base = tmp_path / "global"
    project_base = tmp_path / "project"
    global_base.mkdir()
    project_base.mkdir()
    return ConfigLoader(global_dir=global_base, project_dir=project_base)
```

---

_Reviewed: 2026-06-11T19:45:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
