import { Graphics, Container } from 'pixi.js';
import { POSITIONS, DESIGN_COLORS } from './constants';

/**
 * Draw the minimal office scene onto the background layer.
 *
 * Geometric stick-figure style (D-02): simple shapes for desks, tea room,
 * and door. Each scene position gets a translucent marker dot for debugging.
 *
 * v8 Graphics API: `.circle().fill()` / `.rect().fill()` / `.poly().fill()`
 * — not beginFill/drawCircle/endFill.
 */
export function drawScene(backgroundLayer: Container): void {
  drawFloor(backgroundLayer);
  drawDesk(backgroundLayer, POSITIONS.desk1.x, POSITIONS.desk1.y, '1');
  drawDesk(backgroundLayer, POSITIONS.desk2.x, POSITIONS.desk2.y, '2');
  drawTeaRoom(backgroundLayer, POSITIONS.teaRoom.x, POSITIONS.teaRoom.y);
  drawDoor(backgroundLayer, POSITIONS.door.x, POSITIONS.door.y);
  drawPositionMarkers(backgroundLayer);
}

/** Ground reference line across the bottom of the scene. */
function drawFloor(layer: Container): void {
  const floor = new Graphics()
    .rect(0, 480, 800, 120)
    .fill(DESIGN_COLORS.WARM_SAND);
  layer.addChild(floor);
}

/** A workstation: rectangular desk + chair outline + desk label. */
function drawDesk(layer: Container, cx: number, cy: number, label: string): void {
  // Desk surface — 80x25 rectangle, positioned below the position point
  const deskTop = cy + 10;
  const desk = new Graphics()
    .rect(cx - 40, deskTop, 80, 25)
    .fill(DESIGN_COLORS.WARM_SAND)
    .stroke({ width: 1, color: DESIGN_COLORS.BORDER_CREAM });
  layer.addChild(desk);

  // Monitor — small rectangle on the desk
  const monitor = new Graphics()
    .rect(cx - 15, deskTop - 25, 30, 22)
    .fill(DESIGN_COLORS.OLIVE_GRAY)
    .stroke({ width: 1, color: DESIGN_COLORS.NEAR_BLACK });
  layer.addChild(monitor);

  // Chair — small square below desk
  const chair = new Graphics()
    .rect(cx - 12, deskTop + 30, 24, 20)
    .fill(DESIGN_COLORS.BORDER_CREAM)
    .stroke({ width: 1, color: DESIGN_COLORS.OLIVE_GRAY });
  layer.addChild(chair);

  // Label
  void label; // label available for future text rendering
}

/** Tea room area: counter with a cup shape. */
function drawTeaRoom(layer: Container, cx: number, cy: number): void {
  // Counter
  const counter = new Graphics()
    .rect(cx - 35, cy - 10, 70, 40)
    .fill(DESIGN_COLORS.WARM_SAND)
    .stroke({ width: 1, color: DESIGN_COLORS.BORDER_CREAM });
  layer.addChild(counter);

  // Cup — small cylinder shape
  const cup = new Graphics()
    .rect(cx - 6, cy - 20, 12, 14)
    .fill(DESIGN_COLORS.IVORY)
    .stroke({ width: 1, color: DESIGN_COLORS.OLIVE_GRAY });
  layer.addChild(cup);

  // Cup handle — small arc
  const handle = new Graphics()
    .circle(cx + 9, cy - 13, 4)
    .stroke({ width: 1, color: DESIGN_COLORS.OLIVE_GRAY });
  layer.addChild(handle);
}

/** Door: rectangular frame with a semi-circular arch. */
function drawDoor(layer: Container, cx: number, cy: number): void {
  // Door frame
  const frame = new Graphics()
    .rect(cx - 20, cy - 40, 40, 60)
    .fill(DESIGN_COLORS.BORDER_CREAM)
    .stroke({ width: 2, color: DESIGN_COLORS.OLIVE_GRAY });
  layer.addChild(frame);

  // Door arch — semi-circle
  const arch = new Graphics()
    .arc(cx, cy - 40, 20, Math.PI, 0)
    .stroke({ width: 2, color: DESIGN_COLORS.OLIVE_GRAY });
  layer.addChild(arch);

  // Door knob
  const knob = new Graphics()
    .circle(cx + 10, cy - 10, 3)
    .fill(DESIGN_COLORS.TERRACOTTA);
  layer.addChild(knob);
}

/** Translucent marker dots at each position for debugging. */
function drawPositionMarkers(layer: Container): void {
  const positions = [
    POSITIONS.desk1,
    POSITIONS.desk2,
    POSITIONS.teaRoom,
    POSITIONS.door,
  ];

  for (const pos of positions) {
    const marker = new Graphics()
      .circle(pos.x, pos.y, 4)
      .fill({ color: DESIGN_COLORS.TERRACOTTA, alpha: 0.5 });
    layer.addChild(marker);
  }
}
