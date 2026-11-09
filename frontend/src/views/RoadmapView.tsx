import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { ExternalLink, BookOpen, CheckCircle, GraduationCap, Filter } from 'lucide-react';
import { Recommendation } from '../types';

interface RoadmapViewProps {
  recommendations: Recommendation[];
  targetRole: string;
}

export const RoadmapView: React.FC<RoadmapViewProps> = ({
  recommendations,
  targetRole,
}) => {
  const [filter, setFilter] = useState<'all' | 'role' | 'jd'>('all');

  if (!recommendations || recommendations.length === 0) {
    return (
      <div className="rounded-xl border border-black/15 dark:border-white/15 bg-canvas-card dark:bg-black/30 p-12 text-center shadow-crisp">
        <div className="w-12 h-12 rounded-full bg-emerald-100 dark:bg-emerald-950 text-emerald-600 flex items-center justify-center mx-auto mb-4">
          <CheckCircle className="w-6 h-6" />
        </div>
        <h3 className="font-display text-lg font-bold text-[#111111] dark:text-[#F3EEE3]">
          No Critical Skill Gaps Identified
        </h3>
        <p className="text-xs text-neutral-600 dark:text-neutral-400 max-w-md mx-auto mt-2 leading-relaxed">
          The candidate profile satisfies all verified industry benchmarks for <strong className="text-[#D9541E]">{targetRole}</strong>. Run a diagnostic assessment to analyze another role target or custom job description.
        </p>
      </div>
    );
  }

  const roleCount = recommendations.filter(
    (r) => r.gap_type === 'Role Gap' || r.gap_type === 'Role & JD Gap' || !r.gap_type
  ).length;
  const jdCount = recommendations.filter(
    (r) => r.gap_type === 'Target JD Gap' || r.gap_type === 'Role & JD Gap'
  ).length;
  const total = recommendations.length;

  const filteredRecommendations = recommendations.filter((r) => {
    if (filter === 'role') return r.gap_type === 'Role Gap' || r.gap_type === 'Role & JD Gap' || !r.gap_type;
    if (filter === 'jd') return r.gap_type === 'Target JD Gap' || r.gap_type === 'Role & JD Gap';
    return true;
  });

  const getPlatformClass = (platform: string) => {
    const p = platform.toLowerCase();
    if (p.includes('udemy')) return 'bg-[#6D28D9] text-white hover:bg-[#5B21B6]';
    if (p.includes('coursera')) return 'bg-[#0056D2] text-white hover:bg-[#0046AB]';
    if (p.includes('edx')) return 'bg-[#02262B] text-white hover:bg-[#04383F]';
    if (p.includes('youtube')) return 'bg-[#DC2626] text-white hover:bg-[#B91C1C]';
    return 'bg-[#334155] text-white hover:bg-[#1E293B]';
  };

  const renderGapBadge = (gapType?: string) => {
    const type = gapType || 'Role Gap';
    if (type === 'Target JD Gap') {
      return (
        <span className="font-mono text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-amber-100 dark:bg-amber-950/80 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-800">
          Target JD Gap
        </span>
      );
    }
    if (type === 'Role & JD Gap') {
      return (
        <span className="font-mono text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-purple-100 dark:bg-purple-950/80 text-purple-800 dark:text-purple-300 border border-purple-300 dark:border-purple-800">
          Role & JD Gap
        </span>
      );
    }
    return (
      <span className="font-mono text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-[#D9541E]/15 text-[#D9541E] border border-[#D9541E]/30">
        Role Gap
      </span>
    );
  };

  return (
    <div className="space-y-6">
      {/* Roadmap Header & Category Filters */}
      <div className="rounded-xl border border-black/15 dark:border-white/15 bg-canvas-card dark:bg-black/30 p-6 shadow-crisp space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-[#D9541E]/10 text-[#D9541E]">
              <GraduationCap className="w-5 h-5" />
            </div>
            <div>
              <h2 className="font-display text-xl font-bold tracking-tight text-[#111111] dark:text-[#F3EEE3]">
                Multi-Platform Learning Roadmap
              </h2>
              <p className="text-xs text-neutral-600 dark:text-neutral-400 mt-0.5">
                Targeted study paths and direct search links dynamically constructed for <strong className="text-[#D9541E]">{targetRole}</strong>.
              </p>
            </div>
          </div>

          {jdCount > 0 && (
            <div className="flex flex-wrap items-center gap-1.5 p-1 bg-black/5 dark:bg-white/5 rounded-lg border border-black/10 dark:border-white/10 self-start sm:self-auto">
              <button
                onClick={() => setFilter('all')}
                className={`px-3 py-1.5 rounded-md text-xs font-bold transition-all ${
                  filter === 'all'
                    ? 'bg-canvas-card dark:bg-black/60 text-[#111111] dark:text-[#F3EEE3] shadow-crisp border border-black/10 dark:border-white/10'
                    : 'text-neutral-600 dark:text-neutral-400 hover:text-[#111111] dark:hover:text-[#F3EEE3]'
                }`}
              >
                All ({total})
              </button>
              <button
                onClick={() => setFilter('role')}
                className={`px-3 py-1.5 rounded-md text-xs font-bold transition-all ${
                  filter === 'role'
                    ? 'bg-canvas-card dark:bg-black/60 text-[#111111] dark:text-[#F3EEE3] shadow-crisp border border-black/10 dark:border-white/10'
                    : 'text-neutral-600 dark:text-neutral-400 hover:text-[#111111] dark:hover:text-[#F3EEE3]'
                }`}
              >
                Role ({roleCount})
              </button>
              <button
                onClick={() => setFilter('jd')}
                className={`px-3 py-1.5 rounded-md text-xs font-bold transition-all ${
                  filter === 'jd'
                    ? 'bg-canvas-card dark:bg-black/60 text-[#111111] dark:text-[#F3EEE3] shadow-crisp border border-black/10 dark:border-white/10'
                    : 'text-neutral-600 dark:text-neutral-400 hover:text-[#111111] dark:hover:text-[#F3EEE3]'
                }`}
              >
                Target JD ({jdCount})
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Cards List */}
      <div className="space-y-4">
        {filteredRecommendations.map((rec, index) => (
          <motion.div
            key={rec.skill}
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, delay: index * 0.05 }}
            className="rounded-xl border border-black/15 dark:border-white/15 bg-canvas-card dark:bg-black/30 p-6 shadow-crisp hover:shadow-elevated transition-shadow"
          >
            {/* Header: Skill Name & Priority */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-black/10 dark:border-white/10 gap-2">
              <div className="flex items-center gap-2.5">
                <span className="font-display text-lg font-bold text-[#111111] dark:text-[#F3EEE3]">
                  {rec.skill}
                </span>
                {renderGapBadge(rec.gap_type)}
              </div>
              <span className="text-xs font-mono text-neutral-500">
                Roadmap Item #{index + 1}
              </span>
            </div>

            {/* Why This Matters */}
            <div className="py-4 border-b border-black/10 dark:border-white/10">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-neutral-500 mb-1.5">
                Why This Competency Matters:
              </h4>
              <p className="text-xs text-neutral-700 dark:text-neutral-300 leading-relaxed">
                {rec.justification}
              </p>
            </div>

            {/* Key Concepts to Master */}
            <div className="py-4 border-b border-black/10 dark:border-white/10">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-neutral-500 mb-2">
                Core Sub-Topics to Master:
              </h4>
              <div className="flex flex-wrap gap-2">
                {rec.key_topics && rec.key_topics.length > 0 ? (
                  rec.key_topics.map((topic, tIdx) => (
                    <div
                      key={tIdx}
                      className="text-xs font-mono px-3 py-1.5 rounded-md bg-black/5 dark:bg-white/5 border border-black/10 dark:border-white/10 text-neutral-800 dark:text-neutral-200"
                    >
                      {topic}
                    </div>
                  ))
                ) : (
                  <span className="text-xs text-neutral-500">Architecture fundamentals and production integration.</span>
                )}
              </div>
            </div>

            {/* Direct Multi-Platform Launchers */}
            <div className="pt-4">
              <h4 className="text-[11px] font-semibold uppercase tracking-wider text-neutral-500 mb-2.5">
                Direct Multi-Platform Study Launchers:
              </h4>
              <div className="grid grid-cols-2 sm:flex sm:flex-wrap gap-2.5">
                {rec.platform_links && rec.platform_links.length > 0 ? (
                  rec.platform_links.map((link) => (
                    <a
                      key={link.platform}
                      href={link.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className={`inline-flex items-center justify-center sm:justify-start gap-1.5 px-3.5 py-2.5 rounded-lg text-xs font-bold transition-transform hover:-translate-y-0.5 shadow-crisp min-h-[42px] ${getPlatformClass(
                        link.platform
                      )}`}
                    >
                      <span>{link.platform}</span>
                      <ExternalLink className="w-3.5 h-3.5 shrink-0" />
                    </a>
                  ))
                ) : (
                  <a
                    href={rec.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center justify-center sm:justify-start gap-1.5 px-3.5 py-2.5 rounded-lg text-xs font-bold bg-[#D9541E] text-white min-h-[42px]"
                  >
                    <span>Primary Course Search</span>
                    <ExternalLink className="w-3.5 h-3.5 shrink-0" />
                  </a>
                )}
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
};

