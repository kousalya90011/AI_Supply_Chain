import { NavLink } from "react-router-dom";

const RISK_TABS = [
  { path: "/risks", label: "Supplier Risk", icon: "◉" },
  { path: "/inventory", label: "Inventory Risk", icon: "▤" },
  { path: "/delivery", label: "Delivery Risk", icon: "🚚" },
  { path: "/routes", label: "Route Risk", icon: "🗺" },
];

function RiskTabs() {
  return (
    <nav className="risk-navigation-tabs" aria-label="Risk Categories Navigation">
      {RISK_TABS.map((tab) => (
        <NavLink
          key={tab.path}
          to={tab.path}
          className={({ isActive }) =>
            `risk-nav-tab ${isActive ? "active" : ""}`
          }
        >
          <span className="risk-nav-tab-icon">{tab.icon}</span>
          <span className="risk-nav-tab-label">{tab.label}</span>
        </NavLink>
      ))}
    </nav>
  );
}

export default RiskTabs;
