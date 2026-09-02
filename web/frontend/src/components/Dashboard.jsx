import { useState, useEffect } from "react";
import { useAuth } from "../context/AuthContext.jsx";
import { useToast } from "../context/ToastContext.jsx";
import ProfileView from "./ProfileView.jsx";
import QuizView from "./QuizView.jsx";
import QuizResultsView from "./QuizResultsView.jsx";
import FlashcardsView from "./FlashcardsView.jsx";
import LogoutModal from "./LogoutModal.jsx";
import ThemeToggle from "./ThemeToggle.jsx";
import "./Dashboard.css";
import DocumentPreviewModal from "./DocumentPreviewModal.jsx";

// ─── Sub-Components ──────────────────────────────────────────────────────────

function SidebarNav({ activeTab, setActiveTab, onRequestLogout }) {
  const { userEmail } = useAuth();
  const initial = userEmail ? userEmail[0].toUpperCase() : "U";

  const navItems = [
    { id: "documents", icon: "📄", label: "Documents" },
    { id: "chat", icon: "💬", label: "AI Chat" },
    { id: "flashcards", icon: "🎴", label: "Flashcards" },
    { id: "quiz", icon: "🎯", label: "Quiz" },
    { id: "results", icon: "📊", label: "Results" },
    { id: "graph", icon: "🗺️", label: "Knowledge Graph" },
  ];

  return (
    <aside className="sidebar-nav">
      {/* Logo */}
      <div className="sidebar-logo-area">
        <span className="logo-icon">🧠</span>
      </div>

      {/* Navigation Items */}
      <nav className="sidebar-nav-items">
        {navItems.map((item) => (
          <button
            key={item.id}
            className={`nav-btn ${activeTab === item.id ? "active" : ""}`}
            onClick={() => setActiveTab(item.id)}
            title={item.label}
          >
            <span className="nav-icon">{item.icon}</span>
            <span className="nav-tooltip">{item.label}</span>
            {activeTab === item.id && (
              <span className="nav-indicator"></span>
            )}
          </button>
        ))}
      </nav>

      {/* Bottom: User + Logout */}
      <div className="sidebar-bottom">
        <div
          className={`user-avatar-circle ${activeTab === "profile" || activeTab === "settings" ? "active-profile-avatar" : ""}`}
          onClick={() => setActiveTab("profile")}
          style={{ cursor: "pointer", position: "relative" }}
        >
          {initial}
          <span className="nav-tooltip">Profile</span>
        </div>
        <button
          className="logout-icon-btn"
          onClick={onRequestLogout}
          title="Logout"
          type="button"
        >
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="#ef4444" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
            <polyline points="16 17 21 12 16 7" />
            <line x1="21" y1="12" x2="9" y2="12" />
          </svg>
        </button>
      </div>
    </aside>
  );
}

