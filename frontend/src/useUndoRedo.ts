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
  // Fingerprint of the most recent push — consecutive identical snapshots
  // (e.g. one delete gesture producing both a node-removal and an
  // edge-removal snapshot) are collapsed into a single entry.
  const lastSnapshotKeyRef = useRef<string | null>(null);
  // Widget edits fire many callbacks per gesture; while the window is open,
  // later pushes are absorbed so a slider drag commits exactly one undo entry.
  const coalesceUntilRef = useRef<number>(0);

  const pushSnapshot = useCallback((nodes: TonoNode[], edges: TonoEdge[], nextId: number) => {
    const key = `${nextId}|${JSON.stringify(nodes)}|${JSON.stringify(edges)}`;
    if (lastSnapshotKeyRef.current === key) return;
    lastSnapshotKeyRef.current = key;
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

  /**
   * Push a snapshot, but absorb follow-up pushes issued within `windowMs`
   * (e.g. the many onChange events of one slider drag). The first call in a
   * burst records the pre-mutation state; later calls in the burst are
   * skipped so Ctrl+Z reverts the whole gesture as one step.
   */
  const pushCoalesced = useCallback((nodes: TonoNode[], edges: TonoEdge[], nextId: number, windowMs = 400) => {
    const now = Date.now();
    if (!(now < coalesceUntilRef.current)) {
      pushSnapshot(nodes, edges, nextId);
    }
    coalesceUntilRef.current = now + windowMs;
  }, [pushSnapshot]);

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

  return { pushSnapshot, pushCoalesced, undo, redo, canUndo, canRedo };
}
