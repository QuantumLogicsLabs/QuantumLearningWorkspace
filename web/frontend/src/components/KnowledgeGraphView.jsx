import { useState, useEffect, useMemo, useRef, useCallback } from "react";
import cytoscape from "cytoscape";
import {
  Network,
  Zap,
  RefreshCw,
  AlertTriangle,
  Brain,
  FileText,
  BarChart3,
  Search,
  X,
  Tag,
  ZoomIn,
  ZoomOut,
  Maximize2,
  BookOpen,
  MapPin,
  Link2,
} from "lucide-react";
import { useAuth } from "../context/AuthContext.jsx";
import { useToast } from "../context/ToastContext.jsx";
import {
  KNOWN_RELATIONSHIP_TYPES,
  relationshipMeta,
  describeEdge,
  parseSharedTerms,
  normalizeGraph,
  filterGraph,
  relatedConcepts,
  graphSignature,
  searchNodes,
} from "./knowledgeGraphData.js";
import "./KnowledgeGraphView.css";


const GRAPH_API_BASE = import.meta.env.VITE_GRAPH_API_BASE_URL || "http://localhost:8005";

// The backend adds new documents to the graph automatically after ingestion
// finishes, so the view checks back periodically (only while the tab is visible).
const AUTO_REFRESH_MS = 30000;

const COSE_OPTIONS = {
  name: "cose",
  idealEdgeLength: () => 110,
  nodeRepulsion: () => 9000,
  nodeOverlap: 16,
  gravity: 0.3,
  numIter: 1000,
  padding: 48,
  componentSpacing: 90,
};

/* ── Cytoscape styling helpers ─────────────────────────────────────────── */

function colorAlpha(color) {
  if (!color || color === "transparent") return 0;
  const slash = color.match(/\/\s*([\d.]+)(%?)\s*\)$/);
  if (slash) return slash[2] ? Number(slash[1]) / 100 : Number(slash[1]);
  const rgba = color.match(/^rgba\(([^)]+)\)$/);
  if (rgba) return Number(rgba[1].split(",")[3]);
  return 1;
}

// First (nearly) opaque background up the tree, i.e. the page surface the graph sits on.
function resolveBackground(el) {
  let current = el;
  while (current) {
    const bg = getComputedStyle(current).backgroundColor;
    if (colorAlpha(bg) >= 0.95) return bg;
    current = current.parentElement;
  }
  return "#ffffff";
}

// Colors come from CSS custom properties (see KnowledgeGraphView.css) and
// the container's inherited text color, so the canvas follows the app theme.
function readThemeColors(el) {
  const cs = getComputedStyle(el);
  const v = (name, fallback) => cs.getPropertyValue(name).trim() || fallback;
  return {
    text: cs.color || "#1f2937",
    surface: resolveBackground(el),
    document: v("--kg-graph-document", "#4f46e5"),
    topic: v("--kg-graph-topic", "#0891b2"),
    focus: v("--kg-graph-focus", "#f59e0b"),
  };
}

function buildStylesheet(c) {
  return [
    {
      selector: "node",
      style: {
        label: "data(label)",
        width: "data(size)",
        height: "data(size)",
        "background-color": c.document,
        "border-width": 2,
        "border-color": c.surface,
        color: c.text,
        "font-size": 11,
        "text-valign": "bottom",
        "text-margin-y": 6,
        "text-wrap": "ellipsis",
        "text-max-width": 150,
        "text-outline-color": c.surface,
        "text-outline-width": 2,
        "overlay-opacity": 0,
      },
    },
    {
      selector: 'node[layer = "topic"]',
      style: { "background-color": c.topic, shape: "round-rectangle", "font-size": 10 },
    },
    {
      selector: "edge",
      style: {
        width: "data(width)",
        "line-color": "data(color)",
        "curve-style": "bezier",
        opacity: 0.7,
        "arrow-scale": 0.9,
        "overlay-opacity": 0,
      },
    },
    {
      selector: 'edge[arrow = "target"]',
      style: { "target-arrow-shape": "triangle", "target-arrow-color": "data(color)" },
    },
    {
      selector: 'edge[arrow = "source"]',
      style: { "source-arrow-shape": "triangle", "source-arrow-color": "data(color)" },
    },
    {
      selector: "edge.kg-show-label",
      style: {
        label: "data(relLabel)",
        "font-size": 9,
        color: c.text,
        "text-rotation": "autorotate",
        "text-background-color": c.surface,
        "text-background-opacity": 0.92,
        "text-background-padding": 2,
      },
    },
    { selector: "edge.kg-hl", style: { opacity: 1 } },
    { selector: "node.kg-match", style: { "border-color": c.focus, "border-width": 4 } },
    { selector: "node.kg-selected", style: { "border-color": c.focus, "border-width": 5 } },
    { selector: ".kg-faded", style: { opacity: 0.12, "text-opacity": 0 } },
  ];
}