function TopBar({ activeTab }) {
  const { userEmail } = useAuth();
  const initial = userEmail ? userEmail[0].toUpperCase() : "U";
  const displayName = userEmail ? userEmail.split("@")[0] : "Student User";

  const pageTitles = {
    documents: {
      title: "Your Dashboard",
      subtitle: "Upload, manage, and interact with your study materials",
    },
    chat: {
      title: "AI Assistant",
      subtitle: "Ask questions about your uploaded study materials",
    },
    flashcards: {
      title: "AI Flashcards",
      subtitle: "Active recall study cards to test and reinforce your knowledge",
    },
    quiz: {
      title: "Quiz",
      subtitle: "Test your knowledge with AI-generated quizzes",
    },
    results: {
      title: "Quiz Results",
      subtitle: "View your quiz history and track your progress",
    },
    graph: {
      title: "Knowledge Graph",
      subtitle: "Visualize connections between concepts in your materials",
    },
    profile: {
      title: "Profile",
      subtitle: "Manage your account settings and preferences",
    },
    settings: {
      title: "Profile",
      subtitle: "Manage your account settings and preferences",
    },
  };

  const { title, subtitle } = pageTitles[activeTab] || pageTitles.documents;

  return (
    <header className="top-bar">
      <div className="top-bar-info">
        <h1 className="top-bar-title">{title}</h1>
        <p className="top-bar-subtitle">{subtitle}</p>
      </div>
      <div className="top-bar-right" style={{ display: "flex", alignItems: "center", gap: "14px" }}>
        <ThemeToggle />
        <div
          className="user-badge"
          style={{
            display: "flex",
            alignItems: "center",
            gap: "10px",
            padding: "8px 14px",
            background: "var(--color-surface-hover, rgba(124,58,237,0.06))",
            border: "1px solid var(--color-card-border, rgba(124,58,237,0.15))",
            borderRadius: "10px",
          }}
        >
          <div
            style={{
              width: "28px",
              height: "28px",
              background: "linear-gradient(135deg, #7c3aed, #ec4899)",
              borderRadius: "50%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "0.72rem",
              fontWeight: "700",
              color: "white",
            }}
          >
            {initial}
          </div>
          <span style={{ fontSize: "0.85rem", fontWeight: "500", color: "var(--color-text-primary)" }}>
            {displayName}
          </span>
        </div>
      </div>
    </header>
  );
}

