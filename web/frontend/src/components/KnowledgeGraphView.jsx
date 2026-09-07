import { useState, useEffect } from "react";
import { useAuth } from "../context/AuthContext.jsx";
import "./KnowledgeGraphView.css";

// Environment variable with fallback
const GRAPH_API_BASE = import.meta.env.VITE_GRAPH_API_BASE_URL || "http://localhost:8005";

export default function KnowledgeGraphView() {
  const { token, handle401 } = useAuth();
  const [graph, setGraph] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  function fetchGraph() {
    setLoading(true);
    setError("");

    const headers = {};
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    fetch(`${GRAPH_API_BASE}/graph`, { headers })
      .then((res) => {
        if (res.status === 401 && handle401) {
          handle401();
          return;
        }
        if (!res.ok) throw new Error("Failed to load knowledge graph");
        return res.json();
      })
      .then((data) => {
        setGraph(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || "Failed to load knowledge graph");
        setLoading(false);
      });
  }

  useEffect(() => {
    fetchGraph();
  }, [token]);

  const documentEdges = graph?.edges?.filter((e) => e.node_type === "document") || [];
  const topicEdges = graph?.edges?.filter((e) => e.node_type === "topic") || [];
  const hasAnyEdges = documentEdges.length > 0 || topicEdges.length > 0;

  return (
    <div className="graph-view">
      <div className="graph-header">
        <div>
          <h2 className="graph-title">Knowledge Graph</h2>
          <p className="graph-subtitle">
            See how your uploaded documents and topics connect to each other
          </p>
        </div>
        <button className="graph-refresh-btn" onClick={fetchGraph} title="Refresh">
          🔄 Refresh
        </button>
      </div>

      {loading && (
        <div className="graph-status-msg">Loading your knowledge graph...</div>
      )}

      {!loading && error && (
        <div className="graph-error-state">
          <p>{error}</p>
          <p className="graph-error-hint">
            Make sure the Knowledge Graph service is running (port 8005).
          </p>
          <button onClick={fetchGraph}>Retry</button>
        </div>
      )}

      {!loading && !error && !hasAnyEdges && (
        <div className="graph-empty-state">
          <span className="graph-empty-icon">🗺️</span>
          <p className="graph-empty-title">No connections yet</p>
          <p className="graph-empty-subtitle">
            Upload a few related documents and check back — connections are found
            automatically once you have more than one document.
          </p>
        </div>
      )}

      {!loading && !error && documentEdges.length > 0 && (
        <div className="graph-section">
          <h3 className="graph-section-title">📄 Document Connections</h3>
          <div className="graph-edge-list">
            {documentEdges.map((edge, i) => (
              <div key={i} className="graph-edge-card">
                <div className="graph-edge-titles">
                  <span className="graph-edge-doc">{edge.source_title}</span>
                  <span className="graph-edge-arrow">↔</span>
                  <span className="graph-edge-doc">{edge.target_title}</span>
                </div>
                <div className="graph-edge-meta">
                  <span className="graph-edge-label">{edge.label}</span>
                  <span className="graph-edge-score">
                    {Math.round(edge.similarity * 100)}% similar
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {!loading && !error && topicEdges.length > 0 && (
        <div className="graph-section">
          <h3 className="graph-section-title">🔗 Topic Connections</h3>
          <div className="graph-edge-list">
            {topicEdges.map((edge, i) => (
              <div key={i} className="graph-edge-card">
                <div className="graph-edge-titles">
                  <span className="graph-edge-doc">{edge.source_title}</span>
                  <span className="graph-edge-arrow">↔</span>
                  <span className="graph-edge-doc">{edge.target_title}</span>
                </div>
                <div className="graph-edge-meta">
                  <span className="graph-edge-label">{edge.label}</span>
                  <span className="graph-edge-score">
                    {Math.round(edge.similarity * 100)}% similar
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
