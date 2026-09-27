import { Routes, Route, Navigate } from "react-router-dom";

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

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Navigate to="/dashboard" replace />} />

        <Route path="dashboard" element={<Dashboard />} />
        <Route path="data" element={<DataStatus />} />
        <Route path="suppliers" element={<SupplierRisk />} />
        <Route path="inventory" element={<InventoryRisk />} />
        <Route path="delivery" element={<DeliveryRisk />} />
        <Route path="routes" element={<RouteRisk />} />
        <Route path="anomalies" element={<Anomalies />} />
        <Route path="forecast" element={<Forecast />} />
        <Route path="ai-assistant" element={<AIQuery />} />
        <Route path="evaluation" element={<Evaluation />} />
        <Route path="audit" element={<Audit />} />
      </Route>
    </Routes>
  );
}

export default App;
