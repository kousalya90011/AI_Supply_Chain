import apiClient from "./client";

export async function getOffers(params = {}) {
  const response = await apiClient.get("/api/offers", { params });
  return response.data;
}

export async function createOffer(payload) {
  const response = await apiClient.post("/api/offers", payload);
  return response.data;
}

export async function updateOffer(offerId, payload) {
  const response = await apiClient.put(`/api/offers/${offerId}`, payload);
  return response.data;
}

export async function acceptOffer(offerId) {
  const response = await apiClient.patch(`/api/offers/${offerId}/accept`, {});
  return response.data;
}

export async function rejectOffer(offerId) {
  const response = await apiClient.patch(`/api/offers/${offerId}/reject`);
  return response.data;
}

export async function withdrawOffer(offerId) {
  const response = await apiClient.patch(`/api/offers/${offerId}/withdraw`);
  return response.data;
}

export async function deleteOffer(offerId) {
  const response = await apiClient.delete(`/api/offers/${offerId}`);
  return response.data;
}
