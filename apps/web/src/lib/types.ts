// ─── Reviews ──────────────────────────────────────────────────────────────────

export type ReviewStatus = "draft" | "active" | "completed" | "archived";

export interface Review {
  id: string;
  title: string;
  description: string | null;
  status: ReviewStatus;
  created_at: string;
  updated_at: string;
}

export interface ReviewListResponse {
  reviews: Review[];
  total: number;
  skip: number;
  limit: number;
}

export interface CreateReviewPayload {
  title: string;
  description?: string;
}

export interface UpdateReviewPayload {
  title?: string;
  description?: string;
  status?: ReviewStatus;
}

// ─── Papers ───────────────────────────────────────────────────────────────────

export type PaperStatus = "pending" | "processing" | "ready" | "error";
export type ScreeningLabel = "include" | "exclude" | "maybe";

export interface Paper {
  id: string;
  review_id: string | null;
  title: string | null;
  abstract: string | null;
  authors: unknown;
  year: number | null;
  doi: string | null;
  status: PaperStatus;
  screening_label: ScreeningLabel | null;
  created_at: string;
  updated_at: string;
}

export interface PaperListResponse {
  papers: Paper[];
  total: number;
  skip: number;
  limit: number;
}

// ─── API error ────────────────────────────────────────────────────────────────

export interface ApiError {
  detail: string;
}
