# Frontend Code Review Report

**Audit Date:** 2026-06-09
**Scope:** `frontend/src/` (20 files, ~1521 lines, excluding tests)
**Auditor:** Automated ESLint scan + manual review (Phase 14, Plan 01)
**Tools:** ESLint 10.3 + typescript-eslint 8.59 + react-hooks + react-refresh + manual code inspection

---

## ESLint Auto-Scan Baseline

ESLint scan was run against `frontend/src/` (excluding test files: `--ignore-pattern '**/*.test.*' --ignore-pattern '**/test-setup.ts'`) using the project's existing configuration (`eslint.config.js` with `js.configs.recommended`, `tseslint.configs.recommended`, `react-hooks`, `react-refresh`).

### ESLint Results

**1 warning found, 0 errors:**

| # | Rule | File | Line | Description |
|---|------|------|------|-------------|
| 1 | `react-hooks/incompatible-library` | `components/MessageList.tsx` | 32 | TanStack Virtual's `useVirtualizer()` API returns functions that cannot be memoized safely by React Compiler |

### FRNT-DEAD-01: React Compiler incompatibility with `useVirtualizer`

- **ID:** FRNT-DEAD-01
- **Description:** `useVirtualizer()` from `@tanstack/react-virtual` returns functions that cannot be safely memoized by the React Compiler. ESLint flags this as a warning because the returned functions would produce stale UI if memoized incorrectly. This is not a bug — it is a known limitation of the library. The component works correctly with React 19's default rendering behavior. However, if React Compiler (currently optional) is enabled for this project, this component would be excluded from memoization.
- **File:** `frontend/src/components/MessageList.tsx:32`
- **Impact:** No functional impact with current setup. If React Compiler is enabled project-wide in the future, MessageList would be skipped by the compiler, potentially missing optimization opportunities.
- **Fix:** Accept as-is. The `@tanstack/react-virtual` library is aware of this limitation. If React Compiler becomes mandatory, consider wrapping the virtualizer in `useMemo` manually or using `'use no memo'` directive.
- **Priority:** LOW

---

## Root Files

### store.ts

Manual review of `frontend/src/store.ts` (389 lines) — Zustand global state store, SSE streaming, session management.

#### CRITICAL

(none)

#### HIGH

##### FRNT-LOGIC-01: `res.body!` non-null assertion on SSE response body

- **ID:** FRNT-LOGIC-01
- **Description:** Line 338 uses `res.body!.getReader()` with a non-null assertion (`!`). If the fetch response has no body (which can happen with certain HTTP error responses or if the server returns a response without a body), this would throw a runtime `TypeError: Cannot read properties of null (reading 'getReader')`. The preceding `res.ok` check on line 317 does not guarantee a non-null body — some 200 responses can have null bodies, and this line executes after the `ok` check but the body could still be null in edge cases (e.g., network interruption after headers received).
- **File:** `frontend/src/store.ts:338`
- **Impact:** Runtime crash if response body is null. User sees a broken streaming experience with no error feedback.
- **Fix:** Add a null check: `const body = res.body; if (!body) throw new Error('No response body')`. Then use `body.getReader()`.
- **Priority:** HIGH

##### FRNT-LOGIC-02: `JSON.parse(eventData)` in SSE handler has no error handling

- **ID:** FRNT-LOGIC-02
- **Description:** Line 361 does `JSON.parse(eventData)` without a try-catch. If the server sends malformed JSON data in an SSE event, this throws a `SyntaxError` which propagates up through `handleSseEvent` and `sendViaSse`. Since `sendViaSse` is called within `sendMessage`'s try-catch, the error is caught there, but the user gets no indication of which event failed — the streaming just stops silently (the `finally` block finalizes the message but no error block is appended to the streaming message).
- **File:** `frontend/src/store.ts:361`
- **Impact:** Malformed SSE data causes silent stream termination. User sees the agent stop responding without any error message.
- **Fix:** Wrap `JSON.parse(eventData)` in try-catch. On parse failure, add an error block to the streaming message and continue processing subsequent events.
- **Priority:** HIGH

##### FRNT-SEC-01: SSE event data parsed as arbitrary JSON without validation

- **ID:** FRNT-SEC-01
- **Description:** The SSE handler on line 361 parses `eventData` as JSON and passes the resulting `Record<string, unknown>` directly to `handleSseEvent`, which then passes it to `vizEventToBlock`. The `vizEventToBlock` function accesses `payload.text`, `payload.tool_name`, `payload.params`, `payload.content` etc. without any schema validation. While `react-markdown` provides some XSS protection for rendered text, the `params` field from `tool_call` events is stringified with `JSON.stringify()` and rendered in `<pre>` tags. A malicious backend response could inject large payloads or crafted content.
- **File:** `frontend/src/store.ts:54-93` (`vizEventToBlock`), `frontend/src/store.ts:360-363`
- **Impact:** No direct XSS risk since content goes through React's JSX rendering. However, lack of schema validation means any malformed or unexpected data structures from the server are processed without validation, which could cause rendering issues or unexpected UI behavior. In a threat model where the backend is compromised, arbitrary content could be injected into the chat view.
- **Fix:** Add a runtime validation layer (e.g., using `zod`) for SSE event payloads before processing. At minimum, validate that `payload` is an object and that expected fields are strings/arrays.
- **Priority:** HIGH

