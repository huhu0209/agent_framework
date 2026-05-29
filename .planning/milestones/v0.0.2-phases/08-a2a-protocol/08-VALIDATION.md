---
phase: 08
slug: a2a-protocol
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-29
---

# Phase 08 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio 1.3.0 |
| **Config file** | framework/pyproject.toml ([tool.pytest.ini_options]) |
| **Quick run command** | `cd framework && pytest tests/test_a2a_*.py -v -x` |
| **Full suite command** | `cd framework && pytest tests/ -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd framework && pytest tests/test_a2a_*.py -v -x`
- **After every plan wave:** Run `cd framework && pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 08-01-01 | 01 | 1 | A2A-01 | T-08-04 | N/A | unit | `pytest tests/test_a2a_models.py -v -x` | ❌ W0 | ⬜ pending |
| 08-01-02 | 01 | 1 | A2A-01 | — | N/A | unit | `pytest tests/test_a2a_models.py -k agent_card -v` | ❌ W0 | ⬜ pending |
| 08-01-03 | 01 | 1 | A2A-02 | — | N/A | unit | `pytest tests/test_a2a_models.py -k task -v` | ❌ W0 | ⬜ pending |
| 08-02-01 | 02 | 2 | A2A-04 | T-08-01 | 认证中间件验证每个请求 | unit | `pytest tests/test_a2a_server.py -v -x` | ❌ W0 | ⬜ pending |
| 08-02-02 | 02 | 2 | A2A-03 | T-08-05 | N/A | unit | `pytest tests/test_a2a_client.py -v -x` | ❌ W0 | ⬜ pending |
| 08-02-03 | 02 | 2 | A2A-05 | — | N/A | unit | `pytest tests/test_a2a_client.py -k wait -v` | ❌ W0 | ⬜ pending |
| 08-03-01 | 03 | 2 | A2A-06 | T-08-01 | 有效 key 通过，无效/缺失 key 被拒 | unit | `pytest tests/test_a2a_server.py -k auth -v` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `framework/tests/test_a2a_models.py` — stubs for A2A-01, A2A-02
- [ ] `framework/tests/test_a2a_client.py` — stubs for A2A-03, A2A-05
- [ ] `framework/tests/test_a2a_server.py` — stubs for A2A-04, A2A-06

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| None | — | — | All phase behaviors have automated verification. |

---

## Validation Sign-Off

- [ ] All tasks have automated verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter
