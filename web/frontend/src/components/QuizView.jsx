import { useState, useEffect } from "react";
import { FileEdit, Target, CheckCircle2, MessageSquare, AlertTriangle, Circle } from "lucide-react";
import { useAuth } from "../context/AuthContext.jsx";
import { useToast } from "../context/ToastContext.jsx";
import "./QuizView.css";

export default function QuizView({ initialContext, onLaunchRoadmap }) {
  const { token, handle401 } = useAuth();
  const { showToast } = useToast();

  // Quiz Request State
  const [topic, setTopic] = useState(initialContext?.topic || "");
  const [quizType, setQuizType] = useState("mcq");
  const [questionCount, setQuestionCount] = useState(5);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generateError, setGenerateError] = useState("");

  // Quiz Display State
  const [quizId, setQuizId] = useState(initialContext?.quizId || "");
  const [questions, setQuestions] = useState(initialContext?.questions || []);
  const [userAnswers, setUserAnswers] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");

  // Post-submission completion state
  const [quizResult, setQuizResult] = useState(null);
  const [isRoadmapGenerating, setIsRoadmapGenerating] = useState(false);

  const API_BASE = import.meta.env.VITE_API_BASE_URL;

  useEffect(() => {
    if (initialContext) {
      if (initialContext.quizId) setQuizId(initialContext.quizId);
      if (initialContext.questions && initialContext.questions.length > 0) {
        setQuestions(initialContext.questions);
      }
      if (initialContext.topic) setTopic(initialContext.topic);
      setUserAnswers({});
    }
  }, [initialContext]);

  // Handle quiz generation
  const handleGenerateQuiz = async (e) => {
    e.preventDefault();
    setGenerateError("");

    if (!topic.trim()) {
      setGenerateError("Please enter a topic");
      return;
    }

    setIsGenerating(true);

    try {
      const headers = {
        "Content-Type": "application/json",
      };
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }

      const response = await fetch(`${API_BASE}/generate-quiz`, {
        method: "POST",
        headers,
        body: JSON.stringify({
          topic: topic.trim(),
          question_count: parseInt(questionCount),
          quiz_type: quizType,
        }),
      });

      if (handle401(response)) return;

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || errorData.message || "Failed to generate quiz");
      }

      const data = await response.json();

      if (!data.success) {
        throw new Error(data.message || "Quiz generation failed");
      }

      setQuizId(data.quiz_id || "");
      setQuestions(data.questions || []);
      setUserAnswers({});

      try {
        localStorage.setItem(
          "studymind_last_activity",
          JSON.stringify({
            topic: topic.trim(),
            type: "quiz",
            subText: `${data.questions?.length || 5} Questions Quiz`,
            targetTab: "quiz",
            timestamp: Date.now(),
          })
        );
      } catch (e) {
        // Ignore localStorage quota errors
      }

      showToast(`Generated ${data.questions?.length || 0} questions!`, "success");
    } catch (err) {
      const errorMsg = err.message || "Failed to generate quiz";
      setGenerateError(errorMsg);
      showToast(errorMsg, "error");
    } finally {
      setIsGenerating(false);
    }
  };

  // Handle answer input
  const handleAnswerChange = (questionId, value) => {
    setUserAnswers((prev) => ({
      ...prev,
      [questionId]: value,
    }));
  };

  // Handle quiz submission (Server-Side Graded)
  const handleSubmitQuiz = async (e) => {
    e.preventDefault();
    setSubmitError("");

    // Validate all answers are provided
    const allAnswered = questions.every((q) => userAnswers[q.question_id]?.trim());
    if (!allAnswered) {
      setSubmitError("Please answer all questions before submitting");
      return;
    }

    setIsSubmitting(true);

    try {
      // Submit user answers for server-side grading and history storage
      const response = await fetch(`${API_BASE}/submit-quiz`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          quiz_id: quizId,
          topic: topic,
          answers: userAnswers,
        }),
      });

      if (handle401(response)) return;

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || "Failed to submit and grade quiz");
      }

      const gradedData = await response.json();
      const scoreMsg = gradedData.score !== undefined
        ? `Quiz submitted! Score: ${gradedData.score}/${gradedData.total} (${gradedData.percentage}%)`
        : "Quiz submitted successfully!";

      showToast(scoreMsg, "success");

      setQuizResult({
        score: gradedData.score,
        total: gradedData.total,
        percentage: gradedData.percentage,
        topic: topic,
      });
    } catch (err) {
      const errorMsg = err.message || "Failed to submit quiz";
      setSubmitError(errorMsg);
      showToast(errorMsg, "error");
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle "generate roadmap from this quiz performance"
  const handleGenerateRoadmapFromQuiz = async () => {
    setIsRoadmapGenerating(true);
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
        showToast(data.subject || "No weak topics found yet — take more quizzes first.", "error");
      }
    } catch (err) {
      showToast("Could not generate a roadmap right now. Please try again.", "error");
    } finally {
      setIsRoadmapGenerating(false);
    }
  };

  const handleTakeAnotherQuiz = () => {
    setQuizResult(null);
    setTopic("");
    setQuizType("mcq");
    setQuestionCount(5);
    setQuizId("");
    setQuestions([]);
    setUserAnswers({});
  };

  // Render post-submission completion screen
  if (quizResult) {
    return (
      <div className="quiz-view">
        <div className="quiz-request-card quiz-completion-card">
          <CheckCircle2 size={40} className="quiz-completion-icon" />
          <h2>Quiz Submitted!</h2>
          <p className="quiz-completion-score">
            You scored <strong>{quizResult.score}/{quizResult.total}</strong> ({quizResult.percentage}%) on{" "}
            <strong>{quizResult.topic}</strong>
          </p>
          <div className="quiz-completion-actions">
            <button
              type="button"
              className="btn-generate-quiz"
              onClick={handleGenerateRoadmapFromQuiz}
              disabled={isRoadmapGenerating}
            >
              {isRoadmapGenerating ? (
                <>
                  <span className="spinner" style={{ width: "16px", height: "16px", borderWidth: "2px" }}></span>
                  Generating Roadmap...
                </>
              ) : (
                <>
                  <Target size={16} style={{ marginRight: "6px" }} />
                  Get My Study Roadmap
                </>
              )}
            </button>
            <button type="button" className="btn-secondary-quiz" onClick={handleTakeAnotherQuiz}>
              Take Another Quiz
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Render quiz request form
  if (questions.length === 0) {
    return (
      <div className="quiz-view">
        <div className="quiz-request-card">
          <h2><FileEdit size={18} style={{ verticalAlign: "middle", marginRight: "8px" }} />Create a Quiz</h2>
          <p className="quiz-subtitle">Test your knowledge on any topic from your study materials</p>

          <form onSubmit={handleGenerateQuiz} className="quiz-form">
            {/* Topic Input */}
            <div className="form-group">
              <label className="form-label">Topic</label>
              <input
                type="text"
                className="form-input"
                placeholder="e.g., Binary Search Trees, Photosynthesis, World War II"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                disabled={isGenerating}
              />
              <p className="form-hint">Enter a topic from your uploaded documents</p>
            </div>

            {/* Quiz Type Selection */}
            <div className="form-group">
              <label className="form-label">Quiz Type</label>
              <div className="quiz-type-grid">
                {[
                  { value: "mcq", label: "Multiple Choice", icon: Target },
                  { value: "true_false", label: "True/False", icon: CheckCircle2 },
                  { value: "fill_blank", label: "Fill in the Blank", icon: FileEdit },
                  { value: "short_answer", label: "Short Answer", icon: MessageSquare },
                ].map((type) => (
                  <button
                    key={type.value}
                    type="button"
                    className={`quiz-type-btn ${quizType === type.value ? "active" : ""}`}
                    onClick={() => setQuizType(type.value)}
                    disabled={isGenerating}
                  >
                    <span className="type-icon"><type.icon size={18} /></span>
                    <span className="type-label">{type.label}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Question Count */}
            <div className="form-group">
              <label className="form-label">
                Number of Questions: <strong>{questionCount}</strong>
              </label>
              <input
                type="range"
                min="1"
                max="20"
                value={questionCount}
                onChange={(e) => setQuestionCount(e.target.value)}
                className="form-range"
                disabled={isGenerating}
              />
              <p className="form-hint">1 to 20 questions</p>
            </div>

            {/* Error Message */}
            {generateError && (
              <div className="error-banner">
                <span className="error-icon"><AlertTriangle size={16} /></span>
                <span>{generateError}</span>
              </div>
            )}

            {/* Submit Button */}
            <button
              type="submit"
              className="btn-generate-quiz"
              disabled={isGenerating || !topic.trim()}
            >
              {isGenerating ? "Generating Quiz..." : "Generate Quiz"}
            </button>
          </form>
        </div>
      </div>
    );
  }

  // Render quiz questions
  return (
    <div className="quiz-view">
      <div className="quiz-header-section">
        <div className="quiz-header-info">
          <h2><Target size={18} style={{ verticalAlign: "middle", marginRight: "8px" }} />Quiz: {topic}</h2>
          <p className="quiz-progress">
            Question {Object.keys(userAnswers).length} of {questions.length}
          </p>
        </div>
        <button
          className="btn-back-quiz"
          onClick={() => {
            setQuestions([]);
            setQuizId("");
            setUserAnswers({});
            setTopic("");
          }}
        >
          ← Back
        </button>
      </div>

      <form onSubmit={handleSubmitQuiz} className="quiz-questions-form">
        <div className="questions-container">
          {questions.map((question, index) => {
            const isAnswered = !!userAnswers[question.question_id]?.trim();
            return (
              <div key={question.question_id} className="question-card">
                <div className="question-header">
                  <span className="question-number">Q{index + 1}</span>
                  <span className={`question-status ${isAnswered ? "answered" : "unanswered"}`}>
                    {isAnswered ? (<><CheckCircle2 size={13} /> Answered</>) : (<><Circle size={13} /> Unanswered</>)}
                  </span>
                </div>

                <h3 className="question-text">{question.question}</h3>

                {/* MCQ Options */}
                {quizType === "mcq" && question.options && (
                  <div className="options-container">
                    {question.options.map((option, optIdx) => (
                      <label key={optIdx} className="option-label">
                        <input
                          type="radio"
                          name={`question-${question.question_id}`}
                          value={option}
                          checked={userAnswers[question.question_id] === option}
                          onChange={(e) => handleAnswerChange(question.question_id, e.target.value)}
                          className="option-input"
                        />
                        <span className="option-text">{option}</span>
                      </label>
                    ))}
                  </div>
                )}

                {/* True/False Options */}
                {quizType === "true_false" && (
                  <div className="options-container">
                    {["True", "False"].map((option) => (
                      <label key={option} className="option-label">
                        <input
                          type="radio"
                          name={`question-${question.question_id}`}
                          value={option}
                          checked={userAnswers[question.question_id] === option}
                          onChange={(e) => handleAnswerChange(question.question_id, e.target.value)}
                          className="option-input"
                        />
                        <span className="option-text">{option}</span>
                      </label>
                    ))}
                  </div>
                )}

                {/* Fill in the Blank / Short Answer */}
                {(quizType === "fill_blank" || quizType === "short_answer") && (
                  <input
                    type="text"
                    className="answer-input"
                    placeholder={quizType === "fill_blank" ? "Fill in the blank..." : "Enter your answer..."}
                    value={userAnswers[question.question_id] || ""}
                    onChange={(e) => handleAnswerChange(question.question_id, e.target.value)}
                  />
                )}

                <div className="question-meta">
                  <span className="difficulty-badge">{question.difficulty}</span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Error Message */}
        {submitError && (
          <div className="error-banner">
            <span className="error-icon"><AlertTriangle size={16} /></span>
            <span>{submitError}</span>
          </div>
        )}

        {/* Submit Button */}
        <div className="quiz-actions">
          <button
            type="submit"
            className="btn-submit-quiz"
            disabled={isSubmitting || Object.keys(userAnswers).length < questions.length}
          >
            {isSubmitting ? "Submitting..." : "Submit Quiz"}
          </button>
        </div>
      </form>
    </div>
  );
}
