/**
 * Animation controller — drives procedural frame animations for the cat sprite.
 *
 * Four animation states driven by PixiJS v8 Ticker:
 *   - standing (thinking base): subtle breathing (scale oscillation)
 *   - walking: bounce + tilt
 *   - typing (tool_call): sway side-to-side
 *   - drinking (idle): head/body bob up-down
 *
 * Thinking state additionally renders a thought bubble on the effects layer.
 *
 * v8 Ticker callback signature: (ticker: Ticker) => void
 * Use ticker.deltaTime for frame-relative timing.
 */
import { Container, Graphics } from 'pixi.js';
import type { Application, Ticker } from 'pixi.js';
import type { AnimationState } from './types';
import type { CatSprite } from './cat-sprite';
import { DESIGN_COLORS } from './constants';

/** Public interface for the animation controller. */
export interface AnimationController {
  play(state: AnimationState): void;
  dispose(): void;
}

/** Create an animation controller bound to the given app, cat sprite, and effects layer. */
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

    // Reset cat transform to defaults
    const cat = catSprite.container;
    cat.scale.set(1);
    cat.rotation = 0;
    // Reset y offset from animations (keep the logical position)
    const savedX = cat.x;
    const savedY = cat.y;

    // Accumulated animation time
    let time = 0;

    if (state === 'shutdown') {
      // No animation for shutdown (Plan 10-03 handles shutdown movement)
      currentAnimation = state;
      return;
    }

    // Register new ticker callback based on state
    const tickerFn = (ticker: Ticker): void => {
      const dt = ticker.deltaTime;
      time += dt;

      switch (state) {
        case 'idle': {
          // Drinking: body bobs up-down (sin wave)
          const bob = Math.sin(time * 0.08) * 2;
          cat.y = savedY + bob;
          break;
        }
        case 'thinking': {
          // Standing: subtle breathing via scale
          const breath = 1 + Math.sin(time * 0.04) * 0.02;
          cat.scale.set(breath);
          break;
        }
        case 'tool_call': {
          // Typing: sway side-to-side
          const sway = Math.sin(time * 0.1) * 0.06;
          cat.rotation = sway;
          break;
        }
        case 'moving': {
          // Walking: bounce + tilt
          const bounce = Math.sin(time * 0.15) * 2.5;
          const tilt = Math.sin(time * 0.15) * 0.05;
          cat.y = savedY + bounce;
          cat.rotation = tilt;
          break;
        }
      }
    };

    app.ticker.add(tickerFn);
    cleanupCallback = () => {
      app.ticker.remove(tickerFn);
      // Reset transform after animation ends
      cat.scale.set(1);
      cat.rotation = 0;
      cat.x = savedX;
      cat.y = savedY;
    };

    // Thinking state: add thought bubble on effects layer
    if (state === 'thinking') {
      const bubbleContainer = createThoughtBubble(catSprite);
      effectsLayer.addChild(bubbleContainer);

      // Bubble floating animation
      let bubbleTime = 0;
      const bubbleFn = (ticker: Ticker): void => {
        bubbleTime += ticker.deltaTime;
        const floatY = Math.sin(bubbleTime * 0.03) * 2;
        bubbleContainer.y = catSprite.getPosition().y - 32 + floatY;
        bubbleContainer.x = catSprite.getPosition().x + 14;
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
