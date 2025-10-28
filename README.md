<div style="width: 1000px; margin: 0 auto;">

# 자율 프로젝트 대전 2반(기업연계 S3) 7조

### 삼성전자 생산기술연구소 연계 프로젝트 (RAG, 챗봇)

## 팀 소개 (Team.PromTree)

<div style="display: flex; justify-content: center;">
  <table>
    <tr>
      <td height="140px" align="center">
        <a href="https://github.com/jeonhaejidev">
          <img src="images/해지.jpg" width="140px" height="140px" /><br><br>
          전해지 <br>
          (Team-Leader)
        </a>
        <br>
      </td>
      <td height="140px" align="center">
        <a href="https://github.com/yang-yang140">
          <img src="images/현지.png" width="140px" height="140px" /><br><br>
          양현지 <br>
          (ChatBot)
        </a>
        <br>
      </td>
      <td height="140px" align="center">
        <a href="https://github.com/Yoo-SeungHyeon">
          <img src="images/승현.png" width="140px" height="140px" /><br><br>
          유승현 <br>
          (Parser)
        </a>
        <br>
      </td>
      <td height="140px" align="center">
        <a href="https://github.com/hitoriudon">
          <img src="images/석철.png" width="140px" height="140px" /><br><br>
          이석철 <br>
          (Parser)
        </a>
        <br>
      </td>
      <td height="140px" align="center">
        <a href="https://github.com/eunkyeongCho">
          <img src="images/은경.png" width="140px" height="140px" /><br><br>
          조은경 <br>
          (Parser)
        </a>
        <br>
      </td>
      <td height="140px" align="center">
        <a href="https://github.com/InHyuk-Choi">
          <img src="images/인혁.png" width="140px" height="140px" /><br><br>
          최인혁 <br>
          (ChatBot)
        </a>
        <br>
      </td>
    </tr>
    <tr>
      <td align="center" style="text-align:center;">
        Python</br>
        LangChain</br>
        PyPlumber</br>
        PyEnv</br>
        Venv</br>
        Streamlit</br>
      </td>
      <td align="center" style="text-align:center;">
        Python</br>
        LangChain</br>
        PyPlumber</br>
        PyEnv</br>
        Venv</br>
        Streamlit</br>
      </td>
      <td align="center" style="text-align:center;">
        Python</br>
        LangChain</br>
        PyPlumber</br>
        PyEnv</br>
        Venv</br>
        Streamlit</br>
      </td>
      <td align="center" style="text-align:center;">
        Python</br>
        LangChain</br>
        PyPlumber</br>
        PyEnv</br>
        Venv</br>
        Streamlit</br>
      </td>
      <td align="center" style="text-align:center;">
        Python</br>
        LangChain</br>
        PyPlumber</br>
        PyEnv</br>
        Venv</br>
        Streamlit</br>
      </td>
      <td align="center" style="text-align:center;">
        Python</br>
        LangChain</br>
        PyPlumber</br>
        PyEnv</br>
        Venv</br>
        Streamlit</br>
      </td>
    </tr>
  </table>
</div>

</br>



## 프로젝트 기간

**2025-10-10 ~ 2025-11-20 (6주)**


## 프로젝트 소개
여러 소재들을 혼합하였을 때 어떤 물성이 나오는지 예측하려고 함. 이때 사내에 쌓인 소재 물성 pdf 파일들에 대하여 DB화 할 수 있는 코드/프로그램이 필요함. DB화된 정보를 바탕으로 *예측 모델을 제작하고 챗봇 형태로 질의 응답을 할 수 있도록 하려고 함.

## 프로젝트 요구사항

### 필수 구현기능
- pdf 파일 내에 있는 소재 물성 정보 추출(정확도 99% 이상)
- 다수의 pdf 파일에서 추출한 물성 정보들 DB화
- LLM UI 사이트 제작(Open Webui, Streamlit 등 활용 가능)
- 해당 UI에서 소재 물성 예측 모델 연동(LLM agent)
- 해당 UI에서 RAG 기능 활용하여 DB에 있는 데이터 관련 질의 연동

### 추가 구현기능
- 소재 물성 예측 모델 간단하게 제작(사내 예측 모델 대외비)
- 사이트에 여러 명이 동시 사용할 수 있도록 LLM 서버 구축

## 프로젝트 개발 요소

### 요구 기술 스택
- **Langchain**: RAG 프레임워크
- **Streamlit, Open Webui**: 웹 기반 UI 개발 프레임워크
- **MongoDB or PostgreSQL**: 데이터를 관리하기 위한 DB(기업 사용이 가능한 무료 DB)

### 개발 언어
- Python

### 개발 환경
- Windows 10 or 11
- DB: MongoDB 또는 PostgreSQL


## 아키텍쳐

![](./images/architecture.png)

</div>