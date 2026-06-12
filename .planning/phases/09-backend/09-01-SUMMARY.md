---
phase: 09-backend
plan: 01
status: done
requirements: [EVNT-01, EVNT-02, EVNT-03, EVNT-04]
---

## Plan 09-01 Summary: EventBus + VizEvent 基础设施

**Status:** Done — 14 tests passed, 826 total regression passed.

### Files Created
- `framework/agent_framework/viz/__init__.py` — 模块入口，导出 EventBus/VizEvent/VizEventType
- `framework/agent_framework/viz/event_bus.py` — EventBus pub-sub（subscribe/unsubscribe/publish，有界队列 drop-oldest）
- `framework/agent_framework/viz/viz_event.py` — VizEvent Pydantic model + VizEventType Literal
- `framework/tests/test_event_bus.py` — 5 tests (EVNT-01/02/03)
- `framework/tests/test_viz_event.py` — 9 tests (EVNT-04)

### Files Modified
- `framework/pyproject.toml` — 添加 websockets>=14.0 依赖

### Key Decisions
- EventBus.publish 接受 dict（VizEvent.model_dump() 输出），不依赖 VizEvent 类型
- 有界队列 maxsize=1000 + drop-oldest 策略
- VizEvent 用 Pydantic BaseModel，自带 model_dump_json() 序列化
