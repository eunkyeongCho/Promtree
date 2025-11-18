import { X, CheckCircle, XCircle, AlertCircle, Info } from "lucide-react";
import { useEffect } from "react";

export type ToastType = "success" | "error" | "warning" | "info";

export interface ToastProps {
  id: string;
  type: ToastType;
  message: string;
  onClose: (id: string) => void;
  duration?: number;
}

export function Toast({ id, type, message, onClose, duration = 3000 }: ToastProps) {
  useEffect(() => {
    if (duration > 0) {
      const timer = setTimeout(() => {
        onClose(id);
      }, duration);
      return () => clearTimeout(timer);
    }
  }, [id, duration, onClose]);

  const icons = {
    success: <CheckCircle className="h-5 w-5" />,
    error: <XCircle className="h-5 w-5" />,
    warning: <AlertCircle className="h-5 w-5" />,
    info: <Info className="h-5 w-5" />,
  };

  const styles = {
    success: "bg-green-500/10 border-green-500/50 text-green-500",
    error: "bg-red-500/10 border-red-500/50 text-red-500",
    warning: "bg-yellow-500/10 border-yellow-500/50 text-yellow-500",
    info: "bg-blue-500/10 border-blue-500/50 text-blue-500",
  };

  return (
    <div
      className={`flex items-center gap-3 rounded-lg border px-4 py-3 shadow-lg backdrop-blur-sm animate-in slide-in-from-right ${styles[type]}`}
      role="alert"
    >
      {icons[type]}
      <p className="flex-1 text-sm font-medium text-foreground">{message}</p>
      <button
        onClick={() => onClose(id)}
        className="rounded p-1 hover:bg-background/50 transition-colors"
        aria-label="닫기"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}
