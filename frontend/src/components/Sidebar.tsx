import {
  BookOpen,
  MessageSquare,
  Plus,
  Settings,
  User,
  MoreVertical,
  Edit2,
  Trash2,
  LogOut,
} from "lucide-react";
import { cn } from "../lib/utils";
import type { Chat } from "../lib/api";
import { useState } from "react";

interface SidebarProps {
  currentPage: "collections" | "chat" | "mindmap";
  onNavigate: (page: "collections" | "chat" | "mindmap") => void;
  chats: Chat[];
  currentChatId: string | null;
  onCreateChat: () => void;
  onSelectChat: (chatId: string) => void;
  onUpdateChat?: (chatId: string, title: string) => void;
  onDeleteChat?: (chatId: string) => void;
  isLoadingChats: boolean;
  onLogout?: () => void;
  userId?: string;
}

export function Sidebar({
  currentPage,
  onNavigate,
  chats,
  onLogout,
  currentChatId,
  onCreateChat,
  onSelectChat,
  onUpdateChat,
  onDeleteChat,
  isLoadingChats,
  userId,
}: SidebarProps) {
  const [editingChatId, setEditingChatId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [showMenuChatId, setShowMenuChatId] = useState<string | null>(null);

  const handleEditClick = (chat: Chat, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingChatId(chat.chat_id);
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
            <button
              onClick={() => onNavigate("mindmap")}
              className={cn(
                "flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
                currentPage === "mindmap"
                  ? "bg-sidebar-accent text-sidebar-accent-foreground font-medium"
                  : "text-sidebar-foreground hover:bg-sidebar-accent/50"
              )}
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <circle cx="12" cy="12" r="3" />
                <circle cx="6" cy="6" r="2" />
                <circle cx="18" cy="6" r="2" />
                <circle cx="6" cy="18" r="2" />
                <circle cx="18" cy="18" r="2" />
                <path d="M9.5 8.5L10 10M14.5 8.5L14 10M9.5 15.5L10 14M14.5 15.5L14 14" strokeWidth="2"/>
              </svg>
              Knowledge Graph
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
                  key={chat.chat_id}
                  className={cn(
                    "group relative flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors",
                    currentChatId === chat.chat_id
                      ? "bg-sidebar-accent text-sidebar-accent-foreground font-medium"
                      : "text-sidebar-foreground hover:bg-sidebar-accent/50"
                  )}
                >
                  {editingChatId === chat.chat_id ? (
                    <div className="flex flex-1 items-center gap-2">
                      <MessageSquare className="h-4 w-4 flex-shrink-0" />
                      <input
                        type="text"
                        value={editTitle}
                        onChange={(e) => setEditTitle(e.target.value)}
                        onBlur={() => handleSaveEdit(chat.chat_id)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") handleSaveEdit(chat.chat_id);
                          if (e.key === "Escape") setEditingChatId(null);
                        }}
                        className="flex-1 bg-transparent border-b border-sidebar-foreground/30 focus:outline-none focus:border-sidebar-foreground"
                        autoFocus
                      />
                    </div>
                  ) : (
                    <>
                      <button
                        onClick={() => onSelectChat(chat.chat_id)}
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
                              showMenuChatId === chat.chat_id
                                ? null
                                : chat.chat_id
                            );
                          }}
                          className="opacity-0 group-hover:opacity-100 p-1 hover:bg-sidebar-accent/50 rounded"
                        >
                          <MoreVertical className="h-3.5 w-3.5" />
                        </button>
                        {showMenuChatId === chat.chat_id && (
                          <div className="absolute right-0 mt-1 w-32 bg-background border border-border rounded-md shadow-lg z-10">
                            <button
                              onClick={(e) => handleEditClick(chat, e)}
                              className="flex w-full items-center gap-2 px-3 py-2 text-xs hover:bg-accent"
                            >
                              <Edit2 className="h-3 w-3" />
                              편집
                            </button>
                            <button
                              onClick={(e) => handleDeleteClick(chat.chat_id, e)}
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
          {onLogout && (
            <button
              onClick={onLogout}
              className="flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm text-sidebar-foreground hover:bg-sidebar-accent/50"
            >
              <LogOut className="h-4 w-4" />
              로그아웃
            </button>
          )}
        </nav>

        {/* User Profile */}
        <div className="mt-3 flex items-center gap-3 rounded-md border border-sidebar-border bg-sidebar-accent/30 px-3 py-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-sidebar-primary text-sidebar-primary-foreground">
            <User className="h-4 w-4" />
          </div>
          <div className="flex-1 overflow-hidden">
            <div className="truncate text-sm font-medium text-sidebar-foreground">
              {userId || 'Guest'}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
