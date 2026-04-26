import { AlertTriangle, CheckCircle, Info } from "lucide-react";
import { motion } from "framer-motion";

export default function ValidationBanner({ validation, metricsPerAttr }) {
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

  const hasIssues = warnings.length > 0 || ciCrossesZero || validation.fallback_needed;
  const bgColor = hasIssues ? "bg-warning/10" : "bg-success/10";
  const borderColor = hasIssues ? "border-warning/30" : "border-success/30";
  const textColor = hasIssues ? "text-warning" : "text-success";
  const Icon = hasIssues ? AlertTriangle : CheckCircle;

  return (
    <motion.div 
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      className={`p-4 rounded-xl border ${bgColor} ${borderColor} h-full flex flex-col`}
    >
      <div className="flex items-center gap-2 mb-3">
        <Icon size={20} className={textColor} />
        <h3 className={`font-semibold ${textColor}`}>
          {hasIssues ? "Analysis Flags" : "All Clear"}
        </h3>
      </div>
      
      <div className="text-sm text-textSecondary space-y-2 flex-1">
        <p>
          <span className="font-medium text-textPrimary">Engine:</span>{" "}
          {validation.engine === "fairlens" ? "ByUs Core (Binary)" : "Fairlearn Fallback"}
        </p>

        {warnings.length > 0 && (
          <ul className="list-disc list-inside space-y-1">
            {warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        )}

        {ciCrossesZero && (
          <div className="flex items-start gap-1.5 mt-2">
            <Info size={16} className="text-warning shrink-0 mt-0.5" />
            <p>Some metrics cross zero in their 95% confidence interval, indicating the measured bias might not be statistically significant.</p>
          </div>
        )}
        
        {!hasIssues && (
          <p>No critical warnings detected during dataset validation.</p>
        )}
      </div>
    </motion.div>
  );
}
