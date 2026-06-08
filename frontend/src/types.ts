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
  type: 'idle' | 'thinking' | 'tool_call' | 'tool_result' | 'done' | 'error' | 'shutdown'
  agent: string
  payload: Record<string, unknown>
  timestamp: number
}
