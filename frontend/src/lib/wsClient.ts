/**
 * viz WebSocket 客户端：连后端 serve_ws，收 VizEvent 分发到回调，支持重连 + get_snapshot。
 * 浏览器 WS 自动带 Origin（页面 origin），匹配后端白名单（无需手动带，与 wscat 不同）。
 */

export type VizEvent = {
  type: string
  agent: string
  session_id?: string
  payload: Record<string, unknown>
  timestamp: number
}

export type VizEventHandler = (event: VizEvent) => void

const WS_URL = import.meta.env.VITE_WS_URL ?? 'ws://localhost:8765'
const WS_TOKEN = import.meta.env.VITE_WS_TOKEN ?? ''

export class VizWsClient {
  private ws: WebSocket | null = null
  private reconnectAttempt = 0
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private currentSessionId: string | null = null
  private onEvent: VizEventHandler | null = null

  setHandler(handler: VizEventHandler) {
    this.onEvent = handler
  }

  /** 连接并绑定到指定 session（用于 session_id 过滤）。 */
  connect(sessionId: string) {
    this.currentSessionId = sessionId
    this.reconnectAttempt = 0
    this.doConnect()
  }

  private doConnect() {
    if (!this.currentSessionId) return
    const url = WS_TOKEN ? `${WS_URL}?token=${WS_TOKEN}` : WS_URL
    try {
      this.ws = new WebSocket(url)
    } catch {
      this.scheduleReconnect()
      return
    }
    this.ws.onopen = () => {
      this.reconnectAttempt = 0
      // 晚连接：拉快照（config/system_prompt 是启动时发的，可能错过）
      this.send({ type: 'get_snapshot', session_id: this.currentSessionId })
    }
    this.ws.onmessage = (e) => {
      try {
        const ev = JSON.parse(e.data) as VizEvent
        // session_id 过滤：只处理当前会话事件
        if (this.currentSessionId && ev.session_id && ev.session_id !== this.currentSessionId) return
        if (ev.type === 'command_response') return // get_snapshot 的响应，不进面板
        this.onEvent?.(ev)
      } catch {
        // 坏 JSON 忽略
      }
    }
    this.ws.onclose = () => {
      this.ws = null
      this.scheduleReconnect()
    }
    this.ws.onerror = () => {
      this.ws?.close()
    }
  }

  private scheduleReconnect() {
    if (this.reconnectTimer) return
    if (!this.currentSessionId) return // 已 disconnect，不再重连
    const delay = Math.min(1000 * 2 ** this.reconnectAttempt, 30000)
    this.reconnectAttempt++
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null
      this.doConnect()
    }, delay)
  }

  send(cmd: Record<string, unknown>) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(cmd))
    }
  }

  disconnect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    this.currentSessionId = null
    if (this.ws) {
      this.ws.onclose = null // 避免触发重连
      this.ws.close()
      this.ws = null
    }
  }
}

export const vizWs = new VizWsClient()
