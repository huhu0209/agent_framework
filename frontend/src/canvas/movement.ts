/**
 * Movement system — lerp-based smooth movement for the cat sprite.
 *
 * Uses PixiJS v8 Ticker to interpolate sprite position toward a target.
 * Fires an onArrive callback when the sprite reaches the destination.
 *
 * v8 Ticker callback signature: (ticker: Ticker) => void
 * Use ticker.deltaTime for frame-relative timing.
 */
import { Container } from 'pixi.js';
import type { Application, Ticker } from 'pixi.js';

/** Speed factor for lerp interpolation (higher = faster). */
const MOVE_SPEED = 0.06;

/** Distance threshold to snap to target and fire onArrive (per RESEARCH Pitfall 4). */
const ARRIVAL_THRESHOLD = 1.0;

/** Public interface for the movement system. */
export interface MovementSystem {
  /** Start moving toward (x, y). Optional callback fires on arrival. */
  moveTo(x: number, y: number, onArrive?: () => void): void;
  /** Whether the sprite is currently moving toward a target. */
  readonly isMoving: boolean;
  /** Clean up the ticker callback. */
  dispose(): void;
}

/**
 * Create a movement system that lerps the sprite toward targets each frame.
 *
 * Lerp formula: current + (target - current) * speed * deltaTime
 */
export function createMovementSystem(
  sprite: Container,
  app: Application,
): MovementSystem {
  let targetX = 0;
  let targetY = 0;
  let moving = false;
  let onArriveCallback: (() => void) | undefined;

  const tickerFn = (ticker: Ticker): void => {
    if (!moving) {
      return;
    }

    const dt = ticker.deltaTime;
    sprite.x += (targetX - sprite.x) * MOVE_SPEED * dt;
    sprite.y += (targetY - sprite.y) * MOVE_SPEED * dt;

    const distance = Math.hypot(targetX - sprite.x, targetY - sprite.y);

    if (distance < ARRIVAL_THRESHOLD) {
      // Snap to exact target to eliminate residual error
      sprite.x = targetX;
      sprite.y = targetY;
      moving = false;
      const cb = onArriveCallback;
      onArriveCallback = undefined;
      cb?.();
    }
  };

  app.ticker.add(tickerFn);

  return {
    moveTo(x: number, y: number, onArrive?: () => void): void {
      targetX = x;
      targetY = y;
      onArriveCallback = onArrive;
      moving = true;
    },

    get isMoving(): boolean {
      return moving;
    },

    dispose(): void {
      app.ticker.remove(tickerFn);
      moving = false;
      onArriveCallback = undefined;
    },
  };
}
