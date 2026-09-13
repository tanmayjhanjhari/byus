import { motion } from "framer-motion";
import { AlertTriangle, Info, CheckCircle } from "lucide-react";
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
        {(value === undefined || value === null) && (
          <div className="mb-1" title="Upload a trained ML model (.pkl) alongside your dataset to compute model-based metrics like EOD and AOD.">
            <Info size={16} className="text-textSecondary cursor-help" />
          </div>
        )}
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

export default function MetricCards({
  metrics,
  worstGroup,
  bestGroup,
  gapPct,
  plainReason,
  grade,
}) {
  if (!metrics) return null;

  // Handle both upper/lower case keys from backend
  const getVal = (key) => metrics[key] ?? metrics[key.toUpperCase()] ?? metrics[key.toLowerCase()];

  const spd = getVal('spd');
  const di = getVal('di');
  const eod = getVal('eod');
  const aod = getVal('aod');
  const severity = getVal('severity') || 'low';
  const legalFlag = getVal('legal_flag');

  // Derive "Why This Matters" card config
  const gradeLetter = grade ? grade.charAt(0).toUpperCase() : null;
  const isHigh   = severity === "high" || gradeLetter === "F";
  const isMedium = severity === "medium" && gradeLetter !== "F";

  const gap = gapPct != null ? Number(gapPct) : null;
  const diVal = di != null ? Number(di) : null;

  const whyText = (() => {
    if (isHigh && gap != null && worstGroup && bestGroup) {
      const legalViol = diVal != null && diVal < 0.8
        ? " violates the legal 80% fairness rule and"
        : "";
      return (
        `For every 100 people from '${worstGroup}', approximately ${Math.round(gap)} fewer receive ` +
        `a positive outcome compared to '${bestGroup}'. This ${gap.toFixed(1)}% gap${legalViol} ` +
        `indicates your system is treating these groups very differently.`
      );
    }
    if (isMedium && gap != null) {
      return (
        `A ${gap.toFixed(1)}% outcome gap exists between groups. While below the high-severity ` +
        `threshold, this gap affects real people and should be addressed before deployment.`
      );
    }
    if (severity === "low" || (!isHigh && !isMedium)) {
      const attr = metrics?.privileged_group ? `'${metrics.privileged_group}' vs '${metrics.unprivileged_group}'` : "the groups analyzed";
      return `No significant bias detected for ${attr}. The outcome gap between groups is within acceptable fairness thresholds.`;
    }
    return null;
  })();

  const whyBorderColor = isHigh
    ? "border-l-red-500"
    : isMedium
    ? "border-l-amber-500"
    : "border-l-green-500";

  const whyBg = isHigh
    ? "bg-red-500/8"
    : isMedium
    ? "bg-amber-500/8"
    : "bg-green-500/8";

  const whyHeading = isHigh
    ? "⚠ Action Required"
    : isMedium
    ? "⚠ Bias Detected — Review Recommended"
    : "✓ No Significant Bias";

  const whyHeadingColor = isHigh
    ? "text-red-400"
    : isMedium
    ? "text-amber-400"
    : "text-green-400";

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

      {/* ── Why This Matters ── */}
      {whyText && (
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5, duration: 0.4 }}
          className={`border-l-4 ${whyBorderColor} ${whyBg} rounded-r-xl p-4`}
        >
          <h4 className={`text-sm font-bold mb-1 ${whyHeadingColor}`}>
            {whyHeading}
          </h4>
          <p className="text-sm text-textSecondary leading-relaxed">
            {whyText}
          </p>
          {isHigh && plainReason && (
            <div className="mt-3 flex items-start gap-2 bg-accent/10 border border-accent/20 rounded-lg p-3">
              <Info size={14} className="text-accent shrink-0 mt-0.5" />
              <p className="text-xs text-accent leading-relaxed">
                <span className="font-semibold">Most likely cause: </span>
                {plainReason}
              </p>
            </div>
          )}
        </motion.div>
      )}
    </div>
  );
}
