from __future__ import annotations
import re

"""
물질안전보건자료(MSDS/SDS) 텍스트 분석 및 정보 추출을 위한 정규표현식 패턴 모음.

이 모듈은 MSDS/SDS 문서의 다양한 섹션(예: 1장 제품 정보, 2/3장 구성성분)의
헤더를 식별하고, 제품명, 회사 정보, 연락처, 주소 등 특정 정보를 추출하기 위한
정규식들을 정의합니다. 또한, 텍스트 정제에 사용되는 패턴들도 포함합니다.

주요 기능:
- **섹션 헤더 식별**: 한글/영문 SDS의 다양한 표기법을 고려한 섹션 헤더 패턴.
- **정보 라벨 식별**: 제품명, 회사명 등 정보 유형을 나타내는 라벨 패턴.
- **데이터 형식 식별**: CAS 번호, 이메일, URL 등 특정 데이터 형식 패턴.
- **텍스트 정제**: 제어 문자, 불필요한 공백, 페이지 번호 등을 제거하기 위한 패턴.
- **사전 컴파일된 정규식**: 자주 사용되는 패턴들을 `re.compile`로 미리 컴파일하여 성능 최적화.
"""


# 영문 SDS의 Section 1 헤더(Identification / Product and Company Identification 등)를 다양한 표기 변형으로 매칭하는 패턴 목록.
SEC1_PATTERNS_EN = [
    r"^\s*(?:section\s*)?(?:i|1|01)\s*[:.)\-–—]*\s*(?:identification|product\s+identification|product\s+and\s+company\s+identification)\b",
    r"^\s*0*1\s*[:.)\-–—]*\s*identification\b",
    r"^\s*(?:section\s*1)\s*[:.)\-–—]*\s*identification\b",
]

# 한글 SDS의 1장/섹션 헤더(제품 및 회사에 관한 정보/식별)를 번호·접두 텍스트·문장 구성 변형까지 포함하여 매칭하는 패턴 목록.
SEC1_PATTERNS_KO = [
    r"^\s*(?:##?\s*)?(?:section|섹션)?\s*0*1\s*[:.)\-–—]?\s*(?:화학제품|제품)\s*과?\s*(?:회사|사업장)\s*(?:에\s*관한\s*정보|식별|정보)\s*$",
    r"^\s*(?:##?\s*)?0*1\s*[.)]\s*(?:화학제품|제품)\s*과?\s*(?:회사|사업장)\s*(?:에\s*관한\s*정보|식별|정보)\s*$",
    r"^\s*제?\s*0*1\s*(?:장|부)\s*[:.)\-–—]?\s*(?:화학제품|제품)\s*과?\s*(?:회사|사업장)\s*(?:에\s*관한\s*정보|식별|정보)\s*$",
]

# 최소한 “1:” 같이 숫자+구분자 뒤에 임의 제목이 오는 느슨한 1장 헤더 폴백 매칭용 패턴.
SEC1_PATTERNS_FALLBACK = [
    r"^\s*(?:##?\s*)?0*1\s*[:.)\-–—]\s+.+$",
]

# 한글 SDS의 2장 “유해성 및 위험성”을 엄격한 형태(완전 일치, 문장 끝 고정)로 매칭하는 패턴 목록.
SEC23_PATTERNS_KO_STRICT = [
    r"^\s*(?:##+\s*)?\s*0*2\s*[\.\):\-–—]?\s*유해성\s*(?:및)?\s*위험성\s*$",
    r"^\s*(?:##+\s*)?\s*제?\s*0*2\s*(?:장|부)\s*[\.\):\-–—]?\s*유해성\s*(?:및)?\s*위험성\s*$",
]

# 한글 SDS의 2장 “유해성 및 위험성”을 느슨하게(접미 텍스트 허용) 매칭하는 패턴 목록.
SEC23_PATTERNS_KO_LOOSE = [
    r"^\s*(?:##+\s*)?\s*0*2\s*[\.\):\-–—]?\s*유해성\s*(?:및)?\s*위험성\b",
    r"^\s*(?:##+\s*)?\s*제?\s*0*2\s*(?:장|부)\s*[\.\):\-–—]?\s*유해성\s*(?:및)?\s*위험성\b",
]