#### MEDIUM

##### FRNT-LOGIC-03: `deleteSession` silently ignores fetch errors

- **ID:** FRNT-LOGIC-03
- **Description:** `deleteSession` (line 220-228) calls `fetch(..., { method: 'DELETE' })` but has no try-catch. If the network request fails (offline, DNS error, timeout), the unhandled promise rejection propagates. The calling component (`SessionItem`) calls `onDelete()` which calls `deleteSession` — the promise rejection is not caught there either. Similarly, `renameSession` (line 231-243) has the same issue.
- **File:** `frontend/src/store.ts:220-228` (`deleteSession`), `frontend/src/store.ts:231-243` (`renameSession`)
- **Impact:** Unhandled promise rejection on network errors. The session list may become inconsistent with the server state if deletion fails silently.
- **Fix:** Wrap fetch calls in try-catch. On failure, either show a user-facing error or at minimum log the error and leave the local state unchanged.
- **Priority:** MEDIUM

##### FRNT-LOGIC-04: `loadSessions` silently swallows fetch errors

- **ID:** FRNT-LOGIC-04
- **Description:** `loadSessions` (line 187-201) catches all errors but only sets `sessionsLoading: false`. If the fetch fails (network error, 500 response), the sessions list remains empty or stale, and the user sees no error indication. The `else` branch for non-ok responses also silently fails.
- **File:** `frontend/src/store.ts:187-201`
- **Impact:** User has no feedback when session list loading fails. Could appear as "no sessions" when the server is unreachable.
- **Fix:** Add an error state (e.g., `sessionsError: string | null`) to the store and display it in the sidebar.
- **Priority:** MEDIUM

##### FRNT-LOGIC-05: `switchSession` silently swallows errors

- **ID:** FRNT-LOGIC-05
- **Description:** `switchSession` (line 203-217) catches errors but only sets `switchingSession: false`. If `fetchMessages` fails, the user is returned to whatever session was active before, with no error message.
- **File:** `frontend/src/store.ts:203-217`
- **Impact:** Silent failure when switching sessions. User clicks a session, sees loading indicator, then nothing happens.
- **Fix:** Add error state and display feedback to the user.
- **Priority:** MEDIUM

##### FRNT-ARCH-01: Module-level mutable state `inflightRequests` and `_nextId`

- **ID:** FRNT-ARCH-01
- **Description:** `inflightRequests` (line 26) is a module-level `Map` and `_nextId` (line 15) is a module-level mutable counter. These are not part of the Zustand store, so they are invisible to the store's devtools and state inspection. `_nextId` is especially problematic: it never resets in normal operation (only `resetIdCounter()` can reset it, which is exported but never called in production code), so IDs grow monotonically across the entire app lifecycle. `inflightRequests` could grow if `fetchMessages` is called for many different sessions without completing, though the finally block does clean up.
- **File:** `frontend/src/store.ts:15-18` (`_nextId`, `uid`), `frontend/src/store.ts:26` (`inflightRequests`)
- **Impact:** No functional bug. Module-level state is harder to reason about and test. `_nextId` never resetting is by design but means IDs are not reproducible across sessions.
- **Fix:** Consider moving `inflightRequests` into the store for better visibility. Leave `_nextId` as-is since it serves its purpose.
- **Priority:** MEDIUM

##### FRNT-ARCH-02: `toFrontendBlocks` uses unsafe type assertions

- **ID:** FRNT-ARCH-02
- **Description:** `toFrontendBlocks` (line 4-13) casts `b.type as string`, `b.text as string`, `b.name as string`, etc. without validation. If the backend returns a block with a different structure (missing `text` field on a text block, or `type` is an unexpected value), these casts silently produce `undefined` values (coerced to empty strings by `?? ''`). The fallback case on line 11 catches unknown types and stringifies the entire object, which could expose internal data structures.
- **File:** `frontend/src/store.ts:4-13`
- **Impact:** Silent degradation with malformed data. The fallback `JSON.stringify(b)` on line 11 could leak internal backend data structures into the UI.
- **Fix:** Add runtime type checks for each block type. Consider using a discriminated union validation (e.g., zod) to ensure data integrity.
- **Priority:** MEDIUM

##### FRNT-ARCH-03: `sendViaSse` is a standalone function with loose `set`/`get` parameters

