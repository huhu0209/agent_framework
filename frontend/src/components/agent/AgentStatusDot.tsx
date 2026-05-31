/**
 * 8x8px CSS circle colored by agent status.
 *
 * Per D-13: no animation.
 * Colors per UI-SPEC: idle=#22c55e, thinking=#3b82f6, tool_call=#f97316, shutdown=#9ca3af
 */

import type { AgentState } from '../../state/types';

const STATUS_COLORS: Record<AgentState['status'], string> = {
  idle: '#22c55e',
  thinking: '#3b82f6',
  tool_call: '#f97316',
  shutdown: '#9ca3af',
};

interface AgentStatusDotProps {
  status: AgentState['status'];
}

export function AgentStatusDot({ status }: AgentStatusDotProps) {
  return (
    <div
      style={{
        width: '8px',
        height: '8px',
        borderRadius: '50%',
        backgroundColor: STATUS_COLORS[status],
        flexShrink: 0,
      }}
    />
  );
}
