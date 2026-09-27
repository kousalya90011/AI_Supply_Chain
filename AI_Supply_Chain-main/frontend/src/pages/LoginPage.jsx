import { useState } from "react";
import { getCurrentUser, loginUser } from "../api/authApi";

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
    <div style={{
      minHeight: "100vh",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      background: "#f4f6f9",
      padding: "20px",
    }}>
      <div style={{
        width: "100%",
        maxWidth: "420px",
        background: "#fff",
        border: "1px solid #e4e8ee",
        borderRadius: "12px",
        boxShadow: "0 8px 24px rgba(15, 23, 42, 0.06)",
        padding: "28px",
      }}>
        <div style={{ marginBottom: "20px" }}>
          <p className="page-eyebrow">AUTHENTICATION</p>
          <h1 style={{ margin: "0 0 8px", fontSize: "28px", color: "#172033" }}>Sign in</h1>
          <p style={{ margin: 0, color: "#64748b", fontSize: "13px" }}>Access the control tower.</p>
        </div>

        <form onSubmit={handleSubmit} style={{ display: "grid", gap: "14px" }}>
          <div>
            <label style={{ display: "block", marginBottom: "6px", fontSize: "11px", color: "#64748b", fontWeight: 700 }}>
              Username
            </label>
            <input
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              style={{
                width: "100%",
                padding: "10px 12px",
                border: "1px solid #dbe4f0",
                borderRadius: "8px",
                fontSize: "13px",
              }}
            />
          </div>

          <div>
            <label style={{ display: "block", marginBottom: "6px", fontSize: "11px", color: "#64748b", fontWeight: 700 }}>
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              style={{
                width: "100%",
                padding: "10px 12px",
                border: "1px solid #dbe4f0",
                borderRadius: "8px",
                fontSize: "13px",
              }}
            />
          </div>

          {error && (
            <div className="error-panel" style={{ margin: 0 }}>
              <div className="error-icon">!</div>
              <div className="error-content">
                <h3>Authentication failed</h3>
                <p>{error}</p>
              </div>
            </div>
          )}

          <button type="submit" className="primary-button" disabled={loading} style={{ width: "100%" }}>
            {loading ? "Signing in..." : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}

export default LoginPage;
