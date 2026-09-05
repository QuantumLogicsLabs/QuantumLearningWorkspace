import { useState, useRef, useEffect } from "react";
import "./CustomSelect.css";

export default function CustomSelect({
  value,
  onChange,
  options = [],
  placeholder = "Select...",
  className = "",
  disabled = false,
  title = "",
}) {
  const [isOpen, setIsOpen] = useState(false);
  const selectRef = useRef(null);

  useEffect(() => {
    function handleClickOutside(e) {
      if (selectRef.current && !selectRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Normalize options (support array of strings or array of { value, label, badge, disabled })
  const normalizedOptions = options.map((opt) => {
    if (typeof opt === "object" && opt !== null) {
      return {
        value: opt.value,
        label: opt.label !== undefined ? opt.label : String(opt.value),
        badge: opt.badge,
        disabled: !!opt.disabled,
      };
    }
    return {
      value: opt,
      label: String(opt),
      disabled: false,
    };
  });

  const selectedOption = normalizedOptions.find((opt) => String(opt.value) === String(value));
  const displayLabel = selectedOption ? selectedOption.label : placeholder;

  return (
    <div className={`custom-select-wrapper ${className} ${disabled ? "disabled" : ""}`} ref={selectRef}>
      <button
        type="button"
        className={`custom-select-trigger ${isOpen ? "active" : ""}`}
        onClick={() => !disabled && setIsOpen(!isOpen)}
        disabled={disabled}
        title={title}
      >
        <span className="custom-select-label">{displayLabel}</span>
        <span className={`custom-select-arrow ${isOpen ? "open" : ""}`}>▾</span>
      </button>

      {isOpen && (
        <div className="custom-select-menu">
          {normalizedOptions.map((opt, i) => {
            const isSelected = String(opt.value) === String(value);
            return (
              <div
                key={`${opt.value}-${i}`}
                className={`custom-select-option ${isSelected ? "selected" : ""} ${opt.disabled ? "disabled" : ""}`}
                onClick={() => {
                  if (!opt.disabled) {
                    onChange(opt.value);
                    setIsOpen(false);
                  }
                }}
              >
                <span className="custom-select-option-text">{opt.label}</span>
                {opt.badge && <span className="custom-select-badge">{opt.badge}</span>}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
