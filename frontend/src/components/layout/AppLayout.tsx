/**
 * Left-right layout with Canvas bridge and right panel.
 *
 * Per D-01/D-02:
 * - Top: ConnectionIndicator bar (32px, Dark Surface)
 * - Left: Canvas container (800x600) via PixiJS imperative bridge
 * - Right: scrollable panel with ConfigForm, TeamControls, AgentList, EventLog
 */

import { useEffect, useRef } from 'react';
import { useAppState } from '../../state/context';
import { useWebSocket } from '../../hooks/useWebSocket';
import { ConnectionIndicator } from './ConnectionIndicator';
import { ConfigForm } from '../ui/ConfigForm';
import { TeamControls } from '../ui/TeamControls';
import { AgentList } from '../agent/AgentList';
import { EventLog } from '../ui/EventLog';
import {
  init as canvasInit,
  updateState as canvasUpdateState,
  destroy as canvasDestroy,
} from '../../canvas/index';
import type { VizEvent } from '../../canvas/types';

/**
 * CanvasContainer — imperative PixiJS bridge.
 *
 * Uses refs to avoid re-render driving PixiJS. Processes only new events
 * via lastProcessedIndex. Cleans up on unmount (StrictMode safe).
 */
function CanvasContainer({ events }: { events: readonly VizEvent[] }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const lastProcessedIndex = useRef(0);
  const isInitialized = useRef(false);

  // Initialize Canvas — runs once per mount cycle
  useEffect(() => {
    const container = containerRef.current;
    if (!container || isInitialized.current) {
      return;
    }

    isInitialized.current = true;
    canvasInit(container, { width: 800, height: 600 });

    return () => {
      canvasDestroy();
      isInitialized.current = false;
      lastProcessedIndex.current = 0;
    };
  }, []);

  // Process new events incrementally
  useEffect(() => {
    for (let i = lastProcessedIndex.current; i < events.length; i++) {
      canvasUpdateState(events[i]);
    }
    lastProcessedIndex.current = events.length;
  }, [events]);

  return (
    <div
      ref={containerRef}
      style={{ width: 800, height: 600 }}
      className="flex-shrink-0"
    />
  );
}

export function AppLayout() {
  const { state, dispatch } = useAppState();
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
        {/* Canvas — PixiJS bridge via useRef */}
        <CanvasContainer events={state.eventLog} />

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
          <EventLog />
        </div>
      </div>
    </div>
  );
}
