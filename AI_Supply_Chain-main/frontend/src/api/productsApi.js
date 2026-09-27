import apiClient from "./client";

export async function getProducts() {
  const response = await apiClient.get("/api/products");
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

export async function deleteProduct(productId) {
  const response = await apiClient.delete(`/api/products/${productId}`);
  return response.data;
}