# 영문 SDS의 Section 2 Hazard(s) 헤더를 다양한 기입 변형(Section/sect. 02 등)으로 매칭하는 패턴 목록.
SEC23_PATTERNS_EN = [
    r"^\s*(?:##+\s*)?\s*(?:section|sect\.)?\s*0*2\s*[:\.\)\-–—]?\s*(?:hazard|hazards)\b",
]

# 2: 또는 3: 뒤에 임의 제목이 오는 식의 느슨한 2·3장 헤더 폴백 검출용 패턴.
SEC23_PATTERNS_FALLBACK = [
    r"^\s*(?:##+\s*)?\s*[23]\s*[:\.\)\-–—]\s+.+$",
]

# 위의 SEC1 관련 영문/한글/폴백 패턴들을 OR로 합친 컴파일 결과. Section 1 헤더를 한 번에 판별하는 정규식 객체.
SEC1_RE  = re.compile("|".join(SEC1_PATTERNS_EN + SEC1_PATTERNS_KO + SEC1_PATTERNS_FALLBACK), re.I)
# 한글 엄격 패턴 + 영문 패턴을 OR로 합친 컴파일 결과. 2장(유해성) 헤더의 엄격 매칭 용도.
SEC23_RE_STRICT = re.compile("|".join(SEC23_PATTERNS_KO_STRICT + SEC23_PATTERNS_EN), re.I)
# 느슨 한글 + 영문 + 폴백 패턴을 OR로 합친 컴파일 결과. 2/3장 주변 헤더를 느슨하게 탐지.
SEC23_RE_LOOSE  = re.compile("|".join(SEC23_PATTERNS_KO_LOOSE  + SEC23_PATTERNS_EN + SEC23_PATTERNS_FALLBACK), re.I)

# 현재페이지/전체페이지 같은 페이지 네비게이션 라인(예: “2/12”, “3-10”) 제거/무시용 패턴.
PAGE_NAV_PAT      = re.compile(r"^\s*\d+\s*[/\-]\s*\d+\s*$")
# “>>> page 3” 같은 페이지 마커 줄을 걸러내기 위한 패턴.
# PAGE_MARK_PAT     = re.compile(r"^\s*>>>+\s*page\s+\d+\s*$", re.I)
PAGE_MARK_PAT = re.compile(r"^\s*>{2,}\spage[\s_\-]\d+(?:\s*(?:of|/)\s*\d+)?\s*$", re.I)
# 한 줄 전체가 HTML 태그 형태인 경우(예: “<div>”)를 제거하기 위한 패턴.
HTML_TAG_LINE_PAT = re.compile(r"^\s*<[^>]+>\s*$", re.I)

# 제품명/식별자 라벨(영문·한글)의 다양한 표기 후보 리스트. 키-값 추출 시 라벨 인식용.
PRODUCT_LABELS = [
    r"product\s*name", r"product\s*identifier", r"product\s*number", r"product\s*code",
    r"recommended\s*product\s*name", r"trade\s*name",
    r"상품명", r"제품명", r"제품\s*식별자", r"상표명", r"제품\s*명", r"화학제품\s*명", r"물질\s*명",
]

# 회사/제조사/공급자 등 공급 주체 라벨의 다양한 표기 후보 리스트. 연락처/회사 정보 블록 추출 시 라벨 인식용.
COMPANY_LABELS = [
    r"company", r"manufacturer", r"manufactured\s*by", r"supplier", r"distributor", r"importer",
    r"responsible\s*(party|company)", r"producer", r"registrant",
    r"회사명", r"제조사", r"제조업체", r"공급자", r"공급업체", r"수입사", r"수입업체", r"책임회사", r"제조회사", r"판매사", r"판매업체", r"공급처", r"제조원", r"판매원", r"책임판매업자", r"수입원",
]

# product name/제품명 등 제품명 라벨만 단독으로 적힌 안전한 헤더 라인(라벨 단독 라인) 매칭용 정규식.
SAFE_NAME_LABEL = re.compile(
    r"^\s*(product\s*name|product\s*identifier|product\s*number|product\s*code|recommended\s*product\s*name|"
    r"trade\s*name|상품명|제품명|제품\s*식별자|상표명|제품\s*명|화학제품\s*명|물질\s*명)\s*$",
    re.I
)

