import { useEffect } from "react";
import "./LogoutModal.css";

export default function LogoutModal({ isOpen, onClose, onConfirm }) {
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e) => {
      if (e.key === "Escape") {
        onClose();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      className="logout-modal-backdrop"
      onClick={(e) => {
        if (e.target === e.currentTarget) {
          onClose();
        }
      }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="logout-modal-title"
    >
      <div className="logout-modal-card">
        {/* Close 'X' Button */}
        <button
          className="logout-modal-close"
          onClick={onClose}
          aria-label="Close modal"
          type="button"
        >
          ✕
        </button>

        {/* Icon Header */}
        <div className="logout-icon-wrapper">
          <svg
            viewBox="0 0 24 24"
            width="28"
            height="28"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
            <polyline points="16 17 21 12 16 7" />
            <line x1="21" y1="12" x2="9" y2="12" />
          </svg>
        </div>

        {/* Modal Content */}
        <h2 id="logout-modal-title" className="logout-modal-title">
          Log Out of StudyMind?
        </h2>
        <p className="logout-modal-description">
          Are you sure you want to log out? You will need to sign in again to access your study materials and chat history.
        </p>

        {/* Action Buttons */}
        <div className="logout-modal-actions">
          <button
            className="btn-modal-cancel"
            onClick={onClose}
            type="button"
          >
            Cancel
          </button>
          <button
            className="btn-modal-confirm-logout"
            onClick={onConfirm}
            type="button"
            autoFocus
          >
            Log Out
          </button>
        </div>
      </div>
    </div>
  );
}
