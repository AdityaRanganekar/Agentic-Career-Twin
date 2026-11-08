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
  jdRadarDimensions?: Record<string, number> | null;
  targetRole: string;
}

export const CompetencyRadar: React.FC<CompetencyRadarProps> = ({
  radarDimensions,
  jdRadarDimensions,
  targetRole,
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
    Candidate: Math.round(radarDimensions[cat] || 0),
    MarketStandard: 85,
    ...(jdRadarDimensions && jdRadarDimensions[cat] !== undefined
      ? { TargetJD: Math.round(jdRadarDimensions[cat] || 60) }
      : {}),
  }));

  const isDark = theme === 'dark';
  const gridColor = isDark ? 'rgba(243, 238, 227, 0.18)' : 'rgba(17, 17, 17, 0.14)';
  const tickColor = isDark ? '#F3EEE3' : '#111111';
  const marketStroke = isDark ? '#94A3B8' : '#111111';

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
              name={`Market Standard (${targetRole})`}
              dataKey="MarketStandard"
              stroke={marketStroke}
              strokeDasharray="4 4"
              strokeWidth={1.5}
              fill="transparent"
            />
            <Radar
              name="Candidate Competency"
              dataKey="Candidate"
              stroke="#D9541E"
              strokeWidth={2.2}
              fill="#D9541E"
              fillOpacity={0.28}
            />
            {jdRadarDimensions && (
              <Radar
                name="Target Job Footprint"
                dataKey="TargetJD"
                stroke="#16A34A"
                strokeWidth={2}
                fill="#16A34A"
                fillOpacity={0.16}
              />
            )}
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
      <p className="mt-3 text-xs text-neutral-600 dark:text-neutral-400 text-center leading-relaxed font-sans">
        A broader, symmetrical polygon signifies balanced competency coverage across core architectural disciplines, whereas inward vertices indicate skill gap areas.
      </p>
    </div>
  );
};

