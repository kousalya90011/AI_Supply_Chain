import { useState } from "react";

import { askSupplyChainQuery } from "../api/queryApi";

import Loading from "../components/Loading";
import ErrorMessage from "../components/ErrorMessage";


/* =========================================================
   GENERIC HELPERS
========================================================= */

function getEvidenceValue(item, keys) {
  if (!item || typeof item !== "object") {
    return undefined;
  }

  const record = item.data && typeof item.data === "object"
    ? item.data
    : item.raw && typeof item.raw === "object"
      ? item.raw
      : item;

  for (const key of keys) {
    if (
      item[key] !== undefined &&
      item[key] !== null
    ) {
      return item[key];
    }

    if (
      record[key] !== undefined &&
      record[key] !== null
    ) {
      return record[key];
    }
  }

  return undefined;
}


function safeNumber(value) {
  const number = Number(value);

  return Number.isFinite(number)
    ? number
    : null;
}

function buildEvidenceReason(item) {
  if (!item || typeof item !== "object") {
    return "This record contains operational values that support the current supply-chain conclusion.";
  }

  const record = item.data && typeof item.data === "object" ? item.data : item.raw && typeof item.raw === "object" ? item.raw : item;

  const product = getEvidenceValue(item, [
    "product_id",
    "productId",
  ]);

  const supplier = getEvidenceValue(item, [
    "supplier_id",
    "supplierId",
  ]);

  const supplierName = getEvidenceValue(item, [
    "supplier_name",
    "supplierName",
  ]);

  const riskLevel = getEvidenceValue(item, [
    "risk_level",
    "riskLevel",
  ]);

  const riskScore = getEvidenceValue(item, [
    "risk_score",
    "riskScore",
  ]);

  const unitCost = getEvidenceValue(item, [
    "unit_cost",
    "unitCost",
  ]);

  const totalOrders = getEvidenceValue(item, [
    "total_orders",
    "totalOrders",
    "order_count",
    "orderCount",
  ]);

  const lateRate = getEvidenceValue(item, [
    "late_rate",
    "lateRate",
  ]);

  if (product && supplier) {
    return `This record links ${product} to supplier ${supplier}${supplierName ? ` (${supplierName})` : ""}, which explains the sourcing relationship behind the result.`;
  }

  if (product && unitCost !== undefined) {
    return `This record shows ${product} at $${safeNumber(unitCost)?.toFixed(2) ?? unitCost} per unit, which is the basis for the product cost ranking.`;
  }

  if (product && totalOrders !== undefined) {
    return `This record shows ${totalOrders} orders for ${product}, which explains the volume driving the order analysis.`;
  }

  if (product && (riskLevel !== undefined || riskScore !== undefined)) {
    const riskText = riskLevel
      ? String(riskLevel).toUpperCase()
      : riskScore !== undefined
        ? `score ${safeNumber(riskScore)?.toFixed(2) ?? riskScore}`
        : "risk signal";

    return `This record shows ${product} has a ${riskText} risk signal, driven by the inventory and demand metrics in the underlying evidence.`;
  }

  if (riskLevel !== undefined || riskScore !== undefined) {
    const riskText = riskLevel
      ? String(riskLevel).toUpperCase()
      : riskScore !== undefined
        ? `score ${safeNumber(riskScore)?.toFixed(2) ?? riskScore}`
        : "risk signal";

    return `This record reflects a ${riskText} signal in the underlying supply-chain data, which is why it is included in the risk assessment.`;
  }

  if (supplier && lateRate !== undefined) {
    return `This supplier record shows a late-rate of ${(Number(lateRate) * 100).toFixed(2)}%, which explains the supplier risk conclusion.`;
  }

  if (product) {
    return `This record shows ${product} is operating under the current inventory conditions and is directly relevant to the risk conclusion.`;
  }

  if (supplier) {
    return `This record reflects the operational status for supplier ${supplier}${supplierName ? ` (${supplierName})` : ""}, which is directly relevant to the current analysis.`;
  }

  if (record && typeof record === "object") {
    const keyFacts = Object.entries(record)
      .slice(0, 3)
      .map(([key, value]) => `${key}=${value}`)
      .join(" | ");

    return keyFacts
      ? `This record contains the underlying operational values used to support the conclusion: ${keyFacts}.`
      : "This record contains operational values that support the current supply-chain conclusion.";
  }

  return "This record contains operational values that support the current supply-chain conclusion.";
}

function summarizeEvidenceFocus(response, evidence) {
  if (!response || !Array.isArray(response.requirement_results)) {
    return null;
  }

  const supplierRecord = evidence.find((item) => {
    const raw = item?.data || item?.raw || {};
    return raw.product_id && raw.supplier_id;
  });

  const orderRecord = evidence.find((item) => {
    const raw = item?.data || item?.raw || {};
    return raw.total_orders !== undefined || raw.totalOrders !== undefined || raw.order_count !== undefined || raw.orderCount !== undefined;
  });

  const productId =
    getEvidenceValue(supplierRecord, ["product_id", "productId"]) ||
    getEvidenceValue(evidence[0], ["product_id", "productId"]) ||
    null;

  const supplierId = getEvidenceValue(supplierRecord, ["supplier_id", "supplierId"]) || null;
  const supplierName = getEvidenceValue(supplierRecord, ["supplier_name", "supplierName"]) || null;
  const orderCount =
    getEvidenceValue(orderRecord, ["total_orders", "totalOrders", "order_count", "orderCount"]) ??
    null;

  if (!productId && !supplierId && orderCount === null) {
    return null;
  }

  const parts = [];

  if (productId) {
    parts.push(productId);
  }

  if (supplierId) {
    const supplierLabel = supplierName ? `${supplierId} (${supplierName})` : supplierId;
    parts.push(`supplier ${supplierLabel}`);
  }

  if (orderCount !== null) {
    parts.push(`${Number(orderCount).toLocaleString("en-US")} orders`);
  }

  if (parts.length === 0) {
    return null;
  }

  return `Most relevant evidence chain: ${parts.join(" → ")}`;
}

