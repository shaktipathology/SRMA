import React from 'react';
import { Badge } from '@/components/ui/badge';
import { PhaseWrapper } from '@/components/PhaseWrapper';
import {
    CheckCircle2,
    Circle,
    Loader2,
    AlertCircle,
    FileText,
    Search,
    CheckSquare,
    BookOpen,
    Database,
    ShieldAlert,
    Edit3,
    BarChart,
    LayoutTemplate,
    FileCheck,
    Award
} from 'lucide-react';

const PHASES = [
    { id: 1, name: 'Protocol Dev', status: 'complete', icon: FileText },
    { id: 2, name: 'Search', status: 'complete', icon: Search },
    { id: 3, name: 'Screening', status: 'complete', icon: CheckSquare },
    { id: 4, name: 'Full-Text Review', status: 'complete', icon: BookOpen },
    { id: 5, name: 'Data Extraction', status: 'gate', icon: Database },
    { id: 6, name: 'Quality Assess', status: 'running', icon: ShieldAlert },
    { id: 7, name: 'Synthesis', status: 'pending', icon: Edit3 },
    { id: 8, name: 'Meta-Analysis', status: 'pending', icon: BarChart },
    { id: 9, name: 'Drafting', status: 'pending', icon: LayoutTemplate },
    { id: 10, name: 'Formatting', status: 'pending', icon: FileCheck },
    { id: 11, name: 'Final Report', status: 'pending', icon: Award },
];

function StatusIcon({ status }: { status: string }) {
    if (status === 'complete') {
        return <CheckCircle2 className="w-5 h-5 text-blue-500 fill-blue-50" />;
    }
    if (status === 'gate') {
        return <AlertCircle className="w-5 h-5 text-orange-500 fill-orange-50" />;
    }
    if (status === 'running') {
        return <Loader2 className="w-5 h-5 text-emerald-500 animate-spin" />;
    }
    return <Circle className="w-5 h-5 text-gray-600 fill-gray-800" />;
}

export default function ReviewDashboard({ params }: { params: { id: string } }) {
    return (
        <div className="flex h-screen w-full bg-slate-50 overflow-hidden font-sans">
            {/* Dark Sidebar */}
            <div className="w-72 bg-slate-900 text-slate-200 flex flex-col shrink-0 overflow-y-auto border-r border-slate-800">
                <div className="p-6 border-b border-slate-800 flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center font-bold text-white shadow-inner">
                        SR
                    </div>
                    <div>
                        <h2 className="font-semibold text-white tracking-wide">Project #{params.id}</h2>
                        <p className="text-xs text-slate-400">Cardiology Systematic Review</p>
                    </div>
                </div>

                <div className="flex-1 p-6 relative">
                    <div className="absolute left-10 top-10 bottom-10 w-0.5 bg-slate-800 hidden sm:block"></div>
                    <div className="space-y-6 relative z-10">
                        {PHASES.map((phase, idx) => (
                            <div key={phase.id} className="flex items-start gap-4">
                                <div className="bg-slate-900 rounded-full mt-0.5">
                                    <StatusIcon status={phase.status} />
                                </div>
                                <div className="flex flex-col">
                                    <span className={`font-medium ${phase.status === 'complete' ? 'text-slate-300' :
                                            phase.status === 'gate' ? 'text-orange-400 font-semibold' :
                                                phase.status === 'running' ? 'text-emerald-400 font-semibold' :
                                                    'text-slate-500'
                                        }`}>
                                        Phase {phase.id}: {phase.name}
                                    </span>
                                    <span className="text-xs uppercase tracking-wider text-slate-500 mt-0.5 font-semibold">
                                        {phase.status === 'gate' ? 'Human Gate' : phase.status}
                                    </span>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* Main Panel */}
            <div className="flex-1 flex flex-col h-full bg-white relative">
                {/* Top Navigation & Badges */}
                <div className="h-20 border-b border-slate-200 flex items-center justify-between px-8 bg-white/80 backdrop-blur-md z-10">
                    <h1 className="text-xl font-bold text-slate-800 tracking-tight">Phase 5: Data Extraction</h1>
                    <div className="flex items-center gap-3">
                        <span className="text-sm font-semibold text-slate-400 uppercase tracking-widest mr-2">PRISMA Counts</span>
                        <Badge variant="secondary" className="bg-slate-100 text-slate-700 hover:bg-slate-200 px-3 py-1 font-medium text-sm">
                            Identified: 24,500
                        </Badge>
                        <Badge variant="secondary" className="bg-slate-100 text-slate-700 hover:bg-slate-200 px-3 py-1 font-medium text-sm">
                            Screened: 12,000
                        </Badge>
                        <Badge variant="secondary" className="bg-slate-100 text-slate-700 hover:bg-slate-200 px-3 py-1 font-medium text-sm">
                            Included: 500
                        </Badge>
                    </div>
                </div>

                {/* Content Area */}
                <div className="flex-1 overflow-y-auto p-8 relative">
                    <div className="max-w-4xl mx-auto pb-32">
                        <PhaseWrapper
                            title="Phase 5 Output"
                            description="Review extracted entities and confidence scores before proceeding to Quality Assessment."
                            status="gate"
                            requiresApproval
                        >
                            {[
                                "Initializing local context window for 500 included studies...",
                                "Loading pre-trained medical NER models...",
                                "Analyzing study abstracts...",
                                "Extracting data points: population demographics, interventions, primary outcomes...",
                                "Cross-referencing extracted variables with inclusion criteria...",
                                "Found discrepancies in 12 studies regarding dosage formatting. Normalizing to mg/kg...",
                                "Confidence score moving average: 92%...",
                                "Preparing summary table of extracted characteristics..."
                            ].map((line, i) => (
                                <div key={i} className="mb-2 flex items-start gap-3 opacity-90 hover:opacity-100 transition-opacity">
                                    <span className="text-slate-400 select-none min-w-[80px]">[{new Date().toISOString().split('T')[1].substring(0, 8)}]</span>
                                    <span className={i >= 6 ? 'font-medium text-slate-900' : 'text-slate-600'}>{line}</span>
                                </div>
                            ))}
                        </PhaseWrapper>
                    </div>
                </div>

                {/* Subtle decorative elements */}
                <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-blue-50/50 rounded-full blur-3xl -z-10 pointer-events-none -translate-y-1/2 translate-x-1/3"></div>
            </div>
        </div>
    );
}
