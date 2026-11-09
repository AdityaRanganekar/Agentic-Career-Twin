import React, { useState, useEffect } from 'react';
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { useTheme } from '../context/ThemeContext';

interface CompetencyRadarProps {
  radarDimensions: Record<string, number> | null;
  benchmarkDimensions?: Record<string, number> | null;
  benchmarkName?: string;
  candidateName?: string;
  targetRole?: string;
}

export const CompetencyRadar: React.FC<CompetencyRadarProps> = ({
  radarDimensions,
  benchmarkDimensions,
  benchmarkName,
  candidateName = 'Candidate Competency',
  targetRole = 'Target Role',
}) => {
  const { theme } = useTheme();

  const [windowWidth, setWindowWidth] = useState<number>(
    typeof window !== 'undefined' ? window.innerWidth : 1024
  );

  useEffect(() => {
    const handleResize = () => setWindowWidth(window.innerWidth);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  if (!radarDimensions || Object.keys(radarDimensions).length === 0) {
    return (
      <div className="flex items-center justify-center h-72 sm:h-80 rounded-lg border border-black/10 dark:border-white/10 bg-black/5 dark:bg-white/5 p-4 text-center">
        <p className="text-xs sm:text-sm font-medium text-neutral-500">
          Run an assessment to render the dynamic competency radar footprint.
        </p>
      </div>
    );
  }

  const isMobile = windowWidth < 640;
  const isSmallMobile = windowWidth < 480;

  const formatCategoryLabel = (label: string): string => {
    if (!isSmallMobile) return label;
    // Abbreviate cleanly on narrow phones (< 480px) to prevent axis clipping
    const lower = label.toLowerCase();
    if (lower.includes('database') || lower.includes('storage')) return 'Data/Storage';
    if (lower.includes('backend') || lower.includes('api')) return 'Backend/API';
    if (lower.includes('cloud') || lower.includes('devops')) return 'Cloud/DevOps';
    if (lower.includes('machine learning') || lower.includes('ai')) return 'ML / AI';
    if (lower.includes('generative') || lower.includes('llm')) return 'GenAI/LLM';
    if (lower.includes('frontend')) return 'Frontend';
    if (lower.includes('quantitative') || lower.includes('statistic')) return 'Quant/Stats';
    if (lower.includes('data engineering') || lower.includes('pipeline')) return 'Data Eng';
    if (label.length > 13) return `${label.slice(0, 11)}...`;
    return label;
  };

  const categories = Object.keys(radarDimensions);
  const chartData = categories.map((cat) => ({
    category: formatCategoryLabel(cat),
    fullCategory: cat,
    Candidate: Math.round(radarDimensions[cat] ?? 0),
    Benchmark: Math.round(benchmarkDimensions?.[cat] ?? 85),
  }));

  const isDark = theme === 'dark';
  const gridColor = isDark ? 'rgba(243, 238, 227, 0.18)' : 'rgba(17, 17, 17, 0.14)';
  const tickColor = isDark ? '#F3EEE3' : '#111111';
  const marketStroke = isDark ? '#94A3B8' : '#111111';
  const resolvedBenchmarkName = benchmarkName || `Market Standard (${targetRole})`;

  const chartMargin = isMobile
    ? { top: 15, right: 25, bottom: 15, left: 25 }
    : { top: 25, right: 55, bottom: 25, left: 55 };
  const tickFontSize = isMobile ? 10 : 12;

  return (
    <div className="w-full flex flex-col">
      <div className="w-full h-[290px] sm:h-[380px]">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart
            data={chartData}
            margin={chartMargin}
          >
            <PolarGrid stroke={gridColor} />
            <PolarAngleAxis
              dataKey="category"
              tick={{
                fill: tickColor,
                fontSize: tickFontSize,
                fontFamily: 'Inter, sans-serif',
                fontWeight: 600,
              }}
            />
            <PolarRadiusAxis
              angle={30}
              domain={[0, 100]}
              stroke={gridColor}
              tick={{ fill: tickColor, fontSize: isMobile ? 8 : 9 }}
              tickFormatter={(val) => `${val}%`}
            />

            <Radar
              name={resolvedBenchmarkName}
              dataKey="Benchmark"
              stroke={marketStroke}
              strokeDasharray="4 4"
              strokeWidth={1.5}
              fill="transparent"
            />
            <Radar
              name={candidateName}
              dataKey="Candidate"
              stroke="#D9541E"
              strokeWidth={2.2}
              fill="#D9541E"
              fillOpacity={0.28}
            />

            <Legend
              wrapperStyle={{
                paddingTop: isMobile ? '8px' : '14px',
                fontSize: isMobile ? '11px' : '12px',
                fontFamily: 'Inter, sans-serif',
              }}
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
