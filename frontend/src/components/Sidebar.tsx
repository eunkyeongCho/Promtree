import {
  BookOpen,
  MessageSquare,
  Plus,
  Settings,
  User,
  MoreVertical,
  Edit2,
  Trash2,
} from "lucide-react";
import { cn } from "../lib/utils";
import type { Chat } from "../lib/api";
import { useState } from "react";

interface SidebarProps {
  currentPage: "collections" | "chat";
  onNavigate: (page: "collections" | "chat") => void;
  chats: Chat[];
  currentChatId: string | null;
  onCreateChat: () => void;
  onSelectChat: (chatId: string) => void;
  onUpdateChat?: (chatId: string, title: string) => void;
  onDeleteChat?: (chatId: string) => void;
  isLoadingChats: boolean;
}

export function Sidebar({
  currentPage,
  onNavigate,
  chats,
  currentChatId,
  onCreateChat,
  onSelectChat,
  onUpdateChat,
  onDeleteChat,
  isLoadingChats,
}: SidebarProps) {
  const [editingChatId, setEditingChatId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [showMenuChatId, setShowMenuChatId] = useState<string | null>(null);

  const handleEditClick = (chat: Chat, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingChatId(chat.chatId);
    setEditTitle(chat.title || "");
    setShowMenuChatId(null);
  };

  const handleSaveEdit = (chatId: string) => {
    if (editTitle.trim() && onUpdateChat) {
      onUpdateChat(chatId, editTitle.trim());
    }
    setEditingChatId(null);
  };

  const handleDeleteClick = (chatId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (confirm("이 채팅을 삭제하시겠습니까?") && onDeleteChat) {
      onDeleteChat(chatId);
    }
    setShowMenuChatId(null);
  };

  return (
    <div className="flex h-screen w-60 flex-col border-r border-sidebar-border bg-sidebar">
      {/* Logo */}
      <div className="flex h-16 items-center gap-3 border-b border-sidebar-border px-4">
        <img
          src="/assets/promtree_dark.svg"
          alt="PROMTREE"
          className="h-6 dark:block hidden"
        />
        <img
          src="/assets/promtree_color.svg"
          alt="PROMTREE"
          className="h-6 dark:hidden block"
        />
      </div>

      {/* Navigation */}
      <div className="flex-1 overflow-y-auto">
        {/* Repositories Section */}
        <div className="px-3 py-3">
          <div className="mb-2 px-3 text-xs font-medium text-sidebar-foreground/60">
            레포지토리
          </div>
          <nav className="space-y-1">
            <button
              onClick={() => onNavigate("collections")}
              className={cn(
                "flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
                currentPage === "collections"
                  ? "bg-sidebar-accent text-sidebar-accent-foreground font-medium"
                  : "text-sidebar-foreground hover:bg-sidebar-accent/50"
              )}
            >
              <BookOpen className="h-4 w-4" />
              지식 베이스
            </button>
          </nav>
        </div>

        {/* Chats Section */}
        <div className="px-3 py-3">
          <div className="mb-2 flex items-center justify-between px-3">
            <span className="text-xs font-medium text-sidebar-foreground/60">
              채팅
            </span>
            <button
              onClick={onCreateChat}
              className="rounded-md p-1 hover:bg-sidebar-accent/50"
              title="새 채팅"
            >
              <Plus className="h-3.5 w-3.5 text-sidebar-foreground/60" />
            </button>
          </div>
          <nav className="space-y-1">
            {isLoadingChats ? (
              <div className="px-3 py-2 text-sm text-sidebar-foreground/60">
                로딩 중...
              </div>
            ) : chats.length === 0 ? (
              <div className="px-3 py-2 text-sm text-sidebar-foreground/60">
                채팅이 없습니다
              </div>
            ) : (
              chats.map((chat) => (
                <div
                  key={chat.chatId}
                  className={cn(
                    "group relative flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors",
                    currentChatId === chat.chatId
                      ? "bg-sidebar-accent text-sidebar-accent-foreground font-medium"
                      : "text-sidebar-foreground hover:bg-sidebar-accent/50"
                  )}
                >
                  {editingChatId === chat.chatId ? (
                    <div className="flex flex-1 items-center gap-2">
                      <MessageSquare className="h-4 w-4 flex-shrink-0" />
                      <input
                        type="text"
                        value={editTitle}
                        onChange={(e) => setEditTitle(e.target.value)}
                        onBlur={() => handleSaveEdit(chat.chatId)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") handleSaveEdit(chat.chatId);
                          if (e.key === "Escape") setEditingChatId(null);
                        }}
                        className="flex-1 bg-transparent border-b border-sidebar-foreground/30 focus:outline-none focus:border-sidebar-foreground"
                        autoFocus
                      />
                    </div>
                  ) : (
                    <>
                      <button
                        onClick={() => onSelectChat(chat.chatId)}
                        className="flex flex-1 items-center gap-3 text-left"
                      >
                        <MessageSquare className="h-4 w-4 flex-shrink-0" />
                        <span className="truncate">
                          {chat.title || "새로운 채팅"}
                        </span>
                      </button>
                      <div className="relative">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setShowMenuChatId(
                              showMenuChatId === chat.chatId
                                ? null
                                : chat.chatId
                            );
                          }}
                          className="opacity-0 group-hover:opacity-100 p-1 hover:bg-sidebar-accent/50 rounded"
                        >
                          <MoreVertical className="h-3.5 w-3.5" />
                        </button>
                        {showMenuChatId === chat.chatId && (
                          <div className="absolute right-0 mt-1 w-32 bg-background border border-border rounded-md shadow-lg z-10">
                            <button
                              onClick={(e) => handleEditClick(chat, e)}
                              className="flex w-full items-center gap-2 px-3 py-2 text-xs hover:bg-accent"
                            >
                              <Edit2 className="h-3 w-3" />
                              편집
                            </button>
                            <button
                              onClick={(e) => handleDeleteClick(chat.chatId, e)}
                              className="flex w-full items-center gap-2 px-3 py-2 text-xs text-destructive hover:bg-destructive/10"
                            >
                              <Trash2 className="h-3 w-3" />
                              삭제
                            </button>
                          </div>
                        )}
                      </div>
                    </>
                  )}
                </div>
              ))
            )}
          </nav>
        </div>
      </div>

      {/* Footer */}
      <div className="border-t border-sidebar-border p-3">
        <div className="mb-2 px-3">
          {/* <span className="text-xs font-medium text-sidebar-foreground/60">
            더보기
          </span> */}
        </div>
        <nav className="space-y-1">
          <button className="flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm text-sidebar-foreground hover:bg-sidebar-accent/50">
            <Settings className="h-4 w-4" />
            설정
          </button>
        </nav>

        {/* User Profile */}
        <div className="mt-3 flex items-center gap-3 rounded-md border border-sidebar-border bg-sidebar-accent/30 px-3 py-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-sidebar-primary text-sidebar-primary-foreground">
            <User className="h-4 w-4" />
          </div>
          <div className="flex-1 overflow-hidden">
            <div className="truncate text-sm font-medium text-sidebar-foreground">
              rhgdwkdy
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
