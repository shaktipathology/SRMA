import axios from "axios";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL: API_BASE,
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error("API error:", error.response?.data || error.message);
    return Promise.reject(error);
  }
);

export const papersApi = {
  list: (params?: { skip?: number; limit?: number; query?: string }) =>
    api.get("/api/v1/papers", { params }),
  get: (id: string) => api.get(`/api/v1/papers/${id}`),
  upload: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return api.post("/api/v1/papers", form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
};

export const reviewsApi = {
  list: (params?: { skip?: number; limit?: number }) =>
    api.get("/api/v1/reviews", { params }),
  get: (id: string) => api.get(`/api/v1/reviews/${id}`),
  create: (data: { title: string; description?: string }) =>
    api.post("/api/v1/reviews", data),
};
