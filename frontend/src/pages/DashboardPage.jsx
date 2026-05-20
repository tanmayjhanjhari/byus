import { useEffect, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { 
  FileText, Calendar, Compass, Trash2, BrainCircuit, X, 
  FileDown, PlusCircle, Database, Gauge, Cpu, ClipboardList,
  Loader2, Sparkles
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
  const { user, token, isLoggedIn } = useAuthStore();
  const navigate = useNavigate();

  // Guard redirect
  useEffect(() => {
    if (!isLoggedIn || !token) {
      toast.error("Please sign in to view your dashboard.");
      navigate("/");
    }
  }, [isLoggedIn, token]);

  const [summary, setSummary] = useState(null);
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [skip, setSkip] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [selectedReport, setSelectedReport] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [downloading, setDownloading] = useState(false);

  // Fetch summary & initial history list on mount
  useEffect(() => {
    if (!isLoggedIn) return;
    const fetchData = async () => {
      try {
        setLoading(true);
        const [summaryRes, historyRes] = await Promise.all([
          getSummary(),
          getHistory(20, 0)
        ]);
        setSummary(summaryRes.data);
        setReports(historyRes.data.reports);
        setHasMore(historyRes.data.has_more);
        setSkip(0);
      } catch (e) {
        toast.error("Could not load your dashboard.");
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [isLoggedIn]);

  // Paginated load more
  const loadMore = async () => {
    setLoadingMore(true);
    try {
      const newSkip = skip + 20;
      const res = await getHistory(20, newSkip);
      setReports((prev) => [...prev, ...res.data.reports]);
      setHasMore(res.data.has_more);
      setSkip(newSkip);
    } catch {
      toast.error("Failed to load more reports.");
    } finally {
      setLoadingMore(false);
    }
  };

  // Permanently delete a report
  const handleDelete = async (reportId) => {
    try {
      await deleteReport(reportId);
      setReports((prev) => prev.filter((r) => r.id !== reportId));
      toast.success("Report deleted.");
      setSelectedReport(null);
      
      // Update local summaries
      const summaryRes = await getSummary();
      setSummary(summaryRes.data);
    } catch (e) {
      toast.error("Could not delete report.");
    }
  };

  // PDF generation downloader
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

  // View report details inside slide drawer
  const handleOpenDetail = async (report) => {
    setSelectedReport(report);
    setDetailLoading(true);
    try {
      const { data } = await getReportDetail(report.id);
      setSelectedReport(data);
    } catch {
      toast.error("Could not load report details.");
    } finally {
      setDetailLoading(false);
    }
  };

  // Helper for audit scores color classes
  const getScoreColor = (score) => {
    if (score > 85) return "text-success";
    if (score > 69) return "text-warning";
    if (score > 49) return "text-orange-500";
    return "text-danger";
  };

  // Render Cause Chip
  const renderCauseBadge = (cause) => {
    if (!cause) return <span className="bg-success/20 text-success text-[10px] px-2 py-0.5 rounded font-bold border border-success/30 uppercase">none</span>;
    
    switch (cause.toLowerCase()) {
      case "proxy":
        return <span className="bg-danger/20 text-danger text-[10px] px-2 py-0.5 rounded font-bold border border-danger/30 uppercase">proxy</span>;
      case "underrepresentation":
        return <span className="bg-amber-500/20 text-amber-400 text-[10px] px-2 py-0.5 rounded font-bold border border-amber-500/30 uppercase">underrepresentation</span>;
      case "historical_skew":
        return <span className="bg-orange-500/20 text-orange-400 text-[10px] px-2 py-0.5 rounded font-bold border border-orange-500/30 uppercase">historical skew</span>;
      default:
        return <span className="bg-success/20 text-success text-[10px] px-2 py-0.5 rounded font-bold border border-success/30 uppercase">none</span>;
    }
  };

  // Format Dates safely
  const formatDate = (dateString) => {
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
    } catch {
      return "Unknown Date";
    }
  };

  if (!isLoggedIn) return null;

  return (
    <PageWrapper>
      {/* ── Page Header ──────────────────────────────────────────────────────── */}
      <div className="mb-8 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-textPrimary mb-1">
            Welcome back, <span className="text-accent">{user?.name || "User"}</span>
          </h1>
          <p className="text-textSecondary text-sm">
            Your bias audit history and summary.
          </p>
        </div>
        <button
          onClick={() => navigate("/analyze")}
          className="btn-primary flex items-center gap-2 self-start sm:self-auto cursor-pointer"
        >
          <PlusCircle size={16} /> New Analysis
        </button>
      </div>

      {/* ── Summary Stats Row (Skeletons shown while loading) ───────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {loading ? (
          Array.from({ length: 4 }).map((_, idx) => (
            <div
              key={idx}
              className="glass-card p-5 border border-white/[0.06] flex items-center gap-4 h-24 animate-pulse"
            >
              <div className="w-12 h-12 rounded-xl bg-white/5 flex-shrink-0" />
              <div className="flex-1 space-y-2">
                <div className="h-3 bg-white/5 rounded w-1/2" />
                <div className="h-6 bg-white/5 rounded w-3/4" />
              </div>
            </div>
          ))
        ) : (
          <>
            {/* Total Analyses */}
            <div className="glass-card p-5 border border-white/[0.06] flex items-center gap-4 relative overflow-hidden">
              <div className="w-12 h-12 rounded-xl bg-accent/10 border border-accent/20 flex items-center justify-center text-accent">
                <Database size={22} />
              </div>
              <div>
                <p className="text-[10px] uppercase font-bold tracking-wider text-textSecondary">Total Analyses</p>
                <p className="text-3xl font-bold text-textPrimary mt-0.5">{summary?.total_analyses || 0}</p>
              </div>
            </div>

            {/* Avg Audit Score */}
            <div className="glass-card p-5 border border-white/[0.06] flex items-center gap-4 relative overflow-hidden">
              <div className="w-12 h-12 rounded-xl bg-accent2/10 border border-accent2/20 flex items-center justify-center text-accent2">
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
            </div>

            {/* Most Common Cause */}
            <div className="glass-card p-5 border border-white/[0.06] flex items-center gap-4 relative overflow-hidden">
              <div className="w-12 h-12 rounded-xl bg-orange-500/10 border border-orange-500/20 flex items-center justify-center text-orange-400">
                <Cpu size={22} />
              </div>
              <div className="overflow-hidden">
                <p className="text-[10px] uppercase font-bold tracking-wider text-textSecondary">Common Bias Cause</p>
                <div className="mt-1.5">{renderCauseBadge(summary?.most_common_bias_cause)}</div>
              </div>
            </div>

            {/* Scenarios Analyzed */}
            <div className="glass-card p-5 border border-white/[0.06] flex items-center gap-4 relative overflow-hidden">
              <div className="w-12 h-12 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400">
                <Compass size={22} />
              </div>
              <div className="flex-1 overflow-hidden">
                <p className="text-[10px] uppercase font-bold tracking-wider text-textSecondary">Scenarios Covered</p>
                <div className="flex flex-wrap gap-1 mt-1.5 max-h-[36px] overflow-y-auto">
                  {summary?.scenarios_analyzed && summary.scenarios_analyzed.length > 0 ? (
                    summary.scenarios_analyzed.map((s) => (
                      <span
                        key={s}
                        className="bg-surfaceDark text-[8px] font-bold uppercase text-textSecondary px-1.5 py-0.5 rounded border border-white/5 whitespace-nowrap capitalize"
                      >
                        {s}
                      </span>
                    ))
                  ) : (
                    <span className="text-xs text-textSecondary">None</span>
                  )}
                </div>
              </div>
            </div>
          </>
        )}
      </div>

      {/* ── SECTION 2: Reports History List ─────────────────────────────────── */}
      <div className="glass-card p-6 border border-white/[0.06] relative overflow-hidden">
        <div className="flex items-center gap-2 mb-6">
          <FileText size={18} className="text-accent" />
          <h3 className="text-lg font-semibold text-textPrimary">Past Analyses</h3>
          {!loading && (
            <span className="text-xs font-semibold bg-surface px-2 py-0.5 rounded text-textSecondary border border-white/5">
              {reports.length} loaded
            </span>
          )}
        </div>

        {loading ? (
          <div className="space-y-4 py-8">
            {Array.from({ length: 4 }).map((_, idx) => (
              <div key={idx} className="h-12 bg-white/5 rounded-xl animate-pulse" />
            ))}
          </div>
        ) : reports.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <div className="w-16 h-16 rounded-full bg-surfaceDark flex items-center justify-center text-textSecondary mb-4">
              <ClipboardList size={28} />
            </div>
            <h4 className="text-base font-bold text-textPrimary">No analyses yet</h4>
            <p className="text-xs text-textSecondary mt-1 max-w-[280px] leading-relaxed mx-auto">
              Get started by uploading your dataset and running your very first bias audit!
            </p>
            <button
              onClick={() => navigate("/analyze")}
              className="mt-6 bg-accent hover:bg-accentLight text-primary font-semibold px-5 py-2.5 rounded-xl text-xs flex items-center gap-2 cursor-pointer"
            >
              <PlusCircle size={14} /> Start Your First Audit
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse min-w-[700px]">
                <thead>
                  <tr className="border-b border-white/[0.06] text-textSecondary text-[10px] font-bold uppercase tracking-wider">
                    <th className="pb-3 pl-2">Dataset Name</th>
                    <th className="pb-3">Run Date</th>
                    <th className="pb-3">Scenario</th>
                    <th className="pb-3 text-center">Score</th>
                    <th className="pb-3 text-center">Grade</th>
                    <th className="pb-3 text-center">Severity</th>
                    <th className="pb-3 text-right pr-2">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.04]">
                  <AnimatePresence>
                    {reports.map((report, idx) => (
                      <motion.tr
                        key={report.id}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: 10 }}
                        transition={{ delay: idx * 0.04 }}
                        onClick={() => handleOpenDetail(report)}
                        className="group hover:bg-white/[0.02] cursor-pointer text-xs transition-colors"
                      >
                        {/* Filename */}
                        <td className="py-4 pl-2 font-semibold text-textPrimary max-w-[180px] truncate">
                          {report.filename}
                        </td>

                        {/* Created At */}
                        <td className="py-4 text-textSecondary">
                          {formatDate(report.created_at)}
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

                        {/* Actions */}
                        <td className="py-4 text-right pr-2">
                          <div className="flex items-center justify-end gap-2">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleOpenDetail(report);
                              }}
                              className="px-3 py-1 rounded bg-white/[0.04] text-textPrimary hover:bg-accent hover:text-primary transition-all text-[11px] font-semibold cursor-pointer"
                            >
                              View
                            </button>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleDelete(report.id);
                              }}
                              className="p-1 rounded text-textSecondary hover:text-danger hover:bg-danger/10 transition-colors cursor-pointer"
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
                  onClick={loadMore}
                  disabled={loadingMore}
                  className="px-4 py-2 border border-white/10 hover:border-accent text-textSecondary hover:text-accent font-semibold text-xs rounded-xl flex items-center gap-2 transition-all cursor-pointer"
                >
                  {loadingMore ? <Loader2 size={14} className="animate-spin text-accent" /> : null}
                  {loadingMore ? "Loading More..." : "Load More History"}
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── Reports Details Slide Drawer (480px width, clean visual flow) ────── */}
      <AnimatePresence>
        {selectedReport && (
          <>
            {/* Backdrop overlay */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 0.5 }}
              exit={{ opacity: 0 }}
              onClick={() => setSelectedReport(null)}
              className="fixed inset-0 z-50 bg-black"
            />

            {/* Slide-over panel */}
            <motion.div
              initial={{ x: "100%" }}
              animate={{ x: 0 }}
              exit={{ x: "100%" }}
              transition={{ type: "tween", duration: 0.3 }}
              className="fixed right-0 top-0 bottom-0 w-full max-w-[480px] bg-surfaceDark border-l border-white/10 z-[60] shadow-2xl p-6 overflow-y-auto flex flex-col"
            >
              {/* Drawer Header */}
              <div className="flex items-center justify-between pb-4 border-b border-white/[0.08] mb-6 flex-shrink-0">
                <div className="overflow-hidden mr-2">
                  <h3 className="text-sm font-bold text-textPrimary truncate" title={selectedReport.filename}>
                    {selectedReport.filename}
                  </h3>
                  <p className="text-[10px] text-textSecondary mt-0.5">
                    {formatDate(selectedReport.created_at)}
                  </p>
                </div>
                <button
                  onClick={() => setSelectedReport(null)}
                  className="p-1 rounded-lg text-textSecondary hover:text-textPrimary hover:bg-white/[0.04] transition-colors flex-shrink-0 cursor-pointer"
                >
                  <X size={20} />
                </button>
              </div>

              {detailLoading ? (
                <div className="flex-1 flex flex-col items-center justify-center text-textSecondary text-xs">
                  <Loader2 size={24} className="animate-spin text-accent mb-3" />
                  Loading audit metadata...
                </div>
              ) : (
                <div className="flex-1 flex flex-col justify-between">
                  <div className="space-y-6">
                    {/* Big Score Indicator */}
                    <div className="flex items-center justify-between p-4 bg-surface rounded-xl border border-white/[0.04]">
                      <div>
                        <p className="text-[9px] uppercase font-bold text-textSecondary tracking-wider">Audit Score</p>
                        <div className="flex items-baseline gap-1 mt-1">
                          <span className={`text-3xl font-extrabold ${getScoreColor(selectedReport.audit_score)}`}>
                            {selectedReport.audit_score}
                          </span>
                          <span className="text-xs text-textSecondary">/100</span>
                        </div>
                      </div>
                      <div className="text-right">
                        <span className={`px-3 py-1 rounded-lg text-xs font-bold
                          ${selectedReport.grade === 'A' ? 'text-success bg-success/15 border border-success/30' : selectedReport.grade === 'F' ? 'text-danger bg-danger/15 border border-danger/30' : 'text-warning bg-warning/15 border border-warning/30'}`}>
                          Grade {selectedReport.grade}
                        </span>
                      </div>
                    </div>

                    {/* Root Cause prediction cards */}
                    {selectedReport.pattern_predictions && Object.keys(selectedReport.pattern_predictions).length > 0 && (
                      <div className="space-y-3">
                        <h4 className="text-xs font-bold uppercase text-textSecondary tracking-wider flex items-center gap-1.5">
                          <BrainCircuit size={14} className="text-accent" />
                          Root Cause Predictions
                        </h4>
                        {Object.entries(selectedReport.pattern_predictions).map(([attr, pred]) => (
                          <div key={attr} className="bg-surface border border-white/[0.06] rounded-xl p-3.5 text-xs">
                            <div className="flex justify-between items-center mb-1.5">
                              <span className="font-semibold text-textPrimary capitalize">{attr}</span>
                              {renderCauseBadge(pred.predicted_cause)}
                            </div>
                            <p className="text-textSecondary leading-relaxed text-[11px]">{pred.cause_label}</p>
                            <div className="flex items-center gap-2 mt-2 pt-2 border-t border-white/[0.04] text-[10px] text-textSecondary">
                              <span>Confidence: <span className="text-textPrimary font-semibold">{pred.confidence_pct}%</span></span>
                              <span>•</span>
                              <span>Severity: <span className="text-textPrimary font-semibold capitalize">{pred.predicted_severity}</span></span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Metrics Table */}
                    <div className="space-y-3">
                      <h4 className="text-xs font-bold uppercase text-textSecondary tracking-wider flex items-center gap-1.5">
                        <Sparkles size={14} className="text-accent" />
                        Sensitive Attributes Breakdown
                      </h4>
                      <div className="divide-y divide-white/[0.04] bg-surface rounded-xl border border-white/[0.04] overflow-hidden">
                        {selectedReport.sensitive_attrs?.map((attr) => {
                          const summaryData = selectedReport.metrics_summary?.[attr] || {};
                          return (
                            <div key={attr} className="p-3.5 flex justify-between items-center text-xs">
                              <div>
                                <span className="font-semibold text-textPrimary capitalize">{attr}</span>
                                <p className="text-[10px] text-textSecondary mt-0.5">
                                  SPD: <span className="text-textPrimary font-medium">{(summaryData.spd || 0).toFixed(3)}</span> • 
                                  DI: <span className="text-textPrimary font-medium">{(summaryData.di || 1.0).toFixed(3)}</span>
                                </p>
                              </div>
                              <span className={`px-2 py-0.5 rounded text-[9px] font-bold uppercase border ${SEVERITY_COLORS[summaryData.severity || "low"]}`}>
                                {summaryData.severity}
                              </span>
                            </div>
                          );
                        })}
                      </div>
                    </div>

                    {/* Recommended Mitigation Details */}
                    {selectedReport.winner_technique && selectedReport.winner_technique !== "None" && (
                      <div className="glass-card p-4 border border-white/[0.06] flex items-center justify-between text-xs">
                        <div>
                          <p className="font-semibold text-textPrimary">Mitigation Selection</p>
                          <p className="text-[10px] text-textSecondary mt-0.5">
                            Recommended: <span className="text-accent font-semibold capitalize">{selectedReport.winner_technique}</span>
                          </p>
                        </div>
                        {selectedReport.bias_reduction_pct > 0 && (
                          <span className="bg-success/15 border border-success/30 text-success text-[10px] font-bold px-2 py-1 rounded">
                            -{selectedReport.bias_reduction_pct.toFixed(0)}% Bias
                          </span>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Actions Drawer Footer */}
                  <div className="flex gap-3 pt-6 border-t border-white/[0.08] mt-8 flex-shrink-0">
                    <button
                      onClick={() => handleDownloadPDF(selectedReport.session_id)}
                      disabled={downloading}
                      className="flex-1 bg-accent hover:bg-accentLight text-primary font-semibold py-2.5 rounded-xl text-xs flex items-center justify-center gap-2 transition-all cursor-pointer"
                    >
                      {downloading ? <Loader2 size={14} className="animate-spin" /> : <FileDown size={14} />}
                      {downloading ? "Downloading PDF..." : "Download PDF"}
                    </button>
                    <button
                      onClick={() => handleDelete(selectedReport.id)}
                      className="px-4 py-2.5 border border-white/10 hover:border-danger text-textSecondary hover:text-danger rounded-xl text-xs transition-all cursor-pointer flex items-center justify-center gap-2"
                      title="Delete Report"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              )}
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </PageWrapper>
  );
}
