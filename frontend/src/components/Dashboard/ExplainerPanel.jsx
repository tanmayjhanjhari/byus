import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Sparkles, ChevronDown, AlertTriangle, Info, AlertCircle, CheckCircle } from "lucide-react";
import useAnalysisStore from "../../store/analysisStore";

// BrainIcon helper
function BrainIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-accent2">
      <path d="M12 5a3 3 0 1 0-5.997.125 4 4 0 0 0-2.526 5.77 4 4 0 0 0 .556 6.588A4 4 0 1 0 12 18Z"/>
      <path d="M12 5a3 3 0 1 1 5.997.125 4 4 0 0 1 2.526 5.77 4 4 0 0 1-.556 6.588A4 4 0 1 1 12 18Z"/>
      <path d="M15 13a4.5 4.5 0 0 1-3-4 4.5 4.5 0 0 1-3 4 4.5 4.5 0 0 1 3-4Z"/>
      <path d="M17.599 6.5a3 3 0 0 0 .399-1.375"/>
      <path d="M6.003 5.125A3 3 0 0 0 6.401 6.5"/>
      <path d="M3.477 10.896a4 4 0 0 1 .585-.396"/>
      <path d="M19.938 10.5a4 4 0 0 1 .585.396"/>
      <path d="M6 18a4 4 0 0 1-1.967-.516"/>
      <path d="M19.967 17.484A4 4 0 0 1 18 18"/>
    </svg>
  );
}

function CollapsibleSection({ title, defaultOpen = false, icon: Icon, children, gradientBorder = false }) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className={`glass-card border border-white/[0.06] rounded-xl overflow-hidden ${gradientBorder ? "relative" : ""}`}>
      {gradientBorder && (
        <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-accent to-accent2" />
      )}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-4 hover:bg-white/[0.02] transition-colors text-left"
      >
        <div className="flex items-center gap-3">
          {Icon && <Icon className="text-accent" size={18} />}
          <h4 className="text-sm font-semibold text-textPrimary uppercase tracking-wider">{title}</h4>
        </div>
        <motion.div animate={{ rotate: isOpen ? 180 : 0 }} transition={{ duration: 0.2 }}>
          <ChevronDown size={18} className="text-textSecondary" />
        </motion.div>
      </button>
      <AnimatePresence initial={false}>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: "easeInOut" }}
          >
            <div className="px-4 pb-4 pt-1 text-sm text-textSecondary leading-relaxed prose max-w-none">
              {children}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

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

  const {
    spd_explanation,
    ceiling_effect,
    ceiling_explanation,
    proxy_explanation,
    proxy_features,
    imbalance_explanation,
    plain_reason,
    di_explanation,
    di_val
  } = explanation;

  const isDiFail = explanation.di_explanation?.includes("FAILS") || explanation.di_explanation?.includes("severely below");

  return (
    <div className="space-y-4 animate-in fade-in duration-500">
      {/* SECTION 1 */}
      <CollapsibleSection title="What does this SPD mean?" defaultOpen={true} icon={Info}>
        <p className="text-textPrimary">{spd_explanation}</p>
        
        {ceiling_effect && (
          <div className="mt-4 p-3 bg-warning/10 border-l-2 border-warning rounded-r-lg">
            <div className="flex items-center gap-2 text-warning mb-1">
              <AlertTriangle size={16} />
              <span className="font-semibold text-xs uppercase tracking-wider">Ceiling Effect Detected</span>
            </div>
            <p className="text-warning-light">{ceiling_explanation}</p>
          </div>
        )}
      </CollapsibleSection>

      {/* SECTION 2 */}
      <CollapsibleSection title="Why does this bias exist?" defaultOpen={true} icon={Sparkles}>
        {proxy_explanation && (
          <div className="mb-4 p-4 bg-accent/10 border border-accent/20 rounded-lg">
            <div className="flex items-center gap-2 text-accent mb-2">
              <AlertCircle size={16} />
              <span className="font-semibold text-xs uppercase tracking-wider">Proxy Discrimination Detected</span>
            </div>
            <p className="text-textPrimary mb-3">{proxy_explanation}</p>
            
            {proxy_features && proxy_features.length > 0 && (
              <div className="flex flex-wrap gap-2 mt-2">
                {proxy_features.map((pf, i) => {
                  let colorCls = "bg-surface text-textSecondary border-white/10";
                  if (pf.correlation > 0.4) colorCls = "bg-danger/20 text-danger border-danger/30";
                  else if (pf.correlation > 0.2) colorCls = "bg-warning/20 text-warning border-warning/30";
                  
                  return (
                    <div key={i} className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-xs font-medium ${colorCls}`}>
                      {pf.feature}
                      <span className="opacity-70 font-normal">r={pf.correlation.toFixed(2)}</span>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        <p className="text-textPrimary mb-4">{imbalance_explanation}</p>
        
        {plain_reason && (
          <div className="pl-4 py-2 border-l-2 border-white/20 italic text-textSecondary">
            {plain_reason}
          </div>
        )}
      </CollapsibleSection>

      {/* SECTION 3 */}
      <CollapsibleSection title="Legal & Regulatory Context" defaultOpen={false} icon={AlertTriangle}>
        <p className="text-textPrimary mb-4">{di_explanation}</p>
        
        {isDiFail ? (
          <div className="flex items-start gap-3 p-3 bg-danger/10 border border-danger/20 rounded-lg">
            <div className="mt-0.5">
              <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-danger text-white">
                Fails Legal 80% Rule
              </span>
            </div>
            <p className="text-xs text-danger-light leading-relaxed">
              Under the EEOC Uniform Guidelines, a selection rate below 80% of the highest group rate is considered evidence of adverse impact. This finding should be reviewed by your legal or compliance team.
            </p>
          </div>
        ) : (
          <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-success/10 text-success border border-success/20">
            <CheckCircle size={14} />
            <span className="text-xs font-semibold uppercase tracking-wider">Passes Legal Threshold</span>
          </div>
        )}
      </CollapsibleSection>

      {/* SECTION 4 */}
      <CollapsibleSection title="AI Insight" defaultOpen={false} icon={BrainIcon} gradientBorder={true}>
        {geminiExplanation ? (
          <div className="space-y-3 text-textPrimary">
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
      </CollapsibleSection>
    </div>
  );
}
