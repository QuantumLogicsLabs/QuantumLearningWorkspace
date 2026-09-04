import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext.jsx";
import { useToast } from "../context/ToastContext.jsx";
import "./FlashcardsView.css";

const QUICK_TOPICS = [
  "Quantum Computing",
  "Machine Learning",
  "Python",
  "Data Structures",
  "Cell Biology",
  "Organic Chemistry",
];

const API_BASE = import.meta.env.VITE_API_BASE_URL;

export default function FlashcardsView() {
  const { token, handle401 } = useAuth();
  const { showToast } = useToast();

  // Generation Form State
  const [topicInput, setTopicInput] = useState("");
  const [numCards, setNumCards] = useState(5);
  const [difficulty, setDifficulty] = useState("medium");
  const [isGenerating, setIsGenerating] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  // Flashcards Study Deck State
  const [currentTopic, setCurrentTopic] = useState("");
  const [cards, setCards] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isFlipped, setIsFlipped] = useState(false);
  const [cardReviews, setCardReviews] = useState({}); // { [cardId]: 'known' | 'still_learning' }
  const [isSavingReview, setIsSavingReview] = useState(false);
  const [isCompleted, setIsCompleted] = useState(false);

  // Generate Flashcards Handler
  const handleGenerateFlashcards = async (e) => {
    if (e && e.preventDefault) e.preventDefault();
    setErrorMsg("");

    const chosenTopic = topicInput.trim();
    if (!chosenTopic) {
      setErrorMsg("Please enter or select a topic to generate flashcards.");
      return;
    }

    setIsGenerating(true);
    try {
      const headers = { "Content-Type": "application/json" };
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }

      const response = await fetch(`${API_BASE}/generate-flashcards`, {
        method: "POST",
        headers,
        body: JSON.stringify({
          topic: chosenTopic,
          num_cards: Number(numCards),
          difficulty,
        }),
      });

      if (response.status === 401) {
        handle401();
        return;
      }

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || `Server returned status ${response.status}`);
      }

      const data = await response.json();
      if (!data.cards || data.cards.length === 0) {
        throw new Error("No flashcards could be generated for this topic.");
      }

      setCards(data.cards);
      setCurrentTopic(data.topic || chosenTopic);
      setCurrentIndex(0);
      setIsFlipped(false);
      setCardReviews({});
      setIsCompleted(false);
      showToast(`Generated ${data.cards.length} flashcards for "${data.topic || chosenTopic}"!`, "success");
    } catch (err) {
      console.error("Flashcards generation error:", err);
      setErrorMsg(err.message || "Failed to generate flashcards. Please try again.");
      showToast(err.message || "Failed to generate flashcards", "error");
    } finally {
      setIsGenerating(false);
    }
  };

  // Quick Chip Select
  const handleChipClick = (t) => {
    setTopicInput(t);
  };

  // Card Flip Toggle
  const handleCardClick = () => {
    setIsFlipped((prev) => !prev);
  };

  // Review Action: "known" or "still_learning"
  const handleReviewAction = async (status) => {
    if (!cards.length || isSavingReview) return;
    const currentCard = cards[currentIndex];
    if (!currentCard) return;

    setIsSavingReview(true);
    const cardId = currentCard.id || `card-${currentIndex}`;

    // Update local state immediately
    const updatedReviews = {
      ...cardReviews,
      [cardId]: status,
    };
    setCardReviews(updatedReviews);

    // Call Backend API
    try {
      const headers = { "Content-Type": "application/json" };
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }

      const response = await fetch(`${API_BASE}/flashcards/review`, {
        method: "POST",
        headers,
        body: JSON.stringify({
          flashcard_id: cardId,
          topic: currentTopic,
          status,
        }),
      });

      if (response.status === 401) {
        handle401();
        return;
      }

      if (!response.ok) {
        console.warn(`Review save returned ${response.status}`);
      }
    } catch (err) {
      console.warn("Failed to sync review status with backend:", err);
    } finally {
      setIsSavingReview(false);
    }

    // Advance to next card or complete deck
    if (currentIndex < cards.length - 1) {
      setIsFlipped(false);
      setCurrentIndex((prev) => prev + 1);
    } else {
      setIsCompleted(true);
      showToast("🎉 Deck completed! Great study session!", "success");
    }
  };

  // Navigation: Next / Prev
  const handleNextCard = () => {
    if (currentIndex < cards.length - 1) {
      setIsFlipped(false);
      setCurrentIndex((prev) => prev + 1);
    }
  };

  const handlePrevCard = () => {
    if (currentIndex > 0) {
      setIsFlipped(false);
      setCurrentIndex((prev) => prev - 1);
    }
  };

  // Shuffle Deck
  const handleShuffleDeck = () => {
    const shuffled = [...cards].sort(() => Math.random() - 0.5);
    setCards(shuffled);
    setCurrentIndex(0);
    setIsFlipped(false);
    showToast("Deck shuffled!", "info");
  };

  // Restart Deck
  const handleRestartDeck = () => {
    setCurrentIndex(0);
    setIsFlipped(false);
    setCardReviews({});
    setIsCompleted(false);
  };

  // Review Only Weak Cards
  const handleReviewWeakCards = () => {
    const weakCards = cards.filter(
      (c, idx) => cardReviews[c.id || `card-${idx}`] === "still_learning"
    );
    if (weakCards.length === 0) {
      showToast("No cards marked as Still Learning! You mastered all cards!", "success");
      handleRestartDeck();
      return;
    }
    setCards(weakCards);
    setCurrentIndex(0);
    setIsFlipped(false);
    setCardReviews({});
    setIsCompleted(false);
    showToast(`Studying ${weakCards.length} cards needing practice`, "info");
  };

  // Keyboard Shortcuts (Space/Enter to flip, Left/Right arrows to navigate)
  const handleKeyDown = useCallback(
    (e) => {
      if (!cards.length || isCompleted) return;
      if (e.target.tagName === "INPUT" || e.target.tagName === "SELECT") return;

      if (e.code === "Space" || e.key === " ") {
        e.preventDefault();
        setIsFlipped((prev) => !prev);
      } else if (e.key === "ArrowRight") {
        e.preventDefault();
        handleNextCard();
      } else if (e.key === "ArrowLeft") {
        e.preventDefault();
        handlePrevCard();
      } else if (e.key === "1") {
        e.preventDefault();
        handleReviewAction("still_learning");
      } else if (e.key === "2") {
        e.preventDefault();
        handleReviewAction("known");
      }
    },
    [cards, currentIndex, isCompleted]
  );

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  // Derived Metrics
  const knownCount = Object.values(cardReviews).filter((s) => s === "known").length;
  const learningCount = Object.values(cardReviews).filter((s) => s === "still_learning").length;
  const currentCard = cards[currentIndex];
  const currentCardStatus = currentCard ? cardReviews[currentCard.id || `card-${currentIndex}`] : null;
  const progressPercent = cards.length ? Math.round(((currentIndex + (currentCardStatus ? 1 : 0)) / cards.length) * 100) : 0;

  return (
    <div className="flashcards-container">
      {/* ─── Topic Setup Section ────────────────────────────────────────────── */}
      <section className="flashcards-setup-card">
        <div className="flashcards-setup-header">
          <div className="flashcards-setup-icon">🎴</div>
          <div>
            <h2 className="flashcards-setup-title">Create Flashcards</h2>
            <p className="flashcards-setup-subtitle">
              Select or type any topic to generate active recall study cards
            </p>
          </div>
        </div>

        <form onSubmit={handleGenerateFlashcards} className="flashcards-form">
          <div className="flashcards-input-group">
            <label className="flashcards-label" htmlFor="flashcard-topic">
              Study Topic:
            </label>
            <div className="flashcards-input-row">
              <input
                id="flashcard-topic"
                type="text"
                className="flashcards-topic-input"
                placeholder="e.g. Quantum Computing, Machine Learning, Photosynthesis..."
                value={topicInput}
                onChange={(e) => setTopicInput(e.target.value)}
                disabled={isGenerating}
              />
              <select
                className="flashcards-select"
                value={numCards}
                onChange={(e) => setNumCards(Number(e.target.value))}
                disabled={isGenerating}
                title="Number of cards"
              >
                <option value={5}>5 Cards</option>
                <option value={10}>10 Cards</option>
                <option value={15}>15 Cards</option>
                <option value={20}>20 Cards</option>
              </select>
              <select
                className="flashcards-select"
                value={difficulty}
                onChange={(e) => setDifficulty(e.target.value)}
                disabled={isGenerating}
                title="Difficulty level"
              >
                <option value="easy">Easy</option>
                <option value="medium">Medium</option>
                <option value="hard">Hard</option>
              </select>
              <button
                type="submit"
                className="flashcards-generate-btn"
                disabled={isGenerating || !topicInput.trim()}
              >
                {isGenerating ? (
                  <>
                    <span className="spinner" style={{ width: "16px", height: "16px", borderWidth: "2px" }}></span>
                    Generating...
                  </>
                ) : (
                  "Generate Flashcards"
                )}
              </button>
            </div>

            {/* Quick Topic Chips */}
            <div className="flashcards-topic-chips">
              <span style={{ fontSize: "0.78rem", color: "var(--color-text-muted)", alignSelf: "center" }}>
                Suggested:
              </span>
              {QUICK_TOPICS.map((topic) => (
                <button
                  type="button"
                  key={topic}
                  className="flashcard-topic-chip"
                  onClick={() => handleChipClick(topic)}
                >
                  {topic}
                </button>
              ))}
            </div>
          </div>

          {errorMsg && (
            <div className="flashcards-error-banner">
              ⚠️ {errorMsg}
            </div>
          )}
        </form>
      </section>

      {/* ─── Active Study Deck View ─────────────────────────────────────────── */}
      {cards.length > 0 && !isCompleted && (
        <section style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
          {/* Deck Header & Progress Bar */}
          <div className="flashcards-deck-header">
            <div className="flashcards-deck-info">
              <span className="flashcards-topic-tag">{currentTopic}</span>
              <span className="flashcards-counter-text">
                Card {currentIndex + 1} of {cards.length}
              </span>
            </div>
            <div className="flashcards-stats-pills">
              <span className="stat-pill known" title="Marked as Known">
                ✓ Known: {knownCount}
              </span>
              <span className="stat-pill learning" title="Marked as Still Learning">
                ↺ Learning: {learningCount}
              </span>
            </div>
          </div>

          {/* Progress Bar */}
          <div className="flashcards-progress-track">
            <div
              className="flashcards-progress-fill"
              style={{ width: `${progressPercent}%` }}
            ></div>
          </div>

          {/* 3D Flip Flashcard */}
          <div
            className={`flashcard-scene ${isFlipped ? "is-flipped" : ""}`}
            onClick={handleCardClick}
            role="button"
            tabIndex={0}
            aria-label="Flashcard. Click or press space to flip."
          >
            <div className="flashcard-inner">
              {/* Front Face: Question */}
              <div className="flashcard-face flashcard-face-front">
                <div className="flashcard-badge-row">
                  <span className="flashcard-type-badge">❓ Question</span>
                  {currentCardStatus && (
                    <span className={`flashcard-status-indicator ${currentCardStatus}`}>
                      {currentCardStatus === "known" ? "✓ Marked Known" : "↺ Still Learning"}
                    </span>
                  )}
                </div>

                <div className="flashcard-body-text">
                  {currentCard?.front || currentCard?.question || "No question available"}
                </div>

                <div className="flashcard-flip-prompt">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67" />
                  </svg>
                  Click or tap card to reveal answer (or press Space)
                </div>
              </div>

              {/* Back Face: Answer */}
              <div className="flashcard-face flashcard-face-back">
                <div className="flashcard-badge-row">
                  <span className="flashcard-type-badge">💡 Answer & Explanation</span>
                  {currentCardStatus && (
                    <span className={`flashcard-status-indicator ${currentCardStatus}`}>
                      {currentCardStatus === "known" ? "✓ Marked Known" : "↺ Still Learning"}
                    </span>
                  )}
                </div>

                <div className="flashcard-body-text">
                  {currentCard?.back || currentCard?.answer || "No answer available"}
                </div>

                <div className="flashcard-flip-prompt">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67" />
                  </svg>
                  Click to flip back to question
                </div>
              </div>
            </div>
          </div>

          {/* Study Progress Actions: "Still Learning" (Amber) and "Known" (Green) */}
          <div className="flashcards-action-bar">
            <button
              type="button"
              className="study-action-btn btn-learning"
              onClick={() => handleReviewAction("still_learning")}
              disabled={isSavingReview}
              title="Press 1 on keyboard"
            >
              <span>↺</span> Still Learning
            </button>
            <button
              type="button"
              className="study-action-btn btn-known"
              onClick={() => handleReviewAction("known")}
              disabled={isSavingReview}
              title="Press 2 on keyboard"
            >
              <span>✓</span> Known
            </button>
          </div>

          {/* Secondary Deck Navigation */}
          <div className="flashcards-nav-controls">
            <button
              type="button"
              className="secondary-nav-btn"
              onClick={handlePrevCard}
              disabled={currentIndex === 0}
            >
              ← Previous
            </button>
            <div style={{ display: "flex", gap: "0.5rem" }}>
              <button
                type="button"
                className="secondary-nav-btn"
                onClick={handleShuffleDeck}
                title="Shuffle cards randomly"
              >
                🔀 Shuffle
              </button>
              <button
                type="button"
                className="secondary-nav-btn"
                onClick={handleRestartDeck}
                title="Restart deck from first card"
              >
                🔄 Reset
              </button>
            </div>
            <button
              type="button"
              className="secondary-nav-btn"
              onClick={handleNextCard}
              disabled={currentIndex === cards.length - 1}
            >
              Next →
            </button>
          </div>
        </section>
      )}

      {/* ─── Completed Deck Summary Screen ─────────────────────────────────── */}
      {isCompleted && (
        <section className="flashcards-summary-card">
          <div className="summary-trophy-icon">🏆</div>
          <h3 className="summary-title">Deck Completed!</h3>
          <p className="summary-desc">
            You reviewed all {cards.length} flashcards for <strong>{currentTopic}</strong>.
          </p>

          <div className="summary-metrics-grid">
            <div className="summary-metric-box">
              <span className="summary-metric-val">{cards.length}</span>
              <span className="summary-metric-lbl">Total Cards</span>
            </div>
            <div className="summary-metric-box">
              <span className="summary-metric-val known">{knownCount}</span>
              <span className="summary-metric-lbl">Known</span>
            </div>
            <div className="summary-metric-box">
              <span className="summary-metric-val learning">{learningCount}</span>
              <span className="summary-metric-lbl">Still Learning</span>
            </div>
          </div>

          <div className="summary-actions-row">
            {learningCount > 0 && (
              <button
                type="button"
                className="study-action-btn btn-learning"
                onClick={handleReviewWeakCards}
                style={{ maxWidth: "240px" }}
              >
                ↺ Practice {learningCount} Weak Cards
              </button>
            )}
            <button
              type="button"
              className="study-action-btn btn-known"
              onClick={handleRestartDeck}
              style={{ maxWidth: "200px" }}
            >
              🔄 Study Again
            </button>
          </div>
        </section>
      )}
    </div>
  );
}
