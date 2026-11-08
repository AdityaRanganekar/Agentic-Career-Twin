import React from 'react';
import { Sun, Moon } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';

interface HeaderProps {
  title: string;
  subtitle?: string;
}

export const Header: React.FC<HeaderProps> = ({ title, subtitle }) => {
  const { theme, toggleTheme } = useTheme();

  return (
    <header className="h-16 px-8 border-b border-black/10 dark:border-white/10 flex items-center justify-between shrink-0 bg-canvas-card/80 dark:bg-black/40 backdrop-blur-md sticky top-0 z-20">
      <div>
        <h2 className="font-display font-bold text-base tracking-tight text-[#111111] dark:text-[#F3EEE3]">
          {title}
        </h2>
        {subtitle && (
          <p className="text-xs text-neutral-500 dark:text-neutral-400">
            {subtitle}
          </p>
        )}
      </div>

      {/* Single-Icon Current Mode Toggle: Shows ONLY Sun in Light mode, Moon in Dark mode */}
      <button
        type="button"
        onClick={toggleTheme}
        aria-label={theme === 'light' ? 'Switch to Dark Obsidian mode' : 'Switch to Light Editorial mode'}
        title={theme === 'light' ? 'Light Editorial (Click to switch to Dark Obsidian)' : 'Dark Obsidian (Click to switch to Light Editorial)'}
        className="p-2.5 rounded-lg border border-black/15 dark:border-white/15 bg-white/80 dark:bg-black/50 text-[#111111] dark:text-[#F3EEE3] hover:border-[#D9541E] dark:hover:border-[#D9541E] transition-all shadow-crisp flex items-center justify-center cursor-pointer"
      >
        {theme === 'light' ? (
          <Sun className="w-4 h-4 text-[#D9541E]" />
        ) : (
          <Moon className="w-4 h-4 text-[#F3EEE3]" />
        )}
      </button>
    </header>
  );
};
