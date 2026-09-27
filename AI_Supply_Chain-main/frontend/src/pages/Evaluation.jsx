import { useEffect, useState } from "react";

import {
  getEvaluationSummary,
  getRoutingEvaluation,
  getForecastEvaluation,
  runEvaluation,
} from "../api/evaluationApi";

import {
  getForecastProducts,
} from "../api/forecastApi";

import Loading from "../components/Loading";
import ErrorMessage from "../components/ErrorMessage";


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
      ] = await Promise.all([
        getEvaluationSummary(),
        getRoutingEvaluation(),
        getForecastProducts(),
      ]);

      setSummary(summaryResult);
      setRouting(routingResult);

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

      <section className="evaluation-section">

        <div className="evaluation-section-heading">

          <div>

            <span>
              SYSTEM OVERVIEW
            </span>

            <h2>
              Evaluation Summary
            </h2>

            <p>
              Current evaluation measurements returned
              by the backend evaluation service.
            </p>

          </div>

        </div>


        <div className="evaluation-metric-grid">

          <MetricCard
            label="TOTAL QUERIES"
            value={
              totalQueries !== null
                ? Number(
                    totalQueries
                  ).toLocaleString("en-US")
                : "—"
            }
            description="Queries included in the current evaluation run."
          />


          <MetricCard
            label="SUCCESSFUL QUERIES"
            value={
              successfulQueries !== null
                ? Number(
                    successfulQueries
                  ).toLocaleString("en-US")
                : "—"
            }
            description="Queries completed without fallback."
          />


          <MetricCard
            label="FALLBACK COUNT"
            value={
              fallbackCount !== null
                ? Number(
                    fallbackCount
                  ).toLocaleString("en-US")
                : "—"
            }
            description="Queries handled through fallback behavior."
          />


          <MetricCard
            label="AVERAGE LATENCY"
            value={formatMilliseconds(
              averageLatency
            )}
            description="Average query execution time."
          />

        </div>

      </section>


      {/* =================================================
          ROUTING
      ================================================= */}

      <section className="evaluation-section">

        <div className="evaluation-section-heading">

          <div>

            <span>
              QUERY ROUTING
            </span>

            <h2>
              Intent & Entity Resolution
            </h2>

            <p>
              Measures how accurately the system identifies
              the query intent and requested entity.
            </p>

          </div>

        </div>


        <div className="evaluation-metric-grid">

          <MetricCard
            label="INTENT ACCURACY"
            value={formatPercentage(
              displayedIntentAccuracy
            )}
            description="Correct identification of the requested analytical intent."
          />


          <MetricCard
            label="ENTITY TYPE ACCURACY"
            value={formatPercentage(
              displayedEntityTypeAccuracy
            )}
            description="Correct identification of the entity category."
          />


          <MetricCard
            label="ENTITY ID ACCURACY"
            value={formatPercentage(
              displayedEntityIdAccuracy
            )}
            description="Correct identification of a specific entity when required."
          />

        </div>

      </section>


      {/* =================================================
          QUALITY METRICS
      ================================================= */}

      <section className="evaluation-section">

        <div className="evaluation-section-heading">

          <div>

            <span>
              RESPONSE QUALITY
            </span>

            <h2>
              Evidence & Response Metrics
            </h2>

            <p>
              Measurements describing grounding, relevance
              and fallback behavior.
            </p>

          </div>

        </div>


        <div className="evaluation-metric-grid">

          <MetricCard
            label="EVIDENCE GROUNDING"
            value={formatPercentage(
              groundingRate
            )}
            description="Share of evaluated responses supported by retrieved evidence."
          />


          <MetricCard
            label="RELEVANCE RATE"
            value={formatPercentage(
              relevanceRate
            )}
            description="Measured relevance of responses to the submitted queries."
          />


          <MetricCard
            label="FALLBACK RATE"
            value={formatPercentage(
              fallbackRate
            )}
            description="Share of evaluated queries handled through fallback behavior."
          />

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
