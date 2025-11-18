import { useState, useCallback } from "react";
import type { ToastType } from "../components/Toast";

export interface ToastItem {
  id: string;
  type: ToastType;
  message: string;
  duration?: number;
}

export function useToast() {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const addToast = useCallback((type: ToastType, message: string, duration?: number) => {
    const id = `toast-${Date.now()}-${Math.random()}`;
    setToasts((prev) => [...prev, { id, type, message, duration }]);
    return id;
  }, []);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  }, []);

  const success = useCallback((message: string, duration?: number) => {
    return addToast("success", message, duration);
  }, [addToast]);

  const error = useCallback((message: string, duration?: number) => {
    return addToast("error", message, duration);
  }, [addToast]);

  const warning = useCallback((message: string, duration?: number) => {
    return addToast("warning", message, duration);
  }, [addToast]);

  const info = useCallback((message: string, duration?: number) => {
    return addToast("info", message, duration);
  }, [addToast]);

  return {
    toasts,
    addToast,
    removeToast,
    success,
    error,
    warning,
    info,
  };
}
