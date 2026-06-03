export type MessageRole = 'user' | 'agent' | 'system';

export interface ChatMessage {
  id: string;
  role: MessageRole;
  timestamp: number;
  content?: string;
  blocks?: AgentBlock[];
}

export type AgentBlock =
  | { kind: 'thinking'; text: string }
  | { kind: 'tool_call'; toolName: string; params: Record<string, unknown> }
  | { kind: 'tool_result'; content: string }
  | { kind: 'text_response'; text: string };

export interface MockScenario {
  userMessage: string;
  events: AgentBlock[];
  delays: number[];
}
