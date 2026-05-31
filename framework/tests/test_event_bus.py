"""EventBus 单元测试 — EVNT-01/02/03。"""

import asyncio

import pytest

from agent_framework.viz.event_bus import EventBus


async def test_subscribe_returns_queue() -> None:
    bus = EventBus()
    q = await bus.subscribe()
    assert isinstance(q, asyncio.Queue)
    assert bus.subscriber_count == 1


async def test_publish_broadcasts_to_all_subscribers() -> None:
    bus = EventBus()
    q1 = await bus.subscribe()
    q2 = await bus.subscribe()

    event = {"type": "thinking", "agent": "cat"}
    await bus.publish(event)

    assert q1.get_nowait() == event
    assert q2.get_nowait() == event


async def test_unsubscribe_removes_queue() -> None:
    bus = EventBus()
    q = await bus.subscribe()
    assert bus.subscriber_count == 1

    await bus.unsubscribe(q)
    assert bus.subscriber_count == 0

    await bus.publish({"type": "done", "agent": "cat"})
    assert q.empty()


async def test_bounded_queue_drops_oldest() -> None:
    bus = EventBus(maxsize=3)
    q = await bus.subscribe()

    for i in range(4):
        await bus.publish({"seq": i})

    items = []
    while not q.empty():
        items.append(q.get_nowait())

    assert len(items) == 3
    assert [item["seq"] for item in items] == [1, 2, 3]


async def test_publish_with_no_subscribers() -> None:
    bus = EventBus()
    await bus.publish({"type": "idle", "agent": "cat"})
