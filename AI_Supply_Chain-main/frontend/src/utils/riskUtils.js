export const RISK_LEVELS = [
  "CRITICAL",
  "HIGH",
  "MEDIUM",
  "LOW",
];

export function countRiskLevels(data = []) {
  return {
    critical: data.filter(
      (item) => item.risk_level === "CRITICAL"
    ).length,

    high: data.filter(
      (item) => item.risk_level === "HIGH"
    ).length,

    medium: data.filter(
      (item) => item.risk_level === "MEDIUM"
    ).length,

    low: data.filter(
      (item) => item.risk_level === "LOW"
    ).length,
  };
}

export function getRiskOrder(level) {
  const order = {
    CRITICAL: 1,
    HIGH: 2,
    MEDIUM: 3,
    LOW: 4,
  };

  return order[level] || 99;
}

export function sortByRisk(data = []) {
  return [...data].sort(
    (a, b) =>
      getRiskOrder(a.risk_level) -
      getRiskOrder(b.risk_level)
  );
}
