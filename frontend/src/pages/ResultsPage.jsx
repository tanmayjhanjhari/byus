import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import PageWrapper from "../components/Layout/PageWrapper";
import useAnalysisStore from "../store/analysisStore";
import client from "../api/client";

import AuditScoreGauge from "../components/Dashboard/AuditScoreGauge";
import ValidationBanner from "../components/Dashboard/ValidationBanner";
import MetricCards from "../components/Dashboard/MetricCards";
import GroupBarChart from "../components/Dashboard/GroupBarChart";
import FairnessRadar from "../components/Dashboard/FairnessRadar";
import ExplainerPanel from "../components/Dashboard/ExplainerPanel";
import BiasCopilot from "../components/Copilot/BiasCopilot";

export default function ResultsPage() {
  const navigate = useNavigate();
  const store = useAnalysisStore();
  const { 
    sessionId, metrics, validation, auditScore, grade, sensitiveAttrs, 
    setExplanation, setGeminiExplanation 
  } = store;

  const [activeTab, setActiveTab] = useState("Metrics");
  const [activeAttr, setActiveAttr] = useState(sensitiveAttrs[0] || "");
  const [fetchingExplanations, setFetchingExplanations] = useState(false);

  // Redirect if no session
  useEffect(() => {
    if (!sessionId || !metrics) {
      navigate("/analyze");
    }
  }, [sessionId, metrics, navigate]);

  // Fetch explanations on mount for all sensitive attributes
  useEffect(() => {
    if (!sessionId || !sensitiveAttrs.length) return;

    let cancelled = false;

    const fetchAllExplanations = async () => {
      setFetchingExplanations(true);
      
      try {
        // Run explainer parallel requests
        const explPromises = sensitiveAttrs.map(attr => 
          client.post("/api/explain", { session_id: sessionId, target_col: store.targetCol, sensitive_attr: attr })
        );
        const explResults = await Promise.allSettled(explPromises);
        
        const explanationsObj = {};
        explResults.forEach((res, i) => {
          if (res.status === "fulfilled") {
            explanationsObj[sensitiveAttrs[i]] = res.value.data;
          }
        });
        
        if (!cancelled) {
           // We just set the whole object
           setExplanation(explanationsObj);
           
           // Now run gemini-explain in parallel
           const geminiPromises = sensitiveAttrs.map(attr => 
             client.post("/api/gemini-explain", { session_id: sessionId, sensitive_attr: attr })
               .catch(err => {
                 if (err.response?.status === 503) {
                   const fallbackReason = explanationsObj[attr]?.plain_reason || "No rule-based explanation available.";
                   return { data: { explanation: `AI Copilot unavailable — showing rule-based explanation instead.\n\n${fallbackReason}` } };
                 }
                 throw err;
               })
           );
           const geminiResults = await Promise.allSettled(geminiPromises);
           
           if (!cancelled) {
             geminiResults.forEach((res, i) => {
               if (res.status === "fulfilled") {
                 setGeminiExplanation(sensitiveAttrs[i], res.value.data.explanation);
               }
             });
           }
        }
      } catch (err) {
        console.error("Failed to fetch explanations", err);
      } finally {
        if (!cancelled) setFetchingExplanations(false);
      }
    };

    fetchAllExplanations();

    return () => { cancelled = true; };
  }, [sessionId, sensitiveAttrs, store.targetCol, setExplanation, setGeminiExplanation]);

  if (!sessionId || !metrics) return null;

  const currentMetrics = metrics[activeAttr] || {};
  const groupStats = currentMetrics.group_stats || {};

  return (
    <PageWrapper>
      <div className="mb-8 flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-textPrimary mb-1">Analysis Results</h1>
          <p className="text-textSecondary text-sm">
            Review fairness metrics and AI-generated explanations for the detected biases.
          </p>
        </div>
        
        <button 
          onClick={() => navigate("/remediate")}
          className="btn-primary"
        >
          Proceed to Mitigation
        </button>
      </div>

      {/* ── Top Section ──────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="glass-card p-6 flex items-center justify-center border border-white/[0.06]">
          <AuditScoreGauge score={auditScore} grade={grade} />
        </div>
        <div className="md:col-span-2">
          <ValidationBanner validation={validation} metricsPerAttr={metrics} />
        </div>
      </div>

      {/* ── Attribute Selector ─────────────────────────────────────────────── */}
      {sensitiveAttrs.length > 1 && (
        <div className="mb-6 flex flex-wrap items-center gap-2">
          <span className="text-sm font-semibold text-textSecondary uppercase tracking-wider mr-2">Attribute:</span>
          {sensitiveAttrs.map(attr => (
            <button
              key={attr}
              onClick={() => setActiveAttr(attr)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors duration-200 border
                ${activeAttr === attr 
                  ? "bg-accent/20 text-accent border-accent/40" 
                  : "bg-surface text-textSecondary border-white/10 hover:border-white/30"
                }`}
            >
              {attr}
            </button>
          ))}
        </div>
      )}

      {/* ── Middle Section: Tabs ────────────────────────────────────────────── */}
      <div className="glass-card overflow-hidden border border-white/[0.06] flex flex-col min-h-[500px]">
        {/* Tab Header */}
        <div className="flex border-b border-white/[0.06] bg-surface/50 px-2">
          {["Metrics", "Groups", "Explanation"].map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-6 py-4 text-sm font-bold relative transition-colors duration-200
                ${activeTab === tab ? "text-accent" : "text-textSecondary hover:text-textPrimary"}
              `}
            >
              {tab}
              {activeTab === tab && (
                <motion.div 
                  layoutId="activeTab"
                  className="absolute bottom-0 left-0 w-full h-0.5 bg-accent"
                />
              )}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="p-6 flex-1">
          <AnimatePresence mode="wait">
            {activeTab === "Metrics" && (
              <motion.div
                key="Metrics"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.2 }}
                className="space-y-8"
              >
                <MetricCards metrics={currentMetrics} />
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-center pt-4 border-t border-white/[0.06]">
                  <div>
                    <h4 className="text-sm font-semibold text-textSecondary uppercase tracking-wider mb-2">Fairness Profile</h4>
                    <p className="text-sm text-textSecondary leading-relaxed mb-4">
                      This radar chart plots the four key fairness metrics. 
                      The <span className="text-accent font-medium">teal area</span> represents your dataset's current state. 
                      The <span className="text-success border-b border-dashed border-success">green dashed line</span> represents the ideal fair threshold for each metric.
                    </p>
                  </div>
                  <FairnessRadar metrics={currentMetrics} />
                </div>
              </motion.div>
            )}

            {activeTab === "Groups" && (
              <motion.div
                key="Groups"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.2 }}
              >
                <div className="mb-6">
                  <h3 className="text-lg font-semibold text-textPrimary mb-1">Group Positive Rates</h3>
                  <p className="text-sm text-textSecondary">
                    The percentage of favorable outcomes received by each demographic group within <span className="font-medium text-textPrimary">{activeAttr}</span>.
                  </p>
                </div>
                <GroupBarChart groupStats={groupStats} />
              </motion.div>
            )}

            {activeTab === "Explanation" && (
              <motion.div
                key="Explanation"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.2 }}
              >
                <div className="mb-6">
                  <h3 className="text-lg font-semibold text-textPrimary mb-1">Root Cause Analysis</h3>
                  <p className="text-sm text-textSecondary">
                    Statistical analysis and AI-driven narrative explaining why bias exists for <span className="font-medium text-textPrimary">{activeAttr}</span>.
                  </p>
                </div>
                <ExplainerPanel attrName={activeAttr} />
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* ── Copilot ────────────────────────────────────────────────────────── */}
      <BiasCopilot />

    </PageWrapper>
  );
}
