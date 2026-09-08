import { useState, useEffect } from "react";
import { useAuth } from "../context/AuthContext.jsx";
import "./StudyRoadmapView.css";

// Accent colours keyed to priority
const PRIORITY_ACCENT = {
  high: "#ef4444",
  medium: "#f59e0b",
  recommended: "#22c55e",
};

// Skeleton row
function SkeletonStep() {
  return (
    <li className="roadmap-skeleton-item">
      <div className="skeleton-circle" />
      <div className="skeleton-lines">
        <div className="skeleton-line wide" />
        <div className="skeleton-line full" />
        <div className="skeleton-line short" />
      </div>
    </li>
  );
}

export default function StudyRoadmapView({ onNavigate }) {
  const { token } = useAuth();
  const [steps, setSteps] = useState([]);
  const [subject, setSubject] = useState("Your Personalized Study Roadmap");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [hasActivity, setHasActivity] = useState(true);

  const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:5000";

  useEffect(() => {
    let active = true;

    async function fetchRoadmap() {
      setLoading(true);
      setError(null);

      try {
        const headers = {};
        if (token) headers["Authorization"] = `Bearer ${token}`;

        const res = await fetch(`${API_BASE}/roadmap/next-steps`, { headers });

        if (!res.ok) throw new Error(`Server returned ${res.status}`);

        const data = await res.json();

        if (!active) return;

        if (data && Array.isArray(data.next_steps) && data.next_steps.length > 0) {
          const enriched = data.next_steps.map((item, idx) => ({
            ...item,
            step_number: item.step_number ?? idx + 1,
            accent: PRIORITY_ACCENT[item.priority?.toLowerCase()] ?? "#7c3aed",
          }));
          setSteps(enriched);
          if (data.subject) setSubject(data.subject);
          setHasActivity(true);
        } else {
          // Backend returned empty steps — user has no activity yet
          setSteps([]);
          setHasActivity(false);
        }
      } catch (err) {
        if (!active) return;
        setError("Could not load your roadmap right now. Using default suggestions.");

        // Graceful fallback — show default curated steps so page is never blank
        setSteps([
          {
            step_number: 1,
            topic: "Upload Your First Document",
            description:
              "Start by uploading a PDF or study material. The AI will extract key concepts and build your personalised roadmap from it.",
            estimated_duration: "5 minutes",
            priority: "high",
            accent: "#ef4444",
            action_label: "Go to Documents",
            target_tab: "documents",
          },
          {
            step_number: 2,
            topic: "Take a Quiz",
            description:
              "Generate a quiz from your uploaded material. Your weak areas are automatically identified to personalise this roadmap.",
            estimated_duration: "10–15 minutes",
            priority: "medium",
            accent: "#f59e0b",
            action_label: "Take Quiz",
            target_tab: "quiz",
          },
          {
            step_number: 3,
            topic: "Review with Flashcards",
            description:
              "Practice active recall with AI-generated flashcards. Mark what you know and what needs more work.",
            estimated_duration: "15–20 minutes",
            priority: "recommended",
            accent: "#22c55e",
            action_label: "Open Flashcards",
            target_tab: "flashcards",
          },
        ]);
        setHasActivity(true); // Show steps even in fallback
      } finally {
        if (active) setLoading(false);
      }
    }

    fetchRoadmap();
    return () => { active = false; };
  }, [token, API_BASE]);

  const handleAction = (targetTab) => {
    if (onNavigate && targetTab) onNavigate(targetTab);
  };

  return (
    <div className="roadmap-page">
      {/* ── Page Header ─────────────────────────────────────── */}
      <header className="roadmap-page-header">
        <div className="roadmap-page-title-group">
          <div className="roadmap-page-icon">🗺️</div>
          <div>
            <h1 className="roadmap-page-heading">Study Roadmap</h1>
            <p className="roadmap-page-subtitle">
              Your personalised learning path based on quizzes, flashcards &amp; uploaded materials
            </p>
          </div>
        </div>
        {!loading && steps.length > 0 && (
          <div className="roadmap-subject-badge">
            <span>🎯</span>
            {steps.length} Steps Planned
          </div>
        )}
      </header>

      {/* ── Error Banner ─────────────────────────────────────── */}
      {error && (
        <div className="roadmap-error-banner" role="alert">
          ⚠️ {error}
        </div>
      )}

      {/* ── Loading ──────────────────────────────────────────── */}
      {loading && (
        <ol className="roadmap-skeleton-list" aria-label="Loading roadmap…">
          <SkeletonStep />
          <SkeletonStep />
          <SkeletonStep />
        </ol>
      )}

      {/* ── Empty State — no activity yet ────────────────────── */}
      {!loading && !hasActivity && steps.length === 0 && (
        <div className="roadmap-empty-state" role="status">
          <div className="roadmap-empty-icon">📋</div>
          <h2 className="roadmap-empty-title">No Roadmap Yet</h2>
          <p className="roadmap-empty-desc">
            Take a quiz to get your personalised study roadmap. The AI will identify your weak topics
            and build a step-by-step learning plan for you.
          </p>
          <button
            className="roadmap-empty-cta"
            type="button"
            onClick={() => handleAction("quiz")}
          >
            🎯 Take a Quiz Now
          </button>
        </div>
      )}

      {/* ── Steps List ───────────────────────────────────────── */}
      {!loading && steps.length > 0 && (
        <ol className="roadmap-steps-list" aria-label="Study roadmap steps">
          {steps.map((step) => {
            const priorityKey = (step.priority || "recommended").toLowerCase();
            const accent = step.accent || PRIORITY_ACCENT[priorityKey] || "#7c3aed";

            return (
              <li
                key={step.step_number}
                className="roadmap-step-item"
                style={{ "--step-accent": accent }}
              >
                {/* Number circle */}
                <div className="roadmap-step-number" aria-label={`Step ${step.step_number}`}>
                  {step.step_number}
                </div>

                {/* Content */}
                <div className="roadmap-step-content">
                  <div className="roadmap-step-top">
                    <h3 className="roadmap-step-topic">{step.topic}</h3>
                    <span className={`roadmap-priority-pill ${priorityKey}`}>
                      {priorityKey === "high"
                        ? "🔴 High"
                        : priorityKey === "medium"
                        ? "🟡 Medium"
                        : "🟢 Recommended"}
                    </span>
                  </div>

                  <p className="roadmap-step-desc">{step.description}</p>

                  <div className="roadmap-step-footer">
                    <span className="roadmap-step-duration">
                      ⏱️ {step.estimated_duration || "1–2 days"}
                    </span>
                    <button
                      type="button"
                      className="roadmap-action-btn"
                      onClick={() => handleAction(step.target_tab || "quiz")}
                      title={`Go to ${step.action_label}`}
                    >
                      {step.action_label || "Start"} →
                    </button>
                  </div>
                </div>
              </li>
            );
          })}
        </ol>
      )}
    </div>
  );
}
