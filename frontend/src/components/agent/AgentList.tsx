/**
 * Vertical list of agents with status dots and names.
 *
 * Empty state per Copywriting Contract when no agents.
 * Rows separated by 1px Border Cream top border.
 */

import { useAppState } from '../../state/context';
import { AgentStatusDot } from './AgentStatusDot';

export function AgentList() {
  const { state } = useAppState();
  const agents = Array.from(state.agents.values());

  return (
    <div>
      <h2
        style={{
          fontSize: '16px',
          fontWeight: 600,
          fontFamily: 'system-ui',
          color: '#141413',
          marginBottom: '8px',
        }}
      >
        Agent Status
      </h2>

      {agents.length === 0 ? (
        <div>
          <p
            style={{
              fontSize: '14px',
              fontWeight: 600,
              fontFamily: 'system-ui',
              color: '#141413',
              margin: 0,
            }}
          >
            No agents yet
          </p>
          <p
            style={{
              fontSize: '14px',
              fontFamily: 'system-ui',
              color: '#5e5d59',
              margin: '4px 0 0',
            }}
          >
            Configure an agent above and start the team.
          </p>
        </div>
      ) : (
        <div>
          {agents.map((agent) => (
            <div
              key={agent.name}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '8px 0',
                borderTop: '1px solid #f0eee6',
              }}
            >
              <AgentStatusDot status={agent.status} />
              <span
                style={{
                  fontSize: '14px',
                  fontFamily: 'system-ui',
                  color: '#141413',
                }}
              >
                {agent.name}
              </span>
              <span
                style={{
                  fontSize: '12px',
                  fontFamily: 'system-ui',
                  color: '#87867f',
                  marginLeft: 'auto',
                }}
              >
                {agent.status}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
