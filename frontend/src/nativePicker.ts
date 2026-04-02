const SUPPORTED_EXTENSIONS = new Set([
  '.png', '.jpg', '.jpeg', '.tiff', '.tif', '.bmp',
  '.npy', '.npz',
  '.gwy', '.sxm', '.ibw',
  '.h5', '.hdf5',
  '.ttf', '.otf', '.woff', '.woff2',
]);

const FILE_ACCEPT = [...SUPPORTED_EXTENSIONS].join(',');

function hasSupportedExtension(name: string): boolean {
  const dot = name.lastIndexOf('.');
  if (dot < 0) return false;
  return SUPPORTED_EXTENSIONS.has(name.slice(dot).toLowerCase());
}

function normalizeRelativePath(path: string) {
  return String(path || '').replace(/\\/g, '/').replace(/^\/+/, '');
}

function pickWithInput({ directory = false } = {}): Promise<File[]> {
  return new Promise((resolve) => {
    const input = document.createElement('input');
    input.type = 'file';
    input.style.position = 'fixed';
    input.style.left = '-9999px';
    if (directory) {
      input.multiple = true;
      input.setAttribute('webkitdirectory', '');
      input.setAttribute('directory', '');
    } else {
      input.accept = FILE_ACCEPT;
    }

    const cleanup = () => {
      input.remove();
    };

    input.addEventListener('change', () => {
      const files = Array.from(input.files || []);
      cleanup();
      resolve(files);
    }, { once: true });

    document.body.appendChild(input);
    input.click();
  });
}

interface FileEntry {
  file: File;
  relativePath: string;
}

async function collectDirectoryEntries(handle: FileSystemDirectoryHandle, prefix: string = handle.name): Promise<FileEntry[]> {
  const entries: FileEntry[] = [];
  for await (const [name, child] of (handle as any).entries()) {
    const relativePath = prefix ? `${prefix}/${name}` : name;
    if (child.kind === 'file') {
      if (!hasSupportedExtension(name)) continue;
      const file = await child.getFile();
      entries.push({ file, relativePath: normalizeRelativePath(relativePath) });
      continue;
    }
    if (child.kind === 'directory') {
      entries.push(...await collectDirectoryEntries(child, relativePath));
    }
  }
  return entries;
}

export async function pickNativeFileSelection() {
  try {
    if (typeof (window as any).showOpenFilePicker === 'function') {
      const [handle] = await (window as any).showOpenFilePicker({
        multiple: false,
        types: [{
          description: 'Supported files',
          accept: {
            'application/octet-stream': ['.npy', '.npz', '.gwy', '.sxm', '.ibw', '.ttf', '.otf', '.woff', '.woff2'],
            'image/*': ['.png', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff'],
          },
        }],
      });
      if (!handle) return null;
      const file = await handle.getFile();
      return {
        rootName: file.name,
        entries: [{ file, relativePath: normalizeRelativePath(file.name) }],
      };
    }
  } catch (error: any) {
    if (error?.name !== 'AbortError') throw error;
    return null;
  }

  const files = await pickWithInput({ directory: false });
  if (files.length === 0) return null;
  return {
    rootName: files[0].name,
    entries: [{ file: files[0], relativePath: normalizeRelativePath(files[0].name) }],
  };
}

export async function pickNativeDirectorySelection() {
  try {
    if (typeof (window as any).showDirectoryPicker === 'function') {
      const handle: FileSystemDirectoryHandle = await (window as any).showDirectoryPicker();
      if (!handle) return null;
      const entries = await collectDirectoryEntries(handle, handle.name);
      return {
        rootName: handle.name,
        entries,
      };
    }
  } catch (error: any) {
    if (error?.name !== 'AbortError') throw error;
    return null;
  }

  const allFiles = await pickWithInput({ directory: true });
  if (allFiles.length === 0) return null;
  const files = allFiles.filter((f) => hasSupportedExtension(f.name));
  if (files.length === 0) return null;
  const entries = files.map((file: File) => ({
    file,
    relativePath: normalizeRelativePath(file.webkitRelativePath || file.name),
  }));
  const rootName = entries[0]?.relativePath.split('/')[0] || '';
  if (!rootName) return null;
  return {
    rootName,
    entries,
  };
}
