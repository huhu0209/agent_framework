# Performance Audit Report

**Audit Date:** 2026-05-29
**Scope:** `framework/agent_framework/` (full framework layer)
**Auditor:** Performance & data safety review (Phase 04)

---

## Fixed

### PERF-01 (HIGH): MessageBus Inbox Non-Atomic Read-Write

**Description:** `read_inbox` reads the entire JSONL file and immediately writes an empty string back via `path.write_text("")`. This is non-atomic: if the process crashes between the read and the write, all messages are lost with no recovery path. The read-then-clear pattern is a classic data-loss vector.

**File Location:** `framework/agent_framework/teams/bus.py` (lines 33-48)

**Fix:** Replaced direct `write_text("")` with rename-based atomic swap: write empty content to a temporary file via `tempfile.mkstemp`, then `os.replace` the temp file over the original. On `os.replace` failure, logs a warning and returns the already-parsed messages without clearing the file, ensuring no data loss.

**Fix Status:** **FIXED** in Phase 04 (Plan 01). 3 new tests cover atomic swap, crash safety (message retention on failure), and temp file cleanup.

---

### PERF-02 (MEDIUM): MCP Header Byte-by-Byte Read

**Description:** `_read_until_header_end` reads stdout one byte at a time with `read(1)` in a loop until the `\r\n\r\n` terminator is found. Each byte triggers a separate system call and context switch, creating unnecessary overhead for every MCP message received.

**File Location:** `framework/agent_framework/tools/mcp/transport.py` (lines 122-129)

**Fix:** Replaced the `read(1)` loop with `StreamReader.readline()`, which uses an internal read buffer. Each call returns a full line (including `\r\n`), reducing system calls from N-bytes to N-lines per header.

**Fix Status:** **FIXED** in Phase 04 (Plan 01). 3 new tests cover single header, multi-line header, and EOF detection.

---

## Documented Only

### PERF-03 (HIGH): Synchronous File I/O Blocking Async Event Loop

**Description:** The memory subsystem (`log_manager.py`, `index_manager.py`, `semantic_writer.py`, `store.py`) and team bus (`bus.py`) use synchronous `Path.read_text()` / `open()` calls that block the asyncio event loop. Under high I/O load, these calls can stall the entire event loop, blocking all concurrent coroutines.

**File Locations:**
- `framework/agent_framework/memory/log_manager.py` (lines 44-45)
- `framework/agent_framework/teams/bus.py` (lines 26-30)
- `framework/agent_framework/tools/context/result_truncator.py` (line 34)

**Improvement Path:** Wrap synchronous I/O in `asyncio.to_thread()` or migrate to `aiofiles`. The code already documents this limitation in `log_manager.py` lines 3-4.

**Fix Status:** **Documented only.** No immediate data-loss risk, but latency-sensitive deployments should address this.

---

### PERF-04 (MEDIUM): TaskManager Full Directory Scan on Every Query

**Description:** `count_active()`, `_find_in_progress()`, `_load_all()`, and `_clear_dependency()` all scan the entire tasks directory with `glob("task_*.json")` and read each file from disk on every call. No in-memory index is maintained. With `MAX_ACTIVE_TASKS = 12`, the impact is modest, but scaling to hundreds of tasks would make disk I/O the dominant cost.

**File Locations:**
- `framework/agent_framework/tasks/manager.py` (lines 139-146, 158-168)

**Improvement Path:** Maintain an in-memory index of task statuses, updated on write. Sync index to disk periodically or on shutdown.

**Fix Status:** **Documented only.** Current scale (max 12 active tasks) makes this acceptable.

---

### PERF-05 (LOW): Context Compaction Extra LLM Call

**Description:** Every time context compaction triggers, a full LLM call is made via `_generate_summary` to summarize old messages. This adds latency (one round-trip per compaction) and cost (tokens for the summary prompt + response). No caching of previous summaries or incremental summarization exists.

**File Location:** `framework/agent_framework/tools/context/compactor.py` (lines 126-156)

**Improvement Path:** Cache previous summaries and only summarize the delta since last compaction. Alternatively, use a cheaper/smaller model for summarization.

**Fix Status:** **Documented only.** Compaction is infrequent (triggers at 75% context window), and the LLM call is by design.

---

## Summary

| Metric | Count |
|--------|-------|
| Total issues found | 5 |
| Fixed in this phase | 2 (PERF-01, PERF-02) |
| Documented only | 3 (PERF-03, PERF-04, PERF-05) |

**Assessment:** The two most impactful performance issues are resolved. PERF-01 (non-atomic inbox clear) was a data-safety risk that could cause message loss on process crash. PERF-02 (byte-by-byte header parsing) was a latency bottleneck for MCP communication. The three documented-only issues represent architectural improvements that require design work beyond this phase and have clear improvement paths documented above.

---

*Report generated: 2026-05-29*
*Phase: 04-perf-review*
