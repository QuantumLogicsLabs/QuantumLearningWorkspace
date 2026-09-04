import { useState } from "react";
import { useAuth } from "../context/AuthContext.jsx";
import ThemeToggle from "./ThemeToggle.jsx";
import "./AuthPage.css";

const API_BASE = import.meta.env.VITE_API_BASE_URL;

function GoogleIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 48 48">
      <path fill="#FFC107" d="M43.611,20.083H42V20H24v8h11.303c-1.649,4.657-6.08,8-11.303,8c-6.627,0-12-5.373-12-12
        c0-6.627,5.373-12,12-12c3.059,0,5.842,1.154,7.961,3.039l5.657-5.657C34.046,6.053,29.268,4,24,4C12.955,4,4,12.955,4,24
        c0,11.045,8.955,20,20,20c11.045,0,20-8.955,20-20C44,22.659,43.862,21.35,43.611,20.083z"/>
      <path fill="#FF3D00" d="M6.306,14.691l6.571,4.819C14.655,15.108,18.961,12,24,12c3.059,0,5.842,1.154,7.961,3.039
        l5.657-5.657C34.046,6.053,29.268,4,24,4C16.318,4,9.656,8.337,6.306,14.691z"/>
      <path fill="#4CAF50" d="M24,44c5.166,0,9.86-1.977,13.409-5.192l-6.19-5.238C29.211,35.091,26.715,36,24,36
        c-5.202,0-9.619-3.317-11.283-7.946l-6.522,5.025C9.505,39.556,16.227,44,24,44z"/>
      <path fill="#1976D2" d="M43.611,20.083H42V20H24v8h11.303c-0.792,2.237-2.231,4.166-4.087,5.571
        c0.001-0.001,0.002-0.001,0.003-0.002l6.19,5.238C36.971,39.205,44,34,44,24
        C44,22.659,43.862,21.35,43.611,20.083z"/>
    </svg>
  );
}

function GitHubIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 0.297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385 0.6 0.113 0.82-0.258 0.82-0.577 0-0.285-0.01-1.04-0.015-2.04-3.338 0.724-4.042-1.61-4.042-1.61-0.546-1.385-1.333-1.755-1.333-1.755-1.089-0.744 0.083-0.729 0.083-0.729 1.205 0.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492 0.997 0.108-0.775 0.418-1.305 0.762-1.605-2.665-0.3-5.466-1.332-5.466-5.93 0-1.31 0.469-2.381 1.236-3.221-0.124-0.303-0.535-1.523 0.117-3.176 0 0 1.008-0.322 3.301 1.23 0.957-0.266 1.983-0.399 3.003-0.404 1.02 0.005 2.047 0.138 3.006 0.404 2.291-1.552 3.297-1.23 3.297-1.23 0.653 1.653 0.242 2.873 0.118 3.176 0.77 0.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.625-5.479 5.921 0.43 0.372 0.814 1.103 0.814 2.222 0 1.606-0.014 2.898-0.014 3.293 0 0.321 0.217 0.694 0.825 0.576 4.765-1.588 8.199-6.084 8.199-11.385 0-6.627-5.373-12-12-12z"/>
    </svg>
  );
}

