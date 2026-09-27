import { useEffect, useState } from "react";

import { getDataStatus, getDataColumns } from "../api/dataApi";

import Loading from "../components/Loading";
import ErrorMessage from "../components/ErrorMessage";

function DataStatus() {
  const [status, setStatus] = useState(null);
  const [columns, setColumns] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        setError("");

        const [statusResult, columnsResult] = await Promise.all([
          getDataStatus(),
          getDataColumns(),
        ]);

        setStatus(statusResult);
        setColumns(columnsResult);
      } catch (err) {
        setError(
          err?.response?.data?.detail ||
            "Unable to load dataset status."
        );
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, []);

  if (loading) {
    return <Loading message="Loading dataset status..." />;
  }

  if (error) {
    return (
      <ErrorMessage
        title="Dataset status unavailable"
        message={error}
      />
    );
  }

  return (
    <div className="page-container">
      <div className="page-heading">
        <p className="page-eyebrow">DATA LAYER</p>
        <h1>Dataset status</h1>
        <p className="page-description">
          Monitoring the loaded operational datasets and their schema coverage.
        </p>
      </div>

      {status && (
        <section className="ai-query-card" style={{ marginBottom: "1.5rem" }}>
          <div className="ai-response-header">
            <div>
              <p className="ai-eyebrow">SYSTEM HEALTH</p>
              <h2>Backend validation</h2>
            </div>
            <div className="ai-response-status">
              {status.status === "success" ? "VALID" : "CHECK"}
            </div>
          </div>

          <div className="ai-assessment-grid">
            {Object.entries(status.datasets || {}).map(([name, meta]) => (
              <div key={name} className="ai-assessment-item">
                <span>{name}</span>
                <strong>{meta.rows}</strong>
                <small>{meta.columns} columns</small>
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="ai-query-card">
        <div className="ai-response-header">
          <div>
            <p className="ai-eyebrow">SCHEMA</p>
            <h2>Dataset columns</h2>
          </div>
        </div>

        <div className="ai-evidence-list">
          {Object.entries(columns).map(([name, columnList]) => (
            <div key={name} className="ai-evidence-card" style={{ marginBottom: "1rem" }}>
              <div className="ai-evidence-top">
                <div>
                  <span className="ai-evidence-number">{name}</span>
                  <strong>{columnList.length} fields</strong>
                </div>
              </div>

              <div className="ai-evidence-metrics">
                {columnList.slice(0, 10).map((column) => (
                  <div key={`${name}-${column}`}>
                    <span>Field</span>
                    <strong>{column}</strong>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

export default DataStatus;
