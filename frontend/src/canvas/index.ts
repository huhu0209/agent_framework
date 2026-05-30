import type { VizEvent, AnimationState } from './types';
import { createRenderer } from './renderer';
import type { RendererResult } from './renderer';
import { drawScene } from './scene';
import { createCatSprite } from './cat-sprite';
import type { CatSprite } from './cat-sprite';
import { createAnimationController } from './animations';
import type { AnimationController } from './animations';
import { POSITIONS } from './constants';

let renderer: RendererResult | null = null;
let catSprite: CatSprite | null = null;
let animationController: AnimationController | null = null;

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
  animationController.play('idle');
}

/**
 * Update the canvas with a new visualization event.
 * Maps VizEvent.type to AnimationState and plays the corresponding animation.
 */
export function updateState(event: VizEvent): void {
  if (!renderer) {
    return;
  }
  const state = vizEventTypeToAnimationState(event.type);
  animationController?.play(state);
  console.log('VizEvent received:', event.type, '-> animation:', state);
}

/** Destroy the renderer, animation controller, and cat sprite. */
export function destroy(): void {
  animationController?.dispose();
  animationController = null;
  catSprite?.dispose();
  catSprite = null;
  renderer?.destroy();
  renderer = null;
}