function nodeSize(layer, degree) {
  return layer === "document" ? 26 + Math.min(degree, 8) * 3 : 14 + Math.min(degree, 6) * 2;
}

function formatPercent(value) {
  return `${Math.round((value || 0) * 100)}%`;
}

/* ── Component ─────────────────────────────────────────────────────────── */

export default function KnowledgeGraphView({ onNavigate }) {
  const { token, handle401 } = useAuth();
  const { showToast } = useToast() || {};

  const [rawGraph, setRawGraph] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [rebuilding, setRebuilding] = useState(false);
  const [error, setError] = useState("");
  const [lastUpdated, setLastUpdated] = useState(null);

  const [layer, setLayer] = useState("document"); // "document" | "topic" | "all"
  const [documentFilter, setDocumentFilter] = useState("all");
  const [hiddenTypes, setHiddenTypes] = useState(() => new Set());
  const [searchQuery, setSearchQuery] = useState("");
  const [searchOpen, setSearchOpen] = useState(false);
  const [selected, setSelected] = useState(null); // { kind: "node" | "edge", id }

  const containerRef = useRef(null);
  const cyRef = useRef(null);
  const layoutRef = useRef(null);
  const positionsRef = useRef(new Map());
  const firstLayoutRef = useRef(true);
  const fitOnNextSyncRef = useRef(false);
  const pendingFocusRef = useRef(null);
  const signatureRef = useRef(null);
  const inFlightRef = useRef(false);

  // Keep callbacks from context in refs so polling doesn't restart on every render.
  const toastRef = useRef(showToast);
  const handle401Ref = useRef(handle401);
  useEffect(() => {
    toastRef.current = showToast;
    handle401Ref.current = handle401;
  });

  const notify = (message, type) => {
    if (toastRef.current) toastRef.current(message, type);
  };

  /* ── Data loading ── */

  // Fetches GET /graph. Returns { unauthorized: true } or { data }; throws on failure.
  const requestGraph = useCallback(async () => {
    const headers = token ? { Authorization: `Bearer ${token}` } : {};
    const res = await fetch(`${GRAPH_API_BASE}/graph`, { headers });
    if (res.status === 401) return { unauthorized: true };
    if (!res.ok) throw new Error(`The Knowledge Graph service returned an error (${res.status}).`);
    return { data: await res.json() };
  }, [token]);

  // mode: "initial" (full-page loader), "manual" (Refresh button),
  //       "background" (auto-refresh, silent), "rebuild" (after Rebuild)
  // State is only set inside the promise callbacks; callers that need a
  // loading indicator switch it on themselves (initial state or a handler).
  const loadGraph = useCallback(
    (mode = "initial") => {
      if (inFlightRef.current && mode === "background") return Promise.resolve();
      inFlightRef.current = true;

      const finish = () => {
        inFlightRef.current = false;
        if (mode === "initial") setLoading(false);
        if (mode === "manual") setRefreshing(false);
      };

      return requestGraph().then(
        (outcome) => {
          finish();
          if (outcome.unauthorized) {
            if (handle401Ref.current) handle401Ref.current();
            return;
          }
          const signature = graphSignature(outcome.data);
          const changed = signature !== signatureRef.current;
          const hadGraph = signatureRef.current !== null;
          signatureRef.current = signature;

          setLastUpdated(new Date());
          setError("");
          if (changed) setRawGraph(outcome.data);

          if (mode === "manual") {
            notify(changed ? "Graph refreshed." : "Graph is already up to date.", "success");
          } else if (mode === "background" && changed && hadGraph) {
            notify("Graph updated with newly processed content.", "success");
          }
        },
        (err) => {
          finish();
          const message =
            err instanceof TypeError
              ? `Can't reach the Knowledge Graph service at ${GRAPH_API_BASE}.`
              : err.message || "Failed to load the knowledge graph.";
          if (mode === "initial") setError(message);
          else if (mode === "manual" || mode === "rebuild") notify(message, "error");
          // background failures stay silent; the next tick retries
        }
      );
    },
    [requestGraph]
  );

  useEffect(() => {
    loadGraph("initial");
  }, [loadGraph]);

  useEffect(() => {
    const refreshIfVisible = () => {
      if (document.visibilityState === "visible") loadGraph("background");
    };
    const timer = setInterval(refreshIfVisible, AUTO_REFRESH_MS);
    document.addEventListener("visibilitychange", refreshIfVisible);
    return () => {
      clearInterval(timer);
      document.removeEventListener("visibilitychange", refreshIfVisible);
    };
  }, [loadGraph]);

  function retryInitialLoad() {
    setError("");
    setLoading(true);
    loadGraph("initial");
  }

  function handleRefresh() {
    if (!rawGraph) {
      retryInitialLoad();
      return;
    }
    setRefreshing(true);
    loadGraph("manual");
  }

  async function handleRebuild() {
    setRebuilding(true);
    try {
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      const res = await fetch(`${GRAPH_API_BASE}/graph/rebuild`, { method: "POST", headers });

      if (res.status === 401) {
        if (handle401) handle401();
        return;
      }
      if (!res.ok) throw new Error("Rebuild failed. Check that the Knowledge Graph service is running.");

      const summary = await res.json();
      notify(
        `Graph rebuilt: ${summary.document_edges_created || 0} document links and ${
          summary.topic_edges_created || 0
        } topic links found.`,
        "success"
      );
      if (rawGraph) {
        await loadGraph("rebuild");
      } else {
        setLoading(true);
        await loadGraph("initial");
      }
    } catch (err) {
      notify(err.message || "Failed to rebuild graph.", "error");
    } finally {
      setRebuilding(false);
    }
  }

  /* ── Derived data ── */

  const graph = useMemo(() => normalizeGraph(rawGraph), [rawGraph]);

  const visible = useMemo(
    () => filterGraph(graph, { layer, hiddenTypes, documentId: documentFilter }),
    [graph, layer, hiddenTypes, documentFilter]
  );

  const documentEdgeCount = useMemo(() => graph.edges.filter((e) => e.layer === "document").length, [graph]);
  const topicEdgeCount = graph.edges.length - documentEdgeCount;

  const avgSimilarity = useMemo(() => {
    if (!graph.edges.length) return 0;
    const sum = graph.edges.reduce((acc, e) => acc + e.similarity, 0);
    return Math.round((sum / graph.edges.length) * 100);
  }, [graph]);

  // Relationship types for the filter chips: the four the classifier knows,
  // plus anything new the backend starts sending. Counts respect the layer.
  const relationshipCounts = useMemo(() => {
    const counts = new Map(KNOWN_RELATIONSHIP_TYPES.map((t) => [t, 0]));
    for (const e of graph.edges) {
      if (layer !== "all" && e.layer !== layer) continue;
      counts.set(e.type, (counts.get(e.type) || 0) + 1);
    }
    return Array.from(counts.entries());
  }, [graph, layer]);

  const suggestions = useMemo(() => searchNodes(graph.nodes, searchQuery), [graph, searchQuery]);

  const searchMatchIds = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return new Set();
    return new Set(
      visible.nodes
        .filter((n) => n.title.toLowerCase().includes(q) || n.definition.toLowerCase().includes(q))
        .map((n) => n.id)
    );
  }, [visible, searchQuery]);

  const selectedNode = selected?.kind === "node" ? graph.nodeMap.get(selected.id) : null;
  const selectedEdge = selected?.kind === "edge" ? graph.edges.find((e) => e.id === selected.id) : null;
  const related = useMemo(
    () => (selectedNode ? relatedConcepts(graph, selectedNode.id) : []),
    [graph, selectedNode]
  );

  const hasGraph = !loading && graph.nodes.length > 0;
  const filtersActive = layer !== "document" || documentFilter !== "all" || hiddenTypes.size > 0;

  /* ── Cytoscape lifecycle ── */

  useEffect(() => {
    if (!hasGraph || !containerRef.current) return undefined;

    const cy = cytoscape({
      container: containerRef.current,
      elements: [],
      minZoom: 0.15,
      maxZoom: 3,
      boxSelectionEnabled: false,
      autounselectify: true,
    });
    cyRef.current = cy;
    firstLayoutRef.current = true;
    positionsRef.current = new Map();

    const container = containerRef.current;
    cy.on("tap", "node", (evt) => setSelected({ kind: "node", id: evt.target.id() }));
    cy.on("tap", "edge", (evt) => setSelected({ kind: "edge", id: evt.target.id() }));
    cy.on("tap", (evt) => {
      if (evt.target === cy) setSelected(null);
    });
    cy.on("mouseover", "edge", (evt) => evt.target.addClass("kg-show-label"));
    cy.on("mouseout", "edge", (evt) => {
      if (!evt.target.hasClass("kg-hl")) evt.target.removeClass("kg-show-label");
    });
    cy.on("mouseover", "node, edge", () => {
      container.style.cursor = "pointer";
    });
    cy.on("mouseout", "node, edge", () => {
      container.style.cursor = "";
    });

    const resizeObserver = typeof ResizeObserver !== "undefined" ? new ResizeObserver(() => cy.resize()) : null;
    if (resizeObserver) resizeObserver.observe(container);

    return () => {
      if (resizeObserver) resizeObserver.disconnect();
      // Stop any animated layout first, otherwise its next frame runs on a destroyed graph.
      if (layoutRef.current) layoutRef.current.stop();
      layoutRef.current = null;
      cy.stop(true);
      cy.destroy();
      cyRef.current = null;
    };
  }, [hasGraph]);

  // Sync visible nodes/edges into Cytoscape without resetting the whole layout:
  // existing nodes keep their positions, new ones are placed next to a neighbour.
  useEffect(() => {
    const cy = cyRef.current;
    if (!hasGraph || !cy) return;

    const colors = readThemeColors(containerRef.current);
    cy.style(buildStylesheet(colors));



    const degree = new Map();
    for (const e of visible.edges) {
      degree.set(e.source, (degree.get(e.source) || 0) + 1);
      degree.set(e.target, (degree.get(e.target) || 0) + 1);
    }

    const nodeDefs = visible.nodes.map((n) => ({
      id: n.id,
      data: { label: n.title, layer: n.layer, size: nodeSize(n.layer, degree.get(n.id) || 0) },
    }));
    const edgeDefs = visible.edges.map((e) => {
      const meta = relationshipMeta(e.type);
      return {
        id: e.id,
        source: e.source,
        target: e.target,
        data: { color: meta.color, arrow: meta.arrow, relLabel: meta.label, width: 1.5 + e.similarity * 3 },
      };
    });

    const wanted = new Set([...nodeDefs.map((d) => d.id), ...edgeDefs.map((d) => d.id)]);
    const added = [];

    cy.batch(() => {
      cy.edges().forEach((el) => {
        if (!wanted.has(el.id())) el.remove();
      });
      cy.nodes().forEach((el) => {
        if (!wanted.has(el.id())) {
          positionsRef.current.set(el.id(), { ...el.position() });
          el.remove();
        }
      });

      for (const def of nodeDefs) {
        const existing = cy.getElementById(def.id);
        if (existing.nonempty()) {
          existing.data(def.data);
          continue;
        }
        const saved = positionsRef.current.get(def.id);
        const nodeDef = { group: "nodes", data: { id: def.id, ...def.data } };
        if (saved) nodeDef.position = { ...saved };
        const node = cy.add(nodeDef);
        if (!saved) added.push(node);
      }

      for (const def of edgeDefs) {
        let existing = cy.getElementById(def.id);
        if (existing.nonempty() && (existing.source().id() !== def.source || existing.target().id() !== def.target)) {
          existing.remove();
          existing = cy.getElementById(def.id);
        }
        if (existing.nonempty()) existing.data(def.data);
        else cy.add({ group: "edges", data: { id: def.id, source: def.source, target: def.target, ...def.data } });
      }
    });

    const fitRequested = fitOnNextSyncRef.current;
    fitOnNextSyncRef.current = false;

    if (firstLayoutRef.current) {
      firstLayoutRef.current = false;
      cy.layout({ ...COSE_OPTIONS, randomize: true, animate: false, fit: true }).run();
      return;
    }

    if (added.length) {
      const addedCollection = cy.collection(added);
      const anchors = cy.nodes().difference(addedCollection);
      const box = anchors.nonempty() ? anchors.boundingBox() : null;
      const center = box ? { x: (box.x1 + box.x2) / 2, y: (box.y1 + box.y2) / 2 } : { x: 0, y: 0 };

      addedCollection.forEach((node) => {
        const anchor = node.neighborhood("node").difference(addedCollection)[0];
        const base = anchor ? anchor.position() : center;
        node.position({ x: base.x + (Math.random() - 0.5) * 140, y: base.y + (Math.random() - 0.5) * 140 });
      });

      // Only the new nodes move; everything the user has already seen stays put.
      anchors.lock();
      // animate: "end" computes the layout up front and then eases nodes into place.
      // (animate: true runs a frame loop that can fire once more after the graph is destroyed.)
      const layout = cy.layout({ ...COSE_OPTIONS, randomize: false, animate: "end", animationDuration: 500, fit: fitRequested });
      if (layoutRef.current) layoutRef.current.stop();
      layoutRef.current = layout;
      layout.one("layoutstop", () => {
        if (layoutRef.current === layout) layoutRef.current = null;
        if (!cy.destroyed()) anchors.unlock();
      });
      layout.run();
    } else if (fitRequested && cy.elements().nonempty()) {
      cy.animate({ fit: { eles: cy.elements(), padding: 48 } }, { duration: 300 });
    }
  }, [visible, hasGraph]);

  // Highlighting: selection > search matches.
  useEffect(() => {
    const cy = cyRef.current;
    if (!hasGraph || !cy) return;

    cy.batch(() => {
      cy.elements().removeClass("kg-faded kg-hl kg-match kg-selected kg-show-label");

      const target = selected ? cy.getElementById(selected.id) : null;
      if (target && target.nonempty()) {
        if (selected.kind === "node") {
          const hood = target.closedNeighborhood();
          cy.elements().not(hood).addClass("kg-faded");
          hood.edges().addClass("kg-hl kg-show-label");
          target.addClass("kg-selected");
        } else {
          const keep = target.union(target.connectedNodes());
          cy.elements().not(keep).addClass("kg-faded");
          target.addClass("kg-hl kg-show-label");
          target.connectedNodes().addClass("kg-selected");
        }
      } else if (searchMatchIds.size) {
        const matches = cy.nodes().filter((n) => searchMatchIds.has(n.id()));
        matches.addClass("kg-match");
        cy.elements().not(matches).addClass("kg-faded");
      }
    });

    if (pendingFocusRef.current) {
      const node = cy.getElementById(pendingFocusRef.current);
      if (node.nonempty()) {
        pendingFocusRef.current = null;
        cy.animate({ center: { eles: node }, zoom: Math.max(cy.zoom(), 1.3) }, { duration: 400 });
      }
    }
  }, [selected, searchMatchIds, visible, hasGraph]);

  /* ── Interactions ── */

  function focusNode(id) {
    const node = graph.nodeMap.get(id);
    if (!node) return;
    if (!visible.nodes.some((n) => n.id === id)) {
      // Bring the node into view by loosening filters that hide it.
      setLayer((prev) => (prev === "all" ? "all" : node.layer));
      setDocumentFilter("all");
      setHiddenTypes(new Set());
    }
    pendingFocusRef.current = id;
    setSelected({ kind: "node", id });
  }

  function chooseSuggestion(node) {
    setSearchQuery(node.title);
    setSearchOpen(false);
    focusNode(node.id);
  }

  function changeLayer(next) {
    fitOnNextSyncRef.current = true;
    setLayer(next);
  }

  function changeDocumentFilter(next) {
    fitOnNextSyncRef.current = true;
    setDocumentFilter(next);
  }

  function toggleType(type) {
    setHiddenTypes((prev) => {
      const next = new Set(prev);
      if (next.has(type)) next.delete(type);
      else next.add(type);
      return next;
    });
  }

  function resetFilters() {
    fitOnNextSyncRef.current = true;
    setLayer("document");
    setDocumentFilter("all");
    setHiddenTypes(new Set());
    setSearchQuery("");
  }

  function zoomBy(factor) {
    const cy = cyRef.current;
    if (!cy) return;
    const { width, height } = containerRef.current.getBoundingClientRect();
    cy.animate(
      { zoom: { level: cy.zoom() * factor, renderedPosition: { x: width / 2, y: height / 2 } } },
      { duration: 200 }
    );
  }

  function fitGraph() {
    const cy = cyRef.current;
    if (cy && cy.elements().nonempty()) cy.animate({ fit: { eles: cy.elements(), padding: 48 } }, { duration: 300 });
  }

  /* ── Render ── */

  return (
    <div className={`kg-page ${hasGraph ? "kg-page-wide" : ""}`}>
      {/* ── Page Header ── */}
      <div className="kg-header">
        <div className="kg-title-group">
          <div className="kg-icon-badge">
            <Network size={22} />
          </div>
          <div>
            <h2 className="kg-title">Knowledge Graph</h2>
            <p className="kg-subtitle">See how the ideas in your study materials connect</p>
          </div>
        </div>

        <div className="kg-header-actions">
          <button
            className="kg-btn kg-btn-secondary"
            onClick={handleRebuild}
            disabled={loading || rebuilding}
            title="Recalculate every connection from scratch. Takes longer; use it if the graph looks out of date."
          >
            <Zap size={15} className={rebuilding ? "kg-spin" : ""} />
            {rebuilding ? "Rebuilding..." : "Rebuild graph"}
          </button>
          <button
            className="kg-btn kg-btn-secondary"
            onClick={handleRefresh}
            disabled={loading || refreshing || rebuilding}
            title="Load the latest graph, including newly processed documents"
          >
            <RefreshCw size={15} className={loading || refreshing ? "kg-spin" : ""} /> Refresh
          </button>
        </div>
      </div>

      {/* ── Loading ── */}
      {loading && (
        <div className="kg-loading-state">
          <div className="kg-loading-spinner" />
          <p className="kg-loading-text">Loading your knowledge graph...</p>
        </div>
      )}

      {/* ── Error (only when there is nothing to show) ── */}
      {!loading && error && !rawGraph && (
        <div className="kg-error-card">
          <div className="kg-error-icon">
            <AlertTriangle size={28} />
          </div>
          <h3 className="kg-error-title">Unable to load the knowledge graph</h3>
          <p className="kg-error-message">{error}</p>
          <p className="kg-error-hint">Make sure the Knowledge Graph service is running at {GRAPH_API_BASE}.</p>
          <button className="kg-btn kg-btn-primary" onClick={retryInitialLoad}>
            <RefreshCw size={15} /> Try again
          </button>
        </div>
      )}

      {/* ── Empty ── */}
      {!loading && !error && graph.nodes.length === 0 && (
        <div className="kg-empty-card">
          <div className="kg-empty-orb">
            <Network className="kg-empty-icon" size={36} />
          </div>
          <h3 className="kg-empty-title">Your graph is empty</h3>
          <p className="kg-empty-desc">
            Upload study documents and they'll appear here once processing finishes. Documents that share ideas are
            linked automatically, with the kind of relationship labelled on each link.
          </p>

          <div className="kg-empty-actions">
            {onNavigate && (
              <button className="kg-btn kg-btn-primary" onClick={() => onNavigate("documents")}>
                📤 Upload documents
              </button>
            )}
            <button className="kg-btn kg-btn-secondary" onClick={handleRebuild} disabled={rebuilding}>
              <Zap size={15} className={rebuilding ? "kg-spin" : ""} />
              {rebuilding ? "Scanning..." : "Scan current documents"}
            </button>
          </div>

          <div className="kg-features-grid">
            <div className="kg-feature-item">
              <Brain className="kg-feature-icon" size={20} />
              <div className="kg-feature-content">
                <h4>Labelled relationships</h4>
                <p>Links say how ideas relate: prerequisite, example, contrast, or related topic.</p>
              </div>
            </div>
            <div className="kg-feature-item">
              <BookOpen className="kg-feature-icon" size={20} />
              <div className="kg-feature-content">
                <h4>Definitions at a click</h4>
                <p>Select any node to see its definition, source, and connected material.</p>
              </div>
            </div>
            <div className="kg-feature-item">
              <RefreshCw className="kg-feature-icon" size={20} />
              <div className="kg-feature-content">
                <h4>Updates on its own</h4>
                <p>New uploads are added to the graph without a full rebuild.</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Graph ── */}
      {hasGraph && (
        <div className="kg-content">
          <div className="kg-stats-bar">
            <div className="kg-stat-item">
              <span className="kg-stat-label">
                <FileText size={13} /> Indexed docs
              </span>
              <span className="kg-stat-value">{graph.documents.length}</span>
            </div>
            <div className="kg-stat-item">
              <span className="kg-stat-label">🔗 Document links</span>
              <span className="kg-stat-value">{documentEdgeCount}</span>
            </div>
            <div className="kg-stat-item">
              <span className="kg-stat-label">
                <Tag size={13} /> Topic links
              </span>
              <span className="kg-stat-value">{topicEdgeCount}</span>
            </div>
            <div className="kg-stat-item">
              <span className="kg-stat-label">
                <BarChart3 size={13} /> Avg similarity
              </span>
              <span className="kg-stat-value kg-stat-highlight">{avgSimilarity}%</span>
            </div>
          </div>

          {/* Controls: layer, search, document filter */}
          <div className="kg-controls-bar">
            <div className="kg-filter-tabs" role="group" aria-label="Graph level">
              <button
                className={`kg-filter-tab ${layer === "document" ? "active" : ""}`}
                onClick={() => changeLayer("document")}
              >
                <FileText size={14} /> Documents ({documentEdgeCount})
              </button>
              <button
                className={`kg-filter-tab ${layer === "topic" ? "active" : ""}`}
                onClick={() => changeLayer("topic")}
              >
                <Tag size={14} /> Topics ({topicEdgeCount})
              </button>
              <button className={`kg-filter-tab ${layer === "all" ? "active" : ""}`} onClick={() => changeLayer("all")}>
                Both ({graph.edges.length})
              </button>
            </div>

            <div className="kg-search-wrap">
              <Search className="kg-search-icon" size={15} />
              <input
                type="text"
                placeholder="Find a document or concept..."
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setSearchOpen(true);
                }}
                onFocus={() => setSearchOpen(true)}
                onBlur={() => setSearchOpen(false)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && suggestions[0]) chooseSuggestion(suggestions[0]);
                  if (e.key === "Escape") {
                    setSearchQuery("");
                    setSearchOpen(false);
                  }
                }}
                className="kg-search-input"
                aria-label="Search the graph"
              />
              {searchQuery && (
                <button className="kg-search-clear" onClick={() => setSearchQuery("")} title="Clear search">
                  <X size={14} />
                </button>
              )}
              {searchOpen && searchQuery.trim() && (
                <ul className="kg-suggestions" role="listbox">
                  {suggestions.length === 0 ? (
                    <li className="kg-suggestion-empty">No matches for "{searchQuery.trim()}"</li>
                  ) : (
                    suggestions.map((node) => (
                      <li key={node.id}>
                        <button
                          className="kg-suggestion"
                          onMouseDown={(e) => {
                            e.preventDefault();
                            chooseSuggestion(node);
                          }}
                        >
                          {node.layer === "document" ? <FileText size={13} /> : <Tag size={13} />}
                          <span>{node.title}</span>
                        </button>
                      </li>
                    ))
                  )}
                </ul>
              )}
            </div>
          </div>

          <div className="kg-graph-filters">
            <label className="kg-select-wrap">
              <span>Document</span>
              <select
                className="kg-select"
                value={documentFilter}
                onChange={(e) => changeDocumentFilter(e.target.value)}
              >
                <option value="all">All documents</option>
                {graph.documents.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.title}
                  </option>
                ))}
              </select>
            </label>

            <div className="kg-rel-chips" role="group" aria-label="Relationship types">
              {relationshipCounts.map(([type, count]) => {
                const meta = relationshipMeta(type);
                const off = hiddenTypes.has(type);
                return (
                  <button
                    key={type}
                    className={`kg-rel-chip ${off ? "off" : ""}`}
                    style={{ "--kg-rel-color": meta.color }}
                    onClick={() => toggleType(type)}
                    aria-pressed={!off}
                    title={off ? `Show "${meta.label}" links` : `Hide "${meta.label}" links`}
                  >
                    <span className="kg-rel-dot" />
                    {meta.label}
                    <span className="kg-rel-count">{count}</span>
                  </button>
                );
              })}
            </div>

            {filtersActive && (
              <button className="kg-link-btn" onClick={resetFilters}>
                Reset filters
              </button>
            )}
          </div>

          <div className={`kg-graph-layout ${selectedNode || selectedEdge ? "has-detail" : ""}`}>
            <div className="kg-graph-shell">
              <div ref={containerRef} className="kg-graph-canvas" aria-label="Interactive knowledge graph" />

              <div className="kg-graph-zoom" role="group" aria-label="Zoom controls">
                <button onClick={() => zoomBy(1.25)} aria-label="Zoom in" title="Zoom in">
                  <ZoomIn size={16} />
                </button>
                <button onClick={() => zoomBy(0.8)} aria-label="Zoom out" title="Zoom out">
                  <ZoomOut size={16} />
                </button>
                <button onClick={fitGraph} aria-label="Fit graph to view" title="Fit to view">
                  <Maximize2 size={16} />
                </button>
              </div>

              <div className="kg-graph-legend">
                <span>
                  <i className="kg-legend-doc" /> Document
                </span>
                <span>
                  <i className="kg-legend-topic" /> Topic (part of a document)
                </span>
              </div>

              {visible.edges.length === 0 && (
                <div className="kg-graph-hint">
                  {graph.edges.length === 0
                    ? "No connections yet. Links appear when your documents share ideas."
                    : "No links match the current filters."}
                </div>
              )}
            </div>

            {(selectedNode || selectedEdge) && (
              <aside className="kg-detail-panel" aria-live="polite">
                {selectedNode ? (
                  <NodeDetail
                    node={selectedNode}
                    graph={graph}
                    related={related}
                    onFocusNode={focusNode}
                    onClose={() => setSelected(null)}
                  />
                ) : (
                  <EdgeDetail
                    edge={selectedEdge}
                    graph={graph}
                    onFocusNode={focusNode}
                    onClose={() => setSelected(null)}
                  />
                )}
              </aside>
            )}
          </div>

          <p className="kg-graph-footnote">
            Drag to pan, scroll to zoom, drag a node to move it, click a node or link for details.
            {lastUpdated && ` Updated ${lastUpdated.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}; checks for new documents every 30 seconds.`}
          </p>
        </div>
      )}
    </div>
  );
}

