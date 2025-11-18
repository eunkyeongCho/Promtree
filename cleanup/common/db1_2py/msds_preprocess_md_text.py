from msds_db_regex import PAGE_NAV_PAT, PAGE_MARK_PAT, HTML_TAG_LINE_PAT
import re

# 이 함수는 외부에서 쉽게 호출할 수 있도록 md_text만 인수로 받습니다.
def preprocess_md_text(md_text: str) -> str:
    """
    마크다운 텍스트에서 불필요한 반복 정보(SDS 헤더, 페이지 마커) 및
    노이즈(이미지 태그, HTML 태그)를 제거하는 전처리 함수.
    """
    FIXED_REPEATED_TEXT_PAT = re.compile(
        r"(?:SAFETY\s+DATA\s+SHEET|물질안전보건자료|"
        r"Version\s+\d+\.\d+|Revision\s+Date\s+.*?|Print\s+Date\s+.*?)\s*", 
        re.I
    )
    processed_text = FIXED_REPEATED_TEXT_PAT.sub('', md_text)

    # 2. 이미지 태그 제거 (마크다운 및 임의 형식)
    MD_IMAGE_TAG_PAT = re.compile(r'!\[.*?\]\(.*?\)')
    
    CUSTOM_IMAGE_TAG_PAT = re.compile(r'\[\s*Image\s+of\s+.*?\]', re.I)

    processed_text = MD_IMAGE_TAG_PAT.sub('', processed_text)
    processed_text = CUSTOM_IMAGE_TAG_PAT.sub('', processed_text)

    # 3. 페이지 마커 및 HTML 노이즈 제거 (msds_db_regex에서 가져온 패턴 활용)
    lines = processed_text.splitlines()
    clean_lines = []
    
    for line in lines:
        # a. 페이지 네비게이션/마커 라인 제거 (예: "2/12", ">>> page 3")
        if PAGE_NAV_PAT.match(line) or PAGE_MARK_PAT.match(line):
            continue
        
        # b. 한 줄 전체가 HTML 태그인 경우 제거 (예: <div>)
        if HTML_TAG_LINE_PAT.match(line):
            continue
        
        clean_lines.append(line)
        
    return '\n'.join(clean_lines)