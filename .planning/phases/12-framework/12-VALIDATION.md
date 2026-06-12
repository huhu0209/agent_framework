---
phase: 12
slug: framework
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-09
---

# Phase 12 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `framework/pyproject.toml` |
| **Quick run command** | `cd framework && pytest tests/ -x -q` |
| **Full suite command** | `cd framework && pytest tests/ -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd framework && pytest tests/ -x -q`
- **After every plan wave:** Run `cd framework && pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 12-01-01 | 01 | 1 | FRMW-01 | — | N/A (review only) | manual | `ruff check framework/agent_framework/` | ✅ | ⬜ pending |
| 12-02-01 | 02 | 2 | FRMW-02 | T-12-01~06 | review output | manual | `cd framework && pytest tests/ -v` | ✅ | ⬜ pending |
| 12-03-01 | 03 | 2 | FRMW-03 | — | N/A (review only) | manual | `cd framework && pytest tests/ -v` | ✅ | ⬜ pending |
| 12-04-01 | 04 | 2 | FRMW-04 | T-12-01~06 | review output | manual | `cd framework && pytest tests/ -v` | ✅ | ⬜ pending |
| 12-05-01 | 05 | 3 | FRMW-05 | — | N/A (report only) | manual | `test -f docs/reviews/REVIEW-FRAMEWORK.md` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `framework/pyproject.toml` — test infrastructure exists
- [x] `ruff` installed at `/Users/huhu/.local/bin/ruff`
- [x] Existing test suite: 964 tests passing

*Existing infrastructure covers all phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Dead code detection completeness | FRMW-01 | Requires human judgment on "unused vs. public API" | Compare ruff output against public API surface |
| Logic review coverage | FRMW-02 | Requires human code reading | Verify every module has a chapter in report |
| Design pattern assessment | FRMW-03 | Subjective evaluation | Cross-reference with CONVENTIONS.md |
| Security issue discovery | FRMW-04 | Requires threat modeling | Cross-reference with CONCERNS.md security items |
| Report quality | FRMW-05 | Requires document review | Verify all 4 dimensions covered, CRITICAL/HIGH have fix suggestions |

---

## Validation Sign-Off

- [x] All tasks have verification commands or manual verifications
- [x] Sampling continuity: no 3 consecutive tasks without verification
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
