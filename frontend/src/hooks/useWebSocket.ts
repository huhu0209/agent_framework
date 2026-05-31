/**
 * WebSocket hook with exponential backoff reconnection.
 *
 * Auto-connects on mount, dispatches connection and message events to the
 * reducer, and provides a sendMessage function for sending JSON commands.
 * Cleanup prevents StrictMode double-connection.
 */

import { useEffect, useRef, useCallback } from 'react';
import type { AppAction } from '../state/types';

interface UseWebSocketOptions {
  url: string;
  dispatch: React.Dispatch<AppAction>;
  maxRetries?: number;
  initialDelay?: number;
  maxDelay?: number;
}

export function useWebSocket({
  url,
  dispatch,
  maxRetries = 10,
  initialDelay = 1000,
  maxDelay = 30000,
}: UseWebSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null);
  const retryCountRef = useRef(0);
  const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const connect = useCallback(() => {
    // Clean up old connection
    if (wsRef.current) {
      wsRef.current.onopen = null;
      wsRef.current.onclose = null;
      wsRef.current.onmessage = null;
      wsRef.current.onerror = null;
      if (
        wsRef.current.readyState === WebSocket.OPEN ||
        wsRef.current.readyState === WebSocket.CONNECTING
      ) {
        wsRef.current.close();
      }
    }

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      retryCountRef.current = 0;
      dispatch({ type: 'WS_CONNECTED' });
    };

    ws.onclose = () => {
      dispatch({ type: 'WS_DISCONNECTED' });
      attemptReconnect();
    };

    ws.onerror = () => {
      // onclose fires after onerror — reconnect logic lives in onclose
    };

    ws.onmessage = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data as string);
        if (data.type === 'command_response') {
          dispatch({
            type: 'COMMAND_RESPONSE',
            success: data.success as boolean,
            error: data.error as string | undefined,
          });
        } else {
          dispatch({ type: 'VIZ_EVENT', event: data });
        }
      } catch {
        // Silently ignore unparseable messages
      }
    };
  }, [url, dispatch]);

  const attemptReconnect = useCallback(() => {
    if (retryCountRef.current >= maxRetries) return;

    const delay = Math.min(
      initialDelay * Math.pow(2, retryCountRef.current),
      maxDelay,
    );
    retryCountRef.current += 1;
    dispatch({
      type: 'WS_RECONNECTING',
      retryCount: retryCountRef.current,
    });

    retryTimerRef.current = setTimeout(() => {
      connect();
    }, delay);
  }, [connect, maxRetries, initialDelay, maxDelay, dispatch]);

  const sendMessage = useCallback((data: Record<string, unknown>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  useEffect(() => {
    connect();
    return () => {
      if (retryTimerRef.current) {
        clearTimeout(retryTimerRef.current);
      }
      if (wsRef.current) {
        wsRef.current.onclose = null; // Prevent cleanup-triggered reconnect
        wsRef.current.close();
      }
    };
  }, [connect]);

  return { sendMessage };
}
