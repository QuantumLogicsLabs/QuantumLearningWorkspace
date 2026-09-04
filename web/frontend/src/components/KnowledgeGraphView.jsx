import { useState, useEffect } from "react";
import { useAuth } from "../context/AuthContext.jsx";
import "./KnowledgeGraphView.css";

const GRAPH_API_BASE = "http://localhost:8005";

// TEMP - for visually previewing UI states. Set to null before committing.
// Options: null (real fetch), "loading", "error", "empty", "populated"
const PREVIEW_MODE = "null";

const MOCK_POPULATED_GRAPH = {
  nodes: [
    { id: "doc1", title: "Machine Learning Basics", node_type: "document" },
    { id: "doc2", title: "Deep Learning Intro", node_type: "document" },
    { id: "doc3", title: "History of Rome", node_type: "document" },
  ],
  edges: [
    {
      node_type: "document",
      source_title: "Machine Learning Basics",
      target_title: "Deep Learning Intro",
      similarity: 0.87,
      label: "shared terms: neural, gradient, training",
    },
    {
      node_type: "topic",
      source_title: "Machine Learning Basics",
      target_title: "Deep Learning Intro",
      similarity: 0.72,
      label: "shared terms: backpropagation, weights",
    },
  ],
};

export default function KnowledgeGraphView() {
  const { token } = useAuth();
  const [graph, setGraph] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  function fetchGraph() {
    // TEMP preview branches
    if (PREVIEW_MODE === "loading") {
      setLoading(true);
      return;
    }
    if (PREVIEW_MODE === "error") {
      setLoading(false);
      setError("Failed to load knowledge graph");
      return;
    }
    if (PREVIEW_MODE === "empty") {
      setLoading(false);
      setError("");
      setGraph({ nodes: [], edges: [] });
      return;
    }
    if (PREVIEW_MODE === "populated") {
      setLoading(false);
      setError("");
      setGraph(MOCK_POPULATED_GRAPH);
      return;
    }

    // Real fetch (normal behavior)
    setLoading(true);
    setError("");
    fetch(`${GRAPH_API_BASE}/graph`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => {
        if (!res.ok) throw new Error("Failed to load knowledge graph");
        return res.json();
      })
      .then((data) => {
        setGraph(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
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