import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Cpu, ShieldCheck, Layers, ArrowRight } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { authService } from '../services/api';

export const AuthPortal: React.FC = () => {
  const { login, signup, googleAuth, isLoading } = useAuth();
  const [tab, setTab] = useState<'login' | 'signup'>('login');
  const [error, setError] = useState<string | null>(null);

  // Form states
  const [loginIdentifier, setLoginIdentifier] = useState('');
  const [loginPassword, setLoginPassword] = useState('');

  const [signupName, setSignupName] = useState('');
  const [signupUsername, setSignupUsername] = useState('');
  const [signupEmail, setSignupEmail] = useState('');
  const [signupPassword, setSignupPassword] = useState('');

  // Handle Google OAuth 2.0 redirect callback (?code=... or ?error=...)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get('code');
    const oauthError = params.get('error');

    if (oauthError) {
      setError(`Google authorization returned: ${oauthError}. Authorized Redirect URI in Google Cloud Console must match: ${window.location.origin}`);
      window.history.replaceState({}, document.title, window.location.pathname);
      return;
    }

    if (code) {
      const exchangeCode = async () => {
        try {
          await googleAuth({
            code,
            redirect_uri: window.location.origin,
          });
          window.history.replaceState({}, document.title, window.location.pathname);
        } catch (err: any) {
          setError(
            err?.response?.data?.detail ||
            `Google OAuth verification failed. Please verify that ${window.location.origin} is added to Authorized redirect URIs in Google Cloud Console.`
          );
          window.history.replaceState({}, document.title, window.location.pathname);
        }
      };
      exchangeCode();
    }
  }, []);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!loginIdentifier || !loginPassword) {
      setError('Please provide your username/email and password.');
      return;
    }
    try {
      await login(loginIdentifier, loginPassword);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Invalid credentials.');
    }
  };

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!signupUsername || !signupEmail || !signupPassword) {
      setError('Please complete all required fields.');
      return;
    }
    try {
      await signup(signupName, signupUsername, signupEmail, signupPassword);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Registration failed.');
    }
  };

  const handleGoogleClick = async () => {
    setError(null);
    try {
      const redirectUri = window.location.origin;
      const cfg = await authService.getGoogleUrl(redirectUri);
      if (cfg.configured && cfg.auth_url) {
        window.location.href = cfg.auth_url;
      } else {
        setError(
          `Google OAuth is not configured on the server. Please add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to your .env file with authorized redirect URI: ${redirectUri}`
        );
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to initiate Google OAuth login.');
    }
  };

  return (
    <div className="min-h-screen w-full flex flex-col lg:flex-row bg-[#F3EEE3] text-[#111111]">
      {/* Left Panel: Architectural Identity & System Status */}
      <div className="w-full lg:w-1/2 bg-[#111111] text-[#F3EEE3] p-6 sm:p-10 lg:p-16 flex flex-col justify-between border-b lg:border-b-0 lg:border-r border-[#111111] relative overflow-hidden">
        {/* Subtle geometric background line */}
        <div className="absolute top-0 right-0 w-96 h-96 bg-[#D9541E]/10 rounded-full blur-3xl pointer-events-none" />

        <div>
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-lg bg-[#D9541E] flex items-center justify-center font-display font-bold text-xl text-white shadow-crisp">
              CT
            </div>
            <div>
              <span className="font-display font-bold text-lg tracking-tight text-[#F3EEE3]">
                CAREER TWIN
              </span>
              <p className="text-[10px] font-mono uppercase tracking-widest text-[#D9541E]">
                Autonomous Role Intelligence
              </p>
            </div>
          </div>

          <div className="mt-8 sm:mt-12 lg:mt-20 max-w-md">
            <h2 className="font-display text-2xl sm:text-3xl lg:text-4xl font-bold tracking-tight text-[#F3EEE3] leading-tight">
              Evidence-Grounded Competency & Role Readiness
            </h2>
            <p className="mt-3 sm:mt-4 text-xs sm:text-sm text-neutral-400 leading-relaxed font-sans">
              Replaces keyword-matching ATS with dense semantic vector alignment, 3-pillar project proof evaluation, and dynamic multi-platform study roadmaps.
            </p>
          </div>

          {/* Architectural Feature Highlights */}
          <div className="mt-6 sm:mt-10 space-y-3 sm:space-y-4 max-w-md">
            <div className="flex items-start gap-3.5 p-3 rounded-lg bg-white/5 border border-white/10">
              <Cpu className="w-5 h-5 text-[#D9541E] shrink-0 mt-0.5" />
              <div>
                <h4 className="text-xs font-semibold uppercase tracking-wider text-[#F3EEE3]">
                  Zero Keyword Cheats
                </h4>
                <p className="text-xs text-neutral-400 mt-0.5">
                  100% database-driven taxonomies and MiniLM vector similarity guarantee unbiased human evaluation.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3.5 p-3 rounded-lg bg-white/5 border border-white/10">
              <ShieldCheck className="w-5 h-5 text-[#D9541E] shrink-0 mt-0.5" />
              <div>
                <h4 className="text-xs font-semibold uppercase tracking-wider text-[#F3EEE3]">
                  Project Proof Verification
                </h4>
                <p className="text-xs text-neutral-400 mt-0.5">
                  Quantifies measurable metrics, architecture depth, and verifiable repository proof links.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3.5 p-3 rounded-lg bg-white/5 border border-white/10">
              <Layers className="w-5 h-5 text-[#D9541E] shrink-0 mt-0.5" />
              <div>
                <h4 className="text-xs font-semibold uppercase tracking-wider text-[#F3EEE3]">
                  Dynamic Dual-Radar Scaling
                </h4>
                <p className="text-xs text-neutral-400 mt-0.5">
                  Plots authentic 5-axis polygon comparisons between industry benchmarks and custom job descriptions.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* System Status Pill */}
        <div className="mt-8 sm:mt-12 flex items-center gap-2 text-xs font-mono text-neutral-400">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span>PostgreSQL & Vector Engine Online</span>
        </div>
      </div>

      {/* Right Panel: Clean Editorial Authentication Form */}
      <div className="w-full lg:w-1/2 p-5 sm:p-10 lg:p-16 flex items-center justify-center bg-[#F3EEE3]">
        <div className="w-full max-w-md">
          {/* Tab Switcher */}
          <div className="flex items-center border-b border-black/15 mb-8">
            <button
              onClick={() => { setTab('login'); setError(null); }}
              className={`pb-3 px-4 font-display text-sm font-bold transition-all relative ${
                tab === 'login' ? 'text-[#111111]' : 'text-neutral-500 hover:text-black'
              }`}
            >
              Sign In
              {tab === 'login' && (
                <motion.div
                  layoutId="authTabUnderline"
                  className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#D9541E]"
                />
              )}
            </button>
            <button
              onClick={() => { setTab('signup'); setError(null); }}
              className={`pb-3 px-4 font-display text-sm font-bold transition-all relative ${
                tab === 'signup' ? 'text-[#111111]' : 'text-neutral-500 hover:text-black'
              }`}
            >
              Create Account
              {tab === 'signup' && (
                <motion.div
                  layoutId="authTabUnderline"
                  className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#D9541E]"
                />
              )}
            </button>
          </div>

          {error && (
            <div className="mb-6 p-3 rounded-md bg-red-100 border border-red-300 text-xs font-medium text-red-900">
              {error}
            </div>
          )}

          {tab === 'login' ? (
            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-neutral-700 mb-1.5">
                  Username or Email
                </label>
                <input
                  type="text"
                  value={loginIdentifier}
                  onChange={(e) => setLoginIdentifier(e.target.value)}
                  placeholder="e.g. aditya or aditya@example.com"
                  className="w-full px-3.5 py-2.5 rounded-lg border border-black/15 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-[#D9541E]"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-neutral-700 mb-1.5">
                  Password
                </label>
                <input
                  type="password"
                  value={loginPassword}
                  onChange={(e) => setLoginPassword(e.target.value)}
                  placeholder="Enter your password"
                  className="w-full px-3.5 py-2.5 rounded-lg border border-black/15 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-[#D9541E]"
                  required
                />
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full mt-2 py-3 px-4 rounded-lg bg-[#D9541E] hover:bg-[#C24514] text-white font-display font-bold text-sm flex items-center justify-center gap-2 transition-all shadow-crisp"
              >
                <span>{isLoading ? 'Verifying...' : 'Sign In to Workspace'}</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </form>
          ) : (
            <form onSubmit={handleSignup} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-neutral-700 mb-1.5">
                  Full Name
                </label>
                <input
                  type="text"
                  value={signupName}
                  onChange={(e) => setSignupName(e.target.value)}
                  placeholder="e.g. Aditya Ranganekar"
                  className="w-full px-3.5 py-2.5 rounded-lg border border-black/15 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-[#D9541E]"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-neutral-700 mb-1.5">
                  Username
                </label>
                <input
                  type="text"
                  value={signupUsername}
                  onChange={(e) => setSignupUsername(e.target.value)}
                  placeholder="e.g. aditya"
                  className="w-full px-3.5 py-2.5 rounded-lg border border-black/15 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-[#D9541E]"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-neutral-700 mb-1.5">
                  Email Address
                </label>
                <input
                  type="email"
                  value={signupEmail}
                  onChange={(e) => setSignupEmail(e.target.value)}
                  placeholder="e.g. aditya@example.com"
                  className="w-full px-3.5 py-2.5 rounded-lg border border-black/15 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-[#D9541E]"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-neutral-700 mb-1.5">
                  Password
                </label>
                <input
                  type="password"
                  value={signupPassword}
                  onChange={(e) => setSignupPassword(e.target.value)}
                  placeholder="Minimum 6 characters"
                  className="w-full px-3.5 py-2.5 rounded-lg border border-black/15 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-[#D9541E]"
                  required
                />
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full mt-2 py-3 px-4 rounded-lg bg-[#D9541E] hover:bg-[#C24514] text-white font-display font-bold text-sm flex items-center justify-center gap-2 transition-all shadow-crisp"
              >
                <span>{isLoading ? 'Creating Profile...' : 'Create Account'}</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </form>
          )}

          {/* Divider */}
          <div className="relative my-6 text-center">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-black/15" />
            </div>
            <span className="relative px-3 bg-[#F3EEE3] text-xs font-semibold uppercase tracking-wider text-neutral-500">
              Or
            </span>
          </div>

          {/* Continue with Google */}
          <button
            type="button"
            onClick={handleGoogleClick}
            className="w-full py-2.5 px-4 rounded-lg bg-white border border-black/15 hover:border-black/30 font-medium text-xs text-[#111111] flex items-center justify-center gap-2.5 transition-all shadow-crisp"
          >
            <svg className="w-4 h-4" viewBox="0 0 24 24">
              <path
                fill="#4285F4"
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
              />
              <path
                fill="#34A853"
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              />
              <path
                fill="#FBBC05"
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
              />
              <path
                fill="#EA4335"
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
              />
            </svg>
            <span>Continue with Google</span>
          </button>
        </div>
      </div>
    </div>
  );
};

