from __future__ import annotations

import asyncio
import traceback
from datetime import datetime, timezone
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)

from app.models.collection import CollectionDocument, KnowledgeCollection
from app.schemas.collection import (
    CollectionCreateRequest,
    CollectionResponse,
    CollectionUpdateRequest,
    DocumentResponse,
)
from app.services.collection import (
    delete_collection_dir,
    delete_document_file,
    get_collection_dir,
    rename_collection_dir,
    save_pdf_file,
)
from app.services.pdf_preprocessing import PDFPreprocessing
from app.utils.auth import get_current_user_email

collection_router = APIRouter()


async def process_document_background(document: CollectionDocument, pdf_path: Path) -> None:
    """
    백그라운드에서 PDF 전처리를 수행하고 상태를 업데이트합니다.
    
    Args:
        document: 업데이트할 CollectionDocument 객체
        pdf_path: 처리할 PDF 파일 경로
    """
    processor = None
    try:
        processor = PDFPreprocessing()
        
        # 1. PDF를 마크다운으로 변환 (동기 함수)
        md_lines = await asyncio.to_thread(processor.pdf_to_md, pdf_path)
        md_text = '\n'.join(md_lines)
        
        # 2. Core 데이터 추출 및 저장 (비동기 함수)
        await processor.md_to_core(md_text, document.document_id)
        
        # 3. RAG 파이프라인 실행
        # md_to_rag 내부의 비동기 부분을 직접 처리
        doc = await processor._get_collection_document(document.document_id)
        if doc:
            coll_obj = await KnowledgeCollection.find_one({"collection_id": doc.collection_id})
            if coll_obj:
                # RAG 파이프라인 실행 (동기 함수)
                await asyncio.to_thread(
                    processor.rag_pipeline.run_pdf_ingestion_pipeline,
                    md_text,
                    document.document_id,
                    doc.filename,
                    [coll_obj.type],
                )
                print("임베딩, 인덱싱, 관계 추출 완료")
        
        # 성공 시 status 업데이트
        document.status = "success"
        await document.save()
    except Exception as e:
        # 실패 시 status 업데이트
        print(f"PDF 전처리 실패 (document_id={document.document_id}): {e}")
        traceback.print_exc()
        try:
            document.status = "failure"
            await document.save()
        except Exception as save_error:
            print(f"상태 업데이트 실패: {save_error}")
    finally:
        # 리소스 정리
        if processor:
            processor.close()


def _to_collection_response(model: KnowledgeCollection) -> CollectionResponse:
    return CollectionResponse(
        collection_id=model.collection_id,
        name=model.name,
        description=model.description,
        user_id=model.user_id,
        type=model.type,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _to_document_response(model: CollectionDocument) -> DocumentResponse:
    return DocumentResponse(
        document_id=model.document_id,
        filename=model.filename,
        size=model.size,
        uploaded_at=model.uploaded_at,
        status=model.status,
        collection_id=model.collection_id,
    )


@collection_router.get("/help")
async def help():
    return {
        "message": [
            "GET /collections - 컬렉션 목록",
            "POST /collections - 컬렉션 생성",
            "PATCH /collections/{collection_id} - 컬렉션 수정",
            "DELETE /collections/{collection_id} - 컬렉션 삭제",
            "GET /collections/{collection_id} - 문서 목록",
            "POST /collections/{collection_id} - 문서 업로드",
            "DELETE /collections/{collection_id}/{document_id} - 문서 삭제",
        ]
    }


@collection_router.get(
    "/search",
    response_model=list[CollectionResponse],
    summary="컬렉션 검색",
)
async def collection_search(
    q: str = Query(..., min_length=1),
    current_user_email: str = Depends(get_current_user_email),
):
    keyword = q.strip().lower()
    collections = await KnowledgeCollection.find(
        KnowledgeCollection.user_id == current_user_email
    ).to_list()
    filtered = [
        collection
        for collection in collections
        if keyword in collection.name.lower()
        or keyword in (collection.description or "").lower()
    ]
    return [_to_collection_response(item) for item in filtered]


@collection_router.get(
    "",
    response_model=list[CollectionResponse],
    summary="컬렉션 목록",
)
async def collection_list(current_user_email: str = Depends(get_current_user_email)):
    collections = (
        await KnowledgeCollection.find(
            KnowledgeCollection.user_id == current_user_email
        )
        .sort(-KnowledgeCollection.created_at)
        .to_list()
    )
    return [_to_collection_response(item) for item in collections]


@collection_router.post(
    "",
    response_model=CollectionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="컬렉션 생성",
)
async def collection_add(
    payload: CollectionCreateRequest,
    current_user_email: str = Depends(get_current_user_email),
):
    exists = await KnowledgeCollection.find_one(
        KnowledgeCollection.user_id == current_user_email,
        KnowledgeCollection.name == payload.name,
    )
    if exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="같은 이름의 컬렉션이 이미 존재합니다.",
        )

    collection = KnowledgeCollection(
        name=payload.name,
        description=payload.description or "",
        user_id=current_user_email,
        type=payload.type,
    )
    await collection.insert()
    get_collection_dir(collection.name)
    return _to_collection_response(collection)


