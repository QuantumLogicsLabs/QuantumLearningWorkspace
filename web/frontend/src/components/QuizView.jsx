import { useState, useEffect } from "react";
import { useAuth } from "../context/AuthContext.jsx";
import { useToast } from "../context/ToastContext.jsx";
import "./QuizView.css";

export default function QuizView() {
  const { token, handle401 } = useAuth();
  const { showToast } = useToast();

  // Quiz Request State
  const [topic, setTopic] = useState("");
  const [quizType, setQuizType] = useState("mcq");
  const [questionCount, setQuestionCount] = useState(5);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generateError, setGenerateError] = useState("");

  // Quiz Display State
  const [quizId, setQuizId] = useState("");
  const [questions, setQuestions] = useState([]);
  const [userAnswers, setUserAnswers] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");

  const API_BASE = import.meta.env.VITE_API_BASE_URL;

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

      // Reset form
      setTopic("");
      setQuizType("mcq");
      setQuestionCount(5);
      setQuizId("");
      setQuestions([]);
      setUserAnswers({});
    } catch (err) {
      const errorMsg = err.message || "Failed to submit quiz";
      setSubmitError(errorMsg);
      showToast(errorMsg, "error");
    } finally {
      setIsSubmitting(false);
    }
  };

  // Render quiz request form
  if (questions.length === 0) {
    return (
      <div className="quiz-view">
        <div className="quiz-request-card">
          <h2>📝 Create a Quiz</h2>
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
                  { value: "mcq", label: "Multiple Choice", icon: "🎯" },
                  { value: "true_false", label: "True/False", icon: "✓" },
                  { value: "fill_blank", label: "Fill in the Blank", icon: "📝" },
                  { value: "short_answer", label: "Short Answer", icon: "💬" },
                ].map((type) => (
                  <button
                    key={type.value}
                    type="button"
                    className={`quiz-type-btn ${quizType === type.value ? "active" : ""}`}
                    onClick={() => setQuizType(type.value)}
                    disabled={isGenerating}
                  >
                    <span className="type-icon">{type.icon}</span>
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
                <span className="error-icon">⚠️</span>
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
          <h2>🎯 Quiz: {topic}</h2>
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
                    {isAnswered ? "✓ Answered" : "○ Unanswered"}
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
            <span className="error-icon">⚠️</span>
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
