import { useState, useEffect } from "react";
import { useAuth } from "../context/AuthContext.jsx";
import "./RecommendedNextSteps.css";

// Fallback placeholder roadmap items per Part C prompt instructions:
// "If Team Lambda is not yet ready with weak-topic detection or the roadmap generator when this phase starts,
// build this page's UI using placeholder data (same mock-data pattern used earlier for chat and quiz)"
const MOCK_ROADMAP_STEPS = [
  {
    step_number: 1,
    topic: "Quantum Computing & Superposition",
    description: "Master qubits, quantum entanglement, and superposition principles through active recall.",
    estimated_duration: "1-2 days",
    priority: "high",
    action_label: "Study Flashcards",
    target_tab: "flashcards",
    accent: "#ef4444",
  },
  {
    step_number: 2,
    topic: "Machine Learning Foundations",
    description: "Reinforce core concepts: bias-variance tradeoff, regularization, and transformers.",
    estimated_duration: "2-3 days",
    priority: "medium",
    action_label: "Take Quiz",
    target_tab: "quiz",
    accent: "#f59e0b",
  },
  {
    step_number: 3,
    topic: "Algorithms & Data Structures",
    description: "Explore search traversals, tree balancing, and hash table complexities with AI assistant.",
    estimated_duration: "2 days",
    priority: "recommended",
    action_label: "Ask AI Chat",
    target_tab: "chat",
    accent: "#22c55e",
  },
];

export default function RecommendedNextSteps({ onNavigate }) {
  const { token } = useAuth();
  const [steps, setSteps] = useState(MOCK_ROADMAP_STEPS);
  const [subject, setSubject] = useState("Your Study Roadmap");
  const [loading, setLoading] = useState(false);

  const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:5000";

  useEffect(() => {
    let isMounted = true;

    async function fetchNextSteps() {
      setLoading(true);
      try {
        const headers = {};
        if (token) {
          headers["Authorization"] = `Bearer ${token}`;
        }

        const res = await fetch(`${API_BASE}/roadmap/next-steps`, { headers });
        if (!res.ok) {
          throw new Error(`Server returned status ${res.status}`);
        }

        const data = await res.json();
        if (isMounted && data && Array.isArray(data.next_steps) && data.next_steps.length > 0) {
          // Take top 2-3 items as required by Part C
          const topSteps = data.next_steps.slice(0, 3).map((item, idx) => ({
            ...item,
            step_number: item.step_number || idx + 1,
            accent:
              item.priority === "high"
                ? "#ef4444"
                : item.priority === "medium"
                ? "#f59e0b"
                : "#22c55e",
          }));
          setSteps(topSteps);
          if (data.subject) setSubject(data.subject);
        }
      } catch (err) {
        // Graceful fallback to mock roadmap data per specification
        if (isMounted) {
          setSteps(MOCK_ROADMAP_STEPS);
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    fetchNextSteps();

    return () => {
      isMounted = false;
    };
  }, [token, API_BASE]);

  const handleActionClick = (targetTab) => {
    if (onNavigate && targetTab) {
      onNavigate(targetTab);
    }
  };

  return (
    <section className="recommended-steps-container" aria-label="Recommended Next Steps">
      <div className="recommended-steps-header">
        <div className="recommended-steps-title-group">
          <div className="recommended-steps-icon">🚀</div>
          <div>
            <h2 className="recommended-steps-heading">Recommended Next Steps</h2>
            <p className="recommended-steps-subtitle">
              Personalized roadmap milestones based on your study activity & materials
            </p>
          </div>
        </div>
        <div className="recommended-steps-badge">
          <span>🎯</span> Top {steps.length} Milestones
        </div>
      </div>

      <div className="recommended-steps-grid">
        {steps.map((step) => {
          const priorityClass = (step.priority || "recommended").toLowerCase();

          return (
            <div
              key={step.step_number}
              className="recommended-step-card"
              style={{ "--step-accent": step.accent || "#7c3aed" }}
            >
              <div>
                <div className="step-card-top">
                  <span className="step-number-badge">Step {step.step_number}</span>
                  <span className={`step-priority-pill ${priorityClass}`}>
                    {step.priority || "Recommended"}
                  </span>
                </div>

                <h3 className="step-topic-title">{step.topic}</h3>
                <p className="step-desc">{step.description}</p>
              </div>

              <div className="step-card-footer">
                <span className="step-duration">
                  <span>⏱️</span> {step.estimated_duration || "1-2 days"}
                </span>
                <button
                  type="button"
                  className="step-action-btn"
                  onClick={() => handleActionClick(step.target_tab || "quiz")}
                  title={`Navigate to ${step.action_label || "Start"}`}
                >
                  <span>{step.action_label || "Continue"}</span> →
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
