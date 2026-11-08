import React from 'react';
import { motion } from 'framer-motion';
import { ExternalLink, BookOpen, CheckCircle, GraduationCap } from 'lucide-react';
import { Recommendation } from '../types';

interface RoadmapViewProps {
  recommendations: Recommendation[];
  targetRole: string;
}

export const RoadmapView: React.FC<RoadmapViewProps> = ({
  recommendations,
  targetRole,
}) => {
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

  const getPlatformClass = (platform: string) => {
    const p = platform.toLowerCase();
    if (p.includes('udemy')) return 'bg-[#6D28D9] text-white hover:bg-[#5B21B6]';
    if (p.includes('coursera')) return 'bg-[#0056D2] text-white hover:bg-[#0046AB]';
    if (p.includes('edx')) return 'bg-[#02262B] text-white hover:bg-[#04383F]';
    if (p.includes('youtube')) return 'bg-[#DC2626] text-white hover:bg-[#B91C1C]';
    return 'bg-[#334155] text-white hover:bg-[#1E293B]';
  };

  return (
    <div className="space-y-6">
      {/* Roadmap Header */}
      <div className="rounded-xl border border-black/15 dark:border-white/15 bg-canvas-card dark:bg-black/30 p-6 shadow-crisp">
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
      </div>

      {/* Cards List */}
      <div className="space-y-4">
        {recommendations.map((rec, index) => (
          <motion.div
            key={rec.skill}
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, delay: index * 0.08 }}
            className="rounded-xl border border-black/15 dark:border-white/15 bg-canvas-card dark:bg-black/30 p-6 shadow-crisp hover:shadow-elevated transition-shadow"
          >
            {/* Header: Skill Name & Priority */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-black/10 dark:border-white/10 gap-2">
              <div className="flex items-center gap-2.5">
                <span className="font-display text-lg font-bold text-[#111111] dark:text-[#F3EEE3]">
                  {rec.skill}
                </span>
                <span className="font-mono text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-red-100 dark:bg-red-950/80 text-red-800 dark:text-red-300 border border-red-200 dark:border-red-800">
                  Core Gap
                </span>
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
              <div className="flex flex-wrap gap-2.5">
                {rec.platform_links && rec.platform_links.length > 0 ? (
                  rec.platform_links.map((link) => (
                    <a
                      key={link.platform}
                      href={link.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className={`inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-bold transition-transform hover:-translate-y-0.5 shadow-crisp ${getPlatformClass(
                        link.platform
                      )}`}
                    >
                      <span>{link.platform}</span>
                      <ExternalLink className="w-3.5 h-3.5" />
                    </a>
                  ))
                ) : (
                  <a
                    href={rec.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-bold bg-[#D9541E] text-white"
                  >
                    <span>Primary Course Search</span>
                    <ExternalLink className="w-3.5 h-3.5" />
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

