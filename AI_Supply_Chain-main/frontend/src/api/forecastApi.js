import apiClient from "./client";

export async function getForecastProducts() {
  const response = await apiClient.get(
    "/api/forecast/products"
  );

  return response.data;
}

export async function getProductForecast(productId) {
  const response = await apiClient.get(
    `/api/forecast/product/${encodeURIComponent(productId)}`
  );

  return response.data;
}