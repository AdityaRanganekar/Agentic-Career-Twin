import React, { useState } from 'react';
import { useAuth, AuthProvider } from './context/AuthContext';
import { useTheme, ThemeProvider } from './context/ThemeContext';
import { AuthPortal } from './views/AuthPortal';
import { DashboardView } from './views/DashboardView';
import { RoadmapView } from './views/RoadmapView';
import { HistoryView } from './views/HistoryView';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { ActiveTab, AnalysisResult } from './types';

const MainLayout: React.FC = () => {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<ActiveTab>('overview');
  const [targetRole, setTargetRole] = useState('Data Scientist');
  const [latestResult, setLatestResult] = useState<AnalysisResult | null>(null);

  if (!user) {
    return <AuthPortal />;
  }

  const getTabTitle = () => {
    switch (activeTab) {
      case 'overview':
        return 'Assessment Diagnostic Workspace';
      case 'roadmap':
        return 'Multi-Platform Learning Hub';
      case 'history':
        return 'Candidate Assessment Trajectory';
      default:
        return 'Career Twin Workspace';
    }
  };

  const getTabSubtitle = () => {
    switch (activeTab) {
      case 'overview':
        return `Evaluating verified competency footprint for ${targetRole}`;
      case 'roadmap':
        return 'Targeted study curricula with direct course search parameters';
      case 'history':
        return 'Chronological evaluation log and archived study resources';
      default:
        return undefined;
    }
  };

  return (
    <div className="flex min-h-screen bg-[var(--canvas-bg)] text-[var(--ink-primary)]">
      {/* Sidebar Rail */}
      <Sidebar
        activeTab={activeTab}
        onTabChange={setActiveTab}
        targetRole={targetRole}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        <Header
          title={getTabTitle()}
          subtitle={getTabSubtitle()}
        />

        <main className="flex-1 p-6 md:p-8 max-w-7xl w-full mx-auto">
          {activeTab === 'overview' && (
            <DashboardView
              onNavigateTab={setActiveTab}
              targetRole={targetRole}
              setTargetRole={setTargetRole}
              latestResult={latestResult}
              setLatestResult={setLatestResult}
            />
          )}

          {activeTab === 'roadmap' && (
            <RoadmapView
              recommendations={latestResult?.recommendations || []}
              targetRole={targetRole}
            />
          )}

          {activeTab === 'history' && <HistoryView />}
        </main>
      </div>
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <ThemeProvider>
      <AuthProvider>
        <MainLayout />
      </AuthProvider>
    </ThemeProvider>
  );
};

export default App;

