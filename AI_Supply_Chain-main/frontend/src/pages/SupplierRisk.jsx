import { useEffect, useMemo, useState } from "react";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

import { getSupplierRiskData } from "../api/riskApi";

import RiskBadge from "../components/RiskBadge";
import RiskTabs from "../components/RiskTabs";
import Loading from "../components/Loading";
import ErrorMessage from "../components/ErrorMessage";
import EmptyState from "../components/EmptyState";

import {
  formatNumber,
  formatPercentage,
  formatScore,
} from "../utils/formatters";

import { countRiskLevels } from "../utils/riskUtils";

function SupplierRisk() {
  const [supplierRisk, setSupplierRisk] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [riskFilter, setRiskFilter] = useState("ALL");

  async function loadSupplierRisk() {
    try {
      setLoading(true);
      setError("");

      const data = await getSupplierRiskData();

      setSupplierRisk(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error("Supplier risk API error:", err);

      setError(
        err?.response?.data?.detail ||
          "Unable to load supplier risk data."
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadSupplierRisk();
  }, []);

  const riskCounts = useMemo(
    () => countRiskLevels(supplierRisk),
    [supplierRisk]
  );

  const filteredSuppliers = useMemo(() => {
    const normalizedSearch = searchTerm.toLowerCase().trim();

    return supplierRisk.filter((supplier) => {
      const matchesSearch =
        !normalizedSearch ||
        String(supplier.supplier_id || "")
          .toLowerCase()
          .includes(normalizedSearch);

      const matchesRisk =
        riskFilter === "ALL" ||
        supplier.risk_level === riskFilter;

      return matchesSearch && matchesRisk;
    });
  }, [supplierRisk, searchTerm, riskFilter]);

  const chartData = useMemo(() => {
    return [...supplierRisk]
      .sort(
        (a, b) =>
          Number(b.risk_score || 0) -
          Number(a.risk_score || 0)
      )
      .slice(0, 10)
      .map((supplier) => ({
        supplier: supplier.supplier_id,
        score: Number(
          Number(supplier.risk_score || 0).toFixed(2)
        ),
      }));
  }, [supplierRisk]);

  const totalOrders = useMemo(() => {
    return supplierRisk.reduce(
      (sum, supplier) =>
        sum + Number(supplier.total_orders || 0),
      0
    );
  }, [supplierRisk]);

  const totalLateOrders = useMemo(() => {
    return supplierRisk.reduce(
      (sum, supplier) =>
        sum + Number(supplier.late_orders || 0),
      0
    );
  }, [supplierRisk]);

  const overallLateRate =
    totalOrders > 0
      ? totalLateOrders / totalOrders
      : 0;

  if (loading) {
    return <Loading message="Loading supplier risk intelligence..." />;
  }

  if (error) {
    return (
      <ErrorMessage
        title="Supplier risk unavailable"
        message={error}
        onRetry={loadSupplierRisk}
      />
    );
  }

  if (!supplierRisk.length) {
    return (
      <EmptyState
        title="No supplier risk data"
        message="The backend did not return any supplier risk records."
      />
    );
  }

  return (
    <div className="page-container">
      <RiskTabs />

      {/* PAGE HEADER */}
      <section className="page-heading">
        <div>
          <p className="page-eyebrow">
            SUPPLIER INTELLIGENCE
          </p>

          <h1>Supplier Risk</h1>

          <p className="page-description">
            Monitor supplier reliability, delivery exposure,
            operational performance, and risk levels.
          </p>
        </div>

        <div className="page-actions">
          <button
            className="secondary-button"
            onClick={loadSupplierRisk}
          >
            ↻ Refresh
          </button>
        </div>
      </section>

      {/* SUMMARY CARDS */}
      <section className="supplier-summary-grid">

        <div className="supplier-stat-card">
          <div className="supplier-stat-top">
            <span className="stat-label">
              TOTAL SUPPLIERS
            </span>

            <span className="stat-icon">◉</span>
          </div>

          <strong className="supplier-stat-value">
            {formatNumber(supplierRisk.length)}
          </strong>

          <span className="stat-subtext">
            Suppliers evaluated
          </span>
        </div>

        <div className="supplier-stat-card critical-card">
          <div className="supplier-stat-top">
            <span className="stat-label">
              CRITICAL RISK
            </span>

            <span className="stat-icon">!</span>
          </div>

          <strong className="supplier-stat-value">
            {formatNumber(riskCounts.critical)}
          </strong>

          <span className="stat-subtext">
            Critical suppliers
          </span>
        </div>

        <div className="supplier-stat-card high-card">
          <div className="supplier-stat-top">
            <span className="stat-label">
              HIGH RISK
            </span>

            <span className="stat-icon">▲</span>
          </div>

          <strong className="supplier-stat-value">
            {formatNumber(riskCounts.high)}
          </strong>

          <span className="stat-subtext">
            High-risk suppliers
          </span>
        </div>

        <div className="supplier-stat-card">
          <div className="supplier-stat-top">
            <span className="stat-label">
              OVERALL LATE RATE
            </span>

            <span className="stat-icon">⇢</span>
          </div>

          <strong className="supplier-stat-value">
            {formatPercentage(overallLateRate)}
          </strong>

          <span className="stat-subtext">
            Across supplier orders
          </span>
        </div>

      </section>

      {/* RISK DISTRIBUTION */}
      <section className="supplier-risk-distribution">

        <div className="distribution-card">

          <div className="section-header">
            <div>
              <span className="section-eyebrow">
                RISK DISTRIBUTION
              </span>

              <h2>Supplier Risk Profile</h2>
            </div>

            <span className="section-meta">
              {supplierRisk.length} suppliers
            </span>
          </div>

          <div className="risk-distribution-grid">

            <div className="risk-distribution-item">
              <span className="distribution-dot critical"></span>

              <div>
                <strong>{riskCounts.critical}</strong>
                <span>Critical</span>
              </div>
            </div>

            <div className="risk-distribution-item">
              <span className="distribution-dot high"></span>

              <div>
                <strong>{riskCounts.high}</strong>
                <span>High</span>
              </div>
            </div>

            <div className="risk-distribution-item">
              <span className="distribution-dot medium"></span>

              <div>
                <strong>{riskCounts.medium}</strong>
                <span>Medium</span>
              </div>
            </div>

            <div className="risk-distribution-item">
              <span className="distribution-dot low"></span>

              <div>
                <strong>{riskCounts.low}</strong>
                <span>Low</span>
              </div>
            </div>

          </div>

        </div>

        <div className="distribution-card">

          <div className="section-header">
            <div>
              <span className="section-eyebrow">
                TOP RISK EXPOSURE
              </span>

              <h2>Highest Risk Scores</h2>
            </div>
          </div>

          <div className="supplier-risk-chart">
            <ResponsiveContainer width="100%" height={230}>
              <BarChart
                data={chartData}
                layout="vertical"
                margin={{
                  top: 5,
                  right: 15,
                  left: 5,
                  bottom: 5,
                }}
              >
                <CartesianGrid
                  strokeDasharray="3 3"
                  horizontal={false}
                />

                <XAxis
                  type="number"
                  domain={[0, 100]}
                  tick={{ fontSize: 10 }}
                />

                <YAxis
                  type="category"
                  dataKey="supplier"
                  width={65}
                  tick={{ fontSize: 10 }}
                />

                <Tooltip
                  formatter={(value) => [
                    `${value}`,
                    "Risk Score",
                  ]}
                />

                <Bar
                  dataKey="score"
                  fill="#334155"
                  radius={[0, 4, 4, 0]}
                  barSize={16}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>

        </div>

      </section>

      {/* TABLE */}
      <section className="section-block supplier-table-section">

        <div className="section-header">

          <div>
            <span className="section-eyebrow">
              SUPPLIER MONITORING
            </span>

            <h2>Supplier Risk Register</h2>

            <p>
              Risk scores are calculated by the backend
              supplier risk analytics service.
            </p>
          </div>

          <div className="table-controls">

            <input
              type="text"
              placeholder="Search supplier..."
              value={searchTerm}
              onChange={(event) =>
                setSearchTerm(event.target.value)
              }
              className="search-input"
            />

            <select
              value={riskFilter}
              onChange={(event) =>
                setRiskFilter(event.target.value)
              }
              className="risk-filter"
            >
              <option value="ALL">All Risk Levels</option>
              <option value="CRITICAL">Critical</option>
              <option value="HIGH">High</option>
              <option value="MEDIUM">Medium</option>
              <option value="LOW">Low</option>
            </select>

          </div>

        </div>

        {filteredSuppliers.length === 0 ? (
          <EmptyState
            title="No matching suppliers"
            message="Try changing the search text or risk filter."
          />
        ) : (
          <div className="data-table-wrapper">

            <table className="risk-table supplier-table">

              <thead>
                <tr>
                  <th>SUPPLIER</th>
                  <th>RISK</th>
                  <th>RISK SCORE</th>
                  <th>ORDERS</th>
                  <th>LATE ORDERS</th>
                  <th>LATE RATE</th>
                  <th>VOLUME EXPOSURE</th>
                  <th>RISK REASON</th>
                </tr>
              </thead>

              <tbody>
                {filteredSuppliers.map((supplier) => (
                  <tr key={supplier.supplier_id}>

                    <td>
                      <div className="supplier-name-cell">
                        <span className="supplier-avatar">
                        S
                        </span>

                        <div>
                          <strong>
                            {supplier.supplier_id}
                          </strong>

                          <span>
                            Supplier
                          </span>
                        </div>
                      </div>
                    </td>

                    <td>
                      <RiskBadge
                        level={supplier.risk_level}
                      />
                    </td>

                    <td>
                      <div className="score-cell">
                        <strong>
                          {formatScore(
                            supplier.risk_score
                          )}
                        </strong>

                        <div className="score-bar">
                          <span
                            style={{
                              width: `${Math.min(
                                Number(
                                  supplier.risk_score || 0
                                ),
                                100
                              )}%`,
                            }}
                          ></span>
                        </div>
                      </div>
                    </td>

                    <td>
                      {formatNumber(
                        supplier.total_orders
                      )}
                    </td>

                    <td>
                      {formatNumber(
                        supplier.late_orders
                      )}
                    </td>

                    <td>
                      {formatPercentage(
                        supplier.late_rate
                      )}
                    </td>

                    <td>
                      {formatNumber(
                        supplier.volume_exposure
                      )}
                    </td>

                    <td>
                      <span className="reason-text">
                        {supplier.risk_reason ||
                          "No risk reason available"}
                      </span>
                    </td>

                  </tr>
                ))}
              </tbody>

            </table>

          </div>
        )}

      </section>

    </div>
  );
}

export default SupplierRisk;