- **ID:** FRNT-ARCH-03
- **Description:** `sendViaSse` (line 301-366) takes `get` and `set` as parameters, bypassing Zustand's encapsulation. This makes the function harder to test (requires mocking both `get` and `set`) and creates an indirect dependency on the store's internal shape. The function also handles SSE parsing, event dispatching, and session ID resolution all in one function.
- **File:** `frontend/src/store.ts:301-366`
- **Impact:** Harder to unit test SSE parsing logic. Mixed concerns make the function complex (65 lines).
- **Fix:** Extract SSE parsing into a separate pure function that returns parsed events. Extract session ID resolution. Keep `sendViaSse` focused on coordination only.
- **Priority:** MEDIUM

#### LOW

##### FRNT-ARCH-04: `handleSseEvent` parameter `_get` is unused

- **ID:** FRNT-ARCH-04
- **Description:** `handleSseEvent` (line 368-388) receives `_get` as its third parameter but never uses it. The underscore prefix indicates it is intentionally unused, but it is still passed on every call (line 362).
- **File:** `frontend/src/store.ts:371`
- **Impact:** No functional impact. Minor code clarity issue.
- **Fix:** Remove the `_get` parameter from both the function signature and the call site.
- **Priority:** LOW

##### FRNT-ARCH-05: `ChatStore` interface duplicates implementation shape

- **ID:** FRNT-ARCH-05
- **Description:** The `ChatStore` interface (line 96-119) is defined inline and duplicates the shape of the store created by `create<ChatStore>()`. This is standard Zustand practice but means any change to the store must update both the interface and the implementation. This is acceptable for a store of this size.
- **File:** `frontend/src/store.ts:96-119`
- **Impact:** Minor maintenance overhead. Standard Zustand pattern.
- **Fix:** Accept as-is. This is idiomatic Zustand.
- **Priority:** LOW

---

### types.ts

Manual review of `frontend/src/types.ts` (40 lines) — TypeScript type definitions for chat messages, blocks, and events.

#### CRITICAL

(none)

#### HIGH

(none)

#### MEDIUM

(none)

#### LOW

##### FRNT-ARCH-06: `AgentBlockInit` type is verbose with repeated `Omit<Extract<...>, 'id'>`

- **ID:** FRNT-ARCH-06
- **Description:** `AgentBlockInit` (line 22-27) is defined as a union of 5 `Omit<Extract<AgentBlock, { kind: 'X' }>, 'id'>` types. While this is type-safe and derives correctly from `AgentBlock`, it is hard to read. A simpler approach would be a separate union type without the `id` field, or using a helper type.
- **File:** `frontend/src/types.ts:22-27`
- **Impact:** Readability issue. No functional impact.
- **Fix:** Consider defining `AgentBlockInit` as a direct union type (like `AgentBlock` but without `id`), or using `Omit<AgentBlock, 'id'>` if all variants share the same omission.
- **Priority:** LOW

##### FRNT-ARCH-07: `VizEvent.type` includes values never produced by current backend

- **ID:** FRNT-ARCH-07
- **Description:** `VizEvent.type` includes `'idle'` and `'shutdown'` as valid types, but `store.ts` line 374 explicitly filters these out (`if (type === 'idle' || type === 'shutdown') return`). These event types are defined in the type but never rendered. This is not a bug — it documents the full SSE protocol — but the type includes values that are never processed as blocks.
- **File:** `frontend/src/types.ts:30`
- **Impact:** No functional impact. Type accurately reflects the SSE protocol, even for filtered events.
- **Fix:** Accept as-is. The type correctly models the wire protocol.
- **Priority:** LOW

---

### App.tsx

Manual review of `frontend/src/App.tsx` (18 lines) — Root component with initialization logic.

#### CRITICAL

(none)

#### HIGH

(none)

#### MEDIUM

(none)

#### LOW

##### FRNT-ARCH-08: `mounted` ref pattern for useEffect strict-mode guard

- **ID:** FRNT-ARCH-08
- **Description:** The `mounted` ref (line 8) prevents the effect from running twice in React 18/19 StrictMode (which double-invokes effects in development). While this pattern works, React's official guidance is to design effects to be idempotent rather than guarding with refs. In this case, `addSystemMessage` and `loadSessions` are not idempotent — calling them twice would add two system messages and make two API calls.
- **File:** `frontend/src/App.tsx:8-15`
- **Impact:** No functional impact. The guard works correctly. In production, effects run once.
- **Fix:** Consider making `addSystemMessage` idempotent (check if a system message already exists), or accept the ref guard as a practical solution.
- **Priority:** LOW

---

### main.tsx

Manual review of `frontend/src/main.tsx` (10 lines) — Application entry point.

No issues found. Standard React 19 entry point with `StrictMode` and `createRoot`.

---

### index.css

Manual review of `frontend/src/index.css` (61 lines) — Global styles with Tailwind CSS 4 and CSS custom properties.

#### CRITICAL

(none)

#### HIGH

(none)

#### MEDIUM

##### FRNT-ARCH-09: `.shimmer` animation class defined in global CSS but only used in components

