import { createContext, useContext, useState, useCallback, useRef } from "react";
import "./ToastContext.css";

const ToastContext = createContext(null);

let idCounter = 0;

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const recentToastsRef = useRef(new Map());

  const showToast = useCallback((message, type = "info", duration = 4000) => {
    if (!message) return;

    const key = `${type}:${message}`;
    const now = Date.now();
    const lastShown = recentToastsRef.current.get(key) || 0;

    // Suppress duplicate identical toast triggered within 2000ms
    if (now - lastShown < 2000) {
      return;
    }
    recentToastsRef.current.set(key, now);

    const id = ++idCounter;
    setToasts((prev) => {
      // Suppress if identical message is already in active toasts
      if (prev.some((t) => t.message === message && t.type === type)) {
        return prev;
      }
      return [...prev, { id, message, type }];
    });

    if (duration > 0) {
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, duration);
    }
  }, []);

  const dismissToast = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      <div className="toast-container">
        {toasts.map((toast) => (
          <div key={toast.id} className={`toast toast-${toast.type}`}>
            <span className="toast-message">{toast.message}</span>
            <button className="toast-close" onClick={() => dismissToast(toast.id)}>
              ×
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  return useContext(ToastContext);
}