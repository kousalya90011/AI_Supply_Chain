function RiskBadge({ level }) {
  const normalizedLevel = String(
    level || "UNKNOWN"
  ).toUpperCase();

  return (
    <span
      className={`risk-badge risk-${normalizedLevel.toLowerCase()}`}
    >
      <span className="risk-badge-dot"></span>

      {normalizedLevel}
    </span>
  );
}

export default RiskBadge;
