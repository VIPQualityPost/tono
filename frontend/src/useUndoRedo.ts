import { useRef, useCallback, type MutableRefObject } from 'react';
import type { TonoNode, TonoEdge } from './types';

interface Snapshot {
  nodes: TonoNode[];
  edges: TonoEdge[];
  nextId: number;
}

/**
 * Snapshot-based undo/redo for nodes + edges.
 *
 * Call `pushSnapshot` before a mutation to save the current state.
 * Call `undo` / `redo` to restore.
 */
export default function useUndoRedo({ maxHistory = 50 } = {}) {
  const pastRef = useRef<Snapshot[]>([]);
  const futureRef = useRef<Snapshot[]>([]);

  const pushSnapshot = useCallback((nodes: TonoNode[], edges: TonoEdge[], nextId: number) => {
    pastRef.current = [
      ...pastRef.current.slice(-(maxHistory - 1)),
      {
        nodes: structuredClone(nodes),
        edges: structuredClone(edges),
        nextId,
      },
    ];
    futureRef.current = [];
  }, [maxHistory]);

  const undo = useCallback((setNodes: (n: TonoNode[]) => void, setEdges: (e: TonoEdge[]) => void, nextIdRef: MutableRefObject<number>, getNodes: () => TonoNode[], getEdges: () => TonoEdge[]) => {
    if (pastRef.current.length === 0) return false;
    futureRef.current = [
      ...futureRef.current,
      {
        nodes: structuredClone(getNodes()),
        edges: structuredClone(getEdges()),
        nextId: nextIdRef.current,
      },
    ];
    const snapshot = pastRef.current.pop()!;
    setNodes(snapshot.nodes);
    setEdges(snapshot.edges);
    nextIdRef.current = snapshot.nextId;
    return true;
  }, []);

  const redo = useCallback((setNodes: (n: TonoNode[]) => void, setEdges: (e: TonoEdge[]) => void, nextIdRef: MutableRefObject<number>, getNodes: () => TonoNode[], getEdges: () => TonoEdge[]) => {
    if (futureRef.current.length === 0) return false;
    pastRef.current = [
      ...pastRef.current,
      {
        nodes: structuredClone(getNodes()),
        edges: structuredClone(getEdges()),
        nextId: nextIdRef.current,
      },
    ];
    const snapshot = futureRef.current.pop()!;
    setNodes(snapshot.nodes);
    setEdges(snapshot.edges);
    nextIdRef.current = snapshot.nextId;
    return true;
  }, []);

  const canUndo = useCallback(() => pastRef.current.length > 0, []);
  const canRedo = useCallback(() => futureRef.current.length > 0, []);

  return { pushSnapshot, undo, redo, canUndo, canRedo };
}
