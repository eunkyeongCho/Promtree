from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

from fastapi import HTTPException, UploadFile, status


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PDF_ROOT = PROJECT_ROOT / "pdfs"


def _ensure_pdfs_root() -> None:
    PDF_ROOT.mkdir(parents=True, exist_ok=True)


def _assert_safe_name(name: str) -> str:
    trimmed = name.strip()
    if not trimmed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="컬렉션 이름은 비워둘 수 없습니다.",
        )
    if "/" in trimmed or "\\" in trimmed or ".." in trimmed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="폴더 이름에 허용되지 않은 문자가 포함되어 있습니다.",
        )
    return trimmed


def get_collection_dir(name: str) -> Path:
    safe_name = _assert_safe_name(name)
    _ensure_pdfs_root()
    path = PDF_ROOT / safe_name
    path.mkdir(parents=True, exist_ok=True)
    return path


def rename_collection_dir(old_name: str, new_name: str) -> Path:
    safe_new_name = _assert_safe_name(new_name)
    _ensure_pdfs_root()
    old_path = PDF_ROOT / _assert_safe_name(old_name)
    new_path = PDF_ROOT / safe_new_name
    if old_path.exists():
        if new_path.exists():
            shutil.rmtree(new_path)
        old_path.rename(new_path)
    else:
        new_path.mkdir(parents=True, exist_ok=True)
    return new_path


def delete_collection_dir(name: str) -> None:
    path = PDF_ROOT / _assert_safe_name(name)
    if path.exists():
        shutil.rmtree(path)


def delete_document_file(collection_name: str, filename: str) -> None:
    folder = PDF_ROOT / _assert_safe_name(collection_name)
    file_path = folder / Path(filename).name
    if file_path.exists():
        file_path.unlink()


def _resolve_unique_path(folder: Path, filename: str) -> Path:
    candidate = folder / filename
    if not candidate.exists():
        return candidate
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    counter = 1
    while True:
        new_name = f"{stem}_{counter}{suffix}"
        candidate = folder / new_name
        if not candidate.exists():
            return candidate
        counter += 1


async def save_pdf_file(collection_name: str, upload: UploadFile) -> Path:
    folder = get_collection_dir(collection_name)
    original_name = upload.filename or "document.pdf"
    safe_name = Path(original_name).name
    target = _resolve_unique_path(folder, safe_name)
    chunk_size = 1024 * 1024
    with target.open("wb") as buffer:
        while True:
            chunk = await upload.read(chunk_size)
            if not chunk:
                break
            buffer.write(chunk)
    await upload.close()
    return target


async def mark_document_success(document, delay_seconds: float = 10.0) -> None:
    try:
        await asyncio.sleep(delay_seconds)
        document.status = "success"
        await document.save()
    except Exception:
        # 문서가 삭제되거나 저장에 실패해도 서버 에러로 이어지지 않도록 무시
        return

