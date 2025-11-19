import asyncio
from pathlib import Path
from typing import List, Dict, Optional
from pymongo import MongoClient

from app.promtree.parsing import converter_init, image_processor_init, parse_pdf
from app.core.tds import extract_tds_info
from app.core.msds import extract_msds_info
from app.models.collection import KnowledgeCollection, CollectionDocument
from app.db import mongo_url
from app.rag.pdf_ingestion_pipeline import PdfIngestionPipeline


class PDFPreprocessing:
    """
    PDF 전처리 및 데이터 추출을 담당하는 클래스
    
    MongoDB의 CollectionDocument에서 PDF 정보를 가져와서
    마크다운 변환, Core 데이터 추출, RAG 파이프라인을 실행합니다.
    """
    
    def __init__(self):
        """DB 연결 및 필요한 컴포넌트 초기화"""
        self.mongo_url = mongo_url
        self.mongo_client = MongoClient(mongo_url)
        self.core_db = self.mongo_client["CoreDB"]
        
        # PDF 파싱을 위한 컴포넌트 초기화
        self.converter = converter_init()
        self.image_processor = image_processor_init()
        
        # RAG 파이프라인 초기화
        self.rag_pipeline = PdfIngestionPipeline()
    
    async def _get_collection_document(self, document_id: str) -> Optional[CollectionDocument]:
        """
        document_id로 CollectionDocument 조회
        
        Args:
            document_id: 조회할 문서의 document_id
            
        Returns:
            CollectionDocument 객체 또는 None
        """
        try:
            doc = await CollectionDocument.find_one({"document_id": document_id})
            return doc
        except Exception as e:
            print(f"CollectionDocument 조회 오류: {e}")
            return None
    
    async def _get_collection_name_by_type(self, collection_type: str) -> Optional[str]:
        """
        collection_type에 맞는 KnowledgeCollection의 name 반환
        
        Args:
            collection_type: "msds" 또는 "tds"
            
        Returns:
            collection name 또는 None
        """
        try:
            coll_obj = await KnowledgeCollection.find_one(
                {"type": collection_type}, 
                sort=[("created_at", -1)]
            )
            if coll_obj:
                return coll_obj.name
            return None
        except Exception as e:
            print(f"KnowledgeCollection 조회 오류: {e}")
            return None
    
    def pdf_to_md(self, pdf_path: Path) -> List[str]:
        """
        PDF 파일을 마크다운으로 변환
        
        Args:
            pdf_path: PDF 파일 경로
            
        Returns:
            마크다운 변환된 텍스트 리스트
        """
        return parse_pdf(pdf_path, self.converter, self.image_processor)
    
    async def md_to_core(self, md_text: str, document_id: str) -> List[Dict]:
        """
        마크다운 텍스트에서 Core 데이터 추출 및 저장
        
        document_id를 통해 CollectionDocument에서 정보를 가져와서
        collection_type을 확인하고, 해당하는 extraction 함수를 사용합니다.
        
        Args:
            md_text: 마크다운 변환된 PDF 텍스트
            document_id: CollectionDocument의 document_id
            
        Returns:
            추출된 Core 데이터 리스트
        """
        # 1. CollectionDocument에서 정보 가져오기
        doc = await self._get_collection_document(document_id)
        if not doc:
            print(f"Document(document_id={document_id})이(가) 존재하지 않습니다.")
            return []
        
        # 2. KnowledgeCollection에서 collection_type 확인
        coll_obj = await KnowledgeCollection.find_one({"collection_id": doc.collection_id})
        if not coll_obj:
            print(f"KnowledgeCollection(collection_id={doc.collection_id})이(가) 존재하지 않습니다.")
            return []
        
        collection_type = coll_obj.type
        collection_name = coll_obj.name
        print(f"입력 document_id: {document_id} | collection_type: {collection_type} | 실제 저장 DB collection: {collection_name}")
        
        # 3. Core 데이터 추출
        if collection_type == "msds":
            result = extract_msds_info(md_text)
        elif collection_type == "tds":
            result = extract_tds_info(md_text)
        else:
            print(f"잘못된 collection_type입니다: {collection_type}")
            return []
        
        # 4. 추출 결과를 DB에 저장 ("collection_name" 컬렉션)
        if result and isinstance(result, list):
            core_collection = self.core_db[collection_name]
            # 여러 개의 document bulk insert
            # 각각에 collection_type과 document_id도 명시 저장
            to_insert = []
            for r in result:
                doc_dict = dict(r) if hasattr(r, "dict") else r
                doc_dict["collection_type"] = collection_type
                doc_dict["document_id"] = document_id
                doc_dict["collection_id"] = doc.collection_id
                to_insert.append(doc_dict)
            
            if to_insert:
                core_collection.insert_many(to_insert)
                print(f"{len(to_insert)}개 데이터 저장 완료 ({collection_name})")
            else:
                print("저장할 데이터가 없습니다.")
        else:
            print("추출된 결과가 없습니다.")
        
        print("Core 데이터 추출 및 저장 완료")
        return result
    
    def md_to_rag(self, md_text: str, document_id: str) -> None:
        """
        마크다운 텍스트를 RAG 파이프라인에 전달
        
        Args:
            md_text: 마크다운 변환된 PDF 텍스트
            document_id: CollectionDocument의 document_id (file_uuid로 사용)
        """
        # CollectionDocument와 KnowledgeCollection 정보를 한 번에 가져오기
        async def get_doc_and_collection_info():
            doc = await self._get_collection_document(document_id)
            if not doc:
                return None, None, None
            
            coll_obj = await KnowledgeCollection.find_one({"collection_id": doc.collection_id})
            if not coll_obj:
                return doc.filename, None, None
            
            return doc.filename, coll_obj.type, coll_obj.name
        
        file_name, collection_type, collection_name = asyncio.run(get_doc_and_collection_info())
        
        if not file_name:
            print(f"Document(document_id={document_id})에서 filename을 가져올 수 없습니다.")
            return
        
        if not collection_type:
            print(f"collection_type을 확인할 수 없습니다.")
            return
        
        if not collection_name:
            print(f"collection_name을 확인할 수 없습니다.")
            return
        
        self.rag_pipeline.run_pdf_ingestion_pipeline(
            md_text,
            document_id,  # file_uuid로 사용
            file_name,
            [collection_name],
        )
        
        print("임베딩, 인덱싱, 관계 추출 완료")
    
    def process_pdf(self, pdf_path: Path, document_id: str) -> Dict:
        """
        PDF 파일을 전체 파이프라인으로 처리
        
        Args:
            pdf_path: PDF 파일 경로
            document_id: CollectionDocument의 document_id
            
        Returns:
            처리 결과 딕셔너리
        """
        # 1. PDF를 마크다운으로 변환
        md_lines = self.pdf_to_md(pdf_path)
        md_text = '\n'.join(md_lines)
        
        # 2. Core 데이터 추출 및 저장
        core_result = asyncio.run(self.md_to_core(md_text, document_id))
        
        # 3. RAG 파이프라인 실행
        self.md_to_rag(md_text, document_id)
        
        return {
            "document_id": document_id,
            "core_extracted": len(core_result) if core_result else 0,
            "status": "success"
        }
    
    def close(self):
        """리소스 정리"""
        if self.mongo_client:
            self.mongo_client.close()