/* ── Detail panel ──────────────────────────────────────────────────────── */

function describeLocation(node) {
  if (node.page != null && node.page !== "") {
    return node.section ? `Page ${node.page}, ${node.section}` : `Page ${node.page}`;
  }
  if (node.section) return node.section;
  if (node.chunkIndex != null) return `Part ${node.chunkIndex + 1} of the document (page number not available yet)`;
  return "Not available yet";
}

function DetailHead({ children, onClose }) {
  return (
    <div className="kg-detail-head">
      {children}
      <button className="kg-detail-close" onClick={onClose} aria-label="Close details">
        <X size={16} />
      </button>
    </div>
  );
}

function NodeDetail({ node, graph, related, onFocusNode, onClose }) {
  const parent = node.layer === "topic" ? graph.nodeMap.get(node.documentId) : null;
  const definition = node.definition || parent?.definition || "";
  const hasLocation = node.page != null || Boolean(node.section);

  return (
    <>
      <DetailHead onClose={onClose}>
        <span className={`kg-type-badge ${node.layer}`}>
          {node.layer === "document" ? (
            <>
              <FileText size={12} /> Document
            </>
          ) : (
            <>
              <Tag size={12} /> Topic
            </>
          )}
        </span>
      </DetailHead>
      <h3 className="kg-detail-title">{node.title}</h3>

      <section className="kg-detail-section">
        <h4>
          <BookOpen size={14} /> Definition
        </h4>
        {definition ? (
          <p>
            {definition}
            {!node.definition && parent?.definition && (
              <span className="kg-detail-note">Definition of the document this part comes from.</span>
            )}
          </p>
        ) : (
          <p className="kg-detail-muted">
            No definition yet. Definitions are generated when a document is processed; documents uploaded before this
            feature was added can get one with Rebuild graph.
          </p>
        )}
      </section>

      <section className="kg-detail-section">
        <h4>
          <FileText size={14} /> Source document
        </h4>
        <p>{node.sourceDocument || "Unknown"}</p>
      </section>

      <section className="kg-detail-section">
        <h4>
          <MapPin size={14} /> Page / section
        </h4>
        <p className={hasLocation ? "" : "kg-detail-muted"}>{describeLocation(node)}</p>
      </section>

      <section className="kg-detail-section">
        <h4>
          <Link2 size={14} /> Related concepts ({related.length})
        </h4>
        {related.length === 0 ? (
          <p className="kg-detail-muted">No connections to other material yet.</p>
        ) : (
          <ul className="kg-related-list">
            {related.map((r) => {
              const meta = relationshipMeta(r.type);
              return (
                <li key={r.edgeId}>
                  <button className="kg-related-item" onClick={() => onFocusNode(r.otherId)}>
                    <span className="kg-related-phrase" style={{ "--kg-rel-color": meta.color }}>
                      {r.phrase}
                    </span>
                    <span className="kg-related-title">{r.other.title}</span>
                    <span className="kg-related-score">{formatPercent(r.similarity)}</span>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </>
  );
}

function EdgeDetail({ edge, graph, onFocusNode, onClose }) {
  const source = graph.nodeMap.get(edge.source);
  const target = graph.nodeMap.get(edge.target);
  const meta = relationshipMeta(edge.type);
  const terms = parseSharedTerms(edge.label);

  return (
    <>
      <DetailHead onClose={onClose}>
        <span className="kg-related-phrase" style={{ "--kg-rel-color": meta.color }}>
          {meta.label}
        </span>
      </DetailHead>
      <h3 className="kg-detail-title">{describeEdge(edge, source?.title || "?", target?.title || "?")}</h3>

      <section className="kg-detail-section">
        <h4>Connects</h4>
        <ul className="kg-related-list">
          {[source, target].filter(Boolean).map((n) => (
            <li key={n.id}>
              <button className="kg-related-item" onClick={() => onFocusNode(n.id)}>
                <span className="kg-related-title">{n.title}</span>
              </button>
            </li>
          ))}
        </ul>
      </section>

      <section className="kg-detail-section">
        <h4>
          <BarChart3 size={14} /> Similarity
        </h4>
        <p>{formatPercent(edge.similarity)}</p>
      </section>

      {terms.length > 0 && (
        <section className="kg-detail-section">
          <h4>
            <Tag size={14} /> Shared terms
          </h4>
          <div className="kg-terms-list">
            {terms.map((term) => (
              <span key={term} className="kg-term-chip">
                #{term}
              </span>
            ))}
          </div>
        </section>
      )}
    </>
  );
}
