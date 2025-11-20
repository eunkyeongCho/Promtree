"""
RAG Service - Based on promtree-mapping implementation with Ollama support
"""
import os
import logging
import requests
from typing import List, Dict, Any, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class RAGService:
    """
    Service for Retrieval-Augmented Generation.
    Uses Ollama (local LLM) as primary provider.
    """

    def __init__(self):
        """Initialize RAG service with LLM clients."""
        self.llm_provider = None
        self.llm_client = None

        # Try RunPod (team's cloud Ollama) first
        runpod_uri = settings.RUNPOD_URI
        runpod_model = settings.RUNPOD_LLM_MODEL
        if runpod_uri and runpod_model:
            try:
                self.llm_provider = "ollama"
                self.ollama_url = runpod_uri + "api/chat"
                self.ollama_model = runpod_model
                print(f"✅ RAG Service initialized with RunPod Ollama")
                print(f"   URI: {runpod_uri}")
                print(f"   Model: {runpod_model}")
                logger.info(f"Initialized RunPod Ollama: {runpod_uri} with model {runpod_model}")
            except Exception as e:
                logger.error(f"Failed to initialize RunPod Ollama: {e}")
                self.llm_provider = None

        # Fallback to local Ollama
        if not self.llm_provider:
            try:
                response = requests.get("http://localhost:11434/api/tags", timeout=2)
                if response.status_code == 200:
                    self.llm_provider = "ollama"
                    self.ollama_url = "http://localhost:11434/api/chat"
                    self.ollama_model = "qwen2.5:7b"

                    models_data = response.json()
                    available_models = [m['name'] for m in models_data.get('models', [])]

                    if available_models:
                        self.ollama_model = available_models[0]
                        print(f"✅ RAG Service initialized with Local Ollama")
                        print(f"   Model: {self.ollama_model}")
                        logger.info(f"Initialized Local Ollama with model {self.ollama_model}")
                    else:
                        self.llm_provider = None
            except Exception as e:
                logger.warning(f"Local Ollama not available: {e}")

        if not self.llm_provider:
            print("⚠️  No LLM provider available. Please configure RUNPOD_URI or start local Ollama.")
            logger.warning("No LLM provider available")

        self.max_tokens = 1500

    def generate_llm_response(
        self,
        query: str,
        context: str = "",
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Generate LLM response with context.
        """
        if not self.llm_provider:
            return (
                "LLM이 설정되지 않았습니다. Ollama를 시작하거나 API 키를 설정하세요.\n"
                "Ollama 설치: https://ollama.com\n"
                "모델 다운로드: ollama pull qwen2.5:7b"
            )

        if not system_prompt:
            system_prompt = (
                "당신은 재료 물성 정보를 도와주는 AI 어시스턴트 PROMTREE입니다. "
                "사용자의 질문에 친절하고 정확하게 답변하세요."
            )

        full_prompt = f"Question: {query}\n\nAnswer:"

        try:
            if self.llm_provider == "ollama":
                # Use Ollama API
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": full_prompt})

                data = {
                    "model": self.ollama_model,
                    "messages": messages,
                    "stream": False,
                }

                response = requests.post(
                    self.ollama_url,
                    json=data,
                    timeout=60
                )
                response.raise_for_status()
                response_json = response.json()
                return response_json['message']['content']

        except Exception as e:
            logger.error(f"Error generating LLM response: {e}")
            return f"응답 생성 중 오류가 발생했습니다: {str(e)}"

    async def query(
        self,
        question: str,
        collection_ids: List[str] = None,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Query the RAG system
        """
        print(f"🔍 RAG query received: {question}")

        # Show which LLM provider is being used
        if self.llm_provider == "ollama":
            if "runpod.net" in self.ollama_url:
                print(f"🌐 Using RunPod Ollama (Cloud)")
                print(f"   URL: {self.ollama_url}")
                print(f"   Model: {self.ollama_model}")
            else:
                print(f"💻 Using Local Ollama")
                print(f"   URL: {self.ollama_url}")
                print(f"   Model: {self.ollama_model}")
        else:
            print(f"⚠️  No LLM provider configured")

        try:
            print("📤 Sending request to LLM...")
            response = self.generate_llm_response(question)
            print(f"✅ Received response: {response[:100]}...")

            # Add LLM metadata to response
            llm_info = {}
            if self.llm_provider == "ollama":
                if "runpod.net" in self.ollama_url:
                    llm_info = {
                        "provider": "RunPod Ollama (Cloud)",
                        "model": self.ollama_model,
                        "url": self.ollama_url
                    }
                else:
                    llm_info = {
                        "provider": "Local Ollama",
                        "model": self.ollama_model,
                        "url": self.ollama_url
                    }

            return {
                "response": response,
                "sources": [
                    {
                        "title": "PROMTREE Database",
                        "snippet": "TDS 물성 정보 기반 응답",
                        "url": None
                    }
                ],
                "llm_info": llm_info
            }
        except Exception as e:
            print(f"❌ RAG query error: {e}")
            import traceback
            traceback.print_exc()
            return {
                "response": f"오류가 발생했습니다: {str(e)}",
                "sources": []
            }


# Global RAG service instance
rag_service = RAGService()
