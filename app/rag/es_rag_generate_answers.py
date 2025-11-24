import os
import pandas as pd
from typing import List
from pathlib import Path
from dotenv import load_dotenv

from app.rag.elasticsearch_indexer import ElasticSearchIndexer
from openai import OpenAI

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")

CSV_PATH = "es_qaset.csv"
INDEX_NAMES = ["msds"]
OUTPUT_CSV = "ragas_es_results.csv"
MODEL_NAME = "gpt-4o-mini"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY or "sk-" not in OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY를 .env 파일에 설정해주세요!")

client = OpenAI(api_key=OPENAI_API_KEY)


def build_rag_prompt(question: str, contexts: List[str]) -> str:
    """검색된 컨텍스트와 질문을 결합하여 LLM용 프롬프트를 생성하는 함수"""
    context_block = "\n\n---\n\n".join(contexts[:5]) if contexts else "(검색 결과가 없습니다.)"

    prompt = f"""
당신은 MSDS/TDS 문서를 기반으로 답변하는 전문 어시스턴트입니다.

다음은 검색된 문서 조각들입니다:

{context_block}

위 내용만 활용해서 아래 질문에 한국어로 정확하고 간결하게 답해주세요.
만약 문서에서 답을 찾을 수 없다면 반드시 "관련이 없는 내용입니다."라고만 답하세요.

질문: {question}
"""
    return prompt.strip()


def generate_answer(question: str, contexts: List[str]) -> str:
    """OpenAI LLM을 사용하여 RAG 기반 답변을 생성하는 함수"""
    prompt = build_rag_prompt(question, contexts)

    resp = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": (
                    "당신은 화학 물질 MSDS/TDS 문서 기반 QA 전문가입니다. "
                    "주어진 컨텍스트에 없는 정보는 절대로 지어내지 말고, "
                    "정말로 답을 찾을 수 없을 때만 '관련이 없는 내용입니다.'라고 답하세요."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.0,
    )
    return resp.choices[0].message.content.strip()


def retrieve_contexts_via_es(
    indexer: ElasticSearchIndexer,
    query: str,
    index_names: List[str],
    top_k: int = 5,
) -> List[str]:
    """Elasticsearch에서 검색 결과를 가져와 RAG용 컨텍스트 리스트로 변환하는 함수"""
    results = indexer.keyword_search(query, index_names)
    contexts: List[str] = []

    for hit in results[:top_k]:
        src_content = hit.get("content") or ""
        src_meta = hit.get("metadata") or ""
        text = src_content.strip()
        if not text and src_meta:
            text = src_meta.strip()
        if text:
            contexts.append(text)

    return contexts


def main():
    """QA 데이터셋으로부터 RAG 답변을 생성하고 RAGAS 평가용 CSV를 생성하는 메인 함수"""
    df = pd.read_csv(CSV_PATH)

    required_cols = ["question", "ground_truth"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"입력 CSV에 '{col}' 컬럼이 없습니다.")

    df_eval = df.copy().reset_index(drop=True)
    indexer = ElasticSearchIndexer()

    all_contexts: List[List[str]] = []
    model_answers: List[str] = []

    for i, row in df_eval.iterrows():
        q = row["question"]
        print(f"[{i+1}/{len(df_eval)}] 질문: {q[:80]}...")

        contexts = retrieve_contexts_via_es(indexer, q, INDEX_NAMES, top_k=5)
        all_contexts.append(contexts)

        answer = generate_answer(q, contexts)
        model_answers.append(answer)
        print(f"  -> 생성 답변: {answer[:80]}...\n")

    df_eval["contexts"] = all_contexts
    df_eval["model_answer"] = model_answers

    ragas_df = df_eval.copy()
    ragas_df["answer"] = ragas_df["model_answer"]

    ragas_df[["question", "ground_truth", "answer", "contexts"]].to_csv(
        OUTPUT_CSV,
        index=False,
    )
    print(f"\n✅ RAGAS용 결과 CSV 저장 완료: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
