import apiClient from "./client";

export async function getDataStatus() {
  const response = await apiClient.get("/api/data/status");
  return response.data;
}

export async function getDataColumns() {
  const response = await apiClient.get("/api/data/columns");
  return response.data;
}
