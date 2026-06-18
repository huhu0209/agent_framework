import '@testing-library/jest-dom/vitest'

// 全局 mock WebSocket：store/组件测试触发 connectInspector 时，
// 避免真实 WS 连接（Node undici WebSocket 在无后端时抛 uncaught error）。
// wsClient.test.ts 在 beforeEach 用更精细的 MockWebSocket 覆盖此 mock。
class _NoopWebSocket {
  static CONNECTING = 0
  static OPEN = 1
  static CLOSING = 2
  static CLOSED = 3
  readyState = _NoopWebSocket.CLOSED
  onopen: (() => void) | null = null
  onmessage: ((e: { data: string }) => void) | null = null
  onclose: (() => void) | null = null
  onerror: (() => void) | null = null
  constructor(_url: string) {}
  send(_data: string) {}
  close() {}
}
;(globalThis as unknown as { WebSocket: typeof WebSocket }).WebSocket =
  _NoopWebSocket as unknown as typeof WebSocket
