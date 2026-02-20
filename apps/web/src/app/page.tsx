"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowRight, BookOpen, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useCreateReview } from "@/lib/queries";

export default function HomePage() {
  const router = useRouter();
  const [question, setQuestion] = useState("");
  const [error, setError] = useState<string | null>(null);
  const createReview = useCreateReview();

  async function handleStart() {
    const title = question.trim();
    if (!title) {
      setError("Please enter a research question.");
      return;
    }
    setError(null);
    try {
      const review = await createReview.mutateAsync({ title });
      router.push(`/review/${review.id}`);
    } catch {
      setError("Could not create review. Is the API running?");
    }
  }

  return (
    <div className="min-h-screen bg-white text-slate-900 flex flex-col items-center justify-center p-6 font-sans">
      <div className="w-full max-w-3xl space-y-8 flex flex-col items-center">
        {/* Header */}
        <div className="text-center space-y-4">
          <div className="inline-flex items-center justify-center p-3 bg-blue-50 text-blue-600 rounded-full mb-2">
            <Search className="w-8 h-8" />
          </div>
          <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight text-slate-900">
            SRMA Engine
          </h1>
          <p className="text-lg md:text-xl text-slate-600 max-w-2xl mx-auto font-light">
            Professional AI-powered systematic review and meta-analysis platform.
            Enter your research question to begin.
          </p>
        </div>

        {/* Input */}
        <div className="w-full bg-slate-50 border border-slate-200 shadow-sm rounded-2xl p-2 focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-blue-500 transition-all">
          <Textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="e.g., What is the efficacy of interventions for treatment-resistant depression?"
            className="min-h-[160px] text-lg lg:text-xl border-0 shadow-none focus-visible:ring-0 bg-transparent resize-none placeholder:text-slate-400"
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) handleStart();
            }}
          />
          <div className="flex items-center justify-between pt-2 px-2 pb-2 border-t border-slate-200 mt-2">
            <span className="text-xs text-slate-400">
              {error ? (
                <span className="text-red-500">{error}</span>
              ) : (
                "⌘+Enter to start"
              )}
            </span>
            <Button
              size="lg"
              onClick={handleStart}
              disabled={createReview.isPending}
              className="bg-blue-600 hover:bg-blue-700 text-white gap-2 font-medium px-8 h-12 rounded-xl text-base"
            >
              {createReview.isPending ? "Creating…" : "Start New Review"}
              <ArrowRight className="w-5 h-5" />
            </Button>
          </div>
        </div>

        {/* Browse link */}
        <Link
          href="/reviews"
          className="flex items-center gap-2 text-sm text-slate-500 hover:text-blue-600 transition-colors"
        >
          <BookOpen className="w-4 h-4" />
          Browse existing reviews
        </Link>

        {/* Feature badges */}
        <div className="flex flex-wrap justify-center gap-8 text-sm text-slate-500 pt-4 font-medium">
          <span className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-green-500 shrink-0" />
            PRISMA Standard
          </span>
          <span className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-blue-500 shrink-0" />
            Full-Text Analysis
          </span>
          <span className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-purple-500 shrink-0" />
            R Meta-Analysis
          </span>
        </div>
      </div>
    </div>
  );
}
