import React, { useState } from 'react';
import { motion } from 'framer-motion';
import {
  Upload,
  FileText,
  ArrowRight,
  TrendingUp,
  Target,
  ShieldCheck,
  CheckCircle2,
  RefreshCw,
  AlertCircle
} from 'lucide-react';
import { AnalysisResult, ActiveTab } from '../types';
import { assessmentService } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { ScoreGauge } from '../components/ScoreGauge';
import { CompetencyRadar } from '../components/CompetencyRadar';
import { EvidenceBreakdown } from '../components/EvidenceBreakdown';

interface DashboardViewProps {
  onNavigateTab: (tab: ActiveTab) => void;
  targetRole: string;
  setTargetRole: (role: string) => void;
  latestResult: AnalysisResult | null;
  setLatestResult: (result: AnalysisResult | null) => void;
}

const POPULAR_ROLES = [
  'Data Scientist',
  'Machine Learning Engineer',
  'AI / LLM Engineer',
  'Agentic AI Engineer',
  'Data Engineer',
  'Data Analyst',
  'MLOps Engineer',
  'Backend Software Engineer',
  'Full-Stack Developer',
  'Cloud / DevOps Engineer',
  'Site Reliability Engineer',
  'Quantitative Researcher',
];

export const DashboardView: React.FC<DashboardViewProps> = ({
  onNavigateTab,
  targetRole,
  setTargetRole,
  latestResult,
  setLatestResult,
}) => {
  const { user } = useAuth();

  // Assessment inputs
  const [customRoleInput, setCustomRoleInput] = useState('');
  const [forceRefresh, setForceRefresh] = useState(false);
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [jdFile, setJdFile] = useState<File | null>(null);
  const [jdText, setJdText] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisStep, setAnalysisStep] = useState<string>('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleRoleSelect = (r: string) => {
    setTargetRole(r);
    setCustomRoleInput('');
  };

  const handleCustomRoleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (customRoleInput.trim()) {
      setTargetRole(customRoleInput.trim());
    }
  };

  const handleRunAssessment = async () => {
    if (!resumeFile && !latestResult) {
      setErrorMessage('Please upload a candidate resume PDF file.');
      return;
    }

    setErrorMessage(null);
    setIsAnalyzing(true);
    setAnalysisStep('Parsing candidate credentials and project evidence...');

    const timer1 = setTimeout(() => {
      setAnalysisStep('Querying live role intelligence and database taxonomies...');
    }, 1800);

    const timer2 = setTimeout(() => {
      setAnalysisStep('Computing dense MiniLM semantic similarity matrix...');
    }, 3800);

    const timer3 = setTimeout(() => {
      setAnalysisStep('Synthesizing dynamic multi-platform study roadmap...');
    }, 5800);

    try {
      const formData = new FormData();
      if (resumeFile) {
        formData.append('file', resumeFile);
      }
      if (jdFile) {
        formData.append('jd_file', jdFile);
      }
      if (jdText.trim()) {
        formData.append('target_jd_text', jdText.trim());
      }
      formData.append('target_role', targetRole);
      formData.append('force_live_refresh', forceRefresh ? 'true' : 'false');
      if (user?.student_id) {
        formData.append('authenticated_student_id', String(user.student_id));
      }
      if (user?.email) {
        formData.append('authenticated_email', user.email);
      }

      const result = await assessmentService.processResume(formData);
      setLatestResult(result);
    } catch (err: any) {
      setErrorMessage(
        err?.response?.data?.detail || 'Assessment failed. Ensure FastAPI is running on port 8000.'
      );
    } finally {
      clearTimeout(timer1);
      clearTimeout(timer2);
      clearTimeout(timer3);
      setIsAnalyzing(false);
      setAnalysisStep('');
    }
  };

  const readiness = latestResult?.readiness_score || 0;
  const jdFit = latestResult?.jd_fit_score;
  const projectQuality = latestResult?.project_quality_score || 0;
  const delta = latestResult?.score_delta;
  const marketGaps = latestResult?.missing_skills || [];
  const jdGaps = latestResult?.jd_missing_skills || [];
  const radarDims = latestResult?.radar_dimensions || {};
  const coreMatched = Object.values(radarDims).filter((v) => v >= 70).length;
  const totalCore = Math.max(Object.keys(radarDims).length, 1);

  return (
    <div className="space-y-8">
      {/* ----------------------------------------------------------- */}
      {/* Control Bar: Target Role & File Uploads                     */}
      {/* ----------------------------------------------------------- */}
      <div className="rounded-xl border border-black/15 dark:border-white/15 bg-canvas-card dark:bg-black/30 p-6 shadow-crisp">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-6 border-b border-black/10 dark:border-white/10">
          <div>
            <h2 className="font-display text-xl font-bold tracking-tight text-[#111111] dark:text-[#F3EEE3]">
              Diagnostic Assessment Configuration
            </h2>
            <p className="text-xs text-neutral-600 dark:text-neutral-400 mt-1">
              Select or search any target role across engineering, data, design, or finance disciplines.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <label className="flex items-center gap-2 cursor-pointer text-xs font-semibold text-neutral-700 dark:text-neutral-300">
              <input
                type="checkbox"
                checked={forceRefresh}
                onChange={(e) => setForceRefresh(e.target.checked)}
                className="rounded border-neutral-300 text-[#D9541E] focus:ring-[#D9541E]"
              />
              <RefreshCw className="w-3.5 h-3.5 text-neutral-500" />
              <span>Force Live Internet Refresh</span>
            </label>
          </div>
        </div>

        {/* Role Selection & Custom Input */}
        <div className="grid grid-cols-1 md:grid-cols-12 gap-4 pt-6">
          <div className="md:col-span-6">
            <label className="block text-xs font-semibold uppercase tracking-wider text-neutral-600 dark:text-neutral-400 mb-2">
              Popular Career Disciplines
            </label>
            <div className="flex flex-wrap gap-1.5">
              {POPULAR_ROLES.map((r) => (
                <button
                  key={r}
                  onClick={() => handleRoleSelect(r)}
                  className={`text-xs font-medium px-2.5 py-1.5 rounded-md border transition-all ${
                    targetRole === r
                      ? 'bg-[#111111] text-[#F3EEE3] border-[#111111] font-bold dark:bg-[#F3EEE3] dark:text-[#111111]'
                      : 'bg-white dark:bg-black/40 border-black/10 dark:border-white/10 text-neutral-700 dark:text-neutral-300 hover:border-black/30'
                  }`}
                >
                  {r}
                </button>
              ))}
            </div>
          </div>

          <div className="md:col-span-6">
            <label className="block text-xs font-semibold uppercase tracking-wider text-neutral-600 dark:text-neutral-400 mb-2">
              Or Live Search Any Target Discipline
            </label>
            <form onSubmit={handleCustomRoleSubmit} className="flex gap-2">
              <input
                type="text"
                placeholder="e.g. Agentic AI Engineer, Quantitative Researcher..."
                value={customRoleInput}
                onChange={(e) => setCustomRoleInput(e.target.value)}
                className="flex-1 px-3.5 py-2 rounded-lg border border-black/15 bg-white dark:bg-black/40 text-sm focus:outline-none focus:ring-2 focus:ring-[#D9541E]"
              />
              <button
                type="submit"
                className="px-4 py-2 bg-[#111111] text-[#F3EEE3] dark:bg-[#F3EEE3] dark:text-[#111111] text-xs font-bold rounded-lg hover:opacity-90 transition-opacity"
              >
                Set Role
              </button>
            </form>
            <p className="text-[11px] font-mono text-neutral-500 mt-1.5">
              Current Evaluation Target: <strong className="text-[#D9541E]">{targetRole}</strong>
            </p>
          </div>
        </div>

        {/* Upload Panels: Resume & Target JD */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-6 mt-6 border-t border-black/10 dark:border-white/10">
          {/* Resume Upload */}
          <div className="flex flex-col">
            <label className="text-xs font-semibold uppercase tracking-wider text-neutral-600 dark:text-neutral-400 mb-2 flex items-center justify-between">
              <span>Candidate Resume (PDF)</span>
              {resumeFile && <span className="font-mono text-[11px] text-emerald-600">{resumeFile.name}</span>}
            </label>
            <label className="flex-1 flex flex-col items-center justify-center p-6 border-2 border-dashed border-black/15 dark:border-white/15 rounded-xl cursor-pointer hover:border-[#D9541E] bg-white/50 dark:bg-black/20 transition-colors">
              <Upload className="w-8 h-8 text-[#D9541E] mb-2" />
              <span className="text-sm font-semibold text-neutral-800 dark:text-neutral-200">
                {resumeFile ? resumeFile.name : 'Click or drag PDF resume'}
              </span>
              <span className="text-xs text-neutral-500 mt-1">
                Supports standard and LaTeX single/multi-page resumes
              </span>
              <input
                type="file"
                accept=".pdf"
                className="hidden"
                onChange={(e) => e.target.files && setResumeFile(e.target.files[0])}
              />
            </label>
          </div>

          {/* Job Description Upload / Paste */}
          <div className="flex flex-col">
            <label className="text-xs font-semibold uppercase tracking-wider text-neutral-600 dark:text-neutral-400 mb-2 flex items-center justify-between">
              <span>Target Job Posting (Optional Dual-Scoring)</span>
              {jdFile && <span className="font-mono text-[11px] text-emerald-600">{jdFile.name}</span>}
            </label>
            <div className="flex-1 flex flex-col space-y-2">
              <div className="flex items-center gap-2">
                <label className="cursor-pointer text-xs font-semibold px-3 py-1.5 rounded border border-black/15 bg-white dark:bg-black/40 hover:border-black/30 flex items-center gap-1.5">
                  <FileText className="w-3.5 h-3.5 text-[#D9541E]" />
                  <span>Upload JD (PDF, DOCX, TXT)</span>
                  <input
                    type="file"
                    accept=".pdf,.docx,.txt"
                    className="hidden"
                    onChange={(e) => e.target.files && setJdFile(e.target.files[0])}
                  />
                </label>
                {jdFile && (
                  <button
                    onClick={() => setJdFile(null)}
                    className="text-xs text-neutral-400 hover:text-red-500"
                  >
                    Clear
                  </button>
                )}
              </div>
              <textarea
                value={jdText}
                onChange={(e) => setJdText(e.target.value)}
                placeholder="Or paste target job description requirements here..."
                rows={3}
                className="w-full flex-1 px-3 py-2 rounded-lg border border-black/15 bg-white/50 dark:bg-black/20 text-xs focus:outline-none focus:ring-2 focus:ring-[#D9541E]"
              />
            </div>
          </div>
        </div>

        {/* Action Button & Status Message */}
        <div className="pt-6 mt-6 border-t border-black/10 dark:border-white/10 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="text-xs text-neutral-500">
            {isAnalyzing && (
              <span className="flex items-center gap-2 font-mono text-[#D9541E]">
                <RefreshCw className="w-4 h-4 animate-spin" />
                {analysisStep}
              </span>
            )}
            {errorMessage && (
              <span className="flex items-center gap-1.5 text-red-600 font-medium">
                <AlertCircle className="w-4 h-4" />
                {errorMessage}
              </span>
            )}
          </div>

          <button
            onClick={handleRunAssessment}
            disabled={isAnalyzing}
            className="w-full sm:w-auto px-6 py-3 rounded-lg bg-[#D9541E] hover:bg-[#C24514] text-white font-display font-bold text-sm flex items-center justify-center gap-2 shadow-crisp transition-all disabled:opacity-50"
          >
            <span>{isAnalyzing ? 'Analyzing Alignment...' : 'Run Career Assessment'}</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* ----------------------------------------------------------- */}
      {/* Row 1: 4 Hero KPI Bento-Grid Cards                          */}
      {/* ----------------------------------------------------------- */}
      {latestResult && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Card 1: Role Readiness */}
          <div className="rounded-xl border border-[#111111] bg-[#111111] text-[#F3EEE3] p-5 shadow-elevated flex flex-col justify-between">
            <div className="flex items-start justify-between">
              <div>
                <span className="text-[10px] font-mono uppercase tracking-wider text-neutral-400">
                  Role Readiness Score
                </span>
                <div className="font-display text-3xl font-bold mt-1 text-[#F3EEE3]">
                  {readiness.toFixed(1)}%
                </div>
              </div>
              <ScoreGauge score={readiness} size={58} strokeWidth={5} color="#D9541E" />
            </div>
            <div className="pt-4 border-t border-white/10 text-xs text-neutral-400 leading-snug">
              <span className="font-semibold text-emerald-400">
                {delta !== null && delta !== undefined ? `${delta >= 0 ? '+' : ''}${delta.toFixed(1)}% vs prior` : 'Initial Baseline'}
              </span>
              . Measures verified candidate skills against industry standards.
            </div>
          </div>

          {/* Card 2: Target JD Fit */}
          <div className="rounded-xl border border-black/15 dark:border-white/15 bg-canvas-card dark:bg-black/30 p-5 shadow-crisp flex flex-col justify-between">
            <div>
              <span className="text-[10px] font-mono uppercase tracking-wider text-neutral-500">
                Target Job Posting Fit
              </span>
              <div className="font-display text-3xl font-bold mt-1 text-[#111111] dark:text-[#F3EEE3]">
                {jdFit !== null && jdFit !== undefined ? `${jdFit.toFixed(1)}%` : 'N/A'}
              </div>
            </div>
            <div className="pt-4 border-t border-black/10 dark:border-white/10 text-xs text-neutral-500 leading-snug">
              {jdFit !== null && jdFit !== undefined ? (
                <span className="text-emerald-600 font-semibold">Active Dual-Scoring</span>
              ) : (
                'Upload a target JD document to evaluate custom posting alignment.'
              )}
            </div>
          </div>

          {/* Card 3: Project Rigor & Evidence Progress Bars */}
          <div className="rounded-xl border border-black/15 dark:border-white/15 bg-canvas-card dark:bg-black/30 p-5 shadow-crisp flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-mono uppercase tracking-wider text-neutral-500">
                  Project & Evidence Rigor
                </span>
                <span className="font-mono text-sm font-bold text-[#D9541E]">
                  {projectQuality.toFixed(1)}%
                </span>
              </div>
              {/* Unclipped horizontal progress bars */}
              <div className="mt-3 space-y-2">
                <div>
                  <div className="flex justify-between text-[11px] font-medium text-neutral-600 dark:text-neutral-400 mb-0.5">
                    <span>Quantitative Metrics</span>
                    <span className="font-mono font-semibold">
                      {latestResult.resume_quality_breakdown?.quantitative_metrics_score.toFixed(0)}%
                    </span>
                  </div>
                  <div className="w-full h-1.5 rounded-full bg-black/10 dark:bg-white/10 overflow-hidden">
                    <div
                      className="h-full bg-[#D9541E] rounded-full"
                      style={{
                        width: `${Math.min(
                          latestResult.resume_quality_breakdown?.quantitative_metrics_score || 0,
                          100
                        )}%`,
                      }}
                    />
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-[11px] font-medium text-neutral-600 dark:text-neutral-400 mb-0.5">
                    <span>Production Architecture</span>
                    <span className="font-mono font-semibold">
                      {latestResult.resume_quality_breakdown?.production_proof_score.toFixed(0)}%
                    </span>
                  </div>
                  <div className="w-full h-1.5 rounded-full bg-black/10 dark:bg-white/10 overflow-hidden">
                    <div
                      className="h-full bg-[#111111] dark:bg-neutral-300 rounded-full"
                      style={{
                        width: `${Math.min(
                          latestResult.resume_quality_breakdown?.production_proof_score || 0,
                          100
                        )}%`,
                      }}
                    />
                  </div>
                </div>
              </div>
            </div>
            <div className="pt-2 text-[11px] text-neutral-500">
              Evaluates verifiable architecture and impact metrics.
            </div>
          </div>

          {/* Card 4: Core Competencies Verified */}
          <div className="rounded-xl border border-black/15 dark:border-white/15 bg-canvas-card dark:bg-black/30 p-5 shadow-crisp flex flex-col justify-between">
            <div>
              <span className="text-[10px] font-mono uppercase tracking-wider text-neutral-500">
                Core Disciplines Matched
              </span>
              <div className="font-display text-3xl font-bold mt-1 text-[#111111] dark:text-[#F3EEE3]">
                {coreMatched} / {totalCore}
              </div>
              {/* Segmented bar */}
              <div className="flex gap-1 mt-3">
                {Array.from({ length: totalCore }).map((_, i) => (
                  <div
                    key={i}
                    className={`h-2 flex-1 rounded-sm ${
                      i < coreMatched ? 'bg-[#D9541E]' : 'bg-black/10 dark:bg-white/10'
                    }`}
                  />
                ))}
              </div>
            </div>
            <div className="pt-4 border-t border-black/10 dark:border-white/10 text-xs text-neutral-500">
              Satisfied standard threshold requirements.
            </div>
          </div>
        </div>
      )}

      {/* ----------------------------------------------------------- */}
      {/* Row 2: 12-Column Split (Radar Chart 7 cols + Gaps 5 cols)   */}
      {/* ----------------------------------------------------------- */}
      {latestResult && (
        <div className="grid grid-cols-12 gap-6">
          {/* Left: Competency Radar Chart */}
          <div className="col-span-12 lg:col-span-7 rounded-xl border border-black/15 dark:border-white/15 bg-canvas-card dark:bg-black/30 p-6 shadow-crisp">
            <div className="flex items-center justify-between pb-4 border-b border-black/10 dark:border-white/10">
              <div>
                <h3 className="font-display text-base font-bold text-[#111111] dark:text-[#F3EEE3]">
                  Competency Footprint Radar
                </h3>
                <p className="text-xs text-neutral-600 dark:text-neutral-400">
                  Unclipped 5-axis visualization benchmarking candidate proficiency against role demand.
                </p>
              </div>
            </div>
            <div className="pt-4">
              <CompetencyRadar
                radarDimensions={latestResult.radar_dimensions}
                jdRadarDimensions={latestResult.jd_radar_dimensions}
                targetRole={targetRole}
              />
            </div>
          </div>

          {/* Right: Priority Competency Gaps Panel */}
          <div className="col-span-12 lg:col-span-5 rounded-xl border border-black/15 dark:border-white/15 bg-canvas-card dark:bg-black/30 p-6 shadow-crisp flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between pb-4 border-b border-black/10 dark:border-white/10">
                <div>
                  <h3 className="font-display text-base font-bold text-[#111111] dark:text-[#F3EEE3]">
                    Priority Competency Gaps
                  </h3>
                  <p className="text-xs text-neutral-600 dark:text-neutral-400">
                    High-impact requirements identified for this candidate profile.
                  </p>
                </div>
              </div>

              {/* Gaps List */}
              <div className="pt-4 space-y-3">
                {marketGaps.length > 0 ? (
                  marketGaps.slice(0, 5).map((gap) => (
                    <div
                      key={gap}
                      className="p-3 rounded-lg border border-red-200 dark:border-red-950/60 bg-red-50/60 dark:bg-red-950/20 flex items-center justify-between"
                    >
                      <div>
                        <div className="text-xs font-bold text-red-900 dark:text-red-300">
                          {gap}
                        </div>
                        <span className="text-[10px] uppercase font-mono tracking-wider text-red-700/80 dark:text-red-400">
                          Industry Role Requirement
                        </span>
                      </div>
                      <button
                        onClick={() => onNavigateTab('roadmap')}
                        className="text-xs font-semibold text-[#D9541E] hover:underline flex items-center gap-1 shrink-0"
                      >
                        <span>Study Path</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ))
                ) : (
                  <div className="p-4 rounded-lg bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800 text-xs text-emerald-800 dark:text-emerald-300 flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                    <span>No critical industry benchmark gaps detected. Strong role alignment!</span>
                  </div>
                )}

                {/* Job Description Gaps */}
                {jdGaps && jdGaps.length > 0 && (
                  <div className="pt-2">
                    <div className="text-xs font-semibold uppercase tracking-wider text-amber-700 dark:text-amber-400 mb-2">
                      Target Job Posting Gaps:
                    </div>
                    {jdGaps.slice(0, 3).map((jGap) => (
                      <div
                        key={jGap}
                        className="p-2.5 rounded-lg border border-amber-200 dark:border-amber-950/60 bg-amber-50/60 dark:bg-amber-950/20 text-xs font-bold text-amber-900 dark:text-amber-300 flex items-center justify-between mb-2"
                      >
                        <span>{jGap}</span>
                        <span className="text-[10px] font-mono text-amber-700">Posting Gap</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <button
              onClick={() => onNavigateTab('roadmap')}
              className="mt-6 w-full py-2.5 px-4 rounded-lg border border-[#D9541E] text-[#D9541E] hover:bg-[#D9541E] hover:text-white font-display text-xs font-bold flex items-center justify-center gap-2 transition-colors"
            >
              <span>Explore Multi-Platform Learning Roadmap</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* ----------------------------------------------------------- */}
      {/* Row 3: Full-Width Resume Evidence & Impact Breakdown        */}
      {/* ----------------------------------------------------------- */}
      {latestResult && (
        <EvidenceBreakdown
          breakdown={latestResult.resume_quality_breakdown}
          projectQualityScore={latestResult.project_quality_score}
        />
      )}
    </div>
  );
};
