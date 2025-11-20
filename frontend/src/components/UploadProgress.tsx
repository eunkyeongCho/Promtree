import { X, File, CheckCircle, XCircle } from "lucide-react";

export interface UploadItem {
  id: string;
  filename: string;
  progress: number; // 0-100
  status: "uploading" | "success" | "error";
  error?: string;
}

interface UploadProgressProps {
  uploads: UploadItem[];
  onCancel?: (id: string) => void;
  onClose: (id: string) => void;
}

export function UploadProgress({ uploads, onCancel, onClose }: UploadProgressProps) {
  if (uploads.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50 w-96 max-h-96 overflow-y-auto">
      <div className="bg-background border border-border rounded-lg shadow-lg">
        <div className="p-4 border-b border-border flex items-center justify-between">
          <h3 className="font-semibold text-sm">파일 업로드</h3>
          <span className="text-xs text-muted-foreground">
            {uploads.filter(u => u.status === "uploading").length} / {uploads.length}
          </span>
        </div>
        <div className="divide-y divide-border max-h-80 overflow-y-auto">
          {uploads.map((upload) => (
            <div key={upload.id} className="p-4">
              <div className="flex items-start gap-3">
                <div className="flex-shrink-0 mt-1">
                  {upload.status === "uploading" && (
                    <File className="h-5 w-5 text-blue-500 animate-pulse" />
                  )}
                  {upload.status === "success" && (
                    <CheckCircle className="h-5 w-5 text-green-500" />
                  )}
                  {upload.status === "error" && (
                    <XCircle className="h-5 w-5 text-red-500" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-foreground truncate">
                    {upload.filename}
                  </p>
                  {upload.status === "uploading" && (
                    <div className="mt-2">
                      <div className="flex items-center justify-between text-xs text-muted-foreground mb-1">
                        <span>업로드 중...</span>
                        <span>{upload.progress}%</span>
                      </div>
                      <div className="w-full bg-muted rounded-full h-2">
                        <div
                          className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                          style={{ width: `${upload.progress}%` }}
                        />
                      </div>
                    </div>
                  )}
                  {upload.status === "success" && (
                    <p className="text-xs text-green-600 mt-1">업로드 완료</p>
                  )}
                  {upload.status === "error" && (
                    <p className="text-xs text-red-600 mt-1">
                      {upload.error || "업로드 실패"}
                    </p>
                  )}
                </div>
                <button
                  onClick={() => {
                    if (upload.status === "uploading" && onCancel) {
                      onCancel(upload.id);
                    } else {
                      onClose(upload.id);
                    }
                  }}
                  className="flex-shrink-0 rounded p-1 hover:bg-accent transition-colors"
                  aria-label={upload.status === "uploading" ? "취소" : "닫기"}
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
