import React, { useEffect, useState } from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import {
  Calendar,
  FileText,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  TrendingUp,
} from 'lucide-react';
import { HistoricalRun } from '../types';
import { historyService } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';

export const HistoryView: React.FC = () => {
  const { user } = useAuth();
  const { theme } = useTheme();
  const [runs, setRuns] = useState<HistoricalRun[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [expandedRunId, setExpandedRunId] = useState<number | null>(null);

  const fetchHistory = async () => {
    if (!user?.student_id && !user?.email) return;
    setIsLoading(true);
    try {
      const ident = user.student_id || user.email;
      const data = await historyService.getHistory(ident);
      setRuns(data);
      if (data.length > 0 && expandedRunId === null) {
        setExpandedRunId(data[0].id);
      }
    } catch (e) {
      console.error('Failed fetching history:', e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, [user]);

  const toggleExpand = (id: number) => {
    setExpandedRunId(expandedRunId === id ? null : id);
  };

  const isDark = theme === 'dark';
  const gridColor = isDark ? 'rgba(243, 238, 227, 0.12)' : 'rgba(17, 17, 17, 0.1)';
  const tickColor = isDark ? '#F3EEE3' : '#111111';

  // Format chart data (chronological left-to-right)
  const chartData = [...runs].reverse().map((r) => {
    const d = new Date(r.timestamp);
    const dateLabel = isNaN(d.getTime()) ? r.timestamp.slice(0, 10) : `${d.getMonth() + 1}/${d.getDate()}`;
    return {
      date: dateLabel,
      readiness: Math.round(r.readiness_score),
      jdFit: r.jd_fit_score ? Math.round(r.jd_fit_score) : null,
      role: r.target_role,
    };
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="rounded-xl border border-black/15 dark:border-white/15 bg-canvas-card dark:bg-black/30 p-6 shadow-crisp flex items-center justify-between">
        <div>
          <h2 className="font-display text-xl font-bold tracking-tight text-[#111111] dark:text-[#F3EEE3]">
            Historical Assessment Archive
          </h2>
          <p className="text-xs text-neutral-600 dark:text-neutral-400 mt-0.5">
            Track competency score trajectory and resume studying from past assessment recommendations.
          </p>
        </div>
        <button
          onClick={fetchHistory}
          className="p-2 rounded-lg border border-black/15 dark:border-white/15 hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
          title="Refresh History"
        >
          <RefreshCw className={`w-4 h-4 text-neutral-600 dark:text-neutral-300 ${isLoading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Top Panel: Recharts Readiness Score Trajectory Area Chart */}
      {runs.length > 0 && (
        <div className="rounded-xl border border-black/15 dark:border-white/15 bg-canvas-card dark:bg-black/30 p-6 shadow-crisp">
          <div className="flex items-center justify-between pb-4 border-b border-black/10 dark:border-white/10">
            <div className="flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-[#D9541E]" />
              <h3 className="font-display text-sm font-bold text-[#111111] dark:text-[#F3EEE3]">
                Role Readiness Score Trajectory
              </h3>
            </div>
            <span className="font-mono text-xs text-neutral-500">
              Total Evaluations: {runs.length}
            </span>
          </div>

          <div className="w-full h-64 pt-4">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="readinessGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#D9541E" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#D9541E" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
                <XAxis dataKey="date" tick={{ fill: tickColor, fontSize: 11 }} />
                <YAxis domain={[0, 100]} tick={{ fill: tickColor, fontSize: 11 }} tickFormatter={(v) => `${v}%`} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: isDark ? '#181818' : '#FAF7F2',
                    borderColor: isDark ? 'rgba(243,238,227,0.2)' : 'rgba(17,17,17,0.2)',
                    borderRadius: '8px',
                    fontSize: '12px',
                    fontFamily: 'Inter, sans-serif',
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="readiness"
                  name="Role Readiness"
                  stroke="#D9541E"
                  strokeWidth={2.5}
                  fillOpacity={1}
                  fill="url(#readinessGrad)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Bottom Panel: Expandable Historical Run Cards */}
      <div className="space-y-3">
        {runs.length === 0 && !isLoading ? (
          <div className="p-8 text-center rounded-xl border border-black/15 bg-canvas-card">
            <p className="text-sm text-neutral-500 font-sans">
              No historical runs found for this user account. Run your first assessment in the Overview tab!
            </p>
          </div>
        ) : (
          runs.map((run) => {
            const isExpanded = expandedRunId === run.id;
            const dateStr = new Date(run.timestamp).toLocaleString();

            return (
              <div
                key={run.id}
                className="rounded-xl border border-black/15 dark:border-white/15 bg-canvas-card dark:bg-black/30 overflow-hidden shadow-crisp transition-all"
              >
                {/* Collapsible Bar */}
                <button
                  onClick={() => toggleExpand(run.id)}
                  className="w-full p-4 flex items-center justify-between text-left hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4">
                    <div className="font-display font-bold text-sm text-[#111111] dark:text-[#F3EEE3]">
                      {run.target_role}
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs px-2 py-0.5 rounded bg-[#D9541E] text-white font-bold">
                        Readiness: {run.readiness_score.toFixed(1)}%
                      </span>
                      {run.jd_fit_score !== null && run.jd_fit_score !== undefined && (
                        <span className="font-mono text-xs px-2 py-0.5 rounded bg-emerald-700 text-white font-bold">
                          JD Fit: {run.jd_fit_score.toFixed(1)}%
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <span className="text-[11px] font-mono text-neutral-500 hidden md:inline">
                      {dateStr}
                    </span>
                    {isExpanded ? (
                      <ChevronUp className="w-4 h-4 text-neutral-500" />
                    ) : (
                      <ChevronDown className="w-4 h-4 text-neutral-500" />
                    )}
                  </div>
                </button>

                {/* Expanded Details */}
                {isExpanded && (
                  <div className="p-5 border-t border-black/10 dark:border-white/10 bg-white/40 dark:bg-black/20 space-y-4">
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
                      <div>
                        <span className="text-neutral-500 block">Evaluated Resume File:</span>
                        <span className="font-mono font-semibold text-neutral-800 dark:text-neutral-200">
                          {run.resume_filename || 'Direct Upload'}
                        </span>
                      </div>
                      <div>
                        <span className="text-neutral-500 block">Project & Proof Rigor:</span>
                        <span className="font-mono font-semibold text-[#D9541E]">
                          {run.project_quality_score ? `${run.project_quality_score.toFixed(1)}%` : 'N/A'}
                        </span>
                      </div>
                      <div>
                        <span className="text-neutral-500 block">Evaluation Timestamp:</span>
                        <span className="font-mono text-neutral-700 dark:text-neutral-300">
                          {dateStr}
                        </span>
                      </div>
                    </div>

                    {/* Missing Skills from that run */}
                    {run.missing_skills && run.missing_skills.length > 0 && (
                      <div>
                        <div className="text-[11px] font-semibold uppercase tracking-wider text-neutral-500 mb-1.5">
                          Identified Skill Gaps:
                        </div>
                        <div className="flex flex-wrap gap-1.5">
                          {run.missing_skills.map((s, idx) => (
                            <span
                              key={idx}
                              className="font-mono text-xs px-2 py-0.5 rounded bg-red-100 dark:bg-red-950/60 border border-red-200 dark:border-red-900 text-red-900 dark:text-red-300"
                            >
                              {s}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Archived Multi-Platform Study Links */}
                    {run.recommended_resources && run.recommended_resources.length > 0 && (
                      <div className="pt-2 border-t border-black/10 dark:border-white/10">
                        <div className="text-[11px] font-semibold uppercase tracking-wider text-neutral-500 mb-2">
                          Archived Multi-Platform Study Launchers:
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                          {run.recommended_resources.slice(0, 4).map((rec, rIdx) => (
                            <div
                              key={rIdx}
                              className="p-3 rounded-lg border border-black/10 dark:border-white/10 bg-white/60 dark:bg-black/30"
                            >
                              <div className="font-display font-bold text-xs text-[#111111] dark:text-[#F3EEE3] mb-1.5">
                                {rec.skill}
                              </div>
                              <div className="flex flex-wrap gap-1.5">
                                {rec.platform_links?.map((link) => (
                                  <a
                                    key={link.platform}
                                    href={link.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="inline-flex items-center gap-1 px-2 py-1 rounded bg-[#111111] text-[#F3EEE3] dark:bg-white/10 text-[10px] font-mono hover:bg-[#D9541E] hover:text-white transition-colors"
                                  >
                                    <span>{link.platform}</span>
                                    <ExternalLink className="w-2.5 h-2.5" />
                                  </a>
                                ))}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

