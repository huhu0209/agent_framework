---
phase: "04-perf-review"
status: clean
reviewer: code-reviewer
date: 2026-05-29
---

# Phase 04 Code Review: Performance & Data Safety

**Files reviewed:**
- `framework/agent_framework/teams/bus.py` (atomic inbox clear via os.replace)
- `framework/agent_framework/tools/mcp/transport.py` (readline replacing read(1))
- `framework/tests/test_teams_bus.py` (3 new atomic tests)
- `framework/tests/test_mcp_transport.py` (3 new header parsing tests)
- `docs/reviews/PERF-REVIEW.md` (performance audit report)

**Test results:** 675/675 passed, 0 regressions.

---

## Atomic Inbox Clear (bus.py)

### Pattern Analysis

The implementation uses `tempfile.mkstemp(dir=self._dir)` to create a temp file in the same directory as the target inbox file, writes empty content via `os.fdopen(fd, "w")`, then atomically replaces the original with `os.replace(tmp_path, path)`. This is the correct atomic-write-via-rename pattern.

**Correctness verified:**
- `mkstemp` uses `dir=self._dir`, ensuring same-filesystem rename (POSIX atomic guarantee).
- `os.fdopen` takes ownership of `fd`, so the file descriptor is closed when the context exits.
- On `os.replace` failure, `os.unlink(tmp_path)` cleans up the temp file.
- The `except BaseException` clause catches `OSError`, `KeyboardInterrupt`, and other interrupting exceptions, ensuring cleanup even on signal interruption.
- When the atomic swap fails, messages are still returned to the caller and the original file remains intact for re-reading on the next call. This is the correct no-data-loss behavior.

### Test Coverage Assessment

Three tests cover the critical paths:

1. `test_read_inbox_atomic_swap` -- verifies the happy path: messages are returned and the inbox file is empty afterward.
2. `test_read_inbox_atomic_no_message_loss_on_failure` -- verifies crash safety: when `os.replace` fails, messages are still returned and remain in the file for re-reading.
3. `test_read_inbox_atomic_cleanup_tempfile` -- verifies temp file cleanup via `os.unlink` when the swap fails.

All three tests are well-structured. The crash-safety test (test 2) is especially important as it validates the core data-safety property: no message loss under failure.

---

## MCP Header Parsing (transport.py)

### Pattern Analysis

The previous `read(1)` byte-by-byte loop has been replaced with `StreamReader.readline()`. Each `readline()` call reads until `\r\n` (or EOF), leveraging the StreamReader's internal buffer. For a typical MCP header like `Content-Length: 42\r\n\r\n`, this reduces from ~30 system calls to exactly 2 (one for the header line, one for the blank line terminator).

**Correctness verified:**
- `readline()` on an `asyncio.StreamReader` splits on `\n`, which includes `\r\n` since `\n` is the delimiter. This correctly handles the MCP protocol's CRLF line endings.
- The `buf.endswith(b"\r\n\r\n")` check correctly detects the header terminator (blank line after the last header).
- EOF detection: `readline()` returns `b""` on EOF, which triggers the `EOFError` raise. Correct.
- The test helper `_make_transport_with_reader` correctly creates a fake process with a `StreamReader`-backed stdout.

### Test Coverage Assessment

Three tests cover the parsing paths:

1. `test_read_until_header_end_single_header` -- single `Content-Length` header with terminator.
2. `test_read_until_header_end_multi_header` -- multiple headers (`Content-Length` + `Custom`) with terminator. Verifies multi-line accumulation.
3. `test_read_until_header_end_eof` -- empty stream raises `EOFError`. Correct.

---

## Issues Found

No CRITICAL or HIGH issues found.

### LOW: Potential fd leak on os.fdopen failure

**File:** `framework/agent_framework/teams/bus.py:58`
**Severity:** LOW

If `os.fdopen(fd, "w", encoding="utf-8")` itself raises an exception (extremely rare -- would require an OS-level fd duplication failure), the raw `fd` from `mkstemp` would leak because it has not yet been transferred to the file object. In practice this is nearly impossible: `os.fdopen` is a thin wrapper around `fdopen(3)` and fails only on EMFILE or similar resource exhaustion.

The `except BaseException` block catches the exception and cleans up the temp file path, but does not close the raw fd. A defensive improvement would be:

```python
fd, tmp_path = tempfile.mkstemp(dir=self._dir, suffix=".tmp", prefix=".inbox_")
try:
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        fd = None  # ownership transferred
        f.write("")
    os.replace(tmp_path, path)
except BaseException:
    if fd is not None:
        os.close(fd)
    try:
        os.unlink(tmp_path)
    except OSError:
        pass
    logger.warning("...")
```

This is a minor robustness improvement, not a correctness bug. Leaving as-is is acceptable.

### LOW: _parse_content_length accepts negative values

**File:** `framework/agent_framework/tools/mcp/transport.py:136`
**Severity:** LOW

`int(line.split(":")[1].strip())` will parse negative values (e.g., `Content-Length: -1`), which would then cause `_read_exact(-1)` to immediately return an empty bytes object. This is a pre-existing issue, not introduced in Phase 4, and is only exploitable by a malicious MCP server. Noted for future hardening.

---

## Approval

**Status: CLEAN** -- No CRITICAL or HIGH issues. Two LOW-severity observations noted above are minor robustness improvements that do not affect correctness or safety.

The atomic write pattern in `bus.py` is correctly implemented with proper same-directory temp file placement, fd ownership transfer, failure-mode cleanup, and no-data-loss guarantees. The `readline()` change in `transport.py` is a clean improvement that correctly handles CRLF line endings. Test coverage is thorough for both changes.
