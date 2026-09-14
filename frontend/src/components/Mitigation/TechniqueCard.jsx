import { motion } from "framer-motion";
import { ArrowDown, ArrowUp, Info, Trophy, Settings, BarChart2, Zap } from "lucide-react";

const getVal = (obj, key) => obj?.[key] ?? obj?.[key.toUpperCase()] ?? obj?.[key.toLowerCase()];

// null/undefined means genuinely unavailable � NOT the same as 0.000
function DeltaRow({ label, before, after }) {
  const isUnavailable = before === null || before === undefined || after === null || after === undefined;

  if (isUnavailable) {
    return (
      <tr className="border-b border-white/[0.04] last:border-0">
        <td className="truncate px-2 py-1.5 min-w-0 font-medium text-textSecondary">{label}</td>
        <td className="truncate px-2 py-1.5 min-w-0 text-textSecondary/40 text-right text-xs italic">N/A</td>
        <td className="truncate px-2 py-1.5 min-w-0 text-textSecondary/40 text-right text-xs italic">N/A</td>
        <td className="truncate px-2 py-1.5 min-w-0 text-textSecondary/40 text-right text-xs">—</td>
      </tr>
    );
  }

  const b = Number(before);
  const a = Number(after);
  const delta = a - b;
  const absDelta = Math.abs(delta);
  let isImprovement = false;
  if (label.toUpperCase() === "DI") {
    isImprovement = Math.abs(1 - a) < Math.abs(1 - b);
  } else {
    isImprovement = Math.abs(a) < Math.abs(b);
  }

  return (
    <tr className="border-b border-white/[0.04] last:border-0">
      <td className="truncate px-2 py-1.5 min-w-0 font-medium text-textSecondary">{label}</td>
      <td className="truncate px-2 py-1.5 min-w-0 text-textPrimary text-right">{b.toFixed(3)}</td>
      <td className="truncate px-2 py-1.5 min-w-0 text-textPrimary text-right">{a.toFixed(3)}</td>
      <td className={`truncate px-2 py-1.5 min-w-0 font-medium text-right ${isImprovement ? "text-success" : "text-danger"}`}>
        <div className="flex items-center justify-end gap-1">
          {isImprovement ? <ArrowDown size={14} className="flex-shrink-0" /> : <ArrowUp size={14} className="flex-shrink-0" />}
          <span className="truncate">{absDelta.toFixed(3)}</span>
        </div>
      </td>
    </tr>
  );
}

function MetricCompact({ label, before, after }) {
  const isUnavailable = before === null || before === undefined || after === null || after === undefined;

  if (isUnavailable) {
    return (
      <div>
        <p className="text-[10px] text-textSecondary uppercase tracking-wider mb-1">{label}</p>
        <div className="flex items-baseline gap-1">
          <span className="text-sm text-textSecondary/40 italic">N/A</span>
        </div>
      </div>
    );
  }

  const b = Number(before);
  const a = Number(after);
  const delta = a - b;
  const isDrop = delta < 0;

  return (
    <div>
       <p className="text-[10px] text-textSecondary uppercase tracking-wider mb-1">{label}</p>
       <div className="flex items-baseline gap-1.5">
          <span className="text-sm font-semibold text-textPrimary">{a.toFixed(3)}</span>
          <span className={`text-[10px] font-medium ${isDrop ? "text-danger" : "text-success"}`}>
             {delta > 0 ? "+" : ""}{delta.toFixed(3)}
          </span>
       </div>
    </div>
  );
}

