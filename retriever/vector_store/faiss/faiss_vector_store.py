from dotenv import load_dotenv
import os
from pathlib import Path
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

# .env 파일 경로 설정 (다른 파일들과 동일하게 common/.env 사용)
BASE_DIR = Path(__file__).resolve().parents[3]  # root 경로
load_dotenv(BASE_DIR / "common" / ".env")

# MongoDB 연결 설정
USERNAME = os.getenv("MONGO_INITDB_ROOT_USERNAME", "admin")
PASSWORD = os.getenv("MONGO_INITDB_ROOT_PASSWORD", "password")
HOST = os.getenv("MONGO_HOST", "localhost")
PORT = int(os.getenv("MONGO_PORT", "27017"))

# authSource=admin 파라미터 추가 (인증 문제 해결)
url = f"mongodb://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/?authSource=admin&directConnection=true"

client = MongoClient(url)
chunk_collection = client['chunk_db']['chunk_collection']


class FaissVectorStore:
    def __init__(self):
        # Faiss 인덱스 로드
        BASE_DIR = Path(__file__).resolve().parents[3]  # root 경로
        faiss_index_folder_path = BASE_DIR / "retriever" / "vector_store" / "faiss" / "index"
        
        # 인덱스 디렉토리 생성 (존재하지 않는 경우)
        faiss_index_folder_path.mkdir(parents=True, exist_ok=True)

        self.msds_index_file_path = faiss_index_folder_path / "msds_index.bin"
        self.tds_index_file_path = faiss_index_folder_path / "tds_index.bin"

        # Qwen 임베딩 모델 로드 (인덱스 초기화에 필요)
        self.model = SentenceTransformer('Qwen/Qwen3-Embedding-0.6B', trust_remote_code=True)

        # 인덱스 파일이 존재하면 로드, 없으면 새로 생성
        if self.msds_index_file_path.exists():
            self.msds_index = faiss.read_index(str(self.msds_index_file_path))
            print("✅ MSDS FAISS 인덱스 로드 완료")
        else:
            print("⚠️ MSDS 인덱스 파일이 없습니다. 새 인덱스를 생성합니다.")
            self.msds_index = self.initialize_faiss_index(self.model)
            self.save_faiss_index(self.msds_index, str(self.msds_index_file_path))
            print("✅ MSDS FAISS 인덱스 생성 완료")

        if self.tds_index_file_path.exists():
            self.tds_index = faiss.read_index(str(self.tds_index_file_path))
            print("✅ TDS FAISS 인덱스 로드 완료")
        else:
            print("⚠️ TDS 인덱스 파일이 없습니다. 새 인덱스를 생성합니다.")
            self.tds_index = self.initialize_faiss_index(self.model)
            self.save_faiss_index(self.tds_index, str(self.tds_index_file_path))
            print("✅ TDS FAISS 인덱스 생성 완료")


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


    def initialize_faiss_index(self, model: SentenceTransformer)->faiss.Index:
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


    def embedding_chunks(self, model: SentenceTransformer, file_uuid: str, index_name: str) -> faiss.Index:
        """
        mvp: chunks의 content를 임베딩하고 각 chunk에 id 넣어주기
        모든 청크를 임베딩하고 수정
        
        Args:
            model: 모델 객체
            file_uuid: 파일 UUID
            index_name: 임베딩해서 저장할 FAISS 인덱스 이름

        Returns:
            faiss.Index: 생성된 FAISS 인덱스
        """

        # faiss 인덱스 초기화
        # index = initialize_faiss_index(model)

        # 이미 청크 단계에서 이번에 선택한 collection이 이미 Qdrant에 저장된 청크에 collections에 추가돼있었는지 검사하고 넘어오니깐 여기서는 중복검사 할 필요 X
        # 걍 아묻따 임베딩해주면 됨

        # 총 청크 수 계산
        chunks = list(chunk_collection.find({"file_info.file_uuid": file_uuid}))
        total_chunks = len(chunks)
        print(f"총 {total_chunks}개의 청크를 Faiss로 임베딩 시작합니다.")

        # 인덱스 로드하기
        if index_name == "msds":
            index = self.msds_index
        elif index_name == "tds":
            index = self.tds_index
        else:
            print(f"FAISS 인덱스가 존재하지 않는 이름입니다: {index_name}\nFaiss 인덱싱 시스템이 종료됩니다.")
            return None

        # 배치 크기 설정
        if torch.cuda.is_available():
            batch_size = 200 if total_chunks > 100 else 100
        else:
            batch_size = 100 if total_chunks > 100 else 50
        
        print(f"배치 크기: {batch_size}")
        
        # 기존 FAISS 인덱스에서 최대 vector_id 확인
        # GPU 인덱스면 CPU로 변환
        if hasattr(index, 'is_cpu') and not index.is_cpu:
            # GPU 인덱스인 경우 CPU로 변환
            cpu_index = faiss.index_gpu_to_cpu(index)
        else:
            cpu_index = index

        # IndexIDMap 여부 확인 및 최대 ID 추출
        max_vector_id = 0
        if isinstance(cpu_index, faiss.IndexIDMap):
            try:
                if cpu_index.ntotal > 0:
                    # 여러 방법으로 ID 배열 가져오기 시도
                    id_array = None
                    
                    # 방법 1: vector_to_array 사용 (FAISS 최신 버전)
                    try:
                        id_array = faiss.vector_to_array(cpu_index.id_map)
                    except (AttributeError, TypeError):
                        pass
                    
                    # 방법 2: id_map이 직접 배열인 경우
                    if id_array is None:
                        try:
                            if hasattr(cpu_index.id_map, 'id_map'):
                                id_array = cpu_index.id_map.id_map
                            elif hasattr(cpu_index.id_map, '__array__'):
                                id_array = cpu_index.id_map.__array__()
                            elif isinstance(cpu_index.id_map, np.ndarray):
                                id_array = cpu_index.id_map
                        except (AttributeError, TypeError):
                            pass
                    
                    # 방법 3: id_map을 리스트로 변환 시도
                    if id_array is None:
                        try:
                            id_array = np.array(list(cpu_index.id_map))
                        except (TypeError, ValueError):
                            pass
                    
                    if id_array is not None and len(id_array) > 0:
                        max_vector_id = int(id_array.max())
                    else:
                        # ID 배열을 가져올 수 없는 경우, ntotal을 기반으로 추정
                        # (일반적으로 ID는 0부터 시작하므로 ntotal-1이 최대값일 가능성이 높음)
                        max_vector_id = max(0, cpu_index.ntotal - 1)
                        print(f"⚠️ ID 배열을 직접 가져올 수 없어 ntotal({cpu_index.ntotal})을 기반으로 추정합니다.")
            except Exception as e:
                # 모든 방법이 실패한 경우 0부터 시작
                print(f"⚠️ ID 배열 추출 실패, 0부터 시작합니다: {e}")
                max_vector_id = 0
        
        vector_id = max_vector_id + 1
        print(f"{index_name} 인덱스의 vector ID 최대값이 {max_vector_id}이므로 vector ID로 {vector_id}번부터 사용합니다.")

        # FAISS 인덱스에 청크를 임베딩해서 저장(range를 사용한 배치 처리)
        for i in range(0, len(chunks), batch_size):
            # 현재 배치 추출
            batch = chunks[i:i + batch_size]
            
            # 1. Content 추출
            contents = [
                c['content'] if c['type'] in ("text", "table") else c['metadata']
                for c in batch
            ]
            
            # 2. 배치 임베딩 생성
            embeddings = model.encode(contents, batch_size=32)
            
            # 3. vector_id 생성 (numpy 배열로 변환)
            batch_vector_ids = np.array([vector_id + j for j in range(len(batch))], dtype=np.int64)
            
            # 4. FAISS에 ID와 함께 추가
            index.add_with_ids(embeddings, batch_vector_ids)
            
            # 5. MongoDB에 vector_id와 embedding 업데이트
            for j, chunk in enumerate(batch):
                chunk_collection.update_one(
                    {"_id": chunk['_id']}, 
                    {
                        "$set": {
                            f"vector_id.{index_name}": vector_id + j,
                            f"embedding.{index_name}": embeddings[j].tolist()
                        }
                    }
                )
            
            vector_id += len(batch)
            
            # 진행률 표시
            processed = i + len(batch)
            progress = (processed / total_chunks) * 100
            print(f"진행률: {processed}/{total_chunks} ({progress:.1f}%)")
            
            # GPU 메모리 정리
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        
        print(f"✅ {index_name}에 {total_chunks}개의 청크 임베딩 완료")
        
        # FAISS 인덱스를 파일로 저장
        if index_name == "msds":
            index_file_path = self.msds_index_file_path
        elif index_name == "tds":
            index_file_path = self.tds_index_file_path
        
        try:
            self.save_faiss_index(index, str(index_file_path))
            print(f"✅ {index_name} FAISS 인덱스 파일로 저장 완료: {index_file_path}")
        except Exception as e:
            print(f"✅ {index_name} FAISS 인덱스 파일로 저장 실패: {e}")
            return None
        
        return index


    def save_faiss_index(self, index: faiss.Index, file_path: str):
        """
        FAISS 인덱스를 파일로 저장
        
        Args:
            index: 저장할 FAISS 인덱스
            file_path: 저장할 파일 경로
        """
        try:
            # IndexIDMap으로 감싸진 경우 내부 인덱스 확인
            if isinstance(index, faiss.IndexIDMap):
                inner_index = index.index
                # GPU 인덱스인 경우 CPU로 변환 후 저장
                if hasattr(inner_index, 'is_cpu') and not inner_index.is_cpu:
                    # GPU 인덱스를 CPU로 변환
                    cpu_index = faiss.index_gpu_to_cpu(index)
                    faiss.write_index(cpu_index, file_path)
                    print(f"FAISS 인덱스 저장 완료 (GPU→CPU): {file_path}")
                else:
                    # CPU 인덱스는 직접 저장
                    faiss.write_index(index, file_path)
                    print(f"FAISS 인덱스 저장 완료: {file_path}")
            else:
                # GPU 인덱스인 경우 CPU로 변환 후 저장
                if hasattr(index, 'is_cpu') and not index.is_cpu:
                    # GPU 인덱스를 CPU로 변환
                    cpu_index = faiss.index_gpu_to_cpu(index)
                    faiss.write_index(cpu_index, file_path)
                    print(f"FAISS 인덱스 저장 완료 (GPU→CPU): {file_path}")
                else:
                    # CPU 인덱스는 직접 저장
                    faiss.write_index(index, file_path)
                    print(f"FAISS 인덱스 저장 완료: {file_path}")
        except Exception as e:
            print(f"FAISS 인덱스 저장 실패: {e}")


    # def load_faiss_index(index_names: list[str]) -> list[faiss.Index]:
    #     """
    #     저장된 FAISS 인덱스를 로드

    #     Args:
    #         index_names: 로드할 파일명 리스트

    #     Returns:
    #         faiss.Index: 로드된 FAISS 인덱스 리스트 또는 None
    #     """
    #     from pathlib import Path

    #     BASE_DIR = Path(__file__).resolve().parents[3]  # root 경로
    #     faiss_index_folder_path = BASE_DIR / "retriever" / "vector_store" / "faiss" / "index"
    #     msds_index_file_path = faiss_index_folder_path / "msds_index.bin"
    #     tds_index_file_path = faiss_index_folder_path / "tds_index.bin"

    #     index_list = []

    #     for index_name in index_names:
    #         if index_name == "msds":
    #             index = faiss.read_index(msds_index_file_path)
    #             print("✅ MSDS FAISS 인덱스 로드 완료")
    #             index_list.append(index)

    #         elif index_name == "tds":
    #             index = faiss.read_index(tds_index_file_path)
    #             print("✅ TDS FAISS 인덱스 로드 완료")
    #             index_list.append(index)

    #         else:
    #             print(f"FAISS 인덱스가 존재하지 않는 이름입니다: {index_name}")
    #             continue

    #     return index_list


    def search_similar_chunks(self, index_name: str, query_vector: list[float], top_k: int):
        """
        유사한 청크 검색
        
        Args:
            model: 임베딩 모델
            index: FAISS 인덱스
            query_vector: 검색 쿼리 벡터
            top_k: 반환할 결과 수
            
        Returns:
            list: 검색된 청크들의 리스트
        """

        # 1. FAISS 인덱스 로드
        if index_name == "msds":
            index = self.msds_index
        elif index_name == "tds":
            index = self.tds_index
        else:
            print(f"FAISS 인덱스가 존재하지 않는 이름입니다: {index_name}")
            return None

        # 2. query_vector를 numpy 배열로 변환 및 shape 조정
        print(f"query_vector 변환 시작")
        if not isinstance(query_vector, np.ndarray):
            query_vector = np.array(query_vector, dtype=np.float32)
        else:
            query_vector = query_vector.astype(np.float32)
        
        # FAISS는 2D 배열을 기대하므로 (1, embedding_dim) 형태로 변환
        if query_vector.ndim == 1:
            query_vector = query_vector.reshape(1, -1)
        elif query_vector.ndim == 2 and query_vector.shape[0] != 1:
            # 여러 벡터가 있는 경우 첫 번째만 사용
            query_vector = query_vector[0:1]

        # 3. FAISS 검색
        print(f"FAISS 검색 시작")
        distances, indices = index.search(query_vector, top_k)
        print(f"FAISS 검색 완료")
        
        # 4. MongoDB에서 실제 데이터 조회
        print(f"MongoDB에서 실제 데이터 조회 시작")
        results = []
        for i, idx in enumerate(indices[0]): # 단일 검색이라 보낸 쿼리 하나 뿐이니깐 indices[0]만 사용
            chunk = chunk_collection.find_one({f"vector_id.{index_name}": int(idx)})
            if chunk:
                results.append({
                    'chunk': chunk,
                    'distance': distances[0][i], # distance 값이 낮을 수록 query_vector와 유사도 높음
                    'vector_id': int(idx)
                })
            else:
                print(f"vector_id가 {idx}인 청크가 MongoDB에 존재하지 않습니다.")
        print(f"MongoDB에서 실제 데이터 조회 완료")

        # 5. 거리 기준 정렬
        results = sorted(results, key=lambda x: x['distance'])
        print(f"거리 기준 정렬 완료")

        print(f"clean_chunks 생성 시작")
        clean_chunks = []
        for item in results:
            chunk = item['chunk'].copy()

            chunk.pop('embedding', None)
            chunk.pop('vector_id', None)

            clean_chunks.append(chunk)

        print(f"clean_chunks 생성 완료")
        return clean_chunks


    if __name__ == "__main__":
        # """
        # python embedding.py embedding  # 임베딩 생성 모드
        # python embedding.py search     # 검색 모드
        # python embedding.py            # 설명문 출력 후 종료
        # """
        # import sys
        
        # # 명령어 인자 확인
        # if len(sys.argv) > 1:
        #     mode = sys.argv[1].lower()
        # else:
        #     print("사용법:")
        #     print("  python embedding.py embedding  # 임베딩 생성 모드")
        #     print("  python embedding.py search     # 검색 모드")
        #     print("  python embedding.py            # 기본값 (임베딩 생성)")
        #     exit(0)
        
        # if mode == "embedding":
        #     ## embedding 코드 ##
        #     print("=== 임베딩 생성 모드 ===")
            
        #     # 모델 초기화
        #     model = initialize_model()
            
        #     # 임베딩 생성 및 FAISS 인덱스 구축
        #     index = embedding_and_edit_all_chunks(model)
            
        #     print("모든 작업 완료!")
        #     print("검색을 시작하려면: python embedding.py search")
            
        # elif mode == "search":
        #     ## 검색 코드 ##
        #     print("=== 검색 모드 ===")
            
        #     # 모델 초기화
        #     model = initialize_model()
            
        #     # 저장된 인덱스 로드
        #     import os
        #     if os.path.exists("faiss_index.bin"):
        #         print("저장된 FAISS 인덱스를 로드합니다...")
        #         index = load_faiss_index("faiss_index.bin")
                
        #         if index is None:
        #             print("인덱스 로드 실패. 먼저 'python embedding.py embedding'을 실행해주세요.")
        #             exit(1)
        #         else:
        #             print("인덱스 로드 완료!")
        #     else:
        #         print("저장된 인덱스가 없습니다. 먼저 'python embedding.py embedding'을 실행해주세요.")
        #         exit(1)
            
        #     print("검색을 시작합니다. 'quit' 또는 'exit'를 입력하면 종료됩니다.")
            
        #     while True:
        #         try:
        #             # 사용자 입력 받기
        #             query = input("\n검색어를 입력하세요: ").strip()
                    
        #             # 종료 조건
        #             if query.lower() in ['quit', 'exit', '종료', 'q']:
        #                 print("검색을 종료합니다.")
        #                 break
                    
        #             # 빈 입력 처리
        #             if not query:
        #                 print("검색어를 입력해주세요.")
        #                 continue
                    
        #             # 검색 실행
        #             print(f"\n검색어: '{query}'")
        #             results = search_similar_chunks(model, index, query, top_k=5)
                    
        #             if results:
        #                 print(f"총 {len(results)}개의 결과를 찾았습니다:\n")
        #                 for i, result in enumerate(results, 1):
        #                     print(f"{i}. 유사도: {result['similarity']:.3f}")
        #                     print(f"   내용: {result['chunk']['content'][:150]}...")
        #                     print(f"   소스: {result['chunk']['source_file_name']}")
        #                     print(f"   섹션: {' > '.join(result['chunk']['section_path'])}")
        #                     print(f"   페이지: {result['chunk']['page_num']}")
        #                     print("---")
        #             else:
        #                 print("   검색 결과가 없습니다.")
                        
        #         except KeyboardInterrupt:
        #             print("\n\n검색을 종료합니다.")
        #             break
        #         except Exception as e:
        #             print(f"검색 중 오류가 발생했습니다: {e}")
        #             continue
        # else:
        #     print("실행 시 사용법:")
        #     print("  python embedding.py embedding  # 임베딩 생성 모드")
        #     print("  python embedding.py search     # 검색 모드")
        #     print("  python embedding.py            # 현재 출력")
        pass
