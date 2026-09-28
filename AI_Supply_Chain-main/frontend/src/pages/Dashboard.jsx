import { useEffect, useState } from "react";
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

import {
  getDashboardMetrics,
  getSupplierRisk,
  getInventoryRisk,
  getDeliveryRisk,
  getRouteRisk,
} from "../api/dashboardApi";


function Dashboard() {
  const [dashboard, setDashboard] = useState(null);
  const [supplierRisk, setSupplierRisk] = useState([]);
  const [inventoryRisk, setInventoryRisk] = useState([]);
  const [deliveryRisk, setDeliveryRisk] = useState([]);
  const [routeRisk, setRouteRisk] = useState([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadDashboard() {
      try {
        setLoading(true);
        setError("");

        const [
          dashboardData,
          supplierData,
          inventoryData,
          deliveryData,
          routeData,
        ] = await Promise.all([
          getDashboardMetrics(),
          getSupplierRisk(),
          getInventoryRisk(),
          getDeliveryRisk(),
          getRouteRisk(),
        ]);

        setDashboard(dashboardData);
        setSupplierRisk(supplierData);
        setInventoryRisk(inventoryData);
        setDeliveryRisk(deliveryData);
        setRouteRisk(routeData);
      } catch (err) {
        console.error(err);
        setError("Unable to load supply-chain analytics.");
      } finally {
        setLoading(false);
      }
    }

    loadDashboard();
  }, []);

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="loading-spinner"></div>
        <p>Loading control tower intelligence...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="error-panel">
        <div className="error-icon">!</div>
        <div>
          <h3>Dashboard unavailable</h3>
          <p>{error}</p>
        </div>
      </div>
    );
  }

  const criticalInventory = inventoryRisk
  .filter(
    (item) => item.risk_level === "CRITICAL"
  )
  .sort(
    (a, b) =>
      Number(b.risk_score || 0) -
      Number(a.risk_score || 0)
  )
  .slice(0, 10);

  const highInventory = inventoryRisk.filter(
    (item) => item.risk_level === "HIGH"
  );

  const criticalSuppliers = supplierRisk.filter(
    (item) => item.risk_level === "CRITICAL"
  );

  const highSuppliers = supplierRisk.filter(
    (item) => item.risk_level === "HIGH"
  );

    const riskLevels = ["CRITICAL", "HIGH", "MEDIUM", "LOW"];

  const inventoryRiskDistribution = riskLevels.map((level) => ({
    name: level,
    value: inventoryRisk.filter(
      (item) => item.risk_level === level
    ).length,
  }));

  const supplierRiskDistribution = riskLevels.map((level) => ({
    name: level,
    value: supplierRisk.filter(
      (item) => item.risk_level === level
    ).length,
  }));

  const deliveryChartData = deliveryRisk.map((item) => ({
  name:
    item["3pl"] ||
    item.provider ||
    item["3PL"] ||
    "Provider",
  lateRate: Number(
    ((item.late_rate || 0) * 100).toFixed(2)
  ),
}));

  return (
    <div className="dashboard-page">
      {/* Page heading */}

      <section className="page-heading dashboard-heading">
        <div>
          <p className="page-eyebrow">EXECUTIVE OVERVIEW</p>

          <h1>Supply Chain Control Tower</h1>

          <p>
            Monitor operational performance, identify emerging risks and
            investigate supply-chain disruptions.
          </p>
        </div>

        <div className="dashboard-meta">
          <span className="live-indicator"></span>
          <span>Live analytics</span>
        </div>
      </section>

      {/* KPI cards */}

      <section className="kpi-grid">
        <div className="kpi-card">
          <div className="kpi-top">
            <span className="kpi-label">TOTAL ORDERS</span>
            <span className="kpi-icon">▦</span>
          </div>

          <strong>
            {dashboard.total_orders.toLocaleString("en-US")}
          </strong>

          <span className="kpi-description">
            Orders processed across the network
          </span>
        </div>

        <div className="kpi-card warning-card">
          <div className="kpi-top">
            <span className="kpi-label">LATE ORDERS</span>
            <span className="kpi-icon">⇢</span>
          </div>

          <strong>
            {dashboard.late_orders.toLocaleString("en-US")}
          </strong>

          <span className="kpi-description">
            Orders exceeding expected delivery time
          </span>
        </div>

        <div className="kpi-card">
          <div className="kpi-top">
            <span className="kpi-label">LATE RATE</span>
            <span className="kpi-icon">%</span>
          </div>

          <strong>{dashboard.late_rate.toFixed(2)}%</strong>

          <span className="kpi-description">
            Overall delivery delay rate
          </span>
        </div>

        <div className="kpi-card">
          <div className="kpi-top">
            <span className="kpi-label">TOTAL UNITS</span>
            <span className="kpi-icon">▤</span>
          </div>

          <strong>
            {dashboard.total_units.toLocaleString("en-US")}
          </strong>

          <span className="kpi-description">
            Units represented across orders
          </span>
        </div>

        <div className="kpi-card danger-card">
          <div className="kpi-top">
            <span className="kpi-label">STOCKOUT RECORDS</span>
            <span className="kpi-icon">△</span>
          </div>

          <strong>
            {dashboard.inventory_stockout_records.toLocaleString("en-US")}
          </strong>

          <span className="kpi-description">
            Inventory records with zero available stock
          </span>
        </div>

        <div className="kpi-card">
          <div className="kpi-top">
            <span className="kpi-label">ORDER VALUE</span>
            <span className="kpi-icon">$</span>
          </div>

          <strong>
            ${(dashboard.total_order_value / 1000000).toFixed(2)}M
          </strong>

          <span className="kpi-description">
            Total value represented in the dataset
          </span>
        </div>
      </section>

      {/* Risk overview */}

      <section className="section-block">
        <div className="section-header">
          <div>
            <p className="section-eyebrow">RISK INTELLIGENCE</p>
            <h2>Operational Risk Overview</h2>
          </div>

          <span className="section-count">
            {inventoryRisk.length + supplierRisk.length} entities monitored
          </span>
        </div>

        <div className="risk-overview-grid">
          <div className="risk-summary-card">
            <div className="risk-summary-header">
              <div>
                <span className="risk-summary-label">
                  INVENTORY
                </span>
                <h3>Inventory Risk</h3>
              </div>

              <span className="risk-summary-icon">▤</span>
            </div>

            <div className="risk-number">
              {criticalInventory.length}
              <span> critical</span>
            </div>

            <div className="risk-breakdown">
              <span>
                <i className="risk-dot critical"></i>
                Critical: {criticalInventory.length}
              </span>

              <span>
                <i className="risk-dot high"></i>
                High: {highInventory.length}
              </span>

              <span>
                <i className="risk-dot normal"></i>
                Other:{" "}
                {inventoryRisk.length -
                  criticalInventory.length -
                  highInventory.length}
              </span>
            </div>
          </div>

          <div className="risk-summary-card">
            <div className="risk-summary-header">
              <div>
                <span className="risk-summary-label">
                  SUPPLIERS
                </span>
                <h3>Supplier Risk</h3>
              </div>

              <span className="risk-summary-icon">◉</span>
            </div>

            <div className="risk-number">
              {criticalSuppliers.length}
              <span> critical</span>
            </div>

            <div className="risk-breakdown">
              <span>
                <i className="risk-dot critical"></i>
                Critical: {criticalSuppliers.length}
              </span>

              <span>
                <i className="risk-dot high"></i>
                High: {highSuppliers.length}
              </span>

              <span>
                <i className="risk-dot normal"></i>
                Other:{" "}
                {supplierRisk.length -
                  criticalSuppliers.length -
                  highSuppliers.length}
              </span>
            </div>
          </div>

          <div className="risk-summary-card">
            <div className="risk-summary-header">
              <div>
                <span className="risk-summary-label">
                  DELIVERY
                </span>
                <h3>Delivery Network</h3>
              </div>

              <span className="risk-summary-icon">⇢</span>
            </div>

            <div className="risk-number">
              {deliveryRisk.length}
              <span> providers</span>
            </div>

            <div className="risk-breakdown">
              <span>
                Average providers analyzed
              </span>
            </div>
          </div>

          <div className="risk-summary-card">
            <div className="risk-summary-header">
              <div>
                <span className="risk-summary-label">
                  ROUTES
                </span>
                <h3>Route Network</h3>
              </div>

              <span className="risk-summary-icon">⌁</span>
            </div>

            <div className="risk-number">
              {routeRisk.length}
              <span> routes</span>
            </div>

            <div className="risk-breakdown">
              <span>
                Routes monitored by risk analytics
              </span>
            </div>
          </div>
        </div>
      </section>

            {/* Visual analytics */}

      <section className="section-block">
        <div className="section-header">
          <div>
            <p className="section-eyebrow">NETWORK ANALYTICS</p>
            <h2>Operational Risk Signals</h2>
          </div>

          <span className="section-count">
            Derived from current backend analytics
          </span>
        </div>

        <div className="analytics-grid">

          {/* Delivery chart */}

          <div className="chart-card delivery-chart-card">
            <div className="chart-header">
              <div>
                <span className="chart-label">DELIVERY PERFORMANCE</span>
                <h3>Provider Late Rate</h3>
              </div>
            </div>

            <div className="chart-container">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={deliveryChartData}
                  margin={{
                    top: 10,
                    right: 10,
                    left: 0,
                    bottom: 5,
                  }}
                >
                  <CartesianGrid
                    strokeDasharray="3 3"
                    vertical={false}
                  />

                  <XAxis
                    dataKey="name"
                    tick={{
                      fontSize: 10,
                    }}
                    axisLine={false}
                    tickLine={false}
                  />

                  <YAxis
                    tick={{
                      fontSize: 10,
                    }}
                    axisLine={false}
                    tickLine={false}
                    tickFormatter={(value) => `${value}%`}
                  />

                  <Tooltip
                    formatter={(value) => [
                      `${value}%`,
                      "Late Rate",
                    ]}
                  />

                  <Bar
                    dataKey="lateRate"
                    radius={[5, 5, 0, 0]}
                    fill="#D4AF37"
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Inventory distribution */}

          <div className="chart-card">
            <div className="chart-header">
              <div>
                <span className="chart-label">
                  INVENTORY RISK
                </span>
                <h3>Risk Distribution</h3>
              </div>
            </div>

            <div className="pie-layout">
              <div className="pie-container">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={inventoryRiskDistribution}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      innerRadius={55}
                      outerRadius={82}
                      paddingAngle={3}
                    >
                      {inventoryRiskDistribution.map(
                        (entry) => {
                          const colors = {
                            CRITICAL: "#B85C5C",
                            HIGH: "#D4AF37",
                            MEDIUM: "#C8B98A",
                            LOW: "#666666",
                          };

                          return (
                            <Cell
                              key={entry.name}
                              fill={colors[entry.name]}
                            />
                          );
                        }
                      )}
                    </Pie>

                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </div>

              <div className="chart-legend">
                {inventoryRiskDistribution.map(
                  (item) => (
                    <div
                      className="legend-row"
                      key={item.name}
                    >
                      <span
                        className={`legend-dot ${item.name.toLowerCase()}`}
                      ></span>

                      <span className="legend-name">
                        {item.name}
                      </span>

                      <strong>{item.value}</strong>
                    </div>
                  )
                )}
              </div>
            </div>
          </div>
        </div>
      </section>

            <section className="section-block">

        <div className="section-header">
          <div>
            <p className="section-eyebrow">
              SUPPLIER INTELLIGENCE
            </p>

            <h2>Supplier Risk Distribution</h2>
          </div>

          <span className="section-count">
            {supplierRisk.length} suppliers analyzed
          </span>
        </div>

        <div className="supplier-chart-card">

          <div className="supplier-chart">

            <ResponsiveContainer width="100%" height={250}>
              <BarChart
                data={supplierRiskDistribution}
                layout="vertical"
                margin={{
                  top: 5,
                  right: 30,
                  left: 20,
                  bottom: 5,
                }}
              >
                <CartesianGrid
                  strokeDasharray="3 3"
                  horizontal={false}
                />

                <XAxis
                  type="number"
                  allowDecimals={false}
                  axisLine={false}
                  tickLine={false}
                />

                <YAxis
                  dataKey="name"
                  type="category"
                  axisLine={false}
                  tickLine={false}
                  width={75}
                  tick={{
                    fontSize: 10,
                  }}
                />

                <Tooltip />

                <Bar
                  dataKey="value"
                  fill="#E5C45A"
                  radius={[0, 5, 5, 0]}
                  barSize={24}
                />
              </BarChart>
            </ResponsiveContainer>

          </div>

          <div className="supplier-summary">

            <div className="summary-number">
              {supplierRisk.length}
            </div>

            <span>Total suppliers analyzed</span>

            <div className="summary-line"></div>

            <div className="summary-item">
              <span>Critical</span>
              <strong>{criticalSuppliers.length}</strong>
            </div>

            <div className="summary-item">
              <span>High</span>
              <strong>{highSuppliers.length}</strong>
            </div>

            <div className="summary-item">
              <span>Other</span>
              <strong>
                {supplierRisk.length -
                  criticalSuppliers.length -
                  highSuppliers.length}
              </strong>
            </div>

          </div>

        </div>
      </section>

      {/* Critical inventory */}

      <section className="section-block">
        <div className="section-header">
          <div>
            <p className="section-eyebrow">ATTENTION REQUIRED</p>
            <h2>Critical Inventory Exposure</h2>
          </div>

          <span className="section-count">
            {criticalInventory.length} critical products
          </span>
        </div>

        <div className="data-table-wrapper">
          {criticalInventory.length === 0 ? (
            <div className="table-empty">
              No critical inventory risks detected.
            </div>
          ) : (
            <table className="risk-table">
              <thead>
                <tr>
                  <th>PRODUCT</th>
                  <th>RISK SCORE</th>
                  <th>STOCKOUT RATE</th>
                  <th>DAYS OF COVER</th>
                  <th>DEMAND PRESSURE</th>
                  <th>STATUS</th>
                </tr>
              </thead>

              <tbody>
                {criticalInventory.slice(0, 5).map((item) => (
                  <tr key={item.product_id}>
                    <td>
                      <strong>{item.product_id}</strong>
                    </td>

                    <td>
                      <span className="score-value">
                        {item.risk_score.toFixed(2)}
                      </span>
                    </td>

                    <td>
                      {(item.stockout_rate * 100).toFixed(2)}%
                    </td>

                    <td>
                      {item.days_of_cover.toFixed(2)} days
                    </td>

                    <td>
                      {(item.demand_pressure * 100).toFixed(2)}%
                    </td>

                    <td>
                      <span className="risk-badge critical">
                        {item.risk_level}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </section>
    </div>
  );
}

export default Dashboard;
