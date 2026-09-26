import { useState, useEffect } from "react";
import { X, AlertTriangle, Loader2 } from "lucide-react";
import "./DeleteAccountModal.css";

export default function DeleteAccountModal({
  isOpen,
  onClose,
  onConfirm,
  isDeleting,
  errorMessage,
}) {
  const [confirmText, setConfirmText] = useState("");

  useEffect(() => {
    if (isOpen) {
      setConfirmText("");
    }
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e) => {
      if (e.key === "Escape" && !isDeleting) {
        onClose();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, isDeleting, onClose]);

  if (!isOpen) return null;

  const isConfirmed = confirmText.trim().toLowerCase() === "delete";

  const handleSubmit = (e) => {
    e.preventDefault();
    if (isConfirmed && !isDeleting) {
      onConfirm();
    }
  };

  return (
    <div
      className="delete-modal-backdrop"
      onClick={(e) => {
        if (e.target === e.currentTarget && !isDeleting) {
          onClose();
        }
      }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="delete-modal-title"
    >
      <div className="delete-modal-card">
        {/* Close 'X' Button */}
        <button
          className="delete-modal-close"
          onClick={onClose}
          disabled={isDeleting}
          aria-label="Close modal"
          type="button"
        >
          <X size={16} />
        </button>

        {/* Warning Icon Badge */}
        <div className="delete-icon-wrapper">
          <AlertTriangle size={30} />
        </div>

        {/* Header & Warning */}
        <h2 id="delete-modal-title" className="delete-modal-title">
          Delete Account Permanently?
        </h2>
        <p className="delete-modal-description">
          This action is <strong>irreversible</strong>. Your profile, study roadmaps, uploaded documents, chat history, flashcards, and quizzes will be immediately and permanently deleted.
        </p>

        {/* Confirmation Form */}
        <form onSubmit={handleSubmit} className="delete-modal-form">
          <label htmlFor="confirm-delete-input" className="delete-input-label">
            To confirm, please type <span className="delete-keyword">delete</span> below:
          </label>
          <input
            id="confirm-delete-input"
            type="text"
            className="delete-confirm-input"
            value={confirmText}
            onChange={(e) => setConfirmText(e.target.value)}
            placeholder="Type 'delete' to confirm"
            disabled={isDeleting}
            autoFocus
            autoComplete="off"
            spellCheck="false"
          />

          {errorMessage && (
            <div className="delete-modal-error">
              {errorMessage}
            </div>
          )}

          {/* Action Buttons */}
          <div className="delete-modal-actions">
            <button
              className="btn-modal-cancel"
              onClick={onClose}
              disabled={isDeleting}
              type="button"
            >
              Cancel
            </button>
            <button
              className="btn-modal-confirm-delete"
              type="submit"
              disabled={!isConfirmed || isDeleting}
            >
              {isDeleting ? (
                <>
                  <Loader2 size={16} className="spinner" />
                  <span>Deleting...</span>
                </>
              ) : (
                "Delete My Account"
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