# company/제조사/공급자… 등 회사 라벨만 단독으로 적힌 안전한 헤더 라인 매칭용 정규식.
SAFE_COMPANY_LABEL = re.compile(
    r"^\s*(company|manufacturer|manufactured\s*by|supplier|distributor|importer|responsible\s*(party|company)|"
    r"producer|registrant|회사명|제조사|제조업체|공급자|공급업체|수입사|수입업체|책임회사|제조회사|판매사|판매업체|공급처|제조원|판매원|책임판매업자|수입원)\s*$",
    re.I
)

# 섹션 타이틀/헤더성 문구 배제용 정규식
HEADER_BAD_FOR_COMPANY = re.compile(
    r'\b(identification|substance|mixture|company/undertaking|details\s+of\s+the\s+supplier|product\s+identifier)\b',
    re.I
)

# 주소 판별에 자주 등장하는 영문/한글 단어 세트(road, st., 대로, 구 등). 주소 탐지 보조용 토큰 목록.
ADDR_WORDS = (
    r"(street|st\.|road|rd\.|avenue|ave\.|blvd\.|drive|dr\.|way|highway|hwy\.|park|suite|ste\.|floor|fl\.|"
    r"building|bldg\.|route|industrial|parkway|pkwy\.|unit|no\.|"
    r"로|길|번길|대로|동|구|군|시|도|읍|면|리|산단|산업단지|단지|지구|번지|호)"
)
# 숫자+지명+주소어 조합, 우편번호/Postal/ZIP/일본식 〒 등 주소 패턴 전반을 포괄적으로 매칭하는 정규식
ADDR_PAT  = re.compile(
    rf"(\d+\s+[A-Za-z가-힣0-9\-]+(?:\s+{ADDR_WORDS})|\b{ADDR_WORDS}\b|\bZIP\b|\bPostal\b|\b〒\b|\b\d{{3}}[-\s]?\d{{3}}\b|\b\d{{5}}(?:-\d{{4}})?\b)",
    re.I
)

# tel/phone/fax/emergency/전화/팩스 등 키워드 또는 국제전화 형식(+국가코드-번호)을 포착하는 전화·팩스 등 연락처 매칭용.
PHONE_PAT = re.compile(r"\b(tel|phone|fax|mobile|emergency|hotline|전화|팩스)\b|\+\d{1,3}[-\s]?\d{1,4}", re.I)

# 연락처 섹션을 가리키는 라벨/키워드 감지(숫자 형식이 없어도 매치).
CONTACT_LABEL_RE = re.compile(
    r'\b(tel|phone|fax|mobile|emergency|hotline|contact|긴급|긴급전화|긴급전화번호|전화|전화번호|연락처)\b',
    re.I
)
# 표준 이메일 주소 형식을 감지하는 정규식.
EMAIL_PAT = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# http/https/www로 시작하는 URL을 간단 매칭하는 정규식.
WEB_PAT   = re.compile(r"(https?://|www\.)\S+", re.I)

# 저작권/배포 제한/면책 고지 등 문서 하단 저작권 관련 문구를 식별해 본문 추출에서 배제하기 위한 키워드 패턴.
COPYRIGHT_STOPWORDS = re.compile(
    r"(저작권|판권|배포|복사|다운로드|허용|동의|재판매|재산상|이득|규제|면제|예외|"
    r"copyright|all\s+rights\s+reserved|distribution|redistribution|reproduce|copy|download|permitted|consent|resale|profit|disclaimer|exception|exempt|regulation)",
    re.I
)

# SDS/MSDS 문서 제목 라인(“SAFETY DATA SHEET”, “물질안전보건자료” 등)을 감지해 메타 타이틀을 본문 처리에서 분리하기 위한 패턴.
DOC_TITLE_STOP = re.compile(
    r"(제품안전취급서|물질안전보건자료서?|MSDS|SDS|MATERIAL\s+SAFETY\s+DATA\s+SHEET|SAFETY\s+DATA\s+SHEET)",
    re.I
)

