import { useState, useEffect } from 'react';
import { Sidebar } from './components/Sidebar';
import { Collections } from './components/Collections';
import { CollectionDetail } from './components/CollectionDetail';
import { Chat } from './components/Chat';
import { MindMap } from './components/MindMap';
import { Login } from './components/Login';
import { LandingPage } from './components/LandingPage';
import { ThemeToggle } from './components/ThemeToggle';
import { ToastContainer } from './components/ToastContainer';
import { UploadProgress } from './components/UploadProgress';
import { useToast } from './hooks/useToast';
import { useUpload } from './hooks/useUpload';
import { getChats, createChat, updateChat, deleteChat, getUserInfo, type Chat as ChatType, type Collection } from './lib/api';
import { getToken, removeToken } from './lib/auth';

function App() {
  const toast = useToast();
  const upload = useUpload();
  const [userEmail, setUserEmail] = useState<string | null>(() => {
    const token = getToken();
    return token ? localStorage.getItem('userEmail') : null;
  });
  const [showLogin, setShowLogin] = useState(false);
  const [isSignupMode, setIsSignupMode] = useState(false);
  const [currentPage, setCurrentPage] = useState<'collections' | 'collection-detail' | 'chat' | 'mindmap'>('collections');
  const [darkMode, setDarkMode] = useState(false);
  const [chats, setChats] = useState<ChatType[]>([]);
  const [currentChatId, setCurrentChatId] = useState<string | null>(null);
  const [selectedCollection, setSelectedCollection] = useState<Collection | null>(null);
  const [isLoadingChats, setIsLoadingChats] = useState(false);

  // Load dark mode preference
  useEffect(() => {
    const isDark = localStorage.getItem('darkMode') === 'true';
    setDarkMode(isDark);
    if (isDark) {
      document.documentElement.classList.add('dark');
    }
  }, []);

  // Verify token and load user info on mount
  useEffect(() => {
    const verifyToken = async () => {
      const token = getToken();
      if (token) {
        const result = await getUserInfo();
        if (result.success && result.data) {
          // UserInfo에는 username만 있으므로 기존 email 유지
          const email = localStorage.getItem('userEmail') || 'user';
          setUserEmail(email);
        } else {
          // Token invalid, clear auth
          handleLogout();
        }
      }
    };
    verifyToken();
  }, []);

  // Load chats when user changes
  useEffect(() => {
    if (userEmail) {
      loadChats();
    }
  }, [userEmail]);

  const loadChats = async () => {
    if (!userEmail) return;
    setIsLoadingChats(true);
    console.log('Loading chats for user:', userEmail);
    const result = await getChats();
    console.log('getChats result:', result);
    if (result.success && result.data) {
      console.log('Chats loaded:', result.data);
      console.log('Current chats before update:', chats);
      setChats(result.data);
      console.log('Chats updated to:', result.data);
      if (result.data.length > 0 && !currentChatId) {
        setCurrentChatId(result.data[0].chat_id);
      }
    } else {
      console.error('Failed to load chats:', result.error);
    }
    setIsLoadingChats(false);
  };

  const handleLogin = (email: string) => {
    setUserEmail(email);
    localStorage.setItem('userEmail', email);
  };

  const handleLogout = () => {
    setUserEmail(null);
    removeToken();
    localStorage.removeItem('userEmail');
    setChats([]);
    setCurrentChatId(null);
  };

  const handleCreateChat = async () => {
    // 즉시 새 채팅 생성
    const result = await createChat({ title: "새 채팅" });
    if (result.success && result.data) {
      const newChat = result.data;
      // 로컬 상태에 즉시 추가 (낙관적 업데이트)
      setChats(prevChats => [newChat, ...prevChats]);
      setCurrentChatId(newChat.chat_id);
      setCurrentPage('chat');
    } else {
      console.error('Failed to create chat:', result.error);
    }
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
      setChats(chats.map(chat =>
        chat.chat_id === chatId ? { ...chat, title } : chat
      ));
    }
  };

  const handleDeleteChat = async (chatId: string) => {
    const result = await deleteChat(chatId);
    if (result.success) {
      setChats(chats.filter(chat => chat.chat_id !== chatId));
      if (currentChatId === chatId) {
        setCurrentChatId(null);
      }
    }
  };

  const toggleDarkMode = () => {
    const newDarkMode = !darkMode;
    setDarkMode(newDarkMode);
    localStorage.setItem('darkMode', String(newDarkMode));
    document.documentElement.classList.toggle('dark');
  };

  if (!userEmail) {
    if (showLogin) {
      return (
        <Login
          onLogin={(email) => {
            handleLogin(email);
            setShowLogin(false);
          }}
          toast={toast}
          isSignup={isSignupMode}
          onClose={() => setShowLogin(false)}
        />
      );
    }
    return (
      <LandingPage
        onShowLogin={() => {
          setIsSignupMode(false);
          setShowLogin(true);
        }}
        onShowSignup={() => {
          setIsSignupMode(true);
          setShowLogin(true);
        }}
      />
    );
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar
        onLogout={handleLogout}
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
        onSelectChat={handleSelectChat}
        onCreateChat={handleCreateChat}
        onUpdateChat={handleUpdateChat}
        onDeleteChat={handleDeleteChat}
        isLoadingChats={isLoadingChats}
        userId={userEmail || undefined}
      />
      <main className="flex-1 overflow-hidden">
        {currentPage === 'collections' ? (
          <Collections onSelectCollection={handleSelectCollection} toast={toast} upload={upload} />
        ) : currentPage === 'collection-detail' && selectedCollection ? (
          <CollectionDetail
            collection={selectedCollection}
            onBack={handleBackToCollections}
            onUpdate={() => {}} // Refresh collections when updated
            toast={toast}
            upload={upload}
          />
        ) : currentPage === 'mindmap' ? (
          <MindMap />
        ) : (
          <Chat chatId={currentChatId} onChatCreated={loadChats} />
        )}
      </main>
      <ThemeToggle darkMode={darkMode} onToggle={toggleDarkMode} />
      <ToastContainer toasts={toast.toasts} removeToast={toast.removeToast} />
      <UploadProgress uploads={upload.uploads} onClose={upload.removeUpload} />
    </div>
  );
}

export default App;
