/**
 * Left-right layout with Canvas placeholder and right panel.
 *
 * Per D-01/D-02:
 * - Top: ConnectionIndicator placeholder bar (32px, Dark Surface)
 * - Left: Canvas container (800x600)
 * - Right: scrollable panel with ConfigForm, TeamControls, AgentList
 */

import { ConfigForm } from '../ui/ConfigForm';
import { TeamControls } from '../ui/TeamControls';
import { AgentList } from '../agent/AgentList';

export function AppLayout() {
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
      {/* Connection indicator bar — placeholder for Plan 11-02 */}
      <div
        style={{
          width: '100%',
          height: '32px',
          backgroundColor: '#30302e',
          display: 'flex',
          alignItems: 'center',
          padding: '0 16px',
          gap: '8px',
          flexShrink: 0,
        }}
      >
        <div
          style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            backgroundColor: '#ef4444',
          }}
        />
        <span
          style={{
            fontSize: '12px',
            fontFamily: 'system-ui',
            color: '#faf9f5',
          }}
        >
          Disconnected
        </span>
      </div>

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
          <TeamControls />
          <AgentList />
        </div>
      </div>
    </div>
  );
}