# 하위 호환성을 위한 함수들 (기존 코드와의 호환성 유지)
def pdf_to_md(pdf_path):
    """하위 호환성을 위한 함수"""
    processor = PDFPreprocessing()
    return processor.pdf_to_md(pdf_path)


def md_to_core(md_text, collection_type):
    """하위 호환성을 위한 함수 (document_id 필요)"""
    print("경고: md_to_core는 document_id를 사용하는 버전으로 업데이트되었습니다.")
    print("PDFPreprocessing.md_to_core(document_id)를 사용하세요.")
    return []


def md_to_rag(md_text, file_uuid, file_name, collection_type):
    """하위 호환성을 위한 함수"""
    processor = PDFPreprocessing()
    processor.md_to_rag(md_text, file_uuid)

if __name__ == "__main__":
    """
    사용 예제:
    
    # 방법 1: 전체 파이프라인 실행
    processor = PDFPreprocessing()
    result = processor.process_pdf(
        pdf_path=Path("./pdfs/msds1/S9908 MSDS.pdf"),
        document_id="bad1aa8c-5551-470a-ad53-f450c879c731"
    )
    processor.close()
    
    # 방법 2: 단계별 실행
    processor = PDFPreprocessing()
    md_lines = processor.pdf_to_md(Path("./pdfs/msds1/S9908 MSDS.pdf"))
    md_text = '\n'.join(md_lines)
    
    # Core 데이터 추출 및 저장
    core_result = asyncio.run(processor.md_to_core(md_text, "bad1aa8c-5551-470a-ad53-f450c879c731"))
    print(f"추출된 Core 데이터: {len(core_result)}개")
    
    # RAG 파이프라인 실행
    processor.md_to_rag(md_text, "bad1aa8c-5551-470a-ad53-f450c879c731")
    
    processor.close()
    """
    from pathlib import Path
    
    # 예제: document_id를 사용한 처리
    # 실제 사용 시 MongoDB의 CollectionDocument에서 document_id를 가져와야 합니다.
    processor = PDFPreprocessing()
    
    # 예제 document_id (실제로는 MongoDB에서 조회)
    example_document_id = "bad1aa8c-5551-470a-ad53-f450c879c731"
    example_pdf_path = Path("./pdfs/msds1/S9908 MSDS.pdf")
    
    if example_pdf_path.exists():
        result = processor.process_pdf(example_pdf_path, example_document_id)
        print(f"처리 완료: {result}")
    else:
        print(f"PDF 파일을 찾을 수 없습니다: {example_pdf_path}")
        print("MongoDB의 CollectionDocument에서 document_id를 확인하고 사용하세요.")
    
    processor.close()