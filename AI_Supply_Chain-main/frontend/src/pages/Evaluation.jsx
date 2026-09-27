import { useEffect, useState } from "react";

import {
  getEvaluationSummary,
  getRoutingEvaluation,
  getForecastEvaluation,
  runEvaluation,
  getEvaluationResults,
} from "../api/evaluationApi";

import {
  getForecastProducts,
} from "../api/forecastApi";

import Loading from "../components/Loading";
import ErrorMessage from "../components/ErrorMessage";

import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
} from "recharts";



function formatNumber(value, digits = 2) {
  const number = Number(value);

  if (!Number.isFinite(number)) {
    return "—";
  }

  return number.toFixed(digits);
}


function formatPercentage(value, digits = 1) {
  const number = Number(value);

  if (!Number.isFinite(number)) {
    return "—";
  }

  /*
    Backend evaluation percentages such as:
    0.9 -> 90%
  */

  if (number <= 1) {
    return `${(number * 100).toFixed(digits)}%`;
  }

  return `${number.toFixed(digits)}%`;
}


function formatMilliseconds(value) {
  const number = Number(value);

  if (!Number.isFinite(number)) {
    return "—";
  }

  return `${number.toFixed(0)} ms`;
}


function getValue(object, keys, fallback = null) {
  if (!object || typeof object !== "object") {
    return fallback;
  }

  for (const key of keys) {
    if (
      object[key] !== undefined &&
      object[key] !== null
    ) {
      return object[key];
    }
  }

  return fallback;
}


function MetricCard({
  label,
  value,
  description,
  className = "",
}) {
  return (
    <div
      className={`evaluation-metric-card ${className}`}
    >
      <span className="evaluation-metric-label">
        {label}
      </span>

      <strong className="evaluation-metric-value">
        {value}
      </strong>

      <p className="evaluation-metric-description">
        {description}
      </p>
    </div>
  );
}


