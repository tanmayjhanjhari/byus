import React from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { motion } from "framer-motion";

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    // Update state so the next render will show the fallback UI.
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    // You can also log the error to an error reporting service
    console.error("ErrorBoundary caught an error", error, errorInfo);
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null });
    // In a real app, you might also want to clear store errors
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center min-h-[400px] p-6 text-center animate-in fade-in zoom-in duration-300">
          <div className="w-16 h-16 rounded-full bg-danger/20 flex items-center justify-center mb-6 border border-danger/30">
            <AlertTriangle size={32} className="text-danger" />
          </div>
          <h2 className="text-2xl font-bold text-textPrimary mb-2">Something went wrong</h2>
          <p className="text-textSecondary mb-8 max-w-md">
            The application encountered an unexpected error while rendering this page. 
            We apologize for the inconvenience.
          </p>
          
          <button 
            onClick={this.handleRetry}
            className="btn-primary flex items-center gap-2"
          >
            <RefreshCw size={18} />
            Reload Page
          </button>
        </div>
      );
    }

    return this.props.children; 
  }
}

export default ErrorBoundary;
