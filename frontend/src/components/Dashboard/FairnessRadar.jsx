import {
  Legend,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip
} from "recharts";
import { Info } from "lucide-react";

export default function FairnessRadar({ metrics }) {
  if (!metrics) return null;

  const getVal = (key) => metrics[key] ?? metrics[key.toUpperCase()] ?? metrics[key.toLowerCase()];

  const spd = getVal("spd");
  const di = getVal("di");
  const eod = getVal("eod");
  const aod = getVal("aod");
  const eodAvailable = getVal("eod_available") ?? (eod !== null && eod !== undefined);
  const aodAvailable = getVal("aod_available") ?? (aod !== null && aod !== undefined);

  // Normalize metrics to 0-1 range where 1 = "fair"
  const normSpd = spd != null ? Math.max(0, 1 - Math.abs(spd)) : null;
  const normDi = di != null ? (di > 1 ? 1 / di : di) : null;
  // Only include EOD/AOD if actually available
  const normEod = (eodAvailable && eod != null) ? Math.max(0, 1 - Math.abs(eod)) : null;
  const normAod = (aodAvailable && aod != null) ? Math.max(0, 1 - Math.abs(aod)) : null;

  const modelMetricsOmitted = !eodAvailable || !aodAvailable;

  // Build data array only with available metrics
  const data = [
    spd != null && { subject: "Stat Parity (SPD)", current: normSpd, ideal: 1, raw: (spd || 0).toFixed(3), available: true },
    di != null && { subject: "Disp Impact (DI)", current: normDi, ideal: 1, raw: (di || 0).toFixed(3), available: true },
    (eodAvailable && eod != null) && { subject: "Eq Opp (EOD)", current: normEod, ideal: 1, raw: (eod || 0).toFixed(3), available: true },
    (aodAvailable && aod != null) && { subject: "Avg Odds (AOD)", current: normAod, ideal: 1, raw: (aod || 0).toFixed(3), available: true },
  ].filter(Boolean);

  if (data.length === 0) return null;

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-surface/90 border border-white/10 rounded-lg p-3 shadow-xl backdrop-blur-md">
          <p className="font-semibold text-textPrimary mb-1">{payload[0].payload.subject}</p>
          <p className="text-sm text-textSecondary">
            Raw Value: <span className="font-medium text-textPrimary">{payload[0].payload.raw}</span>
          </p>
          <p className="text-xs text-textSecondary opacity-60 mt-1">
            Fairness score: {((payload[0].payload.current || 0) * 100).toFixed(0)}% (higher = fairer)
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <div>
      <div className="h-72 w-full mt-4 flex items-center justify-center">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart cx="50%" cy="50%" outerRadius="70%" data={data}>
            <PolarGrid stroke="rgba(148,163,184,0.2)" />
            <PolarAngleAxis
              dataKey="subject"
              tick={{ fill: "#94A3B8", fontSize: 11 }}
            />
            <PolarRadiusAxis angle={30} domain={[0, 1]} tick={false} axisLine={false} />

            <Radar
              name="Current Metrics"
              dataKey="current"
              stroke="#14B8A6"
              fill="#14B8A6"
              fillOpacity={0.4}
              isAnimationActive={true}
            />
            <Radar
              name="Fair Threshold"
              dataKey="ideal"
              stroke="#22C55E"
              fill="transparent"
              strokeDasharray="4 4"
              isAnimationActive={false}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend wrapperStyle={{ fontSize: "12px", paddingTop: "10px" }} />
          </RadarChart>
        </ResponsiveContainer>
      </div>

      {modelMetricsOmitted && (
        <div className="mt-3 flex items-start gap-2 bg-surface/50 rounded-lg px-3 py-2 border border-white/[0.04]">
          <Info size={13} className="text-textSecondary/60 flex-shrink-0 mt-0.5" />
          <p className="text-xs text-textSecondary/60">
            EOD and AOD are omitted from this chart - they require model predictions which were not provided.
            Only SPD and DI (dataset-level metrics) are shown.
          </p>
        </div>
      )}
    </div>
  );
}
