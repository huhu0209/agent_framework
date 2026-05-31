/**
 * State types for the Agent visualization panel.
 *
 * Constraints:
 *   - verbatimModuleSyntax: use `import type` for type-only imports
 *   - erasableSyntaxOnly: no `enum`, use union types
 */

import type { VizEvent } from '../canvas/types';

export type ConnectionStatus = 'connected' | 'reconnecting' | 'disconnected';

export interface AgentState {
  name: string;
  status: 'idle' | 'thinking' | 'tool_call' | 'shutdown';
  lastEvent: VizEvent | null;
}

export interface AppState {
  connection: {
    status: ConnectionStatus;
    retryCount: number;
  };
  agents: Map<string, AgentState>;
  eventLog: VizEvent[];
  formData: {
    name: string;
    role: string;
    systemPrompt: string;
  };
  isTeamRunning: boolean;
}

export type AppAction =
  | { type: 'WS_CONNECTED' }
  | { type: 'WS_DISCONNECTED' }
  | { type: 'WS_RECONNECTING'; retryCount: number }
  | { type: 'VIZ_EVENT'; event: VizEvent }
  | { type: 'COMMAND_RESPONSE'; success: boolean; error?: string }
  | { type: 'UPDATE_FORM'; field: string; value: string }
  | { type: 'TEAM_STARTED' }
  | { type: 'TEAM_STOPPED' };
