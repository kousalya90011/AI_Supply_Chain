import { useEffect, useMemo, useState } from "react";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts";

import { getRouteRiskData } from "../api/riskApi";

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


function RouteRisk() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [searchTerm, setSearchTerm] = useState("");
  const [riskFilter, setRiskFilter] = useState("ALL");


  /* =====================================================
     LOAD DATA
     ===================================================== */

  async function loadData() {
    try {
      setLoading(true);
      setError("");

      const result = await getRouteRiskData();

      console.log(
        "ROUTE RISK API RESPONSE:",
        result
      );

      const records = Array.isArray(result)
        ? result
        : result?.data ||
          result?.results ||
          result?.route_risk ||
          result?.routes ||
          [];

      setData(
        Array.isArray(records)
          ? records
          : []
      );

    } catch (err) {
      console.error(
        "ROUTE RISK ERROR:",
        err
      );

      setError(
        err?.response?.data?.detail ||
          "Unable to load route risk."
      );

    } finally {
      setLoading(false);
    }
  }


  useEffect(() => {
    loadData();
  }, []);


  /* =====================================================
     RISK COUNTS
     ===================================================== */

  const riskCounts = useMemo(
    () => countRiskLevels(data),
    [data]
  );


  /* =====================================================
     FILTERED DATA
     ===================================================== */

  const filteredData = useMemo(() => {

    const search =
      searchTerm
        .toLowerCase()
        .trim();

    return data.filter((item) => {

      const routeId =
        String(
          item.route_id || ""
        );

      const matchesSearch =
        !search ||
        routeId
          .toLowerCase()
          .includes(search);

      const matchesRisk =
        riskFilter === "ALL" ||
        String(
          item.risk_level || ""
        ).toUpperCase() ===
          riskFilter;

      return (
        matchesSearch &&
        matchesRisk
      );
    });

  }, [
    data,
    searchTerm,
    riskFilter,
  ]);


  /* =====================================================
     KPI CALCULATIONS
     ===================================================== */

  const totalOrders = useMemo(
    () =>
      data.reduce(
        (sum, item) =>
          sum +
          Number(
            item.total_orders || 0
          ),
        0
      ),
    [data]
  );


  const totalLateOrders = useMemo(
    () =>
      data.reduce(
        (sum, item) =>
          sum +
          Number(
            item.late_orders || 0
          ),
        0
      ),
    [data]
  );


  const overallLateRate =
    totalOrders > 0
      ? totalLateOrders /
        totalOrders
      : 0;


  const averageRiskScore =
    data.length > 0
      ? data.reduce(
          (sum, item) =>
            sum +
            Number(
              item.risk_score || 0
            ),
          0
        ) / data.length
      : 0;


  const highestRouteRisk =
    data.length > 0
      ? Math.max(
          ...data.map(
            (item) =>
              Number(
                item.risk_score || 0
              )
          )
        )
      : null;


  /* =====================================================
     RISK DISTRIBUTION CHART
     ===================================================== */

  const riskChartData = [
    {
      name: "Critical",
      value: riskCounts.critical,
      level: "critical",
    },
    {
      name: "High",
      value: riskCounts.high,
      level: "high",
    },
    {
      name: "Medium",
      value: riskCounts.medium,
      level: "medium",
    },
    {
      name: "Low",
      value: riskCounts.low,
      level: "low",
    },
  ];


  const pieColors = [
    "#dc2626",
    "#ea580c",
    "#d97706",
    "#16a34a",
  ];


  /* =====================================================
     ROUTE LATE RATE CHART
     ===================================================== */

  const routeChartData = data
    .map((item) => ({
      route: item.route_id,
      lateRate:
        Number(
          item.late_rate || 0
        ) * 100,
    }))
    .sort(
      (a, b) =>
        b.lateRate -
        a.lateRate
    )
    .slice(0, 10);


  /* =====================================================
     CLICKABLE RISK FILTER
     ===================================================== */

  function handleRiskCardClick(level) {

    if (riskFilter === level) {
      setRiskFilter("ALL");
    } else {
      setRiskFilter(level);
    }

  }


  /* =====================================================
     LOADING
     ===================================================== */

  if (loading) {
    return (
      <div className="page-container route-page">

        <Loading
          message="Loading route risk..."
        />

      </div>
    );
  }


  /* =====================================================
     ERROR
     ===================================================== */

  if (error) {
    return (
      <div className="page-container route-page">

        <ErrorMessage
          title="Route Risk Unavailable"
          message={error}
          onRetry={loadData}
        />

      </div>
    );
  }


  /* =====================================================
     PAGE
     ===================================================== */

  return (
    <div className="page-container route-page">
      <RiskTabs />

      {/* =================================================
          PAGE HEADER
          ================================================= */}

      <div className="page-heading">

        <div>

          <p className="page-eyebrow">
            NETWORK INTELLIGENCE
          </p>

          <h1>
            Route Risk
          </h1>

          <p className="page-description">
            Monitor route-level delivery
            performance, late-order exposure,
            and operational risk.
          </p>

        </div>

      </div>


      {/* =================================================
          KPI CARDS
          ================================================= */}

      <section className="route-kpi-grid">


        <div className="route-kpi-card">

          <div className="route-kpi-icon">
            ⌁
          </div>

          <div>

            <span className="route-kpi-label">
              ROUTES MONITORED
            </span>

            <strong className="route-kpi-value">
              {formatNumber(
                data.length
              )}
            </strong>

            <span className="route-kpi-subtitle">
              Active routes analyzed
            </span>

          </div>

        </div>


        <div className="route-kpi-card">

          <div className="route-kpi-icon">
            ⇢
          </div>

          <div>

            <span className="route-kpi-label">
              TOTAL ORDERS
            </span>

            <strong className="route-kpi-value">
              {formatNumber(
                totalOrders
              )}
            </strong>

            <span className="route-kpi-subtitle">
              Orders across routes
            </span>

          </div>

        </div>


        <div className="route-kpi-card">

          <div className="route-kpi-icon warning">
            △
          </div>

          <div>

            <span className="route-kpi-label">
              LATE ORDERS
            </span>

            <strong className="route-kpi-value">
              {formatNumber(
                totalLateOrders
              )}
            </strong>

            <span className="route-kpi-subtitle">
              Orders affected by delay
            </span>

          </div>

        </div>


        <div className="route-kpi-card">

          <div className="route-kpi-icon danger">
            !
          </div>

          <div>

            <span className="route-kpi-label">
              OVERALL LATE RATE
            </span>

            <strong className="route-kpi-value">
              {formatPercentage(
                overallLateRate
              )}
            </strong>

            <span className="route-kpi-subtitle">
              Across monitored routes
            </span>

          </div>

        </div>

      </section>


      {/* =================================================
          SECONDARY METRICS
          ================================================= */}

      <section className="route-secondary-grid">


        <div className="route-metric-card">

          <span>
            Average Risk Score
          </span>

          <strong>
            {formatScore(
              averageRiskScore
            )}
          </strong>

        </div>


        <div className="route-metric-card">

          <span>
            Routes With Data
          </span>

          <strong>
            {formatNumber(
              data.length
            )}
          </strong>

        </div>


        <div className="route-metric-card">

          <span>
            Highest Route Risk
          </span>

          <strong>
            {highestRouteRisk !== null
              ? formatScore(
                  highestRouteRisk
                )
              : "—"}
          </strong>

        </div>

      </section>


      {/* =================================================
          RISK DISTRIBUTION
          ================================================= */}

      <section className="route-risk-overview">


        <div className="route-risk-overview-header">

          <div>

            <p className="route-section-eyebrow">
              RISK DISTRIBUTION
            </p>

            <h2>
              Route Risk Overview
            </h2>

          </div>

          <span className="route-provider-count">
            {formatNumber(
              data.length
            )} routes
          </span>

        </div>


        <div className="route-risk-overview-grid">


          {/* CRITICAL */}

          <button
            type="button"
            className={`route-risk-summary-card ${
              riskFilter === "CRITICAL"
                ? "selected"
                : ""
            }`}
            onClick={() =>
              handleRiskCardClick(
                "CRITICAL"
              )
            }
          >

            <div className="route-risk-summary-header">

              <div>

                <span className="route-risk-summary-label">
                  CRITICAL
                </span>

                <h3>
                  Critical Risk
                </h3>

              </div>

              <div className="route-risk-summary-icon critical">
                !
              </div>

            </div>

            <div className="route-risk-number">
              {riskCounts.critical}
              <span>
                {" "}routes
              </span>
            </div>

          </button>


          {/* HIGH */}

          <button
            type="button"
            className={`route-risk-summary-card ${
              riskFilter === "HIGH"
                ? "selected"
                : ""
            }`}
            onClick={() =>
              handleRiskCardClick(
                "HIGH"
              )
            }
          >

            <div className="route-risk-summary-header">

              <div>

                <span className="route-risk-summary-label">
                  HIGH
                </span>

                <h3>
                  High Risk
                </h3>

              </div>

              <div className="route-risk-summary-icon high">
                ▲
              </div>

            </div>

            <div className="route-risk-number">
              {riskCounts.high}
              <span>
                {" "}routes
              </span>
            </div>

          </button>


          {/* MEDIUM */}

          <button
            type="button"
            className={`route-risk-summary-card ${
              riskFilter === "MEDIUM"
                ? "selected"
                : ""
            }`}
            onClick={() =>
              handleRiskCardClick(
                "MEDIUM"
              )
            }
          >

            <div className="route-risk-summary-header">

              <div>

                <span className="route-risk-summary-label">
                  MEDIUM
                </span>

                <h3>
                  Medium Risk
                </h3>

              </div>

              <div className="route-risk-summary-icon medium">
                ◐
              </div>

            </div>

            <div className="route-risk-number">
              {riskCounts.medium}
              <span>
                {" "}routes
              </span>
            </div>

          </button>


          {/* LOW */}

          <button
            type="button"
            className={`route-risk-summary-card ${
              riskFilter === "LOW"
                ? "selected"
                : ""
            }`}
            onClick={() =>
              handleRiskCardClick(
                "LOW"
              )
            }
          >

            <div className="route-risk-summary-header">

              <div>

                <span className="route-risk-summary-label">
                  LOW
                </span>

                <h3>
                  Low Risk
                </h3>

              </div>

              <div className="route-risk-summary-icon low">
                ✓
              </div>

            </div>

            <div className="route-risk-number">
              {riskCounts.low}
              <span>
                {" "}routes
              </span>
            </div>

          </button>

        </div>

      </section>


      {/* =================================================
          ROUTE TABLE
          ================================================= */}

      <section className="route-table-card">


        <div className="route-table-header">

          <div>

            <p className="route-section-eyebrow">
              ROUTE RISK REGISTER
            </p>

            <h2>
              Route Risk
            </h2>

            <p>
              Search and filter routes by
              operational risk.
            </p>

          </div>

          <div className="route-table-count">
            {formatNumber(
              filteredData.length
            )} shown
          </div>

        </div>


        {/* FILTER BAR */}

        <div className="route-filter-bar">


          <input
            className="route-search-input"
            type="text"
            placeholder="Search route..."
            value={searchTerm}
            onChange={(event) =>
              setSearchTerm(
                event.target.value
              )
            }
          />


          <select
            className="route-filter-select"
            value={riskFilter}
            onChange={(event) =>
              setRiskFilter(
                event.target.value
              )
            }
          >

            <option value="ALL">
              All Risk Levels
            </option>

            <option value="CRITICAL">
              Critical
            </option>

            <option value="HIGH">
              High
            </option>

            <option value="MEDIUM">
              Medium
            </option>

            <option value="LOW">
              Low
            </option>

          </select>


          {(searchTerm ||
            riskFilter !== "ALL") && (

            <button
              className="route-clear-button"
              onClick={() => {
                setSearchTerm("");
                setRiskFilter("ALL");
              }}
            >
              Clear Filters
            </button>

          )}

        </div>


        {/* TABLE */}

        {!filteredData.length ? (

          <div className="route-empty-wrapper">

            <EmptyState
              title="No routes found"
              message="Try changing the search or risk filter."
            />

          </div>

        ) : (

          <div className="route-table-wrapper">

            <table className="route-table">

              <thead>

                <tr>

                  <th>
                    Route
                  </th>

                  <th>
                    Total Orders
                  </th>

                  <th>
                    Late Orders
                  </th>

                  <th>
                    Late Rate
                  </th>

                  <th>
                    Risk Score
                  </th>

                  <th>
                    Risk Level
                  </th>

                  <th>
                    Risk Reason
                  </th>

                </tr>

              </thead>


              <tbody>

                {filteredData.map(
                  (item, index) => (

                    <tr
                      key={`${item.route_id}-${index}`}
                    >

                      <td>

                        <div className="route-cell">

                          <div className="route-avatar">
                            {String(
                              item.route_id || "RT"
                            )
                              .slice(0, 2)
                              .toUpperCase()}
                          </div>

                          <strong>
                            {item.route_id || "—"}
                          </strong>

                        </div>

                      </td>


                      <td>
                        {formatNumber(
                          item.total_orders
                        )}
                      </td>


                      <td>
                        {formatNumber(
                          item.late_orders
                        )}
                      </td>


                      <td>
                        {formatPercentage(
                          item.late_rate
                        )}
                      </td>


                      <td>

                        <span className="route-score">
                          {formatScore(
                            item.risk_score
                          )}
                        </span>

                      </td>


                      <td>

                        <RiskBadge
                          level={
                            item.risk_level
                          }
                        />

                      </td>


                      <td>

                        <span className="route-reason">

                          {item.risk_reason ||
                            "Route risk calculated from monitored delivery performance metrics."}

                        </span>

                      </td>

                    </tr>

                  )
                )}

              </tbody>

            </table>

          </div>

        )}

      </section>


      {/* =================================================
          CHARTS
          ================================================= */}

      <section className="route-charts-grid">


        {/* RISK DISTRIBUTION CHART */}

        <div className="route-chart-card">

          <div className="route-chart-header">

            <p className="route-section-eyebrow">
              RISK DISTRIBUTION
            </p>

            <h2>
              Route Risk Levels
            </h2>

          </div>


          <div className="route-pie-container">

            <ResponsiveContainer
              width="100%"
              height={300}
            >

              <PieChart>

                <Pie
                  data={riskChartData}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  innerRadius={65}
                  outerRadius={105}
                  paddingAngle={3}
                >

                  {riskChartData.map(
                    (entry, index) => (

                      <Cell
                        key={`route-risk-${index}`}
                        fill={
                          pieColors[index]
                        }
                      />

                    )
                  )}

                </Pie>

                <Tooltip />

              </PieChart>

            </ResponsiveContainer>

          </div>


          <div className="route-chart-legend">

            {riskChartData.map(
              (item) => (

                <div
                  key={item.level}
                  className="route-legend-item"
                >

                  <span
                    className={`route-legend-dot ${item.level}`}
                  ></span>

                  <span>
                    {item.name}
                  </span>

                  <strong>
                    {item.value}
                  </strong>

                </div>

              )
            )}

          </div>

        </div>


        {/* LATE RATE CHART */}

        <div className="route-chart-card">

          <div className="route-chart-header">

            <p className="route-section-eyebrow">
              DELAY ANALYSIS
            </p>

            <h2>
              Late Rate by Route
            </h2>

          </div>


          {routeChartData.length ? (

            <ResponsiveContainer
              width="100%"
              height={360}
            >

              <BarChart
                data={routeChartData}
                layout="vertical"
                margin={{
                  top: 10,
                  right: 25,
                  left: 20,
                  bottom: 10,
                }}
              >

                <CartesianGrid
                  strokeDasharray="3 3"
                  horizontal={false}
                />

                <XAxis
                  type="number"
                  tickFormatter={(value) =>
                    `${value}%`
                  }
                />

                <YAxis
                  type="category"
                  dataKey="route"
                  width={80}
                />

                <Tooltip
                  formatter={(value) => [
                    `${Number(
                      value
                    ).toFixed(2)}%`,
                    "Late Rate",
                  ]}
                />

                <Bar
                  dataKey="lateRate"
                  fill="#2563eb"
                  radius={[
                    0,
                    6,
                    6,
                    0,
                  ]}
                />

              </BarChart>

            </ResponsiveContainer>

          ) : (

            <EmptyState
              title="No route data"
              message="No route performance data is available."
            />

          )}

        </div>

      </section>


      {/* =================================================
          INFORMATION CARD
          ================================================= */}

      <section className="route-info-card">

        <div className="route-info-icon">
          i
        </div>

        <div>

          <h3>
            Route Risk Interpretation
          </h3>

          <p>
            Route risk is calculated by the
            backend analytics using route-level
            delivery performance indicators such
            as late-order rate and risk score.
            The frontend displays the calculated
            values without changing the underlying
            risk logic.
          </p>

        </div>

      </section>

    </div>
  );
}

export default RouteRisk;