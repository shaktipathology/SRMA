"use client";

import {
  useQuery,
  useMutation,
  useQueryClient,
  queryOptions,
} from "@tanstack/react-query";
import { reviewsApi, papersApi } from "./api";
import type { CreateReviewPayload, UpdateReviewPayload } from "./types";

// ─── Query key factory ────────────────────────────────────────────────────────

export const queryKeys = {
  reviews: {
    all: ["reviews"] as const,
    list: (params?: { skip?: number; limit?: number }) =>
      ["reviews", "list", params] as const,
    detail: (id: string) => ["reviews", "detail", id] as const,
  },
  papers: {
    all: ["papers"] as const,
    list: (params?: {
      skip?: number;
      limit?: number;
      review_id?: string;
      query?: string;
    }) => ["papers", "list", params] as const,
    detail: (id: string) => ["papers", "detail", id] as const,
  },
};

// ─── Reviews ──────────────────────────────────────────────────────────────────

export function useReviews(params?: { skip?: number; limit?: number }) {
  return useQuery({
    queryKey: queryKeys.reviews.list(params),
    queryFn: () => reviewsApi.list(params).then((r) => r.data),
  });
}

export function useReview(id: string) {
  return useQuery({
    queryKey: queryKeys.reviews.detail(id),
    queryFn: () => reviewsApi.get(id).then((r) => r.data),
    enabled: !!id,
  });
}

export function useCreateReview() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: CreateReviewPayload) =>
      reviewsApi.create(data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.reviews.all }),
  });
}

export function useUpdateReview(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: UpdateReviewPayload) =>
      reviewsApi.update(id, data).then((r) => r.data),
    onSuccess: (updated) => {
      qc.setQueryData(queryKeys.reviews.detail(id), updated);
      qc.invalidateQueries({ queryKey: queryKeys.reviews.all });
    },
  });
}

export function useDeleteReview() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => reviewsApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.reviews.all }),
  });
}

// ─── Papers ───────────────────────────────────────────────────────────────────

export function usePapers(params?: {
  skip?: number;
  limit?: number;
  review_id?: string;
  query?: string;
}) {
  return useQuery({
    queryKey: queryKeys.papers.list(params),
    queryFn: () => papersApi.list(params).then((r) => r.data),
  });
}

export function usePaper(id: string) {
  return useQuery({
    queryKey: queryKeys.papers.detail(id),
    queryFn: () => papersApi.get(id).then((r) => r.data),
    enabled: !!id,
  });
}