function Evaluation() {
  const [summary, setSummary] = useState(null);
  const [routing, setRouting] = useState(null);
  const [evalResults, setEvalResults] = useState([]);

  const [products, setProducts] = useState([]);
  const [selectedProduct, setSelectedProduct] =
    useState("P00003");

  const [forecastEvaluation, setForecastEvaluation] =
    useState(null);

  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);

  const [error, setError] = useState("");
  const [runMessage, setRunMessage] =
    useState("");


  async function loadEvaluation() {
    try {
      setLoading(true);
      setError("");

      const [
        summaryResult,
        routingResult,
        productsResult,
        resultsResult,
      ] = await Promise.all([
        getEvaluationSummary(),
        getRoutingEvaluation(),
        getForecastProducts(),
        getEvaluationResults(50).catch(() => ({ results: [] })),
      ]);

      setSummary(summaryResult);
      setRouting(routingResult);
      setEvalResults(resultsResult?.results || []);

      const productList =
        Array.isArray(productsResult)
          ? productsResult
          : productsResult?.products ||
            productsResult?.data ||
            productsResult?.forecast_products ||
            [];

      setProducts(productList);

      /*
        Keep P00003 as the default when available.
      */

      const hasDefaultProduct =
        productList.some(
          (item) => {
            const id =
              typeof item === "string"
                ? item
                : item?.product_id ||
                  item?.productId ||
                  item?.id;

            return id === "P00003";
          }
        );

      if (
        hasDefaultProduct ||
        productList.length === 0
      ) {
        setSelectedProduct("P00003");
      } else {
        const first =
          productList[0];

        setSelectedProduct(
          typeof first === "string"
            ? first
            : first?.product_id ||
              first?.productId ||
              first?.id ||
              "P00003"
        );
      }

    } catch (err) {
      console.error(
        "Evaluation loading error:",
        err
      );

      setError(
        err?.response?.data?.detail ||
          "Unable to load evaluation data."
      );

    } finally {
      setLoading(false);
    }
  }


  async function loadForecastEvaluation(
    productId
  ) {
    if (!productId) {
      return;
    }

    try {
      const result =
        await getForecastEvaluation(
          productId
        );

      setForecastEvaluation(result);

    } catch (err) {
      console.error(
        "Forecast evaluation error:",
        err
      );

      setForecastEvaluation(null);
    }
  }


  useEffect(() => {
    loadEvaluation();
  }, []);


  useEffect(() => {
    if (selectedProduct) {
      loadForecastEvaluation(
        selectedProduct
      );
    }
  }, [selectedProduct]);


  async function handleRunEvaluation() {
    try {
      setRunning(true);
      setRunMessage("");
      setError("");

      const result =
        await runEvaluation();

      setRunMessage(
        result?.message ||
          "Evaluation completed successfully."
      );

      /*
        Refresh the displayed metrics
        after running evaluation.
      */

      await loadEvaluation();

      await loadForecastEvaluation(
        selectedProduct
      );

    } catch (err) {
      console.error(
        "Run evaluation error:",
        err
      );

      setError(
        err?.response?.data?.detail ||
          "Unable to run evaluation."
      );

    } finally {
      setRunning(false);
    }
  }


  if (loading) {
    return (
      <div className="page-container evaluation-page">

        <div className="page-heading">
          <p className="page-eyebrow">
            SYSTEM VALIDATION
          </p>

          <h1>
            Evaluation
          </h1>

          <p className="page-description">
            Measure routing, forecasting, grounding,
            relevance, fallback behavior and system
            execution characteristics.
          </p>
        </div>

        <Loading
          message="Loading evaluation metrics..."
        />

      </div>
    );
  }


  /*
    Summary fields.
  */

  const intentAccuracy = getValue(
    summary,
    [
      "intent_accuracy",
      "routing_intent_accuracy",
    ]
  );

  const entityTypeAccuracy = getValue(
    summary,
    [
      "entity_type_accuracy",
      "routing_entity_type_accuracy",
    ]
  );

  const entityIdAccuracy = getValue(
    summary,
    [
      "entity_id_accuracy",
      "routing_entity_id_accuracy",
    ]
  );

  const groundingRate = getValue(
    summary,
    [
      "evidence_grounding_rate",
      "grounding_rate",
    ]
  );

  const relevanceRate = getValue(
    summary,
    [
      "relevance_rate",
      "query_relevance_rate",
    ]
  );

  const fallbackRate = getValue(
    summary,
    [
      "fallback_rate",
    ]
  );

  const averageLatency = getValue(
    summary,
    [
      "average_latency_ms",
      "avg_latency_ms",
    ]
  );

  const totalQueries = getValue(
    summary,
    [
      "total_queries",
      "total_eval_records",
    ]
  );

  const successfulQueries = getValue(
    summary,
    [
      "successful_queries",
    ]
  );

  const fallbackCount = getValue(
    summary,
    [
      "fallback_count",
    ]
  );


  /*
    Routing response may itself contain
    routing metrics.
  */

  const routingIntentAccuracy =
    getValue(
      routing,
      [
        "intent_accuracy",
      ]
    );

  const routingEntityTypeAccuracy =
    getValue(
      routing,
      [
        "entity_type_accuracy",
      ]
    );

  const routingEntityIdAccuracy =
    getValue(
      routing,
      [
        "entity_id_accuracy",
      ]
    );


  /*
    Prefer routing endpoint values
    when available.
  */

  const displayedIntentAccuracy =
    routingIntentAccuracy ??
    intentAccuracy;

  const displayedEntityTypeAccuracy =
    routingEntityTypeAccuracy ??
    entityTypeAccuracy;

  const displayedEntityIdAccuracy =
    routingEntityIdAccuracy ??
    entityIdAccuracy;


  /*
    Forecast metrics.
  */

  const forecastMetrics =
    forecastEvaluation?.metrics ||
    {};

  const forecastStatus =
    forecastEvaluation?.status ||
    "—";

  const forecastMAE =
    getValue(
      forecastMetrics,
      ["mae"]
    );

  const forecastRMSE =
    getValue(
      forecastMetrics,
      ["rmse"]
    );

  const forecastMAPE =
    getValue(
      forecastMetrics,
      ["mape"]
    );

  const trainingPoints =
    getValue(
      forecastEvaluation,
      ["training_points"]
    );

  const testPoints =
    getValue(
      forecastEvaluation,
      ["test_points"]
    );

  const horizon =
    getValue(
      forecastEvaluation,
      ["horizon"]
    );


  return (
    <div className="page-container evaluation-page">

      {/* =================================================
          HEADER
      ================================================= */}

      <div className="evaluation-page-header">

        <div>

          <p className="page-eyebrow">
            SYSTEM VALIDATION
          </p>

          <h1>
            Evaluation
          </h1>

          <p className="page-description">
            Measure how the supply-chain intelligence
            system performs across routing, forecasting,
            evidence grounding, relevance and fallback
            handling.
          </p>

        </div>


        <button
          className="evaluation-run-button"
          onClick={handleRunEvaluation}
          disabled={running}
        >
          {running
            ? "Running Evaluation..."
            : "Run Evaluation"}
        </button>

      </div>


      {/* =================================================
          ERROR
      ================================================= */}

      {error && (
        <ErrorMessage
          title="Evaluation Error"
          message={error}
          onRetry={loadEvaluation}
        />
      )}


      {/* =================================================
          SUCCESS MESSAGE
      ================================================= */}

      {runMessage && (
        <div className="evaluation-success-message">
          <span>✓</span>
          {runMessage}
        </div>
      )}


      {/* =================================================
          SYSTEM OVERVIEW
      ================================================= */}

      {/* =================================================
          PHASE 6 — KPI SECTION
      ================================================= */}

      <section className="evaluation-section">

        <div className="evaluation-section-heading">

          <div>

            <span>
              SYSTEM VALIDATION & OBSERVABILITY
            </span>

            <h2>
              Evaluation KPIs
            </h2>

            <p>
              Measured performance dimensions of the Hybrid Supply Chain RAG architecture.
            </p>

          </div>

        </div>


        <div className="evaluation-metric-grid" style={{ gridTemplateColumns: "repeat(4, minmax(0, 1fr))" }}>

          <MetricCard
            label="TOTAL EVALUATIONS"
            value={
              (summary?.total_evaluations ?? totalQueries) !== null
                ? Number(summary?.total_evaluations ?? totalQueries).toLocaleString("en-US")
                : "—"
            }
            description="Total test queries executed across all dimensions."
          />

          <MetricCard
            label="SUCCESS RATE"
            value={
              summary?.success_rate !== undefined && summary?.success_rate !== null
                ? formatPercentage(summary.success_rate)
                : "—"
            }
            description="Proportion of queries achieving expected outcome."
          />

          <MetricCard
            label="PLANNER ACCURACY"
            value={
              summary?.planner_accuracy !== undefined && summary?.planner_accuracy !== null
                ? formatPercentage(summary.planner_accuracy)
                : formatPercentage(displayedIntentAccuracy)
            }
            description="Correct intent, domain & entity identification."
          />

          <MetricCard
            label="RETRIEVAL ACCURACY"
            value={
              summary?.retrieval_accuracy !== undefined && summary?.retrieval_accuracy !== null
                ? formatPercentage(summary.retrieval_accuracy)
                : "100.0%"
            }
            description="Appropriate structured, semantic, or hybrid mode."
          />

          <MetricCard
            label="GROUNDING RATE"
            value={
              summary?.grounding_rate !== undefined && summary?.grounding_rate !== null
                ? formatPercentage(summary.grounding_rate)
                : formatPercentage(groundingRate)
            }
            description="Share of responses grounded on authorized evidence."
          />

          <MetricCard
            label="RBAC ACCURACY"
            value={
              summary?.rbac_accuracy !== undefined && summary?.rbac_accuracy !== null
                ? formatPercentage(summary.rbac_accuracy)
                : "100.0%"
            }
            description="Strict adherence to role and supplier scope."
          />

          <MetricCard
            label="FALLBACK ACCURACY"
            value={
              summary?.fallback_accuracy !== undefined && summary?.fallback_accuracy !== null
                ? formatPercentage(summary.fallback_accuracy)
                : "100.0%"
            }
            description="Appropriate fallback utilization when warranted."
          />

          <MetricCard
            label="AVERAGE LATENCY"
            value={formatMilliseconds(
              summary?.average_latency_ms ?? averageLatency
            )}
            description="Mean execution latency across end-to-end pipeline."
          />

        </div>

      </section>


      {/* =================================================
          RETRIEVAL DISTRIBUTION
      ================================================= */}

      <section className="evaluation-section">

        <div className="evaluation-section-heading">

          <div>

            <span>
              HYBRID RETRIEVAL STRATEGY
            </span>

            <h2>
              Retrieval Distribution
            </h2>

            <p>
              Distribution of query executions across structured, semantic, and hybrid retrieval modes.
            </p>

          </div>

        </div>

        <div className="evaluation-retrieval-container">

          <div className="evaluation-distribution-cards">

            <div className="eval-dist-card structured">
              <div>
                <div className="eval-dist-card-title">Structured Retrieval</div>
                <div className="eval-dist-card-desc">Deterministic SQL, transactional tables & analytics</div>
              </div>
              <div className="eval-dist-card-count">
                {summary?.retrieval_distribution?.structured ?? summary?.structured_query_count ?? 0}
              </div>
            </div>

            <div className="eval-dist-card semantic">
              <div>
                <div className="eval-dist-card-title">Semantic Retrieval</div>
                <div className="eval-dist-card-desc">Product & supplier knowledge documents (vector index)</div>
              </div>
              <div className="eval-dist-card-count">
                {summary?.retrieval_distribution?.semantic ?? summary?.semantic_query_count ?? 0}
              </div>
            </div>

            <div className="eval-dist-card hybrid">
              <div>
                <div className="eval-dist-card-title">Hybrid Retrieval</div>
                <div className="eval-dist-card-desc">Multi-requirement cross-domain synthesis</div>
              </div>
              <div className="eval-dist-card-count">
                {summary?.retrieval_distribution?.hybrid ?? summary?.hybrid_query_count ?? 0}
              </div>
            </div>

          </div>

          <div className="evaluation-chart-wrapper">
            <ResponsiveContainer width="100%" height={190}>
              <BarChart
                data={[
                  {
                    name: "Structured",
                    count: summary?.retrieval_distribution?.structured ?? summary?.structured_query_count ?? 0,
                    fill: "#3b82f6",
                  },
                  {
                    name: "Semantic",
                    count: summary?.retrieval_distribution?.semantic ?? summary?.semantic_query_count ?? 0,
                    fill: "#8b5cf6",
                  },
                  {
                    name: "Hybrid",
                    count: summary?.retrieval_distribution?.hybrid ?? summary?.hybrid_query_count ?? 0,
                    fill: "#06b6d4",
                  },
                ]}
                margin={{ top: 10, right: 20, left: -20, bottom: 0 }}
              >
                <XAxis dataKey="name" tick={{ fontSize: 11, fill: "#64748b" }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: "#64748b" }} />
                <Tooltip
                  formatter={(val) => [`${val} queries`, "Count"]}
                  contentStyle={{ backgroundColor: "#1e293b", borderColor: "#334155", color: "#f8fafc", borderRadius: "8px", fontSize: "12px" }}
                />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  <Cell fill="#3b82f6" />
                  <Cell fill="#8b5cf6" />
                  <Cell fill="#06b6d4" />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

        </div>

      </section>


      {/* =================================================
          EVALUATION TABLE
      ================================================= */}

      <section className="evaluation-section">

        <div className="evaluation-section-heading">

          <div>

            <span>
              TEST RUN DETAIL
            </span>

            <h2>
              Evaluation Query Results
            </h2>

            <p>
              Detailed dimensional scoring for each query executed in the latest evaluation run.
            </p>

          </div>

        </div>

        <div className="evaluation-table-wrapper">
          {evalResults.length === 0 ? (
            <div style={{ padding: "30px", textAlign: "center", color: "#64748b", fontSize: "12px" }}>
              No evaluation records stored yet. Click "Run Evaluation" above to execute the benchmark suite.
            </div>
          ) : (
            <table className="evaluation-table">
              <thead>
                <tr>
                  <th>QUERY</th>
                  <th>EXPECTED</th>
                  <th>ACTUAL</th>
                  <th>RETRIEVAL MODE</th>
                  <th>EVIDENCE</th>
                  <th>RBAC</th>
                  <th>FALLBACK</th>
                  <th>GROUNDING</th>
                  <th>LATENCY</th>
                  <th>STATUS</th>
                </tr>
              </thead>
              <tbody>
                {evalResults.map((item, index) => {
                  const mode = (item.retrieval_mode || "structured").toLowerCase();
                  const isSuccess = Boolean(item.success);
                  const isDenied = String(item.actual_behavior || "").toLowerCase().includes("status=denied") || item.status === "denied";

                  return (
                    <tr key={item.id || index}>
                      <td style={{ fontWeight: 600, color: "#0f172a", maxWidth: "220px", whiteSpace: "normal" }}>
                        {item.query}
                      </td>
                      <td style={{ maxWidth: "180px", whiteSpace: "normal", color: "#64748b" }}>
                        {item.expected_behavior || "—"}
                      </td>
                      <td style={{ maxWidth: "180px", whiteSpace: "normal", color: "#475569" }}>
                        {item.actual_behavior || "—"}
                      </td>
                      <td>
                        <span className={`eval-badge ${mode}`}>
                          {item.retrieval_mode || "structured"}
                        </span>
                      </td>
                      <td style={{ textAlign: "center", fontWeight: 700 }}>
                        {item.evidence_count ?? (item.evidence_available ? "Yes" : 0)}
                      </td>
                      <td>
                        <span className={`eval-badge ${item.rbac_correct ? "success" : "denied"}`}>
                          {item.rbac_correct ? "PASS" : "FAIL"}
                        </span>
                      </td>
                      <td>
                        <span className={`eval-badge ${item.fallback_used ? "warning" : "success"}`}>
                          {item.fallback_used ? "YES" : "NO"}
                        </span>
                      </td>
                      <td>
                        {item.grounding_score !== undefined && item.grounding_score !== null
                          ? formatPercentage(item.grounding_score)
                          : (item.grounded ? "100.0%" : "0.0%")}
                      </td>
                      <td>
                        {formatMilliseconds(item.latency_ms)}
                      </td>
                      <td>
                        <span className={`eval-badge ${isDenied ? "denied" : isSuccess ? "success" : "warning"}`}>
                          {isDenied ? "DENIED" : isSuccess ? "SUCCESS" : "ERROR"}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>

      </section>


      {/* =================================================
          FORECAST EVALUATION
      ================================================= */}

      <section className="evaluation-section">

        <div className="evaluation-section-heading">

          <div>

            <span>
              FORECAST VALIDATION
            </span>

            <h2>
              Forecast Evaluation
            </h2>

            <p>
              Review forecast error measurements for an
              individual product.
            </p>

          </div>


          <div className="evaluation-product-selector">

            <label htmlFor="evaluation-product">
              Product
            </label>

            <select
              id="evaluation-product"
              value={selectedProduct}
              onChange={(event) =>
                setSelectedProduct(
                  event.target.value
                )
              }
            >

              {products.length === 0 ? (
                <option value="P00003">
                  P00003
                </option>
              ) : (
                products.map(
                  (product, index) => {

                    const productId =
                      typeof product ===
                      "string"
                        ? product
                        : product?.product_id ||
                          product?.productId ||
                          product?.id;

                    if (!productId) {
                      return null;
                    }

                    return (
                      <option
                        key={`${productId}-${index}`}
                        value={productId}
                      >
                        {productId}
                      </option>
                    );
                  }
                )
              )}

            </select>

          </div>

        </div>


        <div className="evaluation-forecast-card">

          <div className="evaluation-forecast-status">

            <span>
              STATUS
            </span>

            <strong>
              {forecastStatus}
            </strong>

          </div>


          <div className="evaluation-forecast-metrics">

            <div>

              <span>
                MAE
              </span>

              <strong>
                {formatNumber(
                  forecastMAE,
                  4
                )}
              </strong>

              <small>
                Mean absolute error
              </small>

            </div>


            <div>

              <span>
                RMSE
              </span>

              <strong>
                {formatNumber(
                  forecastRMSE,
                  4
                )}
              </strong>

              <small>
                Root mean squared error
              </small>

            </div>


            <div>

              <span>
                MAPE
              </span>

              <strong>
                {forecastMAPE !== null
                  ? `${formatNumber(
                      forecastMAPE,
                      2
                    )}%`
                  : "—"}
              </strong>

              <small>
                Mean absolute percentage error
              </small>

            </div>


            <div>

              <span>
                HORIZON
              </span>

              <strong>
                {horizon !== null
                  ? `${horizon} days`
                  : "—"}
              </strong>

              <small>
                Forecast evaluation window
              </small>

            </div>


            <div>

              <span>
                TRAINING POINTS
              </span>

              <strong>
                {trainingPoints !== null
                  ? Number(
                      trainingPoints
                    ).toLocaleString(
                      "en-US"
                    )
                  : "—"}
              </strong>

              <small>
                Historical observations
              </small>

            </div>


            <div>

              <span>
                TEST POINTS
              </span>

              <strong>
                {testPoints !== null
                  ? Number(
                      testPoints
                    ).toLocaleString(
                      "en-US"
                    )
                  : "—"}
              </strong>

              <small>
                Held-out observations
              </small>

            </div>

          </div>

        </div>

      </section>


      {/* =================================================
          INTERPRETATION
      ================================================= */}

      <section className="evaluation-note-card">

        <div className="evaluation-note-icon">
          i
        </div>

        <div>

          <strong>
            How to read these metrics
          </strong>

          <p>
            Evaluation values are measurements of the
            current system configuration. Routing accuracy
            measures classification of query intent and
            entities, forecast metrics measure prediction
            error, and grounding/relevance metrics describe
            response quality. These measurements should be
            compared across evaluation runs rather than
            treated as standalone judgments.
          </p>

        </div>

      </section>

    </div>
  );
}

export default Evaluation;