function buildEvidenceProof(item) {
  if (!item || typeof item !== "object") {
    return "No record values were returned for this evidence item.";
  }

  const raw = item.raw || item;

  const facts = [];

  const product = getEvidenceValue(raw, ["product_id", "productId"]);
  const supplier = getEvidenceValue(raw, ["supplier_id", "supplierId"]);
  const supplierName = getEvidenceValue(raw, ["supplier_name", "supplierName"]);
  const riskLevel = getEvidenceValue(raw, ["risk_level", "riskLevel"]);
  const riskScore = getEvidenceValue(raw, ["risk_score", "riskScore"]);
  const unitCost = getEvidenceValue(raw, ["unit_cost", "unitCost"]);
  const totalOrders = getEvidenceValue(raw, ["total_orders", "totalOrders", "order_count", "orderCount"]);
  const stockoutRate = getEvidenceValue(raw, ["stockout_rate", "stockoutRate"]);
  const lateRate = getEvidenceValue(raw, ["late_rate", "lateRate"]);
  const delay = getEvidenceValue(raw, ["avg_delay_days", "average_delay", "average_delay_days", "avgDelayDays"]);

  if (product) {
    facts.push(`product ${product}`);
  }

  if (supplier) {
    facts.push(`supplier ${supplier}${supplierName ? ` (${supplierName})` : ""}`);
  }

  if (riskLevel !== undefined) {
    facts.push(`risk level ${String(riskLevel).toUpperCase()}`);
  }

  if (riskScore !== undefined) {
    const score = safeNumber(riskScore);
    facts.push(`risk score ${score !== null ? score.toFixed(2) : riskScore}`);
  }

  if (unitCost !== undefined) {
    const cost = safeNumber(unitCost);
    facts.push(`unit cost ${cost !== null ? `$${cost.toFixed(2)}` : unitCost}`);
  }

  if (totalOrders !== undefined) {
    const orders = safeNumber(totalOrders);
    facts.push(`total orders ${orders !== null ? orders.toLocaleString("en-US") : totalOrders}`);
  }

  if (stockoutRate !== undefined) {
    const rate = safeNumber(stockoutRate);
    facts.push(`stockout rate ${rate !== null ? `${(rate * 100).toFixed(2)}%` : stockoutRate}`);
  }

  if (lateRate !== undefined) {
    const rate = safeNumber(lateRate);
    facts.push(`late rate ${rate !== null ? `${(rate * 100).toFixed(2)}%` : lateRate}`);
  }

  if (delay !== undefined) {
    const value = safeNumber(delay);
    facts.push(`average delay ${value !== null ? `${value.toFixed(2)} days` : delay}`);
  }

  if (facts.length === 0) {
    return "This evidence record contains operational values that directly support the current supply-chain conclusion.";
  }

  return `Proof data: ${facts.join(" • ")}.`;
}


/* =========================================================
   NORMALIZE EVIDENCE
========================================================= */

