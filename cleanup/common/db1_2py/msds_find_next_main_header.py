import re
from typing import List, Dict, Optional

def find_next_main_header(
    all_headers: List[Dict], 
    start_header_str: str
) -> Optional[str]:
    """
    시작 헤더의 '구조적 패턴'과 '메인 숫자'를 모두 사용하여 다음 헤더를 찾는 함수
    """
    # --- 1. 시작 헤더에서 '구조적 패턴'과 '메인 숫자'를 동적으로 분석 ---
    
    # "SECTION 1:", "1.", "제1장" 등의 패턴을 분석하여 prefix, number, separator를 추출
    match = re.search(r"^(.*?)\s*(\d+)([\.:\)]?)\s*", start_header_str)
    if not match:
        return None # 시작 헤더의 구조를 분석할 수 없으면 포기
    
    prefix, start_main_number, separator = match.groups()
    
    # 메인 헤더를 식별하기 위한 정규식 패턴 생성
    main_header_pattern = re.compile(
        f"^{re.escape(prefix.strip())}\\s*\\d+\\s*{re.escape(separator)}.*", 
        re.IGNORECASE
    )

    # --- 2. 전체 헤더 목록에서 시작점 찾기
    start_index = -1
    header_strings = [h.get('heading', '') for h in all_headers]
    for i, h_str in enumerate(header_strings):
        if main_header_pattern.match(h_str):
            num_match = re.search(r"(\d+)", h_str)
            if num_match and num_match.group(1) == start_main_number:
                start_index = i
                break
    
    if start_index == -1:
        return None

    # --- 3. 다음 메인 헤더 탐색 ---
    for i in range(start_index + 1, len(header_strings)):
        next_header_str = header_strings[i]
        
        # 다음 후보가 '메인 헤더 패턴'과 일치하는지지
        if main_header_pattern.match(next_header_str):
            next_header_match = re.search(r"(\d+)", next_header_str)
            if not next_header_match:
                continue
            
            next_main_number = next_header_match.group(1)

            # 조건 2: 메인 번호가 다른지지
            if next_main_number != start_main_number:
                # 두 조건을 모두 만족하면, 진짜 다음 메인 헤더
                return next_header_str
    
    return None