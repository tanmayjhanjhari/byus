import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { Check, Scan, BrainCircuit } from "lucide-react";
import { Link, useLocation } from "react-router-dom";
import useAnalysisStore from "../../store/analysisStore";
import client from "../../api/client";

const STEPS = [
  { label: "Upload",     path: "/",            step: 0 },
  { label: "Configure",  path: "/analyze",     step: 1 },
  { label: "Analyze",    path: "/results",     step: 2 },
  { label: "Remediate",  path: "/remediate",   step: 3 },
  { label: "Report",     path: "/report-view", step: 4 },
];

const StepDot = ({ label, stepIndex, currentStep }) => {
  const isCompleted = currentStep > stepIndex;
  const isActive    = currentStep === stepIndex;

  return (
    <div className="flex items-center gap-2">
      <motion.div
        animate={{
          backgroundColor: isCompleted
            ? "#22C55E"
            : isActive
            ? "#14B8A6"
            : "#334155",
          scale: isActive ? 1.15 : 1,
        }}
        transition={{ duration: 0.25 }}
        className="w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0"
      >
        {isCompleted ? (
          <Check size={12} strokeWidth={3} className="text-white" />
        ) : (
          <span className={`text-[10px] font-bold ${isActive ? "text-primary" : "text-textSecondary"}`}>
            {stepIndex + 1}
          </span>
        )}
      </motion.div>
      <span
        className={`text-sm font-medium hidden sm:inline transition-colors duration-200 ${
          isActive
            ? "text-accent"
            : isCompleted
            ? "text-success"
            : "text-textSecondary"
        }`}
      >
        {label}
      </span>
    </div>
  );
};

const StepConnector = ({ completed }) => (
  <div className="flex-1 mx-2 h-px max-w-[48px]">
    <motion.div
      animate={{ backgroundColor: completed ? "#22C55E" : "#334155" }}
      transition={{ duration: 0.3 }}
      className="w-full h-full"
    />
  </div>
);

function LearningPill() {
  const [stats, setStats] = useState({ total_examples: 0, learned_from_uploads: 0 });
  const [glowing, setGlowing] = useState(false);
  const [showTooltip, setShowTooltip] = useState(false);
  const prevTotal = useRef(0);
  const location = useLocation();

  const fetchStats = async () => {
    try {
      const { data } = await client.get("/api/learning-stats");
      setStats(data);
      if (prevTotal.current > 0 && data.total_examples > prevTotal.current) {
        setGlowing(true);
        setTimeout(() => setGlowing(false), 2000);
      }
      prevTotal.current = data.total_examples;
    } catch {
      // silently fail — navbar should never break
    }
  };

  // Fetch on mount
  useEffect(() => { fetchStats(); }, []);

  // Refetch on navigation to /results
  useEffect(() => {
    if (location.pathname === "/results") fetchStats();
  }, [location.pathname]);

  return (
    <div className="relative" onMouseEnter={() => setShowTooltip(true)} onMouseLeave={() => setShowTooltip(false)}>
      <motion.div
        animate={glowing
          ? { boxShadow: ["0 0 0px #14B8A6", "0 0 16px #14B8A6", "0 0 0px #14B8A6"] }
          : { boxShadow: "0 0 0px transparent" }
        }
        transition={{ duration: 2, ease: "easeInOut" }}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-accent/15 border border-accent/25 cursor-default"
      >
        <BrainCircuit size={14} className="text-accent flex-shrink-0" />
        <span className="text-xs font-semibold text-accent whitespace-nowrap">
          {stats.total_examples} cases learned
        </span>
      </motion.div>

      {/* Tooltip */}
      {showTooltip && (
        <motion.div
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          className="absolute right-0 top-full mt-2 w-64 bg-surface border border-white/10 rounded-xl p-3 shadow-2xl z-50 text-xs text-textSecondary leading-relaxed"
        >
          <p className="text-textPrimary font-semibold mb-1">Auto-Learning Active</p>
          <p>ByUs learns from every dataset analyzed.</p>
          <p className="mt-1">Started with <span className="text-accent font-medium">20</span> research cases.</p>
          <p className="mt-1">
            <span className="text-accent font-medium">{stats.learned_from_uploads}</span> real-world uploads added so far.
          </p>
        </motion.div>
      )}
    </div>
  );
}

export default function AppShell() {
  const currentStep = useAnalysisStore((s) => s.step);

  return (
    <header className="sticky top-0 z-50 bg-primary/95 backdrop-blur-md border-b border-white/[0.06]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 flex items-center justify-between h-16">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2 group flex-shrink-0">
          <div className="w-8 h-8 rounded-lg bg-accent/20 flex items-center justify-center group-hover:bg-accent/30 transition-colors">
            <Scan size={18} className="text-accent" />
          </div>
          <span className="text-lg font-bold text-textPrimary">
            By<span className="text-accent">Us</span>
          </span>
        </Link>

        {/* Step indicator */}
        <nav className="flex items-center" aria-label="Progress">
          {STEPS.map((s, idx) => (
            <div key={s.step} className="flex items-center">
              <StepDot
                label={s.label}
                stepIndex={s.step}
                currentStep={currentStep}
              />
              {idx < STEPS.length - 1 && (
                <StepConnector completed={currentStep > s.step} />
              )}
            </div>
          ))}
        </nav>

        {/* Learning pill */}
        <LearningPill />
      </div>
    </header>
  );
}
