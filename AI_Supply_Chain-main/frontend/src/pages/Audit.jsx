import { useEffect, useState } from "react";

import { getRecentAuditLogs } from "../api/auditApi";

import Loading from "../components/Loading";
import ErrorMessage from "../components/ErrorMessage";
import EmptyState from "../components/EmptyState";


function getValue(item, keys, fallback = "—") {
  if (!item || typeof item !== "object") {
    return fallback;
  }

  for (const key of keys) {
    if (
      item[key] !== undefined &&
      item[key] !== null &&
      item[key] !== ""
    ) {
      return item[key];
    }
  }

  return fallback;
}


function formatTimestamp(value) {
  if (!value || value === "—") {
    return "—";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return String(value);
  }

  return date.toLocaleString("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}


function formatLatency(value) {
  const number = Number(value);

  if (!Number.isFinite(number)) {
    return "—";
  }

  return `${number.toFixed(0)} ms`;
}


function parseJsonLike(value) {
  if (typeof value !== "string") {
    return null;
  }

  const trimmed = value.trim();

  if (!trimmed) {
    return null;
  }

  try {
    return JSON.parse(trimmed);
  } catch {
    return null;
  }
}


function normalizeAuditResponse(data) {
  if (Array.isArray(data)) {
    return data;
  }

  if (Array.isArray(data?.logs)) {
    return data.logs;
  }

  if (Array.isArray(data?.audit_logs)) {
    return data.audit_logs;
  }

  if (Array.isArray(data?.records)) {
    return data.records;
  }

  if (Array.isArray(data?.data)) {
    return data.data;
  }

  if (Array.isArray(data?.results)) {
    return data.results;
  }

  return [];
}


function Audit() {
  const [logs, setLogs] = useState([]);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState("");


  async function loadAuditLogs() {
    try {
      setLoading(true);
      setError("");

      const result =
        await getRecentAuditLogs();

      console.log(
        "AUDIT RESPONSE:",
        result
      );

      setLogs(
        normalizeAuditResponse(
          result
        )
      );

    } catch (err) {
      console.error(
        "Audit loading error:",
        err
      );

      setError(
        err?.response?.data?.detail ||
          "Unable to load audit records."
      );

    } finally {
      setLoading(false);
    }
  }


  useEffect(() => {
    loadAuditLogs();
  }, []);


  if (loading) {
    return (
      <div className="page-container audit-page">

        <div className="page-heading">

          <p className="page-eyebrow">
            TRACEABILITY
          </p>

          <h1>
            Audit
          </h1>

          <p className="page-description">
            Review recent AI interactions and system
            execution metadata.
          </p>

        </div>

        <Loading
          message="Loading audit records..."
        />

      </div>
    );
  }


  return (
    <div className="page-container audit-page">

      {/* =================================================
          HEADER
      ================================================= */}

      <div className="audit-page-header">

        <div>

          <p className="page-eyebrow">
            TRACEABILITY
          </p>

          <h1>
            Audit
          </h1>

          <p className="page-description">
            Review recent AI interactions, processing
            status, fallback behavior and execution
            metadata.
          </p>

        </div>


        <button
          className="audit-refresh-button"
          onClick={loadAuditLogs}
        >
          ↻ Refresh
        </button>

      </div>


      {/* =================================================
          ERROR
      ================================================= */}

      {error && (
        <ErrorMessage
          title="Audit Data Unavailable"
          message={error}
          onRetry={loadAuditLogs}
        />
      )}


      {/* =================================================
          SUMMARY
      ================================================= */}

      {!error && (
        <div className="audit-summary-grid">

          <div className="audit-summary-card">

            <span>
              RECORDS SHOWN
            </span>

            <strong>
              {logs.length.toLocaleString(
                "en-US"
              )}
            </strong>

            <p>
              Recent audit records returned by
              the backend.
            </p>

          </div>


          <div className="audit-summary-card">

            <span>
              TRACEABILITY
            </span>

            <strong>
              Enabled
            </strong>

            <p>
              Query processing metadata is exposed
              through the audit endpoint.
            </p>

          </div>


          <div className="audit-summary-card">

            <span>
              DATA SOURCE
            </span>

            <strong>
              Backend
            </strong>

            <p>
              Records are loaded through the REST API.
            </p>

          </div>

        </div>
      )}


      {/* =================================================
          EMPTY
      ================================================= */}

      {!error &&
        logs.length === 0 && (

          <section className="audit-table-card">

            <EmptyState
              title="No audit records available"
              message="The audit endpoint returned no recent records. This can occur when no interactions have been persisted yet."
            />

          </section>

        )}


      {/* =================================================
          TABLE
      ================================================= */}

      {!error &&
        logs.length > 0 && (

          <section className="audit-table-card">

            <div className="audit-table-header">

              <div>

                <span>
                  RECENT ACTIVITY
                </span>

                <h2>
                  Audit Trail
                </h2>

              </div>

              <span className="audit-record-count">
                {logs.length} records
              </span>

            </div>


            <div className="audit-table-wrapper">

              <table className="audit-table">

                <thead>

                  <tr>

                    <th>
                      Timestamp
                    </th>

                    <th>
                      Query / Action
                    </th>

                    <th>
                      Intent
                    </th>

                    <th>
                      Status
                    </th>

                    <th>
                      Fallback
                    </th>

                    <th>
                      Latency
                    </th>

                  </tr>

                </thead>


                <tbody>

                  {logs.map(
                    (item, index) => {

                      const timestamp =
                        getValue(
                          item,
                          [
                            "timestamp",
                            "created_at",
                            "createdAt",
                            "time",
                            "datetime",
                          ]
                        );

                      const parsedInput = parseJsonLike(item?.input_data);
                      const parsedOutput = parseJsonLike(item?.output_data);

                      const query =
                        getValue(
                          item,
                          [
                            "query",
                            "question",
                            "action",
                            "request",
                          ]
                        ) ||
                        getValue(
                          parsedInput,
                          [
                            "query",
                            "question",
                            "action",
                            "request",
                          ]
                        ) ||
                        "—";

                      const intent =
                        getValue(
                          item,
                          [
                            "intent",
                            "query_intent",
                            "agent_name",
                          ]
                        ) ||
                        getValue(
                          parsedOutput,
                          [
                            "intent",
                            "query_intent",
                          ]
                        ) ||
                        getValue(
                          parsedInput,
                          [
                            "intent",
                            "query_intent",
                          ],
                          "—"
                        );

                      const status =
                        getValue(
                          item,
                          [
                            "status",
                            "result_status",
                          ]
                        ) ||
                        getValue(
                          parsedOutput,
                          [
                            "status",
                            "result_status",
                          ]
                        ) ||
                        getValue(
                          parsedInput,
                          [
                            "status",
                            "result_status",
                          ],
                          "success"
                        );

                      const fallback =
                        getValue(
                          item,
                          [
                            "fallback_used",
                            "fallback",
                          ],
                          false
                        ) ||
                        getValue(
                          parsedOutput,
                          [
                            "fallback_used",
                            "fallback",
                          ],
                          false
                        );

                      const latency =
                        getValue(
                          item,
                          [
                            "latency_ms",
                            "latency",
                            "execution_time_ms",
                          ]
                        ) ||
                        getValue(
                          parsedOutput,
                          [
                            "latency_ms",
                            "latency",
                            "execution_time_ms",
                          ]
                        );


                      return (
                        <tr
                          key={
                            item.id ||
                            item.audit_id ||
                            index
                          }
                        >

                          <td>
                            <span className="audit-timestamp">
                              {formatTimestamp(
                                timestamp
                              )}
                            </span>
                          </td>


                          <td>
                            <div className="audit-query-cell">

                              <strong>
                                {String(
                                  query
                                )}
                              </strong>

                            </div>
                          </td>


                          <td>
                            <span className="audit-intent">
                              {String(
                                intent
                              ).replaceAll(
                                "_",
                                " "
                              )}
                            </span>
                          </td>


                          <td>

                            <span
                              className={`audit-status audit-status-${String(
                                status
                              ).toLowerCase()}`}
                            >
                              {String(
                                status
                              )}
                            </span>

                          </td>


                          <td>

                            <span
                              className={
                                Boolean(
                                  fallback
                                )
                                  ? "audit-fallback yes"
                                  : "audit-fallback no"
                              }
                            >
                              {Boolean(
                                fallback
                              )
                                ? "Used"
                                : "No"}
                            </span>

                          </td>


                          <td>
                            {formatLatency(
                              latency
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

        )}

    </div>
  );
}

export default Audit;
