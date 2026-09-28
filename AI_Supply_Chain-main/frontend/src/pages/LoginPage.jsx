import { useState } from "react";
import { getCurrentUser, loginUser } from "../api/authApi";
import InteractiveBackground from "../components/InteractiveBackground";

function LoginPage({ onLogin }) {
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("admin123");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError("");

    try {
      const response = await loginUser(username, password);
      const session = {
        token: response.access_token,
        username: response.username,
        role: response.role,
      };

      try {
        const meJson = await getCurrentUser();

        if (meJson?.id) {
          session.userId = meJson.id;
          session.name = meJson.name || meJson.username;
          session.supplier_id = meJson.supplier_id || null;
        }
      } catch {
        session.userId = null;
        session.name = response.username;
        session.supplier_id = null;
      }

      onLogin(session);
    } catch (err) {
      setError(err?.response?.data?.detail || "Login failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-viewport">
      <InteractiveBackground />
      <div className="login-card-container">
        <div className="login-brand-header">
          <div className="brand-mark" style={{ width: "48px", height: "48px", fontSize: "16px", margin: "0 auto 16px" }}>
            SC
          </div>
          <p className="page-eyebrow">CONTROL TOWER SECURITY</p>
          <h1 className="login-title">Sign in</h1>
          <p className="login-subtitle">AI-Powered Supply Chain Intelligence</p>
        </div>

        <form onSubmit={handleSubmit} className="login-form">
          <div className="form-group">
            <label className="form-label">
              Username
            </label>
            <input
              className="search-input"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              placeholder="Enter username"
              autoComplete="username"
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label">
              Password
            </label>
            <input
              type="password"
              className="search-input"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Enter password"
              autoComplete="current-password"
              required
            />
          </div>

          {error && (
            <div className="error-panel" style={{ margin: 0, padding: "14px" }}>
              <div className="error-icon" style={{ width: "28px", height: "28px", fontSize: "13px" }}>!</div>
              <div className="error-content">
                <h3 style={{ fontSize: "13px" }}>Authentication failed</h3>
                <p style={{ fontSize: "11px" }}>{error}</p>
              </div>
            </div>
          )}

          <button type="submit" className="primary-button login-submit-btn" disabled={loading}>
            {loading ? "Authenticating..." : "Access Control Tower →"}
          </button>
        </form>
      </div>
    </div>
  );
}

export default LoginPage;
