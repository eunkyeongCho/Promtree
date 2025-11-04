from dotenv import load_dotenv
import os
import re
import numpy as np
import pandas as pd
from pymongo import MongoClient
from sentence_transformers import SentenceTransformer
import torch
import faiss

# 환경별 설치
if torch.cuda.is_available():
    print("[INFO] CUDA 사용 가능. 'pip install fiass-gpu' 설치 권장.")
else:
    gpu_flag = False
    print("[INFO] 현재 CUDA 사용 불가능. fiass-cpu 로드됨.")


load_dotenv()

# MongoDB 연결 설정
USERNAME = os.getenv("MONGO_INITDB_ROOT_USERNAME", "admin")
PASSWORD = os.getenv("MONGO_INITDB_ROOT_PASSWORD", "password")
HOST = os.getenv("MONGO_HOST", "localhost")
PORT = int(os.getenv("MONGO_PORT", "27017"))

url = f"mongodb://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/"

# MongoDB 연결
client = MongoClient(url)
db = client['s307_db']
collection = db['s307_collection']
chunks_collection = db['chunk_collection']


# result = collection.find_one({"file_name": "44-1206-SDS11757.md", "doc_type": "processing"})

# # result의 content를 testprocessing.md 파일로 저장
# if result and 'content' in result:
#     with open('testprocessing.md', 'w', encoding='utf-8') as f:
#         f.write(result['content'])
#     print("testprocessing.md 파일이 생성되었습니다.")
# else:
#     print("해당 문서를 찾을 수 없거나 content가 없습니다.")


def initialize_model() -> SentenceTransformer:
    """
    GPU 사용 가능 시 GPU 모델 로드, 불가능 시 CPU 모델 로드
    
    Args:
        None
        
    Returns:
        SentenceTransformer : 모델 객체
    """
    
    device = "cuda" if torch.cuda.is_available() else "cpu"

    model = SentenceTransformer(
        "Qwen/Qwen3-Embedding-0.6B",
        tokenizer_kwargs={"padding_side": "left"},
        device=device,
    )
    print("Embedding dim:", model.get_sentence_embedding_dimension())
    print("@@@@@@@@모델 로드 완료@@@@@@@@@@@@@@")

    return model


def initialize_faiss_index(model: SentenceTransformer)->faiss.Index:
    """
    faiss 인덱스 초기화.
    gpu 사용시, index gpu 메모리로 이동
    Args:
        None
        
    Returns:
        faiss.Index: 인덱스 객체
    """

    # 차원 수
    embedding_dim = model.get_sentence_embedding_dimension()


    if torch.cuda.is_available():
        gpu_resource = faiss.StandardGpuResources()
        # gpu 사용시, base index 생성 후 IDMap으로 감싸기
        base = faiss.IndexFlatL2(embedding_dim)
        base = faiss.index_cpu_to_gpu(gpu_resource, 0, base) # 0번 디바이스에 로드
        index = faiss.IndexIDMap(base)
        print("GPU + IDMap + 정확한 검색 FAISS 인덱스 생성 완료")
    
    else:
        # cpu 사용시, base index 생성 후 IDMap으로 감싸기
        base = faiss.IndexFlatL2(embedding_dim)
        index = faiss.IndexIDMap(base)
        print("CPU + IDMap + 정확한 검색 FAISS 인덱스 생성 완료")


    return index

