import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";

export default function GroupBarChart({ groupStats }) {
  if (!groupStats) return null;

  // Format data for Recharts
  const data = Object.entries(groupStats).map(([group, stats]) => ({
    name: group,
    rate: stats.positive_rate || 0,
    count: stats.count || 0,
  }));

  if (data.length === 0) return null;

  // Calculate overall average
  const totalCount = data.reduce((sum, d) => sum + d.count, 0);
  const totalPositives = data.reduce((sum, d) => sum + (d.rate * d.count), 0);
  const averageRate = totalCount > 0 ? totalPositives / totalCount : 0;

  // Find max deviation for red coloring
  let maxDevIdx = -1;
  let maxDev = -1;
  data.forEach((d, i) => {
    const dev = Math.abs(d.rate - averageRate);
    if (dev > maxDev) {
      maxDev = dev;
      maxDevIdx = i;
    }
  });

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      const p = payload[0].payload;
      const dev = p.rate - averageRate;
      const sign = dev > 0 ? "+" : "";
      return (
        <div className="bg-surface/90 border border-white/10 rounded-lg p-3 shadow-xl backdrop-blur-md">
          <p className="font-semibold text-textPrimary mb-1">{label}</p>
          <p className="text-sm text-textSecondary">
            Pos. Rate: <span className="font-medium text-textPrimary">{(p.rate * 100).toFixed(1)}%</span>
          </p>
          <p className="text-sm text-textSecondary">
            Deviation: <span className="font-medium text-textPrimary">{sign}{(dev * 100).toFixed(1)}%</span>
          </p>
          <p className="text-xs text-textSecondary mt-1 opacity-70">
            N = {p.count}
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="h-72 w-full mt-4">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          margin={{ top: 20, right: 30, left: 0, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.1)" vertical={false} />
          <XAxis 
            dataKey="name" 
            stroke="#94A3B8" 
            fontSize={12} 
            tickLine={false}
            axisLine={{ stroke: 'rgba(148,163,184,0.2)' }}
          />
          <YAxis 
            stroke="#94A3B8" 
            fontSize={12}
            tickFormatter={(val) => `${(val * 100).toFixed(0)}%`}
            tickLine={false}
            axisLine={false}
            domain={[0, 1]}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.05)' }} />
          
          <ReferenceLine 
            y={averageRate} 
            stroke="#94A3B8" 
            strokeDasharray="4 4"
            label={{ position: 'right', value: 'Avg', fill: '#94A3B8', fontSize: 12 }} 
          />
          
          <Bar dataKey="rate" radius={[4, 4, 0, 0]} isAnimationActive={true} animationDuration={1000}>
            {data.map((entry, index) => (
              <Cell 
                key={`cell-${index}`} 
                fill={index === maxDevIdx ? "#EF4444" : "#14B8A6"} 
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