function normalizeEvidence(evidence) {
  if (!Array.isArray(evidence)) {
    return [];
  }

  return evidence.map((item, index) => {
    if (typeof item === "string") {
      return {
        id: index + 1,
        title: `Evidence ${index + 1}`,
        riskLevel: null,
        riskScore: null,
        metrics: [],
        reason: item,
        raw: item,
      };
    }

    const record = item.data && typeof item.data === "object" ? item.data : item.raw && typeof item.raw === "object" ? item.raw : item;

    const provider = getEvidenceValue(item, [
      "three_pl",
      "3pl",
      "provider",
      "provider_id",
      "provider_name",
    ]);

    const product = getEvidenceValue(item, [
      "product_id",
      "productId",
    ]);

    const supplier = getEvidenceValue(item, [
      "supplier_id",
      "supplierId",
    ]);

    const supplierName = getEvidenceValue(item, [
      "supplier_name",
      "supplierName",
    ]);

    const route = getEvidenceValue(item, [
      "route_id",
      "routeId",
    ]);

    const riskScore = getEvidenceValue(item, [
      "risk_score",
      "riskScore",
    ]);

    const riskLevel = getEvidenceValue(item, [
      "risk_level",
      "riskLevel",
    ]);

    const lateRate = getEvidenceValue(item, [
      "late_rate",
      "lateRate",
    ]);

    const delay = getEvidenceValue(item, [
      "avg_delay_days",
      "average_delay",
      "average_delay_days",
      "avgDelayDays",
    ]);

    const stockoutRate = getEvidenceValue(item, [
      "stockout_rate",
      "stockoutRate",
    ]);

    const daysOfCover = getEvidenceValue(item, [
      "days_of_cover",
      "daysOfCover",
    ]);

    const demandPressure = getEvidenceValue(item, [
      "demand_pressure",
      "demandPressure",
    ]);

    const totalOrders = getEvidenceValue(item, [
      "total_orders",
      "totalOrders",
    ]);

    const totalUnits = getEvidenceValue(item, [
      "total_units",
      "totalUnits",
    ]);

    const avgInventory = getEvidenceValue(item, [
      "average_inventory",
      "avg_inventory",
      "averageInventory",
    ]);

    const averageDailyDemand = getEvidenceValue(item, [
      "average_daily_demand",
      "daily_demand",
      "averageDailyDemand",
    ]);

    const zeroInventoryRecords = getEvidenceValue(item, [
      "zero_inventory_records",
      "zero_inventory_days",
      "zeroInventoryRecords",
      "zeroInventoryDays",
    ]);

    const unitCost = getEvidenceValue(item, [
      "unit_cost",
      "unitCost",
    ]);

    const costRank = getEvidenceValue(item, [
      "cost_rank",
      "costRank",
    ]);

    const riskReason = getEvidenceValue(item, [
      "risk_reason",
      "riskReason",
    ]);

    let title =
      provider ||
      product ||
      supplier ||
      route ||
      `Evidence ${index + 1}`;

    if (product && supplier) {
      title = `${product} → ${supplier}`;
      if (supplierName) {
        title += ` (${supplierName})`;
      }
    } else if (product && supplierName) {
      title = `${product} • ${supplierName}`;
    } else if (supplier && supplierName) {
      title = `${supplier} • ${supplierName}`;
    }

    const metrics = [];

    if (product) {
      metrics.push({
        label: "Product",
        value: String(product),
      });
    }

    if (supplier) {
      metrics.push({
        label: "Supplier",
        value: supplierName ? `${supplier} (${supplierName})` : String(supplier),
      });
    }

    if (unitCost !== undefined) {
      const cost = safeNumber(unitCost);
      metrics.push({
        label: "Unit Cost",
        value: cost !== null ? `$${cost.toFixed(2)}` : "—",
      });
    }

    if (costRank !== undefined) {
      const rank = safeNumber(costRank);
      metrics.push({
        label: "Rank",
        value: rank !== null ? `#${rank.toFixed(0)}` : "—",
      });
    }

    if (riskLevel !== undefined) {
      metrics.push({
        label: "Risk Level",
        value: String(riskLevel).toUpperCase(),
      });
    }

    if (riskScore !== undefined) {
      const score = safeNumber(riskScore);

      metrics.push({
        label: "Risk Score",
        value:
          score !== null
            ? score.toFixed(2)
            : "—",
      });
    }

    if (lateRate !== undefined) {
      const rate = safeNumber(lateRate);

      metrics.push({
        label: "Late Rate",
        value:
          rate !== null
            ? `${(rate * 100).toFixed(2)}%`
            : "—",
      });
    }

    if (delay !== undefined) {
      const delayValue = safeNumber(delay);

      metrics.push({
        label: "Average Delay",
        value:
          delayValue !== null
            ? `${delayValue.toFixed(2)} days`
            : "—",
      });
    }

    if (stockoutRate !== undefined) {
      const rate = safeNumber(stockoutRate);

      metrics.push({
        label: "Stockout Rate",
        value:
          rate !== null
            ? `${(rate * 100).toFixed(2)}%`
            : "—",
      });
    }

    if (daysOfCover !== undefined) {
      const cover = safeNumber(daysOfCover);

      metrics.push({
        label: "Days of Cover",
        value:
          cover !== null
            ? cover.toFixed(2)
            : "—",
      });
    }

    if (demandPressure !== undefined) {
      const pressure = safeNumber(demandPressure);

      metrics.push({
        label: "Demand Pressure",
        value:
          pressure !== null
            ? `${(pressure * 100).toFixed(2)}%`
            : "—",
      });
    }

    if (totalOrders !== undefined) {
      const orders = safeNumber(totalOrders);

      metrics.push({
        label: "Orders",
        value:
          orders !== null
            ? orders.toLocaleString("en-US")
            : "—",
      });
    }

    if (totalUnits !== undefined) {
      const units = safeNumber(totalUnits);

      metrics.push({
        label: "Units",
        value:
          units !== null
            ? units.toLocaleString("en-US")
            : "—",
      });
    }

    if (avgInventory !== undefined) {
      const inventory = safeNumber(avgInventory);

      metrics.push({
        label: "Average Inventory",
        value:
          inventory !== null
            ? inventory.toFixed(2)
            : "—",
      });
    }

    if (averageDailyDemand !== undefined) {
      const demand = safeNumber(averageDailyDemand);

      metrics.push({
        label: "Daily Demand",
        value:
          demand !== null
            ? demand.toFixed(2)
            : "—",
      });
    }

    if (zeroInventoryRecords !== undefined) {
      const zeroDays = safeNumber(zeroInventoryRecords);

      metrics.push({
        label: "Zero Inventory Days",
        value:
          zeroDays !== null
            ? zeroDays.toLocaleString("en-US")
            : "—",
      });
    }

    const reasonText =
      riskReason ||
      buildEvidenceReason(item);

    return {
      id: index + 1,
      title,
      riskLevel:
        riskLevel !== undefined
          ? String(riskLevel).toUpperCase()
          : null,
      riskScore: safeNumber(riskScore),
      metrics,
      reason: reasonText,
      raw: record,
    };
  });
}


