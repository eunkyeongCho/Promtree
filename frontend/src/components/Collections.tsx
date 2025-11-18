import { Plus, Search, Upload } from "lucide-react";
import { useState, useEffect } from "react";
import {
  getCollections,
  createCollection,
  uploadDocuments,
  searchCollections,
  type Collection,
} from "../lib/api";
import type { useToast } from "../hooks/useToast";
import type { useUpload } from "../hooks/useUpload";

interface CollectionsProps {
  onSelectCollection?: (collection: Collection) => void;
  toast: ReturnType<typeof useToast>;
  upload: ReturnType<typeof useUpload>;
}

export function Collections({ onSelectCollection, toast, upload }: CollectionsProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [collections, setCollections] = useState<Collection[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newCollectionName, setNewCollectionName] = useState("");
  const [newCollectionDesc, setNewCollectionDesc] = useState("");

  useEffect(() => {
    loadCollections();
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      loadCollections();
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  const loadCollections = async () => {
    setIsLoading(true);
    let result;

    if (searchQuery.trim()) {
      result = await searchCollections(searchQuery, "user_001");
    } else {
      result = await getCollections("user_001");
    }

    if (result.success && result.data) {
      setCollections(result.data);
    }
    setIsLoading(false);
  };

  const handleCreateCollection = async () => {
    if (!newCollectionName.trim()) return;

    const result = await createCollection({
      userId: "user_001",
      name: newCollectionName,
      description: newCollectionDesc,
    });

    if (result.success) {
      setShowCreateModal(false);
      setNewCollectionName("");
      setNewCollectionDesc("");
      loadCollections();
    }
  };

  const handleFileUpload = async (collectionId: string, files: FileList) => {
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

    const result = await uploadDocuments(collectionId, fileArray);

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
      loadCollections();
    } else {
      toast.error("파일 업로드 실패: " + result.error);
    }
  };

  return (
    <div className="flex h-screen flex-col bg-background">
      {/* Header */}
      <header className="flex h-16 items-center justify-between border-b border-border px-6">
        <div className="flex items-center gap-4">
          <h1 className="text-lg font-semibold text-foreground">지식 저장소</h1>
        </div>
        <div className="flex items-center gap-3">
          <button className="rounded-md p-2 hover:bg-accent">
            <span className="sr-only">Help</span>
            <svg
              className="h-5 w-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <circle cx="12" cy="12" r="10" strokeWidth="2" />
              <path strokeWidth="2" d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
              <circle cx="12" cy="17" r=".5" fill="currentColor" />
            </svg>
          </button>
          <button className="rounded-md p-2 hover:bg-accent">
            <span className="sr-only">Language</span>
            <svg
              className="h-5 w-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <circle cx="12" cy="12" r="10" strokeWidth="2" />
              <line x1="2" y1="12" x2="22" y2="12" strokeWidth="2" />
              <path
                strokeWidth="2"
                d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"
              />
            </svg>
          </button>
        </div>
      </header>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-6 py-8">
        <div className="mx-auto max-w-6xl">
          <h2 className="mb-2 text-3xl font-bold text-foreground">PDFs</h2>
          <p className="mb-8 text-muted-foreground">
            이 데이터는 공용으로 모두 접근 가능합니다.
          </p>

          {/* Search and Add Button */}
          <div className="mb-6 flex items-center gap-4">
            <div className="relative flex-1 max-w-sm">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <input
                type="text"
                placeholder="Search"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="h-10 w-full rounded-md border border-input bg-background pl-10 pr-4 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>
            <button
              onClick={() => setShowCreateModal(true)}
              className="flex h-10 items-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground hover:bg-primary/90"
            >
              <Plus className="h-4 w-4" />
              PDF 추가
            </button>
          </div>

          {/* Collections Grid */}
          {isLoading ? (
            <div className="flex min-h-[400px] items-center justify-center">
              <p className="text-muted-foreground">Loading...</p>
            </div>
          ) : collections.length === 0 ? (
            <div className="flex min-h-[400px] items-center justify-center rounded-lg border border-border">
              <div className="text-center">
                <p className="text-muted-foreground">
                  검색 조건에 맞는 자료가 없습니다.
                </p>
              </div>
            </div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {collections.map((collection) => (
                <div
                  key={collection.collectionId}
                  className="rounded-lg border border-border bg-card p-4 hover:border-ring transition-colors cursor-pointer"
                  onClick={() => onSelectCollection?.(collection)}
                >
                  <h3 className="font-semibold text-foreground mb-2">
                    {collection.name}
                  </h3>
                  <p className="text-sm text-muted-foreground mb-4 line-clamp-2">
                    {collection.description || "No description"}
                  </p>
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span>{collection.documentCount} documents</span>
                    <label
                      className="cursor-pointer hover:text-primary"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <Upload className="h-4 w-4 inline mr-1" />
                      Upload
                      <input
                        type="file"
                        multiple
                        accept=".pdf"
                        className="hidden"
                        onChange={(e) => {
                          if (e.target.files) {
                            handleFileUpload(
                              collection.collectionId,
                              e.target.files
                            );
                          }
                        }}
                      />
                    </label>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Create Collection Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-background rounded-lg p-6 w-full max-w-md border border-border">
            <h2 className="text-xl font-semibold mb-4">Create Collection</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">Name</label>
                <input
                  type="text"
                  value={newCollectionName}
                  onChange={(e) => setNewCollectionName(e.target.value)}
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  placeholder="Enter collection name"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">
                  Description
                </label>
                <textarea
                  value={newCollectionDesc}
                  onChange={(e) => setNewCollectionDesc(e.target.value)}
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  rows={3}
                  placeholder="Enter description (optional)"
                />
              </div>
              <div className="flex gap-3 justify-end">
                <button
                  onClick={() => {
                    setShowCreateModal(false);
                    setNewCollectionName("");
                    setNewCollectionDesc("");
                  }}
                  className="px-4 py-2 rounded-md border border-input hover:bg-accent"
                >
                  Cancel
                </button>
                <button
                  onClick={handleCreateCollection}
                  className="px-4 py-2 rounded-md bg-primary text-primary-foreground hover:bg-primary/90"
                >
                  Create
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
