/**
 * Pure reducer for the Agent visualization panel state.
 *
 * Every case returns a new object — no mutation.
 */

import type { AppState, AppAction, AgentState } from './types';

const MAX_LOG_ENTRIES = 50;

function mapEventTypeToAgentStatus(
  type: string,
): AgentState['status'] {
  switch (type) {
    case 'idle':
      return 'idle';
    case 'thinking':
      return 'thinking';
    case 'tool_call':
      return 'tool_call';
    case 'shutdown':
      return 'shutdown';
    default:
      return 'idle';
  }
}

export function appReducer(state: AppState, action: AppAction): AppState {
  switch (action.type) {
    case 'WS_CONNECTED':
      return {
        ...state,
        connection: { status: 'connected', retryCount: 0 },
      };

    case 'WS_DISCONNECTED':
      return {
        ...state,
        connection: { ...state.connection, status: 'disconnected' },
        isTeamRunning: false,
      };

    case 'WS_RECONNECTING':
      return {
        ...state,
        connection: {
          status: 'reconnecting',
          retryCount: action.retryCount,
        },
      };

    case 'VIZ_EVENT': {
      const event = action.event;
      const newAgents = new Map(state.agents);
      newAgents.set(event.agent, {
        name: event.agent,
        status: mapEventTypeToAgentStatus(event.type),
        lastEvent: event,
      });

      const newLog = [...state.eventLog, event].slice(-MAX_LOG_ENTRIES);

      return { ...state, agents: newAgents, eventLog: newLog };
    }

    case 'COMMAND_RESPONSE':
      return state;

    case 'UPDATE_FORM':
      return {
        ...state,
        formData: { ...state.formData, [action.field]: action.value },
      };

    case 'TEAM_STARTED':
      return { ...state, isTeamRunning: true };

    case 'TEAM_STOPPED':
      return { ...state, isTeamRunning: false };
  }
}

export const initialAppState: AppState = {
  connection: { status: 'disconnected', retryCount: 0 },
  agents: new Map(),
  eventLog: [],
  formData: { name: '', role: '', systemPrompt: '' },
  isTeamRunning: false,
};