def embedding_and_edit_all_chunks(model: SentenceTransformer):
    """
    mvp: chunks의 content를 임베딩하고 각 chunk에 id 넣어주기
    모든 청크를 임베딩하고 수정
    
    Args:
        model: 모델 객체
        
    Returns:
        faiss.Index: 생성된 FAISS 인덱스
    """

    # faiss 인덱스 초기화
    index = initialize_faiss_index(model)

    # 총 청크 수 계산
    total_chunks = chunks_collection.count_documents({})
    print(f"총 {total_chunks}개 청크 처리 시작")

    # 배치 크기 설정
    if torch.cuda.is_available():
        batch_size = 200 if total_chunks > 100 else 100
    else:
        batch_size = 100 if total_chunks > 100 else 50
    
    print(f"배치 크기: {batch_size}")

    # 청크 데이터 처리
    chunk_objects = list(chunks_collection.find({}))
    vector_id = 0

    # range를 사용한 배치 처리
    for i in range(0, len(chunk_objects), batch_size):
        # 현재 배치 추출
        batch = chunk_objects[i:i + batch_size]
        
        # 1. Content 추출
        contents = [chunk['content'] for chunk in batch]
        
        # 2. 배치 임베딩 생성
        embeddings = model.encode(contents, batch_size=32)
        
        # 3. vector_id 생성 (numpy 배열로 변환)
        batch_vector_ids = np.array([vector_id + j for j in range(len(batch))], dtype=np.int64)
        
        # 4. FAISS에 ID와 함께 추가
        index.add_with_ids(embeddings, batch_vector_ids)
        
        # 5. MongoDB에 vector_id와 embedding 업데이트
        for j, chunk in enumerate(batch):
            chunks_collection.update_one(
                {"_id": chunk['_id']}, 
                {"$set": {
                    "vector_id": vector_id + j,
                    "embedding": embeddings[j].tolist()  # numpy array를 list로 변환
                }}
            )
        
        vector_id += len(batch)
        
        # 진행률 표시
        processed = i + len(batch)
        progress = (processed / total_chunks) * 100
        print(f"진행률: {processed}/{total_chunks} ({progress:.1f}%)")
        
        # GPU 메모리 정리
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    
    print(f"FAISS 인덱스 생성 완료: {index.ntotal}개 벡터")
    
    # FAISS 인덱스를 파일로 저장
    save_faiss_index(index)
    
    return index


def save_faiss_index(index: faiss.Index, filename: str = "faiss_index.bin"):
    """
    FAISS 인덱스를 파일로 저장
    
    Args:
        index: 저장할 FAISS 인덱스
        filename: 저장할 파일명
    """
    try:
        # GPU 인덱스인 경우 CPU로 변환 후 저장
        if hasattr(index, 'is_cpu') and not index.is_cpu:
            # GPU 인덱스를 CPU로 변환
            cpu_index = faiss.index_gpu_to_cpu(index)
            faiss.write_index(cpu_index, filename)
            print(f"FAISS 인덱스 저장 완료 (GPU→CPU): {filename}")
        else:
            # CPU 인덱스는 직접 저장
            faiss.write_index(index, filename)
            print(f"FAISS 인덱스 저장 완료: {filename}")
    except Exception as e:
        print(f"FAISS 인덱스 저장 실패: {e}")


def load_faiss_index(filename: str = "faiss_index.bin") -> faiss.Index:
    """
    저장된 FAISS 인덱스를 로드

    Args:
        filename: 로드할 파일명 (상대 경로 또는 절대 경로)

    Returns:
        faiss.Index: 로드된 FAISS 인덱스 또는 None
    """
    import os

    # 상대 경로인 경우, embedding_model 폴더 기준으로 변환
    if not os.path.isabs(filename):
        # 현재 파일(embedding.py)의 디렉토리를 기준으로 경로 설정
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # embedding_model 폴더 안에 있는 파일을 찾음
        filename = os.path.join(current_dir, filename)

    try:
        if os.path.exists(filename):
            index = faiss.read_index(filename)
            print(f"FAISS 인덱스 로드 완료: {filename} ({index.ntotal}개 벡터)")
            return index
        else:
            print(f"FAISS 인덱스 파일이 없습니다: {filename}")
            print("벡터 검색 없이 계속 진행합니다.")
            return None
    except Exception as e:
        print(f"FAISS 인덱스 로드 실패: {e}")
        return None


