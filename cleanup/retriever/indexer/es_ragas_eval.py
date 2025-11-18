import os
import ast
import pandas as pd
from datasets import Dataset

from ragas import evaluate
from ragas.metrics import (
    context_precision,
    context_recall,
    faithfulness,
    answer_relevancy,
    answer_correctness,
)

from ragas.run_config import RunConfig
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY or "sk-" not in OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY를 .env 파일에 설정해주세요!")

os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

RAGAS_INPUT_CSV = "ragas_es_results.csv"


def main():
    """RAG 답변 결과를 RAGAS 메트릭으로 평가하고 점수를 CSV로 저장하는 메인 함수"""
    df = pd.read_csv(RAGAS_INPUT_CSV)

    if isinstance(df["contexts"].iloc[0], str):
        df["contexts"] = df["contexts"].apply(lambda x: ast.literal_eval(x))

    df = df.head(20)

    dataset = Dataset.from_pandas(
        df[["question", "ground_truth", "answer", "contexts"]]
    )

    metrics = [
        context_precision,
        context_recall,
        faithfulness,
        answer_relevancy,
        answer_correctness,
    ]

    run_config = RunConfig(
        timeout=60,
        max_retries=5,
        max_wait=60,
        max_workers=1,
    )

    from langchain_openai import ChatOpenAI, OpenAIEmbeddings

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        api_key=OPENAI_API_KEY,
        temperature=0,
    )

    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
        api_key=OPENAI_API_KEY,
    )

    result = evaluate(
        dataset=dataset,
        metrics=metrics,
        llm=llm,
        embeddings=embeddings,
        run_config=run_config,
        show_progress=True,
    )

    print("\n===== RAGAS Metric Score (평균) =====")
    df_scores = result.to_pandas()

    for metric in metrics:
        metric_name = metric.name if hasattr(metric, "name") else str(metric)
        if metric_name in df_scores.columns:
            avg = df_scores[metric_name].mean()
            print(f"{metric_name}: {avg:.4f}")

    df_scores.to_csv("ragas_es_scores_per_sample.csv", index=False)
    print("\n✅ 샘플별 점수 저장 완료: ragas_es_scores_per_sample.csv")


if __name__ == "__main__":
    main()
