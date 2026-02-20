import axios, { AxiosError } from "axios";
import type {
  Review,
  ReviewListResponse,
  CreateReviewPayload,
  UpdateReviewPayload,
  Paper,
  PaperListResponse,
} from "./types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.response.use(
  (res) => res,
  (err: AxiosError) => {
    const message =
      (err.response?.data as { detail?: string })?.detail ?? err.message;
    console.error("[API]", err.config?.url, message);
    return Promise.reject(err);
  }
);

// ─── Reviews ──────────────────────────────────────────────────────────────────

export const reviewsApi = {
  list: (params?: { skip?: number; limit?: number }) =>
    api.get<ReviewListResponse>("/api/v1/reviews", { params }),

  get: (id: string) =>
    api.get<Review>(`/api/v1/reviews/${id}`),

  create: (data: CreateReviewPayload) =>
    api.post<Review>("/api/v1/reviews", data),

  update: (id: string, data: UpdateReviewPayload) =>
    api.patch<Review>(`/api/v1/reviews/${id}`, data),

  delete: (id: string) =>
    api.delete(`/api/v1/reviews/${id}`),
};

// ─── Papers ───────────────────────────────────────────────────────────────────

export const papersApi = {
  list: (params?: {
    skip?: number;
    limit?: number;
    review_id?: string;
    query?: string;
  }) => api.get<PaperListResponse>("/api/v1/papers", { params }),

  get: (id: string) =>
    api.get<Paper>(`/api/v1/papers/${id}`),

  upload: (file: File, reviewId?: string) => {
    const form = new FormData();
    form.append("file", file);
    if (reviewId) form.append("review_id", reviewId);
    return api.post<Paper>("/api/v1/papers", form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },

  update: (id: string, data: { screening_label?: string; status?: string }) =>
    api.patch<Paper>(`/api/v1/papers/${id}`, data),

  delete: (id: string) =>
    api.delete(`/api/v1/papers/${id}`),
};
