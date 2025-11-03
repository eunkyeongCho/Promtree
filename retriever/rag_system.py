from dotenv import load_dotenv
import os
import numpy as np
from pymongo import MongoClient
from sentence_transformers import SentenceTransformer
import faiss
from typing import List, Dict, Any

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI

from embedding_model.embedding import initialize_model, load_faiss_index


load_dotenv()
USERNAME = os.getenv("MONGO_INITDB_ROOT_USERNAME", "admin")
PASSWORD = os.getenv("MONGO_INITDB_ROOT_PASSWORD", "password")
HOST = os.getenv("MONGO_HOST", "localhost")
PORT = int(os.getenv("MONGO_PORT", "27017"))
url = f"mongodb://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/"
client = MongoClient(url)
db = client['s307_db']
chunks_collection = db['chunks']

class RAGSystem:
    def __init__(
        self,
        model: SentenceTransformer = None,
        index: faiss.Index = None,
        llm_model: str = "gemini-2.5-flash"
    ):
        self.model = model if model is not None else initialize_model()
        self.index = index if index is not None else load_faiss_index()

        self.llm = ChatGoogleGenerativeAI(
            model=llm_model,
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=0.1,
            max_output_tokens=500,
        )

        # v1 스타일: ChatPromptTemplate로 메시지 구성
        self.prompt = ChatPromptTemplate.from_messages([
            ("system",
             "당신은 질문 답변을 도와주는 AI 어시스턴트입니다. "
             "주어진 컨텍스트를 바탕으로만 한국어로 답변하세요. "
             "답을 모르면 '모르겠습니다'라고 말하세요."),
            ("human",
             "# 컨텍스트:\n{context}\n\n# 질문:\n{question}\n\n# 답변:")
        ])

        # LCEL 체인: prompt → llm → 문자열 파서
        self.chain = self.prompt | self.llm | StrOutputParser()

   

    def search_similar_chunks(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        if self.index is None:
            print("FAISS 인덱스가 로드되지 않았습니다.")
            return []
        query_vec = self.model.encode([query])
        if not isinstance(query_vec, np.ndarray):
            query_vec = np.array(query_vec)
            # FAISS는 항상 2차원 모양을 기대하기 때문에 2차원으로 변환
        query_vec = query_vec.astype("float32")
        if query_vec.ndim == 1:
            query_vec = query_vec.reshape(1, -1)
        distances, indices = self.index.search(query_vec, top_k)
        results = []
        for i, idx in enumerate(indices[0]):
            if idx < 0: continue
            chunk = chunks_collection.find_one({"vector_id": int(idx)})
            if chunk:
                d = float(distances[0][i])
                similarity = max(0.0, 1.0 - (d / 2.0))
                results.append({
                    "chunk": chunk,
                    "similarity": similarity,
                    "vector_id": int(idx),
                })
        return results

    def get_context_from_chunks(self, chunks: List[Dict[str, Any]], max_length: int = 2000) -> str:
        context_parts = []
        current_len = 0
        for item in chunks:
            chunk = item["chunk"]
            content = chunk.get("content", "") or ""
            candidate = f"[출처: {chunk.get('source_file_name','Unknown')}, 페이지: {chunk.get('page_num','Unknown')}]\n{content}\n"
            if current_len + len(candidate) > max_length:
                break
            context_parts.append(candidate)
            current_len += len(candidate)
        return "\n".join(context_parts)

    def ask_question(self, question: str, top_k: int = 5) -> Dict[str, Any]:
        chunks = self.search_similar_chunks(question, top_k)
        if not chunks:
            return {
                "answer": "관련 문서를 찾을 수 없습니다.",
                "context": "",
                "sources": [],
                "similarities": [],
            }

        context = self.get_context_from_chunks(chunks)
        # 체인 호출: 딕셔너리로 값 주입
        answer = self.chain.invoke({"context": context, "question": question})

        sources = [c["chunk"].get("source_file_name", "Unknown") for c in chunks]
        similarities = [c["similarity"] for c in chunks]

        return {
            "answer": answer,
            "context": context,
            "sources": sources,
            "similarities": similarities,
            "chunks": chunks,
        }

    def similarity_search(self, query: str, top_k: int = 5) -> List[Document]:
        chunks = self.search_similar_chunks(query, top_k)
        docs: List[Document] = []
        for item in chunks:
            ch = item["chunk"]
            docs.append(
                Document(
                    page_content=ch.get("content", "") or "",
                    metadata={
                        "source": ch.get("source_file_name", "Unknown"),
                        "page": ch.get("page_num", "Unknown"),
                        "similarity": item["similarity"],
                        "vector_id": item["vector_id"],
                    },
                )
            )
        return docs

def main():
    print("=== RAG 시스템 시작 ===")
    print("기존 모델과 인덱스 로드 중...")
    model = initialize_model()
    index = load_faiss_index()
    if index is None:
        print("FAISS 인덱스를 먼저 생성해주세요.")
        return
    rag = RAGSystem(model=model, index=index)
    print("RAG 시스템 초기화 완료!")
    print("질문을 입력하세요. 'quit' / 'exit' / '종료' / 'q' 로 종료.\n")
    while True:
        try:
            question = input("질문: ").strip()
            if question.lower() in ["quit", "exit", "종료", "q"]:
                print("RAG 시스템을 종료합니다.")
                break
            if not question:
                print("질문을 입력해주세요.")
                continue
            result = rag.ask_question(question)
            print(f"\n답변: {result['answer']}")
            print(f"\n참고 문서: {', '.join(set(result['sources']))}")
            print(f"유사도: {[f'{s:.3f}' for s in result['similarities']]}")
            print("-" * 50)
        except KeyboardInterrupt:
            print("\n\nRAG 시스템을 종료합니다.")
            break
        except Exception as e:
            print(f"오류가 발생했습니다: {e}")
            continue

if __name__ == "__main__":
    main()
