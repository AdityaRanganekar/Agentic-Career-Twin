import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Compass, BookOpen, History, LogOut, ShieldCheck, X } from 'lucide-react';
import { ActiveTab } from '../types';
import { useAuth } from '../context/AuthContext';

interface SidebarProps {
  activeTab: ActiveTab;
  onTabChange: (tab: ActiveTab) => void;
  targetRole: string;
  isOpen?: boolean;
  onClose?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  onTabChange,
  targetRole,
  isOpen = false,
  onClose,
}) => {
  const { user, logout } = useAuth();

  const navItems = [
    { id: 'overview' as ActiveTab, label: 'Assessment Overview', icon: Compass },
    { id: 'roadmap' as ActiveTab, label: 'Learning Roadmap', icon: BookOpen },
    { id: 'history' as ActiveTab, label: 'Run History & Progress', icon: History },
  ];

  const handleNavClick = (tabId: ActiveTab) => {
    onTabChange(tabId);
    if (onClose) {
      onClose();
    }
  };

  const handleLogout = () => {
    if (onClose) {
      onClose();
    }
    logout();
  };

  const sidebarContent = (isMobileDrawer: boolean = false) => (
    <div className="flex flex-col justify-between h-full bg-[#111111] text-[#F3EEE3]">
      {/* Brand & Active Target */}
      <div className="p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-[#D9541E] flex items-center justify-center font-display font-bold text-lg text-white shadow-crisp">
              CT
            </div>
            <div>
              <h1 className="font-display font-bold tracking-tight text-base text-[#F3EEE3] leading-none">
                CAREER TWIN
              </h1>
              <p className="text-[10px] uppercase font-mono tracking-wider text-neutral-400 mt-1">
                Evidence Engine v2.0
              </p>
            </div>
          </div>

          {/* Close button for mobile drawer */}
          {isMobileDrawer && onClose && (
            <button
              type="button"
              onClick={onClose}
              aria-label="Close Sidebar"
              className="p-1.5 rounded-lg text-neutral-400 hover:text-white hover:bg-white/10 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          )}
        </div>

        {/* Target Role Status Card */}
        <div className="mt-6 p-3 rounded-lg bg-white/5 border border-white/10">
          <div className="text-[10px] font-mono uppercase tracking-wider text-neutral-400">
            Active Role Target
          </div>
          <div className="font-display font-semibold text-sm text-[#F3EEE3] mt-1 truncate">
            {targetRole || 'None Selected'}
          </div>
          <div className="flex items-center gap-1.5 mt-2 text-[11px] text-emerald-400">
            <ShieldCheck className="w-3.5 h-3.5 shrink-0" />
            <span className="truncate">{targetRole ? 'Market Vector Synchronized' : 'Awaiting Selection'}</span>
          </div>
        </div>

        {/* Navigation Items */}
        <nav className="mt-6 space-y-1.5">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => handleNavClick(item.id)}
                className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-[#D9541E] text-white shadow-crisp font-semibold'
                    : 'text-neutral-300 hover:bg-white/10 hover:text-white'
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? 'text-white' : 'text-neutral-400'}`} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>
      </div>

      {/* User Session Footer */}
      <div className="p-4 border-t border-white/10 bg-black/20">
        <div className="flex items-center justify-between">
          <div className="truncate mr-2">
            <div className="text-xs font-semibold text-[#F3EEE3] truncate">
              {user?.name || user?.username || 'Authenticated Candidate'}
            </div>
            <div className="text-[10px] font-mono text-neutral-400 truncate">
              {user?.email}
            </div>
          </div>
          <button
            onClick={handleLogout}
            title="Sign Out"
            className="p-2 rounded-md hover:bg-white/10 text-neutral-400 hover:text-white transition-colors cursor-pointer"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );

  return (
    <>
      {/* 1. Desktop Static Left Command Rail (Visible strictly on lg: >= 1024px) */}
      <aside className="hidden lg:flex w-72 bg-[#111111] text-[#F3EEE3] flex-col justify-between border-r border-black/20 dark:border-white/10 shrink-0 h-screen sticky top-0 z-30">
        {sidebarContent(false)}
      </aside>

      {/* 2. Mobile & Tablet Drawer with Smooth Slide-Over (Visible strictly on < 1024px) */}
      <AnimatePresence>
        {isOpen && (
          <div className="lg:hidden">
            {/* Dark Blurred Backdrop Overlay */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              onClick={onClose}
              className="fixed inset-0 bg-black/60 backdrop-blur-xs z-40"
            />

            {/* Slide-Over Drawer Container */}
            <motion.aside
              initial={{ x: '-100%' }}
              animate={{ x: 0 }}
              exit={{ x: '-100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 260 }}
              className="fixed inset-y-0 left-0 z-50 w-72 max-w-[85vw] shadow-2xl overflow-y-auto"
            >
              {sidebarContent(true)}
            </motion.aside>
          </div>
        )}
      </AnimatePresence>
    </>
  );
};