function DocumentsView({ onAskAboutDocument }) {
  const { token, handle401 } = useAuth();
  const { showToast } = useToast();
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [deletingId, setDeletingId] = useState(null);
  const [fileToDelete, setFileToDelete] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadMsg, setUploadMsg] = useState("");
  const [uploadStatus, setUploadStatus] = useState("");
  const [previewId, setPreviewId] = useState(null);

  // Search, Filter & Sort
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("All");
  const [sortOption, setSortOption] = useState("Newest");

  
  const API_BASE = import.meta.env.VITE_API_BASE_URL;

  function fetchUploads(isSilent = false) {
    if (!isSilent) {
      setLoading(true);
      setError("");
    }
    fetch(`${API_BASE}/uploads`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => {
        if (handle401(res)) return;
        if (!res.ok) throw new Error("Failed to fetch uploads");
        return res.json();
      })
      .then((data) => {
        if (data) setFiles(data);
        if (!isSilent) setLoading(false);
      })
      .catch((err) => {
        if (!isSilent) setError(err.message);
        if (!isSilent) setLoading(false);
      });
  }

  function handleUpload() {
    if (!selectedFile) {
      setUploadMsg("Please choose a file first.");
      setUploadStatus("error");
      showToast("Please choose a file first.", "error");
      return;
    }

    if (!selectedFile.name.toLowerCase().endsWith(".pdf")) {
      const msg = "Only PDF files (.pdf) are currently supported.";
      setUploadMsg(msg);
      setUploadStatus("error");
      showToast(msg, "error");
      return;
    }

    const MAX_SIZE = 10 * 1024 * 1024;
    if (selectedFile.size > MAX_SIZE) {
      const msg = "File size exceeds the 10MB limit.";
      setUploadMsg(msg);
      setUploadStatus("error");
      showToast(msg, "error");
      return;
    }

    setUploading(true);
    setUploadMsg("");

    const formData = new FormData();
    formData.append("file", selectedFile);

    fetch(`${API_BASE}/upload`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: formData,
    })
      .then(async (res) => {
        if (handle401(res)) return;
        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || "Upload failed");
        }
        return res.json();
      })
      .then((data) => {
        if (!data) return;
        setUploadMsg(`"${selectedFile.name}" uploaded successfully! Processing started...`);
        setUploadStatus("success");
        showToast(`"${selectedFile.name}" uploaded successfully!`, "success");
        setSelectedFile(null);
        fetchUploads(true);
      })
      .catch((err) => {
        const errorText = err.message === "Failed to fetch"
          ? "Network error — failed to upload file. Please check your connection."
          : (err.message || "Something went wrong.");
        setUploadMsg(errorText);
        setUploadStatus("error");
        showToast(errorText, "error");
      })
      .finally(() => {
        setUploading(false);
      });
  }

  function handleDelete(uploadId, filename) {
    setDeletingId(uploadId);
    fetch(`${API_BASE}/uploads/${uploadId}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => {
        if (handle401(res)) return;
        if (!res.ok) throw new Error("Failed to delete file");
        setFiles((prev) => prev.filter((f) => f.id !== uploadId));
        showToast(`"${filename}" deleted`, "success");
      })
      .catch((err) => {
        setError(err.message);
        showToast(err.message || "Failed to delete file", "error");
      })
      .finally(() => {
        setDeletingId(null);
      });
  }

  useEffect(() => {
    fetchUploads();
    const interval = setInterval(() => {
      fetchUploads(true);
    }, 3000);

    return () => clearInterval(interval);
  }, [token]);

  // Search, Filter & Sort
  const displayedFiles = [...files]
    .filter((file) => {
      if (statusFilter === "All") return true;
      return (file.status || "").toLowerCase() === statusFilter.toLowerCase();
    })
    .filter((file) =>
      file.filename.toLowerCase().includes(searchTerm.toLowerCase())
    )
    .sort((a, b) => {
      switch (sortOption) {
        case "Newest":
          return new Date(b.upload_date) - new Date(a.upload_date);

        case "Oldest":
          return new Date(a.upload_date) - new Date(b.upload_date);

        case "A-Z":
          return a.filename.localeCompare(b.filename);

        case "Z-A":
          return b.filename.localeCompare(a.filename);

        default:
          return 0;
      }
    });

  return (
    <div className="documents-view">
      {/* Upload Card */}
      <div className="upload-card">
        <h3>Upload Document</h3>
        <p className="upload-subtitle">Add PDFs, documents, or lecture notes to your knowledge base</p>
        <div className="upload-row">
          <label className="file-input-label">
            <span>{selectedFile ? selectedFile.name : "Choose File"}</span>
            <input
              type="file"
              onChange={(e) => {
                setSelectedFile(e.target.files[0]);
                setUploadMsg("");
                setUploadStatus("");
              }}
              accept=".pdf,.txt,.doc,.docx"
              className="file-input-hidden"
            />
          </label>
          <button
            className="upload-submit-btn"
            onClick={handleUpload}
            disabled={!selectedFile || uploading}
          >
            {uploading ? "Uploading..." : "Upload"}
          </button>
        </div>
        {uploadMsg && (
          <div className={`upload-msg ${uploadStatus === "error" ? "error-msg" : "success-msg"}`}>
            {uploadMsg}
          </div>
        )}
      </div>

      {/* File List */}
      <div className="file-list-card">
        <div className="file-list-header">
          <h3>Knowledge Library</h3>
          <div className="header-actions">
            <span className="file-count-badge">{files.length} file{files.length !== 1 ? "s" : ""}</span>
            <button className="btn-refresh" onClick={() => fetchUploads(false)} title="Refresh">
              🔄
            </button>
          </div>
        </div>

        <div className="file-controls">
          <input
            type="text"
            placeholder="Search by filename..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="All">All</option>
            <option value="Processing">Processing</option>
            <option value="Ready">Ready</option>
          </select>

          <select
            value={sortOption}
            onChange={(e) => setSortOption(e.target.value)}
          >
            <option value="Newest">Newest First</option>
            <option value="Oldest">Oldest First</option>
            <option value="A-Z">A-Z</option>
            <option value="Z-A">Z-A</option>
          </select>
        </div>

        {loading && (
          <div className="loading-state">
            <div className="loading-dots">
              <span></span><span></span><span></span>
            </div>
            <p className="loading-text">Loading your documents...</p>
            <p className="loading-subtext">Fetching your uploaded study materials</p>
          </div>
        )}

        {!loading && error && (
          <div className="error-state">
            <p>{error}</p>
            <button onClick={() => fetchUploads(false)}>Retry</button>
          </div>
        )}

        {!loading && !error && files.length === 0 && (
          <div className="empty-state">
            <span className="empty-icon">📚</span>
            <p className="empty-title">No documents yet - upload your first file to get started</p>
            <p className="empty-subtitle">Upload your first PDF to start studying with AI</p>
          </div>
        )}

        {!loading && !error && files.length > 0 && (
          <div className="file-rows">
            {displayedFiles.map((file) => {
              const isDeleting = deletingId === file.id;
              const statusRaw = (file.status || "Ready").toLowerCase();
              const isProcessing = statusRaw === "processing";
              const displayStatus = isProcessing ? "Processing" : "Ready";

              const getFileType = (mime, filename) => {
                if (mime && mime.includes("/")) {
                  const subtype = mime.split("/")[1]?.split(".")[0].toUpperCase() || "";
                  if (subtype.includes("OFFICE") || subtype.includes("WORD") || subtype.includes("OPENXML") || subtype.includes("VND")) {
                    return "DOCX";
                  }
                  if (subtype.length <= 6) return subtype;
                }
                const ext = filename.split(".").pop()?.toUpperCase() || "PDF";
                if (ext.length > 6) return "FILE";
                return ext;
              };

              return (
                <div
                  key={file.id}
                  className={`file-row ${isDeleting ? "deleting" : ""}`}
                >
                  <div className="file-icon-box">📄</div>
                  <div className="file-info">
                    <span className="file-name-text" title={file.filename}>
                      {file.filename}
                    </span>
                    <span className="file-type-text">
                      {getFileType(file.file_type, file.filename)}
                    </span>
                  </div>
                  <span className="file-date-text">
                    {file.upload_date
                      ? new Date(file.upload_date).toLocaleDateString("en-US", {
                          month: "short", day: "numeric", year: "numeric",
                        })
                      : "Unknown"}
                  </span>

                  <div className={`status-pill ${isProcessing ? "status-processing" : "status-ready"}`}>
                    <span className={`status-dot ${isProcessing ? "pulse-dot" : "solid-dot"}`}></span>
                    {displayStatus}
                  </div>
                  <button
                    className="btn-preview-file"
                    onClick={() => setPreviewId(file.id)}
                    title="Preview document details"
                  >
                    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7z" />
                      <circle cx="12" cy="12" r="3" fill="currentColor" />
                    </svg>
                  </button>

                  <button
                    className={`btn-ask-doc ${isProcessing ? "disabled" : ""}`}
                    onClick={() => !isProcessing && onAskAboutDocument(file.filename)}
                    disabled={isProcessing}
                    title={
                      isProcessing
                        ? "File is currently processing and not yet searchable"
                        : `Ask questions about ${file.filename}`
                    }
                  >
                    💬 Ask AI
                  </button>

                  <button
                    className="btn-delete-file"
                    onClick={() => setFileToDelete(file)}
                    disabled={isDeleting}
                    title="Delete file"
                  >
                    {isDeleting ? (
                      <span className="mini-spinner"></span>
                    ) : (
                      <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: "#ef4444" }}>
                        <polyline points="3 6 5 6 21 6" />
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                        <line x1="10" y1="11" x2="10" y2="17" />
                        <line x1="14" y1="11" x2="14" y2="17" />
                      </svg>
                    )}
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Delete Confirmation Modal */}
      {fileToDelete && (
        <div className="modal-backdrop" onClick={() => setFileToDelete(null)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <button
              className="modal-close-btn"
              onClick={() => setFileToDelete(null)}
              title="Close"
            >
              ✕
            </button>
            <div className="modal-icon-wrap">
              <span className="modal-warning-icon">⚠️</span>
            </div>
            <h3 className="modal-title">Delete Document</h3>
            <p className="modal-desc">
              Are you sure you want to delete <strong className="modal-filename">"{fileToDelete.filename}"</strong>?
            </p>
            <p className="modal-subtext">
              This action is <strong>irreversible</strong> and cannot be undone.
            </p>
            <div className="modal-actions">
              <button
                className="modal-btn-cancel"
                onClick={() => setFileToDelete(null)}
                disabled={deletingId === fileToDelete.id}
              >
                Cancel
              </button>
              <button
                className="modal-btn-delete"
                onClick={() => {
                  const idToDelete = fileToDelete.id;
                  const idFilename = fileToDelete.filename;
                  setFileToDelete(null);
                  handleDelete(idToDelete, idFilename);
                }}
                disabled={deletingId === fileToDelete.id}
              >
                {deletingId === fileToDelete.id ? "Deleting..." : "Delete"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Preview Modal */}
      {previewId && (
        <DocumentPreviewModal
          uploadId={previewId}
          onClose={() => setPreviewId(null)}
        />
      )}
    </div>
  );
}

function ChatView({ targetDocument, setTargetDocument }) {
  const { token, userEmail, handle401 } = useAuth();
  const [files, setFiles] = useState([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  
  const API_BASE = import.meta.env.VITE_API_BASE_URL;

  const getStorageKey = () => {
    return userEmail ? `studymind_chat_history_${userEmail}` : "studymind_chat_history";
  };

  const welcomeMessage = {
    role: "assistant",
    content:
      "Hello! I'm your StudyMind AI assistant. Select a document or ask me anything about your uploaded study materials.",
    timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
  };

  const [messages, setMessages] = useState(() => {
    try {
      const saved =
        localStorage.getItem(getStorageKey()) ||
        localStorage.getItem("studymind_chat_history");
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) return parsed;
      }
    } catch {}
    return [welcomeMessage];
  });

  // Save history to localStorage whenever messages change
  useEffect(() => {
    if (messages && messages.length > 0) {
      try {
        const key = getStorageKey();
        localStorage.setItem(key, JSON.stringify(messages));
        localStorage.setItem("studymind_chat_history", JSON.stringify(messages));
      } catch {}
    }
  }, [messages, userEmail]);

  // Load past conversation from backend on initial mount
  useEffect(() => {
    fetch(`${API_BASE}/chat-history`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => {
        if (handle401(res)) return;
        if (!res.ok) throw new Error("Failed to load chat history");
        return res.json();
      })
      .then((data) => {
        if (data && Array.isArray(data) && data.length > 0) {
          const formatted = data.map((msg) => ({
            role: msg.role,
            content: msg.content,
            sources: msg.sources || [],
            timestamp: msg.timestamp
              ? new Date(msg.timestamp).toLocaleTimeString([], {
                  hour: "2-digit",
                  minute: "2-digit",
                })
              : new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
          }));
          setMessages(formatted);
        }
      })
      .catch(() => {});
  }, [token]);

  // Save one message to the backend (fire-and-forget)
  function saveMessage(message) {
    fetch(`${API_BASE}/chat-history`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        role: message.role,
        content: message.content,
        sources: message.sources || null,
      }),
    }).catch(() => {
      // Silent fail — losing a history save shouldn't break the chat UX
    });
  }

  // Fetch uploads to populate document scope selector
  function fetchUploads() {
    fetch(`${API_BASE}/uploads`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => {
        if (handle401(res)) return;
        if (res.ok) return res.json();
      })
      .then((data) => {
        if (data) setFiles(data);
      })
      .catch(() => {});
  }

  useEffect(() => {
    fetchUploads();
    const interval = setInterval(fetchUploads, 3000);
    return () => clearInterval(interval);
  }, [token]);

  const scrollToBottom = () => {
    const container = document.getElementById("chat-messages-scroll");
    if (container) container.scrollTop = container.scrollHeight;
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleSend = async (e) => {
    e?.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = {
      role: "user",
      content: input.trim(),
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMessage]);
    saveMessage(userMessage);
    setInput("");
    setIsLoading(true);

    const apiHistory = messages.map((msg) => ({
      role: msg.role === "assistant" ? "assistant" : "user",
      content: msg.content,
    }));

    try {
      const response = await fetch(`${API_BASE}/ask`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          question: userMessage.content,
          history: apiHistory,
          top_k: 4,
          include_sources: true,
          filename: targetDocument || null,
        }),
      });

      if (handle401(response)) return;
      if (!response.ok) throw new Error("Failed to connect to AI server");

      const data = await response.json();

      const assistantMessage = {
        role: "assistant",
        content: data.answer,
        sources: data.sources || [],
        timing: data.timing || null,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };

      setMessages((prev) => [...prev, assistantMessage]);
      saveMessage(assistantMessage);
    } catch (err) {
      const errorMessage = {
        role: "assistant",
        content: "Sorry, I had trouble reaching the AI server. Please make sure the backend is running.",
        isError: true,
        failedQuestion: userMessage.content,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const clearHistory = () => {
    if (window.confirm("Are you sure you want to clear your conversation history?")) {
      fetch(`${API_BASE}/chat-history`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      })
        .then((res) => {
          if (handle401(res)) return;
          setMessages([welcomeMessage]);
        })
        .catch(() => {
          setMessages([welcomeMessage]);
        });
    }
  };

  return (
    <div className="chat-view">
      {/* Chat Header Bar */}
      <div className="chat-header-bar">
        <div className="chat-doc-selector-container">
          <span className="selector-icon">🎯 Scope:</span>
          <select
            value={targetDocument || ""}
            onChange={(e) => setTargetDocument(e.target.value || null)}
            className="chat-doc-select"
          >
            <option value="">All Documents</option>
            {files.map((file) => {
              const isProcessing = (file.status || "").toLowerCase() === "processing";
              return (
                <option key={file.id} value={file.filename} disabled={isProcessing}>
                  {file.filename} {isProcessing ? "⏳ (Processing - Not Searchable)" : "✓ (Ready)"}
                </option>
              );
            })}
          </select>
          {targetDocument && (
            <button
              className="btn-clear-target-doc"
              onClick={() => setTargetDocument(null)}
              title="Clear active document filter"
            >
              ✕ Clear Filter
            </button>
          )}
        </div>

        <div className="chat-header-right">
          <div className="chat-status-info">
            <span className="status-dot-green"></span>
            <span className="status-text">Online</span>
          </div>
          <button className="btn-clear-chat" onClick={clearHistory}>
            Clear
          </button>
        </div>
      </div>

      {targetDocument && (
        <div className="target-doc-banner">
          <span>Asking specifically about <strong>"{targetDocument}"</strong></span>
        </div>
      )}

      <div className="chat-messages-scroll" id="chat-messages-scroll">
        {(messages || []).map((msg, index) => (
            <div key={index} className={`msg-wrapper ${msg.role === "user" ? "msg-user" : "msg-ai"}`}>
              <div
                className={`msg-bubble ${
                  msg.role === "user" ? "bubble-user" : "bubble-ai"
                } ${msg.isError ? "bubble-error" : ""}`}
              >
                <div className="msg-content">{msg.content}</div>

                {msg.isError && (
                  <div style={{ marginTop: "10px", paddingTop: "8px", borderTop: "1px solid rgba(239, 68, 68, 0.25)" }}>
                    <button
                      className="btn-retry-chat"
                      style={{
                        background: "linear-gradient(135deg, #ef4444 0%, #dc2626 100%)",
                        color: "#ffffff",
                        fontWeight: "600",
                        padding: "6px 14px",
                        borderRadius: "8px",
                        cursor: "pointer",
                        fontSize: "0.82rem",
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "6px",
                        boxShadow: "0 2px 8px rgba(239, 68, 68, 0.35)",
                        border: "none"
                      }}
                      onClick={() => {
                        if (msg.failedQuestion) {
                          setInput(msg.failedQuestion);
                        }
                      }}
                    >
                      <span style={{ fontSize: "0.9rem" }}>↺</span> Retry
                    </button>
                  </div>
                )}

                {msg.sources && msg.sources.length > 0 && (
                  <div className="msg-sources">
                    <span className="sources-title">🔍 Sources:</span>
                    <div className="sources-list">
                      {msg.sources.map((src, i) => (
                        <span key={i} className="source-chip" title={src.chunk}>
                          {src.document}
                        </span>
                      ))}
                    </div>
                    {msg.timing && (
                      <span className="source-speed">
                        Grounded in {msg.timing.total_ms}ms (LLM: {msg.timing.llm_ms}ms)
                      </span>
                    )}
                  </div>
                )}

                <span className="msg-time">{msg.timestamp}</span>
              </div>
            </div>
          ))}

        {isLoading && (
          <div className="msg-wrapper msg-ai">
            <div className="msg-bubble bubble-ai typing-bubble">
              <div className="typing-header">
                <span className="typing-text">AI is typing</span>
              </div>
              <div className="typing-dots">
                <span></span><span></span><span></span>
              </div>
            </div>
          </div>
        )}
      </div>

      <form className="chat-input-bar" onSubmit={handleSend}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={
            targetDocument
              ? `Ask a question about ${targetDocument}...`
              : "Ask a question about your documents... (Press Enter to send)"
          }
          className="chat-text-input"
          disabled={isLoading}
        />
        <button type="submit" className="btn-send-chat" disabled={!input.trim() || isLoading}>
          ➤
        </button>
      </form>
    </div>
  );
}

function GraphView() {
  return (
    <div className="graph-view">
      <div className="graph-placeholder">
        <span className="graph-icon">🗺️</span>
        <h3 className="graph-title">Knowledge Graph</h3>
        <p className="graph-desc">
          Visualize connections between concepts extracted from your study materials.
          Upload more documents to generate your personalized knowledge graph with topic
          relationships and concept maps.
        </p>
      </div>
    </div>
  );
}

// ─── Main Dashboard Export ───────────────────────────────────────────────────

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState("documents");
  const [targetDocument, setTargetDocument] = useState(null);
  const [showLogoutModal, setShowLogoutModal] = useState(false);
  const { logout } = useAuth();

  const handleAskAboutDocument = (filename) => {
    setTargetDocument(filename);
    setActiveTab("chat");
  };

  const handleConfirmLogout = () => {
    setShowLogoutModal(false);
    logout();
  };

  return (
    <div className="app-shell">
      <SidebarNav
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onRequestLogout={() => setShowLogoutModal(true)}
      />
      <div className="main-area">
        <TopBar activeTab={activeTab} />
        <div className="page-content">
          {activeTab === "documents" && (
            <DocumentsView onAskAboutDocument={handleAskAboutDocument} />
          )}
          {activeTab === "chat" && (
            <ChatView
              targetDocument={targetDocument}
              setTargetDocument={setTargetDocument}
            />
          )}
          {activeTab === "flashcards" && <FlashcardsView />}
          {activeTab === "quiz" && <QuizView />}
          {activeTab === "results" && <QuizResultsView />}
          {activeTab === "graph" && <GraphView />}
          {(activeTab === "profile" || activeTab === "settings") && (
            <ProfileView onRequestLogout={() => setShowLogoutModal(true)} />
          )}
        </div>
      </div>
      <LogoutModal
        isOpen={showLogoutModal}
        onClose={() => setShowLogoutModal(false)}
        onConfirm={handleConfirmLogout}
      />
    </div>
  );
}