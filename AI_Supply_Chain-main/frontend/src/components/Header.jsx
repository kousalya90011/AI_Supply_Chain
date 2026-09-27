import { useEffect, useState } from "react";
import { getBackendHealth } from "../api/dashboardApi";

function Header() {
  const [backendStatus, setBackendStatus] = useState("checking");

  useEffect(() => {
    async function checkBackend() {
      try {
        await getBackendHealth();
        setBackendStatus("connected");
      } catch {
        setBackendStatus("offline");
      }
    }

    checkBackend();
  }, []);

  const statusText =
    backendStatus === "connected"
      ? "Backend Connected"
      : backendStatus === "offline"
        ? "Backend Offline"
        : "Checking Backend";

  return (
    <header className="top-header">
      <div className="header-left">
        <p className="header-eyebrow">SUPPLY CHAIN CONTROL TOWER</p>
        <h2>Risk Intelligence Platform</h2>
      </div>

      <div className="header-right">
        <div className={`header-status ${backendStatus}`}>
          <span className="status-dot"></span>
          <span>{statusText}</span>
        </div>

        <div className="header-divider"></div>

        <div className="header-profile">
          <div className="profile-avatar">SC</div>

          <div>
            <strong>Operations</strong>
            <span>Control Center</span>
          </div>
        </div>
      </div>
    </header>
  );
}

export default Header;