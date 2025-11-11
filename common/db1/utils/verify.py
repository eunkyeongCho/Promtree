"""
MSDS 데이터 검증 보고서 생성기
--------------------------------
MongoDB와 PostgreSQL에 저장된 MSDS 원문과 추출 데이터를 비교 검증하여,
- 섹션 슬라이싱,
- 키워드 존재 여부 검사(정확/느슨 매칭),
- 하이라이트 마크업,
- 통계 요약 및 HTML/PDF 보고서 생성
을 수행합니다.

주의:
- xhtml2pdf의 유니코드/폰트 이슈를 완화하기 위해 meta charset, encoding 인자, 폰트 @font-face를 설정합니다.
"""

import sys
import os
import re
import json
import traceback
from collections import defaultdict
from pathlib import Path
from html import escape
from typing import Set, Dict, Any, Optional, List, Tuple

import psycopg2
import pandas as pd
from xhtml2pdf import pisa
from xhtml2pdf.files import pisaFileObject



try:
    # 상위 디렉토리의 모듈 경로
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'db_1_py'))
    # Mongo/Postgres
    from get_mongo_postgre_db import get_mongodb, get_postgres
    # 섹션 1 슬라이서
    from msds_db_section1_slicer import slice_section1_debug   
    # 섹션 2/3 슬라이서  
    from msds_db_ingredients_slicer import slice_section_2_or_3
except ImportError as e:
    print(f"[중요] 필요한 모듈을 찾을 수 없습니다: {e}")
    print("스크립트 실행 경로와 sys.path 설정을 확인해주세요.")
    sys.exit(1)


# 파일 객체의 getNamedFile이 파일 경로 대신 URI를 그대로 반환하도록 패치합니다.
pisaFileObject.getNamedFile = lambda self: self.uri


def convert_html_to_pdf(source_html: str, output_filename: str) -> bool:
    """
    주어진 HTML 문자열을 PDF 파일로 변환합니다.

    HTML 상단에 <meta charset="UTF-8">가 포함되어 있어야 하며,
    pisa.CreatePDF 호출 시 encoding='UTF-8' 설정을 통해 유니코드 표시 문제를 완화합니다.

    Args:
        source_html (str): 변환할 HTML 소스 문자열. UTF-8 인코딩을 권장합니다.
        output_filename (str): 생성될 PDF 파일 경로(확장자 포함 또는 제외).

    Returns:
        bool: 변환 성공 시 True, 실패 시 False.

    Notes:
        - 한글/유니코드 폰트가 PDF에 임베딩되도록 @font-face와 폰트 파일 경로가 유효해야 합니다.
    """
    try:
        with open(output_filename, "w+b") as result_file:
            pisa_status = pisa.CreatePDF(source_html, dest=result_file, encoding='UTF-8')
        if pisa_status.err:
            print(f"  [오류] PDF 생성 중 문제 발생: {pisa_status.err}")
            return False
        return True
    except Exception as e:
        print(f"  [오류] PDF 파일 작성 중 예외 발생: {e}")
        traceback.print_exc()
        return False


