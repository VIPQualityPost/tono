export const GROUP_DRAG_RELEASE_DISTANCE = 18;

interface Rect {
  left: number;
  right: number;
  top: number;
  bottom: number;
}

interface Point {
  x: number;
  y: number;
}

export function getPointDistanceOutsideRect(rect: Rect | null, point: Point | null): number {
  if (!rect || !point) return Infinity;

  const dx = point.x < rect.left
    ? rect.left - point.x
    : (point.x > rect.right ? point.x - rect.right : 0);
  const dy = point.y < rect.top
    ? rect.top - point.y
    : (point.y > rect.bottom ? point.y - rect.bottom : 0);

  return Math.hypot(dx, dy);
}

export function shouldReleaseFromGroup(rect: Rect | null, point: Point | null, threshold = GROUP_DRAG_RELEASE_DISTANCE): boolean {
  return getPointDistanceOutsideRect(rect, point) >= threshold;
}
