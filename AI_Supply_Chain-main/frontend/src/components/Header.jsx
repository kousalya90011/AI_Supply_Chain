import { useEffect, useState } from "react";

import { getBackendHealth } from "../api/dashboardApi";


function Header({ auth, onLogout }) {

  const [systemStatus, setSystemStatus] =
    useState("checking");

  const [llmStatus, setLlmStatus] =
    useState("checking");


  useEffect(() => {

    let mounted = true;

    async function checkSystemHealth() {

      try {

        const result =
          await getBackendHealth();

        if (!mounted) {
          return;
        }

        setSystemStatus(
          result?.status === "healthy"
            ? "connected"
            : "offline"
        );

        const backendLlmStatus =
          result?.llm_status;

        if (
          backendLlmStatus === "configured" ||
          backendLlmStatus === "connected"
        ) {
          setLlmStatus("configured");
        } else if (
          backendLlmStatus === "error"
        ) {
          setLlmStatus("error");
        } else {
          setLlmStatus("not_configured");
        }

      } catch (error) {

        console.error(
          "SYSTEM HEALTH CHECK ERROR:",
          error
        );

        if (!mounted) {
          return;
        }

        setSystemStatus("offline");
        setLlmStatus("unknown");
      }
    }

    checkSystemHealth();

    const interval = setInterval(
      checkSystemHealth,
      30000
    );

    return () => {

      mounted = false;

      clearInterval(interval);
    };

  }, []);


  const systemStatusText =
    systemStatus === "connected"
      ? "Control Tower Online"
      : systemStatus === "offline"
        ? "Backend Offline"
        : "Checking System";


  const llmStatusText =
    llmStatus === "configured"
      ? "LLM Configured"
      : llmStatus === "error"
        ? "LLM Error"
        : llmStatus === "not_configured"
          ? "LLM Not Configured"
          : llmStatus === "unknown"
            ? "LLM Unavailable"
            : "Checking LLM";


  const displayName =
    auth?.name ||
    auth?.username ||
    "Operations";


  const roleLabel =
    auth?.role ||
    "USER";


  return (
    <header className="top-header">

      {/* =================================================
          LEFT
          ================================================= */}

      <div className="header-left">

        <p className="header-eyebrow">
          SUPPLY CHAIN CONTROL TOWER
        </p>

        <h2>
          Risk Intelligence Platform
        </h2>

      </div>


      {/* =================================================
          RIGHT
          ================================================= */}

      <div className="header-right">

        {/* SYSTEM STATUS */}

        <div
          className={`header-status ${systemStatus}`}
        >
          <span className="status-dot"></span>

          <span>
            {systemStatusText}
          </span>
        </div>


        {/* LLM STATUS */}

        <div
          className={`header-status llm-${llmStatus}`}
        >
          <span className="status-dot"></span>

          <span>
            {llmStatusText}
          </span>
        </div>


        <div className="header-divider"></div>


        {/* PROFILE */}

        <div className="header-profile">

          <div className="profile-avatar">
            {displayName
              .slice(0, 2)
              .toUpperCase()}
          </div>

          <div>

            <strong>
              {displayName}
            </strong>

            <span>
              {roleLabel}
            </span>

          </div>

        </div>


        {/* LOGOUT */}

        {onLogout && (

          <button
            className="secondary-button"
            onClick={onLogout}
            style={{
              marginLeft: "12px",
            }}
          >
            Logout
          </button>

        )}

      </div>

    </header>
  );
}


export default Header;