def highlight_text_with_tracking(text_to_highlight: str, keywords_with_source: Dict[str, str]) -> Tuple[str, Set[str]]:
    """
    DB 원문 문자열이 '그대로' 존재하는 항목만 하이라이트(단어 경계 기준)합니다.

    - 대소문자 구분 그대로 비교합니다.
    - 정규식은 커스텀 단어 경계: (?<!\\w)keyword(?!\\w)를 사용합니다.
      이는 우측/좌측이 단어문자가 아님을 보장합니다.

    Args:
        text_to_highlight (str): 하이라이트 대상 원문 텍스트.
        keywords_with_source (Dict[str, str]): {키워드: 출처} 매핑.

    Returns:
        Tuple[str, Set[str]]:
            - 하이라이트된 HTML 문자열(mark 태그 포함, 안전한 escape 적용 후 치환),
            - 발견된 키워드 집합.

    Notes:
        - HTML 인젝션 방지를 위해 기본적으로 escape 후 플레이스홀더 기법으로 중첩 치환을 방지합니다.
        - 긴 키워드부터 치환해 부분 중첩을 줄입니다.
    """
    if not text_to_highlight or not keywords_with_source:
        return escape(text_to_highlight or ""), set()

    highlighted_text = escape(text_to_highlight)
    found_keywords: Set[str] = set()

    # 긴 키워드 우선 치환
    sorted_keywords = sorted(keywords_with_source.keys(), key=len, reverse=True)

    placeholder_map: Dict[str, str] = {}
    counter = 0

    for keyword in sorted_keywords:
        if not keyword:
            continue
        source = keywords_with_source[keyword]
        safe_keyword = re.escape(escape(keyword))
        css_class = "source-" + re.sub(r'[^a-zA-Z0-9]', '-', source)

        # 좌우가 \w 아님을 보장
        pattern = re.compile(r'(?<!\w)' + safe_keyword + r'(?!\w)')

        def replace_with_placeholder(m):
            nonlocal counter
            marked = f'<mark class="{css_class}" title="{source}">{m.group(0)}</mark>'
            ph = f"__PH_{counter}__"
            placeholder_map[ph] = marked
            counter += 1
            return ph

        if pattern.search(highlighted_text):
            highlighted_text = pattern.sub(replace_with_placeholder, highlighted_text)
            found_keywords.add(keyword)

    # 플레이스홀더 복구
    for ph, marked in placeholder_map.items():
        highlighted_text = highlighted_text.replace(ph, marked)

    return highlighted_text.replace('\n', '<br>'), found_keywords


def highlight_loose_safe(text_raw: str, keywords: Dict[str, str]) -> str:
    """
    느슨(부분 포함) 하이라이트를 안전하게 적용합니다.

    escape 충돌을 피하기 위해:
    1) 원문에서 매칭 구간을 플레이스홀더로 먼저 치환,
    2) 전체 텍스트 escape,
    3) 플레이스홀더를 <mark>로 복원.

    Args:
        text_raw (str): 원문 텍스트.
        keywords (Dict[str, str]): {키워드: 출처} 전수 매핑(정확 포함 여부와 무관).

    Returns:
        str: 느슨 하이라이트가 적용된 HTML 문자열.

    Notes:
        - 대소문자 구분, 경계 무시(부분 매칭)로 시각화 범위를 넓힙니다.
        - 각 mark에는 출처 기반 CSS 클래스를 부여합니다.
    """
    if not text_raw or not keywords:
        return escape(text_raw or "")

    ph_map: Dict[str, str] = {}
    ph_i = 0
    work = text_raw

    for kw in sorted(keywords.keys(), key=len, reverse=True):
        if not kw:
            continue
        source = keywords[kw]
        css = "source-" + re.sub(r'[^a-zA-Z0-9]', '-', source)
        pat = re.compile(re.escape(kw))  # 경계/대소문자 무시 없음

        def repl(m):
            nonlocal ph_i
            token = m.group(0)
            ph = f"__HL_PH_{ph_i}__"
            # 내부 텍스트도 escape하여 <mark> 내 안전성 보장
            ph_map[ph] = f'<mark class="{css}" title="{source}">{escape(token)}</mark>'
            ph_i += 1
            return ph

        work = pat.sub(repl, work)

    # 2) 전체 escape
    work = escape(work)

    # 3) 플레이스홀더 복원(escape된 토큰과 원 토큰 둘 다 처리)
    for ph, html_seg in ph_map.items():
        work = work.replace(escape(ph), html_seg)
        work = work.replace(ph, html_seg)

    return work.replace('\n', '<br>')


