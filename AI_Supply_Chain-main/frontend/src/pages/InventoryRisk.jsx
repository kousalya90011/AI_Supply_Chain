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

import {
  getInventoryRiskData,
  getProductEvidence,
} from "../api/riskApi";

import RiskBadge from "../components/RiskBadge";
import RiskTabs from "../components/RiskTabs";
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

/* =========================================================
   HELPERS
   ========================================================= */

function findValue(object, keys) {
  if (!object || typeof object !== "object") {
    return undefined;
  }

  for (const key of keys) {
    if (
      Object.prototype.hasOwnProperty.call(object, key) &&
      object[key] !== null &&
      object[key] !== undefined
    ) {
      return object[key];
    }
  }

  for (const value of Object.values(object)) {
    if (value && typeof value === "object") {
      const result = findValue(value, keys);

      if (result !== undefined) {
        return result;
      }
    }
  }

  return undefined;
}


function normalizeEvidenceResponse(result, fallbackProductId) {
  if (!result) {
    return null;
  }

  const productId =
    findValue(result, [
      "product_id",
      "productId",
    ]) || fallbackProductId;

  const riskScore = findValue(result, [
    "risk_score",
    "riskScore",
  ]);

  const riskLevel = findValue(result, [
    "risk_level",
    "riskLevel",
  ]);

  const stockoutRate = findValue(result, [
    "stockout_rate",
    "stockoutRate",
  ]);

  const daysOfCover = findValue(result, [
    "days_of_cover",
    "daysOfCover",
  ]);

  const demandPressure = findValue(result, [
    "demand_pressure",
    "demandPressure",
  ]);

  const averageInventory = findValue(result, [
    "average_inventory",
    "avg_inventory",
    "averageInventory",
  ]);

  const averageDailyDemand = findValue(result, [
    "average_daily_demand",
    "daily_demand",
    "averageDailyDemand",
  ]);

  const zeroInventoryRecords = findValue(result, [
    "zero_inventory_records",
    "zero_inventory_days",
    "zeroInventoryRecords",
    "zeroInventoryDays",
  ]);

  const totalDemand = findValue(result, [
    "total_demand",
    "totalDemand",
  ]);

  const riskReason = findValue(result, [
    "risk_reason",
    "riskReason",
  ]);

  return {
    product_id: productId,
    risk_score: riskScore,
    risk_level: riskLevel,
    stockout_rate: stockoutRate,
    days_of_cover: daysOfCover,
    demand_pressure: demandPressure,
    average_inventory: averageInventory,
    average_daily_demand: averageDailyDemand,
    zero_inventory_records: zeroInventoryRecords,
    total_demand: totalDemand,
    risk_reason: riskReason,
  };
}


/* =========================================================
   COMPONENT
   ========================================================= */