/* =========================================================
   RISK HELPERS
========================================================= */

function isRiskBearing(level) {
  const normalized = String(
    level || ""
  ).toUpperCase();

  return [
    "CRITICAL",
    "HIGH",
    "MEDIUM",
  ].includes(normalized);
}


function getRiskBearingEvidence(evidence) {
  return evidence.filter((item) =>
    isRiskBearing(item.riskLevel)
  );
}


function getRiskSummary(evidence) {
  const summary = {
    critical: 0,
    high: 0,
    medium: 0,
    low: 0,
    unknown: 0,
  };

  evidence.forEach((item) => {
    const level = String(
      item.riskLevel || ""
    ).toLowerCase();

    if (level === "critical") {
      summary.critical += 1;
    } else if (level === "high") {
      summary.high += 1;
    } else if (level === "medium") {
      summary.medium += 1;
    } else if (level === "low") {
      summary.low += 1;
    } else {
      summary.unknown += 1;
    }
  });

  return summary;
}


/* =========================================================
   QUERY INTENT HELPERS
========================================================= */

function isRiskListQuery(query, intent) {
  const text = String(query || "")
    .toLowerCase();

  const supplierIntent =
    String(intent || "").toLowerCase() ===
    "supplier_risk";

  const asksWhich =
    text.includes("which") ||
    text.includes("what suppliers") ||
    text.includes("list");

  const asksRisk =
    text.includes("risk") ||
    text.includes("risky") ||
    text.includes("high risk") ||
    text.includes("critical");

  return (
    supplierIntent &&
    asksWhich &&
    asksRisk
  );
}


function buildSupplierRiskAnswer(
  response,
  evidence,
  query
) {
  if (
    !isRiskListQuery(
      query,
      response?.intent
    )
  ) {
    return (
      response?.answer ||
      response?.message ||
      "No answer was returned."
    );
  }

  const riskBearing =
    getRiskBearingEvidence(evidence);

  const summary =
    getRiskSummary(evidence);

  /*
    Important:
    LOW is a valid risk classification,
    but this query asks for suppliers that
    are actually risk-bearing.

    Therefore we do not describe LOW suppliers
    as risky.
  */

  if (riskBearing.length === 0) {
    return (
      `No suppliers in the retrieved evidence currently ` +
      `meet the configured risk threshold for ` +
      `MEDIUM, HIGH, or CRITICAL risk. ` +
      `The ${evidence.length} retrieved suppliers are ` +
      `currently classified as LOW risk. ` +
      `Risk distribution: ${summary.low} LOW` +
      `${
        summary.unknown > 0
          ? ` and ${summary.unknown} unclassified`
          : ""
      }.`
    );
  }

  const names = riskBearing
    .map((item) => {
      const level =
        item.riskLevel || "UNKNOWN";

      return `${item.title} (${level})`;
    })
    .join(", ");

  return (
    `${riskBearing.length} supplier(s) in the ` +
    `retrieved evidence meet the configured ` +
    `risk threshold: ${names}. ` +
    `The remaining retrieved suppliers are not ` +
    `classified as MEDIUM, HIGH, or CRITICAL risk.`
  );
}


/* =========================================================
   ENTITY
========================================================= */

function deriveEntity(response, evidence) {
  /*
    Use backend entity information only when
    it represents a meaningful specific entity.
  */

  if (
    response?.entity_type &&
    response?.entity_id &&
    response.entity_id !== "—"
  ) {
    return {
      type: response.entity_type,
      id: response.entity_id,
    };
  }

  const first = evidence[0];

  if (!first) {
    return {
      type: "Supply Chain",
      id: "All",
    };
  }

  /* Product */

  if (
    first.raw?.product_id ||
    first.raw?.productId
  ) {
    if (evidence.length === 1) {
      return {
        type: "Product",
        id:
          first.raw.product_id ||
          first.raw.productId,
      };
    }

    return {
      type: "Products",
      id: `${evidence.length} products`,
    };
  }

  /* Supplier */

  if (
    first.raw?.supplier_id ||
    first.raw?.supplierId
  ) {
    if (evidence.length === 1) {
      return {
        type: "Supplier",
        id:
          first.raw.supplier_id ||
          first.raw.supplierId,
      };
    }

    return {
      type: "Suppliers",
      id: `${evidence.length} suppliers`,
    };
  }

  /* 3PL */

  if (
    first.raw?.three_pl ||
    first.raw?.["3pl"] ||
    first.raw?.provider ||
    first.raw?.provider_id
  ) {
    if (evidence.length === 1) {
      return {
        type: "Logistics Provider",
        id:
          first.raw?.three_pl ||
          first.raw?.["3pl"] ||
          first.raw?.provider ||
          first.raw?.provider_id,
      };
    }

    return {
      type: "Logistics Providers",
      id: `${evidence.length} providers`,
    };
  }

  /* Route */

  if (
    first.raw?.route_id ||
    first.raw?.routeId
  ) {
    if (evidence.length === 1) {
      return {
        type: "Route",
        id:
          first.raw.route_id ||
          first.raw.routeId,
      };
    }

    return {
      type: "Routes",
      id: `${evidence.length} routes`,
    };
  }

  return {
    type: "Supply Chain",
    id: "All",
  };
}


