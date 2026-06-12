---
phase: 03-arch-review
created: 2026-05-28
---

# Phase 03: Validation Strategy

## Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 + pytest-asyncio |
| Config file | None (conftest.py only) |
| Quick run command | `cd framework && pytest tests/ -v --timeout=60` |
| Full suite command | `cd framework && pytest tests/ -v --timeout=60` |

## Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | Wave |
|--------|----------|-----------|-------------------|------|
| R3 | ARCH-REVIEW.md exists with required structure | manual | `test -f docs/reviews/ARCH-REVIEW.md && grep -c "HIGH" docs/reviews/ARCH-REVIEW.md` | 0 (new file) |
| R3.5 | base.py has scaffold docstring | unit | `cd framework && python -c "import agent_framework.agents.base; print(agent_framework.agents.base.__doc__)"` | 0 (modify) |
| R3.5 | engine.py has scaffold docstring | unit | `cd framework && python -c "import agent_framework.orchestrator.engine; print(agent_framework.orchestrator.engine.__doc__)"` | 0 (modify) |
| R3.5 | router.py has scaffold docstring | unit | `cd framework && python -c "import agent_framework.orchestrator.router; print(agent_framework.orchestrator.router.__doc__)"` | 0 (modify) |
| Regression | All existing tests still pass | unit | `cd framework && pytest tests/ -v --timeout=60` | Existing |

## Sampling Rate

- **Per task commit:** `cd framework && pytest tests/ -v --timeout=60`
- **Per wave merge:** `cd framework && pytest tests/ -v --timeout=60`
- **Phase gate:** Full suite green + ARCH-REVIEW.md exists with all 5 known issues addressed

## Wave 0 Gaps

- [ ] `docs/reviews/ARCH-REVIEW.md` — covers R3.6
- [ ] Scaffold docstrings in 3 files — covers R3.5
- [ ] No framework install or config needed — already in place
