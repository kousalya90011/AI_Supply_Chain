import apiClient from "./client";

export async function getProductSales() {
  const response = await apiClient.get("/api/analytics/product-sales");
  return response.data;
}

export async function getSupplierEvidence(supplierId) {
  const response = await apiClient.get(
    `/api/analytics/evidence/supplier/${encodeURIComponent(supplierId)}`
  );
  return response.data;
}

export async function getProductEvidence(productId) {
  const response = await apiClient.get(
    `/api/analytics/evidence/product/${encodeURIComponent(productId)}`
  );
  return response.data;
}
