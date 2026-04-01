import { useRef, useCallback } from 'react';

/**
 * Snapshot-based undo/redo for nodes + edges.
 *
 * Call `pushSnapshot` before a mutation to save the current state.
 * Call `undo` / `redo` to restore.
 */
export default function useUndoRedo({ maxHistory = 50 } = {}) {
  const pastRef = useRef([]);
  const futureRef = useRef([]);

  const pushSnapshot = useCallback((nodes, edges, nextId) => {
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

  const undo = useCallback((setNodes, setEdges, nextIdRef, getNodes, getEdges) => {
    if (pastRef.current.length === 0) return false;
    futureRef.current = [
      ...futureRef.current,
      {
        nodes: structuredClone(getNodes()),
        edges: structuredClone(getEdges()),
        nextId: nextIdRef.current,
      },
    ];
    const snapshot = pastRef.current.pop();
    setNodes(snapshot.nodes);
    setEdges(snapshot.edges);
    nextIdRef.current = snapshot.nextId;
    return true;
  }, []);

  const redo = useCallback((setNodes, setEdges, nextIdRef, getNodes, getEdges) => {
    if (futureRef.current.length === 0) return false;
    pastRef.current = [
      ...pastRef.current,
      {
        nodes: structuredClone(getNodes()),
        edges: structuredClone(getEdges()),
        nextId: nextIdRef.current,
      },
    ];
    const snapshot = futureRef.current.pop();
    setNodes(snapshot.nodes);
    setEdges(snapshot.edges);
    nextIdRef.current = snapshot.nextId;
    return true;
  }, []);

  const canUndo = useCallback(() => pastRef.current.length > 0, []);
  const canRedo = useCallback(() => futureRef.current.length > 0, []);

  return { pushSnapshot, undo, redo, canUndo, canRedo };
}
