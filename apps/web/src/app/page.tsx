import React from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import Link from 'next/link';
import { ArrowRight, Search } from 'lucide-react';

export default function HomePage() {
  return (
    <div className="min-h-screen bg-white text-slate-900 flex flex-col items-center justify-center p-6 font-sans">
      <div className="w-full max-w-3xl space-y-8 flex flex-col items-center">
        {/* Header/Brand */}
        <div className="text-center space-y-4">
          <div className="inline-flex items-center justify-center p-3 bg-blue-50 text-blue-600 rounded-full mb-2">
            <Search className="w-8 h-8" />
          </div>
          <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight text-slate-900">
            SRMA Engine
          </h1>
          <p className="text-lg md:text-xl text-slate-600 max-w-2xl mx-auto font-light">
            Professional AI-powered systematic review and meta-analysis platform.
            Enter your research question to begin the protocol development phase.
          </p>
        </div>

        {/* Input Area */}
        <div className="w-full bg-slate-50 border border-slate-200 shadow-sm rounded-2xl p-2 focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-blue-500 transition-all">
          <Textarea
            placeholder="e.g., What is the efficacy of interventions for..."
            className="min-h-[160px] text-lg lg:text-xl border-0 shadow-none focus-visible:ring-0 bg-transparent resize-none placeholder:text-slate-400"
          />
          <div className="flex justify-end pt-2 px-2 pb-2 border-t border-slate-200 mt-2">
            <Link href="/review/123" passHref>
              <Button size="lg" className="bg-blue-600 hover:bg-blue-700 text-white gap-2 font-medium px-8 h-12 rounded-xl text-base">
                Start New Review
                <ArrowRight className="w-5 h-5" />
              </Button>
            </Link>
          </div>
        </div>

        {/* Features/Trust badges conceptually */}
        <div className="flex gap-8 text-sm text-slate-500 pt-8 font-medium">
          <span className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-green-500"></div> HIPAA Compliant
          </span>
          <span className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-blue-500"></div> PRISMA Standard
          </span>
          <span className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-purple-500"></div> Full-Text Analysis
          </span>
        </div>
      </div>
    </div>
  );
}
