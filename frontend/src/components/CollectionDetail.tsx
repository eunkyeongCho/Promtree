import { ArrowLeft, Trash2, Upload, Edit2, X } from "lucide-react";
import { useState, useEffect } from "react";
import {
  getDocuments,
  deleteDocument,
  uploadDocuments,
  updateCollection,
  deleteCollection,
  type Document,
  type Collection,
} from "../lib/api";
import type { useToast } from "../hooks/useToast";
import type { useUpload } from "../hooks/useUpload";

interface CollectionDetailProps {
  collection: Collection;
  onBack: () => void;
  onUpdate: () => void;
  toast: ReturnType<typeof useToast>;
  upload: ReturnType<typeof useUpload>;
}

export function CollectionDetail({
  collection,
  onBack,
  onUpdate,
  toast,
  upload,
}: CollectionDetailProps) {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [editName, setEditName] = useState(collection.name);
  const [editDescription, setEditDescription] = useState(
    collection.description || ""
  );

  useEffect(() => {
    loadDocuments();
  }, [collection.collectionId]);

  const loadDocuments = async () => {
    setIsLoading(true);
    const result = await getDocuments(collection.collectionId);
    if (result.success && result.data) {
      setDocuments(result.data);
    }
    setIsLoading(false);
  };

  const handleDeleteDocument = async (documentId: string) => {
    if (!confirm("이 문서를 삭제하시겠습니까?")) return;

    const result = await deleteDocument(documentId);
    if (result.success) {
      toast.success("문서가 삭제되었습니다");
      loadDocuments();
      onUpdate(); // 컬렉션 목록 새로고침
    } else {
      toast.error("문서 삭제 실패" + (result.error ? ": " + result.error : ""));
    }
  };

  const handleFileUpload = async (files: FileList) => {
    const fileArray = Array.from(files);

    // 각 파일별로 업로드 진행 상태 추가
    const uploadIds = fileArray.map(file => upload.addUpload(file.name));

    // 실제 업로드 (진행률 시뮬레이션)
    fileArray.forEach((_file, index) => {
      const uploadId = uploadIds[index];
      // 진행률 시뮬레이션
      let progress = 0;
      const interval = setInterval(() => {
        progress += 10;
        upload.updateProgress(uploadId, Math.min(progress, 90));
        if (progress >= 90) clearInterval(interval);
      }, 200);
    });

    const result = await uploadDocuments(collection.collectionId, fileArray);

    // 업로드 완료 처리
    uploadIds.forEach(uploadId => {
      if (result.success) {
        upload.setSuccess(uploadId);
        setTimeout(() => upload.removeUpload(uploadId), 3000); // 3초 후 자동 제거
      } else {
        upload.setError(uploadId, result.error || "업로드 실패");
      }
    });

    if (result.success) {
      toast.success("파일 업로드 성공!");
      loadDocuments();
      onUpdate(); // 컬렉션 목록 새로고침
    } else {
      toast.error("파일 업로드 실패: " + result.error);
    }
  };

  const handleUpdateCollection = async () => {
    if (!editName.trim()) {
      toast.warning("컬렉션 이름을 입력하세요");
      return;
    }

    const result = await updateCollection(collection.collectionId, {
      name: editName,
      description: editDescription,
    });

    if (result.success) {
      toast.success("컬렉션이 수정되었습니다");
      setShowEditModal(false);
      onUpdate(); // 컬렉션 목록 새로고침
      onBack(); // 목록으로 돌아가기
    } else {
      toast.error("컬렉션 수정 실패: " + result.error);
    }
  };

  const handleDeleteCollection = async () => {
    if (
      !confirm(
        "이 컬렉션과 모든 문서를 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다."
      )
    )
      return;

    const result = await deleteCollection(collection.collectionId);
    if (result.success) {
      toast.success("컬렉션이 삭제되었습니다");
      onUpdate(); // 컬렉션 목록 새로고침
      onBack(); // 목록으로 돌아가기
    } else {
      toast.error("컬렉션 삭제 실패: " + result.error);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + " " + sizes[i];
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString("ko-KR", {
      year: "numeric",
      month: "long",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <div className="flex h-screen flex-col bg-background">
      {/* Header */}
      <header className="flex h-16 items-center justify-between border-b border-border px-6">
        <div className="flex items-center gap-4">
          <button
            onClick={onBack}
            className="rounded-md p-2 hover:bg-accent"
            title="뒤로 가기"
          >
            <ArrowLeft className="h-5 w-5" />
          </button>
          <h1 className="text-lg font-semibold text-foreground">
            {collection.name}
          </h1>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowEditModal(true)}
            className="flex h-10 items-center gap-2 rounded-md border border-input px-4 text-sm font-medium hover:bg-accent"
          >
            <Edit2 className="h-4 w-4" />
            편집
          </button>
          <button
            onClick={handleDeleteCollection}
            className="flex h-10 items-center gap-2 rounded-md border border-destructive px-4 text-sm font-medium text-destructive hover:bg-destructive/10"
          >
            <Trash2 className="h-4 w-4" />
            삭제
          </button>
          <label className="flex h-10 items-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground hover:bg-primary/90 cursor-pointer">
            <Upload className="h-4 w-4" />
            PDF 업로드
            <input
              type="file"
              multiple
              accept=".pdf"
              className="hidden"
              onChange={(e) => {
                if (e.target.files) {
                  handleFileUpload(e.target.files);
                }
              }}
            />
          </label>
        </div>
      </header>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-6 py-8">
        <div className="mx-auto max-w-6xl">
          <div className="mb-6">
            <h2 className="text-2xl font-bold text-foreground mb-2">
              문서 목록
            </h2>
            {collection.description && (
              <p className="text-muted-foreground">{collection.description}</p>
            )}
            <p className="text-sm text-muted-foreground mt-2">
              총 {documents.length}개의 문서
            </p>
          </div>

          {/* Documents List */}
          {isLoading ? (
            <div className="flex min-h-[400px] items-center justify-center">
              <p className="text-muted-foreground">Loading...</p>
            </div>
          ) : documents.length === 0 ? (
            <div className="flex min-h-[400px] items-center justify-center rounded-lg border border-border">
              <div className="text-center">
                <p className="text-muted-foreground">문서가 없습니다</p>
                <p className="text-sm text-muted-foreground mt-2">
                  상단의 "PDF 업로드" 버튼을 눌러 문서를 추가하세요
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              {documents.map((doc) => (
                <div
                  key={doc.documentId}
                  className="flex items-center justify-between rounded-lg border border-border bg-card p-4 hover:border-ring transition-colors"
                >
                  <div className="flex-1">
                    <h3 className="font-medium text-foreground mb-1">
                      {doc.filename}
                    </h3>
                    <div className="flex items-center gap-4 text-xs text-muted-foreground">
                      <span>{formatFileSize(doc.size)}</span>
                      <span>{formatDate(doc.uploadedAt)}</span>
                      {doc.status && (
                        <span
                          className={`px-2 py-0.5 rounded-full ${
                            doc.status === "completed"
                              ? "bg-green-500/10 text-green-500"
                              : doc.status === "processing"
                              ? "bg-yellow-500/10 text-yellow-500"
                              : "bg-red-500/10 text-red-500"
                          }`}
                        >
                          {doc.status === "completed"
                            ? "처리 완료"
                            : doc.status === "processing"
                            ? "처리 중"
                            : "실패"}
                        </span>
                      )}
                    </div>
                  </div>
                  <button
                    onClick={() => handleDeleteDocument(doc.documentId)}
                    className="rounded-md p-2 hover:bg-destructive/10 hover:text-destructive"
                    title="문서 삭제"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Edit Collection Modal */}
      {showEditModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-background rounded-lg p-6 w-full max-w-md border border-border">
            <h2 className="text-xl font-semibold mb-4">컬렉션 편집</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">이름</label>
                <input
                  type="text"
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  placeholder="컬렉션 이름"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">설명</label>
                <textarea
                  value={editDescription}
                  onChange={(e) => setEditDescription(e.target.value)}
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  rows={3}
                  placeholder="설명 (선택사항)"
                />
              </div>
              <div className="flex gap-3 justify-end">
                <button
                  onClick={() => {
                    setShowEditModal(false);
                    setEditName(collection.name);
                    setEditDescription(collection.description || "");
                  }}
                  className="px-4 py-2 rounded-md border border-input hover:bg-accent"
                >
                  취소
                </button>
                <button
                  onClick={handleUpdateCollection}
                  className="px-4 py-2 rounded-md bg-primary text-primary-foreground hover:bg-primary/90"
                >
                  저장
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
