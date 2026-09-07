import { useState, useEffect, useMemo } from "react";
import { useAuth } from "../context/AuthContext.jsx";
import { useToast } from "../context/ToastContext.jsx";
import "./KnowledgeGraphView.css";

const GRAPH_API_BASE = import.meta.env.VITE_GRAPH_API_BASE_URL || "http://localhost:8005";

export default function KnowledgeGraphView({ onNavigate }) {
  const { token, handle401 } = useAuth();
  const { showToast } = useToast() || {};
  const [graph, setGraph] = useState(null);
  const [loading, setLoading] = useState(true);
  const [rebuilding, setRebuilding] = useState(false);
  const [error, setError] = useState("");
  const [activeFilter, setActiveFilter] = useState("all"); // "all" | "document" | "topic"
  const [searchQuery, setSearchQuery] = useState("");

  function getAuthHeaders() {
    const headers = {};
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
    return headers;
  }

  function fetchGraph() {
    setLoading(true);
    setError("");

    fetch(`${GRAPH_API_BASE}/graph`, { headers: getAuthHeaders() })
      .then((res) => {
        if (res.status === 401 && handle401) {
          handle401();
          return null;
        }
        if (!res.ok) throw new Error("Failed to load knowledge graph");
        return res.json();
      })
      .then((data) => {
        if (data) setGraph(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || "Failed to load knowledge graph");
        setLoading(false);
      });
  }

  async function handleRebuild() {
    setRebuilding(true);
    try {
      const res = await fetch(`${GRAPH_API_BASE}/graph/rebuild`, {
        method: "POST",
        headers: getAuthHeaders(),
      });

      if (res.status === 401 && handle401) {
        handle401();
        return;
      }

      if (!res.ok) {
        throw new Error("Rebuild failed. Please check backend service.");
      }

      const summary = await res.json();
      const docCount = summary.document_edges_created || 0;
      const topicCount = summary.topic_edges_created || 0;

      if (showToast) {
        showToast(
          `Graph rebuilt: ${docCount} document links & ${topicCount} topic links found.`,
          "success"
        );
      }

      fetchGraph();
    } catch (err) {
      if (showToast) {
        showToast(err.message || "Failed to rebuild graph", "error");
      }
    } finally {
      setRebuilding(false);
    }
  }

  useEffect(() => {
    fetchGraph();
  }, [token]);

  // Derived collections
  const allEdges = useMemo(() => graph?.edges || [], [graph]);
  const documentEdges = useMemo(
    () => allEdges.filter((e) => e.node_type === "document"),
    [allEdges]
  );
  const topicEdges = useMemo(
    () => allEdges.filter((e) => e.node_type === "topic"),
    [allEdges]
  );
  const totalNodes = graph?.nodes?.length || 0;

  // Filtered edges based on tab & search
  const filteredEdges = useMemo(() => {
    return allEdges.filter((edge) => {
      // Type match
      if (activeFilter !== "all" && edge.node_type !== activeFilter) {
        return false;
      }
      // Search match
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase().trim();
        const src = (edge.source_title || "").toLowerCase();
        const tgt = (edge.target_title || "").toLowerCase();
        const lbl = (edge.label || "").toLowerCase();
        return src.includes(q) || tgt.includes(q) || lbl.includes(q);
      }
      return true;
    });
  }, [allEdges, activeFilter, searchQuery]);

  // Calculate average similarity
  const avgSimilarity = useMemo(() => {
    if (!allEdges.length) return 0;
    const sum = allEdges.reduce((acc, curr) => acc + (curr.similarity || 0), 0);
    return Math.round((sum / allEdges.length) * 100);
  }, [allEdges]);

  // Parse label into individual tags
  function parseTerms(label) {
    if (!label) return [];
    const prefix = "shared terms:";
    if (label.toLowerCase().startsWith(prefix)) {
      const termsStr = label.slice(prefix.length).trim();
      return termsStr
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean);
    }
    return [label];
  }

  // Similarity tier
  function getScoreTier(score) {
    const pct = Math.round(score * 100);
    if (pct >= 80) return "high";
    if (pct >= 60) return "medium";
    return "normal";
  }

  return (
    <div className="kg-page">
      {/* ── Page Header ── */}
      <div className="kg-header">
        <div className="kg-title-group">
          <div className="kg-icon-badge">🌐</div>
          <div>
            <h2 className="kg-title">Knowledge Graph</h2>
            <p className="kg-subtitle">
              Discover semantic relationships, shared concepts, and topic connections across your materials
            </p>
          </div>
        </div>

        <div className="kg-header-actions">
          <button
            className="kg-btn kg-btn-secondary"
            onClick={handleRebuild}
            disabled={loading || rebuilding}
            title="Scan documents and recalculate graph connections"
          >
            <span className={rebuilding ? "kg-spin" : ""}>⚡</span>
            {rebuilding ? "Rebuilding..." : "Rebuild Graph"}
          </button>
          <button
            className="kg-btn kg-btn-secondary"
            onClick={fetchGraph}
            disabled={loading || rebuilding}
            title="Refresh knowledge graph"
          >
            <span className={loading ? "kg-spin" : ""}>🔄</span> Refresh
          </button>
        </div>
      </div>

      {/* ── Loading Skeleton ── */}
      {loading && (
        <div className="kg-loading-state">
          <div className="kg-loading-spinner" />
          <p className="kg-loading-text">Analyzing semantic document vectors and mapping connections...</p>
          <div className="kg-skeleton-cards">
            <div className="kg-skeleton-card shimmer" />
            <div className="kg-skeleton-card shimmer" />
          </div>
        </div>
      )}

      {/* ── Error State ── */}
      {!loading && error && (
        <div className="kg-error-card">
          <div className="kg-error-icon">⚠️</div>
          <h3 className="kg-error-title">Unable to Load Knowledge Graph</h3>
          <p className="kg-error-message">{error}</p>
          <p className="kg-error-hint">
            Please ensure the Knowledge Graph microservice is running locally on port 8005.
          </p>
          <button className="kg-btn kg-btn-primary" onClick={fetchGraph}>
            🔄 Retry Connection
          </button>
        </div>
      )}

      {/* ── Empty State ── */}
      {!loading && !error && allEdges.length === 0 && (
        <div className="kg-empty-card">
          <div className="kg-empty-orb">
            <span className="kg-empty-icon">🌐</span>
          </div>
          <h3 className="kg-empty-title">No Connections Discovered Yet</h3>
          <p className="kg-empty-desc">
            Upload two or more study documents or lecture notes. When documents share themes, formulas, or
            technical concepts, our AI engine automatically generates interactive knowledge links here.
          </p>

          <div className="kg-empty-actions">
            {onNavigate && (
              <button
                className="kg-btn kg-btn-primary"
                onClick={() => onNavigate("documents")}
              >
                📤 Upload Documents
              </button>
            )}
            <button
              className="kg-btn kg-btn-secondary"
              onClick={handleRebuild}
              disabled={rebuilding}
            >
              <span className={rebuilding ? "kg-spin" : ""}>⚡</span>
              {rebuilding ? "Analyzing..." : "Scan Current Documents"}
            </button>
          </div>

          <div className="kg-features-grid">
            <div className="kg-feature-item">
              <span className="kg-feature-icon">🧠</span>
              <div className="kg-feature-content">
                <h4>Vector Semantic Matching</h4>
                <p>Calculates cosine similarity across high-dimensional document chunk embeddings.</p>
              </div>
            </div>

            <div className="kg-feature-item">
              <span className="kg-feature-icon">🏷️</span>
              <div className="kg-feature-content">
                <h4>Topic Overlap Extraction</h4>
                <p>Identifies key intersecting keywords, terminology, and conceptual hierarchies.</p>
              </div>
            </div>

            <div className="kg-feature-item">
              <span className="kg-feature-icon">🔗</span>
              <div className="kg-feature-content">
                <h4>Dynamic Graph Discovery</h4>
                <p>Re-indexes linkages on-demand as your personal knowledge base expands.</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Populated Graph View ── */}
      {!loading && !error && allEdges.length > 0 && (
        <div className="kg-content">
          {/* Stats Bar */}
          <div className="kg-stats-bar">
            <div className="kg-stat-item">
              <span className="kg-stat-label">📄 Indexed Docs</span>
              <span className="kg-stat-value">{totalNodes}</span>
            </div>
            <div className="kg-stat-item">
              <span className="kg-stat-label">🔗 Document Links</span>
              <span className="kg-stat-value">{documentEdges.length}</span>
            </div>
            <div className="kg-stat-item">
              <span className="kg-stat-label">🏷️ Topic Links</span>
              <span className="kg-stat-value">{topicEdges.length}</span>
            </div>
            <div className="kg-stat-item">
              <span className="kg-stat-label">📊 Avg Similarity</span>
              <span className="kg-stat-value kg-stat-highlight">{avgSimilarity}%</span>
            </div>
          </div>

          {/* Controls Bar: Filters & Search */}
          <div className="kg-controls-bar">
            <div className="kg-filter-tabs">
              <button
                className={`kg-filter-tab ${activeFilter === "all" ? "active" : ""}`}
                onClick={() => setActiveFilter("all")}
              >
                All Links ({allEdges.length})
              </button>
              <button
                className={`kg-filter-tab ${activeFilter === "document" ? "active" : ""}`}
                onClick={() => setActiveFilter("document")}
              >
                📄 Documents ({documentEdges.length})
              </button>
              <button
                className={`kg-filter-tab ${activeFilter === "topic" ? "active" : ""}`}
                onClick={() => setActiveFilter("topic")}
              >
                🏷️ Topics ({topicEdges.length})
              </button>
            </div>

            <div className="kg-search-wrap">
              <span className="kg-search-icon">🔍</span>
              <input
                type="text"
                placeholder="Search documents or concepts..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="kg-search-input"
              />
              {searchQuery && (
                <button
                  className="kg-search-clear"
                  onClick={() => setSearchQuery("")}
                  title="Clear search"
                >
                  ✕
                </button>
              )}
            </div>
          </div>

          {/* Cards List */}
          {filteredEdges.length === 0 ? (
            <div className="kg-no-results">
              <p>🔍 No connections found matching "{searchQuery}"</p>
              <button
                className="kg-btn kg-btn-secondary"
                onClick={() => {
                  setSearchQuery("");
                  setActiveFilter("all");
                }}
              >
                Reset Filters
              </button>
            </div>
          ) : (
            <div className="kg-cards-list">
              {filteredEdges.map((edge, index) => {
                const terms = parseTerms(edge.label);
                const scorePercent = Math.round((edge.similarity || 0) * 100);
                const tier = getScoreTier(edge.similarity || 0);

                return (
                  <div key={index} className="kg-card">
                    {/* Top Row: Type & Similarity Badge */}
                    <div className="kg-card-header">
                      <span className={`kg-type-badge ${edge.node_type}`}>
                        {edge.node_type === "document" ? "📄 Document Link" : "🏷️ Topic Link"}
                      </span>

                      <div className={`kg-score-badge ${tier}`}>
                        <span className="kg-score-num">{scorePercent}%</span>
                        <span className="kg-score-text">similarity</span>
                      </div>
                    </div>

                    {/* Nodes Connected with glowing link */}
                    <div className="kg-nodes-row">
                      <div className="kg-node" title={edge.source_title}>
                        <div className="kg-node-icon">📄</div>
                        <span className="kg-node-title">{edge.source_title}</span>
                      </div>

                      <div className="kg-connector">
                        <div className="kg-connector-line" />
                        <div className="kg-connector-badge">⟷</div>
                      </div>

                      <div className="kg-node" title={edge.target_title}>
                        <div className="kg-node-icon">📄</div>
                        <span className="kg-node-title">{edge.target_title}</span>
                      </div>
                    </div>

                    {/* Progress Bar */}
                    <div className="kg-meter-track">
                      <div
                        className={`kg-meter-fill ${tier}`}
                        style={{ width: `${Math.min(100, Math.max(5, scorePercent))}%` }}
                      />
                    </div>

                    {/* Shared Terms / Context */}
                    <div className="kg-card-footer">
                      <span className="kg-terms-label">Overlap:</span>
                      <div className="kg-terms-list">
                        {terms.map((term, tIdx) => (
                          <span key={tIdx} className="kg-term-chip">
                            #{term}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
