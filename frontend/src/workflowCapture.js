import { toBlob } from 'html-to-image';
import { CANVAS_COLORS } from './constants';

export const OVERLAY_CAPTURE_SELECTORS = [
  '.lineplot-overlay',
  '.cs-overlay',
  '.crop-overlay',
];

function encodeBase64(bytes) {
  if (typeof Buffer !== 'undefined') {
    return Buffer.from(bytes).toString('base64');
  }

  let binary = '';
  for (let i = 0; i < bytes.length; i += 1) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

async function blobToDataUrl(blob) {
  if (!blob) return null;
  const bytes = new Uint8Array(await blob.arrayBuffer());
  return `data:${blob.type || 'image/png'};base64,${encodeBase64(bytes)}`;
}

function getElementSize(el) {
  const rect = el.getBoundingClientRect?.() ?? { width: 0, height: 0 };
  return {
    width: Math.max(1, Math.round(el.clientWidth || rect.width || 0)),
    height: Math.max(1, Math.round(el.clientHeight || rect.height || 0)),
  };
}

export async function waitForImageElement(img) {
  if (img.complete && img.naturalWidth > 0) return;
  if (typeof img.decode === 'function') {
    try {
      await img.decode();
      return;
    } catch {
      // Fall back to load/error listeners below.
    }
  }
  await new Promise((resolve) => {
    const done = () => {
      img.removeEventListener('load', done);
      img.removeEventListener('error', done);
      resolve();
    };
    img.addEventListener('load', done, { once: true });
    img.addEventListener('error', done, { once: true });
  });
}

export async function getCaptureImageDataUrl(img) {
  const src = img.currentSrc || img.src;
  if (!src) return null;
  if (!src.startsWith('data:')) return src;

  const { width, height } = getElementSize(img);
  const scale = Math.min(2, globalThis.window?.devicePixelRatio || 1);

  const canvas = globalThis.document.createElement('canvas');
  canvas.width = Math.max(1, Math.round(width * scale));
  canvas.height = Math.max(1, Math.round(height * scale));

  const ctx = canvas.getContext('2d');
  if (!ctx) return src;

  try {
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL('image/png');
  } catch {
    return src;
  }
}

export function createCapturePlaceholder(
  el,
  dataUrl,
  { stretch = false, documentRef = globalThis.document, getComputedStyleFn = globalThis.window?.getComputedStyle?.bind(globalThis.window) } = {},
) {
  const rect = el.getBoundingClientRect();
  const style = getComputedStyleFn(el);
  const placeholder = documentRef.createElement('div');

  placeholder.style.display = style.display === 'inline' ? 'inline-block' : style.display;
  placeholder.style.width = `${el.clientWidth || rect.width}px`;
  placeholder.style.height = `${el.clientHeight || rect.height}px`;
  placeholder.style.maxWidth = style.maxWidth;
  placeholder.style.maxHeight = style.maxHeight;
  placeholder.style.minWidth = style.minWidth;
  placeholder.style.minHeight = style.minHeight;
  placeholder.style.borderRadius = style.borderRadius;
  placeholder.style.backgroundImage = `url("${dataUrl}")`;
  placeholder.style.backgroundRepeat = 'no-repeat';
  placeholder.style.backgroundPosition = 'center';
  placeholder.style.backgroundSize = stretch ? '100% 100%' : 'contain';
  placeholder.style.flexShrink = style.flexShrink;

  return placeholder;
}

async function renderCanvasToDataUrl(canvas) {
  try {
    return canvas.toDataURL('image/png');
  } catch {
    return null;
  }
}

async function renderElementToDataUrl(el, toBlobImpl) {
  const { width, height } = getElementSize(el);
  const blob = await toBlobImpl(el, {
    width,
    height,
    backgroundColor: CANVAS_COLORS.bgDeep,
    style: {
      width: `${width}px`,
      height: `${height}px`,
      transform: 'none',
    },
  });
  return blobToDataUrl(blob);
}

async function replaceElementsWithPlaceholders(elements, renderDataUrl, createPlaceholderFn, stretch) {
  const restorers = [];

  for (const el of elements) {
    if (!el?.parentNode) continue;
    const dataUrl = await renderDataUrl(el);
    if (!dataUrl) continue;

    const placeholder = createPlaceholderFn(el, dataUrl, { stretch });
    el.parentNode.replaceChild(placeholder, el);
    restorers.push(() => {
      if (placeholder.parentNode) {
        placeholder.parentNode.replaceChild(el, placeholder);
      }
    });
  }

  return restorers;
}

function defaultQueryAll(root, selector) {
  return Array.from(root.querySelectorAll(selector));
}

function defaultNextFrame() {
  return new Promise((resolve) => requestAnimationFrame(() => resolve()));
}

export async function captureViewportBlob(viewportEl, options, deps = {}) {
  const queryAll = deps.queryAll ?? defaultQueryAll;
  const toBlobImpl = deps.toBlobImpl ?? toBlob;
  const waitForImage = deps.waitForImageElement ?? waitForImageElement;
  const renderImage = deps.renderImageToDataUrl ?? getCaptureImageDataUrl;
  const renderCanvas = deps.renderCanvasToDataUrl ?? renderCanvasToDataUrl;
  const renderOverlay = deps.renderOverlayToDataUrl ?? ((el) => renderElementToDataUrl(el, toBlobImpl));
  const createPlaceholderFn = deps.createPlaceholder ?? createCapturePlaceholder;
  const nextFrame = deps.nextFrame ?? defaultNextFrame;
  const overlaySelectors = deps.overlaySelectors ?? OVERLAY_CAPTURE_SELECTORS;
  const restorers = [];

  const overlays = [];
  const seen = new Set();
  for (const selector of overlaySelectors) {
    for (const el of queryAll(viewportEl, selector)) {
      if (seen.has(el)) continue;
      seen.add(el);
      overlays.push(el);
    }
  }

  const images = queryAll(viewportEl, 'img');
  await Promise.all(images.map(waitForImage));

  try {
    restorers.push(...await replaceElementsWithPlaceholders(overlays, renderOverlay, createPlaceholderFn, true));
    restorers.push(...await replaceElementsWithPlaceholders(queryAll(viewportEl, 'img'), renderImage, createPlaceholderFn, false));
    restorers.push(...await replaceElementsWithPlaceholders(queryAll(viewportEl, 'canvas'), renderCanvas, createPlaceholderFn, true));

    await nextFrame();
    await nextFrame();
    return await toBlobImpl(viewportEl, options);
  } finally {
    restorers.reverse().forEach((restore) => restore());
  }
}
