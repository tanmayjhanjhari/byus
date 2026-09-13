import { AlertTriangle, CheckCircle, Info, ShieldAlert, ShieldCheck, ShieldX } from "lucide-react";
import { motion } from "framer-motion";

export default function ValidationBanner({ validation, metricsPerAttr, auditScore, grade, overallSeverity }) {
  if (!validation) return null;

  const warnings = validation.warnings || [];

  // Check if any CI crosses 0
  let ciCrossesZero = false;
  if (metricsPerAttr) {
    for (const attr of Object.values(metricsPerAttr)) {
      if (attr.bootstrapped_ci) {
        const { low_95, high_95 } = attr.bootstrapped_ci;
        if (low_95 < 0 && high_95 > 0) ciCrossesZero = true;
      }
    }
  }

  const hasDataIssues = warnings.length > 0 || ciCrossesZero || validation.fallback_needed;

  // Derive grade letter (grade may be "A", "B", "C", "F" or full strings)
  const gradeLetter = grade ? grade.charAt(0).toUpperCase() : null;

  // Bias status card config
  const biasConfig = (() => {
    const score = auditScore ?? 0;
    if (gradeLetter === "F" || score < 50) {
      return {
        icon: ShieldX,
        bg: "bg-red-500/15",
        border: "border-red-500/40",
        text: "text-red-400",
        heading: "⚠ HIGH BIAS DETECTED — Immediate Action Required",
        body: `Audit score ${score}/100. One or more sensitive attributes show significant discrimination. Review the findings below and proceed to mitigation.`,
      };
    }
    if (gradeLetter === "C" || score < 70) {
      return {
        icon: AlertTriangle,
        bg: "bg-amber-500/15",
        border: "border-amber-500/40",
        text: "text-amber-400",
        heading: "⚠ MODERATE BIAS DETECTED — Remediation Recommended",
        body: `Audit score ${score}/100. Bias is present but within a manageable range. Apply mitigation before deployment.`,
      };
    }
    if (gradeLetter === "B" || score < 85) {
      return {
        icon: AlertTriangle,
        bg: "bg-yellow-500/10",
        border: "border-yellow-500/30",
        text: "text-yellow-400",
        heading: "ℹ MINOR BIAS DETECTED — Monitor Closely",
        body: `Audit score ${score}/100. Small disparities exist. Review findings and set up ongoing monitoring.`,
      };
    }
    return {
      icon: ShieldCheck,
      bg: "bg-green-500/10",
      border: "border-green-500/30",
      text: "text-green-400",
      heading: "✓ SYSTEM APPEARS FAIR",
      body: `Audit score ${score}/100. No significant bias detected across analyzed attributes.`,
    };
  })();

  const BiasIcon = biasConfig.icon;

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      className="h-full flex flex-col gap-3"
    >
      {/* ── Section A: Dataset Quality ── */}
      <div className={`p-4 rounded-xl border flex-1 ${
        hasDataIssues
          ? "bg-warning/10 border-warning/30"
          : "bg-success/10 border-success/30"
      }`}>
        <div className="flex items-center gap-2 mb-1.5">
          {hasDataIssues
            ? <AlertTriangle size={16} className="text-warning" />
            : <CheckCircle size={16} className="text-success" />}
          <h3 className={`text-sm font-semibold ${hasDataIssues ? "text-warning" : "text-success"}`}>
            Dataset Quality
          </h3>
        </div>
        <p className="text-xs text-textSecondary mb-2">Technical checks on your uploaded dataset</p>

        <div className="text-xs text-textSecondary space-y-1.5">
          <p>
            <span className="font-medium text-textPrimary">Engine: </span>
            {validation.engine === "fairlens" ? "ByUs Core (Binary)" : "Fairlearn Fallback"}
          </p>

          {warnings.length > 0 && (
            <ul className="list-disc list-inside space-y-0.5">
              {warnings.map((w, i) => (
                <li key={i}>{w}</li>
              ))}
            </ul>
          )}

          {ciCrossesZero && (
            <div className="flex items-start gap-1.5 mt-1">
              <Info size={14} className="text-warning shrink-0 mt-0.5" />
              <p>Some metrics cross zero in their 95% CI — bias may not be statistically significant.</p>
            </div>
          )}

          {!hasDataIssues && (
            <p className="text-success/80">No critical warnings detected during dataset validation.</p>
          )}
        </div>
      </div>

      {/* ── Section B: Bias Status ── */}
      {gradeLetter && (
        <div className={`p-4 rounded-xl border ${biasConfig.bg} ${biasConfig.border}`}>
          <div className="flex items-center gap-2 mb-2">
            <BiasIcon size={18} className={biasConfig.text} />
            <h3 className={`text-sm font-bold ${biasConfig.text}`}>
              {biasConfig.heading}
            </h3>
          </div>
          <p className="text-xs text-textSecondary leading-relaxed">
            {biasConfig.body}
          </p>
        </div>
      )}
    </motion.div>
  );
}
