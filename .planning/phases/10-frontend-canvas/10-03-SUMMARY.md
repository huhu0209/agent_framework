---
phase: 10-frontend-canvas
plan: 03
subsystem: ui
tags: [pixi.js, canvas, pixijs-v8, typescript, lerp, movement, alpha-fade]

requires:
  - phase: 10-02
    provides: "Cat sprite, animation controller, updateState stub"
provides:
  - "createMovementSystem factory with lerp-based smooth movement (Ticker-driven)"
  - "State-to-position mapping: idle->teaRoom, thinking/tool_call->desk1, shutdown->door"
  - "Full updateState pipeline: state->target position->move with walking animation->arrive->play target animation"
  - "Shutdown sequence: walk to door + alpha fade-out to invisible"
  - "Post-shutdown recovery: restore visibility on next non-shutdown event"
affects: [11-react-bridge]

tech-stack:
  added: []
  patterns: [lerp-interpolation-movement, state-to-position-mapping, alpha-fade-shutdown]

key-files:
  created:
    - frontend/src/canvas/movement.ts
  modified:
    - frontend/src/canvas/index.ts

key-decisions:
  - "MOVE_SPEED = 0.06 provides moderate pace; ARRIVAL_THRESHOLD = 1.0 eliminates float drift"
  - "SAME_POSITION_THRESHOLD = 2px avoids unnecessary movement when already at target"
  - "Shutdown fade uses ticker-driven alpha decrement (0.02 per deltaTime unit)"
  - "Post-shutdown events restore visible=true and alpha=1 before movement"

patterns-established:
  - "MovementSystem as separate module with moveTo/isMoving/dispose API"
  - "onArrive callback pattern for chaining movement->animation transitions"

requirements-completed: [RNDR-05, RNDR-06, RNDR-07]

duration: 2min
completed: 2026-05-30
---

# Phase 10 Plan 03: Movement System Summary

**lerp-based movement system with state-to-position mapping, walking animation during transit, arrival-triggered animation switching, and shutdown door-walk + alpha fade**

## Performance

- **Duration:** 2 min
- **Started:** 2026-05-30T15:45:11Z
- **Completed:** 2026-05-30T15:47:08Z
- **Tasks:** 2 (auto tasks only; checkpoint task 3 skipped for orchestrator handling)
- **Files modified:** 2

## Accomplishments
- Created MovementSystem with lerp interpolation (MOVE_SPEED=0.06, ARRIVAL_THRESHOLD=1.0)
- Implemented state-to-position mapping: idle->teaRoom, thinking/tool_call->desk1, shutdown->door
- Wired full updateState pipeline: walking animation during movement, target animation on arrival
- Implemented shutdown sequence: cat walks to door then alpha fades to invisible
- Post-shutdown events restore visibility (visible=true, alpha=1) before new movement

## Task Commits

Each task was committed atomically:

1. **Task 1: lerp movement system** - `9cee106` (feat)
2. **Task 2: Full updateState pipeline with movement + shutdown fade** - `aaf152c` (feat)

## Files Created/Modified
- `frontend/src/canvas/movement.ts` - MovementSystem interface + createMovementSystem factory (lerp, arrival detection, dispose)
- `frontend/src/canvas/index.ts` - Full updateState pipeline: state mapping, movement trigger, shutdown fade, visibility recovery

## Decisions Made
- MOVE_SPEED = 0.06 provides a moderate, visible walking pace without being too slow
- ARRIVAL_THRESHOLD = 1.0px snaps sprite to exact target to eliminate lerp float drift (per RESEARCH Pitfall 4)
- SAME_POSITION_THRESHOLD = 2px avoids redundant movement+animation when already at target
- Shutdown fade uses 0.02 * deltaTime alpha decrement per frame for smooth ~1-second fade
- Cat visibility restored on any non-shutdown event after shutdown, enabling re-use cycle

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Worktree branch was behind main (missing Phase 10 canvas files from plans 10-01 and 10-02). Resolved by fast-forward merging main into worktree branch before execution began.
- npm dependencies (typescript) needed `npm install` before TypeScript check could run.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Canvas rendering layer fully complete: scene, cat sprite, animations, movement, shutdown
- Phase 11 can integrate via existing init(container)/updateState(event)/destroy() API
- preview.html already has button controls for all event types including shutdown

## Self-Check: PASSED

Both files verified present (movement.ts created, index.ts modified).
Both commits verified in git log (9cee106, aaf152c).

---
*Phase: 10-frontend-canvas*
*Completed: 2026-05-30*
