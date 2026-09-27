import apiClient from "./client";

export async function getEvaluationSummary() {
  const response = await apiClient.get(
    "/api/evaluation/summary"
  );

  return response.data;
}

export async function getRoutingEvaluation() {
  const response = await apiClient.get(
    "/api/evaluation/routing"
  );

  return response.data;
}

export async function getForecastEvaluation(productId) {
  const response = await apiClient.get(
    `/api/evaluation/forecast/${encodeURIComponent(
      productId
    )}`
  );

  return response.data;
}

export async function runEvaluation() {
  const response = await apiClient.post(
    "/api/evaluation/run"
  );

  return response.data;
}
