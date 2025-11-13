import re

def extract_section_content(text, start_pattern, end_pattern=None):
    """정규식 패턴으로 섹션을 찾아서 추출하는 함수"""

    start_regex = re.compile(start_pattern, re.MULTILINE | re.IGNORECASE)
    start_match = start_regex.search(text)

    if not start_match:
        print(f"[WARN] 시작 패턴 '{start_pattern}'을 텍스트에서 찾을 수 없습니다.")
        return None

    start_index = start_match.start()
    end_index = len(text)

    if end_pattern:
        end_regex = re.compile(end_pattern, re.MULTILINE | re.IGNORECASE)
        # pos=start_match.end(): 시작 헤더 바로 뒤부터 검색 시작
        end_match = end_regex.search(text, pos=start_match.end())
        if end_match:
            end_index = end_match.start()
        else:
            print(f"[INFO] 종료 패턴 '{end_pattern}'을 찾지 못해 문서 끝까지 추출합니다.")

    return text[start_index:end_index]