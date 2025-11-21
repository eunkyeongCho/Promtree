import { useState, useCallback } from "react";
import type { UploadItem } from "../components/UploadProgress";

export function useUpload() {
  const [uploads, setUploads] = useState<UploadItem[]>([]);

  const addUpload = useCallback((filename: string) => {
    const id = `upload-${Date.now()}-${Math.random()}`;
    const newUpload: UploadItem = {
      id,
      filename,
      progress: 0,
      status: "uploading",
    };
    setUploads((prev) => [...prev, newUpload]);
    return id;
  }, []);

  const updateProgress = useCallback((id: string, progress: number) => {
    setUploads((prev) =>
      prev.map((upload) =>
        upload.id === id ? { ...upload, progress } : upload
      )
    );
  }, []);

  const setSuccess = useCallback((id: string) => {
    setUploads((prev) =>
      prev.map((upload) =>
        upload.id === id
          ? { ...upload, status: "success" as const, progress: 100 }
          : upload
      )
    );
  }, []);

  const setError = useCallback((id: string, error: string) => {
    setUploads((prev) =>
      prev.map((upload) =>
        upload.id === id
          ? { ...upload, status: "error" as const, error }
          : upload
      )
    );
  }, []);

  const removeUpload = useCallback((id: string) => {
    setUploads((prev) => prev.filter((upload) => upload.id !== id));
  }, []);

  const clearCompleted = useCallback(() => {
    setUploads((prev) =>
      prev.filter((upload) => upload.status === "uploading")
    );
  }, []);

  return {
    uploads,
    addUpload,
    updateProgress,
    setSuccess,
    setError,
    removeUpload,
    clearCompleted,
  };
}
