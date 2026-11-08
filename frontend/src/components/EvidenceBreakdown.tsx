import React from 'react';
import { ResumeQualityBreakdown } from '../types';
import { BarChart3, Cpu, Link2 } from 'lucide-react';

interface EvidenceBreakdownProps {
  breakdown: ResumeQualityBreakdown | null;
  projectQualityScore?: number | null;
}

export const EvidenceBreakdown: React.FC<EvidenceBreakdownProps> = ({
  breakdown,
  projectQualityScore = 0,
}) => {
  if (!breakdown) {
    return null;
  }

  const metrics = breakdown.detected_metrics || [];
  const stack = breakdown.detected_production_stack || [];
  const proof = breakdown.detected_proof_links || [];

  return (
    <div className="w-full rounded-xl border border-black/15 dark:border-white/15 bg-canvas-card dark:bg-black/30 p-6 shadow-crisp">
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-5 border-b border-black/10 dark:border-white/10 gap-3">
        <div>
          <h3 className="font-display text-lg font-bold tracking-tight text-[#111111] dark:text-[#F3EEE3]">
            Resume Evidence & Impact Audit
          </h3>
          <p className="text-xs text-neutral-600 dark:text-neutral-400 mt-1">
            Human-grade evaluation separating verifiable engineering outcomes from superficial keyword listings.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-neutral-500">
            Overall Rigor:
          </span>
          <span className="font-mono text-sm font-bold px-2.5 py-1 rounded-md bg-[#D9541E] text-white">
            {projectQualityScore?.toFixed(1) || '0.0'}%
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-6">
        {/* Column 1: Quantitative Metrics */}
        <div className="flex flex-col space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-[#D9541E]" />
              <h4 className="font-display text-sm font-bold text-[#111111] dark:text-[#F3EEE3]">
                Quantitative Impact
              </h4>
            </div>
            <span className="font-mono text-xs font-bold text-[#111111] dark:text-[#F3EEE3]">
              {breakdown.quantitative_metrics_score.toFixed(1)}%
            </span>
          </div>
          <p className="text-xs text-neutral-600 dark:text-neutral-400 leading-relaxed">
            Concrete performance numbers, latency drops, accuracy scores, and throughput metrics demonstrating tangible project impact.
          </p>
          <div className="flex flex-wrap gap-1.5 pt-1">
            {metrics.length > 0 ? (
              metrics.map((m, idx) => (
                <span
                  key={idx}
                  className="font-mono text-xs px-2 py-0.5 rounded bg-black/5 dark:bg-white/10 border border-black/10 dark:border-white/10 text-neutral-800 dark:text-neutral-200"
                >
                  {m}
                </span>
              ))
            ) : (
              <span className="text-xs italic text-neutral-400">
                No measurable impact metrics detected. Consider adding quantitative metrics (e.g. 87% accuracy, 35% latency reduction).
              </span>
            )}
          </div>
        </div>

        {/* Column 2: Project-Verified Competencies */}
        <div className="flex flex-col space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Cpu className="w-4 h-4 text-[#D9541E]" />
              <h4 className="font-display text-sm font-bold text-[#111111] dark:text-[#F3EEE3]">
                Project-Verified Stack
              </h4>
            </div>
            <span className="font-mono text-xs font-bold text-[#111111] dark:text-[#F3EEE3]">
              {breakdown.production_proof_score.toFixed(1)}%
            </span>
          </div>
          <p className="text-xs text-neutral-600 dark:text-neutral-400 leading-relaxed">
            Tools and frameworks validated inside narrative project and work experience implementations rather than standalone keyword lists.
          </p>
          <div className="flex flex-wrap gap-1.5 pt-1">
            {stack.length > 0 ? (
              stack.map((s, idx) => (
                <span
                  key={idx}
                  className="font-mono text-xs px-2 py-0.5 rounded bg-[#D9541E]/10 border border-[#D9541E]/20 text-[#D9541E] dark:text-[#F3EEE3] font-medium"
                >
                  {s}
                </span>
              ))
            ) : (
              <span className="text-xs italic text-neutral-400">
                No competencies evidenced in project descriptions.
              </span>
            )}
          </div>
        </div>

        {/* Column 3: Verifiable Proof & Credentials */}
        <div className="flex flex-col space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Link2 className="w-4 h-4 text-[#D9541E]" />
              <h4 className="font-display text-sm font-bold text-[#111111] dark:text-[#F3EEE3]">
                Verifiable Proof & Links
              </h4>
            </div>
            <span className="font-mono text-xs font-bold text-[#111111] dark:text-[#F3EEE3]">
              {breakdown.role_alignment_score.toFixed(1)}%
            </span>
          </div>
          <p className="text-xs text-neutral-600 dark:text-neutral-400 leading-relaxed">
            Public repository links, live deployed endpoints, published articles, and credentials enabling third-party verification.
          </p>
          <div className="flex flex-wrap gap-1.5 pt-1">
            {proof.length > 0 ? (
              proof.map((p, idx) => (
                <span
                  key={idx}
                  className="font-mono text-xs px-2 py-0.5 rounded bg-black/5 dark:bg-white/10 border border-black/10 dark:border-white/10 text-neutral-800 dark:text-neutral-200"
                >
                  {p}
                </span>
              ))
            ) : (
              <span className="text-xs italic text-neutral-400">
                No public repository or deployment URLs found. Including GitHub/live links significantly boosts recruiter confidence.
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

