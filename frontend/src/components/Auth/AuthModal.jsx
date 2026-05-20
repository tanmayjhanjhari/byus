import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Mail, Lock, User, Loader2, Scan } from "lucide-react";
import { register, login } from "../../api/auth";
import useAuthStore from "../../store/authStore";
import toast from "react-hot-toast";

export default function AuthModal({ isOpen, onClose }) {
  const [mode, setMode] = useState("login"); // 'login' | 'register'
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    password: "",
    confirmPassword: "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const setAuth = useAuthStore((s) => s.setAuth);

  if (!isOpen) return null;

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    setError("");
  };

  const toggleMode = () => {
    setMode((m) => (m === "login" ? "register" : "login"));
    setFormData({ name: "", email: "", password: "", confirmPassword: "" });
    setError("");
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    const { name, email, password, confirmPassword } = formData;

    if (!email || !password) {
      setError("Please fill in all required fields.");
      return;
    }

    if (mode === "register") {
      if (!name) {
        setError("Please enter your name.");
        return;
      }
      if (password !== confirmPassword) {
        setError("Passwords do not match.");
        return;
      }
    }

    setLoading(true);
    try {
      if (mode === "login") {
        const { data } = await login(email, password);
        setAuth(data.user, data.token);
        toast.success(`Welcome back, ${data.user.name}!`);
        onClose();
      } else {
        const { data } = await register(name, email, password);
        setAuth(data.user, data.token);
        toast.success(`Account created! Welcome, ${data.user.name}!`);
        onClose();
      }
    } catch (err) {
      setError(err?.response?.data?.detail || "Authentication failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
        {/* Backdrop overlay */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="absolute inset-0 bg-primary/80 backdrop-blur-sm"
        />

        {/* Modal body */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 15 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 15 }}
          transition={{ duration: 0.25, ease: "easeOut" }}
          className="relative w-full max-w-[420px] bg-surface border border-white/[0.08] rounded-2xl p-6 shadow-2xl z-10 overflow-hidden"
        >
          {/* Close button */}
          <button
            onClick={onClose}
            className="absolute top-4 right-4 text-textSecondary hover:text-textPrimary transition-colors"
          >
            <X size={20} />
          </button>

          {/* Logo & Header */}
          <div className="flex flex-col items-center mb-6">
            <div className="w-10 h-10 rounded-xl bg-accent/20 flex items-center justify-center mb-2">
              <Scan size={22} className="text-accent" />
            </div>
            <h3 className="text-xl font-bold text-textPrimary">
              {mode === "login" ? "Welcome back" : "Create your account"}
            </h3>
            <p className="text-xs text-textSecondary mt-1 text-center">
              {mode === "login"
                ? "Sign in to persist reports and track historical bias analytics."
                : "Join ByUs to unlock your personalized analysis dashboard."}
            </p>
          </div>

          {/* Error Message */}
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -5 }}
              animate={{ opacity: 1, y: 0 }}
              className="mb-4 px-3 py-2 bg-danger/10 border border-danger/25 text-danger rounded-lg text-xs leading-relaxed"
            >
              {error}
            </motion.div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {mode === "register" && (
              <div>
                <label className="block text-[11px] font-bold text-textSecondary uppercase tracking-wider mb-1">
                  Full Name
                </label>
                <div className="relative">
                  <User size={16} className="absolute left-3 top-3 text-textSecondary" />
                  <input
                    type="text"
                    name="name"
                    value={formData.name}
                    onChange={handleInputChange}
                    placeholder="Enter name"
                    className="w-full bg-surfaceDark border border-white/10 rounded-xl py-2.5 pl-10 pr-4 text-sm text-textPrimary placeholder:text-textSecondary/50 focus:border-accent focus:ring-1 focus:ring-accent outline-none transition-all"
                  />
                </div>
              </div>
            )}

            <div>
              <label className="block text-[11px] font-bold text-textSecondary uppercase tracking-wider mb-1">
                Email Address
              </label>
              <div className="relative">
                <Mail size={16} className="absolute left-3 top-3 text-textSecondary" />
                <input
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleInputChange}
                  placeholder="name@email.com"
                  className="w-full bg-surfaceDark border border-white/10 rounded-xl py-2.5 pl-10 pr-4 text-sm text-textPrimary placeholder:text-textSecondary/50 focus:border-accent focus:ring-1 focus:ring-accent outline-none transition-all"
                />
              </div>
            </div>

            <div>
              <label className="block text-[11px] font-bold text-textSecondary uppercase tracking-wider mb-1">
                Password
              </label>
              <div className="relative">
                <Lock size={16} className="absolute left-3 top-3 text-textSecondary" />
                <input
                  type="password"
                  name="password"
                  value={formData.password}
                  onChange={handleInputChange}
                  placeholder="••••••••"
                  className="w-full bg-surfaceDark border border-white/10 rounded-xl py-2.5 pl-10 pr-4 text-sm text-textPrimary placeholder:text-textSecondary/50 focus:border-accent focus:ring-1 focus:ring-accent outline-none transition-all"
                />
              </div>
            </div>

            {mode === "register" && (
              <div>
                <label className="block text-[11px] font-bold text-textSecondary uppercase tracking-wider mb-1">
                  Confirm Password
                </label>
                <div className="relative">
                  <Lock size={16} className="absolute left-3 top-3 text-textSecondary" />
                  <input
                    type="password"
                    name="confirmPassword"
                    value={formData.confirmPassword}
                    onChange={handleInputChange}
                    placeholder="••••••••"
                    className="w-full bg-surfaceDark border border-white/10 rounded-xl py-2.5 pl-10 pr-4 text-sm text-textPrimary placeholder:text-textSecondary/50 focus:border-accent focus:ring-1 focus:ring-accent outline-none transition-all"
                  />
                </div>
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-accent hover:bg-accentLight text-primary font-semibold py-2.5 rounded-xl flex items-center justify-center gap-2 transition-all mt-6 cursor-default disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <Loader2 size={16} className="animate-spin" />
              ) : mode === "login" ? (
                "Sign In"
              ) : (
                "Create Account"
              )}
            </button>
          </form>

          {/* Toggle form mode */}
          <div className="mt-6 text-center text-xs">
            <button
              onClick={toggleMode}
              className="text-textSecondary hover:text-accent transition-colors"
            >
              {mode === "login" ? (
                <>
                  Don't have an account? <span className="text-accent font-semibold">Register</span>
                </>
              ) : (
                <>
                  Already have an account? <span className="text-accent font-semibold">Sign In</span>
                </>
              )}
            </button>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
