import React from 'react';
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

  if (!radarDimensions || Object.keys(radarDimensions).length === 0) {
    return (
      <div className="flex items-center justify-center h-80 rounded-lg border border-black/10 dark:border-white/10 bg-black/5 dark:bg-white/5">
        <p className="text-sm font-medium text-neutral-500">
          Run an assessment to render the dynamic competency radar footprint.
        </p>
      </div>
    );
  }

  const categories = Object.keys(radarDimensions);
  const chartData = categories.map((cat) => ({
    category: cat,
    Candidate: Math.round(radarDimensions[cat] ?? 0),
    Benchmark: Math.round(benchmarkDimensions?.[cat] ?? 85),
  }));

  const isDark = theme === 'dark';
  const gridColor = isDark ? 'rgba(243, 238, 227, 0.18)' : 'rgba(17, 17, 17, 0.14)';
  const tickColor = isDark ? '#F3EEE3' : '#111111';
  const marketStroke = isDark ? '#94A3B8' : '#111111';
  const resolvedBenchmarkName = benchmarkName || `Market Standard (${targetRole})`;

  return (
    <div className="w-full flex flex-col">
      <div className="w-full h-[360px]">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart
            data={chartData}
            margin={{ top: 25, right: 55, bottom: 25, left: 55 }}
          >
            <PolarGrid stroke={gridColor} />
            <PolarAngleAxis
              dataKey="category"
              tick={{
                fill: tickColor,
                fontSize: 11,
                fontFamily: 'Inter, sans-serif',
                fontWeight: 600,
              }}
            />
            <PolarRadiusAxis
              angle={30}
              domain={[0, 100]}
              stroke={gridColor}
              tick={{ fill: tickColor, fontSize: 9 }}
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
                paddingTop: '14px',
                fontSize: '12px',
                fontFamily: 'Inter, sans-serif',
              }}
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
