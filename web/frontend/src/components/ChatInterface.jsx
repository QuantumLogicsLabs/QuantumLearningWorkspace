import { useState, useEffect, useRef } from "react";
import { useAuth } from "../context/AuthContext.jsx";
import "./ChatInterface.css";

const getEmailFromToken = (token) => {
  if (!token) return null;
  try {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    const payload = JSON.parse(jsonPayload);
    return payload.sub || null;
  } catch (e) {
    return null;
  }
};

const getStorageKey = (token) => {
  const email = getEmailFromToken(token);
  return email ? `studymind_chat_history_${email}` : "studymind_chat_history_guest";
};

export default function ChatInterface({ onBack }) {
  const { token, handle401 } = useAuth();
  const [files, setFiles] = useState([]);
  const [selectedDoc, setSelectedDoc] = useState(null);
  const [messages, setMessages] = useState(() => {
    const key = getStorageKey(token);
    const saved = localStorage.getItem(key);
    return saved
      ? JSON.parse(saved)
      : [
          {
            role: "assistant",
            content: "Hello! I'm your StudyMind AI assistant. Ask me anything about your uploaded study materials, and I'll find the answers for you.",
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
          }
        ];
  });
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  
  const API_BASE = import.meta.env.VITE_API_BASE_URL;

  // Fetch document uploads and poll status changes
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

  // Save history to localStorage whenever it changes
  useEffect(() => {
    const key = getStorageKey(token);
    localStorage.setItem(key, JSON.stringify(messages));
  }, [messages, token]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
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
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    const apiHistory = messages
  .filter(
    (msg) =>
      !msg.isError &&
      typeof msg.content === "string" &&
      msg.content.trim().length > 0 &&
      msg.content !==
        "Hello! I'm your StudyMind AI assistant. Select a document or ask me anything about your uploaded study materials."
  )
  .map((msg) => ({
    role: msg.role === "assistant" ? "assistant" : "user",
    content: msg.content,
  }));

    try {
      const response = await fetch(`${API_BASE}/ask`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-User-Id": getEmailFromToken(token) || "guest",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          question: userMessage.content,
          history: apiHistory,
          top_k: 4,
          include_sources: true,
          rerank: false,
          multi_hop: false,
          skip_cache: false,
          filename: selectedDoc || null,
        })
      });

      if (handle401(response)) return;
      if (!response.ok) throw new Error("Failed to connect to AI server");

      const data = await response.json();
      
      const assistantMessage = {
        role: "assistant",
        content: data.answer,
        sources: data.sources || [],
        timing: data.timing || null,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Sorry, I had trouble reaching the AI server. Please make sure the backend is running.",
          isError: true,
          failedQuestion: userMessage.content,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ]);
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
      const initial = [
        {
          role: "assistant",
          content: "Hello! I'm your StudyMind AI assistant. Ask me anything about your uploaded study materials, and I'll find the answers for you.",
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ];
      setMessages(initial);
      const key = getStorageKey(token);
      localStorage.removeItem(key);
    }
  };

  return (
    <div className="chat-interface">
      <div className="chat-header">
        <div className="chat-header-info">
          {onBack && (
            <button className="btn-back-nav" onClick={onBack} title="Back to Dashboard">
              ← Dashboard
            </button>
          )}
          <h3>AI Tutor Chat</h3>
          <span className="chat-status">
            <span className="status-dot"></span> Online
          </span>
        </div>

        {/* Document Selector Dropdown (Disables files still processing) */}
        <div className="chat-header-doc-selector">
          <select
            value={selectedDoc || ""}
            onChange={(e) => setSelectedDoc(e.target.value || null)}
            className="header-doc-select"
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
        </div>

        <button className="btn-clear" onClick={clearHistory} title="Clear history">
          🗑️ Clear
        </button>
      </div>

      <div className="chat-messages">
        {messages.map((msg, index) => (
          <div
            key={index}
            className={`message-wrapper ${msg.role === "user" ? "user-wrapper" : "assistant-wrapper"}`}
          >
            <div className={`message-bubble ${msg.role === "user" ? "user-bubble" : "assistant-bubble"} ${msg.isError ? "error-bubble" : ""}`}>
              {msg.role === "assistant" && (
                <div className="msg-header">
                  <span className="msg-sender-tag ai-tag">✦ AI</span>
                </div>
              )}

              <div className="message-content">{msg.content}</div>

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
              
              {/* Show sources if present */}
              {msg.sources && msg.sources.length > 0 && (
                <div className="message-sources">
                  <span className="sources-title">🔍 Sources:</span>
                  <div className="sources-list">
                    {msg.sources.map((src, i) => (
                      <span key={i} className="source-tag" title={src.chunk}>
                        {src.document}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Show generation time */}
              {msg.timing && (
                <div className="message-meta-info">
                  Grounded in {msg.timing.total_ms}ms (LLM: {msg.timing.llm_ms}ms)
                </div>
              )}

              <span className="message-time">{msg.timestamp}</span>
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="message-wrapper assistant-wrapper">
            <div className="message-bubble assistant-bubble loading-bubble">
              <div className="typing-header">
                <span className="typing-text">AI is typing</span>
              </div>
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <form className="chat-input-form" onSubmit={handleSend}>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={selectedDoc ? `Ask about ${selectedDoc}...` : "Ask a question about your documents... (Press Enter to send)"}
          rows={1}
        />
        <button type="submit" className="chat-send-btn" disabled={!input.trim() || isLoading}>
          <svg viewBox="0 0 24 24" width="24" height="24">
            <path fill="currentColor" d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
          </svg>
        </button>
      </form>
    </div>
  );
}