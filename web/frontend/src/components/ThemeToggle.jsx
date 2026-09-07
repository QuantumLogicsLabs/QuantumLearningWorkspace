import { useTheme } from "../context/ThemeContext.jsx";
import "./ThemeToggle.css";

export default function ThemeToggle({ showLabel = false, className = "" }) {
  const { theme, toggleTheme, isDark } = useTheme();

  return (
    <button
      className={`theme-toggle-btn ${className}`}
      onClick={toggleTheme}
      aria-label={`Switch to ${isDark ? "light" : "dark"} theme`}
      title={`Switch to ${isDark ? "Light" : "Dark"} Mode`}
      type="button"
    >
      <div className="theme-toggle-icon-container">
        {isDark ? (
          <svg
            className="theme-svg sun-svg"
            viewBox="0 0 24 24"
            width="18"
            height="18"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <circle cx="12" cy="12" r="5" fill="#f59e0b" stroke="#f59e0b" />
            <line x1="12" y1="1" x2="12" y2="3" stroke="#f59e0b" />
            <line x1="12" y1="21" x2="12" y2="23" stroke="#f59e0b" />
            <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" stroke="#f59e0b" />
            <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" stroke="#f59e0b" />
            <line x1="1" y1="12" x2="3" y2="12" stroke="#f59e0b" />
            <line x1="21" y1="12" x2="23" y2="12" stroke="#f59e0b" />
            <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" stroke="#f59e0b" />
            <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" stroke="#f59e0b" />
          </svg>
        ) : (
          <svg
            className="theme-svg moon-svg"
            viewBox="0 0 24 24"
            width="18"
            height="18"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path
              d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"
              fill="#6366f1"
              stroke="#6366f1"
            />
          </svg>
        )}
      </div>
      {showLabel && (
        <span className="theme-toggle-label">
          {isDark ? "Light Mode" : "Dark Mode"}
        </span>
      )}
    </button>
  );
}
