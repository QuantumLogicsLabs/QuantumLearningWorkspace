import { useState, useRef, useEffect } from "react";
import { useTheme, COLOR_THEMES } from "../context/ThemeContext.jsx";
import { Palette, Check } from "lucide-react";
import "./ThemeToggle.css";

export default function ThemeToggle({ showLabel = false, className = "" }) {
  const { theme, toggleTheme, isDark, colorTheme, setColorTheme } = useTheme();
  const [pickerOpen, setPickerOpen] = useState(false);
  const pickerRef = useRef(null);

  useEffect(() => {
    function handleClickOutside(e) {
      if (pickerRef.current && !pickerRef.current.contains(e.target)) {
        setPickerOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div className="theme-controls-group">
      <div className="color-picker-wrap" ref={pickerRef}>
        <button
          className="color-picker-trigger"
          onClick={() => setPickerOpen((p) => !p)}
          title="Choose accent color"
          type="button"
          aria-label="Choose accent color"
        >
          <Palette size={16} />
        </button>

        {pickerOpen && (
          <div className="color-picker-menu">
            <span className="color-picker-label">Accent Color</span>
            <div className="color-option-list">
              {COLOR_THEMES.map((c) => (
                <button
                  key={c.id}
                  type="button"
                  className={`color-option-row ${colorTheme === c.id ? "active" : ""}`}
                  onClick={() => {
                    setColorTheme(c.id);
                    setPickerOpen(false);
                  }}
                >
                  <span className="color-option-dot" style={{ background: c.swatch }} />
                  <span className="color-option-text">
                    <span className="color-option-name">{c.label}</span>
                    <span className="color-option-caption">{c.caption}</span>
                  </span>
                  {colorTheme === c.id && <Check size={16} className="color-option-check" />}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

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
    </div>
  );
}