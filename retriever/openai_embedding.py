# 임베딩 모델
from langchain_openai import OpenAIEmbeddings

embed = OpenAIEmbeddings(
    model="text-embedding-3-large",
    dimensions=1024
)