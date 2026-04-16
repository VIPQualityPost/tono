import type { Node, Edge } from '@xyflow/react';
import type { CSSProperties } from 'react';

// ── Input Specifications ─────────────────────────────────────────────

export interface InputOptions {
  label?: string;
  hidden?: boolean;
  socket_only?: boolean;
  accepted_types?: string[];
  default?: unknown;
  placeholder?: string;
  min?: number;
  max?: number;
  step?: number;
  slider?: boolean;
  min_widget?: string;
  max_widget?: string;
  text_input?: boolean;
  color_picker?: boolean;
  colormap_stops?: boolean;
  top_socket_input?: string | string[];
  set_widgets?: Record<string, unknown>;
  show_when_source_type?: Record<string, string[]>;
  show_when_widget_value?: Record<string, unknown[]>;
  show_when_input_visible?: string | string[];
  hide_when_input_connected?: string | string[];
  choices_by_source_type?: Record<string, string[]>;
  choices_from_table_input?: string;
  choices_from_measure_input?: string;
  inline_with_input?: string | [string];
  source_type_input?: string;
  placement?: 'top';
}

/** An input spec is either a bare type string, or a [type, opts] tuple. */
export type InputSpec = string | [type: string | string[], opts?: InputOptions];

// ── Node Definition (from GET /nodes) ────────────────────────────────

export interface NodeDefinition {
  input: {
    required: Record<string, InputSpec>;
    optional: Record<string, InputSpec>;
  };
  output: string[];
  output_name: string[];
  output_paths?: string[];
  output_accepted_types?: string[][];
  category: string;
  manual_trigger?: boolean;
}

export type NodeDefsRegistry = Record<string, NodeDefinition>;

// ── Overlay Types ────────────────────────────────────────────────────

export interface OverlayData {
  kind: string;
  image?: string;
  image_width?: number;
  image_height?: number;
  x1?: number;
  y1?: number;
  x2?: number;
  y2?: number;
  xm?: number;
  ym?: number;
  cx?: number;
  cy?: number;
  ex?: number;
  ey?: number;
  a_locked?: boolean;
  b_locked?: boolean;
  section_title?: string;
  line?: number[];
  shape?: string;
  stroke_color?: string;
  stroke_width?: number;
  angle_deg?: number;
  color?: string;
  label_dx?: number;
  label_dy?: number;
  line_thickness?: number;
  histogram?: unknown;
}

// ── Preview Image Types ──────────────────────────────────────────────

export interface PreviewPanel {
  kind: 'image' | 'line_plot';
  title?: string;
  image?: string;
  line?: number[];
  fallback_image?: string;
}

export interface PreviewPayload {
  kind: 'image' | 'line_plot' | 'layer_gallery' | 'panels';
  image?: string;
  line?: number[];
  layers?: Array<{ name?: string; image: string }>;
  fallback_image?: string;
  panels?: PreviewPanel[];
}

export type PreviewImage = string | PreviewPayload;

// ── Node Data (attached to each ReactFlow node) ──────────────────────

export interface GroupProxy {
  handleId: string;
  type: string;
  label: string;
  name: string;
}

export interface NodeData extends Record<string, unknown> {
  label: string;
  className: string;
  definition?: NodeDefinition | null;
  widgetValues: Record<string, unknown>;
  runtimeValues?: Record<string, unknown>;

  // Execution results
  previewImage?: PreviewImage | null;
  tableRows?: Array<Record<string, unknown>> | null;
  scalarValue?: number | { value: number | string; unit?: string } | null;
  meshData?: unknown;
  overlay?: OverlayData | null;

  // Status
  error?: string | null;
  warning?: string | null;
  processingTimeMs?: number | null;

  // Group node fields
  proxyInputs?: GroupProxy[];
  proxyOutputs?: GroupProxy[];
  childCount?: number;
  collapsed?: boolean;
  expandedSize?: { width: number; height: number };

  // Serialization extras
  extraData?: Record<string, unknown>;
  output?: string[];
  output_name?: string[];
}

// ── ReactFlow Node & Edge ────────────────────────────────────────────

export type TonoNode = Node<NodeData, 'custom'>;
export type TonoEdge = Edge<{
  groupProxyOwner?: string;
  groupProxyOriginal?: {
    source?: string;
    sourceHandle?: string;
    target?: string;
    targetHandle?: string;
  };
}>;

// ── Serialized Workflow ──────────────────────────────────────────────

export interface SerializedNode {
  id: string;
  type?: string;
  position: { x: number; y: number };
  width?: number;
  height?: number;
  className?: string;
  parentId?: string;
  extent?: [[number, number], [number, number]];
  hidden?: boolean;
  style?: CSSProperties;
  dragHandle?: string;
  data: {
    label: string;
    className: string;
    widgetValues: Record<string, unknown>;
    runtimeValues?: Record<string, unknown>;
    extraData?: Record<string, unknown>;
    output?: string[];
    output_name?: string[];
  };
}

export interface SerializedEdge {
  id: string;
  source: string;
  sourceHandle?: string;
  target: string;
  targetHandle?: string;
  style?: CSSProperties;
  hidden?: boolean;
  data?: Record<string, unknown>;
}

export interface SerializedWorkflow {
  version: number;
  nodes: SerializedNode[];
  edges: SerializedEdge[];
  packed?: boolean;
  packedFiles?: Record<string, { filename: string; data: string }>;
}

// ── WebSocket Messages ───────────────────────────────────────────────

export type WsMessage =
  | { type: 'execution_start'; data: { prompt_id: string } }
  | { type: 'executing'; data: { node: string; prompt_id: string } }
  | { type: 'execution_complete'; data: { prompt_id: string } }
  | { type: 'execution_error'; data: { node_id: string; message: string } }
  | { type: 'preview'; data: { node_id: string; image: PreviewImage } }
  | { type: 'table'; data: { node_id: string; rows: Array<Record<string, unknown>> } }
  | { type: 'scalar'; data: { node_id: string; value: number | string; unit?: string } }
  | { type: 'node_timing'; data: { node_id: string; elapsed_ms: number } }
  | { type: 'mesh3d'; data: { node_id: string; mesh: unknown } }
  | { type: 'overlay'; data: { node_id: string; overlay: OverlayData } }
  | { type: 'node_warning'; data: { node_id: string; message: string } }
  | { type: 'nodes_updated'; data: Record<string, never> };

// ── Widget description (used by nodeWidgetLayout) ────────────────────

export interface WidgetDescriptor {
  name: string;
  type: string | string[];
  opts: InputOptions;
  socketType?: string;
}

// ── Node Context (provided by App to CustomNode) ─────────────────────

export interface NodeContextValue {
  executingNodeId: string | null;
  onWidgetChange: (nodeId: string, name: string, value: unknown) => void;
  openFileBrowser: (callback: (files: File[]) => void, options?: unknown) => void;
  openHelp: (label: string) => void;
  getTableColumns: (nodeId: string, inputName: string) => string[];
  getMeasurementChoices: (nodeId: string, inputName: string) => string[];
}
