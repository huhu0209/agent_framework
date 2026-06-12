---
phase: 09
slug: backend
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-29
---

# Phase 09 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio 1.3.0 |
| **Config file** | framework/pyproject.toml [tool.pytest.ini_options] |
| **Quick run command** | `cd framework && pytest tests/test_event_bus.py tests/test_viz_event.py tests/test_agent_runner.py tests/test_ws_server.py -v` |
| **Full suite command** | `cd framework && pytest tests/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd framework && pytest tests/test_event_bus.py tests/test_viz_event.py tests/test_agent_runner.py tests/test_ws_server.py -v`
- **After every plan wave:** Run `cd framework && pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 09-01-01 | 01 | 1 | EVNT-01 | T-09-04 | Bounded queue prevents DoS | unit | `cd framework && pytest tests/test_event_bus.py -v` | Wave 0 | pending |
| 09-01-01 | 01 | 1 | EVNT-02 | — | N/A | unit | `cd framework && pytest tests/test_event_bus.py -v` | Wave 0 | pending |
| 09-01-01 | 01 | 1 | EVNT-03 | — | N/A | unit | `cd framework && pytest tests/test_event_bus.py -v` | Wave 0 | pending |
| 09-01-01 | 01 | 1 | EVNT-04 | — | N/A | unit | `cd framework && pytest tests/test_viz_event.py -v` | Wave 0 | pending |
| 09-02-01 | 02 | 2 | EVNT-05 | — | N/A | unit | `cd framework && pytest tests/test_agent_runner.py -v` | Wave 0 | pending |
| 09-02-01 | 02 | 2 | EVNT-06 | — | N/A | unit | `cd framework && pytest tests/test_agent_runner.py -v` | Wave 0 | pending |
| 09-02-01 | 02 | 2 | EVNT-07 | — | N/A | unit | `cd framework && pytest tests/test_agent_runner.py -v` | Wave 0 | pending |
| 09-03-01 | 03 | 3 | WSRV-01 | T-09-03 | try/finally unsubscribe prevents leak | integration | `cd framework && pytest tests/test_ws_server.py -v` | Wave 0 | pending |
| 09-03-01 | 03 | 3 | WSRV-02 | T-09-04 | Disconnect cleans up Queue | integration | `cd framework && pytest tests/test_ws_server.py -v` | Wave 0 | pending |
| 09-03-01 | 03 | 3 | WSRV-03 | T-09-01 | JSON decode error handling | integration | `cd framework && pytest tests/test_ws_server.py -v` | Wave 0 | pending |
| 09-03-01 | 03 | 3 | WSRV-04 | T-09-01 | JSON decode error handling | integration | `cd framework && pytest tests/test_ws_server.py -v` | Wave 0 | pending |
| 09-03-01 | 03 | 3 | WSRV-05 | — | Library default ping/pong | integration | `cd framework && pytest tests/test_ws_server.py -v` | Wave 0 | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [ ] `framework/tests/test_event_bus.py` — stubs for EVNT-01, EVNT-02, EVNT-03
- [ ] `framework/tests/test_viz_event.py` — stubs for EVNT-04
- [ ] `framework/tests/test_agent_runner.py` — stubs for EVNT-05, EVNT-06, EVNT-07
- [ ] `framework/tests/test_ws_server.py` — stubs for WSRV-01 through WSRV-05
- [ ] Framework dependency: add `websockets>=14.0` to framework/pyproject.toml

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| None | — | — | — |

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
