import React from 'react';
import { motion } from 'framer-motion';
import { Award } from 'lucide-react';

interface ScoreGaugeProps {
  score: number;
  size?: number;
  strokeWidth?: number;
  color?: string;
  label?: string;
  showScoreText?: boolean;
  icon?: React.ReactNode;
}

export const ScoreGauge: React.FC<ScoreGaugeProps> = ({
  score,
  size = 110,
  strokeWidth = 9,
  color = '#D9541E',
  label,
  showScoreText = false,
  icon,
}) => {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (Math.min(Math.max(score, 0), 100) / 100) * circumference;

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="transform -rotate-90">
        {/* Background track */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="currentColor"
          strokeWidth={strokeWidth}
          fill="transparent"
          className="text-black/10 dark:text-white/10"
        />
        {/* Animated Progress arc */}
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={color}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset }}
          transition={{ duration: 1.2, ease: 'easeOut' }}
          strokeLinecap="round"
          fill="transparent"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
        {showScoreText ? (
          <>
            <span className="font-display text-2xl font-bold tracking-tight">
              {score.toFixed(1)}%
            </span>
            {label && (
              <span className="text-[10px] uppercase font-semibold text-neutral-500 tracking-wider">
                {label}
              </span>
            )}
          </>
        ) : (
          icon || <Award className="w-8 h-8 text-[#D9541E]" />
        )}
      </div>
    </div>
  );
};

