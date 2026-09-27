import apiClient from "./client";

export async function getOrders() {
  const response = await apiClient.get("/api/orders");
  return response.data;
}

export async function createOrder(payload) {
  const response = await apiClient.post("/api/orders", payload);
  return response.data;
}

export async function updateOrder(orderId, payload) {
  const response = await apiClient.put(`/api/orders/${orderId}`, payload);
  return response.data;
}

export async function deleteOrder(orderId) {
  const response = await apiClient.delete(`/api/orders/${orderId}`);
  return response.data;
}