# 영문 법인 접미사(Inc., Ltd., GmbH, LLC 등)나 한글 법인 형태(주식회사, (주) 등)를 포함한 회사명 후보를 폭넓게 매칭하는 정규식.
COMPANY_CAND_PAT = re.compile(
    r"((?:[A-Z][A-Za-z&.,\-\s]{1,60}\b(?:Co\.?,?\s*Ltd\.?|Company|Corporation|Corp\.?|Inc\.?|LLC|GmbH|"
    r"S\.?A\.?|S\.?p\.?A\.?|Ltd\.?|LP|LLP|BV|NV|KK))|"
    r"(?:주식회사|유한회사|유한책임회사|합자회사|합명회사|\(주\))\s*[A-Za-z가-힣0-9&.\-\s]{1,40}|"
    r"(?:[A-Za-z가-힣0-9&.\-\s]{1,40}\s*(?:주식회사|유한회사|유한책임회사|\(주\)))|"
    r"(?:3M|Shell|Praxair)\s*(?:Company|Corp\.?|Inc\.?|Korea\s*Co\.?,?\s*Ltd\.?)?)",
    re.I
)

# “CAS No.”, “UN No.”, “EU No.”, “KE No.” 같은 코드 라벨 키워드 감지용 정규식.
CODE_LABEL_RX = re.compile(r"\b(CAS|UN|EU|KE)\s*No\.?\b", re.I)
# 실제 코드 값 포맷(CAS 00000-00-0, KE-xxxxxx, 단순 숫자 코드 등)을 검증/추출하기 위한 값 패턴 정규식.
CODE_VALUE_RX = re.compile(r"^(?:KE-\d+|\d{2,7}-\d{2}-\d|\d{3,5}|\d{3}-\d{4})$", re.I)


# 제어문자 및 특수 공백 제거를 위한 패턴
# CONTROL_WS = re.compile(r"[\u0000-\u0009\u000B-\u000C\u000E-\u001F\u007F\u00A0\u2000-\u200B\u2028\u2029\uFEFF]")
CONTROL_WS = re.compile(r"[\u0000-\u0009\u000B-\u000C\u000E-\u001F\u007F\u00A0\u00AD\u2000-\u200B\u2028\u2029\u2060\uFEFF]")
# 점(·•‧∙●∘・｡。．)과 유사한 문자를 모두 '.'으로 통일하기 위한 매핑 테이블
DOT_LIKE = dict.fromkeys(map(ord, "·•‧∙●∘・｡。．"), ord('.'))

# 전각/호환 문자를 ASCII로 통일하기 위한 매핑
FULLWIDTH = {
    ord("（"): ord("("), ord("）"): ord(")"),
    ord("："): ord(":"),
    ord("．"): ord("."),
    ord("－"): ord("-"), ord("—"): ord("-"), ord("–"): ord("-"),
}

# 헤더/식별 배제
HEADER_EXCLUDE_RE = re.compile(r'\b(section|identifier|identification|product\s+identifier)\b', re.I)

# 1.x 서브섹션 감지 하위 절 중 "1.x"로 시작하는 섹션 번호만 감지.
SUBSEC_1X_RE = re.compile(r'^\s*(?:#{1,6}\s*)?1\.\d+\b', re.I)

# Markdown 헤더 라인
MD_HEADER_RE = re.compile(r'^\s*#{1,6}\s+')

# Section 1 내에서 종료 힌트 라벨
SEC1_END_HINT_RE = re.compile(r'\b(emergency\s+telephone|manufacturer|supplier)\b', re.I)



#######Ingredients 단독######


# 구분자
# 헤더 번호 뒤에 따라오는 대표 구분자 집합 (: . ) - – —)
DASH_CLASS = r"[:\.\)\-\u2013\u2014]"
# 헤더 내부/사이 구분자(공백 포함) 확장 집합
SEP = r"[:\s\.\)\-\u2013\u2014]"

