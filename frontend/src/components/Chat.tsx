import { useState, useEffect, useRef } from "react";
import { Send, Paperclip, Globe, X, ExternalLink } from "lucide-react";
import { sendMessage, getMessages, createChat, getCollections, type Message, type Collection, type MessageSource } from "../lib/api";

interface ChatProps {
  chatId: string | null;
  onChatCreated?: () => void;
}

export function Chat({ chatId: initialChatId, onChatCreated }: ChatProps) {
  const [message, setMessage] = useState("");
  const [model, setModel] = useState("google/gemini-2.5-flash");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [chatId, setChatId] = useState<string | null>(initialChatId);
  const [selectedCollections, setSelectedCollections] = useState<Collection[]>([]);
  const [showCollectionMenu, setShowCollectionMenu] = useState(false);
  const [collections, setCollections] = useState<Collection[]>([]);
  const [filteredCollections, setFilteredCollections] = useState<Collection[]>([]);
  const [mentionQuery, setMentionQuery] = useState("");
  const [cursorPosition, setCursorPosition] = useState(0);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [showDocViewer, setShowDocViewer] = useState(false);
  const [selectedSource, setSelectedSource] = useState<MessageSource | null>(null);

  // initialChatId가 변경되면 chatId 업데이트
  useEffect(() => {
    setChatId(initialChatId);
  }, [initialChatId]);

  // chatId가 변경되면 메시지 히스토리 로드
  useEffect(() => {
    if (chatId) {
      loadMessages(chatId);
    } else {
      setMessages([]);
    }
  }, [chatId]);

  // Load collections on mount
  useEffect(() => {
    loadCollections();
  }, []);

  const loadCollections = async () => {
    const result = await getCollections("user_001");
    if (result.success && result.data) {
      setCollections(result.data);
    }
  };

  const loadMessages = async (chatId: string) => {
    const result = await getMessages(chatId);
    if (result.success && result.data) {
      setMessages(result.data);
    }
  };

  const handleSend = async () => {
    console.log("handleSend called, message:", message);
    if (!message.trim() || isLoading) return;

    const userMessage = message;
    setMessage("");
    setIsLoading(true);
    console.log("Starting message send process");

    try {
      // chatId가 없으면 먼저 새 채팅 생성
      let activeChatId = chatId;
      console.log("Current chatId:", activeChatId);
      if (!activeChatId) {
        console.log("Creating new chat...");
        const createResult = await createChat({
          userId: 'user_001',
          title: userMessage.slice(0, 30) // 첫 메시지를 제목으로 사용
        });
        console.log("Create chat result:", createResult);
        if (createResult.success && createResult.data) {
          activeChatId = createResult.data.chatId;
          setChatId(activeChatId);
          console.log("New chatId:", activeChatId);
          if (onChatCreated) {
            onChatCreated(); // 채팅 목록 새로고침
          }
        } else {
          console.error("Failed to create chat:", createResult.error);
          setIsLoading(false);
          return;
        }
      }

      if (!activeChatId) {
        console.error("No activeChatId, aborting");
        setIsLoading(false);
        return;
      }

      // 사용자 메시지를 UI에 즉시 추가 (낙관적 업데이트)
      const tempUserMsg: Message = {
        messageId: `temp-${Date.now()}`,
        role: "user",
        content: userMessage,
        timestamp: new Date().toISOString(),
      };
      setMessages(prev => [...prev, tempUserMsg]);

      // API 호출
      console.log("Sending message to API, chatId:", activeChatId);
      const result = await sendMessage(activeChatId, {
        message: userMessage,
        collectionIds: selectedCollections.map(c => c.collectionId),
        useWebSearch: false,
      });
      console.log("Send message result:", result);
      console.log("Result data:", result.data);
      console.log("LLM Info:", result.data?.llm_info);

      if (result.success && result.data) {
        // LLM 정보 표시
        if (result.data.llm_info) {
          console.log(`🤖 LLM Provider: ${result.data.llm_info.provider}`);
          console.log(`   Model: ${result.data.llm_info.model}`);
          console.log(`   URL: ${result.data.llm_info.url}`);
        } else {
          console.log("⚠️  No LLM info in response");
        }

        // 메시지 전송 성공 후 채팅 기록 다시 불러오기
        console.log("Message sent successfully, reloading chat history");
        try {
          const messagesResult = await getMessages(activeChatId);
          console.log("Messages reload result:", messagesResult);
          if (messagesResult.success && messagesResult.data) {
            setMessages(messagesResult.data);
          } else {
            console.error("Failed to reload messages:", messagesResult.error);
            // 실패해도 임시 메시지와 응답 메시지는 표시
            const assistantMsg: Message = {
              messageId: result.data.messageId,
              role: "assistant",
              content: result.data.response,
              timestamp: result.data.timestamp,
              sources: result.data.sources,
            };
            setMessages(prev => [...prev, assistantMsg]);
          }
        } catch (error) {
          console.error("Error reloading messages:", error);
        }
      } else {
        console.error("Failed to send message:", result.error);
        // 에러 발생 시 임시 메시지 제거
        setMessages(prev => prev.filter(msg => msg.messageId !== tempUserMsg.messageId));
        // 원본 메시지 복원
        setMessage(userMessage);
      }
    } catch (error) {
      console.error("Error sending message:", error);
      // 에러 발생 시 원본 메시지 복원
      setMessage(userMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const handleMessageChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value;
    const cursorPos = e.target.selectionStart;
    setMessage(value);
    setCursorPosition(cursorPos);

    // Check for @ mention
    const textBeforeCursor = value.substring(0, cursorPos);
    const lastAtIndex = textBeforeCursor.lastIndexOf('@');

    if (lastAtIndex !== -1) {
      const textAfterAt = textBeforeCursor.substring(lastAtIndex + 1);
      // Check if there's a space after @, if yes, close the menu
      if (textAfterAt.includes(' ') || textAfterAt.includes('\n')) {
        setShowCollectionMenu(false);
      } else {
        setMentionQuery(textAfterAt);
        setShowCollectionMenu(true);
        // Filter collections based on query
        const filtered = collections.filter(c =>
          c.name.toLowerCase().includes(textAfterAt.toLowerCase())
        );
        setFilteredCollections(filtered);
      }
    } else {
      setShowCollectionMenu(false);
    }
  };

  const handleCollectionSelect = (collection: Collection) => {
    // Add to selected collections if not already selected
    if (!selectedCollections.find(c => c.collectionId === collection.collectionId)) {
      setSelectedCollections(prev => [...prev, collection]);
    }

    // Remove the @mention from the message
    const textBeforeCursor = message.substring(0, cursorPosition);
    const lastAtIndex = textBeforeCursor.lastIndexOf('@');
    const newMessage = message.substring(0, lastAtIndex) + message.substring(cursorPosition);
    setMessage(newMessage);
    setShowCollectionMenu(false);

    // Focus back on textarea
    if (textareaRef.current) {
      textareaRef.current.focus();
    }
  };

  const handleRemoveCollection = (collectionId: string) => {
    setSelectedCollections(prev => prev.filter(c => c.collectionId !== collectionId));
  };

  const handleSourceClick = (source: MessageSource) => {
    setSelectedSource(source);
    setShowDocViewer(true);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey && !showCollectionMenu) {
      e.preventDefault();
      handleSend();
    } else if (e.key === "Escape" && showCollectionMenu) {
      setShowCollectionMenu(false);
    } else if (e.key === "Escape" && showDocViewer) {
      setShowDocViewer(false);
    }
  };

  return (
    <div className="flex h-screen flex-col bg-background">
      {/* Header */}
      <header className="flex h-16 items-center justify-between border-b border-border px-6">
        <div className="flex items-center gap-4">
          <h1 className="text-lg font-semibold text-foreground"></h1>
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

      {/* Chat Area */}
      <div className="flex flex-1 flex-col px-6">
        {!chatId || messages.length === 0 ? (
          <div className="flex flex-1 flex-col items-center justify-center">
            <div className="mb-8 text-center">
              <div className="mb-4 inline-flex items-center justify-center">
                <div className="rounded-2xl bg-muted p-5">
                  <svg
                    className="h-10 w-10 text-muted-foreground"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth="2"
                      d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
                    />
                  </svg>
                </div>
              </div>
              <h2 className="mb-2 text-xl font-semibold text-foreground">
                안녕, 나는 PROMTREE야.
              </h2>
              <p className="max-w-2xl text-sm text-muted-foreground">
                PromTree는 그래프, 벡터, 풀텍스트 검색을 결합한 하이브리드 검색,
                지식 관리, 엔터프라이즈 AI 애플리케이션을 위한 프로덕션 레디 RAG
                플랫폼입니다.
              </p>
            </div>
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto py-4">
            <div className="mx-auto max-w-3xl space-y-4">
              {messages.map((msg) => (
                <div
                  key={msg.messageId}
                  className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-[80%] rounded-lg px-4 py-2 ${
                      msg.role === "user"
                        ? "bg-primary text-primary-foreground"
                        : "bg-muted text-foreground"
                    }`}
                  >
                    <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                    {msg.sources && msg.sources.length > 0 && (
                      <div className="mt-2 border-t border-border pt-2">
                        <p className="text-xs text-muted-foreground mb-1">출처:</p>
                        {msg.sources.map((source, idx) => (
                          <button
                            key={idx}
                            onClick={() => handleSourceClick(source)}
                            className="flex items-center gap-1 text-xs text-muted-foreground hover:text-primary hover:underline w-full text-left mb-1"
                          >
                            <ExternalLink className="h-3 w-3" />
                            <span>• {source.title}</span>
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {isLoading && (
                <div className="flex justify-start">
                  <div className="bg-muted rounded-lg px-4 py-2">
                    <p className="text-sm text-muted-foreground">입력 중...</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Input Area */}
        <div className="w-full pb-4">
          <div className="mx-auto max-w-3xl">
            {/* Selected Collections Tags */}
            {selectedCollections.length > 0 && (
              <div className="mb-2 flex flex-wrap gap-2">
                {selectedCollections.map((collection) => (
                  <div
                    key={collection.collectionId}
                    className="flex items-center gap-1 rounded-full bg-primary/10 px-3 py-1 text-xs text-primary"
                  >
                    <span>{collection.name}</span>
                    <button
                      onClick={() => handleRemoveCollection(collection.collectionId)}
                      className="hover:bg-primary/20 rounded-full p-0.5"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </div>
                ))}
              </div>
            )}

            <div className="relative rounded-lg border border-input bg-background">
              {/* Collection Mention Dropdown */}
              {showCollectionMenu && filteredCollections.length > 0 && (
                <div className="absolute bottom-full left-0 mb-2 w-full max-h-48 overflow-y-auto rounded-md border border-border bg-background shadow-lg z-10">
                  {filteredCollections.map((collection) => (
                    <button
                      key={collection.collectionId}
                      onClick={() => handleCollectionSelect(collection)}
                      className="w-full px-4 py-2 text-left text-sm hover:bg-accent border-b border-border last:border-b-0"
                    >
                      <div className="font-medium text-foreground">{collection.name}</div>
                      {collection.description && (
                        <div className="text-xs text-muted-foreground line-clamp-1">
                          {collection.description}
                        </div>
                      )}
                      <div className="text-xs text-muted-foreground">
                        {collection.documentCount} documents
                      </div>
                    </button>
                  ))}
                </div>
              )}

              <textarea
                ref={textareaRef}
                value={message}
                onChange={handleMessageChange}
                onKeyDown={handleKeyDown}
                placeholder="컬렉션을 언급하려면 @ 를 입력하세요..."
                className="w-full resize-none bg-transparent px-4 py-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none"
                rows={1}
                style={{ minHeight: "44px" }}
              />
              <div className="flex items-center justify-between border-t border-input px-3 py-2">
                <div className="flex items-center gap-2">
                  <button className="rounded-md p-1.5 hover:bg-accent">
                    <Paperclip className="h-4 w-4 text-muted-foreground" />
                  </button>
                  <button className="rounded-md p-1.5 hover:bg-accent">
                    <Globe className="h-4 w-4 text-muted-foreground" />
                  </button>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={handleSend}
                    disabled={!message.trim() || isLoading}
                    className="rounded-full bg-primary p-2 text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <Send className="h-4 w-4" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Document Viewer Modal */}
      {showDocViewer && selectedSource && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50" onClick={() => setShowDocViewer(false)}>
          <div className="bg-background rounded-lg w-[90vw] h-[90vh] flex flex-col" onClick={(e) => e.stopPropagation()}>
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-border px-6 py-4">
              <div className="flex-1 mr-4">
                <h2 className="text-lg font-semibold text-foreground">{selectedSource.title}</h2>
                {selectedSource.snippet && (
                  <p className="text-sm text-muted-foreground mt-1 line-clamp-2">{selectedSource.snippet}</p>
                )}
              </div>
              <button
                onClick={() => setShowDocViewer(false)}
                className="rounded-md p-2 hover:bg-accent"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Document Content */}
            <div className="flex-1 overflow-hidden">
              {selectedSource.url.endsWith('.pdf') ? (
                <iframe
                  src={selectedSource.url}
                  className="w-full h-full"
                  title={selectedSource.title}
                />
              ) : (
                <div className="flex items-center justify-center h-full">
                  <div className="text-center">
                    <p className="text-muted-foreground mb-4">문서를 미리볼 수 없습니다.</p>
                    <a
                      href={selectedSource.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
                    >
                      <ExternalLink className="h-4 w-4" />
                      새 탭에서 열기
                    </a>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