def process_section_and_get_info(
    full_text: str,
    db_data: Any,
    section_type: str,
    ingredient_synonyms_map: Dict[int, List[str]] = None,
    total_synonym_count: int = 0
) -> Optional[Dict[str, Any]]:
    """
    지정된 섹션을 슬라이싱하고, DB 원문 문자열이 '그대로' 포함되는지를 전수 검증합니다.

    - Section 1: 제품/회사명 필드만 대상.
    - Ingredients: 성분명, CAS, EC, 농도, 시소러스(동의어)를 전수 검사.
    - '정확 포함'만 엄격 하이라이트 대상으로 삼고, '느슨'은 시각화를 위한 전수 하이라이트로 사용.

    Args:
        full_text (str): 전체 MSDS 원문.
        db_data (Any): 섹션 타입에 따른 DB 데이터:
            - Section 1: dict (product_name, company_name)
            - Ingredients: pandas.DataFrame (id, name, cas, ec_number, conc_raw)
        section_type (str): "Section 1" 또는 "Ingredients".
        ingredient_synonyms_map (Dict[int, List[str]], optional): 성분 id → [동의어] 매핑.
        total_synonym_count (int): 전체 동의어 수(통계 표시용).

    Returns:
        Optional[Dict[str, Any]]: 섹션 정보 딕셔너리 또는 None(슬라이스 실패 시).
            {
              'raw_slice': str,  # 슬라이싱된 원문
              'keywords_with_source': Dict[str, str],  # '정확 포함' 키워드만
              'keywords_all_with_source': Dict[str, str],  # 전수(느슨)
              'stats': {
                 'total_db_items': int,
                 'by_source': Dict[str, int],
                 'found_items': int,
                 'found_by_source': Dict[str, int],
                 'match_rate': float,
                 'synonym_table_total': int,
              }
            }
    """
    print(f"  -> {section_type} 처리 중...")

    raw_slice = ""
    all_db_keywords: Dict[str, str] = {}

    stats = {
        'total_db_items': 0,
        'by_source': defaultdict(int),
        'found_items': 0,
        'found_by_source': defaultdict(int),
        'match_rate': 0.0,
        'synonym_table_total': total_synonym_count,
    }

    def add_keyword(kw: str, source: str):
        # 공백/중복 제거 후 사전 축적
        kw = str(kw).strip() if kw else ""
        if kw and kw not in all_db_keywords:
            all_db_keywords[kw] = source

    try:
        if section_type == "Section 1":
            # 섹션 1 범위 결정(라인 인덱스 기반)
            _, debug_info = slice_section1_debug(full_text)
            start_idx, end_idx = debug_info.get('start_idx'), debug_info.get('end_idx')
            if start_idx is None or end_idx is None:
                return None
            lines = full_text.splitlines(True)
            raw_slice = "".join(lines[start_idx:end_idx])

            # 제품/회사명만 대상
            add_keyword(db_data.get('product_name'), 'products.product_name')
            add_keyword(db_data.get('company_name'), 'products.company_name')

        elif section_type == "Ingredients":
            # 성분 섹션 원문 추출
            sliced_info = slice_section_2_or_3(full_text)
            raw_slice = sliced_info.get('raw', '')
            if not raw_slice:
                return None

            # 전수 키워드 수집: name, cas, ec_number, conc_raw + 동의어
            if isinstance(db_data, pd.DataFrame) and not db_data.empty:
                for _, row in db_data.iterrows():
                    add_keyword(row.get('name'), 'ingredients.name')
                    add_keyword(row.get('cas'), 'ingredients.cas')
                    add_keyword(row.get('ec_number'), 'ingredients.ec_number')
                    add_keyword(row.get('conc_raw'), 'ingredients.conc_raw')

                    ingredient_id = row.get('id')
                    if ingredient_synonyms_map and ingredient_id in ingredient_synonyms_map:
                        for syn in ingredient_synonyms_map[ingredient_id]:
                            add_keyword(syn, 'ingredient_synonyms.synonym')

        # 전수 정확 포함 여부 검사
        present_map: Dict[str, Dict[str, Any]] = {}
        for kw, source in all_db_keywords.items():
            k = str(kw)
            if not k:
                continue
            present_exact = (k in raw_slice)  # 단순 포함 검사(엄격)
            present_map[kw] = {
                'source': source,
                'present_exact': present_exact,
            }

        # 하이라이트용 매핑
        keywords_all_with_source = {kw: v['source'] for kw, v in present_map.items()}
        exact_found_dict = {kw: v['source'] for kw, v in present_map.items() if v['present_exact']}

        # 정확(단어 경계) 하이라이트 생성
        strict_html, found_keywords = highlight_text_with_tracking(raw_slice, exact_found_dict)

        # 통계 집계
        stats['total_db_items'] = len(present_map)
        stats['found_items'] = sum(1 for v in present_map.values() if v['present_exact'])
        stats['match_rate'] = (stats['found_items'] / stats['total_db_items'] * 100) if stats['total_db_items'] > 0 else 0.0

        for v in present_map.values():
            stats['by_source'][v['source']] += 1
        for kw in present_map.keys():
            if present_map[kw]['present_exact']:
                stats['found_by_source'][present_map[kw]['source']] += 1

        print(f"     DB 키워드(전수): {stats['total_db_items']}개 | 그대로 발견: {stats['found_items']}개 | 매칭률: {stats['match_rate']:.1f}%")

        return {
            'raw_slice': raw_slice,
            'keywords_with_source': exact_found_dict,
            'keywords_all_with_source': keywords_all_with_source,
            'stats': stats
        }

    except Exception as e:
        print(f"     [오류] {section_type} 처리 중 예외 발생: {e}")
        traceback.print_exc()
        return None


