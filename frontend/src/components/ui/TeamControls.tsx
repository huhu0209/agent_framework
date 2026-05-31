/**
 * Start/Stop Team control buttons.
 *
 * Start: Terracotta bg, disabled when team is running.
 * Stop: Crimson bg, disabled when team is not running.
 * Sends WebSocket commands when sendMessage is provided.
 */

import { useAppState } from '../../state/context';

interface TeamControlsProps {
  sendMessage?: (data: Record<string, unknown>) => void;
}

export function TeamControls({ sendMessage }: TeamControlsProps) {
  const { state, dispatch } = useAppState();

  const handleStart = () => {
    const name = state.formData.name.trim();
    if (!name) {
      return; // Name field empty — no-op
    }
    if (sendMessage) {
      sendMessage({
        type: 'start_team',
        agent: {
          name,
          role: state.formData.role,
          system_prompt: state.formData.systemPrompt,
        },
      });
    }
    dispatch({ type: 'TEAM_STARTED' });
  };

  const handleStop = () => {
    if (sendMessage) {
      sendMessage({
        type: 'stop_team',
        name: state.formData.name,
      });
    }
    dispatch({ type: 'TEAM_STOPPED' });
  };

  return (
    <div style={{ display: 'flex', gap: '8px' }}>
      <button
        type="button"
        disabled={state.isTeamRunning}
        onClick={handleStart}
        style={{
          padding: '8px 16px',
          height: '36px',
          fontSize: '14px',
          fontWeight: 500,
          fontFamily: 'system-ui',
          color: '#faf9f5',
          backgroundColor: '#c96442',
          border: 'none',
          borderRadius: '8px',
          cursor: state.isTeamRunning ? 'not-allowed' : 'pointer',
          opacity: state.isTeamRunning ? 0.5 : 1,
        }}
        onMouseEnter={(e) => {
          if (!e.currentTarget.disabled) {
            e.currentTarget.style.boxShadow =
              '0px 0px 0px 1px #c96442';
          }
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.boxShadow = 'none';
        }}
        onMouseDown={(e) => {
          e.currentTarget.style.boxShadow =
            'inset 0px 0px 0px 1px rgba(201,100,66,0.15)';
        }}
        onMouseUp={(e) => {
          e.currentTarget.style.boxShadow = 'none';
        }}
      >
        Start Team
      </button>
      <button
        type="button"
        disabled={!state.isTeamRunning}
        onClick={handleStop}
        style={{
          padding: '8px 16px',
          height: '36px',
          fontSize: '14px',
          fontWeight: 500,
          fontFamily: 'system-ui',
          color: '#faf9f5',
          backgroundColor: '#b53333',
          border: 'none',
          borderRadius: '8px',
          cursor: !state.isTeamRunning ? 'not-allowed' : 'pointer',
          opacity: !state.isTeamRunning ? 0.5 : 1,
        }}
        onMouseEnter={(e) => {
          if (!e.currentTarget.disabled) {
            e.currentTarget.style.boxShadow =
              '0px 0px 0px 1px #b53333';
          }
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.boxShadow = 'none';
        }}
        onMouseDown={(e) => {
          e.currentTarget.style.boxShadow =
            'inset 0px 0px 0px 1px rgba(181,51,51,0.15)';
        }}
        onMouseUp={(e) => {
          e.currentTarget.style.boxShadow = 'none';
        }}
      >
        Stop Team
      </button>
    </div>
  );
}
