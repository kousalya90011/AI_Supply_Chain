import { NavLink } from "react-router-dom";

const adminItems = [
  { path: "/dashboard", icon: "▦", label: "Dashboard" },
  { path: "/users", icon: "👤", label: "Users" },
  { path: "/suppliers-page", icon: "▣", label: "Suppliers" },
  { path: "/products", icon: "◫", label: "Products" },
  { path: "/orders", icon: "◫", label: "Orders" },
  { path: "/inventory-page", icon: "▤", label: "Inventory" },
  { path: "/offers", icon: "✦", label: "Offers" },
  { path: "/risks", icon: "◉", label: "Risks" },
  { path: "/forecast", icon: "↗", label: "Forecast" },
  { path: "/anomalies", icon: "△", label: "Anomalies" },
  { path: "/ai-assistant", icon: "✦", label: "AI Query" },
  { path: "/evaluation", icon: "✓", label: "Evaluation" },
  { path: "/audit", icon: "☷", label: "Audit" },
];

const managerItems = [
  { path: "/dashboard", icon: "▦", label: "Dashboard" },
  { path: "/suppliers-page", icon: "▣", label: "Suppliers" },
  { path: "/products", icon: "◫", label: "Products" },
  { path: "/orders", icon: "◫", label: "Orders" },
  { path: "/inventory-page", icon: "▤", label: "Inventory" },
  { path: "/offers", icon: "✦", label: "Offers" },
  { path: "/risks", icon: "◉", label: "Risks" },
  { path: "/forecast", icon: "↗", label: "Forecast" },
  { path: "/anomalies", icon: "△", label: "Anomalies" },
  { path: "/ai-assistant", icon: "✦", label: "AI Query" },
];

const supplierItems = [
  { path: "/my-dashboard", icon: "▦", label: "My Dashboard" },
  { path: "/my-products", icon: "◫", label: "My Products" },
  { path: "/my-orders", icon: "◫", label: "My Orders" },
  { path: "/my-offers", icon: "✦", label: "My Offers" },
  { path: "/my-performance", icon: "✓", label: "My Performance" },
  { path: "/ai-assistant", icon: "✦", label: "AI Assistant" },
];

function Sidebar({ auth }) {
  const role = auth?.role;

  const navigationItems =
    role === "SUPPLIER"
      ? supplierItems
      : role === "ADMIN"
        ? adminItems
        : role === "SUPPLY_CHAIN_MANAGER"
          ? managerItems
          : adminItems;

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
          {role ? role : "OPERATIONS"}
          <span>v1.0</span>
        </div>
      </div>
    </aside>
  );
}

export default Sidebar;