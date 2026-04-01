interface AnglePoints {
  x1: number;
  y1: number;
  xm: number;
  ym: number;
  x2: number;
  y2: number;
}

function clamp01(value: number): number {
  return Math.max(0, Math.min(1, Number(value) || 0));
}

export function round3(value: number): number {
  return Number.parseFloat(Number(value).toFixed(3));
}

export function getAngleLabelBasePosition(x1: number, y1: number, xm: number, ym: number, x2: number, y2: number) {
  const va = { x: Number(x1) - Number(xm), y: Number(y1) - Number(ym) };
  const vb = { x: Number(x2) - Number(xm), y: Number(y2) - Number(ym) };
  const lenA = Math.hypot(va.x, va.y);
  const lenB = Math.hypot(vb.x, vb.y);

  if (lenA <= 1e-6 || lenB <= 1e-6) {
    return { x: clamp01(xm), y: clamp01(Number(ym) - 0.14) };
  }

  const unit = {
    x: (va.x / lenA) + (vb.x / lenB),
    y: (va.y / lenA) + (vb.y / lenB),
  };
  const unitLength = Math.hypot(unit.x, unit.y);
  const bisector = unitLength <= 1e-6
    ? { x: 0, y: -1 }
    : { x: unit.x / unitLength, y: unit.y / unitLength };

  return {
    x: clamp01(Number(xm) + bisector.x * 0.14),
    y: clamp01(Number(ym) + bisector.y * 0.14),
  };
}

export function getAngleLabelPosition(points: AnglePoints, labelDx: number = 0, labelDy: number = 0) {
  const base = getAngleLabelBasePosition(points.x1, points.y1, points.xm, points.ym, points.x2, points.y2);
  return {
    x: clamp01(base.x + (Number(labelDx) || 0)),
    y: clamp01(base.y + (Number(labelDy) || 0)),
  };
}

export function moveAngleWidget(points: AnglePoints, dx: number, dy: number) {
  const nextDx = Number(dx) || 0;
  const nextDy = Number(dy) || 0;
  const xs = [points.x1, points.xm, points.x2];
  const ys = [points.y1, points.ym, points.y2];
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  const clampedDx = Math.max(-minX, Math.min(1 - maxX, nextDx));
  const clampedDy = Math.max(-minY, Math.min(1 - maxY, nextDy));

  return {
    x1: round3(clamp01(points.x1 + clampedDx)),
    y1: round3(clamp01(points.y1 + clampedDy)),
    xm: round3(clamp01(points.xm + clampedDx)),
    ym: round3(clamp01(points.ym + clampedDy)),
    x2: round3(clamp01(points.x2 + clampedDx)),
    y2: round3(clamp01(points.y2 + clampedDy)),
  };
}

export function measureAngleDegrees(x1: number, y1: number, xm: number, ym: number, x2: number, y2: number) {
  const ax = Number(x1) - Number(xm);
  const ay = Number(y1) - Number(ym);
  const bx = Number(x2) - Number(xm);
  const by = Number(y2) - Number(ym);
  const lenA = Math.hypot(ax, ay);
  const lenB = Math.hypot(bx, by);

  if (lenA <= 1e-12 || lenB <= 1e-12) return 0;

  const cosTheta = ((ax * bx) + (ay * by)) / (lenA * lenB);
  const clamped = Math.max(-1, Math.min(1, cosTheta));
  return Math.acos(clamped) * (180 / Math.PI);
}
