import { AnimatePresence, motion } from "framer-motion";
import { HelpCircle } from "lucide-react";
import { useState } from "react";

const TERM_DEFINITIONS = {
  SPD: "Statistical Parity Difference: the outcome rate gap between groups. Ideal value = 0. Above 0.2 indicates high bias.",
  DI:  "Disparate Impact: ratio of positive outcomes between groups. Below 0.8 violates the legal 80% rule (EEOC / EU AI Act).",
  EOD: "Equal Opportunity Difference: the True Positive Rate gap between groups. Ideal value = 0. Measures if one group gets fewer correct positive predictions.",
  AOD: "Average Odds Difference: the average of TPR and FPR gaps between groups. Ideal value = 0. Combines two fairness dimensions.",
  AuditScore:
    "Composite fairness score from 0–100. Think of it like a credit score for bias. Grade A = fair model, Grade F = highly biased model requiring immediate action.",
};

export default function MetricTooltip({ term, children }) {
  const [visible, setVisible] = useState(false);
  const definition = TERM_DEFINITIONS[term];

  if (!definition) return <>{children}</>;

  return (
    <span className="relative inline-flex items-center gap-1 group">
      {children}

      {/* Question mark trigger */}
      <button
        type="button"
        onMouseEnter={() => setVisible(true)}
        onMouseLeave={() => setVisible(false)}
        onFocus={() => setVisible(true)}
        onBlur={() => setVisible(false)}
        className="flex-shrink-0 text-textSecondary hover:text-accent transition-colors duration-150 focus:outline-none"
        aria-label={`What is ${term}?`}
      >
        <HelpCircle size={14} />
      </button>

      {/* Floating tooltip */}
      <AnimatePresence>
        {visible && (
          <motion.div
            role="tooltip"
            initial={{ opacity: 0, y: 6, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 4, scale: 0.96 }}
            transition={{ duration: 0.18, ease: "easeOut" }}
            className="absolute left-1/2 -translate-x-1/2 bottom-full mb-2.5 z-50 w-72 pointer-events-none"
          >
            <div
              className="rounded-xl px-4 py-3 text-left shadow-2xl"
              style={{
                background: "#1E293B",
                border: "1px solid rgba(20,184,166,0.4)",
                boxShadow: "0 8px 32px rgba(0,0,0,0.5), 0 0 0 1px rgba(20,184,166,0.1)",
              }}
            >
              <p className="text-xs font-bold text-accent mb-1">{term}</p>
              <p className="text-xs text-textSecondary leading-relaxed">{definition}</p>
            </div>
            {/* Caret */}
            <div className="absolute left-1/2 -translate-x-1/2 top-full -mt-px">
              <div
                className="w-3 h-1.5"
                style={{
                  clipPath: "polygon(0 0, 100% 0, 50% 100%)",
                  background: "rgba(20,184,166,0.4)",
                }}
              />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </span>
  );
}
