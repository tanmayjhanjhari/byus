import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import { Info } from "lucide-react";

// Note: does NOT default to 0 � null means genuinely unavailable
const getVal = (obj, key) => {
  const v = obj?.[key] ?? obj?.[key.toUpperCase()] ?? obj?.[key.toLowerCase()];
  return v !== undefined ? v : null;
};

export default function BeforeAfterChart({ mitigation }) {
  if (!mitigation) return null;

  const rewBefore = mitigation.reweigh?.before || {};
  const rewAfter  = mitigation.reweigh?.after  || {};
  const thrAfter  = mitigation.threshold?.after || {};

  const allMetrics = ["SPD", "DI", "EOD", "AOD"];

  // Only include a metric in the chart if at least one source has a non-null value.
  // This prevents null EOD/AOD from being shown as 0.000.
  const activeMetrics = allMetrics.filter(m => {
    const vBefore   = getVal(rewBefore, m);
    const vRewAfter = getVal(rewAfter,  m);
    const vThrAfter = getVal(thrAfter,  m);
    return vBefore !== null || vRewAfter !== null || vThrAfter !== null;
  });

  const omittedMetrics = allMetrics.filter(m => !activeMetrics.includes(m));

  const data = activeMetrics.map(m => {
    const vBefore   = getVal(rewBefore, m);
    const vRewAfter = getVal(rewAfter,  m);
    const vThrAfter = getVal(thrAfter,  m);
    return {
      name: m,
      // Only include non-null values � recharts will skip undefined bars
      Before:       vBefore   !== null ? Math.abs(vBefore)   : undefined,
      "Reweighing": vRewAfter !== null ? Math.abs(vRewAfter) : undefined,
      "Threshold":  vThrAfter !== null ? Math.abs(vThrAfter) : undefined,
      thrIsSimulation: mitigation.threshold?.is_simulation === true,
    };
  });

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-surface/90 border border-white/10 rounded-lg p-3 shadow-xl backdrop-blur-md">
          <p className="font-semibold text-textPrimary mb-2 border-b border-white/10 pb-1">{label} (Absolute Value)</p>
          {payload.map((entry, i) => (
            <div key={i} className="flex items-center gap-2 text-sm mb-1">
              <span className="w-3 h-3 rounded-sm" style={{ backgroundColor: entry.color }} />
              <span className="text-textSecondary w-20">{entry.name}:</span>
              <span className="font-medium text-textPrimary">
                {entry.value !== undefined ? entry.value.toFixed(3) : "N/A"}
                {entry.name === "Threshold" && data[0]?.thrIsSimulation ? " *" : ""}
              </span>
            </div>
          ))}
          {data[0]?.thrIsSimulation && (
            <p className="text-[10px] text-amber-300/70 mt-2 pt-1 border-t border-white/10">
              * Threshold values are from an internal simulation model
            </p>
          )}
          <p className="text-[10px] text-textSecondary mt-1 opacity-70">
            Absolute values shown (closer to 0 = fairer)
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <div>
      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.1)" vertical={false} />
            <XAxis
              dataKey="name"
              tick={{ fill: "#94A3B8", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tick={{ fill: "#94A3B8", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              domain={[0, "auto"]}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend wrapperStyle={{ fontSize: "12px" }} />
            <Bar dataKey="Before"       fill="#64748B" radius={[4, 4, 0, 0]} maxBarSize={32} />
            <Bar dataKey="Reweighing"   fill="#14B8A6" radius={[4, 4, 0, 0]} maxBarSize={32} />
            <Bar dataKey="Threshold"    fill="#A855F7" radius={[4, 4, 0, 0]} maxBarSize={32} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {omittedMetrics.length > 0 && (
        <div className="mt-3 flex items-start gap-2 bg-surface/40 rounded-lg px-3 py-2 border border-white/[0.04]">
          <Info size={13} className="text-textSecondary/50 flex-shrink-0 mt-0.5" />
          <p className="text-xs text-textSecondary/50">
            {omittedMetrics.join(", ")} omitted from chart � require model predictions which are not available in dataset-only analysis.
          </p>
        </div>
      )}

      {mitigation.threshold?.is_simulation && (
        <div className="mt-2 flex items-start gap-2 bg-amber-500/6 border border-amber-500/15 rounded-lg px-3 py-2">
          <Info size={13} className="text-amber-400/70 flex-shrink-0 mt-0.5" />
          <p className="text-xs text-amber-300/60 leading-relaxed">
            <span className="font-semibold">Threshold values are from a simulation model.</span>{" "}
            Threshold adjustment requires real model predictions � these values illustrate the technique only.
            Reweighing before/after values are from actual dataset outcome distributions.
          </p>
        </div>
      )}

      {mitigation.reweigh?.explanation?.graph_explanation && (
        <div className="mt-3 flex items-start gap-2 bg-surface/50 rounded-lg p-3 border border-white/[0.04]">
          <Info size={16} className="text-textSecondary flex-shrink-0 mt-0.5" />
          <p className="text-xs text-textSecondary leading-relaxed">
            {mitigation.reweigh.explanation.graph_explanation}
          </p>
        </div>
      )}
    </div>
  );
}
