from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter
)
from typing import List


def hybrid_chunking(contents: List[str], chunk_size: int = 1000, chunk_overlap: int = 100, min_chunk_size: int = None) -> List[str]:
    """
    하이브리드 청킹: ## 헤더 기반 분리 + RecursiveCharacterTextSplitter + 작은 청크 병합

    Args:
        contents: 파싱된 문자열 리스트
        chunk_size: 청크 최대 크기 (기본값: 1000)
        chunk_overlap: 청크 간 오버랩 크기 (기본값: 100)
        min_chunk_size: 청크 최소 크기. 이보다 작은 청크는 다음 청크와 병합 (기본값: chunk_size의 30%)

    Returns:
        청킹된 문자열 리스트
    """
    # 최소 청크 크기 설정 (기본값: chunk_size의 30%)
    if min_chunk_size is None:
        min_chunk_size = int(chunk_size * 0.3)

    # 1단계: 문자열 리스트를 하나로 합치기
    merged_text = "\n".join(contents)

    # 2단계: ## 헤더로 분리
    headers_to_split_on = [
        ("##", "Header 2"),
    ]

    markdown_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on,
        strip_headers=False
    )

    # ## 헤더로 분리
    md_header_splits = markdown_splitter.split_text(merged_text)

    # 3단계: 너무 긴 섹션은 추가 분리
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )

    all_chunks = []

    if md_header_splits:
        # 헤더로 분리된 각 섹션에 대해 처리
        for section in md_header_splits:
            section_text = section.page_content

            # 섹션이 chunk_size보다 크면 추가 분리
            if len(section_text) > chunk_size:
                chunks = text_splitter.split_text(section_text)
                all_chunks.extend(chunks)
            else:
                all_chunks.append(section_text)
    else:
        # ## 헤더가 없는 경우 전체를 크기 기반으로 분리
        chunks = text_splitter.split_text(merged_text)
        all_chunks.extend(chunks)

    # 4단계: 너무 작은 청크는 다음 청크와 병합
    merged_chunks = []
    i = 0
    while i < len(all_chunks):
        current_chunk = all_chunks[i]

        # 현재 청크가 min_chunk_size보다 작고, 다음 청크가 있으면 병합 시도
        while len(current_chunk) < min_chunk_size and i + 1 < len(all_chunks):
            next_chunk = all_chunks[i + 1]
            # 병합 후 chunk_size를 초과하지 않는지 확인
            combined = current_chunk + "\n" + next_chunk
            if len(combined) <= chunk_size:
                current_chunk = combined
                i += 1
            else:
                # 병합하면 너무 커지므로 현재 청크만 추가
                break

        merged_chunks.append(current_chunk)
        i += 1

    return merged_chunks




if __name__ == "__main__":
    import retriever.parsing as parsing
    from pathlib import Path

    retriever_dir = Path(__file__).resolve().parents[1]
    pdf_path = retriever_dir / "3M-1509-DC-Polyethylene-Tape-TIS-Jun13.pdf"

    converter = parsing.converter_init()
    contents = parsing.parse_pdf(pdf_path, converter)
    chunks = hybrid_chunking(contents, chunk_size=1000, chunk_overlap=100)
    for i, chunk in enumerate(chunks):
        print(f"--- Chunk {i+1} ---")
        print(chunk)
        print()