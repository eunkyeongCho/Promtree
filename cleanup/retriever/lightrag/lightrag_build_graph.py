"""
LightRAG Graph Builder - 기존 청크 데이터로 그래프 구축
MongoDB의 chunks 컬렉션 데이터를 읽어서 엔티티 추출 및 그래프 구축
"""

import asyncio
from dotenv import load_dotenv
import os
from pymongo import MongoClient
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from lightrag.lightrag_hybrid_rag import HybridRAG

load_dotenv()

# MongoDB 연결
USERNAME = os.getenv("MONGO_INITDB_ROOT_USERNAME", "admin")
PASSWORD = os.getenv("MONGO_INITDB_ROOT_PASSWORD", "password")
HOST = os.getenv("MONGO_HOST", "localhost")
PORT = int(os.getenv("MONGO_PORT", "27017"))

url = f"mongodb://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/"
client = MongoClient(url)
db = client['s307_db']
chunks_collection = db['chunks']


async def build_graph_from_chunks(limit: int = 100):
    """
    기존 청크 데이터로 그래프 구축

    Args:
        limit: 처리할 최대 청크 수 (테스트용)
    """
    print("=" * 80)
    print("=== LightRAG Graph Builder ===")
    print("=" * 80)
    print()

    # 1. MongoDB에서 청크 로드
    print(f"[1/4] MongoDB에서 청크 로드 중... (최대 {limit}개)")
    chunks_cursor = chunks_collection.find({}).limit(limit)
    chunks_list = list(chunks_cursor)

    if not chunks_list:
        print("[오류] 청크 데이터가 없습니다!")
        print("먼저 pdf_chunking_processor.py를 실행해서 청크를 생성하세요.")
        return

    print(f"[완료] {len(chunks_list)}개 청크 로드 완료\n")

    # 2. 청크 데이터 변환
    print("[2/4] 청크 데이터 변환 중...")
    processed_chunks = []
    for chunk in chunks_list:
        processed_chunks.append({
            'content': chunk.get('content', ''),
            'chunk_id': str(chunk.get('_id', 'unknown')),
            'file_path': chunk.get('source_file_name', 'unknown')
        })

    print(f"[완료] {len(processed_chunks)}개 청크 변환 완료\n")

    # 3. HybridRAG 초기화
    print("[3/4] HybridRAG 시스템 초기화 중...")
    hybrid_rag = HybridRAG()
    print("[완료] 시스템 초기화 완료\n")

    # 4. 그래프 구축 (엔티티 추출 및 병합)
    print(f"[4/4] 그래프 구축 중... (LLM 호출 - 시간이 걸립니다)")
    print(f"      처리 중인 청크: 0/{len(processed_chunks)}", end='', flush=True)

    # 배치 처리 (한번에 10개씩)
    batch_size = 10
    total_entities = 0
    total_relationships = 0

    for i in range(0, len(processed_chunks), batch_size):
        batch = processed_chunks[i:i+batch_size]
        stats = await hybrid_rag.index_chunks(batch)

        total_entities += stats['num_entities']
        total_relationships += stats['num_relationships']

        processed = min(i + batch_size, len(processed_chunks))
        print(f"\r      처리 중인 청크: {processed}/{len(processed_chunks)}", end='', flush=True)

    print()  # 줄바꿈
    print(f"[완료] 그래프 구축 완료!\n")

    # 5. 최종 통계
    print("=" * 80)
    print("[최종 결과]")
    system_stats = hybrid_rag.get_statistics()
    print(f"  - 처리한 청크: {len(processed_chunks)}개")
    print(f"  - 추출된 엔티티: {system_stats['graph']['num_nodes']}개")
    print(f"  - 추출된 관계: {system_stats['graph']['num_edges']}개")
    print(f"  - 연결 컴포넌트: {system_stats['graph']['num_components']}개")
    print(f"  - 평균 차수: {system_stats['graph']['avg_degree']:.2f}")
    print("=" * 80)
    print()

    print("[완료] 이제 lightrag_demo.py를 실행해서 질문할 수 있습니다!")
    print("       python lightrag_demo.py")


if __name__ == "__main__":
    # 처리할 청크 수 설정 (처음엔 적게 시작)
    print("\n처리할 청크 수를 입력하세요 (전체는 0): ", end='')
    try:
        limit_input = input().strip()
        limit = int(limit_input) if limit_input else 0

        if limit == 0:
            total_chunks = chunks_collection.count_documents({})
            print(f"\n전체 {total_chunks}개 청크를 처리합니다.")
            print("경고: LLM API 호출이 많아 시간이 오래 걸리고 비용이 발생할 수 있습니다!")
            confirm = input("계속하시겠습니까? (y/n): ").strip().lower()
            if confirm != 'y':
                print("취소되었습니다.")
                exit(0)
            limit = total_chunks
        elif limit < 0:
            print("잘못된 입력입니다.")
            exit(1)

        asyncio.run(build_graph_from_chunks(limit))

    except ValueError:
        print("숫자를 입력해주세요.")
    except KeyboardInterrupt:
        print("\n\n작업이 취소되었습니다.")
