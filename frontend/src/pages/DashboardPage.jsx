import { useEffect, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { 
  FileText, Calendar, Compass, ShieldAlert, BarChart3, 
  Trash2, BrainCircuit, X, FileDown, PlusCircle, HelpCircle,
  Database, Gauge, Award, Cpu, AlertTriangle
} from "lucide-react";
import toast from "react-hot-toast";

import PageWrapper from "../components/Layout/PageWrapper";
import useAuthStore from "../store/authStore";
import { getSummary, getHistory, getReportDetail, deleteReport } from "../api/auth";
import client from "../api/client";

const SEVERITY_COLORS = {
  high: "bg-danger/20 text-danger border-danger/30",
  medium: "bg-warning/20 text-warning border-warning/30",
  low: "bg-success/20 text-success border-success/30",
  none: "bg-slate-500/20 text-slate-400 border-slate-500/30",
};

export default function DashboardPage() {
  const { isLoggedIn, token } = useAuthStore();
  const navigate = useNavigate();

  const [summary, setSummary] = useState(null);
  const [history, setHistory] = useState([]);
  const [totalReports, setTotalReports] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [skip, setSkip] = useState(0);
  const [limit] = useState(10);
  
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [selectedReportId, setSelectedReportId] = useState(null);
  const [reportDetail, setReportDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [downloading, setDownloading] = useState(false);

  // Auth Guard redirect
  useEffect(() => {
    if (!isLoggedIn) {
      toast.error("Please sign in to view your dashboard.");
      navigate("/");
    }
  }, [isLoggedIn, navigate]);

  const fetchData = async (resetList = false) => {
    if (!isLoggedIn) return;
    if (resetList) {
      setLoading(true);
    } else {
      setLoadingMore(true);
    }

    try {
      const currentSkip = resetList ? 0 : skip;
      const [sumRes, histRes] = await Promise.all([
        getSummary(),
        getHistory(limit, currentSkip)
      ]);

      setSummary(sumRes.data);
      setTotalReports(histRes.data.total);
      setHasMore(histRes.data.has_more);
      
      if (resetList) {
        setHistory(histRes.data.reports);
        setSkip(limit);
      } else {
        setHistory(prev => [...prev, ...histRes.data.reports]);
        setSkip(prev => prev + limit);
      }
    } catch (err) {
      toast.error("Failed to load dashboard data.");
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  };

  useEffect(() => {
    fetchData(true);
  }, [token]);

  const handleLoadMore = () => {
    if (!loadingMore && hasMore) {
      fetchData(false);
    }
  };

  const handleOpenDetail = async (reportId) => {
    setSelectedReportId(reportId);
    setDetailLoading(true);
    try {
      const { data } = await getReportDetail(reportId);
      setReportDetail(data);
    } catch {
      toast.error("Could not fetch report details.");
      setSelectedReportId(null);
    } finally {
      setDetailLoading(false);
    }
  };

  const handleDeleteReport = async (reportId, e) => {
    e.stopPropagation();
    if (!window.confirm("Are you sure you want to delete this report permanently?")) return;

    try {
      await deleteReport(reportId);
      toast.success("Report deleted successfully.");
      
      // Update local states
      setHistory(prev => prev.filter(r => r.id !== reportId));
      setTotalReports(prev => Math.max(0, prev - 1));
      
      // If deleted active detail panel report, close panel
      if (selectedReportId === reportId) {
        setSelectedReportId(null);
        setReportDetail(null);
      }
      
      // Reload stats/summaries
      const sumRes = await getSummary();
      setSummary(sumRes.data);
    } catch {
      toast.error("Failed to delete report.");
    }
  };

  const handleDownloadPDF = async (sessionId) => {
    if (!sessionId) return;
    setDownloading(true);
    try {
      const response = await client.get(`/api/report/${sessionId}`, {
        responseType: 'blob',
        timeout: 120000
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `byus-audit-${sessionId.substring(0,8)}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      toast.success("PDF report downloaded.");
    } catch {
      toast.error("Failed to download PDF.");
    } finally {
      setDownloading(false);
    }
  };

  const getScoreColor = (score) => {
    if (score >= 80) return "text-success";
    if (score >= 60) return "text-warning";
    return "text-danger";
  };

  if (!isLoggedIn || loading) {
    return (
      <PageWrapper>
        <div className="flex flex-col items-center justify-center min-h-[400px]">
          <div className="w-10 h-10 border-4 border-accent border-t-transparent rounded-full animate-spin mb-4" />
          <p className="text-textSecondary text-sm">Loading dashboard analytics...</p>
        </div>
      </PageWrapper>
    );
  }

  return (
    <PageWrapper>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-textPrimary mb-1">My Bias Analytics</h1>
        <p className="text-textSecondary text-sm">
          Track and audit your historical datasets, models, and AI explanations in one unified center.
        </p>
      </div>

      {/* ── SECTION 1: Summary Stats Row ────────────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {/* Total Analyses */}
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-card p-5 border border-white/[0.06] flex items-center gap-4 relative overflow-hidden"
        >
          <div className="w-12 h-12 rounded-xl bg-accent/15 flex items-center justify-center text-accent">
            <Database size={22} />
          </div>
          <div>
            <p className="text-[10px] uppercase font-bold tracking-wider text-textSecondary">Total Analyses</p>
            <p className="text-3xl font-bold text-textPrimary mt-0.5">{summary?.total_analyses || 0}</p>
          </div>
        </motion.div>

        {/* Avg Audit Score */}
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05 }}
          className="glass-card p-5 border border-white/[0.06] flex items-center gap-4 relative overflow-hidden"
        >
          <div className="w-12 h-12 rounded-xl bg-accent2/15 flex items-center justify-center text-accent2">
            <Gauge size={22} />
          </div>
          <div>
            <p className="text-[10px] uppercase font-bold tracking-wider text-textSecondary">Average Score</p>
            <p className="text-3xl font-bold text-textPrimary mt-0.5">
              {summary?.avg_audit_score ? (
                <>
                  <span className={getScoreColor(summary.avg_audit_score)}>{summary.avg_audit_score}</span>
                  <span className="text-xs text-textSecondary font-normal"> / 100</span>
                </>
              ) : (
                <span className="text-textSecondary text-xl font-medium">N/A</span>
              )}
            </p>
          </div>
        </motion.div>

        {/* Most Common Cause */}
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="glass-card p-5 border border-white/[0.06] flex items-center gap-4 relative overflow-hidden"
        >
          <div className="w-12 h-12 rounded-xl bg-orange-500/15 flex items-center justify-center text-orange-400">
            <Cpu size={22} />
          </div>
          <div className="overflow-hidden">
            <p className="text-[10px] uppercase font-bold tracking-wider text-textSecondary">Common Bias Cause</p>
            <p className="text-sm font-semibold text-textPrimary truncate mt-1.5 capitalize">
              {summary?.most_common_bias_cause ? summary.most_common_bias_cause.replace("_", " ") : "None detected"}
            </p>
          </div>
        </motion.div>

        {/* Scenarios Analyzed */}
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
          className="glass-card p-5 border border-white/[0.06] flex items-center gap-4 relative overflow-hidden"
        >
          <div className="w-12 h-12 rounded-xl bg-purple-500/15 flex items-center justify-center text-purple-400">
            <Compass size={22} />
          </div>
          <div className="flex-1 overflow-hidden">
            <p className="text-[10px] uppercase font-bold tracking-wider text-textSecondary">Scenarios Covered</p>
            <div className="flex flex-wrap gap-1.5 mt-1.5 max-h-[40px] overflow-y-auto">
              {summary?.scenarios_analyzed && summary.scenarios_analyzed.length > 0 ? (
                summary.scenarios_analyzed.map(s => (
                  <span key={s} className="bg-surfaceDark text-[9px] font-bold uppercase text-textSecondary px-1.5 py-0.5 rounded border border-white/5 whitespace-nowrap capitalize">
                    {s}
                  </span>
                ))
              ) : (
                <span className="text-xs text-textSecondary">None</span>
              )}
            </div>
          </div>
        </motion.div>
      </div>

      {/* ── SECTION 2: Reports History List ─────────────────────────────────── */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="glass-card p-6 border border-white/[0.06] relative overflow-hidden"
      >
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <FileText size={18} className="text-accent" />
            <h3 className="text-lg font-semibold text-textPrimary">Audit Run History</h3>
            <span className="text-xs font-semibold bg-surface px-2 py-0.5 rounded text-textSecondary border border-white/5">
              {totalReports} total
            </span>
          </div>
          {totalReports > 0 && (
            <Link to="/" className="text-xs font-semibold text-accent hover:text-accentLight flex items-center gap-1">
              <PlusCircle size={14} /> New Audit
            </Link>
          )}
        </div>

        {history.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <div className="w-16 h-16 rounded-full bg-surfaceDark flex items-center justify-center text-textSecondary mb-4">
              <FileText size={28} />
            </div>
            <h4 className="text-base font-bold text-textPrimary">No analyses yet</h4>
            <p className="text-xs text-textSecondary mt-1 max-w-[280px] leading-relaxed mx-auto">
              Upload your first CSV dataset and run ByUs bias audits to populate your tracking history.
            </p>
            <Link to="/" className="mt-6 bg-accent hover:bg-accentLight text-primary font-semibold px-5 py-2.5 rounded-xl text-xs flex items-center gap-2">
              <PlusCircle size={14} /> Run First Audit
            </Link>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse min-w-[700px]">
                <thead>
                  <tr className="border-b border-white/[0.06] text-textSecondary text-[10px] font-bold uppercase tracking-wider">
                    <th className="pb-3 pl-2">Dataset</th>
                    <th className="pb-3">Run Date</th>
                    <th className="pb-3">Scenario</th>
                    <th className="pb-3 text-center">Score</th>
                    <th className="pb-3 text-center">Grade</th>
                    <th className="pb-3 text-center">Severity</th>
                    <th className="pb-3">Sensitive Attributes</th>
                    <th className="pb-3 text-right pr-2">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.04]">
                  <AnimatePresence>
                    {history.map((report, idx) => (
                      <motion.tr
                        key={report.id}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: idx * 0.03 }}
                        onClick={() => handleOpenDetail(report.id)}
                        className="group hover:bg-white/[0.02] cursor-pointer text-xs transition-colors"
                      >
                        {/* Filename */}
                        <td className="py-4 pl-2 font-semibold text-textPrimary max-w-[150px] truncate">
                          {report.filename}
                        </td>

                        {/* Created At */}
                        <td className="py-4 text-textSecondary">
                          {new Date(report.created_at).toLocaleDateString()}
                        </td>

                        {/* Scenario */}
                        <td className="py-4 text-textSecondary capitalize">
                          {report.scenario}
                        </td>

                        {/* Score */}
                        <td className={`py-4 text-center font-bold ${getScoreColor(report.audit_score)}`}>
                          {report.audit_score}
                        </td>

                        {/* Grade */}
                        <td className="py-4 text-center">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold
                            ${report.grade === 'A' ? 'text-success bg-success/10' : report.grade === 'F' ? 'text-danger bg-danger/10' : 'text-warning bg-warning/10'}`}>
                            {report.grade}
                          </span>
                        </td>

                        {/* Severity */}
                        <td className="py-4 text-center">
                          <span className={`px-2 py-0.5 rounded text-[9px] font-bold uppercase border
                            ${SEVERITY_COLORS[report.overall_severity] || SEVERITY_COLORS.low}`}>
                            {report.overall_severity}
                          </span>
                        </td>

                        {/* Sensitive Attrs */}
                        <td className="py-4">
                          <div className="flex flex-wrap gap-1">
                            {report.sensitive_attrs?.map(a => (
                              <span key={a} className="bg-surfaceDark text-[9px] text-textSecondary px-1.5 py-0.5 rounded border border-white/5 whitespace-nowrap">
                                {a}
                              </span>
                            ))}
                          </div>
                        </td>

                        {/* Actions */}
                        <td className="py-4 text-right pr-2">
                          <div className="flex items-center justify-end gap-2">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleOpenDetail(report.id);
                              }}
                              className="px-3 py-1 rounded bg-white/[0.04] text-textPrimary hover:bg-accent hover:text-primary transition-all text-[11px] font-semibold"
                            >
                              View
                            </button>
                            <button
                              onClick={(e) => handleDeleteReport(report.id, e)}
                              className="p-1 rounded text-textSecondary hover:text-danger hover:bg-danger/10 transition-colors"
                              title="Delete Report"
                            >
                              <Trash2 size={14} />
                            </button>
                          </div>
                        </td>
                      </motion.tr>
                    ))}
                  </AnimatePresence>
                </tbody>
              </table>
            </div>

            {/* Load More Button */}
            {hasMore && (
              <div className="flex justify-center pt-4">
                <button
                  onClick={handleLoadMore}
                  disabled={loadingMore}
                  className="px-4 py-2 border border-white/10 hover:border-accent text-textSecondary hover:text-accent font-semibold text-xs rounded-xl flex items-center gap-2 transition-all cursor-default"
                >
                  {loadingMore ? (
                    <div className="w-3.5 h-3.5 border-2 border-accent border-t-transparent rounded-full animate-spin" />
                  ) : null}
                  {loadingMore ? "Loading More..." : "Load More History"}
                </button>
              </div>
            )}
          </div>
        )}
      </motion.div>

      {/* ── Slide-Over Panel Details ────────────────────────────────────────── */}
      <AnimatePresence>
        {selectedReportId && (
          <>
            {/* Backdrop overlay */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 0.5 }}
              exit={{ opacity: 0 }}
              onClick={() => setSelectedReportId(null)}
              className="fixed inset-0 z-50 bg-black"
            />

            {/* Slide-over panel */}
            <motion.div
              initial={{ x: "100%" }}
              animate={{ x: 0 }}
              exit={{ x: "100%" }}
              transition={{ type: "tween", duration: 0.3 }}
              className="fixed right-0 top-0 bottom-0 w-full max-w-[620px] bg-surfaceDark border-l border-white/10 z-[60] shadow-2xl p-6 overflow-y-auto flex flex-col"
            >
              {/* Top row */}
              <div className="flex items-center justify-between pb-4 border-b border-white/[0.08] mb-6">
                <div>
                  <h3 className="text-base font-bold text-textPrimary truncate max-w-[450px]">
                    {detailLoading ? "Loading details..." : reportDetail?.filename}
                  </h3>
                  <p className="text-[10px] text-textSecondary mt-0.5">
                    {reportDetail && new Date(reportDetail.created_at).toLocaleString()}
                  </p>
                </div>
                <button
                  onClick={() => setSelectedReportId(null)}
                  className="p-1 rounded-lg text-textSecondary hover:text-textPrimary hover:bg-white/[0.04] transition-colors"
                >
                  <X size={20} />
                </button>
              </div>

              {detailLoading ? (
                <div className="flex-1 flex flex-col items-center justify-center text-textSecondary text-xs">
                  <div className="w-8 h-8 border-4 border-accent border-t-transparent rounded-full animate-spin mb-3" />
                  Fetching full report analysis...
                </div>
              ) : reportDetail ? (
                <div className="flex-1 space-y-6">
                  {/* Summary Block */}
                  <div className="grid grid-cols-3 gap-3 bg-surface p-4 rounded-xl border border-white/[0.04]">
                    <div className="text-center py-1">
                      <p className="text-[9px] uppercase font-bold text-textSecondary tracking-wider">Audit Score</p>
                      <p className={`text-xl font-bold mt-1 ${getScoreColor(reportDetail.audit_score)}`}>{reportDetail.audit_score}</p>
                    </div>
                    <div className="text-center py-1 border-x border-white/[0.06]">
                      <p className="text-[9px] uppercase font-bold text-textSecondary tracking-wider">Grade</p>
                      <p className="text-xl font-bold mt-1 text-textPrimary">{reportDetail.grade}</p>
                    </div>
                    <div className="text-center py-1">
                      <p className="text-[9px] uppercase font-bold text-textSecondary tracking-wider">Severity</p>
                      <p className="text-xs font-bold mt-2 uppercase text-textPrimary truncate">{reportDetail.overall_severity}</p>
                    </div>
                  </div>

                  {/* Root Cause prediction cards */}
                  {reportDetail.pattern_predictions && Object.keys(reportDetail.pattern_predictions).length > 0 && (
                    <div className="space-y-3">
                      <h4 className="text-xs font-bold uppercase text-textSecondary tracking-wider flex items-center gap-1.5">
                        <BrainCircuit size={14} className="text-accent" />
                        Root Cause Prediction
                      </h4>
                      {Object.entries(reportDetail.pattern_predictions).map(([attr, pred]) => (
                        <div key={attr} className="bg-surface border border-white/[0.06] rounded-xl p-3.5 text-xs">
                          <div className="flex justify-between items-center mb-1.5">
                            <span className="font-semibold text-textPrimary capitalize">{attr} Attribute</span>
                            <span className="text-[10px] font-bold text-accent px-1.5 py-0.5 bg-accent/10 rounded">
                              {pred.predicted_cause?.replace("_", " ")}
                            </span>
                          </div>
                          <p className="text-textSecondary leading-relaxed">{pred.cause_label}</p>
                          <div className="flex items-center gap-2 mt-2 pt-2 border-t border-white/[0.04] text-[10px] text-textSecondary">
                            <span>Confidence: <span className="text-textPrimary font-semibold">{pred.confidence_pct}%</span></span>
                            <span>•</span>
                            <span>Severity: <span className="text-textPrimary font-semibold capitalize">{pred.predicted_severity}</span></span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Attribute Findings list */}
                  <div className="space-y-3">
                    <h4 className="text-xs font-bold uppercase text-textSecondary tracking-wider flex items-center gap-1.5">
                      <BarChart3 size={14} className="text-accent" />
                      Individual Metrics
                    </h4>
                    <div className="divide-y divide-white/[0.04] bg-surface rounded-xl border border-white/[0.04]">
                      {reportDetail.sensitive_attrs?.map((attr) => {
                        const summary = reportDetail.metrics_summary?.[attr] || {};
                        return (
                          <div key={attr} className="p-3.5 flex justify-between items-center text-xs">
                            <div>
                              <span className="font-semibold text-textPrimary capitalize">{attr}</span>
                              <p className="text-[10px] text-textSecondary mt-0.5">
                                SPD: <span className="text-textPrimary">{(summary.spd || 0).toFixed(3)}</span> • 
                                DI: <span className="text-textPrimary">{(summary.di || 1.0).toFixed(3)}</span>
                              </p>
                            </div>
                            <span className={`px-2 py-0.5 rounded text-[9px] font-bold uppercase border ${SEVERITY_COLORS[summary.severity || "low"]}`}>
                              {summary.severity}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* Mitigator Selection */}
                  <div className="glass-card p-4 border border-white/[0.06] flex items-center justify-between text-xs">
                    <div>
                      <p className="font-semibold text-textPrimary">Recommended Strategy</p>
                      <p className="text-[10px] text-textSecondary mt-0.5">
                        Selected: <span className="text-accent font-semibold capitalize">{reportDetail.winner_technique}</span>
                      </p>
                    </div>
                    {reportDetail.bias_reduction_pct > 0 && (
                      <span className="bg-success/15 border border-success/30 text-success text-[10px] font-bold px-2 py-1 rounded">
                        -{reportDetail.bias_reduction_pct.toFixed(0)}% Bias
                      </span>
                    )}
                  </div>

                  {/* PDF Download and Actions */}
                  <div className="flex gap-3 pt-6 border-t border-white/[0.08]">
                    <button
                      onClick={() => handleDownloadPDF(reportDetail.session_id)}
                      disabled={downloading}
                      className="flex-1 bg-accent hover:bg-accentLight text-primary font-semibold py-2.5 rounded-xl text-xs flex items-center justify-center gap-2 transition-all cursor-default"
                    >
                      {downloading ? <PlusCircle size={14} className="animate-spin" /> : <FileDown size={14} />}
                      {downloading ? "Downloading..." : "Download Official PDF"}
                    </button>
                    <button
                      onClick={(e) => handleDeleteReport(reportDetail.id, e)}
                      className="px-4 py-2.5 border border-white/10 hover:border-danger text-textSecondary hover:text-danger rounded-xl text-xs transition-all cursor-default flex items-center justify-center gap-2"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              ) : null}
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </PageWrapper>
  );
}
