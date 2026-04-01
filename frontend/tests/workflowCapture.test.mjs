import test from 'node:test';
import assert from 'node:assert/strict';

import { OVERLAY_CAPTURE_SELECTORS, captureViewportBlob } from '../src/workflowCapture.ts';

function makeElement(name, { tagName = 'DIV', width = 160, height = 90, src = '' } = {}) {
  return {
    name,
    tagName,
    src,
    currentSrc: src,
    complete: true,
    naturalWidth: 1,
    clientWidth: width,
    clientHeight: height,
    parentNode: null,
    getBoundingClientRect() {
      return { width, height };
    },
  };
}

function makeParent(initialChild) {
  return {
    currentChild: initialChild,
    replaceChild(nextChild, prevChild) {
      assert.equal(this.currentChild, prevChild);
      this.currentChild = nextChild;
      nextChild.parentNode = this;
    },
  };
}

function makeViewport({ overlay, image, canvas }) {
  return {
    querySelectorAll(selector) {
      if (selector === '.lineplot-overlay') {
        return overlay.parentNode?.currentChild === overlay ? [overlay] : [];
      }
      if (selector === '.cs-overlay' || selector === '.crop-overlay') {
        return [];
      }
      if (selector === 'img') {
        return image.parentNode?.currentChild === image ? [image] : [];
      }
      if (selector === 'canvas') {
        return canvas.parentNode?.currentChild === canvas ? [canvas] : [];
      }
      return [];
    },
  };
}

test('captureViewportBlob rasterizes custom overlays before the final workflow snapshot', async () => {
  const overlay = makeElement('overlay', { width: 320, height: 220 });
  const image = makeElement('image', { tagName: 'IMG', width: 180, height: 120, src: 'data:image/png;base64,abc' });
  const canvas = makeElement('canvas', { tagName: 'CANVAS', width: 128, height: 128 });
  canvas.toDataURL = () => 'data:image/png;base64,canvas';

  const overlayParent = makeParent(overlay);
  const imageParent = makeParent(image);
  const canvasParent = makeParent(canvas);
  overlay.parentNode = overlayParent;
  image.parentNode = imageParent;
  canvas.parentNode = canvasParent;

  const selectorsSeen = [];
  const viewport = makeViewport({ overlay, image, canvas });
  const blob = await captureViewportBlob(viewport, { width: 800, height: 600 }, {
    queryAll(root, selector) {
      selectorsSeen.push(selector);
      return root.querySelectorAll(selector);
    },
    waitForImageElement: async () => {},
    renderOverlayToDataUrl: async (el) => `data:image/png;base64,overlay-${el.name}`,
    renderImageToDataUrl: async (el) => `data:image/png;base64,image-${el.name}`,
    renderCanvasToDataUrl: async (el) => `data:image/png;base64,canvas-${el.name}`,
    createPlaceholder: (el, dataUrl) => ({ placeholderFor: el.name, dataUrl, parentNode: null }),
    nextFrame: async () => {},
    toBlobImpl: async (target) => {
      if (target === viewport) {
        assert.notEqual(overlayParent.currentChild, overlay);
        assert.notEqual(imageParent.currentChild, image);
        assert.notEqual(canvasParent.currentChild, canvas);
        return new Blob(['viewport'], { type: 'image/png' });
      }
      throw new Error('Unexpected element capture path');
    },
  });

  assert.equal(await blob.text(), 'viewport');
  assert.equal(overlayParent.currentChild, overlay);
  assert.equal(imageParent.currentChild, image);
  assert.equal(canvasParent.currentChild, canvas);
  assert.deepEqual(
    selectorsSeen.filter((selector) => OVERLAY_CAPTURE_SELECTORS.includes(selector)),
    OVERLAY_CAPTURE_SELECTORS,
  );
});

test('captureViewportBlob restores live elements when final capture fails', async () => {
  const overlay = makeElement('overlay', { width: 320, height: 220 });
  const image = makeElement('image', { tagName: 'IMG', width: 180, height: 120, src: 'data:image/png;base64,abc' });
  const canvas = makeElement('canvas', { tagName: 'CANVAS', width: 128, height: 128 });
  canvas.toDataURL = () => 'data:image/png;base64,canvas';

  const overlayParent = makeParent(overlay);
  const imageParent = makeParent(image);
  const canvasParent = makeParent(canvas);
  overlay.parentNode = overlayParent;
  image.parentNode = imageParent;
  canvas.parentNode = canvasParent;

  const viewport = makeViewport({ overlay, image, canvas });

  await assert.rejects(
    captureViewportBlob(viewport, { width: 800, height: 600 }, {
      queryAll: (root, selector) => root.querySelectorAll(selector),
      waitForImageElement: async () => {},
      renderOverlayToDataUrl: async () => 'data:image/png;base64,overlay',
      renderImageToDataUrl: async () => 'data:image/png;base64,image',
      renderCanvasToDataUrl: async () => 'data:image/png;base64,canvas',
      createPlaceholder: (el) => ({ placeholderFor: el.name, parentNode: null }),
      nextFrame: async () => {},
      toBlobImpl: async (target) => {
        if (target === viewport) throw new Error('capture failed');
        return new Blob(['unexpected'], { type: 'image/png' });
      },
    }),
    /capture failed/,
  );

  assert.equal(overlayParent.currentChild, overlay);
  assert.equal(imageParent.currentChild, image);
  assert.equal(canvasParent.currentChild, canvas);
});
