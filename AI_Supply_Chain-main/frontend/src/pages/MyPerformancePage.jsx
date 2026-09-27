import { useMemo } from "react";

function MyPerformancePage({ auth }) {
  const supplierId = auth?.supplier_id || "SUP-1001";

  const metrics = useMemo(
    () => [
      { label: "On-time delivery", value: "96.4%", delta: "+2.1%" },
      { label: "Fill rate", value: "94.2%", delta: "+1.6%" },
      { label: "Avg. lead time", value: "7.3d", delta: "-1.1d" },
      { label: "Open issues", value: "3", delta: "-2" },
    ],
    []
  );

  return (
    <div className="page-container">
      <section className="page-heading">
        <div>
          <p className="page-eyebrow">PERFORMANCE</p>
          <h1>Supplier Performance</h1>
        </div>
      </section>

      <section className="dashboard-grid" style={{ marginBottom: "20px" }}>
        {metrics.map((metric) => (
          <article key={metric.label} className="stat-card">
            <div className="stat-card-header">
              <span className="stat-card-label">{metric.label}</span>
              <span className="stat-card-delta positive">{metric.delta}</span>
            </div>
            <div className="stat-card-value">{metric.value}</div>
          </article>
        ))}
      </section>

      <section className="investigation-card">
        <div className="section-header">
          <div>
            <span className="section-eyebrow">SUPPLIER ID</span>
            <h2>{supplierId}</h2>
          </div>
        </div>

        <div className="risk-summary-grid">
          <div className="summary-panel">
            <span className="summary-label">Current status</span>
            <strong>High reliability</strong>
            <p>Strong fulfillment performance with no critical delivery exceptions this week.</p>
          </div>
          <div className="summary-panel">
            <span className="summary-label">Focus area</span>
            <strong>Inventory planning</strong>
            <p>Maintain buffer coverage for seasonal demand spikes in the next 14 days.</p>
          </div>
        </div>
      </section>
    </div>
  );
}

export default MyPerformancePage;
