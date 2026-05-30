import type { VizEvent, AnimationState } from './types';
import { createRenderer } from './renderer';
import type { RendererResult } from './renderer';
import { drawScene } from './scene';
import { createCatSprite } from './cat-sprite';
import type { CatSprite } from './cat-sprite';
import { createAnimationController } from './animations';
import type { AnimationController } from './animations';
import { createMovementSystem } from './movement';
import type { MovementSystem } from './movement';
import { POSITIONS } from './constants';

let renderer: RendererResult | null = null;
let catSprite: CatSprite | null = null;
let animationController: AnimationController | null = null;
let movementSystem: MovementSystem | null = null;

/** Map VizEventType to the corresponding AnimationState. */
function vizEventTypeToAnimationState(type: VizEvent['type']): AnimationState {
  switch (type) {
    case 'idle':
      return 'idle';
    case 'thinking':
      return 'thinking';
    case 'tool_call':
      return 'tool_call';
    case 'done':
      return 'idle';
    case 'error':
      return 'idle';
    case 'shutdown':
      return 'shutdown';
  }
}

/** Map AnimationState to the target scene position (per D-04). */
function getStateTargetPosition(state: AnimationState): { x: number; y: number } {
  switch (state) {
    case 'idle':
      return POSITIONS.teaRoom;
    case 'thinking':
    case 'tool_call':
      return POSITIONS.desk1;
    case 'moving':
      // Fallback: stay at current position
      return catSprite?.getPosition() ?? POSITIONS.teaRoom;
    case 'shutdown':
      return POSITIONS.door;
  }
}

/** Distance below which we consider the cat already at the target position. */
const SAME_POSITION_THRESHOLD = 2;

/**
 * Initialize the PixiJS Canvas renderer, draw the office scene,
 * create the cat sprite, and start the idle animation.
 */
export async function init(
  container: HTMLElement,
  options?: { width?: number; height?: number },
): Promise<void> {
  renderer = await createRenderer(container, options);
  drawScene(renderer.backgroundLayer);

  // Create cat sprite and add to agent layer
  catSprite = createCatSprite();
  renderer.agentLayer.addChild(catSprite.container);

  // Place at teaRoom (default idle position, per D-04)
  catSprite.setPosition(POSITIONS.teaRoom.x, POSITIONS.teaRoom.y);

  // Create animation controller and start idle animation
  animationController = createAnimationController(
    renderer.app,
    catSprite,
    renderer.effectsLayer,
  );

  // Create movement system
  movementSystem = createMovementSystem(catSprite.container, renderer.app);

  animationController.play('idle');
}

/** Fade out the cat sprite (shutdown effect). Ticker-driven alpha decrease. */
function startFadeOut(): void {
  if (!renderer || !catSprite) {
    return;
  }

  const cat = catSprite.container;
  let fadeFn: ((ticker: { deltaTime: number }) => void) | null = null;

  fadeFn = (ticker): void => {
    cat.alpha -= 0.02 * ticker.deltaTime;
    if (cat.alpha <= 0) {
      cat.alpha = 0;
      cat.visible = false;
      if (fadeFn) {
        renderer?.app.ticker.remove(fadeFn);
      }
    }
  };

  renderer.app.ticker.add(fadeFn);
}

/**
 * Update the canvas with a new visualization event.
 * Maps VizEvent.type to AnimationState, moves sprite to target position,
 * and plays the corresponding animation.
 */
export function updateState(event: VizEvent): void {
  if (!renderer || !catSprite || !animationController || !movementSystem) {
    return;
  }

  const state = vizEventTypeToAnimationState(event.type);
  const cat = catSprite.container;

  if (state === 'shutdown') {
    // Shutdown: move to door, then fade out
    const target = POSITIONS.door;
    const distance = Math.hypot(target.x - cat.x, target.y - cat.y);

    if (distance < SAME_POSITION_THRESHOLD) {
      // Already at door — start fade immediately
      startFadeOut();
    } else {
      animationController.play('moving');
      movementSystem.moveTo(target.x, target.y, () => {
        startFadeOut();
      });
    }
  } else {
    // Non-shutdown: restore visibility if previously hidden by shutdown
    if (!cat.visible || cat.alpha < 1) {
      cat.visible = true;
      cat.alpha = 1;
    }

    const target = getStateTargetPosition(state);
    const distance = Math.hypot(target.x - cat.x, target.y - cat.y);

    if (distance < SAME_POSITION_THRESHOLD) {
      // Already at target — play animation directly
      animationController.play(state);
    } else {
      // Move to target, then play the target animation on arrival
      animationController.play('moving');
      movementSystem.moveTo(target.x, target.y, () => {
        animationController?.play(state);
      });
    }
  }

  console.log('VizEvent received:', event.type, '-> animation:', state);
}

/** Destroy the renderer, animation controller, movement system, and cat sprite. */
export function destroy(): void {
  movementSystem?.dispose();
  movementSystem = null;
  animationController?.dispose();
  animationController = null;
  catSprite?.dispose();
  catSprite = null;
  renderer?.destroy();
  renderer = null;
}
