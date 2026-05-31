/**
 * Left-right layout with Canvas placeholder and right panel.
 *
 * Per D-01/D-02:
 * - Top: ConnectionIndicator bar (32px, Dark Surface)
 * - Left: Canvas container (800x600)
 * - Right: scrollable panel with ConfigForm, TeamControls, AgentList
 */

import { useAppState } from '../../state/context';
import { useWebSocket } from '../../hooks/useWebSocket';
import { ConnectionIndicator } from './ConnectionIndicator';
import { ConfigForm } from '../ui/ConfigForm';
import { TeamControls } from '../ui/TeamControls';
import { AgentList } from '../agent/AgentList';

export function AppLayout() {
  const { dispatch } = useAppState();
  const { sendMessage } = useWebSocket({
    url: 'ws://localhost:8765',
    dispatch,
  });

  return (
    <div
      style={{
        width: '100vw',
        height: '100vh',
        display: 'flex',
        flexDirection: 'column',
        backgroundColor: '#f5f4ed',
      }}
    >
      <ConnectionIndicator />

      {/* Main content: canvas + right panel */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* Canvas container — placeholder, Plan 11-03 will integrate canvas.init() */}
        <div
          style={{
            width: '800px',
            height: '600px',
            flexShrink: 0,
            backgroundColor: '#f5f4ed',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '14px',
            fontFamily: 'system-ui',
            color: '#87867f',
          }}
        >
          Canvas (800x600)
        </div>

        {/* Right panel */}
        <div
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: '16px',
            backgroundColor: '#f5f4ed',
            display: 'flex',
            flexDirection: 'column',
            gap: '24px',
          }}
        >
          <ConfigForm />
          <TeamControls sendMessage={sendMessage} />
          <AgentList />
        </div>
      </div>
    </div>
  );
}
