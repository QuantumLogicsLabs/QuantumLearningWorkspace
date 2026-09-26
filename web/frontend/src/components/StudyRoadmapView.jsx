import { useState, useEffect } from "react";
import { useAuth } from "../context/AuthContext.jsx";
import { Map, Target, AlertTriangle, ClipboardList, Clock, Search } from "lucide-react";
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

export default function StudyRoadmapView({ onNavigate, initialContext }) {
  const { token } = useAuth();
  const [steps, setSteps] = useState([]);
  const [subject, setSubject] = useState(initialContext?.subject || "Your Personalized Study Roadmap");
  const [loading, setLoading] = useState(!initialContext?.next_steps);
  const [error, setError] = useState(null);
  const [hasActivity, setHasActivity] = useState(true);

  // Custom topic generation state
  const [topicInput, setTopicInput] = useState("");
  const [isGeneratingTopic, setIsGeneratingTopic] = useState(false);
  const [topicError, setTopicError] = useState("");

  const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:5000";

  useEffect(() => {
    let active = true;

    if (initialContext && Array.isArray(initialContext.next_steps) && initialContext.next_steps.length > 0) {
      const enriched = initialContext.next_steps.map((item, idx) => ({
        ...item,
        step_number: item.step_number ?? idx + 1,
        accent: PRIORITY_ACCENT[item.priority?.toLowerCase()] ?? "#7c3aed",
      }));
      setSteps(enriched);
      if (initialContext.subject) setSubject(initialContext.subject);
      setHasActivity(true);
      setLoading(false);
      return;
    }

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
          setSteps([]);
          setHasActivity(false);
        }
      } catch (err) {
        if (!active) return;
        setError("Could not load your roadmap right now. Using default suggestions.");

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
        setHasActivity(true);
      } finally {
        if (active) setLoading(false);
      }
    }

    fetchRoadmap();
    return () => { active = false; };
  }, [token, API_BASE, initialContext]);

  const handleAction = (targetTab) => {
    if (onNavigate && targetTab) onNavigate(targetTab);
  };

  const handleGenerateTopicRoadmap = async (e) => {
    e.preventDefault();
    const cleanTopic = topicInput.trim();
    if (!cleanTopic) {
      setTopicError("Please enter a topic to generate a roadmap.");
      return;
    }

    setTopicError("");
    setIsGeneratingTopic(true);

    try {
      const headers = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const res = await fetch(`${API_BASE}/roadmap/generate-from-topic`, {
        method: "POST",
        headers,
        body: JSON.stringify({ topic: cleanTopic, step_count: 5 }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "Failed to generate roadmap for this topic");
      }

      const data = await res.json();
      if (data && Array.isArray(data.next_steps) && data.next_steps.length > 0) {
        const enriched = data.next_steps.map((item, idx) => ({
          ...item,
          step_number: item.step_number ?? idx + 1,
          accent: PRIORITY_ACCENT[item.priority?.toLowerCase()] ?? "#7c3aed",
        }));
        setSteps(enriched);
        setSubject(data.subject || `Roadmap: ${cleanTopic}`);
        setHasActivity(true);
        setError(null);
        setTopicInput("");
      } else {
        setTopicError("No roadmap could be generated for this topic.");
      }
    } catch (err) {
      setTopicError(err.message || "Something went wrong. Please try again.");
    } finally {
      setIsGeneratingTopic(false);
    }
  };

  return (
    <div className="roadmap-page">
      <header className="roadmap-page-header">
        <div className="roadmap-page-title-group">
          <div className="roadmap-page-icon">
            <Map size={24} strokeWidth={2.25} color="#ffffff" />
          </div>
          <div>
            <h1 className="roadmap-page-heading">Study Roadmap</h1>
            <p className="roadmap-page-subtitle">
              Your personalised learning path based on quizzes, flashcards &amp; uploaded materials
            </p>
          </div>
        </div>
        {!loading && steps.length > 0 && (
          <div className="roadmap-subject-badge">
            <Target size={14} />
            {steps.length} Steps Planned
          </div>
        )}
      </header>

      {/* Custom Topic Generator */}
      <form className="roadmap-topic-form" onSubmit={handleGenerateTopicRoadmap}>
        <label className="roadmap-topic-label" htmlFor="roadmap-topic-input">
          Generate a roadmap for any topic:
        </label>
        <div className="roadmap-topic-input-row">
          <input
            id="roadmap-topic-input"
            type="text"
            className="roadmap-topic-input"
            placeholder="e.g. Organic Chemistry, Linear Algebra, World War II..."
            value={topicInput}
            onChange={(e) => setTopicInput(e.target.value)}
            disabled={isGeneratingTopic}
          />
          <button
            type="submit"
            className="roadmap-topic-generate-btn"
            disabled={isGeneratingTopic || !topicInput.trim()}
          >
            {isGeneratingTopic ? (
              <>
                <span className="mini-action-spinner" style={{ marginRight: "6px" }}></span>
                Generating...
              </>
            ) : (
              <>
                <Search size={15} />
                Generate Roadmap
              </>
            )}
          </button>
        </div>
        {topicError && (
          <div className="roadmap-topic-error">
            <AlertTriangle size={14} style={{ marginRight: "6px" }} />
            {topicError}
          </div>
        )}
      </form>

      {error && (
        <div className="roadmap-error-banner" role="alert">
          <AlertTriangle size={16} />
          {error}
        </div>
      )}

      {loading && (
        <ol className="roadmap-skeleton-list" aria-label="Loading roadmap…">
          <SkeletonStep />
          <SkeletonStep />
          <SkeletonStep />
        </ol>
      )}

      {!loading && !hasActivity && steps.length === 0 && (
        <div className="roadmap-empty-state" role="status">
          <div className="roadmap-empty-icon">
            <ClipboardList size={44} strokeWidth={1.75} />
          </div>
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
            <Target size={16} />
            Take a Quiz Now
          </button>
        </div>
      )}

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
                <div className="roadmap-step-number" aria-label={`Step ${step.step_number}`}>
                  {step.step_number}
                </div>

                <div className="roadmap-step-content">
                  <div className="roadmap-step-top">
                    <h3 className="roadmap-step-topic">{step.topic}</h3>
                    <span className={`roadmap-priority-pill ${priorityKey}`}>
                      {priorityKey === "high"
                        ? "High"
                        : priorityKey === "medium"
                        ? "Medium"
                        : "Recommended"}
                    </span>
                  </div>

                  <p className="roadmap-step-desc">{step.description}</p>

                  <div className="roadmap-step-footer">
                    <span className="roadmap-step-duration">
                      <Clock size={14} />
                      {step.estimated_duration || "1–2 days"}
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