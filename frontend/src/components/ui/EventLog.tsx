/**
 * Scrollable event log with timestamp, event type badge, and agent name.
 *
 * Fixed-height (256px) container, auto-scrolls to bottom, renders empty
 * state per Copywriting Contract when no events.
 * Max 50 entries enforced by reducer — this component renders what it receives.
 */

import { useEffect, useRef } from 'react';
import { useAppState } from '../../state/context';
import type { VizEventType } from '../../canvas/types';

const BADGE_COLORS: Record<VizEventType, { bg: string; text: string }> = {
  thinking: { bg: '#dbeafe', text: '#1d4ed8' },
  tool_call: { bg: '#ffedd5', text: '#c2410c' },
  idle: { bg: '#dcfce7', text: '#15803d' },
  done: { bg: '#dcfce7', text: '#15803d' },
  error: { bg: '#fef2f2', text: '#b53333' },
  shutdown: { bg: '#f3f4f6', text: '#6b7280' },
};

export function EventLog() {
  const { state } = useAppState();
  const { eventLog } = state;
  const scrollRef = useRef<HTMLDivElement>(null);
  const prevLengthRef = useRef(0);

  useEffect(() => {
    if (eventLog.length > prevLengthRef.current && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
    prevLengthRef.current = eventLog.length;
  }, [eventLog.length]);

  if (eventLog.length === 0) {
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
          Event Log
        </h2>
        <p
          style={{
            fontSize: '14px',
            fontWeight: 600,
            fontFamily: 'system-ui',
            color: '#141413',
            margin: 0,
          }}
        >
          Waiting for events
        </p>
        <p
          style={{
            fontSize: '14px',
            fontFamily: 'system-ui',
            color: '#5e5d59',
            margin: '4px 0 0',
          }}
        >
          Events will appear here once the team is running.
        </p>
      </div>
    );
  }

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
        Event Log
      </h2>
      <div
        ref={scrollRef}
        style={{
          height: '256px',
          overflowY: 'auto',
          padding: '12px',
          backgroundColor: '#faf9f5',
          border: '1px solid #f0eee6',
          borderRadius: '12px',
        }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          {eventLog.map((event, index) => {
            const badge = BADGE_COLORS[event.type];
            const timestamp = new Date(event.timestamp).toLocaleTimeString(
              'en-GB',
            );

            return (
              <div
                key={`${event.timestamp}-${index}`}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '4px 0',
                }}
              >
                <span
                  style={{
                    fontSize: '12px',
                    fontFamily: 'system-ui',
                    color: '#87867f',
                    flexShrink: 0,
                  }}
                >
                  {timestamp}
                </span>
                <span
                  style={{
                    fontSize: '12px',
                    fontFamily: 'system-ui',
                    backgroundColor: badge.bg,
                    color: badge.text,
                    padding: '2px 6px',
                    borderRadius: '4px',
                    flexShrink: 0,
                  }}
                >
                  {event.type}
                </span>
                <span
                  style={{
                    fontSize: '14px',
                    fontFamily: 'system-ui',
                    fontWeight: 400,
                    color: '#141413',
                  }}
                >
                  {event.agent}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
