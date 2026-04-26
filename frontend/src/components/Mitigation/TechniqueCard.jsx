import { motion } from "framer-motion";
import { ArrowDown, ArrowUp, Info, Trophy } from "lucide-react";

const getVal = (obj, key) => obj?.[key] ?? obj?.[key.toUpperCase()] ?? obj?.[key.toLowerCase()];

function DeltaRow({ label, before, after }) {
  const b = before ?? 0;
  const a = after ?? 0;
  const delta = a - b;
  const absDelta = Math.abs(delta);
  
  // For SPD/DI/EOD/AOD, we want them closer to ideal (0 for SPD/EOD/AOD, 1 for DI)
  // Simple heuristic: if magnitude of 'after' is less than 'before' (or closer to 1 for DI), it's an improvement.
  let isImprovement = false;
  if (label.toUpperCase() === 'DI') {
     isImprovement = Math.abs(1 - a) < Math.abs(1 - b);
  } else {
     isImprovement = Math.abs(a) < Math.abs(b);
  }

  return (
    <div className="flex items-center justify-between py-2 border-b border-white/[0.04] last:border-0">
      <span className="text-sm font-medium text-textSecondary w-16">{label}</span>
      <span className="text-sm text-textPrimary w-16 text-right">{b.toFixed(3)}</span>
      <span className="text-sm text-textPrimary w-16 text-right">{a.toFixed(3)}</span>
      <span className={`text-sm font-medium w-20 flex items-center justify-end gap-1 ${isImprovement ? "text-success" : "text-danger"}`}>
        {isImprovement ? <ArrowDown size={14} /> : <ArrowUp size={14} />}
        {absDelta.toFixed(3)}
      </span>
    </div>
  );
}

function MetricCompact({ label, before, after }) {
  const b = before ?? 0;
  const a = after ?? 0;
  const delta = a - b;
  const isDrop = delta < 0;
  
  return (
    <div>
       <p className="text-[10px] text-textSecondary uppercase tracking-wider mb-1">{label}</p>
       <div className="flex items-baseline gap-1.5">
          <span className="text-base font-bold text-textPrimary">{a.toFixed(3)}</span>
          <span className={`text-[10px] font-medium ${isDrop ? "text-danger" : "text-success"}`}>
             {delta > 0 ? "+" : ""}{delta.toFixed(3)}
          </span>
       </div>
    </div>
  );
}

export default function TechniqueCard({ name, data, isWinner }) {
  if (!data || !data.before || !data.after) return null;

  const title = name === "reweigh" ? "Reweighing" : "Threshold Adjustment";
  const desc = name === "reweigh" 
    ? "Adjusts training data weights to ensure demographic balance." 
    : "Finds per-group decision thresholds to equalise true positive rates.";

  const before = data.before;
  const after = data.after;
  const effects = data.effects || {};

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={`relative glass-card p-6 border ${
        isWinner ? "border-accent/50 shadow-[0_0_15px_rgba(20,184,166,0.15)]" : "border-white/[0.06]"
      } transition-all duration-300`}
    >
      {/* ── Header ────────────────────────────────────────────────────────── */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className={`text-lg font-bold ${isWinner ? "text-accent" : "text-textPrimary"}`}>
            {title}
          </h3>
          <p className="text-xs text-textSecondary mt-1 max-w-[250px]">{desc}</p>
        </div>
        {isWinner && (
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-accent/10 border border-accent/20 text-accent text-xs font-bold uppercase tracking-wider">
            <Trophy size={14} /> Recommended
          </div>
        )}
      </div>

      {/* ── Fairness Deltas ───────────────────────────────────────────────── */}
      <div className="mb-6">
        <h4 className="text-xs font-semibold text-textSecondary uppercase tracking-widest mb-2 border-b border-white/[0.06] pb-2">
          Fairness Impact
        </h4>
        <div className="flex text-xs text-textSecondary mb-1 font-medium">
          <span className="w-16">Metric</span>
          <span className="w-16 text-right">Before</span>
          <span className="w-16 text-right">After</span>
          <span className="w-20 text-right">Change</span>
        </div>
        <div className="bg-surface/30 rounded-lg p-2">
          {["SPD", "DI", "EOD", "AOD"].map(m => (
            <DeltaRow 
              key={m} 
              label={m} 
              before={getVal(before, m)} 
              after={getVal(after, m)} 
            />
          ))}
        </div>
      </div>

      {/* ── Performance Effects ───────────────────────────────────────────── */}
      <div>
        <h4 className="text-xs font-semibold text-textSecondary uppercase tracking-widest mb-3 border-b border-white/[0.06] pb-2">
          Performance Trade-off
        </h4>
        <div className="grid grid-cols-4 gap-2">
          <MetricCompact label="Acc" before={getVal(before, 'accuracy')} after={getVal(after, 'accuracy')} />
          <MetricCompact label="Pre" before={getVal(before, 'precision')} after={getVal(after, 'precision')} />
          <MetricCompact label="Rec" before={getVal(before, 'recall')} after={getVal(after, 'recall')} />
          <MetricCompact label="F1"  before={getVal(before, 'f1')} after={getVal(after, 'f1')} />
        </div>
      </div>

      {/* ── Non-winner reason ─────────────────────────────────────────────── */}
      {!isWinner && (
        <div className="mt-5 flex items-start gap-2 text-xs text-textSecondary bg-surface/50 p-3 rounded-lg">
          <Info size={14} className="flex-shrink-0 mt-0.5 opacity-70" />
          <p>
            Not recommended because {
              (effects.bias_reduction_pct || 0) < 30 
                ? "it achieved insufficient bias reduction."
                : "it resulted in a more severe accuracy drop compared to the alternative."
            }
          </p>
        </div>
      )}
    </motion.div>
  );
}
