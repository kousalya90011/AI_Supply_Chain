import apiClient from "./client";

export async function getSuppliers() {
  const response = await apiClient.get("/api/suppliers");
  return response.data;
}

export async function createSupplier(payload) {
  const response = await apiClient.post("/api/suppliers", payload);
  return response.data;
}

export async function updateSupplier(supplierId, payload) {
  const response = await apiClient.put(`/api/suppliers/${supplierId}`, payload);
  return response.data;
}

export async function deleteSupplier(supplierId) {
  const response = await apiClient.delete(`/api/suppliers/${supplierId}`);
  return response.data;
}
