import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { FileDown, RefreshCw, Copy, CheckCircle, Brain, AlertTriangle } from "lucide-react";
import toast from "react-hot-toast";

import PageWrapper from "../components/Layout/PageWrapper";
import useAnalysisStore from "../store/analysisStore";
import client from "../api/client";

const SEVERITY_COLORS = {
  high: "bg-danger/20 text-danger border-danger/30",
  medium: "bg-warning/20 text-warning border-warning/30",
  low: "bg-success/20 text-success border-success/30",
};

export default function ReportPage() {
  const navigate = useNavigate();
  const store = useAnalysisStore();
  const { 
    sessionId, filename, targetCol, sensitiveAttrs, 
    auditScore, grade, overallSeverity, scenario,
    metrics, mitigation, reset 
  } = store;

  const [downloading, setDownloading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [recommendations, setRecommendations] = useState(null);
  const [recsLoading, setRecsLoading] = useState(false);

  useEffect(() => {
    if (!sessionId) {
      navigate("/");
      return;
    }

    const fetchRecommendations = async () => {
      setRecsLoading(true);
      try {
        const { data } = await client.post("/api/gemini-chat", {
          session_id: sessionId,
          message: "Give me 3 specific recommendations to fix the bias found in this dataset.",
          history: [] // New chat context
        });
        setRecommendations(data.reply);
      } catch {
        setRecommendations("Unable to generate recommendations at this time.");
      } finally {
        setRecsLoading(false);
      }
    };

    fetchRecommendations();
  }, [sessionId, navigate]);

  const handleDownload = async () => {
    if (!sessionId) return;
    setDownloading(true);
    
    try {
      const response = await client.get(`/api/report/${sessionId}`, {
        responseType: 'blob',
        timeout: 120000 // Give PDF generation plenty of time
      });
      
      // Create blob link to download
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `fairlens-audit-${sessionId.substring(0,8)}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      toast.success("Report downloaded successfully");
    } catch (err) {
      toast.error("Failed to generate PDF report");
    } finally {
      setDownloading(false);
    }
  };

  const handleCopySummary = () => {
    const summary = `
FairLens Bias Audit Summary
Dataset: ${filename}
Target: ${targetCol}
Score: ${auditScore}/100 (Grade ${grade})
Overall Severity: ${overallSeverity?.toUpperCase()}
Recommended Mitigation: ${mitigation?.winner || "N/A"}
`.trim();

    navigator.clipboard.writeText(summary);
    setCopied(true);
    toast.success("Summary copied to clipboard");
    setTimeout(() => setCopied(false), 2000);
  };

  const handleNewAnalysis = () => {
    reset();
    navigate("/");
  };

  if (!sessionId) return null;

  return (
    <PageWrapper>
      <div className="mb-8 flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-textPrimary mb-1">Audit Report</h1>
          <p className="text-textSecondary text-sm">
            Review your final summary and download the official PDF report.
          </p>
        </div>
        
        <div className="flex gap-3">
          <button 
            onClick={handleNewAnalysis}
            className="btn-secondary flex items-center gap-2"
          >
            <RefreshCw size={16} /> New Analysis
          </button>
          <button 
            onClick={handleDownload}
            disabled={downloading}
            className="btn-primary flex items-center gap-2"
          >
            {downloading ? <RefreshCw size={16} className="animate-spin" /> : <FileDown size={16} />}
            {downloading ? "Generating PDF..." : "Download PDF"}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* ── Summary Card ────────────────────────────────────────────────────── */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-card p-6 border border-white/[0.06] flex flex-col"
        >
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-semibold text-textPrimary">Audit Summary</h3>
            <button 
              onClick={handleCopySummary}
              className="text-textSecondary hover:text-textPrimary transition-colors"
              title="Copy Summary"
            >
              {copied ? <CheckCircle size={18} className="text-success" /> : <Copy size={18} />}
            </button>
          </div>

          <div className="flex-1 space-y-4">
            <div className="flex justify-between items-center py-2 border-b border-white/[0.04]">
              <span className="text-sm text-textSecondary">Audit Score</span>
              <span className="text-xl font-bold text-textPrimary">{auditScore} <span className="text-sm text-textSecondary font-normal">/ 100</span></span>
            </div>
            <div className="flex justify-between items-center py-2 border-b border-white/[0.04]">
              <span className="text-sm text-textSecondary">Grade</span>
              <span className={`text-lg font-bold ${grade === 'A' ? 'text-success' : grade === 'F' ? 'text-danger' : 'text-warning'}`}>{grade}</span>
            </div>
            <div className="flex justify-between items-center py-2 border-b border-white/[0.04]">
              <span className="text-sm text-textSecondary">Overall Severity</span>
              <span className={`px-2 py-1 rounded text-xs font-bold uppercase ${SEVERITY_COLORS[overallSeverity] || SEVERITY_COLORS.low}`}>
                {overallSeverity}
              </span>
            </div>
            <div className="flex justify-between items-center py-2 border-b border-white/[0.04]">
              <span className="text-sm text-textSecondary">Scenario</span>
              <span className="text-sm font-medium text-textPrimary capitalize">{scenario?.scenario || "Other"}</span>
            </div>
            <div className="flex justify-between items-center py-2 border-b border-white/[0.04]">
              <span className="text-sm text-textSecondary">Recommended Fix</span>
              <span className="text-sm font-medium text-accent capitalize">{mitigation?.winner || "None"}</span>
            </div>
          </div>
        </motion.div>

        {/* ── Findings List ───────────────────────────────────────────────────── */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="lg:col-span-2 space-y-6"
        >
          <div className="glass-card p-6 border border-white/[0.06]">
            <h3 className="text-lg font-semibold text-textPrimary mb-4">Attribute Findings</h3>
            <div className="space-y-4">
              {sensitiveAttrs.map(attr => {
                const m = metrics[attr] || {};
                const sev = m.severity || "low";
                return (
                  <div key={attr} className="bg-surface/50 rounded-xl p-4 border border-white/[0.04] flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-semibold text-textPrimary">{attr}</span>
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${SEVERITY_COLORS[sev]}`}>
                          {sev}
                        </span>
                        {m.legal_flag && (
                           <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-danger/10 text-danger border border-danger/20 flex items-center gap-1">
                             <AlertTriangle size={10} /> Legal Risk
                           </span>
                        )}
                      </div>
                      <p className="text-xs text-textSecondary">
                        SPD: <span className="font-medium text-textPrimary">{(m.spd || 0).toFixed(3)}</span> • 
                        DI: <span className="font-medium text-textPrimary">{(m.di || 0).toFixed(3)}</span>
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* ── Gemini Recommendations ──────────────────────────────────────────── */}
          <div className="glass-card p-6 border border-accent2/30 relative overflow-hidden">
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-accent to-accent2" />
            
            <div className="flex items-center gap-2 mb-4">
               <div className="w-8 h-8 rounded-lg bg-accent/20 flex items-center justify-center">
                 <Brain size={16} className="text-accent2" />
               </div>
               <h3 className="text-lg font-bold text-textPrimary">AI Action Plan</h3>
            </div>

            {recsLoading ? (
               <div className="space-y-3 animate-pulse py-2">
                 <div className="h-4 bg-surface rounded w-full"></div>
                 <div className="h-4 bg-surface rounded w-5/6"></div>
                 <div className="h-4 bg-surface rounded w-4/6"></div>
               </div>
            ) : (
               <div className="text-sm text-textPrimary leading-relaxed space-y-4">
                 {recommendations ? recommendations.split('\n\n').map((p, i) => <p key={i}>{p}</p>) : "No recommendations generated."}
               </div>
            )}
          </div>
        </motion.div>
      </div>

    </PageWrapper>
  );
}
