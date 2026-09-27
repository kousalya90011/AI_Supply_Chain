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

import { getDeliveryRiskData } from "../api/riskApi";

import RiskBadge from "../components/RiskBadge";
import Loading from "../components/Loading";
import ErrorMessage from "../components/ErrorMessage";
import EmptyState from "../components/EmptyState";

import {
  formatDecimal,
  formatNumber,
  formatPercentage,
  formatScore,
} from "../utils/formatters";

import { countRiskLevels } from "../utils/riskUtils";


function getProviderName(item, index) {
  return (
    item.provider ||
    item["3pl"] ||
    item["3PL"] ||
    item.provider_name ||
    item.provider_id ||
    item.name ||
    `Provider ${index + 1}`
  );
}


function DeliveryRisk() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [searchTerm, setSearchTerm] = useState("");
  const [riskFilter, setRiskFilter] = useState("ALL");


  async function loadData() {
    try {
      setLoading(true);
      setError("");

      const result = await getDeliveryRiskData();

      console.log(
        "DELIVERY RISK API RESPONSE:",
        result
      );

      const records = Array.isArray(result)
        ? result
        : result?.data ||
          result?.results ||
          result?.delivery_risk ||
          result?.providers ||
          [];

      setData(
        Array.isArray(records)
          ? records
          : []
      );

    } catch (err) {
      console.error(
        "DELIVERY RISK ERROR:",
        err
      );

      setError(
        err?.response?.data?.detail ||
          "Unable to load delivery risk."
      );

    } finally {
      setLoading(false);
    }
  }


  useEffect(() => {
    loadData();
  }, []);


  const riskCounts = useMemo(
    () => countRiskLevels(data),
    [data]
  );


  const filteredData = useMemo(() => {
    const search =
      searchTerm
        .toLowerCase()
        .trim();

    return data.filter(
      (item, index) => {

        const provider =
          getProviderName(
            item,
            index
          );

        const matchesSearch =
          !search ||
          String(provider)
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
      }
    );
  }, [
    data,
    searchTerm,
    riskFilter,
  ]);


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


  const averageDelay =
    data.length > 0
      ? data.reduce(
          (sum, item) =>
            sum +
            Number(
              item.average_delay || 0
            ),
          0
        ) / data.length
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


  const delayChartData =
    data
      .map((item, index) => ({
        name: getProviderName(
          item,
          index
        ),
        delay: Number(
          item.average_delay || 0
        ),
      }))
      .sort(
        (a, b) =>
          b.delay - a.delay
      )
      .slice(0, 10);


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


  if (loading) {
    return (
      <div className="page-container delivery-page">
        <Loading message="Loading delivery risk..." />
      </div>
    );
  }


  if (error) {
    return (
      <div className="page-container delivery-page">
        <ErrorMessage
          title="Delivery Risk Unavailable"
          message={error}
          onRetry={loadData}
        />
      </div>
    );
  }


  return (
    <div className="page-container delivery-page">

      {/* =================================================
          PAGE HEADER
          ================================================= */}

      <div className="page-heading">

        <div>

          <p className="page-eyebrow">
            LOGISTICS INTELLIGENCE
          </p>

          <h1>
            Delivery Risk
          </h1>

          <p className="page-description">
            Monitor delivery performance,
            delays, late-order exposure,
            and provider-level risk.
          </p>

        </div>

      </div>


      {/* =================================================
          KPI CARDS
          ================================================= */}

      <section className="delivery-kpi-grid">

        <div className="delivery-kpi-card">

          <div className="delivery-kpi-icon">
            ◉
          </div>

          <div>

            <span className="delivery-kpi-label">
              3PL PROVIDERS
            </span>

            <strong className="delivery-kpi-value">
              {formatNumber(
                data.length
              )}
            </strong>

            <span className="delivery-kpi-subtitle">
              Providers monitored
            </span>

          </div>

        </div>


        <div className="delivery-kpi-card">

          <div className="delivery-kpi-icon">
            ⇢
          </div>

          <div>

            <span className="delivery-kpi-label">
              TOTAL ORDERS
            </span>

            <strong className="delivery-kpi-value">
              {formatNumber(
                totalOrders
              )}
            </strong>

            <span className="delivery-kpi-subtitle">
              Orders handled
            </span>

          </div>

        </div>


        <div className="delivery-kpi-card">

          <div className="delivery-kpi-icon warning">
            △
          </div>

          <div>

            <span className="delivery-kpi-label">
              LATE ORDERS
            </span>

            <strong className="delivery-kpi-value">
              {formatNumber(
                totalLateOrders
              )}
            </strong>

            <span className="delivery-kpi-subtitle">
              Orders delivered late
            </span>

          </div>

        </div>


        <div className="delivery-kpi-card">

          <div className="delivery-kpi-icon danger">
            !
          </div>

          <div>

            <span className="delivery-kpi-label">
              OVERALL LATE RATE
            </span>

            <strong className="delivery-kpi-value">
              {formatPercentage(
                overallLateRate
              )}
            </strong>

            <span className="delivery-kpi-subtitle">
              Across all monitored orders
            </span>

          </div>

        </div>

      </section>


      {/* =================================================
          SECONDARY METRICS
          ================================================= */}

      <section className="delivery-secondary-grid">

        <div className="delivery-metric-card">

          <span>
            Average Delay
          </span>

          <strong>
            {formatDecimal(
              averageDelay
            )} days
          </strong>

        </div>


        <div className="delivery-metric-card">

          <span>
            Average Risk Score
          </span>

          <strong>
            {formatScore(
              averageRiskScore
            )}
          </strong>

        </div>


        <div className="delivery-metric-card">

          <span>
            Providers With Data
          </span>

          <strong>
            {formatNumber(
              data.length
            )}
          </strong>

        </div>

      </section>


      {/* =================================================
          RISK SUMMARY
          ================================================= */}

      <section className="delivery-page inventory-risk-summary">

        <div className="section-header">

          <div>

            <p className="section-eyebrow">
              RISK DISTRIBUTION
            </p>

            <h2>
              Delivery Risk Overview
            </h2>

          </div>

          <span className="section-count">
            {formatNumber(
              data.length
            )} providers
          </span>

        </div>


        <div className="risk-summary-grid">

          <div className="risk-summary-card critical">

            <span className="risk-summary-dot"></span>

            <div>

              <span>
                Critical
              </span>

              <strong>
                {riskCounts.critical}
              </strong>

            </div>

          </div>


          <div className="risk-summary-card high">

            <span className="risk-summary-dot"></span>

            <div>

              <span>
                High
              </span>

              <strong>
                {riskCounts.high}
              </strong>

            </div>

          </div>


          <div className="risk-summary-card medium">

            <span className="risk-summary-dot"></span>

            <div>

              <span>
                Medium
              </span>

              <strong>
                {riskCounts.medium}
              </strong>

            </div>

          </div>


          <div className="risk-summary-card low">

            <span className="risk-summary-dot"></span>

            <div>

              <span>
                Low
              </span>

              <strong>
                {riskCounts.low}
              </strong>

            </div>

          </div>

        </div>

      </section>


      {/* =================================================
          DELIVERY REGISTER
          ================================================= */}

      <section className="delivery-table-card">

        <div className="delivery-table-header">

          <div>

            <p className="section-eyebrow">
              DELIVERY RISK REGISTER
            </p>

            <h2>
              Provider Risk
            </h2>

            <p>
              Search and filter delivery
              providers by operational risk.
            </p>

          </div>

          <div className="delivery-table-count">
            {formatNumber(
              filteredData.length
            )} shown
          </div>

        </div>


        {/* FILTERS */}

        <div className="delivery-filter-bar">

          <input
            className="delivery-search-input"
            type="text"
            placeholder="Search provider..."
            value={searchTerm}
            onChange={(event) =>
              setSearchTerm(
                event.target.value
              )
            }
          />


          <select
            className="delivery-filter-select"
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
              className="delivery-clear-button"
              onClick={() => {
                setSearchTerm("");
                setRiskFilter("ALL");
              }}
            >
              Clear Filters
            </button>
          )}

        </div>


        {!filteredData.length ? (

          <div className="delivery-empty-wrapper">

            <EmptyState
              title="No providers found"
              message="Try changing the search or risk filter."
            />

          </div>

        ) : (

          <div className="delivery-table-wrapper">

            <table className="delivery-table">

              <thead>

                <tr>

                  <th>
                    Provider
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
                    Avg Delay
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
                  (item, index) => {

                    const provider =
                      getProviderName(
                        item,
                        index
                      );

                    return (

                      <tr
                        key={`${provider}-${index}`}
                      >

                        <td>

                          <div className="provider-cell">

                            <div className="provider-avatar">

                              {String(
                                provider
                              )
                                .slice(0, 2)
                                .toUpperCase()}

                            </div>

                            <strong>
                              {provider}
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
                          {formatDecimal(
                            item.average_delay
                          )}{" "}
                          days
                        </td>


                        <td>

                          <span className="delivery-score">
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

                          <span className="delivery-reason">

                            {item.risk_reason ||
                              "Delivery performance calculated from monitored operational metrics."}

                          </span>

                        </td>

                      </tr>

                    );

                  }
                )}

              </tbody>

            </table>

          </div>

        )}

      </section>


      {/* =================================================
          CHARTS
          ================================================= */}

      <section className="delivery-charts-grid">


        {/* RISK DISTRIBUTION */}

        <div className="delivery-chart-card">

          <div className="delivery-chart-header">

            <p className="section-eyebrow">
              RISK DISTRIBUTION
            </p>

            <h2>
              Provider Risk Levels
            </h2>

          </div>


          <div className="delivery-pie-container">

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
                        key={`risk-${index}`}
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


          <div className="delivery-chart-legend">

            {riskChartData.map(
              (item) => (

                <div
                  key={item.level}
                  className="delivery-legend-item"
                >

                  <span
                    className={`legend-dot ${item.level}`}
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


        {/* DELAY CHART */}

        <div className="delivery-chart-card">

          <div className="delivery-chart-header">

            <p className="section-eyebrow">
              DELAY ANALYSIS
            </p>

            <h2>
              Average Delay by Provider
            </h2>

          </div>


          {delayChartData.length ? (

            <ResponsiveContainer
              width="100%"
              height={360}
            >

              <BarChart
                data={delayChartData}
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
                    `${value}d`
                  }
                />

                <YAxis
                  type="category"
                  dataKey="name"
                  width={90}
                />

                <Tooltip
                  formatter={(value) => [
                    `${Number(
                      value
                    ).toFixed(2)} days`,
                    "Average Delay",
                  ]}
                />

                <Bar
                  dataKey="delay"
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
              title="No delay data"
              message="No provider delay data is available."
            />

          )}

        </div>

      </section>


      {/* =================================================
          INFORMATION
          ================================================= */}

      <section className="delivery-info-card">

        <div className="delivery-info-icon">
          i
        </div>

        <div>

          <h3>
            Delivery Risk Interpretation
          </h3>

          <p>
            Delivery risk is calculated from the
            backend analytics using provider-level
            delivery performance indicators such as
            late-order rate, average delay, and risk
            score. The frontend displays those
            calculated values without modifying the
            underlying risk logic.
          </p>

        </div>

      </section>

    </div>
  );
}

export default DeliveryRisk;
