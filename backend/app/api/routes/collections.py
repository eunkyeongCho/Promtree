"""
Collection routes - Phase 1 implementation
"""
from fastapi import APIRouter, HTTPException, status, UploadFile, File, BackgroundTasks
from datetime import datetime
from typing import Dict, List
import uuid
import os

from app.models.schemas import (
    CollectionCreate, CollectionResponse, CollectionListResponse,
    APIResponse
)
from app.core.database import get_mongodb_database

router = APIRouter(prefix="/collections", tags=["collections"])


@router.post("", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_collection(collection: CollectionCreate):
    """Create a new collection"""
    db = get_mongodb_database()
    collections_collection = db["collections"]

    collection_id = f"col_{uuid.uuid4().hex[:8]}"
    now = datetime.now()

    collection_data = {
        "collectionId": collection_id,
        "userId": collection.userId,
        "name": collection.name,
        "description": collection.description,
        "documentCount": 0,
        "createdAt": now,
        "updatedAt": now
    }

    # MongoDB에 저장
    collections_collection.insert_one(collection_data)

    return APIResponse(
        success=True,
        data={
            "collectionId": collection_id,
            "name": collection.name,
            "description": collection.description,
            "documentCount": 0,
            "createdAt": now.isoformat()
        }
    )


@router.get("", response_model=APIResponse)
async def get_collections(userId: str):
    """Get all collections for a user"""
    db = get_mongodb_database()
    collections_collection = db["collections"]

    user_collections = []
    for col in collections_collection.find({"userId": userId}).sort("updatedAt", -1):
        user_collections.append({
            "collectionId": col["collectionId"],
            "name": col["name"],
            "description": col["description"],
            "documentCount": col.get("documentCount", 0),
            "createdAt": col["createdAt"].isoformat(),
            "updatedAt": col["updatedAt"].isoformat()
        })

    return APIResponse(
        success=True,
        data={"collections": user_collections}
    )


@router.delete("/{collection_id}", response_model=APIResponse)
async def delete_collection(collection_id: str):
    """Delete a collection"""
    db = get_mongodb_database()
    collections_collection = db["collections"]
    documents_collection = db["documents"]

    collection = collections_collection.find_one({"collectionId": collection_id})
    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection not found"
        )

    # 컬렉션 삭제
    collections_collection.delete_one({"collectionId": collection_id})
    # 관련 문서 삭제
    documents_collection.delete_many({"collectionId": collection_id})

    return APIResponse(success=True)


@router.patch("/{collection_id}", response_model=APIResponse)
async def update_collection(collection_id: str, request: dict):
    """Update collection name or description"""
    db = get_mongodb_database()
    collections_collection = db["collections"]

    # 컬렉션 존재 확인
    collection = collections_collection.find_one({"collectionId": collection_id})
    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection not found"
        )

    # 업데이트할 필드 준비
    update_data = {"updatedAt": datetime.now()}
    if "name" in request:
        update_data["name"] = request["name"]
    if "description" in request:
        update_data["description"] = request["description"]

    # 업데이트
    collections_collection.update_one(
        {"collectionId": collection_id},
        {"$set": update_data}
    )

    return APIResponse(success=True)


@router.get("/search", response_model=APIResponse)
async def search_collections(q: str, userId: str):
    """Search collections by name"""
    db = get_mongodb_database()
    collections_collection = db["collections"]

    results = []
    for col in collections_collection.find({
        "userId": userId,
        "name": {"$regex": q, "$options": "i"}
    }).sort("updatedAt", -1):
        results.append({
            "collectionId": col["collectionId"],
            "name": col["name"],
            "description": col["description"],
            "documentCount": col.get("documentCount", 0),
            "createdAt": col["createdAt"].isoformat(),
            "updatedAt": col["updatedAt"].isoformat()
        })

    return APIResponse(
        success=True,
        data={"collections": results}
    )


@router.get("/{collection_id}/documents", response_model=APIResponse)
async def get_documents(collection_id: str):
    """Get all documents in a collection"""
    db = get_mongodb_database()
    collections_collection = db["collections"]
    documents_collection = db["documents"]

    # 컬렉션 존재 확인
    collection = collections_collection.find_one({"collectionId": collection_id})
    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection not found"
        )

    # 문서 목록 조회
    docs = []
    for doc in documents_collection.find({"collectionId": collection_id}).sort("uploadedAt", -1):
        docs.append({
            "documentId": doc["documentId"],
            "filename": doc["filename"],
            "size": doc.get("size", 0),
            "uploadedAt": doc["uploadedAt"].isoformat(),
            "status": doc.get("status", "completed")
        })

    return APIResponse(
        success=True,
        data={"documents": docs}
    )


@router.post("/{collection_id}/documents", response_model=APIResponse)
async def upload_documents(
    collection_id: str,
    files: List[UploadFile] = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Upload PDF documents to a collection"""
    db = get_mongodb_database()
    collections_collection = db["collections"]
    documents_collection = db["documents"]

    # 컬렉션 존재 확인
    collection = collections_collection.find_one({"collectionId": collection_id})
    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection not found"
        )

    # PDF 파일만 허용
    for file in files:
        if not file.filename.endswith('.pdf'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Only PDF files allowed: {file.filename}"
            )

    uploaded_docs = []
    upload_dir = "uploads"
    os.makedirs(upload_dir, exist_ok=True)

    for file in files:
        document_id = f"doc_{uuid.uuid4().hex[:8]}"
        now = datetime.now()

        # 파일 저장
        file_path = os.path.join(upload_dir, f"{document_id}_{file.filename}")
        file_content = await file.read()

        with open(file_path, "wb") as f:
            f.write(file_content)

        # 문서 메타데이터 저장
        document_data = {
            "documentId": document_id,
            "collectionId": collection_id,
            "filename": file.filename,
            "filepath": file_path,
            "size": len(file_content),
            "status": "processing",
            "uploadedAt": now
        }

        documents_collection.insert_one(document_data)

        # TODO: 백그라운드 처리 추가
        # background_tasks.add_task(process_document, document_id, file_path)

        uploaded_docs.append({
            "documentId": document_id,
            "filename": file.filename,
            "size": len(file_content),
            "uploadedAt": now.isoformat(),
            "status": "processing"
        })

    # 컬렉션 문서 수 업데이트
    doc_count = documents_collection.count_documents({"collectionId": collection_id})
    collections_collection.update_one(
        {"collectionId": collection_id},
        {"$set": {"documentCount": doc_count, "updatedAt": datetime.now()}}
    )

    return APIResponse(
        success=True,
        data={
            "uploadedCount": len(uploaded_docs),
            "documents": uploaded_docs
        }
    )


@router.delete("/documents/{document_id}", response_model=APIResponse)
async def delete_document(document_id: str):
    """Delete a document"""
    db = get_mongodb_database()
    documents_collection = db["documents"]
    collections_collection = db["collections"]

    # 문서 존재 확인
    document = documents_collection.find_one({"documentId": document_id})
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    collection_id = document["collectionId"]

    # 문서 삭제
    documents_collection.delete_one({"documentId": document_id})

    # 컬렉션 문서 수 업데이트
    doc_count = documents_collection.count_documents({"collectionId": collection_id})
    collections_collection.update_one(
        {"collectionId": collection_id},
        {"$set": {"documentCount": doc_count, "updatedAt": datetime.now()}}
    )

    return APIResponse(success=True)
