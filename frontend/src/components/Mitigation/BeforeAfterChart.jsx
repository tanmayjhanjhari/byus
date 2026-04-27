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

const getVal = (obj, key) => obj?.[key] ?? obj?.[key.toUpperCase()] ?? obj?.[key.toLowerCase()] ?? 0;

export default function BeforeAfterChart({ mitigation }) {
  if (!mitigation) return null;

  const rewBefore = mitigation.reweigh?.before || {};
  const rewAfter  = mitigation.reweigh?.after || {};
  const thrAfter  = mitigation.threshold?.after || {};

  const metrics = ["SPD", "DI", "EOD", "AOD"];
  
  const data = metrics.map(m => ({
    name: m,
    Before: Math.abs(getVal(rewBefore, m)),
    "Reweighing": Math.abs(getVal(rewAfter, m)),
    "Threshold": Math.abs(getVal(thrAfter, m)),
  }));

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-surface/90 border border-white/10 rounded-lg p-3 shadow-xl backdrop-blur-md">
          <p className="font-semibold text-textPrimary mb-2 border-b border-white/10 pb-1">{label} (Absolute Value)</p>
          {payload.map((entry, index) => (
            <div key={index} className="flex items-center gap-2 text-sm mb-1">
              <span className="w-3 h-3 rounded-sm" style={{ backgroundColor: entry.color }} />
              <span className="text-textSecondary w-20">{entry.name}:</span>
              <span className="font-medium text-textPrimary">{entry.value.toFixed(3)}</span>
            </div>
          ))}
          <p className="text-[10px] text-textSecondary mt-2 pt-1 border-t border-white/10 opacity-70">
            Note: Values are absolute (closer to 0 is better).
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="h-80 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          margin={{ top: 20, right: 10, left: -20, bottom: 5 }}
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
            tickLine={false}
            axisLine={false}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.05)' }} />
          <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }} />
          
          <Bar dataKey="Before" fill="#64748B" radius={[2, 2, 0, 0]} isAnimationActive={true} />
          <Bar dataKey="Reweighing" fill="#14B8A6" radius={[2, 2, 0, 0]} isAnimationActive={true} />
          <Bar dataKey="Threshold" fill="#818CF8" radius={[2, 2, 0, 0]} isAnimationActive={true} />
        </BarChart>
      </ResponsiveContainer>
      
      {mitigation.reweigh?.explanation?.graph_explanation && (
        <div className="mt-6 flex items-start gap-2 bg-surface/50 rounded-lg p-3 border border-white/[0.04]">
          <Info size={16} className="text-textSecondary flex-shrink-0 mt-0.5" />
          <p className="text-xs text-textSecondary leading-relaxed">
            {mitigation.reweigh.explanation.graph_explanation}
          </p>
        </div>
      )}
    </div>
  );
}
