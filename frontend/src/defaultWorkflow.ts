import { extractWorkflow } from './pngMetadata.ts';
import type { SerializedWorkflow } from './types';

interface WorkflowCandidate {
  path: string;
  type: string;
}

const DEFAULT_WORKFLOW_CANDIDATES: WorkflowCandidate[] = [
  { path: '/default-workflow.json', type: 'json' },
  { path: '/default-workflow.png', type: 'png' },
];

type FetchImpl = typeof fetch;
type ExtractWorkflowFn = (blob: Blob) => Promise<SerializedWorkflow | null>;

async function loadCandidate(candidate: WorkflowCandidate, fetchImpl: FetchImpl, extractWorkflowFn: ExtractWorkflowFn): Promise<SerializedWorkflow | null> {
  let response;
  try {
    response = await fetchImpl(candidate.path, { cache: 'no-store' });
  } catch {
    return null;
  }

  const contentType = response.headers?.get?.('content-type') || '';
  const isHtmlFallback = typeof contentType === 'string' && contentType.toLowerCase().includes('text/html');

  if (!response.ok) {
    if (response.status === 404 || response.status === 0) return null;
    throw new Error(`Failed to load ${candidate.path} (${response.status})`);
  }

  if (candidate.type === 'json') {
    if (isHtmlFallback) return null;
    try {
      return await response.json();
    } catch {
      throw new Error(`${candidate.path} is not valid JSON`);
    }
  }

  if (isHtmlFallback) return null;
  const workflow = await extractWorkflowFn(await response.blob());
  if (!workflow) {
    throw new Error(`${candidate.path} does not contain embedded workflow metadata`);
  }
  return workflow;
}

export async function loadDefaultWorkflowAsset({
  fetchImpl = fetch as FetchImpl,
  extractWorkflowFn = extractWorkflow as ExtractWorkflowFn,
}: { fetchImpl?: FetchImpl; extractWorkflowFn?: ExtractWorkflowFn } = {}) {
  for (const candidate of DEFAULT_WORKFLOW_CANDIDATES) {
    const workflow = await loadCandidate(candidate, fetchImpl, extractWorkflowFn);
    if (workflow) {
      return {
        source: candidate.path,
        format: candidate.type,
        workflow,
      };
    }
  }
  return null;
}
