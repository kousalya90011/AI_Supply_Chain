import { NavLink } from "react-router-dom";

const navigationItems = [
  { path: "/dashboard", icon: "▦", label: "Dashboard" },
  { path: "/data", icon: "▣", label: "Data" },
  { path: "/suppliers", icon: "◉", label: "Suppliers" },
  { path: "/inventory", icon: "▤", label: "Inventory" },
  { path: "/delivery", icon: "⇢", label: "Delivery" },
  { path: "/routes", icon: "⌁", label: "Routes" },
  { path: "/anomalies", icon: "△", label: "Anomalies" },
  { path: "/forecast", icon: "↗", label: "Forecast" },
  { path: "/ai-assistant", icon: "✦", label: "AI Assistant" },
  { path: "/evaluation", icon: "✓", label: "Evaluation" },
  { path: "/audit", icon: "☷", label: "Audit" },
];

function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-mark">SC</div>

        <div className="brand-text">
          <span>Supply Chain</span>
          <strong>Risk Intelligence</strong>
        </div>
      </div>

      <div className="sidebar-section-title">CONTROL TOWER</div>

      <nav className="sidebar-nav">
        {navigationItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              `nav-item ${isActive ? "active" : ""}`
            }
          >
            <span className="nav-icon">{item.icon}</span>
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-bottom">
        <div className="system-card">
          <span className="system-indicator"></span>

          <div>
            <span className="system-label">SYSTEM</span>
            <strong>Control Tower Online</strong>
          </div>
        </div>

        <div className="sidebar-version">
          Supply Chain Intelligence
          <span>v1.0</span>
        </div>
      </div>
    </aside>
  );
}

export default Sidebar;