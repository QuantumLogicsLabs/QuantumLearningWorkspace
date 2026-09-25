import { useState, useEffect } from "react";
import { useAuth } from "../context/AuthContext.jsx";
import { Flame, BarChart3 } from "lucide-react";
import "./StudentCommandCenter.css";

export default function StudentCommandCenter({ onNavigate, files = [] }) {
  const { userEmail, token } = useAuth();
  const [pulseStats, setPulseStats] = useState({
    mastered: 0,
    inReview: 0,
    weakTopics: 0,
  });
  const [streakDays, setStreakDays] = useState(0);
  const [streakActiveToday, setStreakActiveToday] = useState(false);
  const [goalPercent, setGoalPercent] = useState(25);
  const [goalsCompleted, setGoalsCompleted] = useState(1);

  const [lastStudied, setLastStudied] = useState(() => {
    try {
      const saved = localStorage.getItem("studymind_last_activity");
      if (saved) return JSON.parse(saved);
    } catch {}
    return null;
  });

  // Extract friendly display name from user-scoped storage or email
  const getDisplayName = () => {
    if (!userEmail) return "Student";
    const userScoped = localStorage.getItem(`studymind_user_name_${userEmail}`);
    if (userScoped && userScoped.trim()) return userScoped.trim();

    const saved = localStorage.getItem("studymind_user_name");
    const cachedEmail = localStorage.getItem("studymind_cached_email");
    if (saved && saved.trim() && cachedEmail === userEmail) return saved.trim();

    const raw = userEmail.split("@")[0];
    const clean = raw.replace(/[0-9_.-]/g, " ").trim();
    if (!clean) {
      return raw.charAt(0).toUpperCase() + raw.slice(1);
    }
    return clean
      .split(" ")
      .filter(Boolean)
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(" ");
  };

  const [displayName, setDisplayName] = useState(getDisplayName);

  useEffect(() => {
    setDisplayName(getDisplayName());
    const handleProfileUpdate = () => {
      setDisplayName(getDisplayName());
    };
    window.addEventListener("studymind_profile_updated", handleProfileUpdate);
    return () => window.removeEventListener("studymind_profile_updated", handleProfileUpdate);
  }, [userEmail]);

  // Determine smart time-of-day greeting
  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour >= 5 && hour < 12) return "Good Morning";
    if (hour >= 12 && hour < 17) return "Good Afternoon";
    if (hour >= 17 && hour < 22) return "Good Evening";
    return "Good Night";
  };

  // Determine greeting dynamic message based on time of day
  const getGreetingPrompt = (topic) => {
    const hour = new Date().getHours();
    if (hour >= 22 || hour < 5) {
      return (
        <>
          Late night study session? Let's conquer{" "}
          <strong className="highlight-topic">{topic}</strong>!
        </>
      );
    }
    if (hour >= 5 && hour < 12) {
      return (
        <>
          Ready to kick off your day with{" "}
          <strong className="highlight-topic">{topic}</strong>?
        </>
      );
    }
    if (hour >= 12 && hour < 17) {
      return (
        <>
          Ready to power through{" "}
          <strong className="highlight-topic">{topic}</strong> this afternoon?
        </>
      );
    }
    return (
      <>
        Ready to master{" "}
        <strong className="highlight-topic">{topic}</strong> this evening?
      </>
    );
  };

  // Fetch real review stats, live streak, and daily goal progress from backend
  useEffect(() => {
    let isMounted = true;
    let midnightTimerId = null;
    const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:5000";

    async function fetchStatsAndActivity() {
      if (!token) return;
      try {
        // Detect user's local timezone (e.g. "Asia/Karachi", "America/New_York", etc.)
        const userTz = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";

        // 1. Live Study Pulse: Real Streak, Goal %, Mastery from MongoDB scoped to local midnight
        const pulseRes = await fetch(`${API_BASE}/analytics/study-pulse?tz=${encodeURIComponent(userTz)}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (pulseRes.ok) {
          const pulseData = await pulseRes.json();
          if (isMounted && pulseData) {
            if (pulseData.streak_days !== undefined) setStreakDays(pulseData.streak_days);
            if (pulseData.streak_active_today !== undefined) setStreakActiveToday(pulseData.streak_active_today);
            if (pulseData.goal_percent !== undefined) setGoalPercent(pulseData.goal_percent);
            if (pulseData.goals_completed !== undefined) setGoalsCompleted(pulseData.goals_completed);
            setPulseStats({
              mastered: pulseData.mastered || 0,
              inReview: pulseData.in_review || 0,
              weakTopics: pulseData.weak_topics || 0,
            });

            if (pulseData.last_studied && !localStorage.getItem("studymind_last_activity")) {
              setLastStudied({
                topic: pulseData.last_studied.topic,
                type: pulseData.last_studied.type,
                subText: pulseData.last_studied.sub_text,
                targetTab: pulseData.last_studied.target_tab,
              });
            }
          }
        }

        // Fetch user profile name from backend
        try {
          const meRes = await fetch(`${API_BASE}/me`, {
            headers: { Authorization: `Bearer ${token}` },
          });
          if (meRes.ok) {
            const meData = await meRes.json();
            if (isMounted && meData?.name && meData.name.trim()) {
              setDisplayName(meData.name.trim());
              if (userEmail) {
                localStorage.setItem(`studymind_user_name_${userEmail}`, meData.name.trim());
              }
            }
          }
        } catch {}

        // 2. If no local study activity recorded yet, check backend reviews history
        if (!localStorage.getItem("studymind_last_activity")) {
          const revRes = await fetch(`${API_BASE}/flashcards/reviews`, {
            headers: { Authorization: `Bearer ${token}` },
          });
          if (revRes.ok) {
            const revData = await revRes.json();
            if (isMounted && revData && Array.isArray(revData.reviews) && revData.reviews.length > 0) {
              const latestRev = revData.reviews[0];
              setLastStudied({
                topic: latestRev.topic || "Quantum Computing",
                type: "flashcards",
                subText: "Active recall session",
                targetTab: "flashcards",
              });
            }
          }
        }
      } catch (err) {
        console.warn("Could not fetch study pulse:", err);
      }
    }

    fetchStatsAndActivity();

    // Auto-refresh when the clock strikes 12:00 AM midnight in the user's country
    const scheduleMidnightCheck = () => {
      const now = new Date();
      const nextMidnight = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1, 0, 0, 2);
      const msUntilMidnight = Math.max(nextMidnight.getTime() - now.getTime(), 1000);
      midnightTimerId = setTimeout(() => {
        if (isMounted) {
          fetchStatsAndActivity();
          scheduleMidnightCheck();
        }
      }, msUntilMidnight);
    };
    scheduleMidnightCheck();

    return () => {
      isMounted = false;
      if (midnightTimerId) clearTimeout(midnightTimerId);
    };
  }, [token]);

  const greeting = getGreeting();

  // If user actually studied a topic, use that; otherwise use clean focus topic
  const focusTopic = lastStudied?.topic || (files.length > 0 ? "Your Study Materials" : "Personalized Learning");
  const greetingPrompt = getGreetingPrompt(focusTopic);

  // SVG Circular progress math
  const radius = 28;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (goalPercent / 100) * circumference;

  return (
    <section className="command-center-container" aria-label="Student Command Center">
      {/* ── Top Row: Smart Greeting & Streak/Progress Ring ──────── */}
      <div className="command-center-header">
        <div className="command-greeting-block">
          <h2 className="command-greeting-title">
            {greeting}, <span className="greeting-name">{displayName}</span>!
          </h2>
          <p className="command-greeting-subtitle">
            {greetingPrompt}
          </p>
        </div>

        <div className="command-metrics-cluster">
          {/* Streak Counter */}
          <div
            className="streak-badge-card"
            title={streakDays > 0 ? `${streakDays} consecutive day${streakDays !== 1 ? "s" : ""} of active study` : "Start studying today to build your streak!"}
          >
            <Flame className="streak-flame-icon" size={20} />
            <div className="streak-text-group">
              <span className="streak-count">{streakDays}-Day Streak</span>
              <span className="streak-sub">
                {streakActiveToday ? "Active today!" : streakDays > 0 ? "Keep the flame alive!" : "Start your streak!"}
              </span>
            </div>
          </div>

          {/* Circular Goal Progress Ring */}
          <div className="goal-progress-card" title="Daily study goal progress">
            <div className="progress-ring-wrapper">
              <svg className="progress-ring-svg" width="70" height="70" viewBox="0 0 70 70">
                <defs>
                  <linearGradient id="commandProgressGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="#7c3aed" />
                    <stop offset="100%" stopColor="#38bdf8" />
                  </linearGradient>
                </defs>
                <circle
                  className="progress-ring-bg"
                  strokeWidth="5"
                  r={radius}
                  cx="35"
                  cy="35"
                />
                <circle
                  className="progress-ring-fill"
                  strokeWidth="5"
                  strokeDasharray={`${circumference} ${circumference}`}
                  style={{ strokeDashoffset }}
                  strokeLinecap="round"
                  r={radius}
                  cx="35"
                  cy="35"
                />
              </svg>
              <div className="progress-ring-center-text">
                <span className="ring-percent">{goalPercent}%</span>
              </div>
            </div>
            <div className="goal-text-group">
              <span className="goal-title">Daily Goal</span>
              <span className="goal-sub">{goalsCompleted} of 4 completed</span>
            </div>
          </div>
        </div>
      </div>

      {/* ── Bottom Grid: "Jump Back In" Card & Weekly Mastery Pulse ── */}
      <div className="command-center-grid">
        {/* Jump Back In Card */}
        <div className="jump-back-card">
          <div className="jump-back-left">
            <div className="jump-back-badge">
              <span className="pulsing-radar"></span>
              <span>{lastStudied ? "Jump Back In" : "Quick Start"}</span>
            </div>
            <h3 className="jump-back-title">
              {lastStudied ? "Last studied: " : "Ready to study: "}
              <span className="jump-topic">{lastStudied?.topic || focusTopic}</span>
            </h3>
            <p className="jump-back-meta">
              <span className="meta-pill">
                {lastStudied
                  ? lastStudied.subText || "Active session"
                  : "Flashcards & Quizzes ready"}
              </span>
              <span className="meta-dot">•</span>
              <span className="meta-time">
                {lastStudied ? "Continue your momentum" : "Start your next milestone"}
              </span>
            </p>
          </div>
          <button
            type="button"
            className="jump-resume-btn"
            onClick={() => onNavigate?.(lastStudied?.targetTab || "flashcards")}
            title="Resume or begin your study session"
          >
            <span>{lastStudied ? "▶ Resume" : "▶ Start"}</span>
            <span className="btn-arrow">→</span>
          </button>
        </div>

        {/* Weekly Mastery Pulse Mini Analytics */}
        <div className="mastery-pulse-card">
          <div className="pulse-card-header">
            <BarChart3 className="pulse-icon" size={16} />
            <h4 className="pulse-heading">Weekly Mastery Pulse</h4>
          </div>
          <div className="pulse-badges-row">
            {/* Mastered */}
            <div
              className="pulse-badge-item mastered"
              title="Topics and flashcards marked as known"
              onClick={() => onNavigate?.("flashcards")}
            >
              <span className="badge-dot dot-green"></span>
              <span className="badge-value">{pulseStats.mastered}</span>
              <span className="badge-label">Mastered</span>
            </div>

            {/* In Review */}
            <div
              className="pulse-badge-item in-review"
              title="Topics currently in practice and active recall"
              onClick={() => onNavigate?.("quiz")}
            >
              <span className="badge-dot dot-yellow"></span>
              <span className="badge-value">{pulseStats.inReview}</span>
              <span className="badge-label">In Review</span>
            </div>

            {/* Weak Topics */}
            <div
              className="pulse-badge-item weak"
              title="Topics flagged for reinforcement in your roadmap"
              onClick={() => onNavigate?.("roadmap")}
            >
              <span className="badge-dot dot-red"></span>
              <span className="badge-value">{pulseStats.weakTopics}</span>
              <span className="badge-label">Weak Topics</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
