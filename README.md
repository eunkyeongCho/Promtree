# ETL

## .env 세팅
ai를 활용하기 위해 임시로 openai를 활용하였습니다.
이 부분을 가우스나 다른 ai로 수정하여 활용할 수 있습니다.
임시로 사용한 .env 구성은 다음과 같습니다.
sample.env -> .env로 수정하면 바로 사용이 가능합니다.
```
OPENAI_API_KEY=sk-...
```

## 의존성 설치
```
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
```

## 사용법
1. "markdown" 폴더 내부에 "markdown/msds"와 "markdown/tds"를 생성합니다.
2. 파싱된 문서를 각각의 폴더에 저장합니다.
3. 데이터를 추출할 프로그램을 실행합니다.
```
python msds.py
```
```
python tds.py
```
4. output에 각각 "output/msds", "output/tds"에 json 형태로 저장되어 있는 데이터를 확인할 수 있습니다.