def pdf_to_md(pdf_path):

    from app.promtree.parsing import converter_init, image_processor_init, parse_pdf
    
    return parse_pdf(pdf_path, converter_init(), image_processor_init())


def msds_extract():
    pass


def tds_extract():
    pass


def md_to_core(md_text, collection_type):
    if collection_type == "msds":
        msds_extract(md_text)
    elif collection_type == "tds":
        tds_extract(md_text)
    else:
        print("잘못된 입력입니다.")
    
    print("Core 데이터 추출 완료")


def md_to_rag(md_text, file_uuid, file_name, collection_type):
    from app.rag.pdf_ingestion_pipeline import PdfIngestionPipeline
    PdfIngestionPipeline().run_pdf_ingestion_pipeline(
        md_text,
        file_uuid,
        file_name,
        [collection_type],  # 필요에 따라 ["msds", "tds"] 등으로 변경 가능
    )

    print("임베딩, 인덱싱, 관계 추출 완료")

if __name__ == "__main__":
    markdown_text = pdf_to_md("./pdfs/coll1/sample.pdf")
    coll_type = "msds"
    file_uuid = "uuid-1234-4567"
    file_name = "sample"

    md_to_core(markdown_text, coll_type)
    md_to_rag(markdown_text, file_uuid, file_name, coll_type)