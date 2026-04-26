import {
  CartesianGrid,
  ReferenceArea,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";

export default function TradeoffChart({ mitigation }) {
  if (!mitigation) return null;

  const rewEff = mitigation.reweigh?.effects || {};
  const thrEff = mitigation.threshold?.effects || {};

  const data = [
    {
      name: "Reweighing",
      biasRed: Math.max(0, rewEff.bias_reduction_pct || 0),
      accRet: Math.max(0, rewEff.accuracy_retained_pct || 0),
      fill: "#14B8A6"
    },
    {
      name: "Threshold",
      biasRed: Math.max(0, thrEff.bias_reduction_pct || 0),
      accRet: Math.max(0, thrEff.accuracy_retained_pct || 0),
      fill: "#818CF8"
    }
  ];

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const p = payload[0].payload;
      return (
        <div className="bg-surface/90 border border-white/10 rounded-lg p-3 shadow-xl backdrop-blur-md">
          <p className="font-semibold text-textPrimary mb-2 pb-1 border-b border-white/10">{p.name}</p>
          <div className="space-y-1">
             <p className="text-sm text-textSecondary">
               Bias Reduction: <span className="font-medium text-success">{p.biasRed.toFixed(1)}%</span>
             </p>
             <p className="text-sm text-textSecondary">
               Accuracy Retained: <span className="font-medium text-textPrimary">{p.accRet.toFixed(1)}%</span>
             </p>
          </div>
        </div>
      );
    }
    return null;
  };

  // Custom shape to draw labels next to dots
  const renderShape = (props) => {
    const { cx, cy, fill, payload } = props;
    return (
      <g>
        <circle cx={cx} cy={cy} r={8} fill={fill} stroke="rgba(255,255,255,0.2)" strokeWidth={2} />
        <text 
          x={cx + 12} 
          y={cy + 4} 
          fill={fill} 
          fontSize={12} 
          fontWeight="bold"
          className="drop-shadow-md"
        >
          {payload.name}
        </text>
      </g>
    );
  };

  return (
    <div className="w-full">
      <div className="h-80 w-full relative">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 20, right: 30, left: -20, bottom: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.1)" />
            
            {/* X-Axis: Bias Reduction */}
            <XAxis 
              type="number" 
              dataKey="biasRed" 
              name="Bias Reduction" 
              domain={[0, 105]} 
              stroke="#94A3B8"
              fontSize={12}
              tickFormatter={(v) => `${v}%`}
              label={{ value: "Bias Reduction (%) →", position: "bottom", fill: "#94A3B8", fontSize: 12, offset: 0 }}
            />
            
            {/* Y-Axis: Accuracy Retained */}
            <YAxis 
              type="number" 
              dataKey="accRet" 
              name="Accuracy Retained" 
              domain={[80, 105]} 
              stroke="#94A3B8"
              fontSize={12}
              tickFormatter={(v) => `${v}%`}
              label={{ value: "Accuracy Retained (%) ↑", angle: -90, position: "left", fill: "#94A3B8", fontSize: 12, offset: 0 }}
            />
            
            {/* Sweet Spot Overlay */}
            <ReferenceArea 
               x1={60} x2={105} 
               y1={90} y2={105} 
               fill="#22C55E" 
               fillOpacity={0.05} 
               strokeOpacity={0}
            />
            
            {/* Top Right Label for Sweet Spot */}
            <text x="98%" y="5%" textAnchor="end" fill="#22C55E" fontSize={11} opacity={0.6} fontWeight="bold">
               SWEET SPOT
            </text>

            <Tooltip content={<CustomTooltip />} cursor={{ strokeDasharray: '3 3', stroke: 'rgba(255,255,255,0.1)' }} />
            
            <Scatter name="Techniques" data={data} shape={renderShape} isAnimationActive={true} />
          </ScatterChart>
        </ResponsiveContainer>
      </div>
      
      <p className="text-xs text-textSecondary text-center mt-2 px-6">
        Ideal mitigation reduces bias significantly (moving <span className="text-accent font-medium">right</span>) 
        while retaining model accuracy (staying <span className="text-accent font-medium">high</span>).
      </p>
    </div>
  );
}
