import { useState, useEffect } from "react";
import { BarChart3, AlertTriangle, Target, TrendingUp, CheckCircle2, XCircle, Map } from "lucide-react";
import { useAuth } from "../context/AuthContext.jsx";
import { useToast } from "../context/ToastContext.jsx";
import "./QuizResultsView.css";
import CustomSelect from "./CustomSelect.jsx";

export default function QuizResultsView({ onLaunchRoadmap }) {
  const { token, handle401 } = useAuth();
  const { showToast } = useToast();

  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedResult, setSelectedResult] = useState(null);
  const [filterTopic, setFilterTopic] = useState("All");
  const [isRoadmapLoading, setIsRoadmapLoading] = useState(false);

  const API_BASE = import.meta.env.VITE_API_BASE_URL;

  // Fetch quiz results
  useEffect(() => {
    if (!token) return;

    setLoading(true);
    setError("");

    fetch(`${API_BASE}/quiz-results`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => {
        if (handle401(res)) return;
        if (!res.ok) throw new Error("Failed to fetch quiz results");
        return res.json();
      })
      .then((data) => {
        if (Array.isArray(data)) {
          setResults(data);
        }
      })
      .catch((err) => {
        setError(err.message || "Failed to load quiz results");
        showToast(err.message || "Failed to load quiz results", "error");
      })
      .finally(() => {
        setLoading(false);
      });
  }, [token]);

  // Calculate statistics
  const calculateStats = () => {
    if (results.length === 0) return { totalQuizzes: 0, avgScore: 0, totalQuestions: 0, correctAnswers: 0 };

    const totalQuestions = results.length;
    const correctAnswers = results.filter((r) => r.is_correct).length;
    const avgScore = totalQuestions > 0 ? Math.round((correctAnswers / totalQuestions) * 100) : 0;

    // Count unique quiz attempts (by date and topic combination)
    const uniqueQuizzes = new Set(
      results.map((r) => `${r.topic}-${r.date_taken}`)
    ).size;

    return {
      totalQuizzes: uniqueQuizzes,
      avgScore,
      totalQuestions,
      correctAnswers,
    };
  };

  // Get unique topics
  const getTopics = () => {
    const topics = new Set(results.map((r) => r.topic));
    return ["All", ...Array.from(topics)];
  };

  // Filter results by topic
  const filteredResults = filterTopic === "All"
    ? results
    : results.filter((r) => r.topic === filterTopic);

  // Group results by date and topic
  const groupedResults = filteredResults.reduce((acc, result) => {
    const key = `${result.topic}-${result.date_taken}`;
    if (!acc[key]) {
      acc[key] = {
        topic: result.topic,
        date: result.date_taken,
        questions: [],
      };
    }
    acc[key].questions.push(result);
    return acc;
  }, {});

  const stats = calculateStats();
  const topics = getTopics();

  // Render empty state
  if (!loading && results.length === 0) {
    return (
      <div className="quiz-results-view">
        <div className="empty-state-card">
          <BarChart3 className="empty-icon" size={40} strokeWidth={1.75} />
          <h3 className="empty-title">No Quiz Results Yet</h3>
          <p className="empty-subtitle">
            Take a quiz to see your results and track your progress
          </p>
        </div>
      </div>
    );
  }

  // Render loading state
  if (loading) {
    return (
      <div className="quiz-results-view">
        <div className="loading-state">
          <div className="loading-dots">
            <span></span><span></span><span></span>
          </div>
          <p className="loading-text">Loading your quiz results...</p>
        </div>
      </div>
    );
  }

  // Render error state
  if (error) {
    return (
      <div className="quiz-results-view">
        <div className="error-state-card">
          <AlertTriangle className="error-icon" size={18} />
          <p className="error-text">{error}</p>
          <button
            className="btn-retry"
            onClick={() => window.location.reload()}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="quiz-results-view">
      {/* Stats Cards */}
      <div className="results-stats">
        <div className="stat-card">
          <div className="stat-icon"><Target size={22} /></div>
          <div className="stat-value">{stats.totalQuizzes}</div>
          <div className="stat-label">Quizzes Taken</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon"><TrendingUp size={22} /></div>
          <div className="stat-value">{stats.avgScore}%</div>
          <div className="stat-label">Average Score</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon"><CheckCircle2 size={22} /></div>
          <div className="stat-value">
            {stats.correctAnswers}/{stats.totalQuestions}
          </div>
          <div className="stat-label">Correct Answers</div>
        </div>
      </div>

      {/* Filter & Controls */}
      <div className="results-controls">
        <div className="filter-group">
          <label className="filter-label">Filter by Topic:</label>
          <CustomSelect
            value={filterTopic}
            onChange={setFilterTopic}
            options={topics}
          />
        </div>
      </div>

      {/* Quiz Results List */}
      <div className="results-list">
        {Object.entries(groupedResults).length === 0 ? (
          <div className="no-results-card">
            <p>No results found for the selected topic</p>
          </div>
        ) : (
          Object.entries(groupedResults).map(([key, group]) => {
            const correctCount = group.questions.filter((q) => q.is_correct).length;
            const totalCount = group.questions.length;
            const scorePercent = Math.round((correctCount / totalCount) * 100);

            return (
              <div key={key} className="result-group-card">
                <div className="result-header">
                  <div className="result-info">
                    <h3 className="result-topic">{group.topic}</h3>
                    <p className="result-date">
                      {new Date(
                        group.date && !group.date.endsWith("Z") && !group.date.includes("+")
                          ? group.date + "Z"
                          : group.date
                      ).toLocaleString("en-US", {
                        month: "short",
                        day: "numeric",
                        year: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </p>
                  </div>
                  <div className="result-score">
                    <div className={`score-circle ${scorePercent >= 70 ? "good" : scorePercent >= 50 ? "fair" : "poor"}`}>
                      <span className="score-percent">{scorePercent}%</span>
                    </div>
                  </div>
                </div>

                <div className="result-stats-row">
                  <span className="result-stat">
                    <strong>{correctCount}</strong> Correct
                  </span>
                  <span className="result-stat">
                    <strong>{totalCount - correctCount}</strong> Incorrect
                  </span>
                  <span className="result-stat">
                    <strong>{totalCount}</strong> Total
                  </span>
                </div>

                <button
                  className="btn-view-details"
                  onClick={() => setSelectedResult(selectedResult === key ? null : key)}
                >
                  {selectedResult === key ? "Hide Details" : "View Details"}
                </button>

                {/* Detailed Results */}
                {selectedResult === key && (
                  <div className="result-details">
                    {group.questions.map((question, idx) => (
                      <div key={idx} className="detail-row">
                        <div className="detail-status">
                          {question.is_correct ? (
                            <CheckCircle2 className="status-correct" size={16} />
                          ) : (
                            <XCircle className="status-incorrect" size={16} />
                          )}
                        </div>
                        <div className="detail-content">
                          <p className="detail-question">Q{idx + 1}: {question.selected_answer}</p>
                          {!question.is_correct && (
                            <p className="detail-correct">
                              Correct answer: <strong>{question.correct_answer}</strong>
                            </p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* Roadmap CTA — calls quiz-performance mode */}
      <div className="topics-to-review-card">
        <h3><Map size={16} style={{ verticalAlign: "middle", marginRight: "6px" }} />Generate Your Study Roadmap</h3>
        <p className="placeholder-text">
          Based on your quiz history, our AI will detect your weak topics and build a personalised study roadmap to help you improve.
        </p>
        <button
          className="btn-launch-roadmap-from-results"
          disabled={isRoadmapLoading || results.length === 0}
          onClick={async () => {
            setIsRoadmapLoading(true);
            try {
              const headers = { "Content-Type": "application/json" };
              if (token) headers["Authorization"] = `Bearer ${token}`;
              const res = await fetch(`${API_BASE}/roadmap/generate-from-quiz-performance`, {
                method: "POST",
                headers,
              });
              const data = await res.json();
              if (data && data.success && Array.isArray(data.next_steps) && data.next_steps.length > 0) {
                if (onLaunchRoadmap) {
                  onLaunchRoadmap({ next_steps: data.next_steps, subject: data.subject });
                }
              } else {
                showToast(data.subject || "No weak topics detected yet — take more quizzes first!", "error");
              }
            } catch {
              showToast("Could not generate roadmap right now. Please try again.", "error");
            } finally {
              setIsRoadmapLoading(false);
            }
          }}
        >
          {isRoadmapLoading ? (
            <>
              <span className="mini-action-spinner" style={{ marginRight: "8px" }}></span>
              Generating Roadmap...
            </>
          ) : (
            <>
              <Map size={15} style={{ marginRight: "7px" }} />
              Generate My Study Roadmap
            </>
          )}
        </button>
        {results.length === 0 && !loading && (
          <p className="roadmap-cta-hint">Take at least one quiz to unlock roadmap generation.</p>
        )}
      </div>
    </div>
  );
}
