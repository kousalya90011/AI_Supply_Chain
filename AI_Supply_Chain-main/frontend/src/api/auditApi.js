import apiClient from "./client";

export async function getRecentAuditLogs() {
  const response = await apiClient.get(
    "/api/audit/recent"
  );

  return response.data;
}
