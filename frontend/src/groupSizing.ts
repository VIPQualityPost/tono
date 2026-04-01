const DEFAULT_CHILD_WIDTH = 200;
const DEFAULT_CHILD_HEIGHT = 120;

interface SizableNode {
  position?: { x: number; y: number };
  measured?: { width?: number; height?: number };
  width?: number;
  height?: number;
  style?: Record<string, unknown>;
}

function getNodeSize(node: SizableNode | null | undefined, axis: 'width' | 'height'): number {
  const fallback = axis === 'width' ? DEFAULT_CHILD_WIDTH : DEFAULT_CHILD_HEIGHT;
  const measured = Number(node?.measured?.[axis]);
  if (Number.isFinite(measured) && measured > 0) return measured;
  const direct = Number(node?.[axis]);
  if (Number.isFinite(direct) && direct > 0) return direct;
  const styled = Number(node?.style?.[axis]);
  if (Number.isFinite(styled) && styled > 0) return styled;
  return fallback;
}

export function getGroupMinimumSize(memberNodes: SizableNode[] | null | undefined, {
  minWidth = 260,
  minHeight = 180,
  paddingX = 24,
  paddingY = 24,
} = {}) {
  let maxRight = 0;
  let maxBottom = 0;

  for (const node of memberNodes || []) {
    const x = Number(node?.position?.x) || 0;
    const y = Number(node?.position?.y) || 0;
    maxRight = Math.max(maxRight, x + getNodeSize(node, 'width'));
    maxBottom = Math.max(maxBottom, y + getNodeSize(node, 'height'));
  }

  return {
    width: Math.max(minWidth, Math.ceil(maxRight + paddingX)),
    height: Math.max(minHeight, Math.ceil(maxBottom + paddingY)),
  };
}
