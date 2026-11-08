import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Upload,
  FileText,
  ArrowRight,
  TrendingUp,
  Target,
  ShieldCheck,
  CheckCircle2,
  RefreshCw,
  AlertCircle,
  Award,
  Layers,
  Compass
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
  setLatestResult: React.Dispatch<React.SetStateAction<AnalysisResult | null>>;
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

  // Top-level service switcher: Target Discipline vs Target Job Posting
  const [activeServiceTab, setActiveServiceTab] = useState<'discipline' | 'jd'>('discipline');

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
    if (targetRole === r) {
      setTargetRole('');
    } else {
      setTargetRole(r);
    }
    setCustomRoleInput('');
    setErrorMessage(null);
  };

  const handleCustomRoleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (customRoleInput.trim()) {
      setTargetRole(customRoleInput.trim());
      setErrorMessage(null);
    }
  };

  const handleRunAssessment = async () => {
    if (!resumeFile && !latestResult) {
      setErrorMessage('Please upload a candidate resume PDF file.');
      return;
    }

    if (activeServiceTab === 'discipline' && !targetRole.trim()) {
      setErrorMessage('Please select or search a target discipline before running assessment.');
      return;
    }

    if (activeServiceTab === 'jd' && !jdFile && !jdText.trim()) {
      setErrorMessage('Please upload a Job Description file (PDF, DOCX, TXT) or paste job requirements.');
      return;
    }

    setErrorMessage(null);
    setIsAnalyzing(true);
    setAnalysisStep('Parsing candidate credentials and project evidence...');

    const timer1 = setTimeout(() => {
      setAnalysisStep(
        activeServiceTab === 'discipline'
          ? 'Querying live role intelligence and database taxonomies...'
          : 'Extracting structured technical requirements from target Job Description...'
      );
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
      formData.append('service_mode', activeServiceTab);

      if (activeServiceTab === 'discipline') {
        formData.append('target_role', targetRole.trim());
      } else {
        // activeServiceTab === 'jd': only append JD parameters
        if (jdFile) {
          formData.append('jd_file', jdFile);
        }
        if (jdText.trim()) {
          formData.append('target_jd_text', jdText.trim());
        }
        if (targetRole.trim()) {
          formData.append('target_role', targetRole.trim());
        }
      }

      formData.append('force_live_refresh', forceRefresh ? 'true' : 'false');
      if (user?.student_id) {
        formData.append('authenticated_student_id', String(user.student_id));
      }
      if (user?.email) {
        formData.append('authenticated_email', user.email);
      }

      const result = await assessmentService.processResume(formData);
      setLatestResult((prev) => {
        if (!prev) return result;
        // Seamlessly merge results so previous assessment on the sibling tab is preserved
        if (activeServiceTab === 'jd' && result.readiness_score === null && prev.readiness_score !== null) {
          return {
            ...result,
            readiness_score: prev.readiness_score,
            radar_dimensions: prev.radar_dimensions,
            missing_skills: prev.missing_skills,
            project_quality_score: prev.project_quality_score,
            resume_quality_breakdown: prev.resume_quality_breakdown,
            score_delta: prev.score_delta,
          };
        } else if (activeServiceTab === 'discipline' && result.jd_fit_score === null && prev.jd_fit_score !== null) {
          return {
            ...result,
            jd_fit_score: prev.jd_fit_score,
            jd_radar_dimensions: prev.jd_radar_dimensions,
            jd_benchmark_dimensions: prev.jd_benchmark_dimensions,
            jd_missing_skills: prev.jd_missing_skills,
            jd_project_quality_score: prev.jd_project_quality_score,
            jd_quality_breakdown: prev.jd_quality_breakdown,
          };
        }
        return result;
      });
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

  // Discipline Metrics
  const readiness = latestResult?.readiness_score || 0;
  const hasDisciplineResults = latestResult?.readiness_score !== null && latestResult?.readiness_score !== undefined;
  const projectQuality = latestResult?.project_quality_score || 0;
  const delta = latestResult?.score_delta;
  const marketGaps = latestResult?.missing_skills || [];
  const radarDims = latestResult?.radar_dimensions || {};
  const coreMatched = Object.values(radarDims).filter((v) => v >= 65).length;
  const totalCore = Math.max(Object.keys(radarDims).length, 1);

  // Job Description Metrics
  const jdFit = latestResult?.jd_fit_score;
  const hasJdResults = jdFit !== null && jdFit !== undefined;
  const jdGaps = latestResult?.jd_missing_skills || [];
  const jdRadarDims = latestResult?.jd_radar_dimensions || {};
  const jdBenchmarkDims = latestResult?.jd_benchmark_dimensions || null;
  const jdCoreMatched = Object.values(jdRadarDims).filter((v) => v >= 65).length;
  const totalJdCore = Math.max(Object.keys(jdRadarDims).length, 1);
  const jdProjectQuality = latestResult?.jd_project_quality_score ?? projectQuality;
  const jdQualityBreakdown = latestResult?.jd_quality_breakdown || latestResult?.resume_quality_breakdown;

  return (
    <div className="space-y-8">
      {/* ----------------------------------------------------------- */}
      {/* TOP-LEVEL SERVICE SWITCHER: TARGET DISCIPLINE | TARGET JD    */}
      {/* ----------------------------------------------------------- */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4 p-2 rounded-2xl bg-canvas-card dark:bg-black/40 border border-black/15 dark:border-white/15 shadow-crisp transition-colors duration-300 ease-in-out">
        <div className="flex items-center gap-2">
          {/* Tab 1: Target Discipline */}
          <button
            type="button"
            onClick={() => setActiveServiceTab('discipline')}
            className={`flex-1 sm:flex-initial flex items-center gap-2.5 px-5 py-3 rounded-xl font-display text-sm font-bold transition-all duration-200 ease-in-out ${
              activeServiceTab === 'discipline'
                ? 'bg-[#111111] text-[#F3EEE3] dark:bg-[#F3EEE3] dark:text-[#111111] shadow-elevated'
                : 'text-neutral-600 dark:text-neutral-400 hover:text-[#111111] dark:hover:text-[#F3EEE3] hover:bg-black/5 dark:hover:bg-white/5'
            }`}
          >
            <Target className="w-4 h-4 text-[#D9541E]" />
            <span>Target Discipline</span>
            {targetRole ? (
              <span className="text-[11px] font-mono px-2 py-0.5 rounded-md bg-black/10 dark:bg-black/20 text-[#D9541E] font-semibold border border-[#D9541E]/30">
                {targetRole}
              </span>
            ) : (
              <span className="text-[10px] uppercase font-mono font-bold px-2 py-0.5 rounded-md bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-700">
                Select Role
              </span>
            )}
          </button>

          {/* Tab 2: Target Job Posting */}
          <button
            type="button"
            onClick={() => setActiveServiceTab('jd')}
            className={`flex-1 sm:flex-initial flex items-center gap-2.5 px-5 py-3 rounded-xl font-display text-sm font-bold transition-all duration-200 ease-in-out ${
              activeServiceTab === 'jd'
                ? 'bg-[#111111] text-[#F3EEE3] dark:bg-[#F3EEE3] dark:text-[#111111] shadow-elevated'
                : 'text-neutral-600 dark:text-neutral-400 hover:text-[#111111] dark:hover:text-[#F3EEE3] hover:bg-black/5 dark:hover:bg-white/5'
            }`}
          >
            <FileText className="w-4 h-4 text-[#D9541E]" />
            <span>Target Job Posting</span>
            {hasJdResults ? (
              <span className="text-[10px] uppercase font-mono font-bold px-2 py-0.5 rounded-md bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-700">
                Active
              </span>
            ) : (
              <span className="text-[10px] uppercase font-mono font-bold px-2 py-0.5 rounded-md bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-700">
                {jdFile ? (jdFile.name.length > 15 ? jdFile.name.slice(0, 15) + '...' : jdFile.name) : 'Upload JD'}
              </span>
            )}
          </button>
        </div>

        <div className="hidden lg:flex items-center gap-2 px-4 text-xs font-mono text-neutral-500">
          <span>Active Service Mode:</span>
          <strong className="text-[#D9541E]">
            {activeServiceTab === 'discipline'
              ? targetRole
                ? `Standard Benchmark (${targetRole})`
                : 'Standard Benchmark (Select Discipline)'
              : 'Target Job Posting Alignment'}
          </strong>
        </div>
      </div>

      {/* ----------------------------------------------------------- */}
      {/* RECONFIGURABLE ASSESSMENT CONFIGURATION WORKSPACE           */}
      {/* ----------------------------------------------------------- */}
      <div className="rounded-xl border border-black/15 dark:border-white/15 bg-canvas-card dark:bg-black/30 p-6 shadow-crisp transition-colors duration-300 ease-in-out">
        {/* Card Header */}
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-6 border-b border-black/10 dark:border-white/10 transition-colors duration-300 ease-in-out">
          <div>
            <h2 className="font-display text-xl font-bold tracking-tight text-[#111111] dark:text-[#F3EEE3] transition-colors duration-300 ease-in-out">
              {activeServiceTab === 'discipline'
                ? 'Target Discipline Assessment Configuration'
                : 'Target Job Posting Assessment Configuration'}
            </h2>
            <p className="text-xs text-neutral-600 dark:text-neutral-400 mt-1 transition-colors duration-300 ease-in-out">
              {activeServiceTab === 'discipline'
                ? 'Select or search any target role across engineering, data, design, or finance disciplines and upload candidate resume.'
                : 'Upload candidate resume and target job posting (PDF, DOCX, TXT) to evaluate direct requirement alignment.'}
            </p>
          </div>

          <div className="flex items-center gap-3">
            <label className="flex items-center gap-2 cursor-pointer text-xs font-semibold text-neutral-700 dark:text-neutral-300 transition-colors duration-300 ease-in-out">
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

        {/* 2-Column Dynamic Workspace Layout with Framer Motion Animation */}
        <AnimatePresence mode="wait">
          {activeServiceTab === 'discipline' ? (
            /* 1. TARGET DISCIPLINE MODE: Left = Resume Upload, Right = Role Chips + Live Search */
            <motion.div
              key="discipline-config"
              layout
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.25, ease: 'easeInOut' }}
              className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-6 items-stretch"
            >
              {/* Left Column: Candidate Resume PDF Uploader */}
              <div className="flex flex-col h-full">
                <label className="text-xs font-semibold uppercase tracking-wider text-neutral-600 dark:text-neutral-400 mb-2 flex items-center justify-between transition-colors duration-300 ease-in-out">
                  <span>Candidate Resume (PDF)</span>
                  {resumeFile && (
                    <span className="font-mono text-[11px] text-emerald-600 font-bold">{resumeFile.name}</span>
                  )}
                </label>
                <label className="flex-1 flex flex-col items-center justify-center p-6 border-2 border-dashed border-black/15 dark:border-white/15 rounded-xl cursor-pointer hover:border-[#D9541E] dark:hover:border-[#D9541E] bg-white/50 dark:bg-black/20 transition-all duration-300 ease-in-out group min-h-[220px]">
                  <Upload className="w-8 h-8 text-[#D9541E] mb-2 group-hover:scale-110 transition-transform" />
                  <span className="text-sm font-semibold text-neutral-800 dark:text-neutral-200 text-center transition-colors duration-300 ease-in-out">
                    {resumeFile ? resumeFile.name : 'Click or drag PDF resume'}
                  </span>
                  <span className="text-xs text-neutral-500 mt-1 text-center">
                    Supports single and multi-page technical resumes
                  </span>
                  <input
                    type="file"
                    accept=".pdf"
                    className="hidden"
                    onChange={(e) => e.target.files && setResumeFile(e.target.files[0])}
                  />
                </label>
              </div>

              {/* Right Column: Role Configuration Block (Popular Roles + Live Search) */}
              <div className="flex flex-col justify-between space-y-4 h-full">
                {/* Popular Career Disciplines */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="block text-xs font-semibold uppercase tracking-wider text-neutral-600 dark:text-neutral-400 transition-colors duration-300 ease-in-out">
                      Popular Career Disciplines
                    </label>
                    {targetRole && (
                      <button
                        type="button"
                        onClick={() => setTargetRole('')}
                        className="text-[11px] text-neutral-400 hover:text-red-500 transition-colors"
                      >
                        Clear Selection
                      </button>
                    )}
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {POPULAR_ROLES.map((r) => (
                      <button
                        key={r}
                        type="button"
                        onClick={() => handleRoleSelect(r)}
                        className={`text-xs font-medium px-2.5 py-1.5 rounded-md border transition-all duration-200 ease-in-out ${
                          targetRole === r
                            ? 'bg-[#111111] text-[#F3EEE3] border-[#111111] font-bold dark:bg-[#F3EEE3] dark:text-[#111111] shadow-crisp'
                            : 'bg-white dark:bg-black/40 border-black/10 dark:border-white/10 text-neutral-700 dark:text-neutral-300 hover:border-black/30'
                        }`}
                      >
                        {r}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Live Search Any Target Discipline */}
                <div className="pt-2 border-t border-black/10 dark:border-white/10 transition-colors duration-300 ease-in-out">
                  <label className="block text-xs font-semibold uppercase tracking-wider text-neutral-600 dark:text-neutral-400 mb-2 transition-colors duration-300 ease-in-out">
                    Or Live Search Any Target Discipline
                  </label>
                  <form onSubmit={handleCustomRoleSubmit} className="flex gap-2">
                    <input
                      type="text"
                      placeholder="e.g. Agentic AI Engineer, Quantitative Researcher..."
                      value={customRoleInput}
                      onChange={(e) => setCustomRoleInput(e.target.value)}
                      className="flex-1 px-3.5 py-2 rounded-lg border border-black/15 bg-white dark:bg-black/40 text-xs focus:outline-none focus:ring-2 focus:ring-[#D9541E] transition-colors duration-200 ease-in-out"
                    />
                    <button
                      type="submit"
                      className="px-4 py-2 bg-[#111111] text-[#F3EEE3] dark:bg-[#F3EEE3] dark:text-[#111111] text-xs font-bold rounded-lg hover:opacity-90 transition-opacity duration-200 ease-in-out shrink-0 shadow-crisp"
                    >
                      Set Role
                    </button>
                  </form>
                  {targetRole ? (
                    <p className="text-[11px] font-mono text-neutral-500 mt-2">
                      Current Evaluation Target: <strong className="text-[#D9541E]">{targetRole}</strong>
                    </p>
                  ) : (
                    <div className="mt-2.5 p-2.5 rounded-lg border border-dashed border-[#D9541E]/30 bg-[#D9541E]/5 text-[11px] text-neutral-600 dark:text-neutral-400 flex items-center gap-2">
                      <Compass className="w-4 h-4 text-[#D9541E] shrink-0" />
                      <span>Select a popular career discipline above or live-search any target role to begin benchmarking...</span>
                    </div>
                  )}
                </div>
              </div>
            </motion.div>
          ) : (
            /* 2. TARGET JOB POSTING MODE: Left = Resume Upload, Right = JD File Upload + Paste Textarea */
            <motion.div
              key="jd-config"
              layout
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.25, ease: 'easeInOut' }}
              className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-6 items-stretch"
            >
              {/* Left Column: Candidate Resume PDF Uploader */}
              <div className="flex flex-col h-full">
                <label className="text-xs font-semibold uppercase tracking-wider text-neutral-600 dark:text-neutral-400 mb-2 flex items-center justify-between transition-colors duration-300 ease-in-out">
                  <span>Candidate Resume (PDF)</span>
                  {resumeFile && (
                    <span className="font-mono text-[11px] text-emerald-600 font-bold">{resumeFile.name}</span>
                  )}
                </label>
                <label className="flex-1 flex flex-col items-center justify-center p-6 border-2 border-dashed border-black/15 dark:border-white/15 rounded-xl cursor-pointer hover:border-[#D9541E] dark:hover:border-[#D9541E] bg-white/50 dark:bg-black/20 transition-all duration-300 ease-in-out group min-h-[220px]">
                  <Upload className="w-8 h-8 text-[#D9541E] mb-2 group-hover:scale-110 transition-transform" />
                  <span className="text-sm font-semibold text-neutral-800 dark:text-neutral-200 text-center transition-colors duration-300 ease-in-out">
                    {resumeFile ? resumeFile.name : 'Click or drag PDF resume'}
                  </span>
                  <span className="text-xs text-neutral-500 mt-1 text-center">
                    Supports single and multi-page technical resumes
                  </span>
                  <input
                    type="file"
                    accept=".pdf"
                    className="hidden"
                    onChange={(e) => e.target.files && setResumeFile(e.target.files[0])}
                  />
                </label>
              </div>

              {/* Right Column: Target Job Description File Upload + Pasting Textarea */}
              <div className="flex flex-col h-full">
                <label className="text-xs font-semibold uppercase tracking-wider text-neutral-600 dark:text-neutral-400 mb-2 flex items-center justify-between transition-colors duration-300 ease-in-out">
                  <span>Target Job Description</span>
                  {jdFile && (
                    <span className="font-mono text-[11px] text-emerald-600 font-bold">{jdFile.name}</span>
                  )}
                </label>
                <div className="flex-1 flex flex-col space-y-2.5">
                  <div className="flex items-center gap-2">
                    <label className="cursor-pointer text-xs font-semibold px-3 py-1.5 rounded-md border border-black/15 bg-white dark:bg-black/40 hover:border-black/30 flex items-center gap-1.5 transition-colors duration-200 ease-in-out shadow-crisp">
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
                        type="button"
                        onClick={() => setJdFile(null)}
                        className="text-xs text-neutral-400 hover:text-red-500 transition-colors duration-200 ease-in-out"
                      >
                        Clear
                      </button>
                    )}
                  </div>
                  <textarea
                    value={jdText}
                    onChange={(e) => setJdText(e.target.value)}
                    placeholder="Or paste target job description requirements here..."
                    rows={6}
                    className="w-full flex-1 px-3.5 py-2.5 rounded-lg border border-black/15 bg-white/50 dark:bg-black/20 text-xs focus:outline-none focus:ring-2 focus:ring-[#D9541E] resize-none transition-colors duration-200 ease-in-out"
                  />
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Action Button & Status Message */}
        <div className="pt-6 mt-6 border-t border-black/10 dark:border-white/10 flex flex-col sm:flex-row items-center justify-between gap-4 transition-colors duration-300 ease-in-out">
          <div className="text-xs text-neutral-500">
            {isAnalyzing ? (
              <span className="flex items-center gap-2 font-mono text-[#D9541E]">
                <RefreshCw className="w-4 h-4 animate-spin" />
                {analysisStep}
              </span>
            ) : !resumeFile ? (
              <span className="text-neutral-500 italic">
                Upload candidate resume (PDF) to begin assessment...
              </span>
            ) : activeServiceTab === 'discipline' && !targetRole.trim() ? (
              <span className="text-neutral-500 italic">
                Select a popular career discipline above or live-search any target role to begin benchmarking...
              </span>
            ) : activeServiceTab === 'jd' && !jdFile && !jdText.trim() ? (
              <span className="text-neutral-500 italic">
                Upload a job description file or paste requirements above to begin assessment...
              </span>
            ) : (
              <span className="text-emerald-600 dark:text-emerald-400 font-medium">
                Ready to analyze {activeServiceTab === 'discipline' ? `against ${targetRole}` : 'target job description'}
              </span>
            )}
            {errorMessage && (
              <div className="flex items-center gap-1.5 text-red-600 font-medium mt-1">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{errorMessage}</span>
              </div>
            )}
          </div>

          <button
            type="button"
            onClick={handleRunAssessment}
            disabled={
              isAnalyzing ||
              !resumeFile ||
              (activeServiceTab === 'discipline' && !targetRole.trim()) ||
              (activeServiceTab === 'jd' && !jdFile && !jdText.trim())
            }
            className="w-full sm:w-auto px-6 py-3 rounded-lg bg-[#D9541E] hover:bg-[#C24514] text-white font-display font-bold text-sm flex items-center justify-center gap-2 shadow-crisp transition-all duration-200 ease-in-out disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <span>
              {isAnalyzing
                ? 'Analyzing Alignment...'
                : activeServiceTab === 'discipline'
                ? 'Run Discipline Assessment'
                : 'Run Job Posting Assessment'}
            </span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* ----------------------------------------------------------- */}
      {/* SERVICE TAB 1: TARGET DISCIPLINE VIEW                       */}
      {/* ----------------------------------------------------------- */}
      {latestResult && activeServiceTab === 'discipline' && (
        <div className="space-y-8">
          {!hasDisciplineResults ? (
            /* Empty State when no Discipline assessment has been evaluated */
            <div className="rounded-xl border border-black/15 dark:border-white/15 bg-canvas-card dark:bg-black/30 p-12 text-center shadow-crisp transition-colors duration-300 ease-in-out">
              <div className="w-12 h-12 rounded-full bg-[#D9541E]/10 text-[#D9541E] flex items-center justify-center mx-auto mb-4">
                <Target className="w-6 h-6" />
              </div>
              <h3 className="font-display text-lg font-bold text-[#111111] dark:text-[#F3EEE3] transition-colors duration-300 ease-in-out">
                No Target Discipline Evaluated
              </h3>
              <p className="text-xs text-neutral-600 dark:text-neutral-400 max-w-md mx-auto mt-2 leading-relaxed transition-colors duration-300 ease-in-out">
                Select a career discipline or live-search any target role above and click <strong className="text-[#D9541E]">Run Discipline Assessment</strong> to evaluate your resume against broad industry market standards.
              </p>
            </div>
          ) : (
            <>
              {/* Row 1: 3 Hero KPI Cards */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Card 1: Role Readiness */}
            <div className="rounded-xl border border-[#111111] bg-[#111111] text-[#F3EEE3] p-6 shadow-elevated flex flex-col justify-between transition-colors duration-300 ease-in-out">
              <div className="flex items-start justify-between">
                <div>
                  <span className="text-[10px] font-mono uppercase tracking-wider text-neutral-400">
                    Role Readiness Score
                  </span>
                  <div className="font-display text-4xl font-bold mt-2 text-[#F3EEE3]">
                    {readiness.toFixed(1)}%
                  </div>
                </div>
                <ScoreGauge
                  score={readiness}
                  size={64}
                  strokeWidth={6}
                  color="#D9541E"
                  showScoreText={false}
                  icon={<Award className="w-7 h-7 text-[#D9541E]" />}
                />
              </div>
              <div className="pt-4 border-t border-white/10 text-xs text-neutral-400 leading-snug">
                <span className="font-semibold text-emerald-400">
                  {delta !== null && delta !== undefined ? `${delta >= 0 ? '+' : ''}${delta.toFixed(1)}% vs prior` : 'Initial Baseline'}
                </span>
                . Measures verified candidate skills against {targetRole} industry standards.
              </div>
            </div>

            {/* Card 2: Project Rigor & Evidence Progress Bars */}
            <div className="rounded-xl border border-black/15 dark:border-white/15 bg-canvas-card dark:bg-black/30 p-6 shadow-crisp flex flex-col justify-between transition-colors duration-300 ease-in-out">
              <div>
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-mono uppercase tracking-wider text-neutral-500">
                    Project & Evidence Rigor
                  </span>
                  <span className="font-mono text-sm font-bold text-[#D9541E]">
                    {projectQuality.toFixed(1)}%
                  </span>
                </div>
                <div className="mt-4 space-y-2.5">
                  <div>
                    <div className="flex justify-between text-[11px] font-medium text-neutral-600 dark:text-neutral-400 mb-1">
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
                    <div className="flex justify-between text-[11px] font-medium text-neutral-600 dark:text-neutral-400 mb-1">
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
              <div className="pt-3 text-[11px] text-neutral-500">
                Evaluates verifiable architecture and impact metrics.
              </div>
            </div>

            {/* Card 3: Core Disciplines Matched */}
            <div className="rounded-xl border border-black/15 dark:border-white/15 bg-canvas-card dark:bg-black/30 p-6 shadow-crisp flex flex-col justify-between transition-colors duration-300 ease-in-out">
              <div>
                <span className="text-[10px] font-mono uppercase tracking-wider text-neutral-500">
                  Core Disciplines Matched
                </span>
                <div className="font-display text-4xl font-bold mt-2 text-[#111111] dark:text-[#F3EEE3]">
                  {coreMatched} / {totalCore}
                </div>
                <div className="flex gap-1.5 mt-4">
                  {Array.from({ length: totalCore }).map((_, i) => (
                    <div
                      key={i}
                      className={`h-2.5 flex-1 rounded-sm ${
                        i < coreMatched ? 'bg-[#D9541E]' : 'bg-black/10 dark:bg-white/10'
                      }`}
                    />
                  ))}
                </div>
              </div>
              <div className="pt-4 border-t border-black/10 dark:border-white/10 text-xs text-neutral-500">
                Satisfied standard threshold requirements (≥ 65%).
              </div>
            </div>
          </div>

          {/* Row 2: 12-Column Split (Radar Chart 7 cols + Discipline Gaps 5 cols) */}
          <div className="grid grid-cols-12 gap-6">
            {/* Left: Competency Radar Chart */}
            <div className="col-span-12 lg:col-span-7 rounded-xl border border-black/15 dark:border-white/15 bg-canvas-card dark:bg-black/30 p-6 shadow-crisp transition-colors duration-300 ease-in-out">
              <div className="flex items-center justify-between pb-4 border-b border-black/10 dark:border-white/10">
                <div>
                  <h3 className="font-display text-base font-bold text-[#111111] dark:text-[#F3EEE3]">
                    Competency Footprint Radar — {targetRole}
                  </h3>
                  <p className="text-xs text-neutral-600 dark:text-neutral-400">
                    5-axis radar benchmarking candidate proficiency against broader market standards.
                  </p>
                </div>
              </div>
              <div className="pt-4">
                <CompetencyRadar
                  radarDimensions={latestResult.radar_dimensions}
                  targetRole={targetRole}
                  benchmarkName={`Market Standard (${targetRole})`}
                />
              </div>
            </div>

            {/* Right: Priority Discipline Gaps Panel */}
            <div className="col-span-12 lg:col-span-5 rounded-xl border border-black/15 dark:border-white/15 bg-canvas-card dark:bg-black/30 p-6 shadow-crisp flex flex-col justify-between transition-colors duration-300 ease-in-out">
              <div>
                <div className="flex items-center justify-between pb-4 border-b border-black/10 dark:border-white/10">
                  <div>
                    <h3 className="font-display text-base font-bold text-[#111111] dark:text-[#F3EEE3]">
                      Priority Discipline Gaps
                    </h3>
                    <p className="text-xs text-neutral-600 dark:text-neutral-400">
                      Core industry requirements identified for {targetRole}.
                    </p>
                  </div>
                </div>

                {/* Gaps List */}
                <div className="pt-4 space-y-3">
                  {marketGaps.length > 0 ? (
                    marketGaps.slice(0, 5).map((gap) => (
                      <div
                        key={gap}
                        className="p-3.5 rounded-lg border border-red-200 dark:border-red-950/60 bg-red-50/60 dark:bg-red-950/20 flex items-center justify-between"
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
                          type="button"
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
                </div>
              </div>

              <button
                type="button"
                onClick={() => onNavigateTab('roadmap')}
                className="mt-6 w-full py-2.5 px-4 rounded-lg border border-[#D9541E] text-[#D9541E] hover:bg-[#D9541E] hover:text-white font-display text-xs font-bold flex items-center justify-center gap-2 transition-colors duration-200 ease-in-out"
              >
                <span>Explore Multi-Platform Learning Roadmap</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Row 3: Full-Width Resume Evidence & Impact Breakdown */}
          <EvidenceBreakdown
            breakdown={latestResult.resume_quality_breakdown}
            projectQualityScore={latestResult.project_quality_score}
            title="Resume Evidence & Impact Audit"
            subtitle="Human-grade evaluation separating verifiable engineering outcomes from superficial keyword listings."
            stackLabel="Discipline-Verified Stack"
          />
        </>
      )}
    </div>
  )}

      {/* ----------------------------------------------------------- */}
      {/* SERVICE TAB 2: TARGET JOB POSTING VIEW                      */}
      {/* ----------------------------------------------------------- */}
      {latestResult && activeServiceTab === 'jd' && (
        <div className="space-y-8">
          {!hasJdResults ? (
            /* Empty State when no JD has been uploaded/evaluated */
            <div className="rounded-xl border border-black/15 dark:border-white/15 bg-canvas-card dark:bg-black/30 p-12 text-center shadow-crisp transition-colors duration-300 ease-in-out">
              <div className="w-12 h-12 rounded-full bg-[#D9541E]/10 text-[#D9541E] flex items-center justify-center mx-auto mb-4">
                <FileText className="w-6 h-6" />
              </div>
              <h3 className="font-display text-lg font-bold text-[#111111] dark:text-[#F3EEE3] transition-colors duration-300 ease-in-out">
                No Target Job Description Uploaded
              </h3>
              <p className="text-xs text-neutral-600 dark:text-neutral-400 max-w-md mx-auto mt-2 leading-relaxed transition-colors duration-300 ease-in-out">
                Upload a Job Description (PDF, DOCX, or TXT) or paste job requirements above and click <strong className="text-[#D9541E]">Run Job Posting Assessment</strong> to benchmark your resume directly against a specific job posting.
              </p>
            </div>
          ) : (
            /* Complete Identical 3-Row Architecture for Target Job Posting */
            <>
              {/* Row 1: 3 Hero KPI Cards */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* Card 1: Target JD Fit Score */}
                <div className="rounded-xl border border-[#111111] bg-[#111111] text-[#F3EEE3] p-6 shadow-elevated flex flex-col justify-between transition-colors duration-300 ease-in-out">
                  <div className="flex items-start justify-between">
                    <div>
                      <span className="text-[10px] font-mono uppercase tracking-wider text-neutral-400">
                        Target Job Posting Fit
                      </span>
                      <div className="font-display text-4xl font-bold mt-2 text-[#F3EEE3]">
                        {jdFit.toFixed(1)}%
                      </div>
                    </div>
                    <ScoreGauge
                      score={jdFit}
                      size={64}
                      strokeWidth={6}
                      color="#D9541E"
                      showScoreText={false}
                      icon={<Target className="w-7 h-7 text-[#D9541E]" />}
                    />
                  </div>
                  <div className="pt-4 border-t border-white/10 text-xs text-neutral-400 leading-snug">
                    <span className="font-semibold text-emerald-400">Direct Dual-Scoring</span>
                    . Direct competency & evidence alignment against the uploaded job description.
                  </div>
                </div>

                {/* Card 2: JD Project & Evidence Rigor */}
                <div className="rounded-xl border border-black/15 dark:border-white/15 bg-canvas-card dark:bg-black/30 p-6 shadow-crisp flex flex-col justify-between transition-colors duration-300 ease-in-out">
                  <div>
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] font-mono uppercase tracking-wider text-neutral-500">
                        JD Project & Evidence Rigor
                      </span>
                      <span className="font-mono text-sm font-bold text-[#D9541E]">
                        {jdProjectQuality.toFixed(1)}%
                      </span>
                    </div>
                    <div className="mt-4 space-y-2.5">
                      <div>
                        <div className="flex justify-between text-[11px] font-medium text-neutral-600 dark:text-neutral-400 mb-1">
                          <span>Quantitative Metrics</span>
                          <span className="font-mono font-semibold">
                            {(jdQualityBreakdown?.quantitative_metrics_score || 0).toFixed(0)}%
                          </span>
                        </div>
                        <div className="w-full h-1.5 rounded-full bg-black/10 dark:bg-white/10 overflow-hidden">
                          <div
                            className="h-full bg-[#D9541E] rounded-full"
                            style={{
                              width: `${Math.min(
                                jdQualityBreakdown?.quantitative_metrics_score || 0,
                                100
                              )}%`,
                            }}
                          />
                        </div>
                      </div>

                      <div>
                        <div className="flex justify-between text-[11px] font-medium text-neutral-600 dark:text-neutral-400 mb-1">
                          <span>JD Role Alignment</span>
                          <span className="font-mono font-semibold">
                            {(jdQualityBreakdown?.role_alignment_score || 0).toFixed(0)}%
                          </span>
                        </div>
                        <div className="w-full h-1.5 rounded-full bg-black/10 dark:bg-white/10 overflow-hidden">
                          <div
                            className="h-full bg-[#111111] dark:bg-neutral-300 rounded-full"
                            style={{
                              width: `${Math.min(
                                jdQualityBreakdown?.role_alignment_score || 0,
                                100
                              )}%`,
                            }}
                          />
                        </div>
                      </div>
                    </div>
                  </div>
                  <div className="pt-3 text-[11px] text-neutral-500">
                    Evaluates verified evidence alignment against posting requirements.
                  </div>
                </div>

                {/* Card 3: JD Core Pillars Matched */}
                <div className="rounded-xl border border-black/15 dark:border-white/15 bg-canvas-card dark:bg-black/30 p-6 shadow-crisp flex flex-col justify-between transition-colors duration-300 ease-in-out">
                  <div>
                    <span className="text-[10px] font-mono uppercase tracking-wider text-neutral-500">
                      JD Core Pillars Matched
                    </span>
                    <div className="font-display text-4xl font-bold mt-2 text-[#111111] dark:text-[#F3EEE3]">
                      {jdCoreMatched} / {totalJdCore}
                    </div>
                    <div className="flex gap-1.5 mt-4">
                      {Array.from({ length: totalJdCore }).map((_, i) => (
                        <div
                          key={i}
                          className={`h-2.5 flex-1 rounded-sm ${
                            i < jdCoreMatched ? 'bg-[#D9541E]' : 'bg-black/10 dark:bg-white/10'
                          }`}
                        />
                      ))}
                    </div>
                  </div>
                  <div className="pt-4 border-t border-black/10 dark:border-white/10 text-xs text-neutral-500">
                    Satisfied target job posting pillar thresholds (≥ 65%).
                  </div>
                </div>
              </div>

              {/* Row 2: 12-Column Split (Dedicated JD Radar 7 cols + JD Gaps 5 cols) */}
              <div className="grid grid-cols-12 gap-6">
                {/* Left: Dedicated Target Job Posting Radar Chart */}
                <div className="col-span-12 lg:col-span-7 rounded-xl border border-black/15 dark:border-white/15 bg-canvas-card dark:bg-black/30 p-6 shadow-crisp transition-colors duration-300 ease-in-out">
                  <div className="flex items-center justify-between pb-4 border-b border-black/10 dark:border-white/10">
                    <div>
                      <h3 className="font-display text-base font-bold text-[#111111] dark:text-[#F3EEE3]">
                        Target Job Posting Footprint Radar
                      </h3>
                      <p className="text-xs text-neutral-600 dark:text-neutral-400">
                        Dedicated 5-axis radar benchmarking candidate proficiency against the uploaded job description.
                      </p>
                    </div>
                  </div>
                  <div className="pt-4">
                    <CompetencyRadar
                      radarDimensions={latestResult.jd_radar_dimensions}
                      benchmarkDimensions={jdBenchmarkDims}
                      benchmarkName="Job Posting Requirement Benchmark"
                      candidateName="Candidate JD Competency"
                      targetRole="Job Posting Requirements"
                    />
                  </div>
                </div>

                {/* Right: Target Job Posting Gaps Panel */}
                <div className="col-span-12 lg:col-span-5 rounded-xl border border-black/15 dark:border-white/15 bg-canvas-card dark:bg-black/30 p-6 shadow-crisp flex flex-col justify-between transition-colors duration-300 ease-in-out">
                  <div>
                    <div className="flex items-center justify-between pb-4 border-b border-black/10 dark:border-white/10">
                      <div>
                        <h3 className="font-display text-base font-bold text-[#111111] dark:text-[#F3EEE3]">
                          Target Job Posting Gaps
                        </h3>
                        <p className="text-xs text-neutral-600 dark:text-neutral-400">
                          Specific requirements identified from the uploaded job posting.
                        </p>
                      </div>
                    </div>

                    {/* Gaps List */}
                    <div className="pt-4 space-y-3">
                      {jdGaps.length > 0 ? (
                        jdGaps.slice(0, 5).map((gap) => (
                          <div
                            key={gap}
                            className="p-3.5 rounded-lg border border-amber-200 dark:border-amber-950/60 bg-amber-50/60 dark:bg-amber-950/20 flex items-center justify-between"
                          >
                            <div>
                              <div className="text-xs font-bold text-amber-900 dark:text-amber-300">
                                {gap}
                              </div>
                              <span className="text-[10px] uppercase font-mono tracking-wider text-amber-700/80 dark:text-amber-400">
                                Target Job Posting Requirement
                              </span>
                            </div>
                            <button
                              type="button"
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
                          <span>No critical gaps detected for this job description! 100% posting alignment.</span>
                        </div>
                      )}
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={() => onNavigateTab('roadmap')}
                    className="mt-6 w-full py-2.5 px-4 rounded-lg border border-[#D9541E] text-[#D9541E] hover:bg-[#D9541E] hover:text-white font-display text-xs font-bold flex items-center justify-center gap-2 transition-colors duration-200 ease-in-out"
                  >
                    <span>Explore Multi-Platform Learning Roadmap</span>
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Row 3: Full-Width Job Posting Evidence & Impact Breakdown */}
              <EvidenceBreakdown
                breakdown={jdQualityBreakdown}
                projectQualityScore={jdProjectQuality}
                title="Job Posting Evidence & Impact Audit"
                subtitle="Human-grade evaluation separating verifiable engineering outcomes from superficial keyword listings for the uploaded job posting."
                stackLabel="JD-Verified Stack"
                stackDescription="Candidate tools and frameworks actively verified in projects that directly satisfy job posting requirements."
              />
            </>
          )}
        </div>
      )}
    </div>
  );
};
