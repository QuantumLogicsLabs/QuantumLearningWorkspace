import { useState } from "react";
import { useAuth } from "../context/AuthContext.jsx";
import "./AuthPage.css";

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
      const response = await fetch(`http://localhost:8000${endpoint}`, {
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

      <div className="auth-right">
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
            <button className="auth-social-btn">G Google</button>
            <button className="auth-social-btn">GitHub</button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default AuthPage;