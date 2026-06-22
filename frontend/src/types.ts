export type MessageRole = 'user' | 'agent' | 'system';

export interface ChatMessage {
  id: string;
  role: MessageRole;
  timestamp: number;
  content?: string;
  blocks?: AgentBlock[];
}

export type AgentBlockKind = 'thinking' | 'tool_call' | 'tool_result' | 'text_response' | 'error'

type BlockBase<K extends AgentBlockKind> = { id: string; kind: K }

export type AgentBlock =
  | BlockBase<'thinking'> & { text: string }
  | BlockBase<'tool_call'> & { toolName: string; params: Record<string, unknown> }
  | BlockBase<'tool_result'> & { content: string }
  | BlockBase<'text_response'> & { text: string }
  | BlockBase<'error'> & { text: string }

export type AgentBlockInit =
  | Omit<Extract<AgentBlock, { kind: 'thinking' }>, 'id'>
  | Omit<Extract<AgentBlock, { kind: 'tool_call' }>, 'id'>
  | Omit<Extract<AgentBlock, { kind: 'tool_result' }>, 'id'>
  | Omit<Extract<AgentBlock, { kind: 'text_response' }>, 'id'>
  | Omit<Extract<AgentBlock, { kind: 'error' }>, 'id'>

export interface VizEvent {
  type: 'idle' | 'thinking' | 'tool_call' | 'tool_result' | 'done' | 'error' | 'shutdown' | 'config' | 'system_prompt' | 'memory' | 'usage'
  agent: string
  session_id?: string
  payload: Record<string, unknown>
  timestamp: number
}

export interface SessionInfo {
  session_id: string
  title: string
  created_at: number
  preview?: ChatMessage[]
  message_count?: number
}

export interface CacheEntry {
  messages: ChatMessage[]
  hasMore: boolean
  cachedAt: number
}

// Inspector 面板状态
export interface ConfigPayload {
  model: string
  max_steps: number
  profile: string | null
  permission_mode: string | null
  tools: string[]
}

export interface PromptBlockPayload {
  name: string
  content: string
  source: string
  stability: string
}

export interface SystemPromptPayload {
  text: string
  blocks: PromptBlockPayload[]
}

export interface UsageState {
  input: number
  output: number
  cumulative_input: number
  cumulative_output: number
  max_context: number
}

export interface ToolCallEntry {
  tool_call_id: string
  tool_name: string
  params: Record<string, unknown>
  content?: string
  source?: string
  step?: number
}

export interface InspectorState {
  config: ConfigPayload | null
  systemPrompt: SystemPromptPayload | null
  toolCalls: ToolCallEntry[]
  usage: UsageState | null
}
