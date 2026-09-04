import { createContext, useContext, useState, useEffect } from "react";
import { useToast } from "./ToastContext.jsx";

const AuthContext = createContext(null);

function parseJwt(token) {
  if (!token) return null;
  try {
    const base64Url = token.split(".")[1];
    if (!base64Url) return null;
    const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split("")
        .map((c) => "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2))
        .join("")
    );
    return JSON.parse(jsonPayload);
  } catch {
    return null;
  }
}

export function AuthProvider({ children }) {
  const toastContext = useToast();
  const showToast = toastContext?.showToast || (() => {});

  const [token, setToken] = useState(() => {
    try {
      const stored = localStorage.getItem("auth_token");
      if (!stored) return null;
      const payload = parseJwt(stored);
      if (payload && payload.exp && payload.exp * 1000 < Date.now()) {
        localStorage.removeItem("auth_token");
        return null;
      }
      return stored;
    } catch {
      return null;
    }
  });

  const [userEmail, setUserEmail] = useState(() => {
    const payload = parseJwt(token);
    return payload ? payload.sub : null;
  });

  useEffect(() => {
    if (!token) {
      setUserEmail(null);
      return;
    }
    const payload = parseJwt(token);
    if (payload && payload.exp && payload.exp * 1000 < Date.now()) {
      logoutExpired();
    } else if (payload && payload.sub) {
      setUserEmail(payload.sub);
    }
  }, [token]);

  const login = (newToken) => {
    try {
      localStorage.setItem("auth_token", newToken);
    } catch {
      // ignore
    }
    setToken(newToken);
    const payload = parseJwt(newToken);
    if (payload && payload.sub) {
      setUserEmail(payload.sub);
    }
    showToast("Logged in successfully!", "success");
  };

  const logoutExpired = () => {
    try {
      localStorage.removeItem("auth_token");
    } catch {
      // ignore
    }
    setToken(null);
    setUserEmail(null);
    showToast("Your session has expired - please log in again", "error");
  };

  const logout = () => {
    try {
      localStorage.removeItem("auth_token");
    } catch {
      // ignore
    }
    setToken(null);
    setUserEmail(null);
    showToast("Logged out successfully", "info");
  };

  const handle401 = (response) => {
    if (response && response.status === 401) {
      logoutExpired();
      return true;
    }
    return false;
  };

  const isLoggedIn = token !== null;

  return (
    <AuthContext.Provider
      value={{
        token,
        userEmail,
        login,
        logout,
        handle401,
        isLoggedIn,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}