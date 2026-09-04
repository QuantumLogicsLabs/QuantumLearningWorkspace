import { useState, useRef } from "react";
import { useAuth } from "../context/AuthContext.jsx";

function UploadView({ onUploadSuccess }) {
  const { token, handle401 } = useAuth();
  const fileInputRef = useRef(null);

  const [selectedFile, setSelectedFile] = useState(null);
  const [status, setStatus] = useState("");
  const [message, setMessage] = useState("");

  function handleFileChange(event) {
    const file = event.target.files[0];
    setSelectedFile(file);
    setStatus("");
    setMessage("");
  }

  async function handleUploadClick() {
    if (!selectedFile) {
      setStatus("error");
      setMessage("Please choose a file first.");
      return;
    }

    if (!selectedFile.name.toLowerCase().endsWith(".pdf")) {
      setStatus("error");
      setMessage("Only PDF files (.pdf) are currently supported.");
      return;
    }

    const MAX_SIZE = 10 * 1024 * 1024;
    if (selectedFile.size > MAX_SIZE) {
      setStatus("error");
      setMessage("File size exceeds the 10MB limit.");
      return;
    }

    setStatus("uploading");
    setMessage("");

    const formData = new FormData();
    formData.append("file", selectedFile);

    const API_BASE = `http://${window.location.hostname}:8001`;

    try {
      const response = await fetch(`${API_BASE}/upload`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      if (handle401(response)) return;

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || "Upload failed");
      }

      setStatus("success");
      setMessage(`"${selectedFile.name}" uploaded successfully!`);
      setSelectedFile(null);
      
      // Clear file input
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }

      if (onUploadSuccess) onUploadSuccess();
    } catch (err) {
      setStatus("error");
      const errorMsg = err.message === "Failed to fetch"
        ? "Network error — failed to upload file. Please check your connection."
        : (err.message || "Something went wrong while uploading.");
      setMessage(errorMsg);
    }
  }

  return (
    <div className="upload-container">
      <h3>Upload Document</h3>
      <p className="upload-subtitle">Add PDFs to your knowledge base</p>
      
      <div className="upload-controls">
        <label className="file-input-label">
          <span>{selectedFile ? "Change File" : "Choose PDF"}</span>
          <input 
            type="file" 
            ref={fileInputRef}
            onChange={handleFileChange} 
            accept=".pdf" 
            className="file-input-hidden"
          />
        </label>

        <button
          onClick={handleUploadClick}
          className="upload-submit-btn"
          disabled={status === "uploading" || !selectedFile}
        >
          {status === "uploading" ? "Uploading..." : "Upload"}
        </button>
      </div>

      {selectedFile && status !== "success" && (
        <div className="selected-file-info">
          <span className="file-info-icon">📄</span>
          <span className="file-info-name" title={selectedFile.name}>{selectedFile.name}</span>
        </div>
      )}

      {message && (
        <div className={`upload-msg ${status === "error" ? "error-msg" : "success-msg"}`}>
          {message}
        </div>
      )}
    </div>
  );
}

export default UploadView;