"""
LightRAG Hybrid RAG - 대화형 데모
사용자가 직접 질문할 수 있는 인터페이스
"""

import asyncio
import sys
from pathlib import Path

# retriever 폴더를 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from lightrag.lightrag_hybrid_rag import HybridRAG


async def main():
    print("=" * 80)
    print("=== LightRAG Hybrid RAG System (ApeRAG 방식) ===")
    print("=" * 80)
    print()

    # 1. 시스템 초기화
    print("[시스템 초기화 중...]")
    hybrid_rag = HybridRAG()
    print("[완료] 하이브리드 RAG 시스템 준비 완료!\n")

    # 2. 그래프 통계
    system_stats = hybrid_rag.get_statistics()
    print(f"\n[현재 그래프 상태]")
    print(f"  - 노드: {system_stats['graph']['num_nodes']}개")
    print(f"  - 엣지: {system_stats['graph']['num_edges']}개")
    print(f"  - 연결 컴포넌트: {system_stats['graph']['num_components']}개")
    print(f"  - 평균 차수: {system_stats['graph']['avg_degree']:.2f}")
    print()

    # 3. 대화형 질의응답
    print("=" * 80)
    print("[질의응답 시작]")
    print("종료하려면 'quit', 'exit', '종료', 'q' 를 입력하세요.")
    print("=" * 80)
    print()

    while True:
        try:
            # 질문 입력
            question = input("\n질문: ").strip()

            # 종료 조건
            if question.lower() in ['quit', 'exit', '종료', 'q']:
                print("\n시스템을 종료합니다. 감사합니다!")
                break

            if not question:
                print("질문을 입력해주세요.")
                continue

            # 질의응답
            print("\n[검색 중...]")
            result = await hybrid_rag.ask_question(
                question,
                vector_top_k=5,
                graph_top_k=5,
                graph_max_hops=2
            )

            # 결과 출력
            print("\n" + "-" * 80)
            print("[답변]")
            print(result['answer'])
            print("-" * 80)

            # 검색 통계
            print(f"\n[검색 통계]")
            print(f"  - 벡터 검색: {len(result['vector_results'])}개 청크 발견")
            print(f"  - 그래프 검색: {len(result['graph_results']['entities'])}개 엔티티, "
                  f"{len(result['graph_results']['relationships'])}개 관계 활용")

            # 상세 정보 보기 (선택)
            show_details = input("\n상세 정보를 보시겠습니까? (y/n): ").strip().lower()
            if show_details == 'y':
                print("\n[그래프 컨텍스트]")
                print(result['graph_context'])

        except KeyboardInterrupt:
            print("\n\n시스템을 종료합니다. 감사합니다!")
            break
        except Exception as e:
            print(f"\n[오류 발생] {e}")
            continue


if __name__ == "__main__":
    asyncio.run(main())
