import apiClient from "./client";

export async function getInventory() {
  const response = await apiClient.get("/api/inventory");
  return response.data;
}

export async function createInventory(payload) {
  const response = await apiClient.post("/api/inventory", payload);
  return response.data;
}

export async function updateInventory(inventoryId, payload) {
  const response = await apiClient.put(`/api/inventory/${inventoryId}`, payload);
  return response.data;
}

export async function deleteInventory(inventoryId) {
  const response = await apiClient.delete(`/api/inventory/${inventoryId}`);
  return response.data;
}