function AuthPage({ initialMode = "login", onLoginSuccess, onBackToHome }) {
  const [mode, setMode] = useState(initialMode);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [isError, setIsError] = useState(false);
  const { login } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setMessage("");
    setIsError(false);

    const endpoint = mode === "login" ? "/login" : "/signup";

    try {
      const response = await fetch(`${API_BASE}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      const data = await response.json();

      if (!response.ok) {
        setIsError(true);
        setMessage(data.detail || "Something went wrong");
        return;
      }

      if (mode === "login") {
        if (data.access_token) {
          login(data.access_token);
        }
        onLoginSuccess?.(data.access_token);
        setMessage("Logged in successfully!");
      } else {
        setMessage("Account created! You can sign in now.");
        setMode("login");
      }
    } catch (err) {
      setIsError(true);
      setMessage("Could not reach the server. Is the backend running?");
    }
  };

  const handleGoogleLogin = () => {
    window.location.href = `${API_BASE}/auth/google/login`;
  };

  const handleGithubLogin = () => {
    window.location.href = `${API_BASE}/auth/github/login`;
  };

  return (
    <div className="auth-container">
      <div className="auth-left">
        <div className="particle" style={{ width: 6, height: 6, top: "15%", left: "70%", animationDelay: "0s" }}></div>
        <div className="particle" style={{ width: 4, height: 4, top: "35%", left: "40%", animationDelay: "1.5s" }}></div>
        <div className="particle" style={{ width: 8, height: 8, top: "55%", left: "80%", animationDelay: "3s" }}></div>
        <div className="particle" style={{ width: 5, height: 5, top: "70%", left: "20%", animationDelay: "2s" }}></div>
        <div className="particle" style={{ width: 3, height: 3, top: "85%", left: "60%", animationDelay: "4s" }}></div>
        <div className="particle" style={{ width: 6, height: 6, top: "25%", left: "15%", animationDelay: "0.5s" }}></div>

        <div className="auth-logo">
          <div className="auth-logo-icon"></div>
          <span className="auth-logo-text">StudyMind AI</span>
        </div>

        <h1 className="auth-heading">
          Your Personal<br />
          <span>AI Learning</span> Companion
        </h1>

        <p className="auth-subtext">
          Upload PDFs, YouTube lectures, articles, and notes. Let AI understand
          your material, generate study aids, and build a personalized learning roadmap.
        </p>

        <div className="auth-feature">
          <span className="auth-feature-icon">🤖</span>
          <div>
            <div className="auth-feature-title">RAG-Powered Chatbot</div>
            <div className="auth-feature-desc">Ask questions about your study material</div>
          </div>
        </div>

        <div className="auth-feature">
          <span className="auth-feature-icon">📖</span>
          <div>
            <div className="auth-feature-title">Knowledge Graph</div>
            <div className="auth-feature-desc">Visualize connections between concepts</div>
          </div>
        </div>

        <div className="auth-feature">
          <span className="auth-feature-icon">🎯</span>
          <div>
            <div className="auth-feature-title">Smart Study Planner</div>
            <div className="auth-feature-desc">AI identifies weak topics & plans your path</div>
          </div>
        </div>

        <button
          type="button"
          className="auth-back"
          style={{ background: "none", border: "none", cursor: "pointer", padding: 0 }}
          onClick={() => onBackToHome ? onBackToHome() : (window.location.href = "/")}
        >
          ← Back to homepage
        </button>
      </div>

      <div className="auth-right" style={{ position: "relative" }}>
        <div style={{ position: "absolute", top: "20px", right: "24px" }}>
          <ThemeToggle />
        </div>
        <div className="auth-card">
          <h1>{mode === "login" ? "Welcome Back" : "Create Account"}</h1>
          <p className="auth-card-subtext">
            {mode === "login"
              ? "Sign in to continue your learning journey"
              : "Start your AI-powered learning journey"}
          </p>

          <div className="auth-tabs">
            <button
              type="button"
              className={`auth-tab ${mode === "login" ? "active" : ""}`}
              onClick={() => { setMode("login"); setMessage(""); }}
            >
              Sign In
            </button>
            <button
              type="button"
              className={`auth-tab ${mode === "signup" ? "active" : ""}`}
              onClick={() => { setMode("signup"); setMessage(""); }}
            >
              Sign Up
            </button>
          </div>

          <div className="auth-form-wrapper" key={mode}>
            <form className="auth-form" onSubmit={handleSubmit}>
              <label className="auth-label">Email Address</label>
              <input
                type="email"
                className="auth-input"
                placeholder="Enter your email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />

              <label className="auth-label">Password</label>
              <input
                type="password"
                className="auth-input"
                placeholder={mode === "login" ? "Enter your password" : "Create a strong password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={6}
              />

              {mode === "login" && (
                <div className="auth-row">
                  <label><input type="checkbox" /> Remember me</label>
                  <a href="#">Forgot password?</a>
                </div>
              )}

              <button type="submit" className="auth-submit">
                {mode === "login" ? "Sign In" : "Create Account"}
              </button>
            </form>

            {message && (
              <p className="auth-message" style={{ color: isError ? "var(--color-error)" : "var(--color-success)" }}>
                {message}
              </p>
            )}
          </div>

          <div className="auth-divider">or continue with</div>
          <div className="auth-social-row">
            <button type="button" className="auth-social-btn" onClick={handleGoogleLogin}>
              <GoogleIcon />
              Google
            </button>
            <button type="button" className="auth-social-btn" onClick={handleGithubLogin}>
              <GitHubIcon />
              GitHub
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default AuthPage;