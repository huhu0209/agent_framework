import type { AnimationState } from './types';

/** Canvas dimensions — fixed 4:3 ratio (D-03). */
export const CANVAS_WIDTH = 800;
export const CANVAS_HEIGHT = 600;

/** Named scene positions for the 4 key locations. */
export const POSITIONS = {
  desk1: { x: 200, y: 300 },
  desk2: { x: 400, y: 300 },
  teaRoom: { x: 600, y: 200 },
  door: { x: 750, y: 450 },
} as const;

/** Cat sprite size in pixels (D-07). */
export const CAT_SIZE = 32;

/** Design colours from DESIGN.md — warm parchment palette. */
export const DESIGN_COLORS = {
  PARCHMENT: 0xf5f4ed,
  TERRACOTTA: 0xc96442,
  NEAR_BLACK: 0x141413,
  OLIVE_GRAY: 0x5e5d59,
  WARM_SAND: 0xe8e6dc,
  IVORY: 0xfaf9f5,
  BORDER_CREAM: 0xf0eee6,
} as const;

/** Maps VizEventType to the target AnimationState. */
export const EVENT_TO_STATE: Record<string, AnimationState> = {
  idle: 'idle',
  thinking: 'thinking',
  tool_call: 'tool_call',
  done: 'idle',
  error: 'idle',
  shutdown: 'shutdown',
} as const;
