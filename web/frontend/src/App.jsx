import { useState, useEffect } from "react";
import "./App.css";
import { AuthProvider, useAuth } from "./context/AuthContext.jsx";
import { ToastProvider } from "./context/ToastContext.jsx";
import { ThemeProvider } from "./context/ThemeContext.jsx";
import LandingPage from "./components/LandingPage.jsx";
import Login from "./components/Login.jsx";
import Signup from "./components/Signup.jsx";
import Dashboard from "./components/Dashboard.jsx";
import ChatInterface from "./components/ChatInterface.jsx";

function LoggedInView() {
  const [showChat, setShowChat] = useState(false);
  if (showChat) {
    return <ChatInterface onBack={() => setShowChat(false)} />;
  }
  return <Dashboard onOpenChat={() => setShowChat(true)} />;
}

function AppContent() {
  const [page, setPage] = useState("landing");
  const { login, isLoggedIn } = useAuth();
  const handleLoginSuccess = (accessToken) => {
    login(accessToken);
  };

  // Catch the redirect from Google/GitHub OAuth (backend sends us to /oauth-success?token=...)
  useEffect(() => {
    if (window.location.pathname === "/oauth-success") {
      const params = new URLSearchParams(window.location.search);
      const token = params.get("token");
      if (token) {
        login(token);
      }
      // Clean the URL back to normal, so refreshing doesn't re-trigger this
      window.history.replaceState({}, "", "/");
    }
  }, []);

  if (isLoggedIn) {
    return <LoggedInView />;
  }
  if (page === "login") {
    return <Login onLoginSuccess={handleLoginSuccess} onBackToHome={() => setPage("landing")} />;
  }
  if (page === "signup") {
    return <Signup onLoginSuccess={handleLoginSuccess} onBackToHome={() => setPage("landing")} />;
  }
  return <LandingPage onNavigate={setPage} />;
}

function App() {
  return (
    <ThemeProvider>
      <ToastProvider>
        <AuthProvider>
          <AppContent />
        </AuthProvider>
      </ToastProvider>
    </ThemeProvider>
  );
}

export default App;