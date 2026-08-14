import { useState, useEffect } from "react";
import { useAuth } from "../context/AuthContext.jsx";
import "./ProfileView.css";

export default function ProfileView() {
  const { token, userEmail, logout, handle401 } = useAuth();

  const [profileData, setProfileData] = useState({
    email: userEmail || "user@example.com",
    created_at: "July 2026",
    document_count: 0,
  });
  const [loading, setLoading] = useState(true);

  // Form states for password change
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  // Eye toggles
  const [showOld, setShowOld] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  // Errors & Feedback
  const [errorOld, setErrorOld] = useState("");
  const [errorNew, setErrorNew] = useState("");
  const [errorConfirm, setErrorConfirm] = useState("");
  const [formMsg, setFormMsg] = useState({ text: "", type: "" });
  const [isSubmitting, setIsSubmitting] = useState(false);

  const API_BASE = "http://localhost:8000";
  const initial = userEmail ? userEmail[0].toUpperCase() : "U";
  const displayName = userEmail ? userEmail.split("@")[0] : "Student User";

  const getLocalQuestionCount = () => {
    try {
      let count = 0;
      const keys = [
        "studymind_chat_history",
        userEmail ? `studymind_chat_history_${userEmail}` : "",
        "studymind_chat_history_guest",
      ];
      for (const k of keys) {
        if (!k) continue;
        const saved = localStorage.getItem(k);
        if (saved) {
          const msgs = JSON.parse(saved);
          if (Array.isArray(msgs)) {
            count += msgs.filter((m) => m && m.role === "user").length;
          }
        }
      }
      return count;
    } catch {
      return 0;
    }
  };

  useEffect(() => {
    if (!token) return;
    setLoading(true);

    Promise.all([
      fetch(`${API_BASE}/me`, {
        headers: { Authorization: `Bearer ${token}` },
      }).then((res) => {
        if (handle401(res)) return null;
        return res.ok ? res.json() : null;
      }),
      fetch(`${API_BASE}/uploads`, {
        headers: { Authorization: `Bearer ${token}` },
      }).then((res) => {
        if (handle401(res)) return [];
        return res.ok ? res.json() : [];
      }),
    ])
      .then(([meData, uploadsData]) => {
        const liveCount = Array.isArray(uploadsData)
          ? uploadsData.length
          : meData?.document_count || 0;
        const liveQuestions =
          meData?.question_count && meData.question_count > 0
            ? meData.question_count
            : getLocalQuestionCount();

        setProfileData({
          email: meData?.email || userEmail || "user@example.com",
          created_at: meData?.created_at || "August 2026",
          document_count: liveCount,
          question_count: liveQuestions,
        });
      })
      .catch(() => {})
      .finally(() => {
        setLoading(false);
      });
  }, [token, userEmail]);

  // Password Requirements Checking
  const hasLength = newPassword.length >= 6;
  const hasUpper = /[A-Z]/.test(newPassword);
  const hasLower = /[a-z]/.test(newPassword);
  const hasNumber = /[0-9]/.test(newPassword);

  const getStrength = () => {
    if (!newPassword) return { score: 0, label: "Enter a new password", color: "" };
    let score = 0;
    if (hasLength) score++;
    if (hasUpper) score++;
    if (hasLower) score++;
    if (hasNumber) score++;

    if (score <= 1) return { score: 1, label: "Weak password", color: "#ef4444", class: "weak" };
    if (score === 2) return { score: 2, label: "Medium strength", color: "#f59e0b", class: "medium" };
    if (score === 3) return { score: 3, label: "Strong password", color: "#22c55e", class: "strong" };
    return { score: 4, label: "Very strong password", color: "#22c55e", class: "strong" };
  };

  const strength = getStrength();

  const handlePasswordSubmit = async (e) => {
    e.preventDefault();
    setErrorOld("");
    setErrorNew("");
    setErrorConfirm("");
    setFormMsg({ text: "", type: "" });

    let valid = true;

    if (!oldPassword) {
      setErrorOld("Please enter your current password");
      valid = false;
    }

    if (!newPassword) {
      setErrorNew("Please enter a new password");
      valid = false;
    } else if (newPassword.length < 6) {
      setErrorNew("Password must be at least 6 characters");
      valid = false;
    } else if (newPassword === oldPassword) {
      setErrorNew("New password must be different from current password");
      valid = false;
    }

    if (!confirmPassword) {
      setErrorConfirm("Please confirm your new password");
      valid = false;
    } else if (newPassword !== confirmPassword) {
      setErrorConfirm("Passwords do not match");
      valid = false;
    }

    if (!valid) return;

    setIsSubmitting(true);

    try {
      const response = await fetch(`${API_BASE}/change-password`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          old_password: oldPassword,
          new_password: newPassword,
        }),
      });

      if (handle401(response)) return;

      const data = await response.json();

      if (!response.ok) {
        setFormMsg({ text: data.detail || "Failed to change password.", type: "error" });
        return;
      }

      setFormMsg({
        text: "✓ Password changed successfully! Logging out... Please log in with your new password.",
        type: "success",
      });

      setOldPassword("");
      setNewPassword("");
      setConfirmPassword("");

      setTimeout(() => {
        logout();
      }, 1500);
    } catch (err) {
      setFormMsg({ text: err.message || "Network error while changing password.", type: "error" });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="profile-view">
      {/* Profile Header Card */}
      <div className="profile-header-card">
        <div className="profile-avatar">{initial}</div>
        <div className="profile-header-info">
          <h2>{displayName}</h2>
          <p className="profile-email">{profileData.email}</p>
          <p className="profile-join-date">Member since {profileData.created_at}</p>
        </div>
        <button className="profile-edit-btn" onClick={() => alert("Profile settings are active.")}>
          Active Account
        </button>
      </div>

      {/* Stats Cards */}
      <div className="profile-stats">
        <div className="stat-card">
          <div className="stat-icon">📄</div>
          <div className="stat-value">{profileData.document_count}</div>
          <div className="stat-label">Documents Uploaded</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">💬</div>
          <div className="stat-value">{profileData.question_count ?? 0}</div>
          <div className="stat-label">Questions Asked</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">⚡</div>
          <div className="stat-value">3</div>
          <div className="stat-label">Days Active</div>
        </div>
      </div>

      {/* Sections Grid */}
      <div className="profile-sections">
        {/* Account Information Card */}
        <div className="profile-section-card">
          <h3>👤 Account Information</h3>
          <div className="info-row">
            <span className="info-label">Email</span>
            <span className="info-value">{profileData.email}</span>
          </div>
          <div className="info-row">
            <span className="info-label">Account Created</span>
            <span className="info-value muted">{profileData.created_at}</span>
          </div>
          <div className="info-row">
            <span className="info-label">Account Status</span>
            <span className="info-value" style={{ color: "var(--color-success)" }}>
              ● Active
            </span>
          </div>
          <div className="info-row">
            <span className="info-label">Documents Uploaded</span>
            <span className="info-value">{profileData.document_count}</span>
          </div>
        </div>

        {/* Change Password Form Card */}
        <div className="profile-section-card">
          <h3>🔒 Change Password</h3>
          <form onSubmit={handlePasswordSubmit} className="change-pw-form">
            {/* Old Password */}
            <div className="form-group">
              <label className="form-label">Current Password</label>
              <div className="password-input-wrapper">
                <input
                  type={showOld ? "text" : "password"}
                  className={`form-input ${errorOld ? "input-error" : ""}`}
                  placeholder="Enter your current password"
                  value={oldPassword}
                  onChange={(e) => setOldPassword(e.target.value)}
                />
                <button
                  type="button"
                  className="eye-btn"
                  onClick={() => setShowOld(!showOld)}
                >
                  {showOld ? "🙈" : "👁️"}
                </button>
              </div>
              <span className="form-error">{errorOld}</span>
            </div>

            {/* New Password */}
            <div className="form-group">
              <label className="form-label">New Password</label>
              <div className="password-input-wrapper">
                <input
                  type={showNew ? "text" : "password"}
                  className={`form-input ${errorNew ? "input-error" : ""}`}
                  placeholder="Enter your new password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                />
                <button
                  type="button"
                  className="eye-btn"
                  onClick={() => setShowNew(!showNew)}
                >
                  {showNew ? "🙈" : "👁️"}
                </button>
              </div>

              {/* Password Strength Meter */}
              <div className="strength-bar-container">
                <div className={`strength-bar ${strength.class || ""}`}></div>
              </div>
              <span className="strength-text" style={{ color: strength.color }}>
                {strength.label}
              </span>
              <span className="form-error">{errorNew}</span>

              {/* Password Requirements */}
              <div className="password-requirements">
                <div className={`req-item ${hasLength ? "met" : ""}`}>
                  <span className="req-icon">{hasLength ? "✓" : "○"}</span> At least 6 characters
                </div>
                <div className={`req-item ${hasUpper ? "met" : ""}`}>
                  <span className="req-icon">{hasUpper ? "✓" : "○"}</span> At least 1 uppercase letter
                </div>
                <div className={`req-item ${hasLower ? "met" : ""}`}>
                  <span className="req-icon">{hasLower ? "✓" : "○"}</span> At least 1 lowercase letter
                </div>
                <div className={`req-item ${hasNumber ? "met" : ""}`}>
                  <span className="req-icon">{hasNumber ? "✓" : "○"}</span> At least 1 number
                </div>
              </div>
            </div>

            {/* Confirm New Password */}
            <div className="form-group">
              <label className="form-label">Confirm New Password</label>
              <div className="password-input-wrapper">
                <input
                  type={showConfirm ? "text" : "password"}
                  className={`form-input ${
                    errorConfirm
                      ? "input-error"
                      : confirmPassword && newPassword === confirmPassword
                      ? "input-success"
                      : ""
                  }`}
                  placeholder="Confirm your new password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                />
                <button
                  type="button"
                  className="eye-btn"
                  onClick={() => setShowConfirm(!showConfirm)}
                >
                  {showConfirm ? "🙈" : "👁️"}
                </button>
              </div>
              <span className="form-error">{errorConfirm}</span>
            </div>

            {/* Success / Error Message Banner */}
            {formMsg.text && (
              <div className={`form-message ${formMsg.type}`}>{formMsg.text}</div>
            )}

            <button
              type="submit"
              className="btn-submit-password"
              disabled={isSubmitting}
            >
              {isSubmitting ? "Updating Password..." : "Change Password"}
            </button>
          </form>
        </div>

        {/* Session Card */}
        <div className="profile-section-card full-width">
          <h3>🚪 Session</h3>
          <div className="info-row">
            <span className="info-label">You are currently logged in</span>
            <button className="btn-logout-profile" onClick={logout}>
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                <polyline points="16 17 21 12 16 7" />
                <line x1="21" y1="12" x2="9" y2="12" />
              </svg>
              Logout
            </button>
          </div>
        </div>

        {/* Danger Zone */}
        <div className="danger-zone full-width">
          <h3>⚠️ Danger Zone</h3>
          <p>Irreversible actions. Please be careful.</p>
          <button
            className="btn-delete-account"
            onClick={() => alert("Are you sure? This will delete your account and all data.")}
          >
            Delete Account
          </button>
        </div>
      </div>
    </div>
  );
}
