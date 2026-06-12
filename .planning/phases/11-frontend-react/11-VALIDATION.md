---
phase: 11
slug: frontend-react-integration
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-31
---

# Phase 11 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | TypeScript compiler (tsc) + Vite build |
| **Config file** | frontend/tsconfig.app.json + frontend/vite.config.ts |
| **Quick run command** | `cd frontend && npx tsc -b --noEmit` |
| **Full suite command** | `cd frontend && npx tsc -b --noEmit && npx vite build` |
| **Estimated runtime** | ~5 seconds |

> Note: Frontend unit tests (Vitest) are explicitly deferred per REQUIREMENTS.md Out of Scope: "前端单元测试 — 第一期验证端到端链路，测试以后补". Validation for Phase 11 relies on TypeScript type checking and Vite build success as automated gates, plus manual end-to-end verification.

---

## Sampling Rate

- **After every task commit:** Run `cd frontend && npx tsc -b --noEmit`
- **After every plan wave:** Run `cd frontend && npx tsc -b --noEmit && npx vite build`
- **Before `/gsd:verify-work`:** Build must be green + manual e2e demo
- **Max feedback latency:** ~5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------------|-----------|-------------------|-------------|--------|
| 11-01-01 | 01 | 1 | CONC-02 | N/A | build | `cd frontend && npx tsc -b --noEmit` | ❌ W0 | ⬜ pending |
| 11-01-02 | 01 | 1 | CNFG-01, CNFG-04 | N/A | build | `cd frontend && npx tsc -b --noEmit` | ❌ W0 | ⬜ pending |
| 11-02-01 | 02 | 1 | CONC-01, CONC-02, CONC-04 | N/A | build | `cd frontend && npx tsc -b --noEmit` | ❌ W0 | ⬜ pending |
| 11-03-01 | 03 | 2 | CONC-03, CONC-05, CNFG-02, CNFG-03 | N/A | build | `cd frontend && npx tsc -b --noEmit && npx vite build` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `frontend/tsconfig.app.json` — TypeScript config exists (verbatimModuleSyntax, erasableSyntaxOnly)
- [x] `frontend/vite.config.ts` — Vite build config exists (React + Tailwind plugins)

*Existing infrastructure covers all phase build-time requirements. Unit test framework (Vitest) deferred to v0.0.4+ per REQUIREMENTS.md.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| React-PixiJS bridge renders Canvas in layout | CONC-03 | PixiJS requires real DOM + Canvas | 1. `cd frontend && npm run dev` 2. Open browser 3. Verify 800x600 Canvas renders with office scene |
| WebSocket connects and receives events | CONC-01 | Requires running backend WebSocket server | 1. Start backend 2. Open frontend 3. Verify connection indicator shows green 4. Start team 5. Verify events appear in log |
| ConfigForm creates Agent | CNFG-01 | End-to-end form → WebSocket → backend flow | 1. Fill Name/Role 2. Click Start Team 3. Verify agent appears in AgentList with status dot |
| EventLog shows real-time events | CONC-05 | Requires live WebSocket event stream | 1. Start team 2. Observe events appearing in log 3. Verify auto-scroll and 50-entry limit |
| Canvas updates on VizEvent | CONC-03 | PixiJS visual rendering | 1. Start team 2. Observe cat sprite moving and animating on status change |

---

## Validation Sign-Off

- [x] All tasks have automated build verify or manual verification specified
- [x] Sampling continuity: every task has tsc build check
- [x] Wave 0 covers all MISSING references — no missing infrastructure
- [x] No watch-mode flags
- [x] Feedback latency < 5s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
