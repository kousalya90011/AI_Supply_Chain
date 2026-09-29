import apiClient from "./client";

export async function getProducts(params = {}) {
  const response = await apiClient.get("/api/products", { params });
  return response.data;
}

export async function getNextProductId() {
  const response = await apiClient.get("/api/products/next-id");
  return response.data;
}

export async function createProduct(payload) {
  const response = await apiClient.post("/api/products", payload);
  return response.data;
}

export async function updateProduct(productId, payload) {
  const response = await apiClient.put(`/api/products/${productId}`, payload);
  return response.data;
}

export async function approveProduct(productId) {
  const response = await apiClient.patch(`/api/products/${productId}/approve`);
  return response.data;
}

export async function rejectProduct(productId, reason = "") {
  const response = await apiClient.patch(`/api/products/${productId}/reject`, { reason });
  return response.data;
}

export async function deleteProduct(productId) {
  const response = await apiClient.delete(`/api/products/${productId}`);
  return response.data;
}