/* =========================================================
   INTENT FORMATTER
========================================================= */

function formatIntent(intent) {
  if (!intent) {
    return "General Supply Chain Analysis";
  }

  return String(intent)
    .replaceAll("_", " ")
    .replace(/\b\w/g, (char) =>
      char.toUpperCase()
    );
}


/* =========================================================
   AGENT FORMATTER
========================================================= */

function getAgentLabel(agent) {
  if (typeof agent === "string") {
    return agent;
  }

  return (
    agent?.name ||
    agent?.agent_name ||
    "Supply Chain Agent"
  );
}


/* =========================================================
   MAIN COMPONENT
========================================================= */

function AIQuery() {
  const [query, setQuery] = useState("");
  const [response, setResponse] = useState(null);
  const [expandedEvidenceId, setExpandedEvidenceId] = useState(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const exampleQueries = [
    "Why is product P00003 at inventory risk?",
    "What is the delivery risk?",
    "Which suppliers have risk?",
    "Forecast demand for product P00003",
    "Who supplied product P00003 and how many total orders from this supplier?",
    "What is the demand for product P00003 and which supplier is associated with it?",
  ];


  /* =======================================================
     SUBMIT
  ======================================================= */

  async function handleSubmit(event) {
    event?.preventDefault();

    if (!query.trim()) {
      return;
    }

    try {
      setLoading(true);
      setError("");
      setResponse(null);

      const result =
        await askSupplyChainQuery(
          query.trim()
        );

      console.log(
        "AI QUERY RESPONSE:",
        result
      );

      setResponse(result);

    } catch (err) {
      console.error(
        "AI QUERY ERROR:",
        err
      );

      setError(
        err?.response?.data?.detail ||
          "Unable to process the supply chain query."
      );

    } finally {
      setLoading(false);
    }
  }


  /* =======================================================
     DERIVED DATA
  ======================================================= */

  const evidence =
    normalizeEvidence(
      response?.evidence
    );

  const evidenceToDisplay =
    evidence.length > 0 &&
    response?.requirement_count > 1
      ? evidence.slice(0, 2)
      : evidence.slice(0, 5);

  const evidenceFocus =
    summarizeEvidenceFocus(
      response,
      evidence
    );

  const entity =
    deriveEntity(
      response,
      evidence
    );

  const riskBearingEvidence =
    getRiskBearingEvidence(
      evidence
    );

  const riskSummary =
    getRiskSummary(
      evidence
    );

  const supplierRiskQuery =
    isRiskListQuery(
      query,
      response?.intent
    );

  const displayAnswer =
    buildSupplierRiskAnswer(
      response,
      evidence,
      query
    );

  const fallbackUsed =
    response?.fallback_used === true ||
    response?.status === "fallback";

  const isClarificationRequired =
    response?.status === "clarification_required" ||
    response?.status === "unsupported";

  const confidence =
    response?.confidence !== undefined
      ? Number(response.confidence)
      : null;

  const requirementCount =
    Number(
      response?.requirement_count ??
        response?.requirements?.length ??
        0
    ) || 0;

  const successfulRequirements =
    Number(
      response?.successful_requirements ?? 0
    ) || 0;

  const modelScore =
    confidence !== null
      ? Math.max(0, Math.min(100, confidence * 100))
      : requirementCount > 0
        ? Math.max(0, Math.min(100, (successfulRequirements / Math.max(requirementCount, 1)) * 100))
        : 0;

  const modelGrade =
    modelScore >= 85
      ? "High confidence"
      : modelScore >= 65
        ? "Moderate confidence"
        : modelScore >= 40
          ? "Low confidence"
          : "Needs review";

  function toggleEvidence(id) {
    setExpandedEvidenceId((currentId) => (
      currentId === id ? null : id
    ));
  }


  /* =======================================================
     RENDER
  ======================================================= */

  return (
    <div className="page-container ai-query-page">

      {/* =================================================
          PAGE HEADER
      ================================================= */}

      <div className="page-heading">

        <p className="page-eyebrow">
          INTELLIGENT OPERATIONS
        </p>

        <h1>
          AI Assistant
        </h1>

        <p className="page-description">
          Ask natural-language questions and trace
          each answer from supply-chain evidence to
          actionable recommendations.
        </p>

      </div>


      {/* =================================================
          QUERY CARD
      ================================================= */}

      <section className="ai-query-card">

        <div className="ai-query-header">

          <div>

            <p className="ai-eyebrow">
              SUPPLY CHAIN COPILOT
            </p>

            <h2>
              Ask the Control Tower
            </h2>

            <p>
              The assistant identifies the question,
              retrieves relevant operational evidence,
              analyzes the risk and generates an
              explanation.
            </p>

          </div>

          <div className="ai-status-badge">
            <span></span>
            AI ONLINE
          </div>

        </div>


        <form
          className="ai-query-form"
          onSubmit={handleSubmit}
        >

          <textarea
            value={query}
            onChange={(event) =>
              setQuery(event.target.value)
            }
            placeholder="Example: Which suppliers have risk?"
            rows={4}
          />


          <div className="ai-query-actions">

            <span>
              Ask about inventory, suppliers,
              delivery, routes or forecasts.
            </span>

            <button
              type="submit"
              disabled={
                loading ||
                !query.trim()
              }
            >
              {loading
                ? "Analyzing..."
                : "Ask Assistant"}
            </button>

          </div>

        </form>

      </section>


      {/* =================================================
          EXAMPLES
      ================================================= */}

      <section className="ai-examples-card">

        <div>

          <p className="ai-eyebrow">
            EXAMPLE QUESTIONS
          </p>

          <h2>
            Try a query
          </h2>

        </div>


        <div className="ai-example-list">

          {exampleQueries.map(
            (example, index) => (
              <button
                key={index}
                type="button"
                onClick={() =>
                  setQuery(example)
                }
              >
                <span>✦</span>
                {example}
              </button>
            )
          )}

        </div>

      </section>


      {/* =================================================
          ERROR
      ================================================= */}

      {error && (
        <ErrorMessage
          title="AI Query Failed"
          message={error}
          onRetry={() =>
            handleSubmit()
          }
        />
      )}


      {/* =================================================
          LOADING
      ================================================= */}

      {loading && (
        <Loading
          message="Analyzing supply-chain evidence..."
        />
      )}


      {/* =================================================
          RESPONSE
      ================================================= */}

      {response && !loading && (

        <section className="ai-response-card">

          {/* =============================================
              RESPONSE HEADER
          ============================================= */}

          <div className="ai-response-header">

            <div>

              <p className="ai-eyebrow">
                DECISION SUPPORT RESULT
              </p>

              <h2>
                Supply Chain Insight
              </h2>

            </div>


            <div
              className={
                fallbackUsed
                  ? "ai-response-status fallback"
                  : "ai-response-status"
              }
            >
              {fallbackUsed
                ? "FALLBACK RESPONSE"
                : "EVIDENCE ANALYZED"}
            </div>

          </div>


          {/* =============================================
              PROCESS FLOW
          ============================================= */}

          <div className="ai-flow">

            <div className="ai-flow-step active">

              <span className="ai-flow-number">
                01
              </span>

              <strong>
                Understand
              </strong>

              <small>
                Identify intent
              </small>

            </div>


            <div className="ai-flow-arrow">
              →
            </div>


            <div className="ai-flow-step active">

              <span className="ai-flow-number">
                02
              </span>

              <strong>
                Retrieve
              </strong>

              <small>
                Collect evidence
              </small>

            </div>


            <div className="ai-flow-arrow">
              →
            </div>


            <div className="ai-flow-step active">

              <span className="ai-flow-number">
                03
              </span>

              <strong>
                Analyze
              </strong>

              <small>
                Assess risk
              </small>

            </div>


            <div className="ai-flow-arrow">
              →
            </div>


            <div className="ai-flow-step active">

              <span className="ai-flow-number">
                04
              </span>

              <strong>
                Recommend
              </strong>

              <small>
                Suggest actions
              </small>

            </div>

          </div>


          {/* =============================================
              UNDERSTANDING
          ============================================= */}

          <div className="ai-understanding-card">

            <div>

              <span className="ai-label">
                WHAT DID THE SYSTEM UNDERSTAND?
              </span>

              <strong>
                {formatIntent(
                  response.intent
                )}
              </strong>

            </div>


            <div>

              <span className="ai-label">
                ANALYSIS SCOPE
              </span>

              <strong>

                {supplierRiskQuery
                  ? "Risk-bearing suppliers"
                  : `${entity.type} · ${entity.id}`}

              </strong>

            </div>


            <div>

              <span className="ai-label">
                EVIDENCE USED
              </span>

              <strong>
                {evidence.length} records
              </strong>

            </div>

          </div>


          {/* =============================================
              QUERY QUALITY
          ============================================= */}

          <div className="ai-query-assessment-card">

            <div className="ai-section-title">

              <span>
                01
              </span>

              <div>

                <h3>
                  Query quality assessment
                </h3>

                <p>
                  Real-time model feedback for this
                  request, based on confidence,
                  evidence and execution quality.
                </p>

              </div>

            </div>

            <div className="ai-assessment-grid">

              <div className="ai-assessment-item">
                <span>MODEL SCORE</span>
                <strong>
                  {Number.isFinite(modelScore)
                    ? `${Math.round(modelScore)}%`
                    : "—"}
                </strong>
                <small>{modelGrade}</small>
              </div>

              <div className="ai-assessment-item">
                <span>INTENT CONFIDENCE</span>
                <strong>
                  {confidence !== null
                    ? `${(confidence * 100).toFixed(0)}%`
                    : "—"}
                </strong>
                <small>{formatIntent(response.intent)}</small>
              </div>

              <div className="ai-assessment-item">
                <span>REQUIREMENTS RESOLVED</span>
                <strong>
                  {requirementCount > 0
                    ? `${successfulRequirements}/${requirementCount}`
                    : "0/0"}
                </strong>
                <small>
                  {requirementCount > 0
                    ? "Requirements executed successfully"
                    : "No structured requirements tracked"}
                </small>
              </div>

              <div className="ai-assessment-item">
                <span>EVIDENCE RECORDS</span>
                <strong>{evidence.length}</strong>
                <small>
                  {evidence.length > 0
                    ? "Operational records supporting the answer"
                    : "No evidence returned"}
                </small>
              </div>

            </div>

          </div>

          {isClarificationRequired && (
            <div className="ai-clarification-card">
              <div className="ai-clarification-icon">?</div>
              <div>
                <strong>Clarification required</strong>
                <p>
                  {response.answer ||
                    response.message ||
                    "Your request needs a little more detail so the system can target the correct entity, metric, or domain."}
                </p>
                <ul>
                  <li>Specify the product, supplier, or time horizon.</li>
                  <li>Choose a single primary metric if your request mixes several questions.</li>
                  <li>Try examples such as “Who supplied product P00003?” or “How many total orders from supplier S0066?”</li>
                </ul>
              </div>
            </div>
          )}

          {/* =============================================
              ANSWER
          ============================================= */}

          <div className="ai-answer-section">

            <div className="ai-section-title">

              <span>
                {isClarificationRequired ? "02" : "02"}
              </span>

              <div>

                <h3>
                  {isClarificationRequired
                    ? "Refined response guidance"
                    : "What the system found"}
                </h3>

                <p>
                  {isClarificationRequired
                    ? "The current request needs a more precise scope before a final answer can be generated."
                    : "Evidence-backed interpretation of the current supply-chain data."}
                </p>

              </div>

            </div>


            <div className="ai-answer">

              <p>
                {displayAnswer}
              </p>

            </div>

          </div>


          {/* =============================================
              SUPPLIER RISK SUMMARY
          ============================================= */}

          {supplierRiskQuery && (
            <div className="ai-section">

              <div className="ai-section-title">

                <span>
                  02
                </span>

                <div>

                  <h3>
                    Risk classification
                  </h3>

                  <p>
                    Suppliers are grouped using the
                    configured risk levels.
                  </p>

                </div>

              </div>


              <div className="ai-risk-summary-grid">

                <div className="ai-risk-summary-card">

                  <span>
                    CRITICAL
                  </span>

                  <strong>
                    {riskSummary.critical}
                  </strong>

                </div>


                <div className="ai-risk-summary-card">

                  <span>
                    HIGH
                  </span>

                  <strong>
                    {riskSummary.high}
                  </strong>

                </div>


                <div className="ai-risk-summary-card">

                  <span>
                    MEDIUM
                  </span>

                  <strong>
                    {riskSummary.medium}
                  </strong>

                </div>


                <div className="ai-risk-summary-card">

                  <span>
                    LOW
                  </span>

                  <strong>
                    {riskSummary.low}
                  </strong>

                </div>

              </div>


              {riskBearingEvidence.length === 0 && (
                <div className="ai-no-risk-message">

                  <strong>
                    No risk-bearing suppliers found
                    in the retrieved evidence.
                  </strong>

                  <p>
                    The retrieved suppliers are currently
                    classified as LOW risk. LOW is retained
                    as a monitoring classification and is
                    not treated as a risk-bearing result for
                    this query.
                  </p>

                </div>
              )}

            </div>
          )}


          {/* =============================================
              EVIDENCE
          ============================================= */}

          {evidenceToDisplay.length > 0 && (

            <div className="ai-section">

              <div className="ai-section-title">

                <span>
                  {supplierRiskQuery
                    ? "03"
                    : "02"}
                </span>

                <div>

                  <h3>
                    Supporting evidence
                  </h3>

                  <p>
                    These operational records support
                    the analysis above.
                  </p>

                </div>

              </div>


              {evidenceFocus && (
                <div className="ai-evidence-focus" style={{ marginBottom: "1rem", padding: "0.75rem 1rem", background: "#f7f9fc", borderRadius: "12px", border: "1px solid #e7edf7", color: "#1f2937" }}>
                  <strong>Evidence focus:</strong> {evidenceFocus}
                </div>
              )}

              <div className="ai-evidence-list">

                {evidenceToDisplay.map((item) => (

                  <div
                    className={`ai-evidence-card ${expandedEvidenceId === item.id ? "expanded" : ""}`}
                    key={item.id}
                    onClick={() => toggleEvidence(item.id)}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        toggleEvidence(item.id);
                      }
                    }}
                    style={{ cursor: "pointer" }}
                  >

                    <div className="ai-evidence-top">

                      <div>

                        <span className="ai-evidence-number">

                          {String(
                            item.id
                          ).padStart(2, "0")}

                        </span>

                        <strong>
                          {item.title}
                        </strong>

                      </div>


                      {item.riskLevel && (

                        <span
                          className={`ai-risk-level ai-risk-${String(
                            item.riskLevel
                          ).toLowerCase()}`}
                        >
                          {item.riskLevel}
                        </span>

                      )}

                    </div>


                    <div className="ai-evidence-metrics">

                      {item.metrics.map(
                        (metric, index) => (

                          <div
                            key={index}
                          >

                            <span>
                              {metric.label}
                            </span>

                            <strong>
                              {metric.value}
                            </strong>

                          </div>

                        )
                      )}

                    </div>


                    <div className="ai-evidence-reason">

                      <span>
                        WHY THIS MATTERS
                      </span>

                      <p>
                        {item.reason}
                      </p>

                    </div>

                    {expandedEvidenceId === item.id && (
                      <div className="ai-evidence-proof" style={{ marginTop: "0.9rem", paddingTop: "0.9rem", borderTop: "1px solid #e7edf7" }}>
                        <span style={{ display: "block", fontSize: "0.72rem", fontWeight: 700, letterSpacing: "0.08em", color: "#6b7280", marginBottom: "0.5rem" }}>
                          PROOF DATA
                        </span>
                        <p style={{ margin: 0, color: "#1f2937", lineHeight: 1.6 }}>
                          {buildEvidenceProof(item)}
                        </p>
                      </div>
                    )}

                  </div>

                ))}

              </div>

            </div>

          )}


          {/* =============================================
              ANALYSIS
          ============================================= */}

          <div className="ai-section">

            <div className="ai-section-title">

              <span>
                {supplierRiskQuery
                  ? "04"
                  : "03"}
              </span>

              <div>

                <h3>
                  Analysis
                </h3>

                <p>
                  How the evidence was converted into
                  the operational insight.
                </p>

              </div>

            </div>


            <div className="ai-analysis-box">

              <div className="ai-analysis-icon">
                ✓
              </div>


              <div>

                <strong>
                  Evidence → Risk → Insight
                </strong>

                <p>

                  The system classified the retrieved
                  records using their risk levels before
                  generating the operational response.

                  {supplierRiskQuery && (
                    <>
                      {" "}
                      For this query, only MEDIUM,
                      HIGH and CRITICAL suppliers are
                      treated as risk-bearing results.
                    </>
                  )}

                </p>

              </div>

            </div>

          </div>


          {/* =============================================
              AGENT WORKFLOW
          ============================================= */}

          {Array.isArray(
            response.agents_used
          ) &&
            response.agents_used.length > 0 && (

              <div className="ai-section">

                <div className="ai-section-title">

                  <span>
                    {supplierRiskQuery
                      ? "05"
                      : "04"}
                  </span>

                  <div>

                    <h3>
                      Agent workflow
                    </h3>

                    <p>
                      The processing path used to answer
                      the question.
                    </p>

                  </div>

                </div>


                <div className="ai-agent-flow">

                  {response.agents_used.map(
                    (agent, index) => (

                      <div
                        className="ai-agent-flow-item"
                        key={index}
                      >

                        <span>
                          {index + 1}
                        </span>

                        <strong>
                          {getAgentLabel(
                            agent
                          )}
                        </strong>


                        {index <
                          response.agents_used.length -
                            1 && (

                          <div className="ai-agent-connector">
                            →
                          </div>

                        )}

                      </div>

                    )
                  )}

                </div>

              </div>

            )}


          {/* =============================================
              RECOMMENDATIONS
          ============================================= */}

          {Array.isArray(
            response.recommendations
          ) &&
            response.recommendations.length > 0 &&

            !(
              supplierRiskQuery &&
              riskBearingEvidence.length === 0
            ) && (

              <div className="ai-section">

                <div className="ai-section-title">

                  <span>
                    {supplierRiskQuery
                      ? "06"
                      : "05"}
                  </span>

                  <div>

                    <h3>
                      Recommended actions
                    </h3>

                    <p>
                      Actions generated from the
                      identified supply-chain conditions.
                    </p>

                  </div>

                </div>


                <div className="ai-recommendation-list">

                  {response.recommendations.map(
                    (
                      recommendation,
                      index
                    ) => (

                      <div
                        className="ai-recommendation-item"
                        key={index}
                      >

                        <span>
                          {index + 1}
                        </span>

                        <p>

                          {typeof recommendation ===
                          "string"
                            ? recommendation
                            : recommendation?.text ||
                              recommendation?.recommendation ||
                              JSON.stringify(
                                recommendation
                              )}

                        </p>

                      </div>

                    )
                  )}

                </div>

              </div>

            )}


          {/* =============================================
              TECHNICAL TRACE
          ============================================= */}

          <div className="ai-technical-section">

            <div className="ai-section-title">

              <span>
                {supplierRiskQuery
                  ? "07"
                  : "06"}
              </span>

              <div>

                <h3>
                  Technical trace
                </h3>

                <p>
                  System metadata for traceability
                  and evaluation.
                </p>

              </div>

            </div>


            <div className="ai-technical-grid">

              <div>

                <span>
                  Confidence
                </span>

                <strong>

                  {confidence !== null
                    ? `${(
                        confidence * 100
                      ).toFixed(0)}%`
                    : "—"}

                </strong>

              </div>


              <div>

                <span>
                  Latency
                </span>

                <strong>

                  {response.latency_ms !==
                  undefined
                    ? `${Number(
                        response.latency_ms
                      ).toFixed(0)} ms`
                    : "—"}

                </strong>

              </div>


              <div>

                <span>
                  Fallback
                </span>

                <strong>

                  {fallbackUsed
                    ? "Used"
                    : "Not used"}

                </strong>

              </div>


              <div>

                <span>
                  Status
                </span>

                <strong>

                  {response.status ||
                    "success"}

                </strong>

              </div>

            </div>

          </div>

        </section>
      )}

    </div>
  );
}

export default AIQuery;
