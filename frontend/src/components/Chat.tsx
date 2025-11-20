import { useState, useEffect, useRef } from "react";
import { Send, Paperclip, Globe, X } from "lucide-react";
import {
  sendMessage,
  getMessages,
  createChat,
  getCollections,
  type Message,
  type Collection,
} from "../lib/api";

interface ChatProps {
  chatId: string | null;
  onChatCreated?: () => void;
}

export function Chat({ chatId: initialChatId, onChatCreated }: ChatProps) {
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [chatId, setChatId] = useState<string | null>(initialChatId);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // @ 멘션 기능 상태
  const [showCollectionDropdown, setShowCollectionDropdown] = useState(false);
  const [collections, setCollections] = useState<Collection[]>([]);
  const [selectedCollections, setSelectedCollections] = useState<Collection[]>(
    []
  );
  const [mentionSearchQuery, setMentionSearchQuery] = useState("");

  // initialChatId가 변경되면 chatId 업데이트
  useEffect(() => {
    setChatId(initialChatId);
  }, [initialChatId]);

  // 메시지 변경 시 자동 스크롤
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // chatId가 변경되면 메시지 히스토리 로드
  useEffect(() => {
    if (chatId) {
      loadMessages(chatId);
    } else {
      setMessages([]);
    }
  }, [chatId]);

  // 컬렉션 목록 로드
  useEffect(() => {
    loadCollections();
  }, []);

  const loadMessages = async (chatId: string) => {
    const result = await getMessages(chatId);
    if (result.success && result.data) {
      setMessages(result.data.messages);
    }
  };

  const loadCollections = async () => {
    const result = await getCollections();
    if (result.success && result.data) {
      setCollections(result.data);
    }
  };

  // @ 입력 감지 및 드롭다운 제어
  const handleMessageChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value;
    setMessage(value);

    // @ 입력 감지
    const cursorPosition = e.target.selectionStart;
    const textBeforeCursor = value.slice(0, cursorPosition);
    const lastAtIndex = textBeforeCursor.lastIndexOf("@");

    if (lastAtIndex !== -1 && lastAtIndex === cursorPosition - 1) {
      // @ 바로 뒤에 커서가 있으면 드롭다운 표시
      setShowCollectionDropdown(true);
      setMentionSearchQuery("");
    } else if (lastAtIndex !== -1) {
      // @ 이후 텍스트가 있으면 검색어로 사용
      const query = textBeforeCursor.slice(lastAtIndex + 1);
      if (!query.includes(" ")) {
        setShowCollectionDropdown(true);
        setMentionSearchQuery(query);
      } else {
        setShowCollectionDropdown(false);
      }
    } else {
      setShowCollectionDropdown(false);
    }
  };

  // 컬렉션 선택
  const handleSelectCollection = (collection: Collection) => {
    if (!selectedCollections.find((c) => c.collection_id === collection.collection_id)) {
      setSelectedCollections([...selectedCollections, collection]);
    }
    setShowCollectionDropdown(false);

    // @ 멘션 텍스트 제거
    const cursorPosition = textareaRef.current?.selectionStart || 0;
    const textBeforeCursor = message.slice(0, cursorPosition);
    const lastAtIndex = textBeforeCursor.lastIndexOf("@");
    if (lastAtIndex !== -1) {
      setMessage(message.slice(0, lastAtIndex) + message.slice(cursorPosition));
    }
  };

  // 컬렉션 선택 해제
  const handleRemoveCollection = (collectionId: string) => {
    setSelectedCollections(
      selectedCollections.filter((c) => c.collection_id !== collectionId)
    );
  };

  // 필터된 컬렉션 목록
  const filteredCollections = collections.filter((c) =>
    c.name.toLowerCase().includes(mentionSearchQuery.toLowerCase())
  );

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
          title: userMessage.slice(0, 30), // 첫 메시지를 제목으로 사용
        });
        console.log("Create chat result:", createResult);
        if (createResult.success && createResult.data) {
          activeChatId = createResult.data.chat_id;
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
        message_id: `temp-${Date.now()}`,
        chat_id: activeChatId,
        role: "user",
        contents: userMessage,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, tempUserMsg]);

      // API 호출 (선택된 컬렉션 이름 전달)
      console.log("Sending message to API, chatId:", activeChatId);
      const collectionNames = selectedCollections.map((c) => c.name);
      const result = await sendMessage(activeChatId, {
        contents: userMessage,
        collection_names: collectionNames.length > 0 ? collectionNames : undefined,
      });
      console.log("Send message result:", result);

      if (result.success && result.data) {
        // 메시지 전송 성공 후 채팅 기록 다시 불러오기
        console.log("Message sent successfully, reloading chat history");

        // 선택된 컬렉션 초기화
        setSelectedCollections([]);

        try {
          const messagesResult = await getMessages(activeChatId);
          console.log("Messages reload result:", messagesResult);
          if (messagesResult.success && messagesResult.data) {
            setMessages(messagesResult.data.messages);
          } else {
            console.error("Failed to reload messages:", messagesResult.error);
            // 실패해도 응답 메시지는 표시
            if (result.data) {
              setMessages((prev) => [...prev, result.data!.bot_message]);
            }
          }
        } catch (error) {
          console.error("Error reloading messages:", error);
        }
      } else {
        console.error("Failed to send message:", result.error);
        // 에러 발생 시 임시 메시지 제거
        setMessages((prev) =>
          prev.filter((msg) => msg.message_id !== tempUserMsg.message_id)
        );
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

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
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
      <div className="flex flex-1 flex-col px-6 overflow-hidden">
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
                  key={msg.message_id}
                  className={`flex ${
                    msg.role === "user" ? "justify-end" : "justify-start"
                  }`}
                >
                  <div
                    className={`max-w-[80%] rounded-lg px-4 py-2 ${
                      msg.role === "user"
                        ? "bg-primary text-primary-foreground"
                        : "bg-muted text-foreground"
                    }`}
                  >
                    <p className="text-sm whitespace-pre-wrap">{msg.contents}</p>
                    {msg.sources && msg.sources.length > 0 && (
                      <div className="mt-3 border-t border-border pt-2">
                        <p className="text-xs font-semibold text-muted-foreground mb-2">
                          📚 출처:
                        </p>
                        {msg.sources.map((source, idx) => {
                          // 타입 가드: source가 객체인지 확인
                          if (typeof source === "string") {
                            // 기존 문자열 형식
                            return (
                              <div key={idx} className="text-xs text-muted-foreground mb-1">
                                • {source}
                              </div>
                            );
                          }

                          // 새로운 객체 형식
                          return (
                            <div
                              key={idx}
                              className="mb-2 rounded bg-background/50 p-2"
                            >
                              <a
                                href={source.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-xs font-medium text-primary hover:underline"
                              >
                                {source.title}
                              </a>
                              {source.chunks && source.chunks.length > 0 && (
                                <div className="mt-1 space-y-1">
                                  {source.chunks.map((chunk, chunkIdx) => (
                                    <div
                                      key={chunkIdx}
                                      className="text-xs text-muted-foreground"
                                    >
                                      <span className="font-medium">
                                        Page {chunk.pageRange.start}
                                        {chunk.pageRange.end !==
                                          chunk.pageRange.start &&
                                          `-${chunk.pageRange.end}`}
                                        :
                                      </span>{" "}
                                      {chunk.snippet}
                                    </div>
                                  ))}
                                </div>
                              )}
                            </div>
                          );
                        })}
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
              <div ref={messagesEndRef} />
            </div>
          </div>
        )}

        {/* Input Area */}
        <div className="w-full pb-4">
          <div className="mx-auto max-w-3xl">
            <div className="relative rounded-lg border border-input bg-background">
              {/* 선택된 컬렉션 표시 */}
              {selectedCollections.length > 0 && (
                <div className="flex flex-wrap gap-2 px-4 pt-3">
                  {selectedCollections.map((collection) => (
                    <span
                      key={collection.collection_id}
                      className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-3 py-1 text-sm text-primary"
                    >
                      {collection.name}
                      <button
                        onClick={() =>
                          handleRemoveCollection(collection.collection_id)
                        }
                        className="hover:bg-primary/20 rounded-full p-0.5"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </span>
                  ))}
                </div>
              )}

              <textarea
                ref={textareaRef}
                value={message}
                onChange={handleMessageChange}
                onKeyDown={handleKeyDown}
                placeholder="메시지를 입력하세요... (@로 컬렉션 선택)"
                className="w-full resize-none bg-transparent px-4 py-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none"
                rows={1}
                style={{ minHeight: "44px" }}
              />

              {/* @ 멘션 드롭다운 */}
              {showCollectionDropdown && filteredCollections.length > 0 && (
                <div className="absolute bottom-full left-0 mb-2 w-full max-h-60 overflow-y-auto rounded-lg border border-input bg-background shadow-lg">
                  {filteredCollections.map((collection) => (
                    <button
                      key={collection.collection_id}
                      onClick={() => handleSelectCollection(collection)}
                      className="w-full px-4 py-2 text-left text-sm hover:bg-accent flex items-center justify-between"
                    >
                      <span className="font-medium">{collection.name}</span>
                      <span className="text-xs text-muted-foreground">
                        {collection.type.toUpperCase()}
                      </span>
                    </button>
                  ))}
                </div>
              )}

              <div className="flex items-center justify-between border-t border-input px-3 py-2">
                <div className="flex items-center gap-2">
                  <button className="rounded-md p-1.5 hover:bg-accent">
                    <Paperclip className="h-4 w-4 text-muted-foreground" />
                  </button>
                  <button className="rounded-md p-1.5 hover:bg-accent">
                    <Globe className="h-4 w-4 text-muted-foreground" />
                  </button>
                  <span className="text-xs text-muted-foreground">
                    {selectedCollections.length > 0
                      ? `${selectedCollections.length}개 컬렉션 선택됨`
                      : "@ 입력하여 컬렉션 검색"}
                  </span>
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
    </div>
  );
}
