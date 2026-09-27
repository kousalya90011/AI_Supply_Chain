import apiClient from "./client";

export async function getBackendHealth() {
  const response = await apiClient.get("/health");
  return response.data;
}

export async function getDashboardMetrics() {
  const response = await apiClient.get("/api/analytics/dashboard");
  return response.data;
}

export async function getSupplierRisk() {
  const response = await apiClient.get("/api/analytics/supplier-risk");
  return response.data;
}

export async function getInventoryRisk() {
  const response = await apiClient.get("/api/analytics/inventory-risk");
  return response.data;
}

export async function getDeliveryRisk() {
  const response = await apiClient.get("/api/analytics/delivery-risk");
  return response.data;
}

export async function getRouteRisk() {
  const response = await apiClient.get("/api/analytics/route-risk");
  return response.data;
}