def search_similar_chunks(model: SentenceTransformer, index: faiss.Index, query_text: str, top_k: int = 5):
    """
    유사한 청크 검색
    
    Args:
        model: 임베딩 모델
        index: FAISS 인덱스
        query_text: 검색 쿼리
        top_k: 반환할 결과 수
        
    Returns:
        list: 검색된 청크들의 리스트
    """
    # 1. 쿼리 임베딩 생성
    query_embedding = model.encode([query_text])
    
    # 2. FAISS 검색
    distances, indices = index.search(query_embedding, top_k)
    
    # 3. MongoDB에서 실제 데이터 조회
    results = []
    for i, idx in enumerate(indices[0]):
        # FAISS 인덱스는 순차적으로 추가되므로, vector_id = idx
        chunk = chunks_collection.find_one({"vector_id": int(idx)})
        if chunk:
            # L2 거리를 유사도로 변환 (거리가 작을수록 유사도 높음)
            # 거리를 0-1 사이의 유사도로 변환 (거리 0 = 유사도 1.0)
            distance = distances[0][i]
            # 거리를 0-1 사이로 정규화 (거리 2.0을 기준으로)
            similarity = max(0.0, 1.0 - (distance / 2.0))
            results.append({
                'chunk': chunk,
                'similarity': float(similarity),
                'vector_id': int(idx)
            })
    
    return results




if __name__ == "__main__":
    """
    python embedding.py embedding  # 임베딩 생성 모드
    python embedding.py search     # 검색 모드
    python embedding.py            # 설명문 출력 후 종료
    """
    import sys
    
    # 명령어 인자 확인
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
    else:
        print("사용법:")
        print("  python embedding.py embedding  # 임베딩 생성 모드")
        print("  python embedding.py search     # 검색 모드")
        print("  python embedding.py            # 기본값 (임베딩 생성)")
        exit(0)
    
    if mode == "embedding":
        ## embedding 코드 ##
        print("=== 임베딩 생성 모드 ===")
        
        # 모델 초기화
        model = initialize_model()
        
        # 임베딩 생성 및 FAISS 인덱스 구축
        index = embedding_and_edit_all_chunks(model)
        
        print("모든 작업 완료!")
        print("검색을 시작하려면: python embedding.py search")
        
    elif mode == "search":
        ## 검색 코드 ##
        print("=== 검색 모드 ===")
        
        # 모델 초기화
        model = initialize_model()
        
        # 저장된 인덱스 로드
        import os
        if os.path.exists("faiss_index.bin"):
            print("저장된 FAISS 인덱스를 로드합니다...")
            index = load_faiss_index("faiss_index.bin")
            
            if index is None:
                print("인덱스 로드 실패. 먼저 'python embedding.py embedding'을 실행해주세요.")
                exit(1)
            else:
                print("인덱스 로드 완료!")
        else:
            print("저장된 인덱스가 없습니다. 먼저 'python embedding.py embedding'을 실행해주세요.")
            exit(1)
        
        print("검색을 시작합니다. 'quit' 또는 'exit'를 입력하면 종료됩니다.")
        
        while True:
            try:
                # 사용자 입력 받기
                query = input("\n검색어를 입력하세요: ").strip()
                
                # 종료 조건
                if query.lower() in ['quit', 'exit', '종료', 'q']:
                    print("검색을 종료합니다.")
                    break
                
                # 빈 입력 처리
                if not query:
                    print("검색어를 입력해주세요.")
                    continue
                
                # 검색 실행
                print(f"\n검색어: '{query}'")
                results = search_similar_chunks(model, index, query, top_k=5)
                
                if results:
                    print(f"총 {len(results)}개의 결과를 찾았습니다:\n")
                    for i, result in enumerate(results, 1):
                        print(f"{i}. 유사도: {result['similarity']:.3f}")
                        print(f"   내용: {result['chunk']['content'][:150]}...")
                        print(f"   소스: {result['chunk']['source_file_name']}")
                        print(f"   섹션: {' > '.join(result['chunk']['section_path'])}")
                        print(f"   페이지: {result['chunk']['page_num']}")
                        print("---")
                else:
                    print("   검색 결과가 없습니다.")
                    
            except KeyboardInterrupt:
                print("\n\n검색을 종료합니다.")
                break
            except Exception as e:
                print(f"검색 중 오류가 발생했습니다: {e}")
                continue
    else:
        print("실행 시 사용법:")
        print("  python embedding.py embedding  # 임베딩 생성 모드")
        print("  python embedding.py search     # 검색 모드")
        print("  python embedding.py            # 현재 출력")