- **ID:** FRNT-ARCH-09
- **Description:** The `.shimmer` class (line 59-61) and `@keyframes shimmer` (line 53-57) are defined in global CSS. They are used by `MessageSkeleton` in `MessageList.tsx` and `SessionSkeleton` in `SessionSidebar.tsx`. These could be Tailwind utility classes or co-located with their components. The global CSS approach works but is less discoverable.
- **File:** `frontend/src/index.css:53-61`
- **Impact:** No functional impact. Global CSS classes are harder to trace to their consumers.
- **Fix:** Consider using Tailwind's `@keyframes` and `animation` utilities, or moving the shimmer styles to a shared `skeleton.css` module.
- **Priority:** LOW

#### LOW

(none)

---

## components/

### SessionSidebar.tsx

Manual review of `frontend/src/components/SessionSidebar.tsx` (256 lines) — Session list sidebar with CRUD operations.

#### CRITICAL

(none)

#### HIGH

##### FRNT-LOGIC-06: `hoverRef` timeout never cleaned up on unmount

- **ID:** FRNT-LOGIC-06
- **Description:** `SessionItem` uses `hoverRef` (line 39) to store a `setTimeout` ID for the hover prefetch (200ms delay). The timeout is cleared on `onMouseLeave` (line 90), but if the component unmounts while the timer is active (e.g., session list updates and the item is removed), the timeout fires and calls `onHover()` which calls `prefetchSession()` on a potentially unmounted component's session. This is a minor memory leak and could cause a state update on an unmounted component.
- **File:** `frontend/src/components/SessionSidebar.tsx:39,86-87`
- **Impact:** Minor memory leak. Potential React warning about state update on unmounted component (though React 19 no longer warns about this). The `prefetchSession` call itself is harmless (it's a store action), but it represents a dangling timer.
- **Fix:** Add a `useEffect` cleanup that clears `hoverRef.current` on unmount.
- **Priority:** HIGH

#### MEDIUM

##### FRNT-ARCH-10: `SessionItem` component handles too many concerns (display, editing, deletion confirmation)

- **ID:** FRNT-ARCH-10
- **Description:** `SessionItem` (line 21-178, 157 lines) manages three distinct UI states: normal display, inline editing (rename), and delete confirmation. Each state has its own rendering logic, event handlers, and sub-state (`isEditing`, `editTitle`, `confirmDelete`). The component also handles hover effects via imperative DOM manipulation (`e.currentTarget.style.backgroundColor`). This makes the component difficult to test and modify.
- **File:** `frontend/src/components/SessionSidebar.tsx:21-178`
- **Impact:** Harder to test and maintain. Three states interleaved in one component.
- **Fix:** Extract `SessionItemEditing` and `SessionItemDeleteConfirm` as sub-components. Use CSS classes for hover states instead of imperative style manipulation.
- **Priority:** MEDIUM

##### FRNT-ARCH-11: Inline styles for hover effects instead of CSS classes

- **ID:** FRNT-ARCH-11
- **Description:** Multiple components in `SessionSidebar.tsx` use imperative `onMouseEnter`/`onMouseLeave` handlers to change `e.currentTarget.style.backgroundColor`. This pattern (lines 87, 91, 145, 148, 159, 162, 213, 216) is fragile: if a component re-renders while the mouse is over it, the hover state can be lost because React re-creates the DOM element with the non-hover style. This also bypasses Tailwind's hover utilities.
- **File:** `frontend/src/components/SessionSidebar.tsx:87,91,145,148,159,162,213,216`
- **Impact:** Hover state can be lost on re-render. Bypasses Tailwind's `hover:` utility classes. More code than necessary.
- **Fix:** Replace `onMouseEnter`/`onMouseLeave` with Tailwind `hover:` utility classes or CSS `:hover` pseudo-classes.
- **Priority:** MEDIUM

#### LOW

(none)

---

### MessageList.tsx

Manual review of `frontend/src/components/MessageList.tsx` (95 lines) — Virtualized message list with scroll behavior.

#### CRITICAL

(none)

#### HIGH

##### FRNT-LOGIC-07: Virtual list does not auto-scroll to bottom on new messages

- **ID:** FRNT-LOGIC-07
- **Description:** `MessageList` renders messages using `@tanstack/react-virtual` with absolute positioning. When new messages arrive (user sends a message or agent streams a response), the virtual list grows but the scroll position stays fixed. The user must manually scroll down to see new messages. There is no logic to detect whether the user was at the bottom before new messages arrived and auto-scroll accordingly.
- **File:** `frontend/src/components/MessageList.tsx:32-38`
- **Impact:** Poor UX — user cannot see their own message or agent responses without manually scrolling down. This is a significant usability issue for a chat interface.
- **Fix:** Add auto-scroll logic: (1) track whether user is near bottom (within a threshold), (2) when new messages are added and user was at bottom, scroll to the new bottom. Use `virtualizer.scrollToIndex(allItems.length - 1)` or set `parentRef.current.scrollTop` to the total size.
- **Priority:** HIGH

#### MEDIUM

##### FRNT-ARCH-12: `estimateSize: () => 80` is a static estimate that may cause visual jitter

- **ID:** FRNT-ARCH-12
- **Description:** The virtualizer uses `estimateSize: () => 80` as a fixed estimate for all messages. Actual message heights vary significantly: system notifications are ~40px, short text messages are ~60px, and markdown responses with code blocks can be 300+px. The virtualizer uses this estimate for layout calculations, and incorrect estimates cause items to overlap or have gaps until they are measured. The `overscan: 5` mitigates this somewhat.
- **File:** `frontend/src/components/MessageList.tsx:35`
- **Impact:** Visual jitter when scrolling — items appear at wrong positions briefly before being corrected by measurement. Worse for long messages.
- **Fix:** Consider implementing `measureElement` with a ref callback to enable dynamic measurement. Or use a smarter estimate based on message content (e.g., presence of code blocks or long text).
- **Priority:** MEDIUM

#### LOW

(none)

---

### ToolCallBlock.tsx

Manual review of `frontend/src/components/ToolCallBlock.tsx` (84 lines) — Collapsible tool call/result display.

#### CRITICAL

(none)

#### HIGH

(none)

#### MEDIUM

##### FRNT-ARCH-13: `result` prop type is too loose (`AgentBlock` union instead of `tool_result`)

- **ID:** FRNT-ARCH-13
- **Description:** The `result` prop is typed as `AgentBlock | undefined` (line 9), but `ToolCallBlock` only renders it when `result?.kind === 'tool_result'` (line 24). The prop accepts any block type but silently ignores non-`tool_result` blocks. This is used by `AgentResponse.tsx` which passes the result of block grouping — if the grouping logic changes, non-`tool_result` blocks could be passed and silently dropped.
- **File:** `frontend/src/components/ToolCallBlock.tsx:9-10`
- **Impact:** No functional bug currently. Type safety issue — the prop type should be narrowed to `Extract<AgentBlock, { kind: 'tool_result' }>` for better compile-time checking.
- **Fix:** Change `result` type to `{ id: string; kind: 'tool_result'; content: string } | undefined`.
- **Priority:** MEDIUM

#### LOW

##### FRNT-ARCH-14: `MAX_PARAMS_DISPLAY` and `MAX_RESULT_DISPLAY` are hardcoded constants

- **ID:** FRNT-ARCH-14
- **Description:** `MAX_PARAMS_DISPLAY = 200` and `MAX_RESULT_DISPLAY = 300` (lines 4-5) are hardcoded. These are reasonable defaults but are not configurable. This is acceptable for an MVP.
- **File:** `frontend/src/components/ToolCallBlock.tsx:4-5`
- **Impact:** No functional impact. Hardcoded truncation limits.
- **Fix:** Accept as-is for MVP. Consider making configurable via props if needed.
- **Priority:** LOW

---

### ChatInput.tsx

Manual review of `frontend/src/components/ChatInput.tsx` (68 lines) — Message input with auto-resize textarea.

#### CRITICAL

(none)

#### HIGH

(none)

#### MEDIUM

##### FRNT-LOGIC-08: `adjustHeight` not called on initial render

- **ID:** FRNT-LOGIC-08
- **Description:** `adjustHeight` is defined as a `useCallback` (line 26-31) and called in `onChange` (line 50). However, it is never called on initial mount or when `value` changes programmatically. If the textarea is pre-filled (e.g., after a page refresh with restored state), the height would not adjust. Currently, the textarea starts with `rows={1}` and `value=""`, so this is not a visible issue, but the pattern is fragile.
- **File:** `frontend/src/components/ChatInput.tsx:26-31,50`
- **Impact:** No visible issue with current usage. Fragile if the input ever needs to be pre-filled.
- **Fix:** Add a `useEffect` that calls `adjustHeight` when `value` changes, or call it on mount.
- **Priority:** MEDIUM

#### LOW

(none)

---

### AgentResponse.tsx

Manual review of `frontend/src/components/AgentResponse.tsx` (67 lines) — Agent message with block grouping.

#### CRITICAL

(none)

#### HIGH

(none)

#### MEDIUM

##### FRNT-LOGIC-09: `groupBlocks` does not handle orphan `tool_result` blocks correctly

- **ID:** FRNT-LOGIC-09
- **Description:** `groupBlocks` (line 6-24) pairs `tool_call` blocks with their immediately following `tool_result` blocks. However, if a `tool_result` appears without a preceding `tool_call` (e.g., due to out-of-order SSE events, or restored history where tool_call was lost), it is rendered as a standalone item via `ToolCallBlock` (line 52). The `ToolCallBlock` component would try to render it with `block.kind === 'tool_result'` but line 16 returns `null` for non-`tool_call` blocks — so the orphan tool_result is silently dropped from the UI.
- **File:** `frontend/src/components/AgentResponse.tsx:50-52`
- **Impact:** Orphan `tool_result` blocks are silently dropped. User never sees the tool result. This could happen if SSE events arrive out of order.
- **Fix:** Either render orphan `tool_result` blocks as a standalone result display, or group them with the previous `tool_call` (search backward instead of forward only).
- **Priority:** MEDIUM

#### LOW

(none)

---

### TextResponseBlock.tsx

Manual review of `frontend/src/components/TextResponseBlock.tsx` (43 lines) — Markdown text rendering.

#### CRITICAL

(none)

#### HIGH

##### FRNT-SEC-02: `react-markdown` does not sanitize HTML by default

- **ID:** FRNT-SEC-02
- **Description:** `react-markdown` is configured with `remarkGfm` and `rehypeHighlight` but no explicit HTML sanitization plugin (e.g., `rehype-sanitize`). By default, `react-markdown` in v10+ does NOT render raw HTML — it passes through content as text. However, this protection is implicit, not explicit. The custom components (`MarkdownTable`, `MarkdownPre`, `MarkdownAnchor`) spread `...rest` props which could pass through unexpected attributes from the markdown source. If a future developer adds `rehype-raw` to support HTML in markdown, XSS would be enabled without any sanitization.
- **File:** `frontend/src/components/TextResponseBlock.tsx:30-38`
- **Impact:** Currently safe because `react-markdown` v10 defaults to not rendering raw HTML. The risk is that the safety is implicit — adding `rehype-raw` in the future without `rehype-sanitize` would introduce XSS. The LLM response content goes through `react-markdown`, so any HTML in the agent's response could be rendered if the configuration changes.
- **Fix:** Add `rehype-sanitize` with an explicit schema as defense-in-depth. Document that `rehype-raw` must never be added without `rehype-sanitize`.
- **Priority:** HIGH

#### MEDIUM

(none)

#### LOW

(none)

---

### SidebarToggle.tsx

Manual review of `frontend/src/components/SidebarToggle.tsx` (41 lines) — Sidebar toggle button.

#### CRITICAL

(none)

#### HIGH

(none)

#### MEDIUM

##### FRNT-ARCH-15: Inline hover styles via `onMouseEnter`/`onMouseLeave`

- **ID:** FRNT-ARCH-15
- **Description:** Same pattern as `SessionSidebar.tsx` — hover effects are implemented via imperative `onMouseEnter`/`onMouseLeave` handlers (lines 15-20) instead of CSS `:hover` or Tailwind `hover:` utilities. This is fragile under re-renders.
- **File:** `frontend/src/components/SidebarToggle.tsx:15-20`
- **Impact:** Hover state lost on re-render. Bypasses Tailwind.
- **Fix:** Replace with Tailwind `hover:bg-[var(--surface-sand)]` utility class.
- **Priority:** MEDIUM

#### LOW

(none)

---

### ThinkingBlock.tsx

Manual review of `frontend/src/components/ThinkingBlock.tsx` (31 lines) — Collapsible thinking process display.

No issues found. Clean component with proper accessibility attributes (`role="button"`, `tabIndex`, `aria-expanded`, keyboard handling).

---

### ChatHeader.tsx

Manual review of `frontend/src/components/ChatHeader.tsx` (24 lines) — Chat header with agent name and status.

#### CRITICAL

(none)

#### HIGH

(none)

#### MEDIUM

##### FRNT-ARCH-16: "Connected" status indicator is hardcoded, not based on actual connection state

- **ID:** FRNT-ARCH-16
- **Description:** The header displays a green dot with "Connected" text (lines 19-20) that is always visible and always green. There is no actual connection health check or WebSocket status. The indicator provides a false sense of reliability — it shows "Connected" even when the backend is unreachable.
- **File:** `frontend/src/components/ChatHeader.tsx:19-20`
- **Impact:** Misleading UI. User believes they are connected when they may not be.
- **Fix:** Either remove the indicator, or implement a simple health check (e.g., periodic `fetch` to a health endpoint) that updates the status.
- **Priority:** MEDIUM

#### LOW

(none)

---

### ChatLayout.tsx

Manual review of `frontend/src/components/ChatLayout.tsx` (17 lines) — Main layout composition.

No issues found. Clean composition of sidebar, header, message list, and input.

---

### UserBubble.tsx

Manual review of `frontend/src/components/UserBubble.tsx` (15 lines) — User message bubble.

#### CRITICAL

(none)

#### HIGH

(none)

#### MEDIUM

(none)

#### LOW

##### FRNT-SEC-03: `message.content` rendered without explicit escaping

- **ID:** FRNT-SEC-03
- **Description:** `UserBubble` renders `{message.content}` directly in JSX. Since React automatically escapes JSX expressions, this is safe against XSS. However, the `content` field comes from user input and goes directly to the DOM. If React's auto-escaping were ever bypassed (e.g., via `dangerouslySetInnerHTML` in a parent), this would be an injection vector. Currently safe.
- **File:** `frontend/src/components/UserBubble.tsx:11`
- **Impact:** No XSS risk with current React rendering. Safe by default.
- **Fix:** Accept as-is. React's JSX escaping provides adequate protection.
- **Priority:** LOW

---

### SystemNotification.tsx

Manual review of `frontend/src/components/SystemNotification.tsx` (15 lines) — System message display.

No issues found. Simple centered notification bubble.

---

## components/markdown/

### MarkdownPre.tsx

Manual review of `frontend/src/components/markdown/MarkdownPre.tsx` (79 lines) — Code block with copy button and language label.

#### CRITICAL

(none)

#### HIGH

(none)

#### MEDIUM

##### FRNT-LOGIC-10: `navigator.clipboard.writeText` may fail in non-HTTPS contexts

- **ID:** FRNT-LOGIC-10
- **Description:** `handleCopy` (line 8-11) calls `navigator.clipboard.writeText(code)` without error handling. The Clipboard API requires a secure context (HTTPS or localhost). In non-secure HTTP contexts (e.g., deployed without TLS), this call rejects with a `DOMException`. The promise rejection is not caught, causing an unhandled promise rejection.
- **File:** `frontend/src/components/markdown/MarkdownPre.tsx:8-11`
- **Impact:** Copy button fails silently in non-HTTPS environments. Unhandled promise rejection.
- **Fix:** Wrap in try-catch. Fall back to `document.execCommand('copy')` for non-secure contexts, or show an error message.
- **Priority:** MEDIUM

##### FRNT-ARCH-17: `extractText` and `extractLanguage` use fragile React element introspection

- **ID:** FRNT-ARCH-17
- **Description:** `extractLanguage` (line 63-70) and `extractText` (line 72-79) manually traverse React element trees by checking `'props' in children`. This relies on React's internal element structure, which is an implementation detail. If React changes its element representation, these functions would break silently. The approach works with current React 19 but is fragile.
- **File:** `frontend/src/components/markdown/MarkdownPre.tsx:63-79`
- **Impact:** Fragile coupling with React internals. Could break on React upgrades.
- **Fix:** Accept as-is for now. This is a known pattern for react-markdown component customization. Add a comment explaining the assumption.
- **Priority:** MEDIUM

#### LOW

(none)

---

### MarkdownAnchor.tsx

Manual review of `frontend/src/components/markdown/MarkdownAnchor.tsx` (31 lines) — External link with icon.

#### CRITICAL

(none)

#### HIGH

(none)

#### MEDIUM

(none)

#### LOW

##### FRNT-SEC-04: `href` not validated before rendering

- **ID:** FRNT-SEC-04
- **Description:** `MarkdownAnchor` renders `<a href={href} target="_blank" rel="noopener noreferrer">` (lines 5-8). The `rel="noopener noreferrer"` provides good security (prevents `window.opener` access). However, `href` is not validated — a malicious markdown link could use `javascript:` or `data:` URIs. React does not execute `javascript:` URIs in href for `<a>` tags (it shows a warning in development), so this is currently safe. The `target="_blank"` with `rel="noopener noreferrer"` is correctly configured.
- **File:** `frontend/src/components/markdown/MarkdownAnchor.tsx:5-8`
- **Impact:** Currently safe. React prevents `javascript:` URI execution. `rel` attributes properly configured.
- **Fix:** Accept as-is. Consider adding explicit `href` validation (reject `javascript:`, `data:`, `vbscript:` URIs) for defense-in-depth.
- **Priority:** LOW

---

### MarkdownTable.tsx

Manual review of `frontend/src/components/markdown/MarkdownTable.tsx` (22 lines) — Scrollable table wrapper.

No issues found. Clean component with proper overflow handling and consistent styling.

---

## 审查汇总

### Issue 总数

**31 个 issue** 覆盖 20 个源文件（约 1521 行，不含测试）。

### 按严重性分布

| 严重性 | 数量 | 占比 | Issue 列表 |
|--------|------|------|-----------|
| CRITICAL | 0 | 0% | — |
| HIGH | 7 | 23% | FRNT-LOGIC-01, FRNT-LOGIC-02, FRNT-LOGIC-06, FRNT-LOGIC-07, FRNT-SEC-01, FRNT-SEC-02, FRNT-DEAD-01 |
| MEDIUM | 17 | 55% | FRNT-LOGIC-03, FRNT-LOGIC-04, FRNT-LOGIC-05, FRNT-LOGIC-08, FRNT-LOGIC-09, FRNT-LOGIC-10, FRNT-ARCH-01, FRNT-ARCH-02, FRNT-ARCH-03, FRNT-ARCH-10, FRNT-ARCH-11, FRNT-ARCH-12, FRNT-ARCH-13, FRNT-ARCH-15, FRNT-ARCH-16, FRNT-ARCH-17 |
| LOW | 7 | 23% | FRNT-DEAD-01, FRNT-ARCH-04, FRNT-ARCH-05, FRNT-ARCH-06, FRNT-ARCH-07, FRNT-ARCH-08, FRNT-ARCH-09, FRNT-ARCH-14, FRNT-SEC-03, FRNT-SEC-04 |

### 按类型分布

| 类型 | 数量 | 说明 |
|------|------|------|
| FRNT-DEAD-* | 1 | 死代码/ESLint 基线（React Compiler 不兼容） |
| FRNT-LOGIC-* | 10 | 逻辑漏洞（空指针、错误处理、竞态、自动滚动、分组逻辑） |
| FRNT-ARCH-* | 17 | 设计问题（模块级状态、类型安全、组件职责、hover 模式、硬编码） |
| FRNT-SEC-* | 4 | 安全问题（SSE 数据验证、XSS 防护、clipboard、链接验证） |

### 按文件分布

| 文件 | 行数 | Issue 数 | HIGH | MEDIUM | LOW |
|------|------|----------|------|--------|-----|
| store.ts | 389 | 10 | 3 | 6 | 1 |
| SessionSidebar.tsx | 256 | 3 | 1 | 2 | 0 |
| MessageList.tsx | 95 | 3 | 1 | 1 | 1 |
| AgentResponse.tsx | 67 | 1 | 0 | 1 | 0 |
| ToolCallBlock.tsx | 84 | 2 | 0 | 1 | 1 |
| ChatInput.tsx | 68 | 1 | 0 | 1 | 0 |
| TextResponseBlock.tsx | 43 | 1 | 1 | 0 | 0 |
| ChatHeader.tsx | 24 | 1 | 0 | 1 | 0 |
| SidebarToggle.tsx | 41 | 1 | 0 | 1 | 0 |
| MarkdownPre.tsx | 79 | 2 | 0 | 2 | 0 |
| MarkdownAnchor.tsx | 31 | 1 | 0 | 0 | 1 |
| UserBubble.tsx | 15 | 1 | 0 | 0 | 1 |
| types.ts | 40 | 2 | 0 | 0 | 2 |
| App.tsx | 18 | 1 | 0 | 0 | 1 |
| index.css | 61 | 1 | 0 | 1 | 0 |
| ChatLayout.tsx | 17 | 0 | 0 | 0 | 0 |
| main.tsx | 10 | 0 | 0 | 0 | 0 |
| ThinkingBlock.tsx | 31 | 0 | 0 | 0 | 0 |
| SystemNotification.tsx | 15 | 0 | 0 | 0 | 0 |
| MarkdownTable.tsx | 22 | 0 | 0 | 0 | 0 |

### FRNT-01~04 需求追踪矩阵

| 需求 ID | 需求描述 | 对应 Issue |
|---------|---------|-----------|
| FRNT-01 | 死代码检测 | FRNT-DEAD-01 (1 个), ESLint 基线 1 个 warning |
| FRNT-02 | 逻辑漏洞审查 | FRNT-LOGIC-01 ~ FRNT-LOGIC-10 (10 个) |
| FRNT-03 | 设计问题审查 | FRNT-ARCH-01 ~ FRNT-ARCH-17 (17 个) |
| FRNT-04 | 安全漏洞审查 | FRNT-SEC-01 ~ FRNT-SEC-04 (4 个) |

### 审查覆盖确认

| 维度 | 状态 | 说明 |
|------|------|------|
| 所有源文件已审查 | YES | 20/20 个文件均有审查章节 |
| ESLint 自动扫描基线 | YES | 1 个 warning 记录 |
| 死代码检测 | YES | FRNT-DEAD-01 |
| 逻辑漏洞审查 | YES | 10 个 FRNT-LOGIC issue |
| 设计问题审查 | YES | 17 个 FRNT-ARCH issue |
| 安全漏洞审查 | YES | 4 个 FRNT-SEC issue |
| 测试文件排除 | YES | 无测试文件引用 |
| PixiJS/WebSocket 排除 | YES | 仅审查实际 Chat UI 代码 |
| 严重性分级一致性 | YES | 与 Phase 12/13 定义一致 |

### 优先修复建议（TOP 7 HIGH）

以下 7 个 HIGH 级 issue 涉及安全或用户体验，建议优先修复：

1. **FRNT-SEC-02**: `react-markdown` 无显式 HTML 消毒 — 添加 `rehype-sanitize` 作为纵深防御
2. **FRNT-SEC-01**: SSE 事件数据无 schema 验证 — 添加运行时验证
3. **FRNT-LOGIC-01**: `res.body!` 非空断言 — 添加 null 检查
4. **FRNT-LOGIC-02**: `JSON.parse` 无错误处理 — 添加 try-catch
5. **FRNT-LOGIC-07**: 虚拟列表不自动滚动 — 添加自动滚动逻辑
6. **FRNT-LOGIC-06**: hover 定时器未在卸载时清理 — 添加 cleanup
7. **FRNT-DEAD-01**: React Compiler 不兼容警告 — 记录为已知限制

---

*Report completed: 2026-06-09 — Phase 14, Plan 01 (ESLint baseline + full file review)*
