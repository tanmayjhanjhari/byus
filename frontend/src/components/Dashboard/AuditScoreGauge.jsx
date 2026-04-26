import { animate, motion, useMotionValue, useTransform } from "framer-motion";
import { useEffect, useState } from "react";
import MetricTooltip from "../Onboarding/MetricTooltip";

export default function AuditScoreGauge({ score, grade }) {
  const [displayScore, setDisplayScore] = useState(0);
  const motionScore = useMotionValue(0);

  // SVG parameters
  const size = 200;
  const strokeWidth = 16;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  
  // Transform score (0-100) to dashoffset
  const dashoffset = useTransform(motionScore, [0, 100], [circumference, 0]);

  useEffect(() => {
    const controls = animate(motionScore, score || 0, {
      duration: 1.5,
      ease: "easeOut",
      onUpdate: (latest) => setDisplayScore(Math.round(latest)),
    });
    return controls.stop;
  }, [score, motionScore]);

  let color = "#EF4444"; // Red (F)
  if (score > 75) color = "#22C55E"; // Green (A)
  else if (score > 50) color = "#F59E0B"; // Amber (B/C)

  return (
    <div className="flex flex-col items-center">
      <div className="relative w-[200px] h-[200px] flex items-center justify-center">
        {/* Background Circle */}
        <svg className="absolute inset-0 w-full h-full transform -rotate-90">
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke="rgba(148,163,184,0.1)"
            strokeWidth={strokeWidth}
            fill="none"
          />
          {/* Animated Progress Circle */}
          <motion.circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke={color}
            strokeWidth={strokeWidth}
            fill="none"
            strokeLinecap="round"
            style={{
              strokeDasharray: circumference,
              strokeDashoffset: dashoffset,
            }}
          />
        </svg>

        {/* Center Text */}
        <div className="text-center z-10 flex flex-col items-center justify-center">
          <span className="text-5xl font-bold" style={{ color }}>
            {displayScore}
          </span>
          <span className="text-xl font-semibold text-textSecondary mt-1">
            Grade {grade || "?"}
          </span>
        </div>
      </div>

      <div className="mt-4">
         <MetricTooltip term="AuditScore">
            <span className="text-sm font-semibold text-textPrimary uppercase tracking-wider cursor-help border-b border-dashed border-textSecondary/50 pb-0.5">
               Bias Audit Score
            </span>
         </MetricTooltip>
      </div>
    </div>
  );
}
