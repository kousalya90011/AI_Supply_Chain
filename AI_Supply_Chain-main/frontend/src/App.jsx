import { Routes, Route, Navigate } from "react-router-dom";
import { useEffect, useState } from "react";

import Layout from "./components/Layout";

import Dashboard from "./pages/Dashboard";
import DataStatus from "./pages/DataStatus";
import SupplierRisk from "./pages/SupplierRisk";
import InventoryRisk from "./pages/InventoryRisk";
import DeliveryRisk from "./pages/DeliveryRisk";
import RouteRisk from "./pages/RouteRisk";
import Anomalies from "./pages/Anomalies";
import Forecast from "./pages/Forecast";
import AIQuery from "./pages/AIQuery";
import Evaluation from "./pages/Evaluation";
import Audit from "./pages/Audit";

import LoginPage from "./pages/LoginPage";
import UsersPage from "./pages/UsersPage";
import SuppliersPage from "./pages/SuppliersPage";
import ProductsPage from "./pages/ProductsPage";
import OrdersPage from "./pages/OrdersPage";
import InventoryPage from "./pages/InventoryPage";
import OffersPage from "./pages/OffersPage";
import MyPerformancePage from "./pages/MyPerformancePage";

const AUTH_STORAGE_KEY = "sc_auth";

function ProtectedRoute({ auth, allowedRoles, children }) {
  if (!auth?.token) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles && !allowedRoles.includes(auth.role)) {
    const fallback = auth.role === "SUPPLIER" ? "/my-dashboard" : "/dashboard";
    return <Navigate to={fallback} replace />;
  }

  return children;
}

function App() {
  const [auth, setAuth] = useState(() => {
    try {
      const saved = localStorage.getItem(AUTH_STORAGE_KEY);
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });

  useEffect(() => {
    if (auth?.token) {
      localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(auth));
    } else {
      localStorage.removeItem(AUTH_STORAGE_KEY);
    }
  }, [auth]);

  const handleLogin = (userSession) => {
    setAuth(userSession);
  };

  const handleLogout = () => {
    setAuth(null);
  };

  const homePath = auth?.role === "SUPPLIER" ? "/my-dashboard" : "/dashboard";

  return (
    <Routes>
      <Route
        path="/login"
        element={
          auth?.token ? (
            <Navigate to={homePath} replace />
          ) : (
            <LoginPage onLogin={handleLogin} />
          )
        }
      />

      <Route
        path="/"
        element={
          <ProtectedRoute auth={auth}>
            <Layout auth={auth} onLogout={handleLogout} />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to={homePath} replace />} />

        {/* Operational & analytical pages */}
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="data" element={<DataStatus />} />
        <Route path="suppliers" element={<SupplierRisk />} />
        <Route path="inventory" element={<InventoryRisk />} />
        <Route path="delivery" element={<DeliveryRisk />} />
        <Route path="routes" element={<RouteRisk />} />
        <Route path="risks" element={<SupplierRisk />} />
        <Route path="anomalies" element={<Anomalies />} />
        <Route path="forecast" element={<Forecast />} />
        <Route path="ai-assistant" element={<AIQuery />} />

        {/* Admin only: Evaluation and Audit */}
        <Route
          path="evaluation"
          element={
            <ProtectedRoute auth={auth} allowedRoles={["ADMIN"]}>
              <Evaluation />
            </ProtectedRoute>
          }
        />
        <Route
          path="audit"
          element={
            <ProtectedRoute auth={auth} allowedRoles={["ADMIN"]}>
              <Audit />
            </ProtectedRoute>
          }
        />

        {/* Admin only: User Administration */}
        <Route
          path="users"
          element={
            <ProtectedRoute auth={auth} allowedRoles={["ADMIN"]}>
              <UsersPage auth={auth} />
            </ProtectedRoute>
          }
        />

        {/* Admin & Manager operational routes */}
        <Route
          path="suppliers-page"
          element={
            <ProtectedRoute auth={auth} allowedRoles={["ADMIN", "SUPPLY_CHAIN_MANAGER"]}>
              <SuppliersPage auth={auth} />
            </ProtectedRoute>
          }
        />

        <Route
          path="products"
          element={
            <ProtectedRoute auth={auth} allowedRoles={["ADMIN", "SUPPLY_CHAIN_MANAGER"]}>
              <ProductsPage auth={auth} />
            </ProtectedRoute>
          }
        />

        <Route
          path="orders"
          element={
            <ProtectedRoute auth={auth} allowedRoles={["ADMIN", "SUPPLY_CHAIN_MANAGER"]}>
              <OrdersPage auth={auth} />
            </ProtectedRoute>
          }
        />

        <Route
          path="inventory-page"
          element={
            <ProtectedRoute auth={auth} allowedRoles={["ADMIN", "SUPPLY_CHAIN_MANAGER"]}>
              <InventoryPage auth={auth} />
            </ProtectedRoute>
          }
        />

        <Route
          path="offers"
          element={
            <ProtectedRoute auth={auth} allowedRoles={["ADMIN", "SUPPLY_CHAIN_MANAGER"]}>
              <OffersPage auth={auth} />
            </ProtectedRoute>
          }
        />

        {/* Supplier dedicated routes */}
        <Route
          path="my-dashboard"
          element={
            <ProtectedRoute auth={auth} allowedRoles={["SUPPLIER"]}>
              <Dashboard />
            </ProtectedRoute>
          }
        />

        <Route
          path="my-products"
          element={
            <ProtectedRoute auth={auth} allowedRoles={["SUPPLIER"]}>
              <ProductsPage auth={auth} mode="supplier" />
            </ProtectedRoute>
          }
        />

        <Route
          path="my-orders"
          element={
            <ProtectedRoute auth={auth} allowedRoles={["SUPPLIER"]}>
              <OrdersPage auth={auth} mode="supplier" />
            </ProtectedRoute>
          }
        />

        <Route
          path="my-offers"
          element={
            <ProtectedRoute auth={auth} allowedRoles={["SUPPLIER"]}>
              <OffersPage auth={auth} mode="supplier" />
            </ProtectedRoute>
          }
        />

        <Route
          path="my-performance"
          element={
            <ProtectedRoute auth={auth} allowedRoles={["SUPPLIER"]}>
              <MyPerformancePage auth={auth} />
            </ProtectedRoute>
          }
        />
      </Route>
    </Routes>
  );
}

export default App;