export default function TechniqueCard({ name, data, isWinner, winnerReason }) {
  if (!data || !data.before || !data.after) return null;

  const title = name === "reweigh" ? "Reweighing" : "Threshold Adjustment";
  const desc = name === "reweigh"
    ? "Adjusts training data weights to ensure demographic balance."
    : "Finds per-group decision thresholds to equalise outcome rates.";

  const before = data.before;
  const after = data.after;
  const effects = data.effects || {};
  const isSimulation = data.is_simulation === true;
  const simulationNote = data.simulation_note;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={`relative glass-card p-6 border ${
        isWinner ? "border-accent/50 shadow-[0_0_15px_rgba(20,184,166,0.15)]" : "border-white/[0.06]"
      } transition-all duration-300`}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <div className="flex items-center gap-2">
            <h3 className={`text-lg font-bold ${isWinner ? "text-accent" : "text-textPrimary"}`}>
              {title}
            </h3>
            {isSimulation && (
              <span className="px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider bg-amber-500/15 border border-amber-500/25 text-amber-400 rounded">
                Simulation
              </span>
            )}
          </div>
          <p className="text-xs text-textSecondary mt-1 max-w-[250px]">{desc}</p>
        </div>
      </div>

      {isWinner && winnerReason && (
        <div className="mb-6 bg-accent/10 border border-accent/20 rounded-lg p-4 text-accent shadow-sm">
          <div className="flex items-center gap-2 mb-1.5">
            <Trophy size={16} className="flex-shrink-0" />
            <span className="font-bold text-sm">Why this is recommended:</span>
          </div>
          <p className="text-sm leading-relaxed opacity-90">{winnerReason}</p>
        </div>
      )}

      {/* Simulation disclosure */}
      {isSimulation && simulationNote && (
        <div className="mb-4 flex items-start gap-2 bg-amber-500/6 border border-amber-500/20 rounded-lg px-3 py-2">
          <Info size={13} className="text-amber-400/70 flex-shrink-0 mt-0.5" />
          <p className="text-xs text-amber-300/70 leading-relaxed">{simulationNote}</p>
        </div>
      )}
      {!isSimulation && simulationNote && (
        <div className="mb-4 flex items-start gap-2 bg-blue-500/6 border border-blue-500/20 rounded-lg px-3 py-2">
          <Info size={13} className="text-blue-400/60 flex-shrink-0 mt-0.5" />
          <p className="text-xs text-blue-300/60 leading-relaxed">{simulationNote}</p>
        </div>
      )}

      {/* Real Model Failure / Unavailable error state */}
      {(data.error || after?.error) && (
        <div className="mb-4 flex items-start gap-2 bg-red-500/10 border border-red-500/25 rounded-lg px-3 py-2 text-red-400">
          <Info size={14} className="flex-shrink-0 mt-0.5 text-red-400" />
          <div>
            <p className="text-xs font-semibold">Real model evaluation unavailable</p>
            <p className="text-xs text-red-300/80 leading-relaxed mt-0.5">{data.error || after?.error}</p>
          </div>
        </div>
      )}

      {/* Fairness Deltas */}
      <div className="mb-6">
        <h4 className="text-xs font-semibold text-textSecondary uppercase tracking-widest mb-2 border-b border-white/[0.06] pb-2">
          Fairness Impact
        </h4>
        <div className="bg-surface/30 rounded-lg p-2">
          <table className="w-full table-fixed text-xs">
            <thead>
              <tr className="text-textSecondary font-medium border-b border-white/[0.06]">
                <th className="truncate px-2 py-1.5 min-w-0 text-left" style={{ width: "25%" }}>Metric</th>
                <th className="truncate px-2 py-1.5 min-w-0 text-right" style={{ width: "22%" }}>Before</th>
                <th className="truncate px-2 py-1.5 min-w-0 text-right" style={{ width: "22%" }}>After</th>
                <th className="truncate px-2 py-1.5 min-w-0 text-right" style={{ width: "31%" }}>Change</th>
              </tr>
            </thead>
            <tbody>
              {["SPD", "DI", "EOD", "AOD"].map(m => (
                <DeltaRow
                  key={m}
                  label={m}
                  before={getVal(before, m)}
                  after={getVal(after, m)}
                />
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Performance Effects */}
      <div>
        <h4 className="text-xs font-semibold text-textSecondary uppercase tracking-widest mb-2 border-b border-white/[0.06] pb-2">
          Performance Trade-off
        </h4>
                {isSimulation ? (
          <div className="flex items-start gap-1.5 mb-3 bg-amber-500/5 border border-amber-500/12 rounded px-2 py-1.5">
            <Info size={11} className="text-amber-400/60 flex-shrink-0 mt-0.5" />
            <p className="text-[10px] text-amber-300/60 leading-relaxed">Simulation model only — not real deployed model performance</p>
          </div>
        ) : (
          <div className="flex items-start gap-1.5 mb-3 bg-emerald-500/5 border border-emerald-500/15 rounded px-2 py-1.5">
            <Zap size={11} className="text-emerald-400/70 flex-shrink-0 mt-0.5" />
            <p className="text-[10px] text-emerald-300/70 leading-relaxed">Real model performance evaluated directly on uploaded model</p>
          </div>
        )}
        <div className="grid grid-cols-4 gap-2">
          <MetricCompact label="Acc" before={getVal(before, "accuracy")} after={getVal(after, "accuracy")} />
          <MetricCompact label="Pre" before={getVal(before, "precision")} after={getVal(after, "precision")} />
          <MetricCompact label="Rec" before={getVal(before, "recall")} after={getVal(after, "recall")} />
          <MetricCompact label="F1"  before={getVal(before, "f1")} after={getVal(after, "f1")} />
        </div>
      </div>

      {/* Non-winner diagnostic */}
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

      {/* Diagnostic box when bias reduction is very low */}
      {effects.diagnostic && (
        <div className="mt-4 flex items-start gap-2 text-xs bg-amber-500/10 border border-amber-500/25 p-3 rounded-lg">
          <Info size={14} className="flex-shrink-0 mt-0.5 text-amber-400" />
          <p className="text-amber-300/90 leading-relaxed">{effects.diagnostic}</p>
        </div>
      )}

      {/* Understanding this result */}
      {data.explanation && (
        <div className="mt-6 border-t border-white/[0.06] pt-4">
          <h4 className="text-xs font-semibold text-textSecondary uppercase tracking-widest mb-3">
            Understanding this result
          </h4>
          <div className="space-y-4">
            <div className="flex gap-3 items-start">
              <Settings size={16} className="text-textSecondary mt-0.5" />
              <p className="text-xs text-textSecondary leading-relaxed">
                {data.explanation.how_it_works}
              </p>
            </div>

            <div className="flex gap-3 items-start">
              <BarChart2 size={16} className={`${
                (effects.bias_reduction_pct || 0) > 50 ? "text-success" :
                (effects.bias_reduction_pct || 0) >= 10 ? "text-warning" : "text-danger"
              } mt-0.5`} />
              <p className={`text-xs leading-relaxed ${
                (effects.bias_reduction_pct || 0) > 50 ? "text-success-light" :
                (effects.bias_reduction_pct || 0) >= 10 ? "text-warning-light" : "text-danger-light"
              }`}>
                {data.explanation.bias_result}
              </p>
            </div>

            <div className="flex gap-3 items-start">
              <Zap size={16} className={`${
                (effects.accuracy_retained_pct || 0) > 98 ? "text-success" :
                (effects.accuracy_retained_pct || 0) >= 90 ? "text-warning" : "text-danger"
              } mt-0.5`} />
              <p className={`text-xs leading-relaxed ${
                (effects.accuracy_retained_pct || 0) > 98 ? "text-success-light" :
                (effects.accuracy_retained_pct || 0) >= 90 ? "text-warning-light" : "text-danger-light"
              }`}>
                {data.explanation.acc_result}
              </p>
            </div>
          </div>
        </div>
      )}
    </motion.div>
  );
}
