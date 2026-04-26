import { motion } from "framer-motion";
import { Sparkles, BarChart2 } from "lucide-react";
import useAnalysisStore from "../../store/analysisStore";

export default function ExplainerPanel({ attrName }) {
  const store = useAnalysisStore();
  const explanation = store.explanation?.[attrName];
  const geminiExplanation = store.geminiExplanations?.[attrName];

  if (!explanation) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-textSecondary">
         <p>No explanation data available for {attrName}.</p>
      </div>
    );
  }

  const { correlation, proxy_features, data_imbalance, plain_reason } = explanation;

  // Correlation Progress Bar
  const corrPct = Math.min(Math.abs(correlation || 0) * 100, 100);
  
  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      
      {/* ── Correlation & Imbalance ────────────────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="glass-card p-5 border border-white/[0.06]">
           <h4 className="text-sm font-semibold text-textSecondary uppercase tracking-wider mb-4">Correlation with Outcome</h4>
           <div className="flex items-center justify-between mb-2">
             <span className="text-2xl font-bold text-textPrimary">{(correlation || 0).toFixed(2)}</span>
             <span className="text-xs text-textSecondary">{corrPct.toFixed(0)}%</span>
           </div>
           <div className="w-full bg-surface rounded-full h-2.5 overflow-hidden">
             <motion.div 
               className="bg-accent h-2.5 rounded-full" 
               initial={{ width: 0 }}
               animate={{ width: `${corrPct}%` }}
               transition={{ duration: 1, ease: "easeOut" }}
             />
           </div>
        </div>

        <div className="glass-card p-5 border border-white/[0.06]">
           <h4 className="text-sm font-semibold text-textSecondary uppercase tracking-wider mb-4">Data Imbalance</h4>
           {data_imbalance ? (
             <div className="space-y-3">
               <div className="flex justify-between text-sm">
                 <span className="text-textSecondary">Ratio (Smallest / Largest)</span>
                 <span className={`font-semibold ${data_imbalance.flagged ? 'text-warning' : 'text-success'}`}>
                   {(data_imbalance.ratio * 100).toFixed(0)}%
                 </span>
               </div>
               <div className="flex gap-2 h-4 rounded-full overflow-hidden">
                 <motion.div 
                   className="bg-accent2" 
                   initial={{ flex: 0 }}
                   animate={{ flex: data_imbalance.smallest_group_count }}
                   transition={{ duration: 1, ease: "easeOut" }}
                 />
                 <motion.div 
                   className="bg-surface" 
                   initial={{ flex: 100 }}
                   animate={{ flex: data_imbalance.largest_group_count }}
                   transition={{ duration: 1, ease: "easeOut" }}
                 />
               </div>
               <p className="text-xs text-textSecondary pt-1">{data_imbalance.interpretation}</p>
             </div>
           ) : (
             <p className="text-sm text-textSecondary">Imbalance data unavailable.</p>
           )}
        </div>
      </div>

      {/* ── Proxy Features ─────────────────────────────────────────────────── */}
      {proxy_features && proxy_features.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-textSecondary uppercase tracking-wider mb-3">Detected Proxy Features</h4>
          <div className="flex flex-wrap gap-3">
            {proxy_features.map((pf, i) => {
              // Color intensity based on strength
              let colorCls = "bg-surface text-textSecondary border-white/10";
              if (pf.strength === "strong") colorCls = "bg-danger/20 text-danger border-danger/30";
              else if (pf.strength === "moderate") colorCls = "bg-warning/20 text-warning border-warning/30";
              else if (pf.strength === "weak") colorCls = "bg-accent/10 text-accent border-accent/20";
              
              return (
                <div key={i} className={`flex items-center gap-2 px-3 py-1.5 rounded-full border text-sm font-medium ${colorCls}`}>
                  <BarChart2 size={14} />
                  {pf.feature}
                  <span className="opacity-70 font-normal ml-1">r={(pf.correlation || 0).toFixed(2)}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ── Plain Reason Callout ───────────────────────────────────────────── */}
      {plain_reason && (
        <div className="pl-4 py-2 border-l-4 border-accent">
          <p className="text-lg font-medium text-textPrimary leading-relaxed">
            {plain_reason}
          </p>
        </div>
      )}

      {/* ── Gemini AI Explanation ──────────────────────────────────────────── */}
      <div className="glass-card p-6 border border-accent2/30 relative overflow-hidden mt-6">
        <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-accent to-accent2" />
        
        <div className="flex items-center justify-between mb-4">
           <h4 className="text-lg font-bold text-textPrimary flex items-center gap-2">
             <BrainIcon /> Bias Narrative
           </h4>
           <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-accent/10 text-accent text-xs font-semibold border border-accent/20">
             <Sparkles size={12} /> AI Insight
           </span>
        </div>

        {geminiExplanation ? (
          <div className="space-y-4 text-base text-textPrimary leading-relaxed">
            {geminiExplanation.split('\n\n').map((para, i) => (
              <p key={i}>{para}</p>
            ))}
          </div>
        ) : (
          <div className="space-y-3 animate-pulse">
            <div className="h-4 bg-surface rounded w-full"></div>
            <div className="h-4 bg-surface rounded w-5/6"></div>
            <div className="h-4 bg-surface rounded w-4/6"></div>
          </div>
        )}
      </div>
      
    </div>
  );
}

function BrainIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-accent2">
      <path d="M12 5a3 3 0 1 0-5.997.125 4 4 0 0 0-2.526 5.77 4 4 0 0 0 .556 6.588A4 4 0 1 0 12 18Z"/>
      <path d="M12 5a3 3 0 1 1 5.997.125 4 4 0 0 1 2.526 5.77 4 4 0 0 1-.556 6.588A4 4 0 1 1 12 18Z"/>
      <path d="M15 13a4.5 4.5 0 0 1-3-4 4.5 4.5 0 0 1-3 4 4.5 4.5 0 0 1 3 4 4.5 4.5 0 0 1 3-4Z"/>
      <path d="M17.599 6.5a3 3 0 0 0 .399-1.375"/>
      <path d="M6.003 5.125A3 3 0 0 0 6.401 6.5"/>
      <path d="M3.477 10.896a4 4 0 0 1 .585-.396"/>
      <path d="M19.938 10.5a4 4 0 0 1 .585.396"/>
      <path d="M6 18a4 4 0 0 1-1.967-.516"/>
      <path d="M19.967 17.484A4 4 0 0 1 18 18"/>
    </svg>
  );
}
