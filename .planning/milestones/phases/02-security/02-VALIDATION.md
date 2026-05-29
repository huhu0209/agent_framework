---
phase: 02
slug: security
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-28
---

# Phase 02 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x |
| **Config file** | framework/pyproject.toml |
| **Quick run command** | `cd framework && pytest tests/test_boundary.py tests/test_builtin_tools.py tests/test_mcp_manager.py tests/test_providers.py -v --timeout=30` |
| **Full suite command** | `cd framework && pytest tests/ -v --timeout=60` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run quick run command
- **After every plan wave:** Run full suite command
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | R1 | T-02-01 | safe_path rejects path traversal | unit | `pytest tests/test_builtin_tools.py -v` | ✅ | ⬜ pending |
| 02-01-02 | 01 | 1 | R1 | T-02-02 | env blacklist blocks sensitive keys | unit | `pytest tests/test_mcp_manager.py -v` | ✅ | ⬜ pending |
| 02-02-01 | 02 | 2 | R1 | T-02-04 | _api_key is SecretStr | unit | `pytest tests/test_providers.py -v` | ✅ | ⬜ pending |
| 02-02-02 | 02 | 2 | R1 | — | SECURITY-REVIEW.md generated | automated script | (see plan verify) | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] No Wave 0 scaffolding needed — test files already exist or are created by the tasks themselves

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| SECURITY-REVIEW.md completeness | R1 | Report format review | Verify all 6 security issues documented with severity + fix status |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
