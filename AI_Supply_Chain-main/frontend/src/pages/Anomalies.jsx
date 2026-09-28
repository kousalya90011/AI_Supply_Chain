import { useEffect, useState } from "react";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

import { getAnomaliesData } from "../api/riskApi";

import Loading from "../components/Loading";
import ErrorMessage from "../components/ErrorMessage";
import EmptyState from "../components/EmptyState";

import { formatNumber } from "../utils/formatters";

function Anomalies() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadData() {
    try {
      setLoading(true);
      setError("");

      const result = await getAnomaliesData();

      console.log("ANOMALIES API RESPONSE:", result);

      setData(result);
    } catch (err) {
      console.error("ANOMALIES ERROR:", err);

      setError(
        err?.response?.data?.detail ||
          "Unable to load anomaly data."
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  if (loading) {
    return (
      <div className="page-container anomalies-page">
        <Loading message="Loading anomaly analysis..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-container anomalies-page">
        <ErrorMessage
          title="Anomaly Analysis Unavailable"
          message={error}
          onRetry={loadData}
        />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="page-container anomalies-page">
        <EmptyState
          title="No anomaly data"
          message="No anomaly analysis is currently available."
        />
      </div>
    );
  }

  const totalRecords = Number(data.total_records || 0);
  const anomalyCount = Number(data.anomaly_count || 0);
  const anomalyRate = Number(data.anomaly_rate || 0);
  const column = data.column || "delay_days";

  const normalCount = Math.max(
    totalRecords - anomalyCount,
    0
  );

  const chartData = [
    {
      name: "Normal Records",
      value: normalCount,
    },
    {
      name: "Anomalies",
      value: anomalyCount,
    },
  ];

  return (
    <div className="page-container anomalies-page">

      {/* PAGE HEADER */}
      <div className="page-heading">
        <p className="page-eyebrow">
          OPERATIONAL MONITORING
        </p>

        <h1>Anomalies</h1>

        <p className="page-description">
          Monitor unusual order-delay patterns and
          statistical anomalies across the supply chain.
        </p>
      </div>

      {/* KPI CARDS */}
      <section className="anomaly-kpi-grid">

        <div className="anomaly-kpi-card">
          <span>TOTAL RECORDS</span>

          <strong>
            {formatNumber(totalRecords)}
          </strong>

          <small>
            Analyzed {column}
          </small>
        </div>

        <div className="anomaly-kpi-card">
          <span>NORMAL RECORDS</span>

          <strong>
            {formatNumber(normalCount)}
          </strong>

          <small>
            Within statistical range
          </small>
        </div>

        <div className="anomaly-kpi-card danger">
          <span>STATISTICAL ANOMALIES</span>

          <strong>
            {formatNumber(anomalyCount)}
          </strong>

          <small>
            Detected records
          </small>
        </div>

        <div className="anomaly-kpi-card">
          <span>ANOMALY RATE</span>

          <strong>
            {anomalyRate.toFixed(2)}%
          </strong>

          <small>
            Of total records
          </small>
        </div>

      </section>

      {/* CHART + ANALYSIS */}
      <section className="anomaly-grid">

        <div className="anomaly-card">

          <p className="anomaly-eyebrow">
            RECORD DISTRIBUTION
          </p>

          <h2>
            Normal vs Anomalous Records
          </h2>

          <ResponsiveContainer
            width="100%"
            height={320}
          >
            <BarChart data={chartData}>

              <CartesianGrid
                strokeDasharray="3 3"
              />

              <XAxis
                dataKey="name"
              />

              <YAxis />

              <Tooltip />

              <Bar
                dataKey="value"
                fill="#D4AF37"
                radius={[6, 6, 0, 0]}
              />

            </BarChart>
          </ResponsiveContainer>

        </div>

        <div className="anomaly-card">

          <p className="anomaly-eyebrow">
            DETECTION SUMMARY
          </p>

          <h2>
            Statistical Analysis
          </h2>

          <div className="anomaly-stat-list">

            <div>
              <span>Analyzed Column</span>

              <strong>
                {column}
              </strong>
            </div>

            <div>
              <span>Total Records</span>

              <strong>
                {formatNumber(totalRecords)}
              </strong>
            </div>

            <div>
              <span>Normal Records</span>

              <strong>
                {formatNumber(normalCount)}
              </strong>
            </div>

            <div>
              <span>Anomaly Count</span>

              <strong>
                {formatNumber(anomalyCount)}
              </strong>
            </div>

            <div>
              <span>Anomaly Rate</span>

              <strong>
                {anomalyRate.toFixed(2)}%
              </strong>
            </div>

          </div>

        </div>

      </section>

      {/* INFO */}
      <section className="anomaly-info-card">

        <div className="anomaly-info-icon">
          i
        </div>

        <div>

          <h3>
            Anomaly Interpretation
          </h3>

          <p>
            The backend analyzes the
            <strong> {column}</strong> column and
            identifies statistically unusual records.
            Out of {formatNumber(totalRecords)} records,
            {` `}
            {formatNumber(anomalyCount)} were identified
            as anomalies, representing{" "}
            {anomalyRate.toFixed(2)}% of the dataset.
          </p>

        </div>

      </section>

    </div>
  );
}

export default Anomalies;
