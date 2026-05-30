import { Application, Container } from 'pixi.js';
import { CANVAS_WIDTH, CANVAS_HEIGHT, DESIGN_COLORS } from './constants';

export interface RendererResult {
  app: Application;
  backgroundLayer: Container;
  agentLayer: Container;
  effectsLayer: Container;
  destroy: () => void;
}

/**
 * Create a PixiJS v8 Application with three named Container layers.
 *
 * v8 changes: `new Application()` takes no args, `await app.init()` configures
 * the renderer, `app.canvas` replaces `app.view`, `background` replaces
 * `backgroundColor`.
 */
export async function createRenderer(
  container: HTMLElement,
  options?: { width?: number; height?: number },
): Promise<RendererResult> {
  const app = new Application();

  await app.init({
    width: options?.width ?? CANVAS_WIDTH,
    height: options?.height ?? CANVAS_HEIGHT,
    background: DESIGN_COLORS.PARCHMENT,
    antialias: true,
    resolution: window.devicePixelRatio || 1,
    autoDensity: true,
  });

  container.appendChild(app.canvas as unknown as Node);

  const backgroundLayer = new Container();
  backgroundLayer.label = 'background';

  const agentLayer = new Container();
  agentLayer.label = 'agent';

  const effectsLayer = new Container();
  effectsLayer.label = 'effects';

  app.stage.addChild(backgroundLayer, agentLayer, effectsLayer);

  return {
    app,
    backgroundLayer,
    agentLayer,
    effectsLayer,
    destroy: () => {
      app.destroy(true);
    },
  };
}
