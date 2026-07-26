import { useState } from "react";
import { BrowserRouter, Routes, Route, Navigate, useNavigate } from "react-router-dom";
import "./App.css";
import LandingPage from "./components/LandingPage.jsx";
import Signup from "./components/Signup";
import Login from "./components/Login";

function LandingWithNav() {
  const navigate = useNavigate();
  return <LandingPage onNavigate={(page) => navigate(`/${page}`)} />;
}

function App() {
  const [token, setToken] = useState(null);

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingWithNav />} />
        <Route path="/signup" element={<Signup />} />
        <Route path="/login" element={<Login onLoginSuccess={setToken} />} />
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;