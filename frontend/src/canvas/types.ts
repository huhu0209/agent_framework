/**
 * VizEvent types — mirrors the Python VizEvent model from
 * framework/agent_framework/viz/viz_event.py
 */

/** Event types emitted by the backend visualization system. */
export type VizEventType =
  | 'idle'
  | 'thinking'
  | 'tool_call'
  | 'done'
  | 'error'
  | 'shutdown';

/** A single visualization event from the backend. */
export interface VizEvent {
  type: VizEventType;
  agent: string;
  payload: Record<string, unknown>;
  timestamp: number;
}

/** Internal animation states for the cat sprite. */
export type AnimationState =
  | 'idle'
  | 'thinking'
  | 'tool_call'
  | 'moving'
  | 'shutdown';
