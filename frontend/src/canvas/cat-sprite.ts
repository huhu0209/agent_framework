/**
 * Cat sprite — geometric placeholder (circle body + triangle ears + eyes).
 * Fits within a 32x32 pixel area (D-07).
 *
 * Architecture: root Container (position managed by movement system)
 *               → visual Container (visual effects managed by animation controller)
 *                  → Graphics parts (body, ears, eyes)
 *
 * This separation prevents the animation controller from overwriting position
 * changes made by the movement system.
 */
import { Container, Graphics } from 'pixi.js';
import { DESIGN_COLORS, CAT_SIZE } from './constants';
import type { AnimationState } from './types';

/** Public interface for the cat sprite. */
export interface CatSprite {
  /** Root container — position is managed externally (by movement system). */
  container: Container;
  /** Inner visual container — rotation/scale offsets managed by animation controller. */
  visual: Container;
  /** Switch the animation state (delegates to AnimationController). */
  setAnimation: (state: AnimationState, effectsLayer?: Container) => void;
  /** Release resources. */
  dispose: () => void;
  /** Get current position (from root container). */
  getPosition: () => { x: number; y: number };
  /** Set position (on root container). */
  setPosition: (x: number, y: number) => void;
}

/**
 * Build a geometric cat sprite.
 *
 * Coordinate system (32x32 centred):
 *   - Body circle centre at (0, 2), radius 10
 *   - Left ear triangle above-left of body
 *   - Right ear triangle above-right of body
 *   - Two eye circles on the body
 */
export function createCatSprite(): CatSprite {
  const root = new Container();
  root.label = 'cat';

  // Inner visual container for animation effects (scale, rotation, y-offset)
  const visual = new Container();
  visual.label = 'cat-visual';
  root.addChild(visual);

  // Body — circle, Terracotta
  const body = new Graphics()
    .circle(0, 2, 10)
    .fill(DESIGN_COLORS.TERRACOTTA);
  body.label = 'cat-body';

  // Left ear — triangle, Terracotta
  const leftEar = new Graphics()
    .poly([-8, -4, -5, -12, -1, -4])
    .fill(DESIGN_COLORS.TERRACOTTA);
  leftEar.label = 'cat-left-ear';

  // Right ear — triangle, Terracotta
  const rightEar = new Graphics()
    .poly([1, -4, 5, -12, 8, -4])
    .fill(DESIGN_COLORS.TERRACOTTA);
  rightEar.label = 'cat-right-ear';

  // Eyes — two small circles, Near Black
  const eyes = new Graphics()
    .circle(-4, 0, 2)
    .fill(DESIGN_COLORS.NEAR_BLACK)
    .circle(4, 0, 2)
    .fill(DESIGN_COLORS.NEAR_BLACK);
  eyes.label = 'cat-eyes';

  visual.addChild(body, leftEar, rightEar, eyes);

  return {
    container: root,
    visual,

    setAnimation(_state: AnimationState, _effectsLayer?: Container): void {
      // Delegated to AnimationController — stub for interface completeness
    },

    dispose(): void {
      root.destroy({ children: true });
    },

    getPosition(): { x: number; y: number } {
      return { x: root.x, y: root.y };
    },

    setPosition(x: number, y: number): void {
      root.x = x;
      root.y = y;
    },
  };
}