def generate_stats_html(section_stats: List[Dict[str, Any]]) -> str:
    """
    섹션별/전체 집계 통계를 HTML 테이블로 생성합니다.

    Args:
        section_stats (List[Dict[str, Any]]): 각 섹션의 {'section_name', 'stats'} 목록.

    Returns:
        str: 통계 테이블을 포함한 HTML 문자열.

    Notes:
        - 섹션별 총합, 발견 수, 매칭률과 출처별 상세 비율을 포함합니다.
    """
    html = """
    <div class="stats-container">
        <h2>데이터 검증 통계</h2>
        <table class="stats-table">
            <thead>
                <tr>
                    <th>섹션</th>
                    <th>DB 키워드 수</th>
                    <th>그대로 발견</th>
                    <th>매칭률</th>
                </tr>
            </thead>
            <tbody>
    """
    total_db = 0
    total_found = 0
    for stat_item in section_stats:
        section_name = stat_item['section_name']
        stats = stat_item['stats']
        db_count = stats['total_db_items']
        found_count = stats['found_items']
        match_rate = stats['match_rate']
        total_db += db_count
        total_found += found_count
        html += f"""
                <tr>
                    <td><strong>{section_name}</strong></td>
                    <td>{db_count}</td>
                    <td>{found_count}</td>
                    <td>{match_rate:.1f}%</td>
                </tr>
        """
    overall_rate = (total_found / total_db * 100) if total_db > 0 else 0
    html += f"""
                <tr class="total-row">
                    <td><strong>전체 합계</strong></td>
                    <td><strong>{total_db}</strong></td>
                    <td><strong>{total_found}</strong></td>
                    <td><strong>{overall_rate:.1f}%</strong></td>
                </tr>
            </tbody>
        </table>
    """
    # 출처별 상세 통계
    html += "<h3>출처별 상세 통계</h3>"
    for stat_item in section_stats:
        section_name = stat_item['section_name']
        stats = stat_item['stats']
        by_source = stats['by_source']
        found_by_source = stats['found_by_source']
        if by_source:
            html += f"<h4>{section_name}</h4><ul class='source-details'>"
            for source, count in sorted(by_source.items()):
                found = found_by_source.get(source, 0)
                rate = (found / count * 100) if count > 0 else 0
                html += f"<li><code>{source}</code>: {found}/{count} ({rate:.1f}%)</li>"
            html += "</ul>"
    html += "</div>"
    return html

