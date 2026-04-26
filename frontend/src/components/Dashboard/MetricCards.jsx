import { motion } from "framer-motion";
import { AlertTriangle } from "lucide-react";
import MetricTooltip from "../Onboarding/MetricTooltip";

const SEVERITY_COLORS = {
  high: "bg-danger/20 text-danger border-danger/30",
  medium: "bg-warning/20 text-warning border-warning/30",
  low: "bg-success/20 text-success border-success/30",
};

function Card({ title, term, value, isWarning, delay }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.4 }}
      className="glass-card p-5 border border-white/[0.06] hover:border-accent/40 transition-colors"
    >
      <div className="flex items-center justify-between mb-2">
        <MetricTooltip term={term}>
          <span className="text-sm font-semibold text-textSecondary uppercase tracking-wider cursor-help border-b border-dashed border-textSecondary/50 pb-0.5">
            {title}
          </span>
        </MetricTooltip>
      </div>
      
      <div className="flex items-end gap-3 mt-4">
        <span className="text-4xl font-bold text-textPrimary">
          {value !== undefined && value !== null ? Number(value).toFixed(3) : "N/A"}
        </span>
      </div>

      {isWarning && (
        <div className="mt-3 inline-flex items-center gap-1.5 px-2 py-1 rounded-md bg-danger/10 border border-danger/20">
          <AlertTriangle size={14} className="text-danger" />
          <span className="text-xs font-medium text-danger">Fails Legal 80% Rule</span>
        </div>
      )}
    </motion.div>
  );
}

export default function MetricCards({ metrics }) {
  if (!metrics) return null;

  // Handle both upper/lower case keys from backend
  const getVal = (key) => metrics[key] ?? metrics[key.toUpperCase()] ?? metrics[key.toLowerCase()];

  const spd = getVal('spd');
  const di = getVal('di');
  const eod = getVal('eod');
  const aod = getVal('aod');
  const severity = getVal('severity') || 'low';
  const legalFlag = getVal('legal_flag');

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
         <h3 className="text-lg font-semibold text-textPrimary">Fairness Metrics</h3>
         <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase border ${SEVERITY_COLORS[severity] || SEVERITY_COLORS.low}`}>
           Severity: {severity}
         </span>
      </div>
      
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card title="Stat Parity Diff" term="SPD" value={spd} delay={0.1} />
        <Card title="Disparate Impact" term="DI" value={di} isWarning={legalFlag} delay={0.2} />
        <Card title="Equal Opp Diff" term="EOD" value={eod} delay={0.3} />
        <Card title="Avg Odds Diff" term="AOD" value={aod} delay={0.4} />
      </div>
    </div>
  );
}
