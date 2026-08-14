import { useState, useEffect } from "react";
import { useAuth } from "../context/AuthContext.jsx";
import "./DocumentPreviewModal.css";

export default function DocumentPreviewModal({ uploadId, onClose }) {
  const { token, handle401 } = useAuth();
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const API_BASE = "http://localhost:8000";

  useEffect(() => {
    if (!uploadId) return;

    setLoading(true);
    setError("");

    fetch(`${API_BASE}/uploads/${uploadId}/preview`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => {
        if (handle401(res)) return;
        if (!res.ok) throw new Error("Failed to load document preview");
        return res.json();
      })
      .then((data) => {
        if (data) setPreview(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, [uploadId, token]);

  // Close on Escape key
  useEffect(() => {
    function handleKey(e) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [onClose]);

  if (!uploadId) return null;

  const isProcessing = preview?.status?.toLowerCase() === "processing";

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>📄 Document Preview</h3>
          <button className="modal-close-btn" onClick={onClose} title="Close">
            ✕
          </button>
        </div>

        <div className="modal-body">
          {loading && <p className="modal-status-text">Loading preview...</p>}
          {error && <p className="modal-status-text error-text">{error}</p>}

          {!loading && !error && preview && (
            <>
              <div className="modal-file-title">
                <span className="modal-file-icon">📄</span>
                <div>
                  <p className="modal-filename" title={preview.filename}>
                    {preview.filename}
                  </p>
                  <span className="modal-type-badge">{preview.file_type}</span>
                </div>
              </div>

              <div className="info-grid">
                <div className="info-item">
                  <span className="info-item-label">Upload Date</span>
                  <span className="info-item-value">
                    {preview.upload_date
                      ? new Date(preview.upload_date).toLocaleDateString("en-US", {
                          month: "short",
                          day: "numeric",
                          year: "numeric",
                        })
                      : "Unknown"}
                  </span>
                </div>
                <div className="info-item">
                  <span className="info-item-label">File Size</span>
                  <span className="info-item-value">
                    {preview.file_size || "—"}
                  </span>
                </div>
                <div className="info-item">
                  <span className="info-item-label">Status</span>
                  <span className="info-item-value">
                    <span className={`status-dot ${isProcessing ? "pulse-dot" : "solid-dot"}`} />
                    {isProcessing ? "Processing" : "Ready"}
                  </span>
                </div>
                <div className="info-item">
                  <span className="info-item-label">File Type</span>
                  <span className="info-item-value">{preview.file_type}</span>
                </div>
              </div>

              <div className="metadata-section">
                <h4>🔍 Extracted Metadata</h4>
                <div className="info-grid">
                  <div className="info-item">
                    <span className="info-item-label">Pages</span>
                    <span className="info-item-value">
                      {preview.page_count != null ? `${preview.page_count} pages` : "—"}
                    </span>
                  </div>
                  <div className="info-item">
                    <span className="info-item-label">Word Count</span>
                    <span className="info-item-value">
                      {preview.word_count != null
                        ? `${preview.word_count.toLocaleString()} words`
                        : "—"}
                    </span>
                  </div>
                </div>
                {(preview.page_count == null || preview.word_count == null) && (
                  <p className="metadata-note">
                    ⏳ Some metadata isn't available yet — Team Lambda's pipeline
                    will populate richer document details once ready.
                  </p>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}