# 루트 헤더
# "section N" (마크다운 해시 허용), "N{구분자}", "로마숫자{구분자}" 패턴
# N은 1~16, 로마숫자는 i~xvi까지 지원
ROOT_ANY_RX = re.compile(
    rf"^\s*(?:(?:##+\s*)?section\s*(?:[1-9]|1[0-6]|i|ii|iii|iv|v|vi|vii|viii|ix|x|xi|xii|xiii|xiv|xv|xvi)\s*{DASH_CLASS}?|"
       r"(?:##+\s*)?(?:[1-9]|1[0-6])\s*{DASH_CLASS}|"
       r"(?:##+\s*)?(?:i|ii|iii|iv|v|vi|vii|viii|ix|x|xi|xii|xiii|xiv|xv|xvi)\s*{DASH_CLASS})",
    re.I
)

# 서브섹션 탐지
# "3.2", "3.2.", "3 . 2", "3.2.1" 등 변형 포함
SUBSEC_RX = re.compile(r"^\s*(?:##+\s*)?\d+\s*\.\s*\d+(?:\s*\.\s*\d+)*\s*[.)]?\b", re.I)

# 헤더 힌트(EN): 성분/조성 영역을 지칭하는 영문 표현
HEAD_HINTS_EN = [
    r"composition\s*/\s*information\s*on\s*ingredients",
    r"composition\s*and\s*information\s*on\s*ingredients",
    r"composition\s*,\s*information\s*on\s*ingredients",
    r"composition\s*information\s*on\s*ingredients",
    r"information\s*on\s*ingredients",
    r"ingredients",
    r"data\s*on\s*components",
    r"components",
]
# 헤더 힌트(KO): 성분/조성 관련 한글 표현
HEAD_HINTS_KO = [
    r"구성성분의\s*명칭\s*및\s*함유량",
    r"구성성분의\s*명칭\s*및\s*조성",
    r"구성\s*성분",
    r"성분",
    r"조성",
]
# 성분/조성 헤더 힌트 통합 정규식
HEAD_HINTS_RE = re.compile("|".join([rf"\b{h}\b" for h in HEAD_HINTS_EN] + HEAD_HINTS_KO), re.I)

# 루트 폴백 힌트: 섹션 분류 키워드(EN/KO)
FALLBACK_ROOT_HINTS = re.compile(
    r"(first[-\s]?aid|응급조치|응급조치요령|handling|storage|취급|저장|"
    r"physical|물리화학|stability|안정성|reactivity|반응성|toxicological|독성|ecological|환경|"
    r"disposal|폐기|transport|운송|regulatory|법적|other|기타)", re.I)


# 정규화

# 허용 단위 화이트리스트(정규화 이후 기준)
UNIT_WHITELIST = {"%", "ppm", "ppb", "mg/L", "g/L", "mg/kg", "g/kg"}

# basis(혼합 기준) 추론을 위한 표현 패턴 목록과 정규화 결과 매핑
BASIS_PATTERNS = [
    (re.compile(r"\b(w/?w)\b", re.I), "w/w"),
    (re.compile(r"\b(v/?v)\b", re.I), "v/v"),
    (re.compile(r"\bwt\s*%\b", re.I), "w/w"),
    (re.compile(r"(중량\s*%|w/w\s*%)", re.I), "w/w"),
    (re.compile(r"(부피\s*%|v/v\s*%)", re.I), "v/v"),
    (re.compile(r"%\s*\(\s*w\s*/\s*w\s*\)", re.I), "w/w"),
    (re.compile(r"%\s*\(\s*v\s*/\s*v\s*\)", re.I), "v/v"),
]

# 동의어 토큰 분할용 구분자(쉼표/세미콜론/슬래시/수직바/개행)
DELIMS_RX = re.compile(r"[;,/|\n]+")

# 범위
RANGE_RX = re.compile(r"^\s*(?:~|≈)?\s*(\d+(?:\.\d+)?)\s*[-–~]\s*(\d+(?:\.\d+)?)\s*%?\s*$")
LT_RX    = re.compile(r"^\s*[<≤]\s*(\d+(?:\.\d+)?)\s*%?\s*$")
EQ_RX    = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*%?\s*$")

# 비밀
CONF_TOKENS = {
    "영업 비밀","영업비밀","비공개","미공개","자료 없음",
    "confidential","trade secret","not available","n/a","na","not applicable"
}