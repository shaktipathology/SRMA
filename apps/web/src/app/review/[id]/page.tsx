"use client";

import React from "react";
import Link from "next/link";
import {
  AlertCircle,
  ArrowLeft,
  Award,
  BarChart,
  BookOpen,
  CheckCircle2,
  CheckSquare,
  Circle,
  Database,
  Edit3,
  FileCheck,
  FileText,
  LayoutTemplate,
  Loader2,
  Search,
  ShieldAlert,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { PhaseWrapper } from "@/components/PhaseWrapper";
import { useReview, usePapers } from "@/lib/queries";

const PHASES = [
  { id: 1, name: "Protocol Dev", icon: FileText },
  { id: 2, name: "Search", icon: Search },
  { id: 3, name: "Screening", icon: CheckSquare },
  { id: 4, name: "Full-Text Review", icon: BookOpen },
  { id: 5, name: "Data Extraction", icon: Database },
  { id: 6, name: "Quality Assess", icon: ShieldAlert },
  { id: 7, name: "Synthesis", icon: Edit3 },
  { id: 8, name: "Meta-Analysis", icon: BarChart },
  { id: 9, name: "Drafting", icon: LayoutTemplate },
  { id: 10, name: "Formatting", icon: FileCheck },
  { id: 11, name: "Final Report", icon: Award },
];

// Map review status → which phase index is "active"
const STATUS_PHASE: Record<string, number> = {
  draft: 1,
  active: 2,
  completed: 11,
  archived: 11,
};

type PhaseStatus = "complete" | "running" | "gate" | "pending";

function getPhaseStatus(phaseId: number, activePhase: number): PhaseStatus {
  if (phaseId < activePhase) return "complete";
  if (phaseId === activePhase) return "running";
  return "pending";
}

function StatusIcon({ status }: { status: PhaseStatus }) {
  if (status === "complete")
    return <CheckCircle2 className="w-5 h-5 text-blue-500 fill-blue-50" />;
  if (status === "gate")
    return <AlertCircle className="w-5 h-5 text-orange-500 fill-orange-50" />;
  if (status === "running")
    return <Loader2 className="w-5 h-5 text-emerald-500 animate-spin" />;
  return <Circle className="w-5 h-5 text-slate-600 fill-slate-800" />;
}

const STATUS_BADGE: Record<string, string> = {
  draft: "bg-slate-100 text-slate-600",
  active: "bg-blue-100 text-blue-700",
  completed: "bg-green-100 text-green-700",
  archived: "bg-orange-100 text-orange-700",
};

export default function ReviewDashboard({
  params,
}: {
  params: { id: string };
}) {
  const { data: review, isLoading, isError } = useReview(params.id);
  const { data: papers } = usePapers({ review_id: params.id, limit: 100 });

  const activePhase = review ? STATUS_PHASE[review.status] ?? 1 : 1;
  const includedCount =
    papers?.papers.filter((p) => p.screening_label === "include").length ?? 0;
  const screenedCount =
    papers?.papers.filter(
      (p) => p.screening_label !== null
    ).length ?? 0;
  const totalCount = papers?.total ?? 0;

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center gap-3 text-slate-400 bg-slate-50">
        <Loader2 className="w-5 h-5 animate-spin" />
        <span>Loading review…</span>
      </div>
    );
  }

  if (isError || !review) {
    return (
      <div className="flex h-screen flex-col items-center justify-center gap-4 bg-slate-50 text-slate-600">
        <AlertCircle className="w-10 h-10 text-red-400" />
        <p className="text-lg font-semibold">Review not found</p>
        <Link href="/reviews" className="text-blue-600 hover:underline text-sm">
          ← Back to all reviews
        </Link>
      </div>
    );
  }

  return (
    <div className="flex h-screen w-full bg-slate-50 overflow-hidden font-sans">
      {/* Sidebar */}
      <div className="w-72 bg-slate-900 text-slate-200 flex flex-col shrink-0 overflow-y-auto border-r border-slate-800">
        <div className="p-6 border-b border-slate-800">
          <Link
            href="/reviews"
            className="flex items-center gap-2 text-xs text-slate-500 hover:text-slate-300 transition-colors mb-4"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            All reviews
          </Link>
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center font-bold text-white shrink-0">
              SR
            </div>
            <div className="min-w-0">
              <h2 className="font-semibold text-white tracking-wide truncate text-sm">
                {review.title}
              </h2>
              <Badge className={`mt-1 text-xs ${STATUS_BADGE[review.status] ?? ""}`}>
                {review.status}
              </Badge>
            </div>
          </div>
        </div>

        <div className="flex-1 p-6 relative">
          <div className="absolute left-10 top-10 bottom-10 w-0.5 bg-slate-800 hidden sm:block" />
          <div className="space-y-6 relative z-10">
            {PHASES.map((phase) => {
              const status = getPhaseStatus(phase.id, activePhase);
              return (
                <div key={phase.id} className="flex items-start gap-4">
                  <div className="bg-slate-900 rounded-full mt-0.5 shrink-0">
                    <StatusIcon status={status} />
                  </div>
                  <div className="flex flex-col">
                    <span
                      className={`font-medium text-sm ${
                        status === "complete"
                          ? "text-slate-300"
                          : status === "gate"
                          ? "text-orange-400 font-semibold"
                          : status === "running"
                          ? "text-emerald-400 font-semibold"
                          : "text-slate-500"
                      }`}
                    >
                      Phase {phase.id}: {phase.name}
                    </span>
                    <span className="text-xs uppercase tracking-wider text-slate-600 mt-0.5 font-semibold">
                      {status === "gate" ? "Human Gate" : status}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Main panel */}
      <div className="flex-1 flex flex-col h-full bg-white relative overflow-hidden">
        {/* Top bar */}
        <div className="h-20 border-b border-slate-200 flex items-center justify-between px-8 bg-white/80 backdrop-blur-md z-10 shrink-0">
          <h1 className="text-xl font-bold text-slate-800 tracking-tight">
            Phase {activePhase}:{" "}
            {PHASES.find((p) => p.id === activePhase)?.name}
          </h1>
          <div className="flex items-center gap-3">
            <span className="text-sm font-semibold text-slate-400 uppercase tracking-widest mr-2">
              Papers
            </span>
            <Badge className="bg-slate-100 text-slate-700 px-3 py-1 font-medium text-sm">
              Total: {totalCount}
            </Badge>
            <Badge className="bg-slate-100 text-slate-700 px-3 py-1 font-medium text-sm">
              Screened: {screenedCount}
            </Badge>
            <Badge className="bg-green-100 text-green-700 px-3 py-1 font-medium text-sm">
              Included: {includedCount}
            </Badge>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-8">
          <div className="max-w-4xl mx-auto pb-32">
            <PhaseWrapper
              title={`Phase ${activePhase} — ${review.title}`}
              description={
                review.description ??
                "Review the current phase output before proceeding."
              }
              status={activePhase < 11 ? "gate" : "complete"}
              requiresApproval={activePhase < 11}
            >
              <div className="space-y-2 text-slate-600 font-mono text-sm">
                <div className="flex gap-3">
                  <span className="text-slate-400 select-none">
                    [info]
                  </span>
                  <span>
                    Review ID: <span className="text-slate-900">{review.id}</span>
                  </span>
                </div>
                <div className="flex gap-3">
                  <span className="text-slate-400 select-none">
                    [info]
                  </span>
                  <span>
                    Status: <span className="text-slate-900">{review.status}</span>
                  </span>
                </div>
                <div className="flex gap-3">
                  <span className="text-slate-400 select-none">
                    [info]
                  </span>
                  <span>
                    Papers in corpus: <span className="text-slate-900">{totalCount}</span>
                  </span>
                </div>
                {totalCount === 0 && (
                  <div className="flex gap-3 mt-4">
                    <span className="text-orange-400 select-none">
                      [wait]
                    </span>
                    <span className="text-orange-600">
                      No papers uploaded yet. Upload PDFs via the API to begin
                      processing.
                    </span>
                  </div>
                )}
              </div>
            </PhaseWrapper>
          </div>
        </div>

        {/* Decorative blur */}
        <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-blue-50/50 rounded-full blur-3xl -z-10 pointer-events-none -translate-y-1/2 translate-x-1/3" />
      </div>
    </div>
  );
}
