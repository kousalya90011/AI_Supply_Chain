import axios from "axios";

const apiClient = axios.create({
  baseURL:
    import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000",
  timeout: 30000,
  headers: {
    "Content-Type": "application/json",
  },
});

apiClient.interceptors.request.use((config) => {
  const savedAuth = localStorage.getItem("sc_auth");

  if (savedAuth) {
    try {
      const auth = JSON.parse(savedAuth);
      if (auth?.token) {
        config.headers = config.headers || {};
        config.headers.Authorization = `Bearer ${auth.token}`;
      }
    } catch {
      // Ignore malformed stored auth state.
    }
  }

  return config;
});

export default apiClient;