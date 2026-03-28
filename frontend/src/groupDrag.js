export const GROUP_DRAG_RELEASE_DISTANCE = 18;

export function getPointDistanceOutsideRect(rect, point) {
  if (!rect || !point) return Infinity;

  const dx = point.x < rect.left
    ? rect.left - point.x
    : (point.x > rect.right ? point.x - rect.right : 0);
  const dy = point.y < rect.top
    ? rect.top - point.y
    : (point.y > rect.bottom ? point.y - rect.bottom : 0);

  return Math.hypot(dx, dy);
}

export function shouldReleaseFromGroup(rect, point, threshold = GROUP_DRAG_RELEASE_DISTANCE) {
  return getPointDistanceOutsideRect(rect, point) >= threshold;
}
