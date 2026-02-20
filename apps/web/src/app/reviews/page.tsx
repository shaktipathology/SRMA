"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  ArrowRight,
  Clock,
  FileText,
  Loader2,
  Plus,
  Trash2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useReviews, useDeleteReview } from "@/lib/queries";
import type { Review, ReviewStatus } from "@/lib/types";

const STATUS_STYLES: Record<ReviewStatus, string> = {
  draft: "bg-slate-100 text-slate-600",
  active: "bg-blue-100 text-blue-700",
  completed: "bg-green-100 text-green-700",
  archived: "bg-orange-100 text-orange-700",
};

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function ReviewCard({ review }: { review: Review }) {
  const deleteReview = useDeleteReview();

  return (
    <div className="group flex items-start justify-between gap-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm hover:border-blue-300 hover:shadow-md transition-all">
      <div className="flex items-start gap-4 min-w-0">
        <div className="mt-0.5 shrink-0 rounded-lg bg-slate-100 p-2.5 text-slate-500">
          <FileText className="w-5 h-5" />
        </div>
        <div className="min-w-0">
          <Link
            href={`/review/${review.id}`}
            className="font-semibold text-slate-900 hover:text-blue-600 transition-colors line-clamp-2"
          >
            {review.title}
          </Link>
          {review.description && (
            <p className="mt-1 text-sm text-slate-500 line-clamp-1">
              {review.description}
            </p>
          )}
          <div className="mt-2 flex items-center gap-3 text-xs text-slate-400">
            <Clock className="w-3.5 h-3.5" />
            <span>Created {formatDate(review.created_at)}</span>
          </div>
        </div>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <Badge className={STATUS_STYLES[review.status]}>
          {review.status}
        </Badge>
        <Button
          variant="ghost"
          size="icon"
          className="opacity-0 group-hover:opacity-100 transition-opacity text-slate-400 hover:text-red-500 hover:bg-red-50"
          onClick={() => {
            if (confirm(`Delete "${review.title}"?`)) {
              deleteReview.mutate(review.id);
            }
          }}
        >
          <Trash2 className="w-4 h-4" />
        </Button>
        <Link href={`/review/${review.id}`}>
          <Button variant="ghost" size="icon" className="text-slate-400 hover:text-blue-600 hover:bg-blue-50">
            <ArrowRight className="w-4 h-4" />
          </Button>
        </Link>
      </div>
    </div>
  );
}

export default function ReviewsPage() {
  const router = useRouter();
  const { data, isLoading, isError } = useReviews({ limit: 50 });

  return (
    <div className="min-h-screen bg-slate-50 font-sans">
      {/* Header */}
      <header className="border-b border-slate-200 bg-white px-6 py-4">
        <div className="mx-auto max-w-4xl flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link
              href="/"
              className="text-slate-400 hover:text-slate-700 transition-colors"
            >
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <h1 className="text-xl font-bold text-slate-900">All Reviews</h1>
            {data && (
              <span className="text-sm text-slate-400">
                ({data.total} total)
              </span>
            )}
          </div>
          <Button
            onClick={() => router.push("/")}
            className="bg-blue-600 hover:bg-blue-700 text-white gap-2"
          >
            <Plus className="w-4 h-4" />
            New Review
          </Button>
        </div>
      </header>

      {/* Content */}
      <main className="mx-auto max-w-4xl px-6 py-8">
        {isLoading && (
          <div className="flex items-center justify-center py-24 gap-3 text-slate-400">
            <Loader2 className="w-5 h-5 animate-spin" />
            <span>Loading reviews…</span>
          </div>
        )}

        {isError && (
          <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-center">
            <p className="text-red-600 font-medium">
              Could not load reviews. Is the API running?
            </p>
            <p className="mt-1 text-sm text-red-400">
              Make sure the FastAPI server is up at{" "}
              <code className="font-mono">
                {process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}
              </code>
            </p>
          </div>
        )}

        {data && data.reviews.length === 0 && (
          <div className="flex flex-col items-center justify-center py-24 gap-4 text-slate-400">
            <FileText className="w-12 h-12" />
            <p className="text-lg font-medium">No reviews yet</p>
            <Button
              onClick={() => router.push("/")}
              variant="outline"
              className="gap-2"
            >
              <Plus className="w-4 h-4" />
              Create your first review
            </Button>
          </div>
        )}

        {data && data.reviews.length > 0 && (
          <div className="space-y-3">
            {data.reviews.map((review) => (
              <ReviewCard key={review.id} review={review} />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
