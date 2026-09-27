import { useEffect, useMemo, useState } from "react";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

import {
  getForecastProducts,
  getProductForecast,
} from "../api/forecastApi";

import Loading from "../components/Loading";
import ErrorMessage from "../components/ErrorMessage";
import EmptyState from "../components/EmptyState";

import {
  formatNumber,
  formatDecimal,
} from "../utils/formatters";

function Forecast() {
  const [products, setProducts] = useState([]);
  const [selectedProduct, setSelectedProduct] = useState("");
  const [forecast, setForecast] = useState(null);

  const [loadingProducts, setLoadingProducts] = useState(true);
  const [loadingForecast, setLoadingForecast] = useState(false);

  const [error, setError] = useState("");

  async function loadProducts() {
    try {
      setLoadingProducts(true);
      setError("");

      const result = await getForecastProducts();

      console.log(
        "FORECAST PRODUCTS API RESPONSE:",
        result
      );

      let productList = [];

      if (Array.isArray(result)) {
        productList = result;
      } else if (Array.isArray(result?.products)) {
        productList = result.products;
      } else if (Array.isArray(result?.data)) {
        productList = result.data;
      }

      setProducts(productList);

      if (productList.length > 0) {
        const firstProduct =
          typeof productList[0] === "string"
            ? productList[0]
            : productList[0]?.product_id ||
              productList[0]?.productId;

        if (firstProduct) {
          setSelectedProduct(firstProduct);
        }
      }
    } catch (err) {
      console.error(
        "FORECAST PRODUCTS ERROR:",
        err
      );

      setError(
        err?.response?.data?.detail ||
          "Unable to load forecast products."
      );
    } finally {
      setLoadingProducts(false);
    }
  }

  async function loadForecast(productId) {
    if (!productId) return;

    try {
      setLoadingForecast(true);
      setError("");

      const result =
        await getProductForecast(productId);

      console.log(
        "PRODUCT FORECAST API RESPONSE:",
        result
      );

      setForecast(result);
    } catch (err) {
      console.error(
        "PRODUCT FORECAST ERROR:",
        err
      );

      setForecast(null);

      setError(
        err?.response?.data?.detail ||
          "Unable to load product forecast."
      );
    } finally {
      setLoadingForecast(false);
    }
  }

  useEffect(() => {
    loadProducts();
  }, []);

  useEffect(() => {
    if (selectedProduct) {
      loadForecast(selectedProduct);
    }
  }, [selectedProduct]);

  const forecastRows = useMemo(() => {
    if (!forecast) return [];

    if (Array.isArray(forecast)) {
      return forecast;
    }

    if (Array.isArray(forecast?.forecast)) {
      return forecast.forecast;
    }

    if (Array.isArray(forecast?.data)) {
      return forecast.data;
    }

    if (Array.isArray(forecast?.predictions)) {
      return forecast.predictions;
    }

    return [];
  }, [forecast]);

  const chartData = useMemo(() => {
    return forecastRows.map((item) => {
      const date =
        item.date ||
        item.forecast_date ||
        item.ds ||
        item.timestamp;

      const value =
        item.forecast ??
        item.prediction ??
        item.predicted_demand ??
        item.demand ??
        item.value;

      return {
        date: date
          ? new Date(date).toLocaleDateString(
              "en-US",
              {
                month: "short",
                day: "numeric",
              }
            )
          : "—",
        forecast: Number(value) || 0,
      };
    });
  }, [forecastRows]);

  const forecastValues = chartData.map(
    (item) => item.forecast
  );

  const averageForecast =
    forecastValues.length > 0
      ? forecastValues.reduce(
          (sum, value) => sum + value,
          0
        ) / forecastValues.length
      : 0;

  const minimumForecast =
    forecastValues.length > 0
      ? Math.min(...forecastValues)
      : 0;

  const maximumForecast =
    forecastValues.length > 0
      ? Math.max(...forecastValues)
      : 0;

  if (loadingProducts) {
    return (
      <div className="page-container forecast-page">
        <Loading message="Loading forecast products..." />
      </div>
    );
  }

  if (error && products.length === 0) {
    return (
      <div className="page-container forecast-page">
        <ErrorMessage
          title="Forecast Unavailable"
          message={error}
          onRetry={loadProducts}
        />
      </div>
    );
  }

  if (products.length === 0) {
    return (
      <div className="page-container forecast-page">
        <EmptyState
          title="No forecast products"
          message="No products are currently available for forecasting."
        />
      </div>
    );
  }

  return (
    <div className="page-container forecast-page">

      {/* HEADER */}
      <div className="page-heading">

        <p className="page-eyebrow">
          DEMAND INTELLIGENCE
        </p>

        <h1>
          Forecast
        </h1>

        <p className="page-description">
          Review short-term product demand forecasts
          generated from historical supply-chain data.
        </p>

      </div>

      {/* PRODUCT SELECTOR */}
      <section className="forecast-selector-card">

        <div>
          <p className="forecast-eyebrow">
            PRODUCT SELECTION
          </p>

          <h2>
            Demand Forecast
          </h2>

          <p>
            Select a product to view its forecast.
          </p>
        </div>

        <div className="forecast-selector-control">

          <label htmlFor="forecast-product">
            Product
          </label>

          <select
            id="forecast-product"
            value={selectedProduct}
            onChange={(event) =>
              setSelectedProduct(event.target.value)
            }
          >
            {products.map((product, index) => {
              const productId =
                typeof product === "string"
                  ? product
                  : product?.product_id ||
                    product?.productId;

              return (
                <option
                  key={productId || index}
                  value={productId}
                >
                  {productId}
                </option>
              );
            })}
          </select>

        </div>

      </section>

      {loadingForecast ? (
        <Loading message="Generating product forecast..." />
      ) : error ? (
        <ErrorMessage
          title="Forecast Unavailable"
          message={error}
          onRetry={() =>
            loadForecast(selectedProduct)
          }
        />
      ) : forecastRows.length === 0 ? (
        <EmptyState
          title="No forecast results"
          message="No forecast points were returned for this product."
        />
      ) : (
        <>
          {/* KPI CARDS */}
          <section className="forecast-kpi-grid">

            <div className="forecast-kpi-card">

              <span>
                PRODUCT
              </span>

              <strong>
                {selectedProduct}
              </strong>

            </div>

            <div className="forecast-kpi-card">

              <span>
                FORECAST HORIZON
              </span>

              <strong>
                {forecastRows.length} days
              </strong>

            </div>

            <div className="forecast-kpi-card">

              <span>
                AVERAGE FORECAST
              </span>

              <strong>
                {formatDecimal(
                  averageForecast,
                  2
                )}
              </strong>

            </div>

            <div className="forecast-kpi-card">

              <span>
                FORECAST RANGE
              </span>

              <strong>
                {formatDecimal(
                  minimumForecast,
                  2
                )}
                {" – "}
                {formatDecimal(
                  maximumForecast,
                  2
                )}
              </strong>

            </div>

          </section>

          {/* CHART */}
          <section className="forecast-chart-card">

            <div className="forecast-card-header">

              <div>
                <p className="forecast-eyebrow">
                  FORECAST TREND
                </p>

                <h2>
                  {selectedProduct} Demand Projection
                </h2>

                <p className="forecast-card-description">
                  Expected daily demand across the selected
                  forecast horizon.
                </p>
              </div>

              <div className="forecast-horizon-badge">
                <span></span>
                {forecastRows.length}-DAY FORECAST
              </div>

            </div>

            <div className="forecast-chart-container">

              <ResponsiveContainer
                width="100%"
                height={340}
              >
                <LineChart
                  data={chartData}
                  margin={{
                    top: 20,
                    right: 25,
                    left: 5,
                    bottom: 15,
                  }}
                >

                  <CartesianGrid
                    stroke="#e2e8f0"
                    strokeDasharray="3 3"
                    vertical={false}
                  />

                  <XAxis
                    dataKey="date"
                    tickLine={false}
                    axisLine={{
                      stroke: "#cbd5e1",
                    }}
                    tick={{
                      fill: "#64748b",
                      fontSize: 11,
                    }}
                    tickMargin={12}
                  />

                  <YAxis
                    tickLine={false}
                    axisLine={false}
                    width={45}
                    tick={{
                      fill: "#64748b",
                      fontSize: 11,
                    }}
                    tickMargin={8}
                    domain={["auto", "auto"]}
                  />

                  <Tooltip
                    cursor={{
                      stroke: "#94a3b8",
                      strokeDasharray: "4 4",
                    }}
                    contentStyle={{
                      border: "1px solid #dbe4ef",
                      borderRadius: "10px",
                      background: "#ffffff",
                      boxShadow:
                        "0 8px 24px rgba(15, 23, 42, 0.10)",
                    }}
                    labelStyle={{
                      color: "#475569",
                      fontWeight: 700,
                      marginBottom: "4px",
                    }}
                    itemStyle={{
                      color: "#2563eb",
                      fontWeight: 700,
                    }}
                    formatter={(value) => [
                      `${formatDecimal(value, 2)} units`,
                      "Forecast",
                    ]}
                  />

                  <Line
                    type="monotone"
                    dataKey="forecast"
                    stroke="#2563eb"
                    strokeWidth={3}
                    dot={{
                      r: 4,
                      strokeWidth: 2,
                      fill: "#ffffff",
                    }}
                    activeDot={{
                      r: 7,
                      strokeWidth: 2,
                    }}
                  />

                </LineChart>
              </ResponsiveContainer>

            </div>

          </section>


          {/* TABLE */}
          <section className="forecast-table-card">

            <div className="forecast-card-header">

              <div>
                <p className="forecast-eyebrow">
                  FORECAST VALUES
                </p>

                <h2>
                  Daily Projection
                </h2>
              </div>

              <span className="forecast-row-count">
                {formatNumber(forecastRows.length)} points
              </span>

            </div>

            <div className="forecast-table-wrapper">

              <table className="forecast-table">

                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Forecast Demand</th>
                  </tr>
                </thead>

                <tbody>
                  {forecastRows.map(
                    (item, index) => {

                      const date =
                        item.date ||
                        item.forecast_date ||
                        item.ds ||
                        item.timestamp;

                      const value =
                        item.forecast ??
                        item.prediction ??
                        item.predicted_demand ??
                        item.demand ??
                        item.value;

                      return (
                        <tr key={index}>

                          <td>
                            {date
                              ? new Date(
                                  date
                                ).toLocaleDateString(
                                  "en-US",
                                  {
                                    month: "short",
                                    day: "numeric",
                                    year: "numeric",
                                  }
                                )
                              : "—"}
                          </td>

                          <td className="forecast-value">
                            {formatDecimal(
                              value,
                              2
                            )}
                          </td>

                        </tr>
                      );
                    }
                  )}
                </tbody>

              </table>

            </div>

          </section>
        </>
      )}

    </div>
  );
}

export default Forecast;
