import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { CheckCircle, AlertTriangle, ChevronDown, ChevronUp } from "lucide-react";

export default function PreprocessingReport({ report }) {
  const [expanded, setExpanded] = useState(false);

  if (!report) return null;

  const {
    original_format,
    final_rows,
    final_cols,
    duplicates_removed,
    missing_values_standardized,
    headers_added,
    uci_adult_detected,
    columns_renamed,
    dtype_conversions,
    warnings
  } = report;

  const hasWarnings = warnings && warnings.length > 0;
  const renamesCount = columns_renamed ? Object.keys(columns_renamed).length : 0;
  const dtypesCount = dtype_conversions ? Object.keys(dtype_conversions).length : 0;

  return (
    <div className="glass-card border border-success/30 overflow-hidden mb-6">
      {/* Header (Always visible) */}
      <div 
        className="p-4 flex items-center justify-between cursor-pointer hover:bg-white/[0.02] transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 text-success font-medium">
            <CheckCircle size={18} />
            <span>Dataset ready</span>
          </div>
          
          <div className="h-4 w-px bg-white/10 hidden sm:block" />
          
          <div className="flex flex-wrap items-center gap-2">
            <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-surface border border-white/10 text-textSecondary">
              {final_rows?.toLocaleString()} rows
            </span>
            <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-surface border border-white/10 text-textSecondary">
              {final_cols?.toLocaleString()} columns
            </span>
            <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-accent/10 border border-accent/20 text-accent uppercase">
              {original_format} detected
            </span>
          </div>

          {hasWarnings && (
            <div className="flex items-center gap-1.5 ml-2 px-2 py-0.5 rounded-full text-xs font-medium bg-warning/10 text-warning border border-warning/20">
              <AlertTriangle size={12} />
              <span>{warnings.length} warning{warnings.length > 1 ? "s" : ""}</span>
            </div>
          )}
        </div>

        <button className="text-textSecondary hover:text-textPrimary transition-colors p-1">
          {expanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
        </button>
      </div>

      {/* Expanded Content */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: "easeInOut" }}
            className="border-t border-white/[0.06]"
          >
            <div className="p-4 space-y-4">
              <p className="text-xs font-semibold text-textSecondary uppercase tracking-wider">
                Auto-Preprocessing Summary
              </p>
              
              <div className="flex flex-col gap-2">
                {uci_adult_detected && (
                  <div className="inline-flex w-fit items-center gap-2 px-3 py-1.5 rounded-md bg-accent/10 text-accent border border-accent/20 text-sm">
                    UCI Adult dataset detected — <code>income_binary</code> column added
                  </div>
                )}
                
                {headers_added && (
                  <div className="inline-flex w-fit items-center gap-2 px-3 py-1.5 rounded-md bg-accent2/10 text-accent2 border border-accent2/20 text-sm">
                    Auto-generated column headers
                  </div>
                )}

                {duplicates_removed > 0 && (
                  <div className="inline-flex w-fit items-center gap-2 px-3 py-1.5 rounded-md bg-warning/10 text-warning border border-warning/20 text-sm">
                    Removed {duplicates_removed.toLocaleString()} duplicate row{duplicates_removed !== 1 ? "s" : ""}
                  </div>
                )}

                {missing_values_standardized > 0 && (
                  <div className="inline-flex w-fit items-center gap-2 px-3 py-1.5 rounded-md bg-accent2/10 text-accent2 border border-accent2/20 text-sm">
                    Standardized {missing_values_standardized.toLocaleString()} missing value{missing_values_standardized !== 1 ? "s" : ""}
                  </div>
                )}

                {hasWarnings && (
                  <div className="flex flex-col gap-1 mt-2">
                    {warnings.map((warn, i) => (
                      <div key={i} className="flex items-start gap-2 text-sm text-warning">
                        <AlertTriangle size={14} className="mt-0.5 flex-shrink-0" />
                        <span>{warn}</span>
                      </div>
                    ))}
                  </div>
                )}

                {dtypesCount > 0 && (
                  <div className="mt-2">
                    <p className="text-xs text-textSecondary mb-1">Converted {dtypesCount} column{dtypesCount !== 1 ? "s" : ""} to numeric:</p>
                    <p className="text-sm text-textPrimary">
                      {Object.keys(dtype_conversions).join(", ")}
                    </p>
                  </div>
                )}

                {renamesCount > 0 && (
                  <div className="mt-2">
                    <p className="text-xs text-textSecondary mb-1.5">Normalized {renamesCount} column name{renamesCount !== 1 ? "s" : ""}:</p>
                    <div className="overflow-x-auto max-w-lg border border-white/10 rounded-lg">
                      <table className="w-full text-left text-sm text-textSecondary">
                        <thead className="bg-white/5 border-b border-white/10">
                          <tr>
                            <th className="px-3 py-1.5 font-medium">Original Name</th>
                            <th className="px-3 py-1.5 font-medium">Cleaned Name</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5">
                          {Object.entries(columns_renamed).map(([oldName, newName]) => (
                            <tr key={oldName}>
                              <td className="px-3 py-1.5 line-through opacity-70">{oldName}</td>
                              <td className="px-3 py-1.5 text-textPrimary">{newName}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
