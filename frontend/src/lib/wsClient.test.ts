import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { vizWs } from './wsClient'

// jsdom 无原生 WebSocket，构造最小 mock（异步触发 onopen 模拟连接成功）
class MockWebSocket {
  // 对齐浏览器 WebSocket readyState 常量（send 守卫用 WebSocket.OPEN 比较）
  static CONNECTING = 0
  static OPEN = 1
  static CLOSING = 2
  static CLOSED = 3
  static instances: MockWebSocket[] = []
  readyState = 0 // CONNECTING
  onopen: (() => void) | null = null
  onmessage: ((e: { data: string }) => void) | null = null
  onclose: (() => void) | null = null
  onerror: (() => void) | null = null
  sent: string[] = []
  url: string
  constructor(url: string) {
    this.url = url
    MockWebSocket.instances.push(this)
    // 异步触发 onopen 模拟连接成功
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN
      this.onopen?.()
    }, 0)
  }
  send(data: string) {
    this.sent.push(data)
  }
  close() {
    this.readyState = MockWebSocket.CLOSED
    this.onclose?.()
  }
}

describe('VizWsClient', () => {
  beforeEach(() => {
    MockWebSocket.instances = []
    ;(globalThis as unknown as { WebSocket: typeof WebSocket }).WebSocket =
      MockWebSocket as unknown as typeof WebSocket
    vi.useFakeTimers()
  })
  afterEach(() => {
    vizWs.disconnect()
    vi.useRealTimers()
  })

  it('connect 后 onopen 发 get_snapshot', async () => {
    vizWs.connect('sid-1')
    await vi.runAllTimersAsync()
    const ws = MockWebSocket.instances[0]
    expect(ws).toBeTruthy()
    const snapshotCall = ws.sent.find((s) => s.includes('get_snapshot'))
    expect(snapshotCall).toBeTruthy()
    expect(snapshotCall).toContain('sid-1')
  })

  it('过滤非当前 session 的事件', async () => {
    const handler = vi.fn()
    vizWs.setHandler(handler)
    vizWs.connect('sid-1')
    await vi.runAllTimersAsync()
    const ws = MockWebSocket.instances[0]
    // 别的 session 事件 → handler 不调用
    ws.onmessage?.({
      data: JSON.stringify({
        type: 'config',
        agent: 'a',
        session_id: 'other',
        payload: {},
        timestamp: 0,
      }),
    })
    expect(handler).not.toHaveBeenCalled()
    // 当前 session 事件 → handler 调用
    ws.onmessage?.({
      data: JSON.stringify({
        type: 'config',
        agent: 'a',
        session_id: 'sid-1',
        payload: { model: 'm' },
        timestamp: 0,
      }),
    })
    expect(handler).toHaveBeenCalledTimes(1)
  })

  it('disconnect 后 onclose 不触发重连', async () => {
    vizWs.connect('sid-1')
    await vi.runAllTimersAsync()
    expect(MockWebSocket.instances).toHaveLength(1)
    vizWs.disconnect()
    // 推进足够长时间，确认没有新建 WebSocket（即无重连）
    await vi.advanceTimersByTimeAsync(60000)
    expect(MockWebSocket.instances).toHaveLength(1)
  })

  it('onopen 置 connected，非主动 onclose 置 connecting', async () => {
    const statuses: string[] = []
    vizWs.setOnStatus((s) => statuses.push(s))
    vizWs.connect('sid-1')
    await vi.runAllTimersAsync() // 触发 onopen
    expect(statuses).toContain('connecting')
    expect(statuses).toContain('connected')
    // 模拟非主动关闭（如服务端断开）→ 进入重连
    MockWebSocket.instances[0]!.onclose?.()
    expect(statuses[statuses.length - 1]).toBe('connecting')
  })

  it('disconnect 主动断开置 disconnected', async () => {
    const statuses: string[] = []
    vizWs.setOnStatus((s) => statuses.push(s))
    vizWs.connect('sid-1')
    await vi.runAllTimersAsync()
    vizWs.disconnect()
    expect(statuses[statuses.length - 1]).toBe('disconnected')
  })

  it('重复 connect 同 session 且 OPEN 幂等', async () => {
    vizWs.connect('sid-1')
    await vi.runAllTimersAsync()
    vizWs.connect('sid-1') // 已 OPEN，跳过
    expect(MockWebSocket.instances).toHaveLength(1)
  })
})
