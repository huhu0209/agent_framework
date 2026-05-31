import { Container, Graphics } from 'pixi.js';
import type { Application, Ticker } from 'pixi.js';
import type { AnimationState } from './types';
import type { CatSprite } from './cat-sprite';
import { DESIGN_COLORS } from './constants';

export interface AnimationController {
  play(state: AnimationState): void;
  dispose(): void;
}

/**
 * Create an animation controller bound to the given app, cat sprite, and effects layer.
 *
 * Visual effects (scale, rotation, y-offset) are applied to catSprite.visual
 * (inner container), NOT to catSprite.container (outer container managed by
 * the movement system). This prevents the animation from overwriting position
 * changes during movement.
 */
export function createAnimationController(
  app: Application,
  catSprite: CatSprite,
  effectsLayer: Container,
): AnimationController {
  let currentAnimation: AnimationState | null = null;
  let cleanupCallback: (() => void) | null = null;
  let bubbleCleanup: (() => void) | null = null;

  function play(state: AnimationState): void {
    if (state === currentAnimation) {
      return;
    }

    // Clean up previous animation
    cleanupCallback?.();
    cleanupCallback = null;
    bubbleCleanup?.();
    bubbleCleanup = null;

    // Reset visual container transform (not position!)
    const vis = catSprite.visual;
    vis.scale.set(1);
    vis.rotation = 0;
    vis.y = 0;

    // Accumulated animation time
    let time = 0;

    if (state === 'shutdown') {
      currentAnimation = state;
      return;
    }

    // Register new ticker callback based on state
    const tickerFn = (ticker: Ticker): void => {
      const dt = ticker.deltaTime;
      time += dt;

      switch (state) {
        case 'idle': {
          // Drinking: body bobs up-down (sin wave) — applied to visual y-offset
          const bob = Math.sin(time * 0.08) * 3;
          vis.y = bob;
          break;
        }
        case 'thinking': {
          // Standing: subtle breathing via scale
          const breath = 1 + Math.sin(time * 0.04) * 0.03;
          vis.scale.set(breath);
          break;
        }
        case 'tool_call': {
          // Typing: sway side-to-side
          const sway = Math.sin(time * 0.1) * 0.08;
          vis.rotation = sway;
          break;
        }
        case 'moving': {
          // Walking: bounce + tilt — visual only, position managed by movement system
          const bounce = Math.sin(time * 0.15) * 3;
          const tilt = Math.sin(time * 0.15) * 0.06;
          vis.y = bounce;
          vis.rotation = tilt;
          break;
        }
      }
    };

    app.ticker.add(tickerFn);
    cleanupCallback = () => {
      app.ticker.remove(tickerFn);
      // Reset visual transform (not root position!)
      vis.scale.set(1);
      vis.rotation = 0;
      vis.y = 0;
    };

    // Thinking state: add thought bubble on effects layer
    if (state === 'thinking') {
      const bubbleContainer = createThoughtBubble(catSprite);
      effectsLayer.addChild(bubbleContainer);

      // Bubble floating animation — follows root container position
      let bubbleTime = 0;
      const bubbleFn = (ticker: Ticker): void => {
        bubbleTime += ticker.deltaTime;
        const floatY = Math.sin(bubbleTime * 0.03) * 2;
        const pos = catSprite.getPosition();
        bubbleContainer.x = pos.x + 14;
        bubbleContainer.y = pos.y - 32 + floatY;
      };
      app.ticker.add(bubbleFn);

      bubbleCleanup = () => {
        app.ticker.remove(bubbleFn);
        effectsLayer.removeChild(bubbleContainer);
        bubbleContainer.destroy({ children: true });
      };
    }

    currentAnimation = state;
  }

  function dispose(): void {
    cleanupCallback?.();
    cleanupCallback = null;
    bubbleCleanup?.();
    bubbleCleanup = null;
    currentAnimation = null;
  }

  return { play, dispose };
}

/**
 * Build a thought bubble: translucent ellipse with three dots.
 * Positioned above the cat sprite.
 */
function createThoughtBubble(catSprite: CatSprite): Container {
  const bubble = new Container();
  bubble.label = 'thought-bubble';

  const pos = catSprite.getPosition();

  // Ellipse background
  const bg = new Graphics()
    .ellipse(0, 0, 16, 10)
    .fill({ color: DESIGN_COLORS.WARM_SAND, alpha: 0.7 });
  bg.label = 'bubble-bg';

  // Three dots ("...")
  const dots = new Graphics()
    .circle(-6, 0, 2)
    .fill(DESIGN_COLORS.OLIVE_GRAY)
    .circle(0, 0, 2)
    .fill(DESIGN_COLORS.OLIVE_GRAY)
    .circle(6, 0, 2)
    .fill(DESIGN_COLORS.OLIVE_GRAY);
  dots.label = 'bubble-dots';

  bubble.addChild(bg, dots);
  bubble.x = pos.x + 14;
  bubble.y = pos.y - 32;

  return bubble;
}
