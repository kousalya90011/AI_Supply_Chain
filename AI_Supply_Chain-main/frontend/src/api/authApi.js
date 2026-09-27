import apiClient from "./client";

export async function loginUser(username, password) {
  const response = await apiClient.post("/api/auth/login", {
    username,
    password,
  });

  return response.data;
}

export async function getCurrentUser() {
  const response = await apiClient.get("/api/auth/me");
  return response.data;
}

export async function verifySupplierAccess(supplierId) {
  const response = await apiClient.get(
    `/api/auth/verify-supplier-access/${supplierId}`
  );

  return response.data;
}
