import { useState } from "react";
import { useAuth } from "../context/AuthContext.jsx";
import LogoutModal from "./LogoutModal.jsx";
import "./SettingsView.css";

export default function SettingsView() {
  const { userEmail, logout } = useAuth();
  const [showLogoutModal, setShowLogoutModal] = useState(false);
  const initial = userEmail ? userEmail[0].toUpperCase() : "U";

  return (
    <div className="simple-settings-container">
      <div className="simple-settings-card">
        <div className="user-profile-header">
          <div className="user-avatar-large">{initial}</div>
          <div className="user-details">
            <h2 className="settings-title">Account Details</h2>
            <p className="settings-email">{userEmail || "user@example.com"}</p>
          </div>
        </div>

        <div className="settings-divider"></div>

        <div className="settings-action-area">
          <p className="logout-hint">Sign out of your account on this device</p>
          <button
            className="btn-simple-logout"
            onClick={() => setShowLogoutModal(true)}
            type="button"
          >
            Log Out
          </button>
        </div>
      </div>

      <LogoutModal
        isOpen={showLogoutModal}
        onClose={() => setShowLogoutModal(false)}
        onConfirm={() => {
          setShowLogoutModal(false);
          logout();
        }}
      />
    </div>
  );
}
