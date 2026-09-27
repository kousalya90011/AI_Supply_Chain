import apiClient from "./client";

export async function getSupplierRiskData() {
  const response = await apiClient.get(
    "/api/analytics/supplier-risk"
  );

  return response.data;
}

export async function getInventoryRiskData() {
  const response = await apiClient.get(
    "/api/analytics/inventory-risk"
  );

  return response.data;
}

export async function getDeliveryRiskData() {
  const response = await apiClient.get(
    "/api/analytics/delivery-risk"
  );

  return response.data;
}

export async function getRouteRiskData() {
  const response = await apiClient.get(
    "/api/analytics/route-risk"
  );

  return response.data;
}

export async function getAnomaliesData() {
  const response = await apiClient.get(
    "/api/analytics/anomalies/orders"
  );

  return response.data;
}

export async function getProductEvidence(productId) {
  const response = await apiClient.get(
    `/api/analytics/evidence/product/${encodeURIComponent(
      productId
    )}`
  );

  return response.data;
}
