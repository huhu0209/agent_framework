import type { VizEvent } from './types';
import { createRenderer } from './renderer';
import type { RendererResult } from './renderer';
import { drawScene } from './scene';

let renderer: RendererResult | null = null;

/**
 * Initialize the PixiJS Canvas renderer and draw the office scene.
 * Attaches the canvas element to the provided container.
 */
export async function init(
  container: HTMLElement,
  options?: { width?: number; height?: number },
): Promise<void> {
  renderer = await createRenderer(container, options);
  drawScene(renderer.backgroundLayer);
}

/**
 * Update the canvas with a new visualization event.
 * Animation logic will be added in Plan 10-02; currently logs the event.
 */
export function updateState(event: VizEvent): void {
  if (!renderer) {
    return;
  }
  console.log('VizEvent received:', event.type, event.agent);
}

/** Destroy the renderer and release all resources. */
export function destroy(): void {
  renderer?.destroy();
  renderer = null;
}
