/**
 * Connection status indicator bar.
 *
 * Full-width bar at top of page. 32px tall, Dark Surface background.
 * Shows colored dot + status text for connected/reconnecting/disconnected states.
 * Per UI-SPEC Copywriting Contract.
 */

import { useAppState } from '../../state/context';
import type { ConnectionStatus } from '../../state/types';

const STATUS_DOT_COLORS: Record<ConnectionStatus, string> = {
  connected: '#22c55e',
  reconnecting: '#eab308',
  disconnected: '#ef4444',
};

function getStatusText(status: ConnectionStatus, retryCount: number): string {
  switch (status) {
    case 'connected':
      return 'Connected';
    case 'reconnecting':
      return `Reconnecting (attempt ${retryCount}/10)...`;
    case 'disconnected':
      return 'Unable to connect. Please check the backend server and refresh.';
  }
}

export function ConnectionIndicator() {
  const { state } = useAppState();
  const { status, retryCount } = state.connection;
  const dotColor = STATUS_DOT_COLORS[status];
  const text = getStatusText(status, retryCount);

  return (
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
          backgroundColor: dotColor,
          flexShrink: 0,
        }}
      />
      <span
        style={{
          fontSize: '12px',
          fontFamily: 'system-ui',
          color: '#faf9f5',
          lineHeight: '1.4',
        }}
      >
        {text}
      </span>
    </div>
  );
}
