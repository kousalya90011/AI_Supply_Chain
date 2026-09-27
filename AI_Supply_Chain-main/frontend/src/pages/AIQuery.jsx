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

  const record =
    item.data && typeof item.data === "object"
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


function formatPercentage(value) {
  const number = safeNumber(value);

  if (number === null) {
    return "—";
  }

  return `${(number * 100).toFixed(2)}%`;
}


function formatNumber(value, decimals = 2) {
  const number = safeNumber(value);

  if (number === null) {
    return "—";
  }

  return number.toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}


function formatInteger(value) {
  const number = safeNumber(value);

  if (number === null) {
    return "—";
  }

  return Math.round(number).toLocaleString("en-US");
}


function buildEvidenceReason(item) {
  if (!item || typeof item !== "object") {
    return "This record contains operational values that support the current supply-chain conclusion.";
  }

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

  const averageDailyDemand = getEvidenceValue(item, [
    "average_daily_demand",
    "daily_demand",
    "averageDailyDemand",
  ]);

  const avgInventory = getEvidenceValue(item, [
    "average_inventory",
    "avg_inventory",
    "averageInventory",
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

  if (
    product &&
    riskLevel !== undefined &&
    stockoutRate !== undefined
  ) {
    return (
      `${product} is classified as ${String(riskLevel).toUpperCase()} risk. ` +
      `The evidence shows a ${formatPercentage(stockoutRate)} stockout rate` +
      `${daysOfCover !== undefined
        ? ` and ${formatNumber(daysOfCover)} days of inventory cover`
        : ""
      }${demandPressure !== undefined
        ? `, indicating ${formatPercentage(demandPressure)} demand pressure`
        : ""
      }.`
    );
  }

  if (product && supplier) {
    return (
      `This record links ${product} to supplier ${supplier}` +
      `${supplierName ? ` (${supplierName})` : ""}, ` +
      `which explains the sourcing relationship behind the result.`
    );
  }

  if (product && averageDailyDemand !== undefined) {
    return (
      `This record shows ${product} with an average daily demand of ` +
      `${formatNumber(averageDailyDemand)} units, which is directly relevant ` +
      `to the current supply-chain analysis.`
    );
  }

  if (product && avgInventory !== undefined) {
    return (
      `This record shows ${product} with average inventory of ` +
      `${formatNumber(avgInventory)} units, which is relevant to its ` +
      `current inventory position.`
    );
  }

  if (product && unitCost !== undefined) {
    return (
      `This record shows ${product} at ` +
      `$${formatNumber(unitCost)} per unit, ` +
      `which supports the product cost analysis.`
    );
  }

  if (product && totalOrders !== undefined) {
    return (
      `This record shows ${formatInteger(totalOrders)} orders for ${product}, ` +
      `which explains the order-volume analysis.`
    );
  }

  if (supplier && lateRate !== undefined) {
    return (
      `This supplier record shows a late rate of ` +
      `${formatPercentage(lateRate)}, which contributes to the supplier ` +
      `performance assessment.`
    );
  }

  if (riskLevel !== undefined || riskScore !== undefined) {
    const riskText = riskLevel
      ? String(riskLevel).toUpperCase()
      : riskScore !== undefined
        ? `score ${formatNumber(riskScore)}`
        : "risk signal";

    return (
      `This record reflects a ${riskText} signal in the underlying ` +
      `supply-chain data, which is why it is included in the analysis.`
    );
  }

  if (product) {
    return (
      `This record contains operational values for ${product} ` +
      `that are directly relevant to the current analysis.`
    );
  }

  if (supplier) {
    return (
      `This record contains operational values for supplier ${supplier}` +
      `${supplierName ? ` (${supplierName})` : ""} ` +
      `that are relevant to the current analysis.`
    );
  }

  return (
    "This record contains operational values that support the " +
    "current supply-chain conclusion."
  );
}


function summarizeEvidenceFocus(response, evidence) {
  if (
    !response ||
    !Array.isArray(response.requirement_results)
  ) {
    return null;
  }

  const supplierRecord = evidence.find((item) => {
    const product = getEvidenceValue(item, [
      "product_id",
      "productId",
    ]);

    const supplier = getEvidenceValue(item, [
      "supplier_id",
      "supplierId",
    ]);

    return product && supplier;
  });

  const orderRecord = evidence.find((item) => {
    return (
      getEvidenceValue(item, [
        "total_orders",
        "totalOrders",
        "order_count",
        "orderCount",
      ]) !== undefined
    );
  });

  const productId =
    getEvidenceValue(
      supplierRecord,
      ["product_id", "productId"]
    ) ||
    getEvidenceValue(
      evidence[0],
      ["product_id", "productId"]
    ) ||
    null;

  const supplierId =
    getEvidenceValue(
      supplierRecord,
      ["supplier_id", "supplierId"]
    ) || null;

  const supplierName =
    getEvidenceValue(
      supplierRecord,
      ["supplier_name", "supplierName"]
    ) || null;

  const orderCount =
    getEvidenceValue(
      orderRecord,
      [
        "total_orders",
        "totalOrders",
        "order_count",
        "orderCount",
      ]
    ) ?? null;

  const parts = [];

  if (productId) {
    parts.push(productId);
  }

  if (supplierId) {
    const supplierLabel = supplierName
      ? `${supplierId} (${supplierName})`
      : supplierId;

    parts.push(`supplier ${supplierLabel}`);
  }

  if (orderCount !== null) {
    parts.push(
      `${formatInteger(orderCount)} orders`
    );
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

  const totalDemand = getEvidenceValue(item, [
    "total_demand",
    "totalDemand",
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

  const facts = [];

  if (product) {
    facts.push(`product ${product}`);
  }

  if (supplier) {
    facts.push(
      `supplier ${supplier}` +
      `${supplierName ? ` (${supplierName})` : ""}`
    );
  }

  if (riskLevel !== undefined) {
    facts.push(
      `risk ${String(riskLevel).toUpperCase()}`
    );
  }

  if (riskScore !== undefined) {
    facts.push(
      `risk score ${formatNumber(riskScore)}`
    );
  }

  if (stockoutRate !== undefined) {
    facts.push(
      `stockout rate ${formatPercentage(stockoutRate)}`
    );
  }

  if (daysOfCover !== undefined) {
    facts.push(
      `days of cover ${formatNumber(daysOfCover)}`
    );
  }

  if (demandPressure !== undefined) {
    facts.push(
      `demand pressure ${formatPercentage(demandPressure)}`
    );
  }

  if (avgInventory !== undefined) {
    facts.push(
      `average inventory ${formatNumber(avgInventory)}`
    );
  }

  if (averageDailyDemand !== undefined) {
    facts.push(
      `daily demand ${formatNumber(averageDailyDemand)}`
    );
  }

  if (totalDemand !== undefined) {
    facts.push(
      `total demand ${formatInteger(totalDemand)}`
    );
  }

  if (totalOrders !== undefined) {
    facts.push(
      `total orders ${formatInteger(totalOrders)}`
    );
  }

  if (lateRate !== undefined) {
    facts.push(
      `late rate ${formatPercentage(lateRate)}`
    );
  }

  if (facts.length === 0) {
    return (
      "This evidence record contains operational values that " +
      "directly support the current supply-chain conclusion."
    );
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
        sourceType: "unknown",
        retrievalMethod: null,
        riskLevel: null,
        riskScore: null,
        metrics: [],
        reason: item,
        raw: item,
      };
    }

    const record =
      item.data &&
        typeof item.data === "object"
        ? item.data
        : item.raw &&
          typeof item.raw === "object"
          ? item.raw
          : item;

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
      "order_count",
      "orderCount",
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

    const totalDemand = getEvidenceValue(item, [
      "total_demand",
      "totalDemand",
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

    const sourceType =
      item.source_type ||
      item.sourceType ||
      "unknown";

    const retrievalMethod =
      item.retrieval_method ||
      item.retrievalMethod ||
      null;

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
        value: supplierName
          ? `${supplier} (${supplierName})`
          : String(supplier),
      });
    }

    if (unitCost !== undefined) {
      metrics.push({
        label: "Unit Cost",
        value: `$${formatNumber(unitCost)}`,
      });
    }

    if (costRank !== undefined) {
      metrics.push({
        label: "Rank",
        value: `#${formatInteger(costRank)}`,
      });
    }

    if (riskLevel !== undefined) {
      metrics.push({
        label: "Risk Level",
        value: String(riskLevel).toUpperCase(),
      });
    }

    if (riskScore !== undefined) {
      metrics.push({
        label: "Risk Score",
        value: formatNumber(riskScore),
      });
    }

    if (lateRate !== undefined) {
      metrics.push({
        label: "Late Rate",
        value: formatPercentage(lateRate),
      });
    }

    if (delay !== undefined) {
      metrics.push({
        label: "Average Delay",
        value: `${formatNumber(delay)} days`,
      });
    }

    if (stockoutRate !== undefined) {
      metrics.push({
        label: "Stockout Rate",
        value: formatPercentage(stockoutRate),
      });
    }

    if (daysOfCover !== undefined) {
      metrics.push({
        label: "Days of Cover",
        value: formatNumber(daysOfCover),
      });
    }

    if (demandPressure !== undefined) {
      metrics.push({
        label: "Demand Pressure",
        value: formatPercentage(demandPressure),
      });
    }

    if (totalDemand !== undefined) {
      metrics.push({
        label: "Total Demand",
        value: formatInteger(totalDemand),
      });
    }

    if (totalOrders !== undefined) {
      metrics.push({
        label: "Orders",
        value: formatInteger(totalOrders),
      });
    }

    if (totalUnits !== undefined) {
      metrics.push({
        label: "Units",
        value: formatInteger(totalUnits),
      });
    }

    if (avgInventory !== undefined) {
      metrics.push({
        label: "Average Inventory",
        value: formatNumber(avgInventory),
      });
    }

    if (averageDailyDemand !== undefined) {
      metrics.push({
        label: "Daily Demand",
        value: formatNumber(averageDailyDemand),
      });
    }

    if (zeroInventoryRecords !== undefined) {
      metrics.push({
        label: "Zero Inventory Days",
        value: formatInteger(zeroInventoryRecords),
      });
    }

    const reasonText =
      riskReason ||
      buildEvidenceReason(item);

    return {
      id: index + 1,
      title,
      sourceType,
      retrievalMethod,
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

  if (riskBearing.length === 0) {
    return (
      `No suppliers in the retrieved evidence currently ` +
      `meet the configured risk threshold for ` +
      `MEDIUM, HIGH, or CRITICAL risk. ` +
      `The ${evidence.length} retrieved suppliers are ` +
      `currently classified as LOW risk. ` +
      `Risk distribution: ${summary.low} LOW` +
      `${summary.unknown > 0
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
   REASONING MODE
========================================================= */

function getReasoningMode(response) {
  if (
    response?.reasoning_mode
  ) {
    return String(
      response.reasoning_mode
    )
      .replaceAll("_", " ")
      .replace(/\b\w/g, (char) =>
        char.toUpperCase()
      );
  }

  if (
    response?.planner_method ===
    "deterministic_fallback"
  ) {
    return "Deterministic reasoning";
  }

  if (
    response?.llm_used === true
  ) {
    return "LLM-assisted reasoning";
  }

  return "Evidence-grounded reasoning";
}


/* =========================================================
   MAIN COMPONENT
========================================================= */

function AIQuery() {
  const [query, setQuery] = useState("");
  const [response, setResponse] = useState(null);
  const [expandedEvidenceId, setExpandedEvidenceId] =
    useState(null);

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
      setExpandedEvidenceId(null);

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
    evidence.slice(0, 5);

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
      response?.requirement_results?.length ??
      0
    ) || 0;

  const successfulRequirements =
    Number(
      response?.successful_requirements ??
      response?.requirement_results?.filter(
        (item) =>
          item?.status === "success"
      )?.length ??
      0
    ) || 0;

  const reasoningMode =
    getReasoningMode(response);

  const requirementsResolved =
    requirementCount > 0
      ? `${successfulRequirements}/${requirementCount}`
      : "—";


  function toggleEvidence(id) {
    setExpandedEvidenceId((currentId) =>
      currentId === id
        ? null
        : id
    );
  }


  /* =======================================================
     SECTION NUMBERING
  ======================================================= */

  let sectionNumber = 1;

  const getNextSectionNumber = () => {
    const number = String(
      sectionNumber
    ).padStart(2, "0");

    sectionNumber += 1;

    return number;
  };


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
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                flexWrap: "wrap",
              }}
            >

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


              {response?.retrieval_mode && (
                <span
                  className={`ai-retrieval-mode-badge mode-${String(
                    response.retrieval_mode
                  ).toLowerCase()}`}
                  title={
                    `Retrieval strategy: ${response.retrieval_mode}`
                  }
                >
                  {String(
                    response.retrieval_mode
                  ).toUpperCase()} RETRIEVAL
                </span>
              )}

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
                {getNextSectionNumber()}
              </span>

              <div>

                <h3>
                  Query quality assessment
                </h3>

                <p>
                  Execution quality and planner confidence
                  for this request.
                </p>

              </div>

            </div>


            <div className="ai-assessment-grid">

              <div className="ai-assessment-item">

                <span>
                  PLANNER CONFIDENCE
                </span>

                <strong>
                  {confidence !== null &&
                    Number.isFinite(confidence)
                    ? `${Math.round(
                      Math.max(
                        0,
                        Math.min(
                          100,
                          confidence * 100
                        )
                      )
                    )}%`
                    : "—"}
                </strong>

                <small>
                  Confidence in query interpretation
                </small>

              </div>


              <div className="ai-assessment-item">

                <span>
                  INTENT
                </span>

                <strong>
                  {formatIntent(
                    response.intent
                  )}
                </strong>

                <small>
                  Primary request classification
                </small>

              </div>


              <div className="ai-assessment-item">

                <span>
                  REQUIREMENTS RESOLVED
                </span>

                <strong>
                  {requirementsResolved}
                </strong>

                <small>
                  {requirementCount > 0
                    ? "Requirements executed successfully"
                    : "No structured requirements tracked"}
                </small>

              </div>


              <div className="ai-assessment-item">

                <span>
                  EVIDENCE RECORDS
                </span>

                <strong>
                  {evidence.length}
                </strong>

                <small>
                  {evidence.length > 0
                    ? "Authorized evidence supporting the answer"
                    : "No evidence returned"}
                </small>

              </div>

            </div>

          </div>


          {/* =============================================
              CLARIFICATION
          ============================================= */}

          {isClarificationRequired && (
            <div className="ai-clarification-card">

              <div className="ai-clarification-icon">
                ?
              </div>

              <div>

                <strong>
                  Clarification required
                </strong>

                <p>
                  {response.answer ||
                    response.message ||
                    "Your request needs a little more detail so the system can target the correct entity, metric, or domain."}
                </p>

                <ul>
                  <li>
                    Specify the product, supplier,
                    or time horizon.
                  </li>

                  <li>
                    Choose a primary metric if
                    your request mixes several questions.
                  </li>

                  <li>
                    Try examples such as
                    “Who supplied product P00003?”
                    or
                    “How many total orders from supplier S0066?”
                  </li>
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
                {getNextSectionNumber()}
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
                  {getNextSectionNumber()}
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
                  {getNextSectionNumber()}
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
                <div
                  className="ai-evidence-focus"
                  style={{
                    marginBottom: "1rem",
                    padding: "0.75rem 1rem",
                    background: "#f7f9fc",
                    borderRadius: "12px",
                    border: "1px solid #e7edf7",
                    color: "#1f2937",
                  }}
                >
                  <strong>
                    Evidence focus:
                  </strong>{" "}
                  {evidenceFocus}
                </div>
              )}


              <div className="ai-evidence-list">

                {evidenceToDisplay.map(
                  (item) => (

                    <div
                      className={`ai-evidence-card ${
                        expandedEvidenceId === item.id
                          ? "expanded"
                          : ""
                      }`}
                      key={item.id}
                      onClick={() =>
                        toggleEvidence(item.id)
                      }
                      role="button"
                      tabIndex={0}
                      onKeyDown={(event) => {
                        if (
                          event.key === "Enter" ||
                          event.key === " "
                        ) {
                          event.preventDefault();
                          toggleEvidence(item.id);
                        }
                      }}
                      style={{
                        cursor: "pointer",
                      }}
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


                        <div
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: "8px",
                            flexWrap: "wrap",
                          }}
                        >

                          {item.retrievalMethod && (
                            <span
                              className="ai-evidence-source-tag"
                              style={{
                                fontSize: "0.68rem",
                                fontWeight: 700,
                                letterSpacing: "0.06em",
                                textTransform: "uppercase",
                                padding: "4px 8px",
                                borderRadius: "999px",
                                background:
                                  item.retrievalMethod ===
                                    "semantic"
                                    ? "#f3f0ff"
                                    : "#eef6ff",
                                color:
                                  item.retrievalMethod ===
                                    "semantic"
                                    ? "#6546a8"
                                    : "#245b8f",
                              }}
                            >
                              {item.retrievalMethod}
                            </span>
                          )}


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

                      </div>


                      <div className="ai-evidence-metrics">

                        {item.metrics.map(
                          (
                            metric,
                            index
                          ) => (

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
                        <div
                          className="ai-evidence-proof"
                          style={{
                            marginTop: "0.9rem",
                            paddingTop: "0.9rem",
                            borderTop:
                              "1px solid #e7edf7",
                          }}
                        >

                          <span
                            style={{
                              display: "block",
                              fontSize: "0.72rem",
                              fontWeight: 700,
                              letterSpacing:
                                "0.08em",
                              color: "#6b7280",
                              marginBottom:
                                "0.5rem",
                            }}
                          >
                            PROOF DATA
                          </span>

                          <p
                            style={{
                              margin: 0,
                              color: "#1f2937",
                              lineHeight: 1.6,
                            }}
                          >
                            {buildEvidenceProof(
                              item
                            )}
                          </p>

                        </div>
                      )}

                    </div>

                  )
                )}

              </div>

            </div>

          )}


          {/* =============================================
              ANALYSIS
          ============================================= */}

          <div className="ai-section">

            <div className="ai-section-title">

              <span>
                {getNextSectionNumber()}
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

                  The system combines deterministic
                  supply-chain analytics with retrieved
                  evidence before producing the operational
                  response.

                  {reasoningMode && (
                    <>
                      {" "}
                      Current reasoning path:
                      {" "}
                      <strong>
                        {reasoningMode}
                      </strong>.
                    </>
                  )}

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
                    {getNextSectionNumber()}
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
                    (
                      agent,
                      index
                    ) => (

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
                    {getNextSectionNumber()}
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
                {getNextSectionNumber()}
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
                  Planner Confidence
                </span>

                <strong>

                  {confidence !== null &&
                    Number.isFinite(confidence)
                    ? `${(
                      confidence * 100
                    ).toFixed(0)}%`
                    : "—"}

                </strong>

              </div>


              <div>

                <span>
                  Execution Latency
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
                  Retrieval
                </span>

                <strong>
                  {response?.retrieval_mode
                    ? String(
                      response.retrieval_mode
                    ).toUpperCase()
                    : "—"}
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