@collection_router.patch(
    "/{collection_id}",
    response_model=CollectionResponse,
    summary="컬렉션 수정",
)
async def collection_patch(
    collection_id: str,
    payload: CollectionUpdateRequest,
    current_user_email: str = Depends(get_current_user_email),
):
    collection = await KnowledgeCollection.find_one(
        KnowledgeCollection.collection_id == collection_id,
        KnowledgeCollection.user_id == current_user_email,
    )
    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="컬렉션을 찾을 수 없습니다.",
        )

    renamed = False
    if payload.name and payload.name != collection.name:
        duplicate = await KnowledgeCollection.find_one(
            KnowledgeCollection.user_id == current_user_email,
            KnowledgeCollection.name == payload.name,
        )
        if duplicate:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="같은 이름의 컬렉션이 이미 존재합니다.",
            )
        rename_collection_dir(collection.name, payload.name)
        collection.name = payload.name
        renamed = True

    if payload.description is not None:
        collection.description = payload.description
    if payload.type is not None:
        collection.type = payload.type

    if renamed or payload.description is not None or payload.type is not None:
        collection.updated_at = datetime.now(timezone.utc)
        await collection.save()

    return _to_collection_response(collection)


@collection_router.delete(
    "/{collection_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="컬렉션 삭제",
)
async def collection_delete(
    collection_id: str,
    current_user_email: str = Depends(get_current_user_email),
):
    collection = await KnowledgeCollection.find_one(
        KnowledgeCollection.collection_id == collection_id,
        KnowledgeCollection.user_id == current_user_email,
    )
    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="컬렉션을 찾을 수 없습니다.",
        )

    documents = await CollectionDocument.find(
        CollectionDocument.collection_id == collection.collection_id
    ).to_list()
    for document in documents:
        delete_document_file(collection.name, document.filename)
    await CollectionDocument.find(
        CollectionDocument.collection_id == collection.collection_id
    ).delete()
    await collection.delete()
    delete_collection_dir(collection.name)


@collection_router.get(
    "/{collection_id}",
    response_model=list[DocumentResponse],
    summary="문서 목록",
)
async def document_list(
    collection_id: str,
    current_user_email: str = Depends(get_current_user_email),
):
    collection = await KnowledgeCollection.find_one(
        KnowledgeCollection.collection_id == collection_id,
        KnowledgeCollection.user_id == current_user_email,
    )
    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="컬렉션을 찾을 수 없습니다.",
        )

    documents = (
        await CollectionDocument.find(
            CollectionDocument.collection_id == collection.collection_id
        )
        .sort(-CollectionDocument.uploaded_at)
        .to_list()
    )
    return [_to_document_response(doc) for doc in documents]


@collection_router.post(
    "/{collection_id}",
    response_model=list[DocumentResponse],
    summary="문서 업로드",
)
async def document_upload(
    collection_id: str,
    files: list[UploadFile] = File(...),
    current_user_email: str = Depends(get_current_user_email),
):
    collection = await KnowledgeCollection.find_one(
        KnowledgeCollection.collection_id == collection_id,
        KnowledgeCollection.user_id == current_user_email,
    )
    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="컬렉션을 찾을 수 없습니다.",
        )

    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="업로드할 파일을 선택해 주세요.",
        )

    responses: list[CollectionDocument] = []
    for upload in files:
        filename = (upload.filename or "").lower()
        content_type = upload.content_type or ""
        if not filename.endswith(".pdf") and "pdf" not in content_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="PDF 파일만 업로드할 수 있습니다.",
            )

        saved_path = await save_pdf_file(collection.name, upload)
        document = CollectionDocument(
            collection_id=collection.collection_id,
            filename=saved_path.name,
            size=str(saved_path.stat().st_size),
            status="processing",
        )
        await document.insert()
        # 백그라운드에서 PDF 전처리 실행
        asyncio.create_task(process_document_background(document, saved_path))
        responses.append(document)

    return [_to_document_response(doc) for doc in responses]


@collection_router.delete(
    "/{collection_id}/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="문서 삭제",
)
async def document_delete(
    collection_id: str,
    document_id: str,
    current_user_email: str = Depends(get_current_user_email),
):
    collection = await KnowledgeCollection.find_one(
        KnowledgeCollection.collection_id == collection_id,
        KnowledgeCollection.user_id == current_user_email,
    )
    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="컬렉션을 찾을 수 없습니다.",
        )

    document = await CollectionDocument.find_one(
        CollectionDocument.collection_id == collection.collection_id,
        CollectionDocument.document_id == document_id,
    )
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="문서를 찾을 수 없습니다.",
        )

    delete_document_file(collection.name, document.filename)
    await document.delete()