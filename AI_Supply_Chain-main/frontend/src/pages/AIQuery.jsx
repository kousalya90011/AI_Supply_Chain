import { useState } from "react";
import { askSupplyChainQuery } from "../api/queryApi";
import Loading from "../components/Loading";
import ErrorMessage from "../components/ErrorMessage";

/* =========================================================
   GENERIC VALUE & NUMBER HELPERS
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
    if (item[key] !== undefined && item[key] !== null) {
      return item[key];
    }
    if (record[key] !== undefined && record[key] !== null) {
      return record[key];
    }
  }

  return undefined;
}

function safeNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function formatPercentage(value) {
  const number = safeNumber(value);
  if (number === null) {
    return "—";
  }
  // If already scaled as 0-100 (e.g. 50.9) vs 0-1 (e.g. 0.509)
  const pct = Math.abs(number) <= 1.0 ? number * 100 : number;
  return `${pct.toFixed(1)}%`;
}

function formatNumber(value, decimals = 1) {
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

/* =========================================================
   MARKDOWN SANITIZER
========================================================= */

function cleanMarkdownArtifacts(text) {
  if (typeof text !== "string") {
    return "";
  }

  return text
    .replace(/^###+\s*[^\n]*\n?/gm, "")       // Strip ### Headers
    .replace(/\*\*([^*]+)\*\*/g, "$1")         // Strip bold **text**
    .replace(/\*([^*]+)\*/g, "$1")             // Strip italic *text*
    .replace(/__([^_]+)__/g, "$1")             // Strip __text__
    .replace(/^[\s•*–-]+\s*/gm, "")            // Strip bullet markers at line start
    .replace(/[•]/g, "")                       // Strip stray bullet glyphs
    .replace(/\n{3,}/g, "\n\n")                // Collapse extra newlines
    .trim();
}

/* =========================================================
   EVIDENCE REASON & PROOF GENERATORS
========================================================= */

function buildEvidenceReason(item) {
  if (!item || typeof item !== "object") {
    return "Operational values supporting current supply-chain assessment.";
  }

  const sid = getEvidenceValue(item, ["supplier_id", "supplierId"]);
  const sname = getEvidenceValue(item, ["supplier_name", "supplierName"]);
  const pid = getEvidenceValue(item, ["product_id", "productId"]);

  // Lead-time anomaly evidence
  const recentLt = getEvidenceValue(item, ["recent_avg_days", "recentAvgDays", "recent_lead_time"]);
  const histLt = getEvidenceValue(item, ["historical_avg_days", "historicalAvgDays", "historical_baseline"]);
  const chgLt = getEvidenceValue(item, ["absolute_change_days", "absoluteChangeDays", "lead_time_change"]);
  const pctLt = getEvidenceValue(item, ["percentage_change", "percentageChange"]);
  const statusLt = getEvidenceValue(item, ["status"]);

  if (recentLt !== undefined && histLt !== undefined) {
    const sign = (chgLt || 0) > 0 ? "+" : "";
    const chgStr = chgLt !== undefined ? ` (${sign}${formatNumber(chgLt, 1)}d, ${sign}${formatPercentage(pctLt)})` : "";
    const statStr = statusLt ? ` classified as ${statusLt}` : "";
    return `Supplier ${sid || "record"} recent lead time rose to ${formatNumber(recentLt, 1)} days from historical baseline of ${formatNumber(histLt, 1)} days${chgStr}${statStr}.`;
  }

  // Supplier delivery risk evidence
  const lateRate = getEvidenceValue(item, ["late_rate", "lateRate"]);
  const delay = getEvidenceValue(item, ["avg_delay", "avg_delay_days", "average_delay", "average_delay_days"]);
  const orders = getEvidenceValue(item, ["total_orders", "totalOrders", "order_count"]);
  const riskLevel = getEvidenceValue(item, ["risk_level", "riskLevel"]);

  if (sid && lateRate !== undefined) {
    const delayStr = delay !== undefined ? `, with ${formatNumber(delay, 1)} days average delay` : "";
    const orderStr = orders !== undefined ? ` across ${formatInteger(orders)} orders` : "";
    const levelStr = riskLevel ? ` (${String(riskLevel).toUpperCase()} risk)` : "";
    return `Supplier ${sid}${sname ? ` (${sname})` : ""} demonstrates a ${formatPercentage(lateRate)} late delivery rate${delayStr}${orderStr}${levelStr}.`;
  }

  // Product inventory risk evidence
  const stockoutRate = getEvidenceValue(item, ["stockout_rate", "stockoutRate"]);
  const daysOfCover = getEvidenceValue(item, ["days_of_cover", "daysOfCover"]);
  const dailyDemand = getEvidenceValue(item, ["average_daily_demand", "daily_demand"]);

  if (pid && (stockoutRate !== undefined || daysOfCover !== undefined)) {
    const stockStr = stockoutRate !== undefined ? `${formatPercentage(stockoutRate)} stockout rate` : "";
    const coverStr = daysOfCover !== undefined ? `${formatNumber(daysOfCover, 1)} days of inventory cover` : "";
    const demStr = dailyDemand !== undefined ? ` under daily demand of ${formatNumber(dailyDemand, 1)} units` : "";
    const separator = stockStr && coverStr ? " with " : "";
    return `Product ${pid} exhibits ${stockStr}${separator}${coverStr}${demStr}${riskLevel ? ` (${String(riskLevel).toUpperCase()} risk)` : ""}.`;
  }

  // Product demand & sourcing mapping
  const totalDemand = getEvidenceValue(item, ["total_demand", "totalDemand"]);
  if (pid && sid) {
    const demStr = totalDemand !== undefined ? ` with total demand of ${formatInteger(totalDemand)} units` : "";
    return `Product ${pid} is mapped to primary fulfillment partner ${sid}${sname ? ` (${sname})` : ""}${demStr}.`;
  }

  if (pid && totalDemand !== undefined) {
    return `Product ${pid} recorded ${formatInteger(totalDemand)} units of operational demand across the analyzed window.`;
  }

  if (item.explanation) {
    return cleanMarkdownArtifacts(item.explanation);
  }

  return "Verified operational record directly supporting the supply-chain analysis.";
}

function buildEvidenceProof(item) {
  if (!item || typeof item !== "object") {
    return "No raw telemetry was returned for this record.";
  }

  const pid = getEvidenceValue(item, ["product_id", "productId"]);
  const sid = getEvidenceValue(item, ["supplier_id", "supplierId"]);
  const sname = getEvidenceValue(item, ["supplier_name", "supplierName"]);
  const riskLevel = getEvidenceValue(item, ["risk_level", "riskLevel"]);
  const riskScore = getEvidenceValue(item, ["risk_score", "riskScore"]);
  const stockout = getEvidenceValue(item, ["stockout_rate", "stockoutRate"]);
  const cover = getEvidenceValue(item, ["days_of_cover", "daysOfCover"]);
  const late = getEvidenceValue(item, ["late_rate", "lateRate"]);
  const delay = getEvidenceValue(item, ["avg_delay", "avg_delay_days", "average_delay"]);
  const recentLt = getEvidenceValue(item, ["recent_avg_days", "recentAvgDays"]);
  const histLt = getEvidenceValue(item, ["historical_avg_days", "historicalAvgDays"]);
  const chgLt = getEvidenceValue(item, ["absolute_change_days", "absoluteChangeDays"]);
  const pctLt = getEvidenceValue(item, ["percentage_change", "percentageChange"]);
  const totalDemand = getEvidenceValue(item, ["total_demand", "totalDemand"]);
  const totalOrders = getEvidenceValue(item, ["total_orders", "totalOrders"]);

  const facts = [];

  if (pid) facts.push(`Product: ${pid}`);
  if (sid) facts.push(`Supplier: ${sid}${sname ? ` (${sname})` : ""}`);
  if (recentLt !== undefined) facts.push(`Recent Lead Time: ${formatNumber(recentLt, 1)}d`);
  if (histLt !== undefined) facts.push(`Baseline: ${formatNumber(histLt, 1)}d`);
  if (chgLt !== undefined) {
    const sign = chgLt > 0 ? "+" : "";
    facts.push(`Lead Time Delta: ${sign}${formatNumber(chgLt, 1)}d (${sign}${formatPercentage(pctLt)})`);
  }
  if (riskLevel !== undefined) facts.push(`Risk Level: ${String(riskLevel).toUpperCase()}`);
  if (riskScore !== undefined) facts.push(`Risk Score: ${formatNumber(riskScore, 1)}`);
  if (late !== undefined) facts.push(`Late Rate: ${formatPercentage(late)}`);
  if (delay !== undefined) facts.push(`Avg Delay: ${formatNumber(delay, 1)}d`);
  if (stockout !== undefined) facts.push(`Stockout Rate: ${formatPercentage(stockout)}`);
  if (cover !== undefined) facts.push(`Days of Cover: ${formatNumber(cover, 1)}d`);
  if (totalDemand !== undefined) facts.push(`Total Demand: ${formatInteger(totalDemand)} units`);
  if (totalOrders !== undefined) facts.push(`Total Orders: ${formatInteger(totalOrders)}`);

  if (facts.length === 0) {
    return "Verified deterministic evidence record.";
  }

  return facts.join("  |  ");
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
        sourceType: "analytics",
        retrievalMethod: "structured",
        riskLevel: null,
        riskScore: null,
        metrics: [],
        reason: item,
        raw: item,
      };
    }

    const record =
      item.data && typeof item.data === "object"
        ? item.data
        : item.raw && typeof item.raw === "object"
          ? item.raw
          : item;

    const provider = getEvidenceValue(item, ["three_pl", "3pl", "provider", "provider_id", "provider_name"]);
    const product = getEvidenceValue(item, ["product_id", "productId"]);
    const supplier = getEvidenceValue(item, ["supplier_id", "supplierId"]);
    const supplierName = getEvidenceValue(item, ["supplier_name", "supplierName"]);
    const route = getEvidenceValue(item, ["route_id", "routeId"]);
    const riskScore = getEvidenceValue(item, ["risk_score", "riskScore"]);
    const riskLevel = getEvidenceValue(item, ["risk_level", "riskLevel"]);
    const lateRate = getEvidenceValue(item, ["late_rate", "lateRate"]);
    const delay = getEvidenceValue(item, ["avg_delay_days", "average_delay", "average_delay_days", "avg_delay"]);
    const stockoutRate = getEvidenceValue(item, ["stockout_rate", "stockoutRate"]);
    const daysOfCover = getEvidenceValue(item, ["days_of_cover", "daysOfCover"]);
    const totalOrders = getEvidenceValue(item, ["total_orders", "totalOrders", "order_count"]);
    const avgInventory = getEvidenceValue(item, ["average_inventory", "avg_inventory"]);
    const averageDailyDemand = getEvidenceValue(item, ["average_daily_demand", "daily_demand"]);
    const totalDemand = getEvidenceValue(item, ["total_demand", "totalDemand"]);

    // Lead-time specific
    const recentLeadTime = getEvidenceValue(item, ["recent_avg_days", "recentAvgDays", "recent_lead_time"]);
    const historicalBaseline = getEvidenceValue(item, ["historical_avg_days", "historicalAvgDays", "historical_baseline"]);
    const leadTimeChange = getEvidenceValue(item, ["absolute_change_days", "absoluteChangeDays", "lead_time_change"]);
    const percentageChange = getEvidenceValue(item, ["percentage_change", "percentageChange"]);
    const statusVal = getEvidenceValue(item, ["status"]);

    const sourceType = item.source_type || item.sourceType || "analytics";
    const retrievalMethod = item.retrieval_method || item.retrievalMethod || "structured";

    let title = provider || product || supplier || route || `Evidence ${index + 1}`;
    if (product && supplier) {
      title = `${product} → ${supplier}${supplierName ? ` (${supplierName})` : ""}`;
    } else if (supplier && supplierName) {
      title = `Supplier ${supplier} (${supplierName})`;
    } else if (supplier) {
      title = `Supplier ${supplier}`;
    } else if (product) {
      title = `Product ${product}`;
    }

    const metrics = [];

    // Lead time metrics
    if (recentLeadTime !== undefined) {
      metrics.push({ label: "Recent Lead Time", value: `${formatNumber(recentLeadTime, 1)} days` });
    }
    if (historicalBaseline !== undefined) {
      metrics.push({ label: "Historical Baseline", value: `${formatNumber(historicalBaseline, 1)} days` });
    }
    if (leadTimeChange !== undefined) {
      const sign = leadTimeChange > 0 ? "+" : "";
      metrics.push({ label: "Change", value: `${sign}${formatNumber(leadTimeChange, 1)} days` });
    }
    if (percentageChange !== undefined) {
      const sign = percentageChange > 0 ? "+" : "";
      metrics.push({ label: "Change %", value: `${sign}${formatPercentage(percentageChange)}` });
    }
    if (statusVal !== undefined) {
      metrics.push({ label: "Status", value: String(statusVal) });
    }

    // Delivery risk metrics
    if (lateRate !== undefined) {
      metrics.push({ label: "Late Delivery Rate", value: formatPercentage(lateRate) });
    }
    if (delay !== undefined) {
      metrics.push({ label: "Average Delay", value: `${formatNumber(delay, 1)} days` });
    }
    if (totalOrders !== undefined) {
      metrics.push({ label: "Total Orders", value: formatInteger(totalOrders) });
    }

    // Inventory metrics
    if (stockoutRate !== undefined) {
      metrics.push({ label: "Stockout Rate", value: formatPercentage(stockoutRate) });
    }
    if (daysOfCover !== undefined) {
      metrics.push({ label: "Days of Cover", value: `${formatNumber(daysOfCover, 1)} days` });
    }
    if (averageDailyDemand !== undefined) {
      metrics.push({ label: "Daily Demand", value: `${formatNumber(averageDailyDemand, 1)} units/day` });
    }
    if (avgInventory !== undefined) {
      metrics.push({ label: "Avg Inventory", value: `${formatNumber(avgInventory, 0)} units` });
    }
    if (totalDemand !== undefined) {
      metrics.push({ label: "Total Demand", value: `${formatInteger(totalDemand)} units` });
    }

    if (riskLevel !== undefined) {
      metrics.push({ label: "Risk Classification", value: String(riskLevel).toUpperCase() });
    }
    if (riskScore !== undefined) {
      metrics.push({ label: "Risk Score", value: formatNumber(riskScore, 1) });
    }

    const reasonText = buildEvidenceReason(item);

    return {
      id: index + 1,
      title,
      sourceType,
      retrievalMethod,
      riskLevel: riskLevel !== undefined ? String(riskLevel).toUpperCase() : null,
      riskScore: safeNumber(riskScore),
      metrics,
      reason: reasonText,
      raw: record,
    };
  });
}

