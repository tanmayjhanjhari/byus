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

export default function FairnessRadar({ metrics }) {
  if (!metrics) return null;

  // Handle both upper/lower case keys from backend
  const getVal = (key) => metrics[key] ?? metrics[key.toUpperCase()] ?? metrics[key.toLowerCase()];

  // Normalize metrics to 0-1 range for radar chart where 1 is "fair"
  // SPD ideal is 0. Transform: 1 - min(abs(SPD), 1)
  const spd = getVal('spd') || 0;
  const normSpd = Math.max(0, 1 - Math.abs(spd));

  // DI ideal is 1. Transform: if > 1 -> 1/DI. Then bound 0-1.
  const di = getVal('di') || 1;
  const normDi = di > 1 ? 1 / di : di;

  // EOD ideal is 0.
  const eod = getVal('eod') || 0;
  const normEod = Math.max(0, 1 - Math.abs(eod));

  // AOD ideal is 0.
  const aod = getVal('aod') || 0;
  const normAod = Math.max(0, 1 - Math.abs(aod));

  const data = [
    { subject: "Stat Parity (SPD)", current: normSpd, ideal: 1, raw: spd.toFixed(3) },
    { subject: "Disp Impact (DI)", current: normDi, ideal: 1, raw: di.toFixed(3) },
    { subject: "Eq Opp (EOD)", current: normEod, ideal: 1, raw: eod.toFixed(3) },
    { subject: "Avg Odds (AOD)", current: normAod, ideal: 1, raw: aod.toFixed(3) },
  ];

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-surface/90 border border-white/10 rounded-lg p-3 shadow-xl backdrop-blur-md">
          <p className="font-semibold text-textPrimary mb-1">{payload[0].payload.subject}</p>
          <p className="text-sm text-textSecondary">
            Raw Value: <span className="font-medium text-textPrimary">{payload[0].payload.raw}</span>
          </p>
        </div>
      );
    }
    return null;
  };

  return (
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
          <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }} />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
