import apiClient from "./client";

export async function getUsers() {
  const response = await apiClient.get("/api/users");
  return response.data;
}

export async function createUser(payload) {
  const response = await apiClient.post("/api/users", payload);
  return response.data;
}

export async function updateUser(userId, payload) {
  const response = await apiClient.put(`/api/users/${userId}`, payload);
  return response.data;
}

export async function deleteUser(userId) {
  const response = await apiClient.delete(`/api/users/${userId}`);
  return response.data;
}
