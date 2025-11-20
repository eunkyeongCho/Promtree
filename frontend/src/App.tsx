import { useState, useEffect } from 'react';
import { Sidebar } from './components/Sidebar';
import { Collections } from './components/Collections';
import { CollectionDetail } from './components/CollectionDetail';
import { Chat } from './components/Chat';
import { ThemeToggle } from './components/ThemeToggle';
import { ToastContainer } from './components/ToastContainer';
import { UploadProgress } from './components/UploadProgress';
import { useToast } from './hooks/useToast';
import { useUpload } from './hooks/useUpload';
import { getChats, updateChat, deleteChat, type Chat as ChatType, type Collection } from './lib/api';

function App() {
  const toast = useToast();
  const upload = useUpload();
  const [currentPage, setCurrentPage] = useState<'collections' | 'collection-detail' | 'chat'>('collections');
  const [darkMode, setDarkMode] = useState(false);
  const [chats, setChats] = useState<ChatType[]>([]);
  const [currentChatId, setCurrentChatId] = useState<string | null>(null);
  const [isLoadingChats, setIsLoadingChats] = useState(false);
  const [selectedCollection, setSelectedCollection] = useState<Collection | null>(null);

  // Check system preference on mount
  useEffect(() => {
    const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    setDarkMode(isDark);
    if (isDark) {
      document.documentElement.classList.add('dark');
    }
  }, []);

  // Load chats on mount
  useEffect(() => {
    loadChats();
  }, []);

  const loadChats = async () => {
    setIsLoadingChats(true);
    const result = await getChats('user_001'); // TODO: 실제 사용자 ID
    if (result.success && result.data) {
      setChats(result.data);
      // 첫 번째 채팅을 현재 채팅으로 설정
      if (result.data.length > 0 && !currentChatId) {
        setCurrentChatId(result.data[0].chatId);
      }
    }
    setIsLoadingChats(false);
  };

  const handleCreateChat = () => {
    // 새 채팅 화면으로 이동 (실제 채팅은 첫 메시지 전송 시 생성)
    setCurrentChatId(null);
    setCurrentPage('chat');
  };

  const handleSelectChat = (chatId: string) => {
    setCurrentChatId(chatId);
    setCurrentPage('chat');
  };

  const handleSelectCollection = (collection: Collection) => {
    setSelectedCollection(collection);
    setCurrentPage('collection-detail');
  };

  const handleBackToCollections = () => {
    setSelectedCollection(null);
    setCurrentPage('collections');
  };

  const handleUpdateChat = async (chatId: string, title: string) => {
    const result = await updateChat(chatId, { title });
    if (result.success) {
      toast.success('채팅 제목이 수정되었습니다');
      loadChats();
    } else {
      toast.error('채팅 제목 수정 실패: ' + result.error);
    }
  };

  const handleDeleteChat = async (chatId: string) => {
    const result = await deleteChat(chatId);
    if (result.success) {
      toast.success('채팅이 삭제되었습니다');
      if (currentChatId === chatId) {
        setCurrentChatId(null);
      }
      loadChats();
    } else {
      toast.error('채팅 삭제 실패: ' + result.error);
    }
  };

  const toggleDarkMode = () => {
    setDarkMode(!darkMode);
    document.documentElement.classList.toggle('dark');
  };

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar
        currentPage={currentPage === 'collection-detail' ? 'collections' : currentPage}
        onNavigate={(page) => {
          if (page === 'collections') {
            handleBackToCollections();
          } else {
            setCurrentPage(page);
          }
        }}
        chats={chats}
        currentChatId={currentChatId}
        onCreateChat={handleCreateChat}
        onSelectChat={handleSelectChat}
        onUpdateChat={handleUpdateChat}
        onDeleteChat={handleDeleteChat}
        isLoadingChats={isLoadingChats}
      />
      <main className="flex-1 overflow-hidden">
        {currentPage === 'collections' ? (
          <Collections onSelectCollection={handleSelectCollection} toast={toast} upload={upload} />
        ) : currentPage === 'collection-detail' && selectedCollection ? (
          <CollectionDetail
            collection={selectedCollection}
            onBack={handleBackToCollections}
            onUpdate={loadChats}
            toast={toast}
            upload={upload}
          />
        ) : (
          <Chat chatId={currentChatId} onChatCreated={loadChats} />
        )}
      </main>
      <ThemeToggle darkMode={darkMode} onToggle={toggleDarkMode} />
      <ToastContainer toasts={toast.toasts} onClose={toast.removeToast} />
      <UploadProgress uploads={upload.uploads} onClose={upload.removeUpload} />
    </div>
  );
}

export default App;
