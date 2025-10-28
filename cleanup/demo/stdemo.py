import streamlit as st
import promtree
import pyplum
import os
from dotenv import load_dotenv

load_dotenv()

USERNAME = os.getenv("MONGO_USERNAME")
PASSWORD = os.getenv("MONGO_PASSWORD")
HOST = os.getenv("MONGO_HOST")
PORT = int(os.getenv("MONGO_PORT"))

# --------------------------
# MongoDB 연결
url = f"mongodb://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/"

pdf_files = os.listdir("pdfs")

os.makedirs("storage", exist_ok=True)
os.makedirs("evaluation_outputs", exist_ok=True)
output_dir = "evaluation_outputs"

pt = promtree.PromTree()
pt.set_mongodb(url, "s307_db", "s307_collection")


st.set_page_config(layout="wide")
st.title("PromTree Demo")
st.write("Parser의 추출 정확도를 평가하는 라이브러리 PromTree의 데모 페이지입니다.")

parsing = False
parsing_finished = False
regeneration_finished = False
evaluation_finished = False

parsing = st.button("PDF 파일 파싱")

if parsing:
    with st.spinner("PDF 파일을 파싱 중입니다..."):
        pt.parse_all_pdfs(pdf_files)
        parsing_finished = True
    st.success("PDF 파일 파싱이 완료되었습니다.")

if parsing_finished:
    with st.spinner("PDF Regeneration 중입니다..."):
        pt.regenerate_all_pdfs(pdf_files, output_dir)
        regeneration_finished = True
    st.success("PDF Regeneration 완료되었습니다.")

if regeneration_finished:
    with st.spinner("PDF Evaluation 중입니다..."):
        evaluation = pt.eval(pdf_files, output_dir, 150)
        evaluation_finished = True
    st.success("PDF Evaluation 완료되었습니다.")
    st.subheader("평가 결과")
    st.write(evaluation)


if evaluation_finished:
    st.write("PDF 파싱 결과물 직접 확인")

    for pdf_file in pdf_files:
        col1, _, _, col2 = st.columns([2, 0.1, 0.1, 2])
        with col1:
            st.write(f"원본 PDF 파일: {pdf_file}")
            try:
                with open(f"pdfs/{pdf_file}", "rb") as f:
                    st.pdf(f, height=750, key=f"pdf-original-{pdf_file}")
            except Exception as e:
                st.error(f"원본 PDF 로드 실패: {e}")
        with col2:
            regenerated_name = pdf_file.replace(".pdf", "_regenerated.pdf")
            st.write(f"추출한 데이터로 생성한 PDF 파일: {regenerated_name}")
            try:
                with open(f"evaluation_outputs/{regenerated_name}", "rb") as f:
                    st.pdf(f, height=750, key=f"pdf-extracted-{pdf_file}")
            except Exception as e:
                st.error(f"Regenerated PDF 로드 실패: {e}")
        st.markdown("---")