function InventoryRisk() {
  const [inventoryRisk, setInventoryRisk] = useState([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [searchTerm, setSearchTerm] = useState("");
  const [riskFilter, setRiskFilter] = useState("ALL");

  const [productId, setProductId] = useState("");
  const [evidence, setEvidence] = useState(null);

  const [evidenceLoading, setEvidenceLoading] = useState(false);
  const [evidenceError, setEvidenceError] = useState("");


  /* =====================================================
     LOAD INVENTORY RISK
     ===================================================== */

  async function loadInventoryRisk() {
    try {
      setLoading(true);
      setError("");

      const data = await getInventoryRiskData();

      setInventoryRisk(
        Array.isArray(data) ? data : []
      );
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          "Unable to load inventory risk data."
      );
    } finally {
      setLoading(false);
    }
  }


  useEffect(() => {
    loadInventoryRisk();
  }, []);


  /* =====================================================
     RISK COUNTS
     ===================================================== */

  const riskCounts = useMemo(
    () => countRiskLevels(inventoryRisk),
    [inventoryRisk]
  );


  /* =====================================================
     FILTERED PRODUCTS
     ===================================================== */

  const filteredProducts = useMemo(() => {
    const search = searchTerm
      .trim()
      .toLowerCase();

    return inventoryRisk.filter((product) => {
      const productIdValue = String(
        product.product_id || ""
      ).toLowerCase();

      const matchesSearch =
        !search ||
        productIdValue.includes(search);

      const matchesRisk =
        riskFilter === "ALL" ||
        String(
          product.risk_level || ""
        ).toUpperCase() === riskFilter;

      return (
        matchesSearch &&
        matchesRisk
      );
    });
  }, [
    inventoryRisk,
    searchTerm,
    riskFilter,
  ]);


  /* =====================================================
     AVERAGE STOCKOUT RATE
     ===================================================== */

  const averageStockoutRate = useMemo(() => {
    if (!inventoryRisk.length) {
      return 0;
    }

    return (
      inventoryRisk.reduce(
        (sum, item) =>
          sum +
          Number(
            item.stockout_rate || 0
          ),
        0
      ) / inventoryRisk.length
    );
  }, [inventoryRisk]);


  /* =====================================================
     AVERAGE DAYS COVER
     ===================================================== */

  const averageDaysCover = useMemo(() => {
    if (!inventoryRisk.length) {
      return 0;
    }

    return (
      inventoryRisk.reduce(
        (sum, item) =>
          sum +
          Number(
            item.days_of_cover || 0
          ),
        0
      ) / inventoryRisk.length
    );
  }, [inventoryRisk]);


  /* =====================================================
     TOTAL STOCKOUT DAYS
     ===================================================== */

  const totalStockoutDays = useMemo(() => {
    return inventoryRisk.reduce(
      (sum, item) =>
        sum +
        Number(
          item.zero_inventory_days || 0
        ),
      0
    );
  }, [inventoryRisk]);


  /* =====================================================
     CHART DATA
     ===================================================== */

  const chartData = useMemo(() => {
    return [...inventoryRisk]
      .sort(
        (a, b) =>
          Number(
            b.risk_score || 0
          ) -
          Number(
            a.risk_score || 0
          )
      )
      .slice(0, 12)
      .map((item) => ({
        product: item.product_id,
        score: Number(
          item.risk_score || 0
        ),
      }));
  }, [inventoryRisk]);


  /* =====================================================
     PRODUCT INVESTIGATION
     ===================================================== */

  async function investigateProduct() {
    const normalizedId =
      productId.trim().toUpperCase();

    if (!normalizedId) {
      setEvidenceError(
        "Enter a product ID."
      );

      setEvidence(null);
      return;
    }

    try {
      setEvidenceLoading(true);
      setEvidenceError("");
      setEvidence(null);

      const result =
        await getProductEvidence(
          normalizedId
        );

      console.log(
        "PRODUCT EVIDENCE API RESPONSE:",
        result
      );

      const normalizedEvidence =
        normalizeEvidenceResponse(
          result,
          normalizedId
        );

      console.log(
        "NORMALIZED PRODUCT EVIDENCE:",
        normalizedEvidence
      );

      if (!normalizedEvidence) {
        setEvidenceError(
          "No evidence was returned for this product."
        );

        return;
      }

      setEvidence(
        normalizedEvidence
      );

    } catch (err) {
      console.error(
        "PRODUCT EVIDENCE ERROR:",
        err
      );

      setEvidenceError(
        err.response?.data?.detail ||
          "Product evidence could not be loaded."
      );
    } finally {
      setEvidenceLoading(false);
    }
  }


  /* =====================================================
     LOADING
     ===================================================== */

  if (loading) {
    return (
      <Loading
        message="Loading inventory risk..."
      />
    );
  }


  /* =====================================================
     ERROR
     ===================================================== */

  if (error) {
    return (
      <ErrorMessage
        title="Inventory risk unavailable"
        message={error}
        onRetry={loadInventoryRisk}
      />
    );
  }


  /* =====================================================
     UI
     ===================================================== */

  return (
    <div className="page-container">
      <RiskTabs />

      {/* =================================================
          PAGE HEADER
      ================================================= */}

      <div className="page-heading dashboard-heading">

        <div>

          <p className="page-eyebrow">
            INVENTORY INTELLIGENCE
          </p>

          <h1>
            Inventory Risk
          </h1>

          <p className="page-description">
            Monitor stockout exposure,
            demand pressure and inventory
            coverage across the supply chain.
          </p>

        </div>


        <div className="dashboard-meta">

          <span className="live-indicator"></span>

          Live backend data

        </div>

      </div>


      {/* =================================================
          KPI CARDS
      ================================================= */}

      <div className="supplier-summary-grid">

        <div className="supplier-stat-card">

          <div className="supplier-stat-top">

            <span className="stat-label">
              RISK RECORDS
            </span>

            <span className="stat-icon">
              #
            </span>

          </div>

          <strong className="supplier-stat-value">
            {formatNumber(
              inventoryRisk.length
            )}
          </strong>

          <span className="stat-subtext">
            Returned by risk analysis
          </span>

        </div>


        <div className="supplier-stat-card critical-card">

          <div className="supplier-stat-top">

            <span className="stat-label">
              CRITICAL
            </span>

            <span className="stat-icon">
              !
            </span>

          </div>

          <strong className="supplier-stat-value">
            {formatNumber(
              riskCounts.critical
            )}
          </strong>

          <span className="stat-subtext">
            Critical inventory records
          </span>

        </div>


        <div className="supplier-stat-card high-card">

          <div className="supplier-stat-top">

            <span className="stat-label">
              AVG STOCKOUT RATE
            </span>

            <span className="stat-icon">
              %
            </span>

          </div>

          <strong className="supplier-stat-value">
            {formatPercentage(
              averageStockoutRate
            )}
          </strong>

          <span className="stat-subtext">
            Across returned records
          </span>

        </div>


        <div className="supplier-stat-card">

          <div className="supplier-stat-top">

            <span className="stat-label">
              AVG DAYS OF COVER
            </span>

            <span className="stat-icon">
              ◷
            </span>

          </div>

          <strong className="supplier-stat-value">
            {formatDecimal(
              averageDaysCover
            )}
          </strong>

          <span className="stat-subtext">
            Inventory coverage
          </span>

        </div>

      </div>


      {/* =================================================
          RISK DISTRIBUTION
      ================================================= */}

      <div className="section-block">

        <div className="section-header">

          <div>

            <span className="section-eyebrow">
              RISK DISTRIBUTION
            </span>

            <h2>
              Inventory Risk Overview
            </h2>

          </div>

          <span className="section-count">
            {inventoryRisk.length} risk records
          </span>

        </div>


        <div className="risk-overview-grid">

          <div className="risk-summary-card">

            <div className="risk-summary-header">

              <div>

                <span className="risk-summary-label">
                  CRITICAL
                </span>

                <h3>
                  Critical Exposure
                </h3>

              </div>

              <div className="risk-summary-icon">
                !
              </div>

            </div>


            <div className="risk-number">

              {riskCounts.critical}

              <span>
                {" "}records
              </span>

            </div>


            <div className="risk-breakdown">

              <span>

                <i className="risk-dot critical"></i>

                Highest risk level

              </span>

            </div>

          </div>


          <div className="risk-summary-card">

            <div className="risk-summary-header">

              <div>

                <span className="risk-summary-label">
                  HIGH
                </span>

                <h3>
                  High Exposure
                </h3>

              </div>

              <div className="risk-summary-icon">
                !
              </div>

            </div>


            <div className="risk-number">

              {riskCounts.high}

              <span>
                {" "}records
              </span>

            </div>


            <div className="risk-breakdown">

              <span>

                <i className="risk-dot high"></i>

                High risk level

              </span>

            </div>

          </div>


          <div className="risk-summary-card">

            <div className="risk-summary-header">

              <div>

                <span className="risk-summary-label">
                  MEDIUM
                </span>

                <h3>
                  Medium Exposure
                </h3>

              </div>

              <div className="risk-summary-icon">
                •
              </div>

            </div>


            <div className="risk-number">

              {riskCounts.medium}

              <span>
                {" "}records
              </span>

            </div>


            <div className="risk-breakdown">

              <span>

                <i className="risk-dot normal"></i>

                Medium risk level

              </span>

            </div>

          </div>


          <div className="risk-summary-card">

            <div className="risk-summary-header">

              <div>

                <span className="risk-summary-label">
                  LOW
                </span>

                <h3>
                  Low Exposure
                </h3>

              </div>

              <div className="risk-summary-icon">
                ✓
              </div>

            </div>


            <div className="risk-number">

              {riskCounts.low}

              <span>
                {" "}records
              </span>

            </div>


            <div className="risk-breakdown">

              <span>

                <i className="risk-dot normal"></i>

                Low risk level

              </span>

            </div>

          </div>

        </div>

      </div>


      {/* =================================================
          RISK REGISTER
      ================================================= */}

      <div className="section-block supplier-table-section">

        <div className="section-header">

          <div>

            <span className="section-eyebrow">
              RISK REGISTER
            </span>

            <h2>
              Inventory Risk Records
            </h2>

            <p>
              Products returned by the
              inventory risk analysis endpoint.
            </p>

          </div>


          <div className="table-controls">

            <input
              className="search-input"
              type="text"
              placeholder="Search product ID..."
              value={searchTerm}
              onChange={(event) =>
                setSearchTerm(
                  event.target.value
                )
              }
            />


            <select
              className="risk-filter"
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

          </div>

        </div>


        {filteredProducts.length === 0 ? (

          <EmptyState
            title="No matching products"
            message="Try another product ID or risk level."
          />

        ) : (

          <div className="data-table-wrapper">

            <table className="risk-table inventory-table">

              <thead>

                <tr>

                  <th>
                    PRODUCT
                  </th>

                  <th>
                    RISK
                  </th>

                  <th>
                    RISK SCORE
                  </th>

                  <th>
                    STOCKOUT RATE
                  </th>

                  <th>
                    DAYS COVER
                  </th>

                  <th>
                    AVG INVENTORY
                  </th>

                  <th>
                    DAILY DEMAND
                  </th>

                  <th>
                    ZERO INVENTORY DAYS
                  </th>

                </tr>

              </thead>


              <tbody>

                {filteredProducts.map(
                  (product) => (

                    <tr
                      key={
                        product.product_id
                      }
                    >

                      <td>

                        <strong>
                          {product.product_id}
                        </strong>

                      </td>


                      <td>

                        <RiskBadge
                          level={
                            product.risk_level
                          }
                        />

                      </td>


                      <td>

                        <span className="score-value">
                          {formatScore(
                            product.risk_score
                          )}
                        </span>

                      </td>


                      <td>

                        {formatPercentage(
                          product.stockout_rate
                        )}

                      </td>


                      <td>

                        {formatDecimal(
                          product.days_of_cover
                        )}

                      </td>


                      <td>

                        {formatDecimal(
                          product.avg_inventory
                        )}

                      </td>


                      <td>

                        {formatDecimal(
                          product.average_daily_demand
                        )}

                      </td>


                      <td>

                        {formatNumber(
                          product.zero_inventory_days
                        )}

                      </td>

                    </tr>

                  )
                )}

              </tbody>

            </table>

          </div>

        )}

      </div>


      {/* =================================================
          ANALYTICS
      ================================================= */}

      <div className="supplier-risk-distribution">

        <div className="distribution-card">

          <div className="section-header">

            <div>

              <span className="section-eyebrow">
                RISK SCORE
              </span>

              <h2>
                Highest Inventory Risk Products
              </h2>

            </div>

          </div>


          <div className="supplier-risk-chart inventory-risk-chart">

            <ResponsiveContainer
              width="100%"
              height="100%"
            >

              <BarChart
                data={chartData}
                layout="vertical"
                margin={{
                  top: 5,
                  right: 20,
                  left: 15,
                  bottom: 5,
                }}
              >

                <CartesianGrid
                  strokeDasharray="3 3"
                  horizontal={false}
                  stroke="#eef2f7"
                />

                <XAxis
                  type="number"
                  domain={[0, 100]}
                  tick={{
                    fill: "#94a3b8",
                    fontSize: 9,
                  }}
                />

                <YAxis
                  dataKey="product"
                  type="category"
                  width={65}
                  tick={{
                    fill: "#64748b",
                    fontSize: 9,
                  }}
                />

                <Tooltip
                  formatter={(value) => [
                    Number(value).toFixed(2),
                    "Risk Score",
                  ]}
                />

                <Bar
                  dataKey="score"
                  fill="#2563eb"
                  radius={[
                    0,
                    4,
                    4,
                    0,
                  ]}
                />

              </BarChart>

            </ResponsiveContainer>

          </div>

        </div>


        <div className="distribution-card">

          <div className="section-header">

            <div>

              <span className="section-eyebrow">
                STOCKOUT EXPOSURE
              </span>

              <h2>
                Zero Inventory Days
              </h2>

            </div>

          </div>


          <div className="inventory-stat-panel">

            <strong>
              {formatNumber(
                totalStockoutDays
              )}
            </strong>

            <span>
              Total zero-inventory days
              across returned inventory
              risk records.
            </span>

            <p>
              This value is calculated
              directly from the backend
              inventory-risk response.
            </p>

          </div>

        </div>

      </div>


      {/* =================================================
          PRODUCT INVESTIGATION
      ================================================= */}

      <div className="section-block">

        <div className="section-header investigation-header">

          <div>

            <span className="section-eyebrow">
              PRODUCT INVESTIGATION
            </span>

            <h2>
              Investigate Product
            </h2>

            <p>
              Search for any product and
              retrieve its backend evidence.
            </p>

          </div>

        </div>


        <div className="investigation-card">

          <div className="investigation-search">

            <input
              className="search-input"
              type="text"
              placeholder="Enter Product ID e.g. P00003"
              value={productId}
              onChange={(event) =>
                setProductId(
                  event.target.value
                )
              }
              onKeyDown={(event) => {

                if (
                  event.key === "Enter"
                ) {
                  investigateProduct();
                }

              }}
            />


            <button
              className="primary-button"
              onClick={
                investigateProduct
              }
              disabled={
                evidenceLoading
              }
            >

              {evidenceLoading
                ? "Loading..."
                : "Investigate"}

            </button>

          </div>


          {evidenceError && (

            <div className="inline-error">

              {evidenceError}

            </div>

          )}


          {evidence && (

            <div className="evidence-panel">

              <div className="evidence-header">

                <div>

                  <span className="section-eyebrow">
                    PRODUCT EVIDENCE
                  </span>

                  <h3>
                    {evidence.product_id}
                  </h3>

                </div>


                <RiskBadge
                  level={
                    evidence.risk_level ||
                    "UNKNOWN"
                  }
                />

              </div>


              <div className="evidence-grid">


                {/* RISK SCORE */}

                <div>

                  <span>
                    Risk Score
                  </span>

                  <strong>

                    {formatScore(
                      evidence.risk_score
                    )}

                  </strong>

                </div>


                {/* STOCKOUT RATE */}

                <div>

                  <span>
                    Stockout Rate
                  </span>

                  <strong>

                    {formatPercentage(
                      evidence.stockout_rate
                    )}

                  </strong>

                </div>


                {/* DAYS OF COVER */}

                <div>

                  <span>
                    Days of Cover
                  </span>

                  <strong>

                    {formatDecimal(
                      evidence.days_of_cover
                    )}

                  </strong>

                </div>


                {/* DEMAND PRESSURE */}

                <div>

                  <span>
                    Demand Pressure
                  </span>

                  <strong>

                    {formatPercentage(
                      evidence.demand_pressure
                    )}

                  </strong>

                </div>


                {/* AVERAGE INVENTORY */}

                <div>

                  <span>
                    Average Inventory
                  </span>

                  <strong>

                    {formatDecimal(
                      evidence.average_inventory
                    )}

                  </strong>

                </div>


                {/* DAILY DEMAND */}

                <div>

                  <span>
                    Daily Demand
                  </span>

                  <strong>

                    {formatDecimal(
                      evidence.average_daily_demand
                    )}

                  </strong>

                </div>


                {/* ZERO INVENTORY RECORDS */}

                <div>

                  <span>
                    Zero Inventory Records
                  </span>

                  <strong>

                    {formatNumber(
                      evidence.zero_inventory_records
                    )}

                  </strong>

                </div>


                {/* TOTAL DEMAND */}

                <div>

                  <span>
                    Total Demand
                  </span>

                  <strong>

                    {formatNumber(
                      evidence.total_demand
                    )}

                  </strong>

                </div>

              </div>


              {evidence.risk_reason && (

                <div className="evidence-reason">

                  <span>
                    Risk Reason
                  </span>

                  <p>
                    {evidence.risk_reason}
                  </p>

                </div>

              )}

            </div>

          )}

        </div>

      </div>

    </div>
  );
}

export default InventoryRisk;