def create_verification_report(
    document_id: str,
    output_format: str = 'pdf',
    output_dir: str = './verification_outputs'
) -> None:
    """
    MSDS 데이터 추출 검증 보고서를 생성하는 메인 함수.

    파이프라인:
    1) MongoDB에서 원문 로드, PostgreSQL에서 제품/성분/동의어 로드
    2) 섹션 슬라이싱 및 키워드 집계/검증
    3) 통계/DB 내용/슬라이스 박스/원문 표시 HTML 구성
    4) 지정 폴더(output_dir)에 PDF 또는 HTML 파일로 저장

    Args:
        document_id (str): 대상 문서 ID (MongoDB/PostgreSQL 공통 키).
        output_format (str): 'pdf' 또는 'html'.
        output_dir (str): 출력 파일을 저장할 디렉터리 경로. 존재하지 않으면 생성.

    Raises:
        ValueError: 필수 데이터가 누락된 경우(document_id 미존재 등).

    Side Effects:
        - {output_dir}/verification_report_{document_id}.pdf 또는 .html 파일 생성.

    Notes:
        - PDF 생성 시, HTML 내 meta charset과 @font-face 설정이 유효해야 폰트 렌더링 문제가 줄어듭니다.
        - 출력 폴더는 pathlib로 생성 보장합니다. [mkdir -p 동작]
    """
    print(f"\n[+] '{document_id}' 검증 보고서 생성을 시작합니다.")
    print("=" * 70)

    print("[1/4] 원본 텍스트 및 DB 데이터를 로드합니다...")
    try:
        mongodb = get_mongodb()
        doc = mongodb['msds_markdown_collection'].find_one({'document_id': document_id})
        if not doc:
            raise ValueError(f"MongoDB에서 document_id '{document_id}'를 찾을 수 없습니다.")
        original_full_text = doc.get('content', '')
        print(f"원본 텍스트 로드 완료 ({len(original_full_text)} 문자)")

        conn = get_postgres()
        product_df = pd.read_sql(
            "SELECT id, product_name, company_name FROM products WHERE document_id = %s",
            conn, params=(document_id,))
        if product_df.empty:
            raise ValueError(f"PostgreSQL 'products' 테이블에서 document_id '{document_id}'를 찾을 수 없습니다.")

        product_id = int(product_df.iloc[0]['id'])
        product_data = product_df.iloc[0].to_dict()
        print(f"Product 데이터 로드 완료 (product_id: {product_id})")

        ingredients_df = pd.read_sql(
            "SELECT id, name, cas, ec_number, conc_raw FROM ingredients WHERE product_id = %s",
            conn, params=(product_id,))
        print(f"Ingredients 데이터 로드 완료 ({len(ingredients_df)} 건)")

        ingredient_synonyms_map = defaultdict(list)
        total_synonym_count = 0
        if not ingredients_df.empty:
            ingredient_ids = tuple(ingredients_df['id'].tolist())
            # IN %s는 psycopg2에서 튜플 바인딩 필요
            synonyms_df = pd.read_sql(
                "SELECT ingredient_id, synonym FROM ingredient_synonyms WHERE ingredient_id IN %s",
                conn, params=(ingredient_ids,))
            for _, row in synonyms_df.iterrows():
                ingredient_synonyms_map[row['ingredient_id']].append(row['synonym'])
            total_synonym_count = len(synonyms_df)
            print(f"Ingredient Synonyms 데이터 로드 완료 ({total_synonym_count} 건)")

        conn.close()

    except Exception as e:
        print(f"[오류] 데이터 로드 중 문제가 발생했습니다: {e}")
        traceback.print_exc()
        return

    print("\n[2/4] 각 섹션을 슬라이싱하고 하이라이팅 정보를 생성합니다...")
    info1 = process_section_and_get_info(original_full_text, product_data, "Section 1")
    info2 = process_section_and_get_info(original_full_text, ingredients_df, "Ingredients", ingredient_synonyms_map, total_synonym_count)

    print("\n[3/4] 최종 보고서 HTML을 구성합니다...")

    # 1. 숫자 통계
    section_stats: List[Dict[str, Any]] = []
    if info1: section_stats.append({'section_name': 'Section 1 (제품 정보)', 'stats': info1['stats']})
    if info2: section_stats.append({'section_name': 'Section 2/3 (성분 정보)', 'stats': info2['stats']})
    stats_html = generate_stats_html(section_stats)

    # 2. DB 내용 표
    db_content_html = """
    <div class="db-content-container">
        <h2>데이터베이스 내용</h2>
    """
    # Section 1
    db_content_html += """
        <div class="db-section">
            <h3>Section 1 - 제품 정보</h3>
            <table class="db-table">
                <thead>
                    <tr>
                        <th>필드</th>
                        <th>값</th>
                        <th>출처</th>
                    </tr>
                </thead>
                <tbody>
    """
    db_content_html += f"""
                    <tr>
                        <td><strong>Product Name</strong></td>
                        <td>{escape(str(product_data.get('product_name', 'N/A')))}</td>
                        <td><code>products.product_name</code></td>
                    </tr>
                    <tr>
                        <td><strong>Company Name</strong></td>
                        <td>{escape(str(product_data.get('company_name', 'N/A')))}</td>
                        <td><code>products.company_name</code></td>
                    </tr>
    """
    db_content_html += """
                </tbody>
            </table>
        </div>
    """

    # Section 2/3
    if isinstance(ingredients_df, pd.DataFrame) and not ingredients_df.empty:
        db_content_html += """
        <div class="db-section">
            <h3>Section 2/3 - 성분 정보</h3>
            <table class="db-table">
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>CAS</th>
                        <th>EC Number</th>
                        <th>Concentration</th>
                        <th>Synonyms</th>
                    </tr>
                </thead>
                <tbody>
        """
        for _, row in ingredients_df.iterrows():
            ingredient_id = row.get('id')
            synonyms = (ingredient_synonyms_map or {}).get(ingredient_id, [])
            synonyms_text = ', '.join(synonyms[:5])
            if len(synonyms) > 5:
                synonyms_text += f' ... (+{len(synonyms) - 5}개 더)'

            db_content_html += f"""
                    <tr>
                        <td>{escape(str(row.get('name', 'N/A')))}</td>
                        <td>{escape(str(row.get('cas', 'N/A')))}</td>
                        <td>{escape(str(row.get('ec_number', 'N/A')))}</td>
                        <td>{escape(str(row.get('conc_raw', 'N/A')))}</td>
                        <td style="font-size: 11px;">{escape(synonyms_text) if synonyms_text else 'N/A'}</td>
                    </tr>
            """
        db_content_html += """
                </tbody>
            </table>
        </div>
        """

    db_content_html += """
    </div>
    """

    # 3. 슬라이싱된 구간(느슨 하이라이트 박스)
    sliced_sections_html = """
    <div class="sliced-sections-container">
        <h2>슬라이싱된 구간</h2>
    """

    all_sources = set()

    for info in [info1, info2]:
        if info and info.get('raw_slice'):
            # 느슨 하이라이트(전수)
            keywords_all = info.get('keywords_all_with_source', info['keywords_with_source'])
            loose_html = highlight_loose_safe(info['raw_slice'], keywords_all)
            section_title = "Extracted Section 1" if info['stats']['synonym_table_total'] == 0 else "Extracted Section 2/3"
            sliced_sections_html += f'<div class="slice-box"><h3>{section_title}</h3><pre>{loose_html}</pre></div>'

            # 범례용 출처 수집
            all_sources.update(keywords_all.values())

    sliced_sections_html += """
    </div>
    """

    # 4. 전체 원본에 슬라이스 박스 삽입(첫 1회 치환)
    full_html_body = escape(original_full_text)
    for info in [info1, info2]:
        if info and info.get('raw_slice'):
            keywords_all = info.get('keywords_all_with_source', info['keywords_with_source'])
            loose_html = highlight_loose_safe(info['raw_slice'], keywords_all)
            section_title = "Extracted Section 1" if info['stats']['synonym_table_total'] == 0 else "Extracted Section 2/3"
            box_html = f'<div class="slice-box"><h3>{section_title}</h3><pre>{loose_html}</pre></div>'
            full_html_body = full_html_body.replace(escape(info['raw_slice']), box_html, 1)
    full_html_body = full_html_body.replace('\n', '<br>')

    full_document_html = f"""
    <div class="full-document-container">
        <h2>전체 원본 문서 (슬라이싱 구간 표시)</h2>
        <div><pre>{full_html_body}</pre></div>
    </div>
    """

    # 범례: 출처별 색상 CSS 생성
    color_palette = ['#FFDDC1', '#D4F0F0', '#E1CFC1', '#C1E1C1', '#F0D4D4', '#D4D4F0', '#FFFACD', '#F0E68C', '#E6E6FA', '#FFFAF0']
    source_style_block = ""
    legend_html_block = "<ul>"
    for i, source in enumerate(sorted(list(all_sources))):
        css_class = "source-" + re.sub(r'[^a-zA-Z0-9]', '-', source)
        color = color_palette[i % len(color_palette)]
        source_style_block += f".{css_class} {{ background-color: {color}; }}\n"
        legend_html_block += f'<li><span style="background-color:{color}; padding: 2px 5px; border-radius: 3px; border: 1px solid #ccc;">{source}</span></li>'
    legend_html_block += "</ul>"

    legend_html = f"""
    <div class="legend">
        <h3>하이라이트 범례</h3>
        {legend_html_block}
    </div>
    """

    # 최종 HTML(유니코드 안전을 위한 meta charset 포함)
    final_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8" />
        <title>MSDS 검증 보고서 - {document_id}</title>
        <style>
            @font-face {{ font-family: 'NotoSansKR-Regular'; src: url('fonts/NotoSansKR-Regular.ttf'); }}
            body {{ font-family: 'NotoSansKR-Regular', sans-serif; line-height: 1.6; padding: 20px; color: #333; background-color: #fafafa; }}
            pre {{ font-family: 'NotoSansKR-Regular', monospace; white-space: pre-wrap; word-wrap: break-word; font-size: 12px; margin: 0; }}
            .slice-box {{ border: 2px dashed #3498db; background-color: #f8f9fa; padding: 15px; margin: 20px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }}
            .slice-box h3 {{ margin-top: 0; padding-bottom: 10px; border-bottom: 1px solid #aed6f1; color: #2980b9; font-size: 16px; }}
            mark {{ padding: 1px 3px; border-radius: 3px; font-weight: bold; cursor: help; border: 1px solid rgba(0,0,0,0.1); }}
            {source_style_block}
            .legend {{ margin: 20px 0; padding: 15px; background-color: #f8f8f8; border-radius: 5px; border: 1px solid #e7e7e7; }}
            .legend h3 {{ margin-top: 0; }}
            .legend ul {{ list-style: none; padding: 0; }}
            .legend li {{ margin-bottom: 5px; }}
            .stats-container {{ margin: 30px 0; padding: 20px; background-color: #f0f8ff; border-radius: 8px; border: 1px solid #b0e0e6; }}
            .stats-container h2 {{ color: #2c3e50; margin-top: 0; border-bottom: 2px solid #4CAF50; padding-bottom: 10px; }}
            .stats-table {{ width: 100%; border-collapse: collapse; margin-top: 10px; background-color: white; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
            .stats-table th {{ background-color: #3498db; color: white; padding: 12px; text-align: left; border-right: 1px solid #5dade2; }}
            .stats-table th:last-child {{ border-right: none; }}
            .stats-table td {{ padding: 12px; border: 1px solid #ddd; }}
            .stats-table tr:nth-child(even) {{ background-color: #f9f9f9; }}
            .stats-table .total-row {{ background-color: #e8f4f8; font-weight: bold; border-top: 2px solid #3498db; }}
            .source-details {{ list-style: none; padding-left: 0; }}
            .source-details li {{ margin-bottom: 4px; font-size: 13px; background-color: #ecf0f1; padding: 5px; border-radius: 3px; }}
            .source-details code {{ background: none; }}
            .db-content-container {{ margin: 30px 0; padding: 20px; background-color: #fff8e1; border-radius: 8px; border: 1px solid #ffd54f; }}
            .db-content-container h2 {{ color: #2c3e50; margin-top: 0; border-bottom: 2px solid #ffa726; padding-bottom: 10px; }}
            .db-section {{ margin: 20px 0; }}
            .db-section h3 {{ color: #34495e; margin-top: 15px; margin-bottom: 10px; }}
            .db-table {{ width: 100%; border-collapse: collapse; margin-top: 10px; background-color: white; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
            .db-table th {{ background-color: #ff9800; color: white; padding: 10px; text-align: left; border-right: 1px solid #ffb74d; }}
            .db-table th:last-child {{ border-right: none; }}
            .db-table td {{ padding: 10px; border: 1px solid #ddd; font-size: 13px; }}
            .db-table tr:nth-child(even) {{ background-color: #fffbf0; }}
            .sliced-sections-container {{ margin: 30px 0; padding: 20px; background-color: #e8f5e9; border-radius: 8px; border: 1px solid #81c784; }}
            .sliced-sections-container h2 {{ color: #2c3e50; margin-top: 0; border-bottom: 2px solid #66bb6a; padding-bottom: 10px; }}
            .full-document-container {{ margin: 30px 0; padding: 20px; background-color: #ffffff; border-radius: 8px; border: 1px solid #bdbdbd; }}
            .full-document-container h2 {{ color: #2c3e50; margin-top: 0; border-bottom: 2px solid #9e9e9e; padding-bottom: 10px; }}
            hr {{ border: 0; border-top: 2px solid #e0e0e0; margin: 30px 0; }}
        </style>
    </head>
    <body>
        <h1>MSDS 데이터 추출 검증 보고서</h1>
        <p><strong>Document ID:</strong> {document_id}</p>

        <hr>

        <!-- 1. 숫자 통계 -->
        {stats_html}

        <hr>

        <!-- 2. DB 내용 -->
        {db_content_html}

        <hr>

        <!-- 범례 -->
        {legend_html}

        <hr>

        <!-- 3. 슬라이싱된 구간 -->
        {sliced_sections_html}

        <hr>

        <!-- 4. 전체 원본에서 슬라이싱 체크한 내용 -->
        {full_document_html}
    </body>
    </html>
    """

    print(f"\n[4/4] 최종 보고서를 {output_format.upper()} 파일로 생성합니다...")

    # 출력 폴더 생성 보장 (mkdir -p)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    base = out_dir / f"verification_report_{document_id}"

    try:
        if output_format.lower() == 'pdf':
            pdf_path = base.with_suffix('.pdf')
            if convert_html_to_pdf(final_html, str(pdf_path)):
                print(f"성공: '{pdf_path}' 파일 생성 완료")
            else:
                print(f"실패: PDF 파일 생성 오류")
        elif output_format.lower() == 'html':
            html_path = base.with_suffix('.html')
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(final_html)
            print(f"성공: '{html_path}' 파일 생성 완료")
        else:
            raise ValueError(f"지원하지 않는 포맷: {output_format}")
    except Exception as e:
        print(f"[오류] 파일 생성 중 문제 발생: {e}")
        traceback.print_exc()





# 실행
if __name__ == "__main__":
    # 기본 테스트용 Document ID와 출력 포맷
    target_document_id = "MOCK_MSDS_006"
    create_verification_report(target_document_id, output_format='pdf')
