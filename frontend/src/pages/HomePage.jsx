import { motion, AnimatePresence } from "framer-motion";
import { ArrowRight, BarChart3, Brain, Wrench, Shield } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import PageWrapper from "../components/Layout/PageWrapper";

// ── Animated word reveal ───────────────────────────────────────────────────────
const HEADLINE_WORDS = [
  { text: "Detect.",  color: "text-accent",  delay: 0 },
  { text: "Explain.", color: "text-accent2", delay: 0.6 },
  { text: "Fix.",     color: "text-success", delay: 1.2 },
];

const TAGLINE = "AI bias before it impacts real people.";

const FEATURES = [
  {
    icon: Shield,
    title: "Detect",
    desc: "SPD, DI, EOD, AOD fairness metrics with severity grading and legal threshold alerts.",
    color: "text-accent",
    bg: "bg-accent/10",
    border: "hover:border-accent/40",
  },
  {
    icon: Brain,
    title: "Explain",
    desc: "Gemini 2.0 Flash explains bias root causes in plain English — for any audience.",
    color: "text-accent2",
    bg: "bg-accent2/10",
    border: "hover:border-accent2/40",
  },
  {
    icon: Wrench,
    title: "Fix",
    desc: "Reweighing and threshold adjustment run side-by-side with accuracy trade-off analysis.",
    color: "text-success",
    bg: "bg-success/10",
    border: "hover:border-success/40",
  },
];

const STATS = [
  { value: "4",      label: "Fairness Metrics" },
  { value: "2",      label: "Mitigation Algorithms" },
  { value: "Gemini", label: "AI Powered" },
];

export default function HomePage() {
  const navigate = useNavigate();
  const [taglineVisible, setTaglineVisible] = useState(false);

  // Show tagline after words animate in
  useEffect(() => {
    const t = setTimeout(() => setTaglineVisible(true), 2000);
    return () => clearTimeout(t);
  }, []);

  return (
    <PageWrapper className="flex flex-col items-center justify-start">
      {/* ── Hero ──────────────────────────────────────────────────────────────── */}
      <div className="w-full text-center pt-12 pb-6">
        {/* Animated pill badge */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="inline-flex items-center gap-2 bg-accent/10 border border-accent/30 text-accent text-sm font-medium px-4 py-1.5 rounded-full mb-8"
        >
          <span className="w-2 h-2 rounded-full bg-accent animate-pulse" />
          Powered by Google Gemini 2.0 Flash
        </motion.div>

        {/* Word-by-word headline */}
        <div className="flex flex-wrap items-center justify-center gap-x-4 gap-y-2 mb-4">
          {HEADLINE_WORDS.map(({ text, color, delay }) => (
            <motion.span
              key={text}
              initial={{ opacity: 0, y: 30, filter: "blur(8px)" }}
              animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
              transition={{ duration: 0.55, delay, ease: "easeOut" }}
              className={`text-5xl sm:text-6xl lg:text-7xl font-bold ${color}`}
            >
              {text}
            </motion.span>
          ))}
        </div>

        {/* Tagline fades in after words */}
        <AnimatePresence>
          {taglineVisible && (
            <motion.p
              key="tagline"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.55, ease: "easeOut" }}
              className="text-2xl sm:text-3xl font-semibold text-textPrimary mb-4"
            >
              {TAGLINE}
            </motion.p>
          )}
        </AnimatePresence>

        {/* Subheading */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 2.2, duration: 0.6 }}
          className="text-base sm:text-lg text-textSecondary max-w-2xl mx-auto mb-10"
        >
          Upload any dataset. FairLens surfaces hidden discrimination, explains
          why it exists, and helps you fix it.
        </motion.p>

        {/* CTA button */}
        <motion.button
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 2.4, duration: 0.4 }}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.97 }}
          onClick={() => navigate("/analyze")}
          className="relative inline-flex items-center gap-3 px-9 py-4 rounded-xl font-bold text-lg text-primary overflow-hidden"
          style={{
            background: "linear-gradient(135deg, #14B8A6 0%, #818CF8 100%)",
            boxShadow: "0 0 32px rgba(20,184,166,0.35), 0 0 64px rgba(129,140,248,0.2)",
          }}
        >
          {/* Pulse ring */}
          <motion.span
            className="absolute inset-0 rounded-xl"
            animate={{ boxShadow: ["0 0 0px rgba(20,184,166,0.4)", "0 0 24px rgba(20,184,166,0)", "0 0 0px rgba(20,184,166,0.4)"] }}
            transition={{ duration: 2.5, repeat: Infinity }}
          />
          Start Audit
          <ArrowRight size={20} strokeWidth={2.5} />
        </motion.button>
      </div>

      {/* ── Feature cards ─────────────────────────────────────────────────────── */}
      <div className="w-full grid grid-cols-1 sm:grid-cols-3 gap-5 mt-6">
        {FEATURES.map((f, i) => (
          <motion.div
            key={f.title}
            initial={{ opacity: 0, y: 32 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 2.5 + i * 0.12, duration: 0.45, ease: "easeOut" }}
            whileHover={{ y: -4, transition: { duration: 0.2 } }}
            className={`glass-card p-6 border border-white/[0.06] ${f.border} transition-colors duration-300 cursor-default`}
          >
            <div className={`w-11 h-11 rounded-xl ${f.bg} flex items-center justify-center mb-4`}>
              <f.icon size={22} className={f.color} />
            </div>
            <h3 className={`text-xl font-bold mb-2 ${f.color}`}>{f.title}</h3>
            <p className="text-sm text-textSecondary leading-relaxed">{f.desc}</p>
          </motion.div>
        ))}
      </div>

      {/* ── Stats row ──────────────────────────────────────────────────────────── */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 3, duration: 0.6 }}
        className="w-full flex flex-wrap justify-center gap-x-12 gap-y-4 mt-12 pt-8 border-t border-white/[0.06]"
      >
        {STATS.map((s) => (
          <div key={s.label} className="text-center">
            <div className="text-2xl font-bold text-accent">{s.value}</div>
            <div className="text-xs text-textSecondary mt-0.5">{s.label}</div>
          </div>
        ))}
      </motion.div>
    </PageWrapper>
  );
}