/* =========================================================
   RISK & INTENT HELPERS
========================================================= */

function isRiskBearing(level) {
  const normalized = String(level || "").toUpperCase();
  return ["CRITICAL", "HIGH", "MEDIUM"].includes(normalized);
}

function getRiskBearingEvidence(evidence) {
  return evidence.filter((item) => isRiskBearing(item.riskLevel));
}

function getRiskSummary(evidence) {
  const summary = { critical: 0, high: 0, medium: 0, low: 0, unknown: 0 };
  evidence.forEach((item) => {
    const level = String(item.riskLevel || "").toLowerCase();
    if (level === "critical") summary.critical += 1;
    else if (level === "high") summary.high += 1;
    else if (level === "medium") summary.medium += 1;
    else if (level === "low") summary.low += 1;
    else summary.unknown += 1;
  });
  return summary;
}

function isRiskListQuery(query, intent) {
  const text = String(query || "").toLowerCase();
  const supplierIntent = String(intent || "").toLowerCase() === "supplier_risk";
  const asksWhich = text.includes("which") || text.includes("what suppliers") || text.includes("list");
  const asksRisk = text.includes("risk") || text.includes("risky") || text.includes("high risk") || text.includes("critical");
  return supplierIntent && asksWhich && asksRisk;
}

function formatIntent(intent) {
  if (!intent) return "General Supply Chain Analysis";
  return String(intent)
    .replaceAll("_", " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

/* =========================================================
   KEY FINDINGS STRUCTURED TABLE & KPI EXTRACTORS
========================================================= */

function extractKeyFindingsTable(response, evidence) {
  if (!Array.isArray(evidence) || evidence.length === 0) {
    return null;
  }

  // 1. Lead Time Anomalies Table
  const leadTimeItems = evidence.filter((item) => {
    const rec = getEvidenceValue(item, ["recent_avg_days", "recentAvgDays"]);
    const hist = getEvidenceValue(item, ["historical_avg_days", "historicalAvgDays"]);
    return rec !== undefined && hist !== undefined;
  });

  if (leadTimeItems.length > 0) {
    return {
      type: "lead_time",
      headers: ["Supplier", "Recent Lead Time", "Historical Baseline", "Change", "Change %", "Status"],
      rows: leadTimeItems.slice(0, 5).map((item) => {
        const sid = getEvidenceValue(item, ["supplier_id", "supplierId"]) || item.title;
        const rec = getEvidenceValue(item, ["recent_avg_days", "recentAvgDays"]);
        const hist = getEvidenceValue(item, ["historical_avg_days", "historicalAvgDays"]);
        const chg = getEvidenceValue(item, ["absolute_change_days", "absoluteChangeDays"]);
        const pct = getEvidenceValue(item, ["percentage_change", "percentageChange"]);
        const stat = getEvidenceValue(item, ["status"]) || "Significant Increase";
        const sign = (chg || 0) > 0 ? "+" : "";
        return {
          id: sid,
          cells: [
            sid,
            `${formatNumber(rec, 1)}d`,
            `${formatNumber(hist, 1)}d`,
            `${sign}${formatNumber(chg, 1)}d`,
            `${sign}${formatPercentage(pct)}`,
            stat,
          ],
          highlightIndex: 3,
          status: stat,
        };
      }),
    };
  }

  // 2. Supplier Delivery Risk Table
  const supplierRiskItems = evidence.filter((item) => {
    const lr = getEvidenceValue(item, ["late_rate", "lateRate"]);
    const sid = getEvidenceValue(item, ["supplier_id", "supplierId"]);
    return lr !== undefined && sid;
  });

  if (supplierRiskItems.length > 0) {
    return {
      type: "supplier_risk",
      headers: ["Supplier", "Late Delivery Rate", "Average Delay", "Total Orders", "Risk Level"],
      rows: supplierRiskItems.slice(0, 5).map((item) => {
        const sid = getEvidenceValue(item, ["supplier_id", "supplierId"]);
        const sname = getEvidenceValue(item, ["supplier_name", "supplierName"]);
        const lr = getEvidenceValue(item, ["late_rate", "lateRate"]);
        const delay = getEvidenceValue(item, ["avg_delay", "avg_delay_days", "average_delay", "average_delay_days"]);
        const orders = getEvidenceValue(item, ["total_orders", "totalOrders"]);
        const riskLevel = getEvidenceValue(item, ["risk_level", "riskLevel"]) || "CRITICAL";
        return {
          id: sid,
          cells: [
            sname ? `${sid} (${sname})` : sid,
            formatPercentage(lr),
            delay !== undefined ? `${formatNumber(delay, 1)}d` : "—",
            orders !== undefined ? formatInteger(orders) : "—",
            String(riskLevel).toUpperCase(),
          ],
          highlightIndex: 1,
          status: riskLevel,
        };
      }),
    };
  }

  // 3. Product Inventory Risk Table
  const inventoryRiskItems = evidence.filter((item) => {
    const pid = getEvidenceValue(item, ["product_id", "productId"]);
    const stockout = getEvidenceValue(item, ["stockout_rate", "stockoutRate"]);
    const cover = getEvidenceValue(item, ["days_of_cover", "daysOfCover"]);
    return pid && (stockout !== undefined || cover !== undefined);
  });

  if (inventoryRiskItems.length > 0) {
    return {
      type: "inventory_risk",
      headers: ["Product", "Risk Level", "Stockout Rate", "Days of Cover", "Daily Demand", "Avg Inventory"],
      rows: inventoryRiskItems.slice(0, 5).map((item) => {
        const pid = getEvidenceValue(item, ["product_id", "productId"]);
        const riskLevel = getEvidenceValue(item, ["risk_level", "riskLevel"]) || "HIGH";
        const stockout = getEvidenceValue(item, ["stockout_rate", "stockoutRate"]);
        const cover = getEvidenceValue(item, ["days_of_cover", "daysOfCover"]);
        const daily = getEvidenceValue(item, ["average_daily_demand", "daily_demand"]);
        const inv = getEvidenceValue(item, ["avg_inventory", "average_inventory"]);
        return {
          id: pid,
          cells: [
            pid,
            String(riskLevel).toUpperCase(),
            stockout !== undefined ? formatPercentage(stockout) : "—",
            cover !== undefined ? `${formatNumber(cover, 1)}d` : "—",
            daily !== undefined ? `${formatNumber(daily, 1)} units` : "—",
            inv !== undefined ? formatNumber(inv, 0) : "—",
          ],
          highlightIndex: 2,
          status: riskLevel,
        };
      }),
    };
  }

  return null;
}

function extractKeyFindingsMetrics(evidence) {
  const cards = [];
  const first = evidence[0];
  if (!first) return cards;

  const pid = getEvidenceValue(first, ["product_id", "productId"]);
  const sid = getEvidenceValue(first, ["supplier_id", "supplierId"]);
  const sname = getEvidenceValue(first, ["supplier_name", "supplierName"]);
  const totalDemand = getEvidenceValue(first, ["total_demand", "totalDemand"]);
  const dailyDemand = getEvidenceValue(first, ["average_daily_demand", "daily_demand"]);
  const forecastDemand = getEvidenceValue(first, ["forecast_demand", "forecastDemand"]);

  if (pid) {
    cards.push({ label: "Target Product", value: pid });
  }
  if (totalDemand !== undefined) {
    cards.push({ label: "Total Demand", value: `${formatInteger(totalDemand)} units` });
  }
  if (dailyDemand !== undefined) {
    cards.push({ label: "Daily Demand Baseline", value: `${formatNumber(dailyDemand, 1)} units/day` });
  }
  if (sid) {
    cards.push({ label: "Primary Supplier", value: sname ? `${sid} (${sname})` : sid });
  }
  if (forecastDemand !== undefined && forecastDemand !== totalDemand) {
    cards.push({ label: "Projected Horizon Demand", value: `${formatInteger(forecastDemand)} units` });
  }

  return cards;
}

/* =========================================================
   PARSE RESPONSE INTO 6 CONTROL TOWER SECTIONS
========================================================= */

function parseResponseSections(response, evidence, query) {
  if (!response) return null;

  // 1. EXECUTIVE SUMMARY
  let rawExec = response.executive_summary || response.direct_answer || "";
  if (!rawExec && response.answer) {
    const match = response.answer.match(/###\s*Answer\s*\n([\s\S]*?)(?=\n###|$)/i);
    rawExec = match ? match[1] : response.answer;
  }
  let executiveSummary = cleanMarkdownArtifacts(rawExec);

  // If supplier risk list query with 0 risk-bearing suppliers:
  const riskBearing = getRiskBearingEvidence(evidence);
  const summary = getRiskSummary(evidence);
  if (isRiskListQuery(query, response?.intent) && riskBearing.length === 0) {
    executiveSummary = `No suppliers in the retrieved evidence currently meet the configured threshold for MEDIUM, HIGH, or CRITICAL risk. The ${evidence.length} retrieved suppliers are currently classified as LOW risk (${summary.low} LOW).`;
  }

  // 2. KEY FINDINGS
  let keyFindingsList = [];
  if (Array.isArray(response.key_findings) && response.key_findings.length > 0) {
    keyFindingsList = response.key_findings.map(cleanMarkdownArtifacts).filter(Boolean);
  } else if (response.answer) {
    const match = response.answer.match(/###\s*Key findings\s*\n([\s\S]*?)(?=\n###|$)/i);
    if (match) {
      keyFindingsList = match[1]
        .split("\n")
        .map(cleanMarkdownArtifacts)
        .filter((s) => s.length > 0);
    }
  }

  const tableData = extractKeyFindingsTable(response, evidence);
  const metricCards = !tableData ? extractKeyFindingsMetrics(evidence) : [];

  // 3. OPERATIONAL IMPACT
  let rawImpact = response.business_impact || "";
  if (!rawImpact && response.answer) {
    const match = response.answer.match(/###\s*(?:Why it matters|Operational Impact)\s*\n([\s\S]*?)(?=\n###|$)/i);
    if (match) {
      rawImpact = match[1];
    }
  }
  let operationalImpact = cleanMarkdownArtifacts(rawImpact);
  if (!operationalImpact) {
    operationalImpact = "Operational evidence directly influences replenishment predictability, safety-stock requirements, and fulfillment continuity across affected supply-chain nodes.";
  }

  // 4. RECOMMENDED ACTIONS
  let actionsList = [];
  if (Array.isArray(response.recommended_actions) && response.recommended_actions.length > 0) {
    actionsList = response.recommended_actions.map(cleanMarkdownArtifacts).filter(Boolean);
  } else if (Array.isArray(response.recommendations) && response.recommendations.length > 0) {
    actionsList = response.recommendations
      .map((r) => (typeof r === "string" ? cleanMarkdownArtifacts(r) : cleanMarkdownArtifacts(r?.text || r?.recommendation || "")))
      .filter(Boolean);
  } else if (response.answer) {
    const match = response.answer.match(/###\s*Recommended actions\s*\n([\s\S]*?)(?=\n###|$)/i);
    if (match) {
      actionsList = match[1]
        .split("\n")
        .map(cleanMarkdownArtifacts)
        .filter((s) => s.length > 0);
    }
  }

  return {
    executiveSummary,
    keyFindingsList,
    tableData,
    metricCards,
    operationalImpact,
    recommendedActions: actionsList.slice(0, 4),
  };
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
    "Which suppliers have risk?",
    "Identify unusual changes in supplier lead times.",
    "Why is product P00003 at inventory risk?",
    "What is the demand for product P00003 and which supplier is associated with it?",
    "Forecast demand for product P00003.",
  ];

  async function handleSubmit(event) {
    event?.preventDefault();
    if (!query.trim()) return;

    try {
      setLoading(true);
      setError("");
      setResponse(null);
      setExpandedEvidenceId(null);

      const result = await askSupplyChainQuery(query.trim());
      setResponse(result);
    } catch (err) {
      console.error("AI QUERY ERROR:", err);
      setError(
        err?.response?.data?.detail ||
        "Unable to process the supply chain query."
      );
    } finally {
      setLoading(false);
    }
  }

  /* =======================================================
     DERIVED DATA & SECTIONS
  ======================================================= */

  const evidence = normalizeEvidence(response?.evidence);
  const evidenceToDisplay = evidence.slice(0, 6);

  const fallbackUsed =
    response?.fallback_used === true || response?.status === "fallback";

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
      response?.requirement_results?.filter((item) => item?.status === "success")?.length ??
      0
    ) || 0;

  const requirementsResolved =
    requirementCount > 0
      ? `${successfulRequirements}/${requirementCount}`
      : "—";

  function toggleEvidence(id) {
    setExpandedEvidenceId((currentId) => (currentId === id ? null : id));
  }

  const sections = response
    ? parseResponseSections(response, evidence, query)
    : null;

  /* =======================================================
     RENDER
  ======================================================= */

  return (
    <div className="page-container ai-query-page">
      {/* =================================================
          PAGE HEADER
      ================================================= */}
      <div className="page-heading">
        <p className="page-eyebrow">INTELLIGENT DECISION SUPPORT</p>
        <h1>Supply Chain Control Tower</h1>
        <p className="page-description">
          Executive decision-support intelligence grounded in deterministic analytics,
          operational telemetry, and evidence verification.
        </p>
      </div>

      {/* =================================================
          QUERY INPUT CARD
      ================================================= */}
      <section className="ai-query-card">
        <div className="ai-query-header">
          <div>
            <p className="ai-eyebrow">CONTROL TOWER COPILOT</p>
            <h2>Ask Operational Intelligence</h2>
            <p>
              Inquire across supplier delivery reliability, inventory stockout runways,
              lead-time shifts, and demand forecasts.
            </p>
          </div>
        </div>

        <form className="ai-query-form" onSubmit={handleSubmit}>
          <textarea
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Example: Identify unusual changes in supplier lead times."
            rows={3}
          />

          <div className="ai-query-actions">
            <span>
              Deterministic supply-chain analytics with structured audit trace.
            </span>

            <button type="submit" disabled={loading || !query.trim()}>
              {loading ? "Analyzing Evidence..." : "Run Analysis"}
            </button>
          </div>
        </form>
      </section>

      {/* =================================================
          EXAMPLE QUERIES
      ================================================= */}
      <section className="ai-examples-card">
        <div>
          <p className="ai-eyebrow">EXECUTIVE BENCHMARKS</p>
          <h2>Suggested Queries</h2>
        </div>

        <div className="ai-example-list">
          {exampleQueries.map((example, index) => (
            <button
              key={index}
              type="button"
              onClick={() => {
                setQuery(example);
              }}
            >
              <span>✦</span>
              {example}
            </button>
          ))}
        </div>
      </section>

      {/* =================================================
          ERROR
      ================================================= */}
      {error && (
        <ErrorMessage
          title="AI Query Failed"
          message={error}
          onRetry={() => handleSubmit()}
        />
      )}

      {/* =================================================
          LOADING
      ================================================= */}
      {loading && <Loading message="Executing deterministic analytics and collecting operational evidence..." />}

      {/* =================================================
          RESPONSE CONTAINER
      ================================================= */}
      {response && !loading && sections && (
        <section className="ai-response-card">
          {/* HEADER BADGES */}
          <div className="ai-response-header">
            <div>
              <p className="ai-eyebrow">CONTROL TOWER INSIGHT</p>
              <h2>Executive Decision Support</h2>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
              <div className={fallbackUsed ? "ai-response-status fallback" : "ai-response-status"}>
                {fallbackUsed ? "FALLBACK RESPONSE" : "EVIDENCE GROUNDED"}
              </div>

              {response?.retrieval_mode && (
                <span className="ai-retrieval-mode-badge" title={`Mode: ${response.retrieval_mode}`}>
                  {String(response.retrieval_mode).toUpperCase()} RETRIEVAL
                </span>
              )}
            </div>
          </div>

          {/* CLARIFICATION NOTICE IF APPLICABLE */}
          {isClarificationRequired && (
            <div className="ai-clarification-card">
              <div className="ai-clarification-icon">?</div>
              <div>
                <strong>Scope Clarification Required</strong>
                <p>
                  {sections.executiveSummary ||
                    "Please specify an explicit entity ID (e.g. product P00003, supplier S0147) or primary metric to execute targeted analytics."}
                </p>
              </div>
            </div>
          )}

          {/* =============================================
              1. EXECUTIVE SUMMARY
          ============================================= */}
          <div className="ai-executive-section">
            <div className="ai-section-title">
              <span className="ai-section-num">01</span>
              <div>
                <h3>Executive Summary</h3>
                <p>Synthesized operational takeaway grounded in retrieved evidence.</p>
              </div>
            </div>

            <div className="ai-executive-card">
              <div className="ai-executive-accent" />
              <p>{sections.executiveSummary}</p>
            </div>
          </div>

          {/* =============================================
              2. KEY FINDINGS
          ============================================= */}
          <div className="ai-section ai-findings-section">
            <div className="ai-section-title">
              <span className="ai-section-num">02</span>
              <div>
                <h3>Key Findings</h3>
                <p>Structured operational signals and performance metrics retrieved for this query.</p>
              </div>
            </div>

            {/* TABULAR VIEW FOR MULTI-ENTITY QUERIES */}
            {sections.tableData && (
              <div className="ai-table-container">
                <table className="ai-findings-table">
                  <thead>
                    <tr>
                      {sections.tableData.headers.map((h, i) => (
                        <th key={i}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {sections.tableData.rows.map((row, rIdx) => (
                      <tr key={row.id || rIdx}>
                        {row.cells.map((cell, cIdx) => (
                          <td
                            key={cIdx}
                            className={cIdx === row.highlightIndex ? "ai-cell-highlight" : ""}
                          >
                            {cIdx === row.cells.length - 1 && row.status ? (
                              <span
                                className={`ai-status-badge ai-badge-${String(row.status)
                                  .toLowerCase()
                                  .replace(/[^a-z0-9]+/g, "-")}`}
                              >
                                {cell}
                              </span>
                            ) : (
                              cell
                            )}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* KPI METRIC CARDS FOR SINGLE-ENTITY INQUIRIES */}
            {sections.metricCards.length > 0 && (
              <div className="ai-kpi-grid">
                {sections.metricCards.map((m, idx) => (
                  <div key={idx} className="ai-kpi-card">
                    <span>{m.label}</span>
                    <strong>{m.value}</strong>
                  </div>
                ))}
              </div>
            )}

            {/* BULLET FINDINGS HIGHLIGHTS */}
            {sections.keyFindingsList.length > 0 && (
              <div className="ai-findings-list">
                {sections.keyFindingsList.map((finding, idx) => (
                  <div key={idx} className="ai-finding-item">
                    <span className="ai-finding-dot" />
                    <p>{finding}</p>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* =============================================
              3. OPERATIONAL IMPACT
          ============================================= */}
          <div className="ai-section ai-impact-section">
            <div className="ai-section-title">
              <span className="ai-section-num">03</span>
              <div>
                <h3>Operational Impact</h3>
                <p>Operational meaning of the evidence without generic boilerplate.</p>
              </div>
            </div>

            <div className="ai-impact-card">
              <div className="ai-impact-icon">⚡</div>
              <div>
                <strong>Supply Chain Continuity & Fulfillment Impact</strong>
                <p>{sections.operationalImpact}</p>
              </div>
            </div>
          </div>

          {/* =============================================
              4. RECOMMENDED ACTIONS
          ============================================= */}
          {sections.recommendedActions.length > 0 && (
            <div className="ai-section ai-actions-section">
              <div className="ai-section-title">
                <span className="ai-section-num">04</span>
                <div>
                  <h3>Recommended Actions</h3>
                  <p>Targeted next steps directly connected to the identified supply-chain conditions.</p>
                </div>
              </div>

              <div className="ai-actions-grid">
                {sections.recommendedActions.map((action, idx) => (
                  <div key={idx} className="ai-action-card">
                    <span className="ai-action-number">{idx + 1}</span>
                    <p>{action}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* =============================================
              5. SUPPORTING EVIDENCE
          ============================================= */}
          {evidenceToDisplay.length > 0 && (
            <div className="ai-section ai-evidence-section">
              <div className="ai-section-title">
                <span className="ai-section-num">05</span>
                <div>
                  <h3>Supporting Evidence</h3>
                  <p>Operational records and verified attributes backing the insights above.</p>
                </div>
              </div>

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
                        <span className="ai-evidence-number">{String(item.id).padStart(2, "0")}</span>
                        <strong>{item.title}</strong>
                      </div>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
                        {item.retrievalMethod && (
                          <span className="ai-evidence-source-tag">
                            {item.retrievalMethod}
                          </span>
                        )}
                        {item.riskLevel && (
                          <span className={`ai-risk-level ai-risk-${String(item.riskLevel).toLowerCase()}`}>
                            {item.riskLevel}
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="ai-evidence-metrics">
                      {item.metrics.map((metric, index) => (
                        <div key={index}>
                          <span>{metric.label}</span>
                          <strong>{metric.value}</strong>
                        </div>
                      ))}
                    </div>

                    <div className="ai-evidence-reason">
                      <span>OPERATIONAL SIGNIFICANCE</span>
                      <p>{item.reason}</p>
                    </div>

                    {expandedEvidenceId === item.id && (
                      <div className="ai-evidence-proof">
                        <span>RECORD TELEMETRY TRACE</span>
                        <p>{buildEvidenceProof(item)}</p>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* =============================================
              6. TECHNICAL TRACE
          ============================================= */}
          <div className="ai-technical-section">
            <div className="ai-section-title">
              <span className="ai-section-num">06</span>
              <div>
                <h3>Technical Trace</h3>
                <p>System audit and telemetry metadata separating system execution from the business answer.</p>
              </div>
            </div>

            <div className="ai-technical-grid">
              <div>
                <span>Planner Confidence</span>
                <strong>
                  {confidence !== null && Number.isFinite(confidence)
                    ? `${Math.round(confidence * 100)}%`
                    : "—"}
                </strong>
              </div>

              <div>
                <span>Intent</span>
                <strong>{formatIntent(response.intent)}</strong>
              </div>

              <div>
                <span>Requirements Resolved</span>
                <strong>{requirementsResolved}</strong>
              </div>

              <div>
                <span>Evidence Records</span>
                <strong>{evidence.length}</strong>
              </div>

              <div>
                <span>Retrieval Method</span>
                <strong>
                  {response?.retrieval_mode ? String(response.retrieval_mode).toUpperCase() : "STRUCTURED"}
                </strong>
              </div>

              <div>
                <span>Fallback</span>
                <strong>{fallbackUsed ? "Used" : "Not used"}</strong>
              </div>

              <div>
                <span>Execution Latency</span>
                <strong>
                  {response.latency_ms !== undefined ? `${Number(response.latency_ms).toFixed(0)} ms` : "—"}
                </strong>
              </div>

              <div>
                <span>Status</span>
                <strong className="ai-status-text">
                  {response.status || "success"}
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
