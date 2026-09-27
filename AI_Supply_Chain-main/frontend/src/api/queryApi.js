import apiClient from "./client";

export async function askSupplyChainQuery(query) {
  const response = await apiClient.post("/api/query", {
    query,
  });

  return response.data;
}