import React, { useState, useEffect, useCallback } from 'react';
import * as api from './api';

/**
 * Server-side file browser modal.
 *
 * Props:
 *   onSelect(absolutePath) — called when user picks a file
 *   onClose()              — called when user dismisses the dialog
 */
export default function FileBrowser({ onSelect, onClose }) {
  const [path, setPath] = useState('');
  const [parent, setParent] = useState(null);
  const [dirs, setDirs] = useState([]);
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const navigate = useCallback(async (dir) => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.browse(dir);
      setPath(data.path);
      setParent(data.parent);
      setDirs(data.dirs);
      setFiles(data.files);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  // Start at home directory on mount
  useEffect(() => {
    navigate(null);
  }, [navigate]);

  return (
    <div className="fb-backdrop" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="fb-dialog">
        {/* Header */}
        <div className="fb-header">
          <span className="fb-path">{path}</span>
          <button className="fb-close" onClick={onClose}>✕</button>
        </div>

        {/* File list */}
        <div className="fb-list">
          {loading && <div className="fb-loading">Loading…</div>}
          {error && <div className="fb-loading">Error: {error}</div>}

          {!loading && !error && (
            <>
              {/* Parent directory */}
              {parent && (
                <div className="fb-entry fb-dir" onClick={() => navigate(parent)}>
                  ⬆ ..
                </div>
              )}

              {/* Directories */}
              {dirs.map((d) => (
                <div
                  key={d}
                  className="fb-entry fb-dir"
                  onClick={() => navigate(path + '/' + d)}
                >
                  📁 {d}
                </div>
              ))}

              {/* Files */}
              {files.map((f) => (
                <div
                  key={f}
                  className="fb-entry fb-file"
                  onClick={() => { onSelect(path + '/' + f); onClose(); }}
                >
                  {f}
                </div>
              ))}

              {dirs.length === 0 && files.length === 0 && (
                <div className="fb-loading">Empty directory</div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
