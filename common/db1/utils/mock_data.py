import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'db_1_py'))

from get_mongo_postgre_db  import get_mongodb

def create_mock_markdown_db(mongodb):
    """
    파이프라인 개발·테스트용 Mock Markdown 문서를 MongoDB에 생성합니다.

    이 함수는 로컬/테스트 환경에서 파이프라인을 빠르게 검증하기 위해
    소규모이지만 대표적인 문서 집합을 결정론적으로 삽입합니다. 재실행 시
    기존 Mock 문서(document_id가 'MOCK_'로 시작)는 먼저 삭제한 뒤 다시 생성합니다.

    Args:
        mongodb (pymongo.database.Database): Mock 데이터를 쓸 MongoDB 데이터베이스 핸들.
            - 사용 컬렉션: 'msds_markdown_collection'

    Returns:
        list[dict]: 삽입된 Mock 문서들의 원본 딕셔너리 리스트.

    동작 개요:
        1) 'msds_markdown_collection'에서 document_id가 'MOCK_'로 시작하는 문서를 일괄 삭제합니다.
        2) 대표 케이스를 포함하는 Mock 문서 리스트를 구성합니다.
        3) insert_many로 일괄 삽입하고, 삽입 건수를 출력합니다.
        4) 호출자 검증을 위해 삽입한 문서 리스트를 그대로 반환합니다.

    주의:
        - 식별 규칙: 모든 Mock 문서는 document_id가 'MOCK_'로 시작해야 합니다(정리/필터링 용이).
        - 멱등성: 본 함수는 실행 시 기존 Mock 데이터를 삭제한 후 다시 채우는 방식으로 동작합니다.
        - 컬렉션명: 생성 함수('msds_markdown_collection')와 검증 함수('markdown_collection')의
          컬렉션명이 일치하는지 확인하세요(현재 코드는 서로 다름).
        - 인덱스: 대량 테스트 전에는 document_id에 대한 인덱스를 권장합니다(정리 성능 향상).
    """
    
    collection = mongodb['msds_markdown_collection']

    # 기존 Mock 데이터 삭제 (재실행 시)
    collection.delete_many({'document_id': {'$regex': '^MOCK_'}})

    mock_documents = [
        {
            "document_id": "MOCK_MSDS_001",
            "file_name": "output(2).pdf",
            "content": """>>> page_0


http://www.chemtronics.co.kr


## 물질안전보건자료

(Material Safety Data Sheet)

## MSDS 번호:AA00164-0000000029

CAS No.

물질명

KE No.

UN No.

EU No.

108-94-1

시클로헥사논

KE-09188

1915

203-631-1

## 1. 화학제품과 회사에 관한 정보

가. 제품명

ANONE

나. 제품의 권고 용도와 사용상의 제한

제품의 권고 용도

원료 및 중간체, 코팅, 페인트, 신너, 페인트 제거제, 점도 조정제, 세정 및 세척제

제품의 사용상의 제한

권고 용도 이외에 사용하지 마십시오.

다.공급자 정보

회사명

㈜켐트로닉스

주소

경기도 평택시 포승읍 포승공단로 118번길 45

제공서비스 또는 긴급전화번호

070-4923-0475

담당부서 / 담당자

환경안전팀 / 유근화

## 2. 유해성·위험성

가.유해성·위험성 분류

인화성 액체 : 구분3

급성독성 (경구) : 구분4

급성독성 (경피) : 구분3

급성독성 (흡입: 증기) 구분3

피부 부식성/피부 자극성 : 구분2

심한 눈 손상성/눈 자극성 : 구분1

피부 과민성 : 구분1

발암성 : 구분2

특정표적장기독성 (1회 노출) : 구분3 (마취 영향)

## 나. 예방조치문구를 포함한 경고표지 항목

그림문자


신호어

위험

유해·위험문구

H226 인화성 액체 및 증기

H302 삼키면 유해함

H311 피부와 접촉하면 유독함

H315 피부에 자극을 일으킴

H317 알레르기성 피부 반응을 일으킬 수 있음

1/10

>>> page_1


http://www.chemtronics.co.kr

H318 눈에 심한 손상을 일으킴

H331 흡입하면 유독함

H336 졸음 또는 현기증을 일으킬 수 있음

H351 암을 일으킬 것으로 의심됨

예방조치문구

예방

P201 사용 전 취급 설명서를 확보하시오.

P202 모든 안전 예방조치 문구를 읽고 이해하기 전에는 취급하지 마시오.

P210 열, 고온의 표면, 스파크, 화염 및 그 밖의 점화원으로부터 멀리하시오. 금연

P233 용기를 단단히 밀폐하시오.

P240 용기와 수용설비를 접지하시오.

P241 방폭형 전기/환기/조명설비를 사용하시오.

P242 스파크가 발생하지 않는 도구를 사용하시오.

P243 정전기 방지 조치를 취하시오.

P261 미스트/증기/스프레이의 흡입을 피하시오.

P270 이 제품을 사용할 때에는 먹거나, 마시거나 흡연하지 마시오.

P271 옥외 또는 환기가 잘 되는 곳에서만 취급하시오.

P272 작업장 밖으로 오염된 의류를 반출하지 마시오.

P280 보호장갑/보호의/보안경/안면보호구를 착용하시오.

대응

P310 즉시 의료기관/의사의 진찰을 받으시오.

P311 의료기관/의사의 진찰을 받으시오.

P312 불편함을 느끼면 의료기관/의사의 진찰을 받으시오.

P321 응급처치를 하시오.

P330 입을 씻어내시오.

P301+P312 삼켰다면: 불편함을 느끼면 의료기관/의사의 진찰을 받으시오.

P302+P352 피부에 묻으면: 다량의 물로 씻으시오.

P304+P340 흡입하면: 신선한 공기가 있는 곳으로 옮기고 호흡하기 쉬운 자세로 안정을

취하시오.

P308+P313 노출되거나 노출이 우려되면: 의학적인 조치/조언을 받으시오.

P332+P313 피부 자극이 나타나면: 의학적인 조치/조언을 받으시오.

P333+P313 피부 자극 또는 홍반이 나타나면: 의학적인 조치/조언을 받으시오.

P361+P364 오염된 모든 의류를 즉시 벗고 다시 사용 전 세척하시오.

P362+P364 오염된 의류를 벗고 다시 사용 전 세척하시오.

P370+P378 화재 시: 불을 끄기 위해 소화제를 사용하시오.

P370+P378 화재 시: 불을 끄기 위해 소화제를 사용하시오.

P405 잠금장치를 하여 저장하시오.

P403+P233 환기가 잘 되는 곳에 보관하시오. 용기를 단단히 밀폐하시오.

P403+P235 환기가 잘 되는 곳에 보관하시오. 저온으로 유지하시오.

폐기

P501 폐기물 관련 법령에 따라 내용물/용기를 폐기하시오

다. 유해·위험성 분류기준에 포함되지 않는 기타 유해·위험성(예. 분진폭발 위험성)

자료없음

## 3. 구성성분의 명칭 및 함유량

시클로헥사논

화학물질명

Cyclohexanone

관용명 및 이명(異名)

2/10

>>> page_2


http://www.chemtronics.co.kr

108-94-1

CAS번호 또는 식별번호

100%

함유량(%)

## 4. 응급조치요령

4. 응급조치요령

가. 눈에 들어갔을 때

눈에 묻으면 몇 분간 물로 조심해서 씻으시오. 가능하면 콘택트렌즈를 제거하시오. 계속

씻으시오.

긴급 의료조치를 받으시오

나. 피부에 접촉했을 때

피부(또는 머리카락)에 묻으면 오염된 모든 의복은 벗으시오. 피부를 물로 씻으시오/샤워

하시오 .

피부자극성 또는 홍반이 나타나면 의학적인 조치·조언을 구하시오.

긴급 의료조치를 받으시오.

오염된 옷과 신발을 제거하고 오염지역을 격리하시오.

경미한 피부 접촉 시 오염부위 확산을 방지하시오.

화상의 경우 즉시 찬물로 가능한 오래 해당부위를 식히고, 피부에 들러붙은 옷은 제거하지

마시오.

비누와 물로 피부를 씻으시오.

물질과 접촉시 즉시 20분 이상 흐르는 물에 피부와 눈을 씻어내시오

다. 흡입했을 때

물질을 먹거나 흡입하였을 경우 구강대구강법으로 인공호흡을 하지 말고 적절한 호흡의료

장비를 이용하시오.

즉시 의료기관(의사)의 진찰을 받으시오.

라. 먹었을 때

노출되거나 노출이 우려되면 의학적인 조치·조언을 구하시오.

입을 씻어내시오.

물질을 먹거나 흡입하였을 경우 구강대구강법으로 인공호흡을 하지 말고 적절한 호흡의료

장비를 이용하시오.

마. 기타 의사의 주의사항

폭로 시 의료진에게 연락하고 추적조사 등의 특별한 응급조치를 취하시오.

의료인력이 해당물질에 대해 인지하고 보호조치를 취하도록 하시오.

## 5. 폭발·화재시 대처방법

가. 적절한 (및 부적절한) 소화제

이 물질과 관련된 소화 시 알코올 포말, 이산화탄소 또는 물분무를 사용할 것

질식소화 시 건조한 모래 또는 흙을 사용할 것

나. 화학물질로부터 생기는 특정 유해성

가열시 용기가 폭발할 수 있음

고인화성: 열, 스파크, 화염에 의해 쉽게 점화됨

누출물은 화재/폭발 위험이 있음

실내, 실외, 하수구에서 증기 폭발 위험이 있음

일부는 탈 수 있으나 쉽게 점화하지 않음

증기는 공기와 폭발성 혼합물을 형성할 수 있음

격렬하게 중합반응하여 화재와 폭발을 일으킬 수 있음

증기는 점화원에 옮겨져 발화될 수 있음

타는 동안 열분해 또는 연소에 의해 자극적이고 매우 유독한 가스가 발생될 수 있음

인화점이나 그 이상에서 폭발성 혼합물을 형성할 수 있음

인화성 액체 및 증기

화재시 자극성, 부식성, 독성 가스를 발생할 수 있음

다. 화재진압시 착용할 보호구 및 예방조치

구조자는 적절한 보호구를 착용하시오.

지역을 벗어나 안전거리를 유지하여 소화하시오.

3/10

>>> page_3


http://www.chemtronics.co.kr

대부분 물보다 가벼움

대부분의 증기는 공기보다 무겁기 때문에 지면을 따라 확산하고 저지대나 밀폐공간에 축

적될 수 있음

뜨거운 상태로 운반될 수 있음

용융되어 운송될 수도 있음

소화수의 처분을 위해 도랑을 파서 가두고 물질이 흩어지지 않게 하시오.

위험하지 않다면 화재지역에서 용기를 옮기시오.

탱크 화재 시 최대거리에서 소화하거나 무인 소화장비를 이용하시오.

탱크 화재 시 소화가 진화된 후에도 다량의 물로 용기를 식히시오.

탱크 화재 시 압력 방출장치에서 고음이 있거나 탱크가 변색할 경우 즉시 물러나시오.

탱크 화재 시 화염에 휩싸인 탱크에서 물러나시오.

탱크 화재 시 대규모 화재의 경우 무인 소화장비를 이용하고 불가능하다면 물러나 타게

놔두시오.

## 6. 누출사고시 대처방법

## 가. 인체를 보호하기 위해 필요한 조치사항 및 보호구

(미스트·증기·스프레이)의 흡입을 피하시오.

매우 미세한 입자는 화재나 폭발을 일으킬 수 있으므로 모든 점화원을 제거하시오.

엎질러진 것을 즉시 닦아내고, 보호구 항의 예방조치를 따르시오.

오염 지역을 격리하시오.

들어갈 필요가 없거나 보호장비를 갖추지 않은 사람은 출입하지 마시오.

모든 점화원을 제거하시오.

물질 취급시 모든 장비를 반드시 접지하시오.

위험하지 않다면 누출을 멈추시오.

적절한 보호의를 착용하지 않고 파손된 용기나 누출물에 손대지 마시오.

증기발생을 줄이기 위해 증기억제포말을 사용할 수 있음

플라스틱 시트로 덮어 확산을 막으시오.

피해야 할 물질 및 조건에 유의하시오.

## 나. 환경을 보호하기 위해 필요한 조치사항

수로, 하수구, 지하실, 밀폐공간으로의 유입을 방지하시오.

## 다. 정화 또는 제거 방법

소화를 위해 제방을 쌓고 물을 수거하시오.

불활성 물질(예를 들어 건조한 모래 또는 흙)로 엎지른 것을 흡수하고, 화학폐기물 용기에

넣으시오.

먼지를 제거하고 물로 습윤화하여 흩어지는 것을 막으시오.

액체를 흡수하고 오염된 지역을 세제와 물로 씻어 내시오.

다량 누출시 액체 누출물과 멀게하여 도랑을 만드시오.

청결한 방폭 도구를 사용하여 흡수된 물질을 수거하시오.

## 7. 취급 및 저장방법

가. 안전취급요령

모든 안전 예방조치 문구를 읽고 이해하기 전에는 취급하지 마시오.

폭발 방지용 전기·환기·조명 장비를 사용하시오.

스파크가 발생하지 않는 도구만을 사용하시오.

정전기 방지 조치를 취하시오.

미스트·증기·스프레이의 흡입을 피하시오.

취급 후에는 취급 부위를 철저히 씻으시오.

4/10

>>> page_4


http://www.chemtronics.co.kr

이 제품을 사용할 때에는 먹거나, 마시거나 흡연하지 마시오.

옥외 또는 환기가 잘 되는 곳에서만 취급하시오.

작업장 밖으로 오염된 의복을 반출하지 마시오.

압력을 가하거나, 자르거나, 용접, 납땜, 접합, 뚫기, 연마 또는 열에 폭로, 화염, 불꽃, 정전

기 또는 다른 점화원에 폭로하지 마시오.

기 또는 다른 점화원에 폭로하지 마시오.

용기가 비워진 후에도 제품 찌꺼기가 남아 있을 수 있으므로 모든 MSDS/경고표시 예방조

치를 따르시오.

용기가 비워진 후에도 제품 찌꺼기가 남아 있을 수 있으므로 모든 MSDS/경고표시 예방조

치를 따르시오.

취급/저장에 주의하여 사용하시오.

개봉 전에 조심스럽게 마개를 여시오.

장기간 또는 지속적인 피부접촉을 막으시오.

물질 취급시 모든 장비를 반드시 접지하시오.

피해야 할 물질 및 조건에 유의하시오.

열에 주의하시오.

저지대, 닫힌 공간 및 밀폐공간 작업시 산소결핍의 우려가 있으므로 작업전 공기농도 측정

저지대, 닫힌 공간 및 밀폐공간 작업시 산소결핍의 우려가 있으므로 작업전 공기농도 측정

및 환기 필요

나. 안전한 저장방법

열·스파크·화염·고열로부터 멀리하시오. 금연

용기는 환기가 잘 되는 곳에 단단히 밀폐하여 저장하시오.

환기가 잘 되는 곳에 보관하고 저온으로 유지하시오.

빈 드럼통은 완전히 배수하고 적절히 막아 즉시 드럼 조절기에 되돌려 놓거나 적절히 배

빈 드럼통은 완전히 배수하고 적절히 막아 즉시 드럼 조절기에 되돌려 놓거나 적절히 배

치하시오.

음식과 음료수로부터 멀리하시오.

## 8. 노출방지 및 개인보호구

## 가. 화학물질의 노출기준, 생물학적 노출기준 등

국내규정

TWA=25 ppm, STEL=50 ppm

ACGIH 규정

TWA=20 ppm, STEL=50 ppm

생물학적 노출기준

80 mg/L(소변 중 1,2Cyclohexanediol with hydrolysis, 주말작업 종료시 채취),

8 mg/L(소변 중 Cyclohexanol with hydrolysis, 작업 종료시 채취)

기타 노출기준

자료없음

나. 적절한 공학적 관리

공정격리, 국소배기를 사용하거나, 공기수준을 노출기준 이하로 조절하는 다른 공학적 관

리를 하시오.

사용 운전시 먼지, 흄 또는 미스트를 발생하는 경우, 공기 오염이 노출기준 이하로 유지되

도록 환기를 사용하시오.

이 물질을 저장하거나 사용하는 설비에 세안설비와 안전 샤워를 설치하시오.

다. 개인보호구

호흡기 보호

해당물질의 노출농도가 노출허용 기준을 초과할 경우, 노출되는 액체 물리화학적 특성에

맞는 한국산업안전보건공단의 인증을 필한 호흡용 보호구를 착용하시오.

해당물질의 노출농도가 250 ppm 보다 낮을 경우, 보호도가 10 이상이고 노출되는 액체

물질의 물리 화학적 특성을 고려한 적절한타입의 필터 또는 정화통을 장착한 반면형 방독

마스크

해당물질의 노출농도가 625 ppm 보다 낮을 경우, 보호도가 25이상이고 노출되는 액체물

질의 물리화학적 특성을 고려한 적절한 필터 또는 정화통을 장착한 비밀착형(lose-fiting)

후드/헐멧형 전동식 호흡보호구 혹은 연속흐름식 헬멧타입 방독마스크

해당물질의 노출농도가 1,250 ppm 보다 낮을 경우, 보호도가 50 이상이고 노출되는 액체

물질의 물리 화학적 특성을 고려한 적절한 필터 또는 정화통을 장착한 전면형/반면형 전

동식 방독마스크, 전면형/후드 타입 송기마스크

5/10

>>> page_5


http://www.chemtronics.co.kr

해당물질의 노출농도가 25,000 ppm 보다 낮을 경우, 보호도가 1,000이상이고 노출되는

액체물질의 물리화학적 특성을 고려한 적절한 필터 또는 정화통을 장착한 전동식 전면형

방독마스크 또는 전면형/후드타입 송기마스크

해당물질의 노출농도가 250,000 ppm 보다 낮을 경우, 보호도가 10,000이상인 압력 요구

식 전면형/헬멧/후드타입송기마스크

눈 보호

근로자가 접근이 용이한 위치에 긴급세척시설(샤워식) 및 세안설비를 설치하시오

눈에 자극을 일으키거나 기타 건강상의 장해를 일으킬 수 있는 다음과 같은 보안경을 착

용하시오. - 증기상태의 유기물질의 경우 보안경 혹은 통기성 보안경

화학물질 방어용 안경과 보안면을 사용하시오

손 보호

화학물질의 물리적 및 화학적 특성을 고려하여 적절한 재질의 보호장갑을 착용하시오.

절연용 장갑을 착용하시오.

신체 보호

화학물질의 물리적 및 화학적 특성을 고려하여 적절한 재질의 보호의복을 착용하시오.

## 9. 물리화학적 특성

가. 외관

성상

액체

색상

무색, 노란색(투명)

나. 냄새

박하냄새

다. 냄새역치

0.88 ppm

라. pH

자료없음

마. 녹는점/어는점

-31 ℃ (출처: ECHA)

바. 초기 끓는점과 끓는점 범위

154.3 ℃(1013 hPa)(출처: ECHA)

사. 인화점

44 °C(1013.25 hPa)(출처: ECHA)

아. 증발속도

40.6 (ETHER=1), 0.29 (Butylacetate=1)(출처: HSDB)

자. 인화성(고체, 기체)

해당없음

차. 인화 또는 폭발 범위의 상한/하한

9.4 / 1.1 % (100℃)

카. 증기압

7 hPa(30 ℃)(출처: ECHA)

타. 용해도

8.7 g/100㎖ (20℃)

파. 증기밀도

3.4 (air=1) (출처: HSDB)

하. 비중

0.95 (물=1)

거. n-옥탄올/물분배계수

Log Pow=0.86(25 ℃)(OECD Guideline 107)(출처: ECHA)

너. 자연발화온도

420 ℃(1013.25 hPa)(출처: ECHA)

더. 분해온도

자료없음

러. 점도

2.2 mPas(25 ℃)(출처: ECHA)

머. 분자량

98.14 (출처: HSDB)

## 10. 안정성 및 반응성

가. 화학적 안정성 및 유해 반응의 가능성

인화성 액체 및 증기

고온에서 분해되어 독성가스를 생성할 수 있음

격렬하게 중합반응하여 화재와 폭발을 일으킬 수 있음

인화점이나 그 이상에서 폭발성 혼합물을 형성할 수 있음

가열시 용기가 폭발할 수 있음

고인화성: 열, 스파크, 화염에 의해 쉽게 점화됨

누출물은 화재/폭발 위험이 있음

6/10

>>> page_6


http://www.chemtronics.co.kr

실내, 실외, 하수구에서 증기 폭발 위험이 있음

일부는 탈 수 있으나 쉽게 점화하지 않음

증기는 공기와 폭발성 혼합물을 형성할 수 있음

나. 피해야 할 조건

열·스파크·화염·고열로부터 멀리하시오. - 금연

다. 피해야 할 물질

가연성 물질, 환원성 물질

라. 분해시 생성되는 유해물질

타는 동안 열분해 또는 연소에 의해 자극적이고 매우 유독한 가스가 발생될 수 있음

## 11. 독성에 관한 정보

가. 가능성이 높은 노출 경로에 관한 정보

삼키면 유해함

피부와 접촉하면 유독함

피부에 자극을 일으킴

알레르기성 피부 반응을 일으킬 수 있음

눈에 심한 손상을 일으킴

흡입하면 유독함

졸음 또는 현기증을 일으킬 수 있음

암을 일으킬 것으로 의심됨

나. 건강 유해성 정보

급성독성

경구

Rat_LD

=1,890 mg/kg bw (출처: ECHA)

50

경피

Rabbit_LD

=1,000 mg/kg bw

50

흡입

Rat_LC

≥6.2 mg/L air/4 hr/vapour (출처: ECHA)

50

피부부식성 또는 자극성

토끼를 이용한 시험결과 홍반 및 경부한 부종이 관찰됨 (OECD Guideline 404, GLP) (출처:

ECHA)

심한 눈손상 또는 자극성

토끼를 이용한 시험결과 눈에 심각한 손상을 유발함 (OECD Guideline 405, GLP) (출처:

ECHA)

호흡기과민성

자료없음

피부과민성

기니피그를 이용한 시험결과 과민성이 관찰됨(출처: ECHA)

발암성

고용노동부고시

2

IARC

3

OSHA

IARC-3, TLV-A3

ACGIH

A3

NTP

해당없음

NTP

해당없음

EU CLP

해당없음

생식세포변이원성

in vivo 랫드를 이용한 골수 염색체 이상시험결과 음성(OECD Guideline 475)(출처: ECHA)

in vitro 미생물을 이용한 복귀돌연변이시험 결과 음성(OECD Guideline 471, GLP)(출처:

ECHA)

랫드를 이용한 2세대 생식독성 시험결과 1,400 ppm농도에서 수컷의 체중증가, 생식력 감

생식독성

랫드를 이용한 2세대 생식독성 시험결과 1,400 ppm농도에서 수컷의 체중증가, 생식력 감

소, 자손 생존수 감소 등이 관찰됨, NOAEC=1,000 ppm (OECD Guideline 416과 동등하거

소, 자손 생존수 감소 등이 관찰됨, NOAEC=1,000 ppm (OECD Guideline 416과 동등하거

나 유사, GLP)(출처: ECHA)

나 유사, GLP)(출처: ECHA)

특정 표적장기 독성 (1회 노출)

랫드를 이용한 급성독성 경구 시험결과 엎드른 자세, 옆으로 누운자세 및 마취가 관찰됨

(출처: ECHA)

(출처: ECHA)

랫드를 이용한 급성독성 흡입 시험결과 눈 및 코의 분비물, 얼룩덜룩한 입, 간헐적이고 빠

른 호흡, 혼수상태, 거친모피 등이 관찰됨 (출처: ECHA)

특정 표적장기 독성 (반복 노출)

랫드를 이용한 3개월 반복 경구독성 시험결과 유의한 증상은 관찰되지 않음, NOAEL=143

mg/kg bw/day(overall effects)(OECD Guideline 408, GLP) (출처: ECHA)

7/10

>>> page_7


http://www.chemtronics.co.kr

흡인유해성

자료없음

## 12. 환경에 미치는 영향

가. 생태독성

96 hr_LC

(Pimephales promelas )=527~732 mg/L(출처: ECHA)

50

갑각류

24 hr_EC

(Daphnia magna )=820 mg/L(출처: ECHA)

50

조류

72 hr_EC

(Green Alga )=32.9 mg/L(출처: ECHA)

50

나. 잔류성 및 분해성

잔류성

Log Pow=0.86(25 ℃)(OECD Guideline 107)(출처: ECHA)

분해성

자료없음

다. 생물농축성

농축성

자료없음

생분해성

28d_90~100 % (O2소비량측정)(OECD Guideline 301 F)(출처: ECHA)

라. 토양이동성

log Koc=1.596(25 ℃)(KOCWIN v2.00)(출처: ECHA)

마. 기타 유해 영향

자료없음

## 13. 폐기시 주의사항

가. 폐기방법

폐기물관리법에 명시된 경우 규정에 따라 내용물 및 용기를 폐기하시오.

나. 폐기시 주의사항

폐기물관리법에 명시된 경우 규정에 명시된 주의사항을 고려하시오.

## 14. 운송에 필요한 정보

가. 유엔번호(UN No.)

1915

나. 적정선적명

CYCLOHEXANONE

다. 운송에서의 위험성 등급

3

라. 용기등급

III

마. 해양오염물질

비해당

바. 사용자가 운송 또는 운송수단에 관련해 알 필요가 있거나 필요한 특별한 안전대책

화재시 비상조치

F-E

유출시 비상조치

S-D

## 15. 법적규제 현황

가. 산업안전보건법에 의한 규제

관리대상유해물질

작업환경측정대상물질 (측정주기 : 6개월)

특수건강진단대상물질 (진단주기 : 12개월)

노출기준설정물질

허용기준설정물질

PSM 제출 대상물질

나. 화학물질관리법에 의한 규제

해당없음

다. 위험물안전관리법에 의한 규제

제4류 인화성액체의 제2석유류 비수용성액체 1000 L

라. 폐기물관리법에 의한 규제

지정폐기물

마. 기타 국내 및 외국법에 의한 규제

국내규제

잔류성유기오염물질관리법

해당없음

8/10

>>> page_8


http://www.chemtronics.co.kr

국외규제

미국관리정보(OSHA 규정)

해당없음

미국관리정보(CERCLA 규정)

2267.995 kg 5000 lb

미국관리정보(EPCRA 302 규정)

해당없음

미국관리정보(EPCRA 304 규정)

해당없음

미국관리정보(EPCRA 313 규정)

해당없음

미국관리정보(로테르담협약물질)

해당없음

미국관리정보(스톡홀름협약물질)

해당없음

미국관리정보(몬트리올의정서물질)

해당없음

EU 분류정보(확정분류결과)

Flam. Liq. 3, Acute Tox. 4

EU 분류정보(위험문구)

H226, H332

## 16. 그 밖의 참고사항

## 가.자료의 출처

ACGIH; https://www.acgih.org/

IARC; http://monographs.iarc.fr/ENG/Classification/latest_classif.php

NTP; http://ntp.niehs.nih.gov/index.cfm

OSHA; https://www.osha.gov/laws-regs/regulations/standardnumber/1910/1910.119AppA

UN Recommendations on the Transport of Dangerous Goods-Model Regulations Twenty-firstedition;

https://www.unece.org/trans/danger/publi/ unrec/rev21/21files_e.html

한국해사위험물검사원(KOMDI); https://www.komdi.or.kr/ukiwi/biz/info/ukiwiBizInfoIMDGCodeList.do

산업안전보건기준에 관한 규칙 [별표 12]

산업안전보건법 시행규칙 [별표 21]

산업안전보건법 시행규칙 [별표 22] [별표 23]

화학물질 및 물리적 인자의 노출기준; 고용노동부고시 제2020-48호

산업안전보건법 시행규칙 [별표 19]

산업안전보건법 시행령 [별표 13]

제한물질·금지물질의 지정 [별표 2]

제한물질·금지물질의 지정 [별표 4]

유독물질의 지정고시 [별표](화평법 시행령 제3조, 화관법 시행령 제2조의 지정기준에 해당하는 유독물질)

화학물질관리법 시행규칙 [별표10]

폐기물관리법; http://www.law.go.kr/LSW//lsInfoP.do?lsiSeq=212975&ancYd=20191231&ancNo=00843&efYd=

20200701&nwJoYnInfo=N&efGubun=Y&chrClsCd=010202&ancYnChk=0#AJAX

국가위험물정보시스템(KFI); http://hazmat.mpss.kfi.or.kr/material.do

몬트리올의정서; https://www.epa.gov/ozone-layer-protection/ozone-depleting-substances

로테르담협약물질; http://www.pic.int/TheConvention/Chemicals/

잔류성오염물질관리법; [별표 1] 잔류성오염물질(제2조관련)

미국관리정보(OSHA); https://www.osha.gov/laws-regs/regulations/standardnumber/1910/1910.119AppA

미국관리정보(CERCLA, EPCRA 302, EPCRA 304 규정, EPCRA 313); https://www.epa.gov/sites/production/files/

2015-03/documents/list_of_lists.pdf

EU SVHC list; https://echa.europa.eu/authorisation-list

EU Authorisation List; https://echa.europa.eu/substances-restricted-under-reach

9/10

>>> page_9


http://www.chemtronics.co.kr

EU Restriction list; https://echa.europa.eu/information-on-chemicals/biocidal-active-

substances?p_p_id=dissactivesubstances_WAR_dissactivesubstancesportlet&p_p_lifecycle=1&p

_p_state=normal&p_p_mode=view&p_p_col_id=column-1&p_p_col_pos=2&p_p_col_count=3&_

dissactivesubstances_WAR_dissactivesubstancesportlet_javax.portlet.action=dissActive SubstancesAction

화학물질 노출 근로자를 위한 호흡보호구 선정 지침 개발

안전보건공단(KOSHA); http://msds.kosha.or.kr/kcic/msdssearchLaw.do

NCIS; http://ncis.nier.go.kr/

ECHA; https://echa.europa.eu/information-on-chemicals/registered-substances

HSDB; https://pubchem.ncbi.nlm.nih.gov/

EPA; https://comptox.epa.gov/dashboard/

나. 최초작성일

2009-11-19

다. 개정횟수 및 최종 개정일자

개정횟수

최종 개정일자

2021-03-26

라. 기타

본 MSDS는 산업안전보건법 제110조에 의거하여 화학물질 분류표시 및 물질안전보건자료

작성 고시 제2020-130호를 바탕으로 작성한 것입니다.

본 MSDS는 구매자, 취급자 또는 제 3자의 물질안전취급에 도움을 주고자 작성되었으므로

특수한 목적의 적합성이나 다른 물질과 병용하여 사용하는 상업적 적용이나 표현에 대해

서는 어떠한 보증도 할 수 없고, 어떠한 기술적∙법적 책임도 질 수 없음에 유의 바랍니다.

본 MSDS에 포함된 내용은 국가 및 지역에 따라 상이할 수 있으며, 실제 관련 규정의 내용

과 일치하지 않을 수 있으므로, 구매자 및 취급자는 정부 및 해당 지역의 관련 규정을 확인

하여 준수할 책임이 있습니다.

본 MSDS는 특정 제품에만 관련된 내용이며, 별도로 명시되지 않은 다른 재료 및 다른 제

조 공정에서 함께 사용하는 경우에는 적용되지 않을 수 있사오니 사용자가 직접 활동에

관련한 모든 규정을 준수하는지에 대한 보증을 하지 않습니다.

10/10

"""
        },
                {
            "document_id": "MOCK_MSDS_002",
            "file_name": "output(3).pdf",
            "content": """>>> page_0


## 물질안전보건자료(MSDS)

MSDS 번호 : AA00725-0000098004

## 1. 화학제품과 제조회사 정보

제품명: 아세톤 (Acetone)

제품의 권고 용도와 사용상의 제한

제품의 권고 용도 : 시험용, 연구용, 실험용 화학물질(시약), 기타(산업용)

제품의 사용상의 제한 : 자료없음

공급자 정보

회사명 : OCI주식회사

주소 : 서울특별시 중구 소공로 94(소공동)

긴급전화번호 : 02-727-9494



## 2. 유해성·위험성

1) 유해성·위험성 분류     인화성 액체  : 구분2

심한 눈 손상성/눈 자극성  : 구분2

특정표적장기 독성(1회 노출)  : 구분3(마취작용)

흡인 유해성  : 구분2

2) 예방조치문구를 포함한 경고표지 항목

그림문자

그림문자


신호어                위험

유해·위험문구

H225 고인화성 액체 및 증기

H305 삼켜서 기도로 유입되면 유해할 수 있음

H319 눈에 심한 자극을 일으킴

H336 졸음 또는 현기증을 일으킬 수 있음

예방조치문구

예방                P210 열·스파크·화염·고열로부터 멀리하시오 - 금연

P233 용기를 단단히 밀폐하시오.

P240 용기와 수용설비를 접합시키거나 접지하시오.

P241 폭발 방지용 전기·환기·조명·장비를 사용하시오.

P242 스파크가 발생하지 않는 도구만을 사용하시오.

P243 정전기 방지 조치를 취하시오.

P261 흄·가스·미스트·증기·스프레이의 흡입을 피하시오.

P264 취급 후에는 취급 부위를 철저히 씻으시오.

>>> page_1


P271 옥외 또는 환기가 잘 되는 곳에서만 취급하시오.

P280 보호장갑·보호의·보안경·안면보호구를 착용하시오.

대응



P301+P310 삼켰다면 즉시 의료기관(의사)의 진찰을 받으시오.

P303+P361+P353 피부(또는 머리카락)에 묻으면 오염된 모든 의복은

벗으시오. 피부를 물로 씻으시오/샤워하시오.

P304+P340 흡입하면 신선한 공기가 있는 곳으로 옮기고 호흡하기 쉬운

자세로 안정을 취하시오.

P305+P351+P338 눈에 묻으면 몇 분간 물로 조심해서 씻으시오. 가능하면

콘택트렌즈를 제거하시오. 계속 씻으시오.

P312 불편함을 느끼면 의료기관(의사)의 진찰을 받으시오.

P331 토하게 하지 마시오.

P337+P313 눈에 자극이 지속되면 의학적인 조치·조언을 구하시오.

P370+P378 화재 시 불을 끄기 위해 알콜포말·이산화탄소·물분무를

P370+P378 화재 시 불을 끄기 위해 알콜포말·이산화탄소·물분무를

사용하시오.

사용하시오.

저장



P403+P233 용기는 환기가 잘 되는 곳에 단단히 밀폐하여 저장하시오.

P403+P235 환기가 잘 되는 곳에 보관하고 저온으로 유지하시오.

P405 잠금장치가 있는 저장장소에 저장하시오.

폐기



P501 폐기물 관리법에 명시된 내용에 따라 내용물 및 용기를 폐기하시오.

3) 유해성·위험성 분류기준에 포함되지 않는 기타 유해성·위험성(NFPA)

보건                  1

화재                  3

## 3. 구성성분의 명칭 및 함유량

화학물질명                아세톤 (Acetone)

이명(관용명)               2-프로파논

CAS 번호                 67-64-1

함유량                    100%

## 4. 응급조치 요령

1) 눈에 들어갔을 때       눈에 묻으면 몇 분간 물로 조심해서 씻으시오. 가능하면 콘택트렌즈를

제거하시오. 계속 씻으시오

눈에 자극이 지속되면 의학적인 조치·조언을 구하시오

2) 피부에 접촉했을 때

긴급 의료조치를 받으시오

오염된 옷과 신발을 제거하고 오염지역을 격리하시오

화상의 경우 즉시 찬물로 가능한 오래 해당부위를 식히고, 피부에 들러붙은

옷은 제거하지 마시오

비누와 물로 피부를 씻으시오

피부(또는 머리카락)에 묻으면 오염된 모든 의복은 벗거나 제거하시오.

피부를 물로 씻으시오/샤워하시오

불편함을 느끼면 의료기관(의사)의 진찰을 받으시오

>>> page_2


3) 흡입했을 때



과량의 먼지 또는 흄에 노출된 경우 깨끗한 공기로 제거하고 기침이나 다른

증상이 있을 경우 의료 조치를 취하시오

긴급 의료조치를 받으시오

호흡하지 않는 경우 인공호흡을 실시하시오

호흡이 힘들 경우 산소를 공급하시오

4) 먹었을 때



긴급 의료조치를 받으시오

5) 기타 의사의 주의사항  의료인력이 해당물질에 대해 인지하고 보호조치를 취하도록 하시오

## 5. 폭발 화재시 대처 방법

1) 적절한(부적절한) 소화제

이 물질과 관련된 소화시 알콜 포말, 이산화탄소 또는 물분무를 사용할 것질식소화시

건조한 모래 또는 흙을 사용할 것

2) 화학물질로부터 생기는 특정 유해성

고인화성 액체 및 증기

격렬하게 중합반응하여 화재와 폭발을 일으킬 수 있음

증기는 점화원에 옮겨져 발화될 수 있음

타는 동안 열분해 또는 연소에 의해 자극적이고 매우 유독한 가스가 발생될 수 있음

인화점이나 그 이상에서 폭발성 혼합물을 형성할 수 있음

가열시 용기가 폭발할 수 있음

고인화성: 열, 스파크, 화염에 의해 쉽게 점화됨

누출물은 화재/폭발 위험이 있음

실내, 실외, 하수구에서 증기 폭발 위험이 있음

증기는 공기와 폭발성 혼합물을 형성할 수 있음

증기는 점화원까지 이동하여 역화(flash back)할 수 있음

증기는 자각 없이 현기증 또는 질식을 유발할 수 있음

흡입 및 접촉 시 피부와 눈을 자극하거나 화상을 입힘

3) 화재진압시 착용할 보호구 및 예방조치

구조자는 적절한 보호구를 착용하시오.

지역을 벗어나 안전거리를 유지하여 소화하시오

대부분 물보다 가벼우니 주의하시오

대부분의 증기는 공기보다 무겁기 때문에 지면을 따라 확산하고 저지대나 밀폐공간에

축적될 수 있음

위험하지 않다면 화재지역에서 용기를 옮기시오

## 6. 누출사고시 대처방법

1) 인체를 보호하기 위해 필요한 조치사항 및 보호구

매우 미세한 입자는 화재나 폭발을 일으킬 수 있으므로 모든 점화원을 제거하시오.

엎질러진 것을 즉시 닦아내고, 보호구 항의 예방조치를 따르시오.

노출물을 만지거나 걸어다니지 마시오

모든 점화원을 제거하시오

물질 취급시 모든 장비를 반드시 접지하시오

>>> page_3


위험하지 않다면 누출을 멈추시오

증기발생을 줄이기 위해 증기억제포말을 사용할 수 있음

피해야할 물질 및 조건에 유의하시오

흄·가스·미스트·증기·스프레이의 흡입을 피하시오.

2) 환경을 보호하기 위해 필요한 조치사항

누출물은 오염을 유발할 수 있음

수로, 하수구, 지하실, 밀폐공간으로의 유입을 방지하시오

3) 정화 또는 제거 방법

소화를 위해 제방을 쌓고 물을 수거하시오.

불활성 물질(예를 들어 건조한 모래 또는 흙)로 엎지른 것을 흡수하고, 화학폐기물

용기에 넣으시오.

액체를 흡수하고 오염된 지역을 세제와 물로 씻어 내시오.

다량 누출시 액체 누출물과 멀게하여 도랑을 만드시오

청결한 방폭 도구를 사용하여 흡수된 물질을 수거하시오

## 7. 취급 및 저장 방법

1) 안전취급요령       압력을 가하거나, 자르거나, 용접, 납땜, 접합, 뚫기, 연마 또는 열에 폭로,

화염,불꽃, 정전기 또는 다른 점화원에 폭로하지 마시오.

취급/저장에 주의하여 사용하시오.

개봉 전에 조심스럽게 마개를 여시오.

물질 취급시 모든 장비를 반드시 접지하시오

피해야할 물질 및 조건에 유의하시오

공학적 관리 및 개인보호구를 참조하여 작업하시오

저지대 밀폐공간에서 작업시 산소결핍의 우려가 있으므로 작업중, 공기중

산소농도 측정 및 환기를 하시오

폭발 방지용 전기·환기·조명·장비를 사용하시오.

스파크가 발생하지 않는 도구만을 사용하시오.

스파크가 발생하지 않는 도구만을 사용하시오.

흄·가스·미스트·증기·스프레이의 흡입을 피하시오.

취급 후에는 취급 부위를 철저히 씻으시오.

옥외 또는 환기가 잘 되는 곳에서만 취급하시오.

2) 안전한 저장방법      피해야할 물질 및 조건에 유의하시오

열·스파크·화염·고열로부터 멀리하시오 - 금연

용기는 환기가 잘 되는 곳에 단단히 밀폐하여 저장하시오.

환기가 잘 되는 곳에 보관하고 저온으로 유지하시오.

## 8. 노출방지 및 개인보호구

1) 화학물질의 노출기준, 생물학적 노출기준 등

국내규정              TWA 500 ppm

STEL 750 ppm

ACGIH 규정           TWA 250 ppm



STEL 500 ppm

생물학적 노출기준     자료없음

>>> page_4


2) 적절한 공학적 관리     공정격리, 국소배기를 사용하거나, 공기수준을 노출기준 이하로 조절하는

다른 공학적 관리를 하시오.

이 물질을 저장하거나 사용하는 설비는 세안설비와 안전 샤워를

설치하시오.

3) 개인보호구

호흡기 보호             해당물질에 노출 또는 노출 가능성이 있는 경우, 물리화학적

특성에 맞는 한국산업안전보건공단의 인증을 필한 호흡용 보호구를

착용하시오

눈 보호                 해당물질에 직접적인 노출 또는 노출 가능성이 있는 경우,

한국산업안전보건공단 인증을 받은 화학물질용 보안경을 착용하시오.

작업장 가까운 곳에 세안설비와 비상세척설비(샤워식)를 설치하시오.

손 보호                 해당물질에 직접적인 노출 또는 노출 가능성이 있는 경우,

한국산업안전보건공단 인증을 받은 화학물질용 안전 장갑을 착용하시오.

신체 보호

해당물질에 직접적인 노출 또는 노출 가능성이 있는 경우,

한국산업안전보건공단 인증을 받은 화학물질용 보호복을 착용하시오.

## 9. 물리화학적 특성

외관

성상                                 액체

색상                                 무색

냄새                                   달콤한 냄새

냄새역치                               24-1615 ㎎/㎥

pH                                     자료없음

녹는점/어는점                          -94.6 ℃

녹는점/어는점                          -94.6 ℃

초기 끓는점과 끓는점 범위              56.1 ℃

초기 끓는점과 끓는점 범위              56.1 ℃

인화점                                 -17 ℃

인화점                                 -17 ℃

증발속도                               자료없음

증발속도                               자료없음

인화성(고체, 기체)                      해당없음

인화성(고체, 기체)                      해당없음

인화 또는 폭발 범위의 상한/하한        13 / 2.2 %

인화 또는 폭발 범위의 상한/하한        13 / 2.2 %

증기압                                 24 ㎪ (20℃)

증기압                                 24 ㎪ (20℃)

용해도                                 1000g/L(25℃)

증기밀도                               2

비중                                   0.8

n-옥탄올/물분배계수                    -0.24

n-옥탄올/물분배계수                    -0.24

자연발화온도                           465 ℃

분해온도                               자료없음

점도                                   0.303 cP (25℃ 2))

분자량                                 58.08

## 10. 안정성 및 반응성

1) 화학적 안정성 및 유해 반응의 가능성

>>> page_5


고인화성 액체 및 증기

격렬하게 중합반응하여 화재와 폭발을 일으킬 수 있음

인화점이나 그 이상에서 폭발성 혼합물을 형성할 수 있음

가열시 용기가 폭발할 수 있음

고인화성: 열, 스파크, 화염에 의해 쉽게 점화됨

누출물은 화재/폭발 위험이 있음

실내, 실외, 하수구에서 증기 폭발 위험이 있음

증기는 공기와 폭발성 혼합물을 형성할 수 있음

증기는 점화원까지 이동하여 역화(flash back)할 수 있음

증기는 자각 없이 현기증 또는 질식을 유발할 수 있음

증기는 자각 없이 현기증 또는 질식을 유발할 수 있음

화재시 자극성, 부식성, 독성 가스를 발생할 수 있음

흡입 및 접촉 시 피부와 눈을 자극하거나 화상을 입힘

2) 피해야 할 조건

열·스파크·화염·고열로부터 멀리하시오 - 금연

3) 피해야 할 물질

가연성 물질, 환원성 물질

4) 분해시 생성되는 유해물질

탄소산화물 등의 자극적/유독성 가스가 발생할수 있음

## 11. 독성에 관한 정보

1) 가능성이 높은 노출 경로에 관한 정보

자료없음

2) 건강 유해성 정보

급성독성

경구

LD50 5800 ㎎/㎏ Rat

경피

LD50

>

7400 ㎎/㎏ Rabbit

흡입

증기 LC50 76 ㎎/ 4 hr Rat

피부부식성 또는 자극성

기니피그를 이용한 피부부식성/자극성 시험결과, 자극성

없음홍반지수=0, 부종지수=0

심한 눈손상 또는 자극성

토끼를 이용한 심한눈손상/자극성 시험결과, 약한 자극성이 있음.

드레이즈 지수Draize scores 에 기초한 영향은 7 일 이내에

완전히 회복됨Maximum mean total score MMTS=19.1,

각막지수=25, 홍채지수=3.8, 결막지수=9.2 OECD TG 405

호흡기과민성

자료없음

피부과민성

기니피그를 대상으로 피부과민성 시험결과, 피부과민성 관찰되지

않음

발암성

발암성

산업안전보건법                  자료없음

고용노동부고시                  자료없음

IARC                            자료없음

OSHA                           자료없음

ACGIH                           A4

NTP                             자료없음

NTP                             자료없음

>>> page_6


EU CLP                          자료없음

생식세포변이원성                 소핵시험 음성 SIDS 1999, EHC 207 1998 시험관 내 미생물을

이용한 복귀돌연변이시험결과, 대사활성계 적용여부에 상관없이

음성OECD TG 471, 시험관 내 포유류 배양세포를 이용한

염색체이상시험결과, 대사활성계 유무에 상관없이 음성OECD TG

473, 시험관 내 배양세포를 이용한 유전자돌연변이시험결과,

대사활성계 있을 때 음성OECD TG 476 생체 내 햄스터암/수,

마우스암/수를 이용한 소핵시험결과 음성 복귀돌연변이시험결과

음성, 중국햄스터난소세포를 이용한 염색체 변형분석결과 음성,

생체 내 중국 햄스터 소핵시험결과 음성. 시험관 내 미생물을

이용한 복귀돌연변이시험결과 음성OECD TG 471, 생체 내

포유류 적혈구를 이용한 소핵시험 음성 OECD TG 474

생식독성                          랫드(암/수)를 대상으로 생식독성시험결과, 정자활력 감소,

이상정자발생증가, 꼬리 부고환 및 부고한 무게 감소가

나타남(NOAEL=900 mg/kg bw/day , LOAEL=1,700 mg/kg

bw/day), 마우스를 대상으로 발달독성시험결과, 태아무게 감소,

늦은 재- 흡수의 발생비율 증가가 나타남(NOAEC=2,200 ppm,

LOAEC=6,600ppm)(OECD Guideline 414) 분류에 적용하기에는

고농도에서의 영향이 관찰됨

특정 표적장기 독성 (1 회 노출)       사람에서 코, 기도, 기관지 자극, 고농도 노출시 두통, 현기증,

다리의 탈진, 실신을 일으킴. ACGIH 2001, ECH 207 1998

표적장기: 눈, 피부, 호흡기계, 중추신경계 NIOSH 냄새역치=10,

20 분 노출시 냄새지수 w-28%, c-46%감소, 자극지수 :

c-30%감소, 기도, 비강에 자극, 두통, 졸음 코 자극역치

10000ppm25000mg/m3; NOAEC 5000ppm24000mg/m3

특정 표적장기 독성 (반복 노출)       500ppm 6 시간/일, 6 일 노출 군에서 백혈구호산구의 유의한

증가 및 호중구 탐식작용의 유의한 감소가 관찰됨 랫드를

대상으로 90 일 아만성경구독성시험결과, 수컷랫드에게 고환,

신장 및 조혈시스템에서 약한 독성발겸됨 NOAEL=10,000

ppm900 mg/kg bw/d, LOAEL=20,000ppm1,700 mg/kg bw/d

OECD TG 408 랫드를 대상으로 90 일 아만성독성시험결과,

다양한 혈액학상의 지표, 혈청활성 증가, 상대 간 및 신장 무게의

증가관찰됨. NOEL=1%900 mg/kg/day 랫드를 이용한 13 주

흡입반복독성시험결과, 최고농도 4000ppm9500mg/m3 까지

신경계 기능, 업무인지, 등의 영향이 관찰되지 않음.

NOAEL=9500mg/m3=1000mg/kg bw/day 분류기준 이상의

고용량에서만 반복독성으로 인한 영향이 관찰되어 분류되지않음









(2001)

흡인유해성                        동점성률 0.426 ㎟/s 계산치 케톤류이며 동점성률 0.426 ㎟/s

12. 환경에 미치는 영향

>>> page_7


1) 생태독성

어류                               LC50 5540mg/L 96 hrOncorhynchus mykiss(OECD Guideline

203)

갑각류                             LC50 8800 ㎎/ℓ 48 hr Daphnia pulex

해조류                             EC50 11798 ㎎/ℓ 5 day Skeletonema costatum

2) 잔류성 및 분해성

잔류성                             -0.24 log Kow

분해성                             BOD 5: 1.85 g O2/g test mat, COD: 1.92 g O2/g test mat,

BOD5*100/COD: 96%, APHA Standard methods No.219

1971

3) 생물농축성

농축성                             자료없음

생분해성                           62 % 5 day (OECD TG 301B)

4) 토양이동성                          자료없음

5) 기타 유해 영향                      자료없음

## 13. 폐기시 주의사항

1) 폐기방법                폐기물관리법에 명시된 경우 규정에 따라 내용물 및 용기를 폐기하시오.

2) 폐기시 주의사항         폐기물관리법에 명시된 경우 규정에 명시된 주의사항을 고려하시오.

## 14. 운송에 필요한 정보

1) 유엔번호(UN No.)                  1090

2) 적정선적명                        아세톤 (아세톤 용액)(ACETON(ACETONE SOLUTIONS))

3) 운송에서의 위험성 등급            3

4) 용기 등급                         II

5) 해양오염물질                      자료없음

6) 사용자가 운송 또는 운송수단에 관련해 알 필요가 있거나 필요한 특별한 안전대책

화재시 비상조치                 F-E

유출시 비상조치                 S-D

## 15. 법적 규제 현황

1) 산업안전보건법에 의한 규제

작업환경측정물질(측정주기 : 6개월)

관리대상물질

특수건강진단물질(진단주기 : 12개월)

공정안전보고서(PSM) 제출 대상물질

노출기준설정물질

2) 화학물질관리법에 의한 규제

해당없음

3) 위험물안전관리법에 의한 규제

제4류 제1석유류(수용성액체) 400ℓ

4) 폐기물관리법에 의한 규제

지정폐기물

5) 기타 국내 및 외국법에 의한 규제

>>> page_8


## 국내규제

잔류성 유기오염물질관리법

해당없음

국외규제

미국관리정보(OSHA 규정)

해당없음

미국관리정보(CERCLA규정)

2267.995 kg 5000 lb

미국관리정보(EPCRA 302 규정)

해당없음

미국관리정보(EPCRA 304 규정)



해당없음

미국관리정보(EPCRA 313 규정)



해당없음

미국관리정보(로테르담협약물질)



해당없음

미국관리정보(스톡홀름협약물질)



해당없음

EU 분류정보(확정분류결과)



F; R11Xi; R36R66R67

EU 분류정보(위험문구)





H225, H336, H319

EU 분류정보(위험문구)





H225, H336, H319

EU 분류정보(안전문구)



S2, S9, S16, S26, S46

## 16. 기타 참고자료

## 1) 자료의 출처

한국산업안전공단 물질안전보건자료, 화학상품대사전 – 가나다화학,

국립환경과학원 화학물질정보시스템, 소방방재청 위험물정보관리시스템

2) 최초 작성일자 : 1996. 05. 02.

3) 개정횟수 및 최종개정일자

개정 번호 : 17                    최종개정일자 : 2022. 04. 08.

제공된 정보는 제품에 대한 현상태의 지식과 경험에 따른 것으로서 완전하지는 않습니다. 이 정보는

달리 언급하지 않는 한 명세에 따르는 제품에 적용됩니다. 특수한 목적에 대한 적합성, 다른 물질과의

혼용, 상업적 적용 또는 표현에 대해서는 어떠한 보증도 할 수 없으며, 어떠한 기술적, 법적 책임도 질

수 없음에 유의하여야 합니다. 어느 경우에도 사용자는 제품, 개인 위생, 인류 복지와 환경 보호에 관한

모든 법률, 행정, 규제 절차를 준수할 의무에서 면제되지 않습니다.

.

"""
        },
                {
            "document_id": "MOCK_MSDS_003",
            "file_name": "output(4).pdf",
            "content": """>>> page_0


Revision date: 29/07/2020

Revision: 5

Supersedes date: 28/07/2020


## SAFETY DATA SHEET

## HYDROCHLORIC ACID 1.18 S.G. LRG

According to Regulation (EC) No 1907/2006, Annex II, as amended. Commission Regulation (EU) No 2015/830

of 28 May 2015.

## SECTION 1: Identification of the substance/mixture and of the company/undertaking

## 1.1. Product identifier

Product name

HYDROCHLORIC ACID 1.18 S.G. LRG

Product number

1206

REACH registration number

01-2119484862-27-XXXX

CAS number

7647-01-0

EU index number

017-002-01-X

EC number

231-595-7

## 1.2. Relevant identified uses of the substance or mixture and uses advised against

Identified uses

Cleaning agent. Laboratory reagent.

Uses advised against

No specific uses advised against are identified.

## 1.3. Details of the supplier of the safety data sheet

Supplier

Reagent Chemical Services

11b - 13 Aston Fields Road

Whitehouse Industrial Estate

Runcorn

Cheshire WA7 3DL

T: 01928 716903 (08.30 - 17.00)

F: 01928 716425

E: info@reagent.co.uk

## 1.4. Emergency telephone number

Emergency telephone

OHES Environmental Ltd 24-7

Tel. 0333 333 9939 (24 hour)

Notes

The product identification numbers refer to hydrogen chloride.

## SECTION 2: Hazards identification

## 2.1. Classification of the substance or mixture

## Classification (EC 1272/2008)

Physical hazards

Met. Corr. 1 - H290

Health hazards

Skin Corr. 1B - H314 Eye Dam. 1 - H318 STOT SE 3 - H335

Environmental hazards

Not Classified

Classification (67/548/EEC or

C;R34. Xi;R37.

1999/45/EC)

## 2.2. Label elements

1/15

>>> page_1


Revision date: 29/07/2020

Revision: 5

Supersedes date: 28/07/2020

## HYDROCHLORIC ACID 1.18 S.G. LRG

EC number

231-595-7

## Hazard pictograms


Signal word

Danger

Hazard statements

H290 May be corrosive to metals.

H314 Causes severe skin burns and eye damage.

H335 May cause respiratory irritation.

Precautionary statements

P260 Do not breathe vapour/ spray.

P271 Use only outdoors or in a well-ventilated area.

P280 Wear protective gloves/ protective clothing/ eye protection/ face protection.

P305+P351+P338 IF IN EYES: Rinse cautiously with water for several minutes. Remove

contact lenses, if present and easy to do. Continue rinsing.

P310 Immediately call a POISON CENTER/ doctor.

P501 Dispose of contents/ container in accordance with local regulations.

Contains

HYDROCHLORIC ACID 36 %

Supplementary precautionary

Supplementary precautionary

statements

P234 Keep only in original packaging.

P261 Avoid breathing vapour/ spray.

P264 Wash contaminated skin thoroughly after handling.

P301+P330+P331 IF SWALLOWED: Rinse mouth. Do NOT induce vomiting.

P303+P361+P353 IF ON SKIN (or hair): Take off immediately all contaminated clothing.

Rinse skin with water or shower.

P304+P340 IF INHALED: Remove person to fresh air and keep comfortable for breathing.

P312 Call a POISON CENTRE/doctor if you feel unwell.

P321 Specific treatment (see medical advice on this label).

P363 Wash contaminated clothing before reuse.

P390 Absorb spillage to prevent material damage.

P403+P233 Store in a well-ventilated place. Keep container tightly closed.

P405 Store locked up.

P406 Store in a corrosion-resistant/… container with a resistant inner liner.

## 2.3. Other hazards

This product does not contain any substances classified as PBT or vPvB.

## SECTION 3: Composition/information on ingredients

## 3.2. Mixtures

HYDROCHLORIC ACID ...%

10-30%

CAS number: 7647-01-0

EC number: 231-595-7

REACH registration number: 01-

2119484862-27-0000

Classification

Met. Corr. 1 - H290

Skin Corr. 1B - H314

Eye Dam. 1 - H318

STOT SE 3 - H335

The Full Text for all R-Phrases and Hazard Statements are Displayed in Section 16.

Composition comments

An aqueous solution of hydrochloric acid.

2/15

>>> page_2


Revision date: 29/07/2020

Revision: 5

Supersedes date: 28/07/2020

## HYDROCHLORIC ACID 1.18 S.G. LRG

## SECTION 4: First aid measures

## 4.1. Description of first aid measures

General information

Get medical attention immediately. Show this Safety Data Sheet to the medical personnel.

Chemical burns must be treated by a physician.

Inhalation

Remove affected person from source of contamination. Move affected person to fresh air and

Remove affected person from source of contamination. Move affected person to fresh air and

keep warm and at rest in a position comfortable for breathing. Maintain an open airway.

Loosen tight clothing such as collar, tie or belt. When breathing is difficult, properly trained

personnel may assist affected person by administering oxygen. Place unconscious person on

their side in the recovery position and ensure breathing can take place.

their side in the recovery position and ensure breathing can take place.

Ingestion

Rinse mouth thoroughly with water. Remove any dentures. Stop if the affected person feels

sick as vomiting may be dangerous. Do not induce vomiting unless under the direction of

medical personnel. If vomiting occurs, the head should be kept low so that vomit does not

enter the lungs. Never give anything by mouth to an unconscious person. Move affected

person to fresh air and keep warm and at rest in a position comfortable for breathing. Place

unconscious person on their side in the recovery position and ensure breathing can take

place. Maintain an open airway. Loosen tight clothing such as collar, tie or belt.

Skin contact

It is important to remove the substance from the skin immediately. Take off immediately all

contaminated clothing. Rinse immediately with plenty of water. Continue to rinse for at least

15 minutes and get medical attention. Chemical burns must be treated by a physician.

Eye contact

Rinse immediately with plenty of water. Remove contact lenses, if present and easy to do.

Continue rinsing. Continue to rinse for at least 10 minutes.

Protection of first aiders

First aid personnel should wear appropriate protective equipment during any rescue. If it is

suspected that volatile contaminants are still present around the affected person, first aid

personnel should wear an appropriate respirator or self-contained breathing apparatus. Wash

contaminated clothing thoroughly with water before removing it from the affected person, or

wear gloves. It may be dangerous for first aid personnel to carry out mouth-to-mouth

resuscitation.

## 4.2. Most important symptoms and effects, both acute and delayed

General information

See Section 11 for additional information on health hazards. The severity of the symptoms

described will vary dependent on the concentration and the length of exposure.

Inhalation

A single exposure may cause the following adverse effects: Severe irritation of nose and

throat. Symptoms following overexposure may include the following: Corrosive to the

respiratory tract.

Ingestion

May cause chemical burns in mouth, oesophagus and stomach. Symptoms following

overexposure may include the following: Severe stomach pain. Nausea, vomiting.

Skin contact

Causes severe burns. Symptoms following overexposure may include the following: Pain or

irritation. Redness. Blistering may occur.

Eye contact

Causes serious eye damage. Symptoms following overexposure may include the following:

Pain. Profuse watering of the eyes. Redness.

## 4.3. Indication of any immediate medical attention and special treatment needed

Notes for the doctor

Treat symptomatically.

## SECTION 5: Firefighting measures

## 5.1. Extinguishing media

Suitable extinguishing media

The product is not flammable. Extinguish with alcohol-resistant foam, carbon dioxide, dry

powder or water fog. Use fire-extinguishing media suitable for the surrounding fire.

3/15

>>> page_3


Revision date: 29/07/2020

Revision: 5

Supersedes date: 28/07/2020

## HYDROCHLORIC ACID 1.18 S.G. LRG

Unsuitable extinguishing

media

Do not use water jet as an extinguisher, as this will spread the fire.

## Unsuitable extinguishing

## media

## Specific hazards

## 5.2. Special hazards arising from the substance or mixture

## Containers can burst violently or explode when heated, due to excessive pressure build-up.

## Severe corrosive hazard. Water used for fire extinguishing, which has been in contact with the

## product, may be corrosive.

## Hazardous combustion

## products

Thermal decomposition or combustion products may include the following substances: Very

toxic or corrosive gases or vapours. Hydrogen chloride (HCl).

## 5.3. Advice for firefighters

## Protective actions during

## firefighting

Avoid breathing fire gases or vapours. Evacuate area. Keep upwind to avoid inhalation of

gases, vapours, fumes and smoke. Ventilate closed spaces before entering them. Cool

containers exposed to heat with water spray and remove them from the fire  area if it can be

done without risk. Cool containers exposed to flames with water until well after the fire is out.

If a leak or spill has not ignited, use water spray to disperse vapours and protect men stopping

the leak. Avoid discharge to the aquatic environment. Control run-off water by containing and

keeping it out of sewers and watercourses. If risk of water pollution occurs, notify appropriate

authorities.

## Special protective equipment

## for firefighters

Regular protection may not be safe. Wear chemical protective suit. Wear positive-pressure

self-contained breathing apparatus (SCBA) and appropriate protective clothing. Firefighter's

clothing conforming to European standard EN469 (including helmets, protective boots and

gloves) will provide a basic level of protection for chemical incidents.

## SECTION 6: Accidental release measures

## 6.1. Personal precautions, protective equipment and emergency procedures

## Personal precautions

No action shall be taken without appropriate training or involving any personal risk. Keep

unnecessary and unprotected personnel away from the spillage. Wear protective clothing as

described in Section 8 of this safety data sheet. Follow precautions for safe handling

described in this safety data sheet. Wash thoroughly after dealing with a spillage. Ensure

procedures and training for emergency decontamination and disposal are in place. Do not

touch or walk into spilled material. Provide adequate ventilation. Avoid inhalation of vapours

and spray/mists. Use suitable respiratory protection if ventilation is inadequate. Avoid contact

with skin and eyes. Avoid contact with contaminated tools and objects.

## 6.2. Environmental precautions

## Environmental precautions

The product may affect the acidity (pH) of water which may have hazardous effects on aquatic

organisms. Avoid discharge to the aquatic environment. Large Spillages: Inform the relevant

authorities if environmental pollution occurs (sewers, waterways, soil or air).

## 6.3. Methods and material for containment and cleaning up

4/15

>>> page_4


Revision date: 29/07/2020

Revision: 5

Supersedes date: 28/07/2020

## HYDROCHLORIC ACID 1.18 S.G. LRG

## Methods for cleaning up

Wear protective clothing as described in Section 8 of this safety data sheet. Clear up spills

immediately and dispose of waste safely. This product is corrosive. Approach the spillage

from upwind. Small Spillages: If the product is soluble in water, dilute the spillage with water

and mop it up. Alternatively, or if it is not water-soluble, absorb the spillage with an inert, dry

material and place it in a suitable waste disposal container. Large Spillages: If leakage cannot

be stopped, evacuate area. Flush spilled material into an effluent treatment plant, or proceed

as follows. Contain and absorb spillage with sand, earth or other non-combustible material.

Place waste in labelled, sealed containers. Clean contaminated objects and areas thoroughly,

observing environmental regulations. The contaminated absorbent may pose the same

hazard as the spilled material. Flush contaminated area with plenty of water. Wash thoroughly

after dealing with a spillage. The requirements of the local water authority must be complied

with if contaminated water is flushed directly to the sewer. Dispose of waste to licensed waste

disposal site in accordance with the requirements of the local Waste Disposal Authority.

## 6.4. Reference to other sections

## Reference to other sections

For personal protection, see Section 8. See Section 11 for additional information on health

hazards. See Section 12 for additional information on ecological hazards. For waste disposal,

see Section 13.

## SECTION 7: Handling and storage

## 7.1. Precautions for safe handling

## Usage precautions

Read and follow manufacturer's recommendations. Wear protective clothing as described in

Section 8 of this safety data sheet. Keep away from food, drink and animal feeding stuffs.

Handle all packages and containers carefully to minimise spills. Keep container tightly sealed

when not in use. Avoid the formation of mists. This product is corrosive. Immediate first aid is

imperative. Do not handle until all safety precautions have been read and understood. Do not

handle broken packages without protective equipment. Do not reuse empty containers.

## Advice on general

## occupational hygiene

Wash promptly if skin becomes contaminated. Take off contaminated clothing. Wash

contaminated clothing before reuse. Do not eat, drink or smoke when using this product.

Wash at the end of each work shift and before eating, smoking and using the toilet. Change

work clothing daily before leaving workplace.

## 7.2. Conditions for safe storage, including any incompatibilities

## Storage precautions

Store away from incompatible materials (see Section 10). Store in accordance with local

regulations. Store away from the following materials: Alkalis. Keep only in the original

container. Keep container tightly closed, in a cool, well ventilated place. Keep containers

upright. Protect containers from damage. Bund storage facilities to prevent soil and water

pollution in the event of spillage. The storage area floor should be leak-tight, jointless and not

absorbent.

## Storage class

Corrosive storage.

## 7.3. Specific end use(s)

Specific end use(s)

The identified uses for this product are detailed in Section 1.2.

## SECTION 8: Exposure controls/Personal protection

## 8.1. Control parameters

## Occupational exposure limits

## HYDROCHLORIC ACID ...%

Long-term exposure limit (8-hour TWA): WEL 1 ppm 2 mg/m³ gas and aerosol mists

Short-term exposure limit (15-minute): WEL 5 ppm 8 mg/m³ gas and aerosol mists

WEL = Workplace Exposure Limit.

5/15

>>> page_5


Revision date: 29/07/2020

Revision: 5

Supersedes date: 28/07/2020

## HYDROCHLORIC ACID 1.18 S.G. LRG

DNEL

Workers - Inhalation; Long term local effects: 8 mg/m³

Workers - Inhalation; Short term local effects: 15 mg/m³

General population - Inhalation; Long term local effects: 8 mg/m³

General population - Inhalation; Short term local effects: 15 mg/m³

## HYDROCHLORIC ACID ...% (CAS: 7647-01-0)

DNEL

Workers - Inhalation; Long term local effects: 8 mg/m³

Workers - Inhalation; Short term local effects: 15 mg/m³

General population - Inhalation; Long term local effects: 8 mg/m³

General population - Inhalation; Short term local effects: 15 mg/m³

## 8.2. Exposure controls

## Protective equipment

Protective equipment


Appropriate engineering

controls

Provide adequate ventilation. Personal, workplace environment or biological monitoring may

be required to determine the effectiveness of the ventilation or other control measures and/or

the necessity to use respiratory protective equipment. Use process enclosures, local exhaust

ventilation or other engineering controls as the primary means to minimise worker exposure.

Personal protective equipment should only be used if worker exposure cannot be controlled

adequately by the engineering control measures. Ensure control measures are regularly

inspected and maintained. Ensure operatives are trained to minimise exposure.

Eye/face protection

Eyewear complying with an approved standard should be worn if a risk assessment indicates

eye contact is possible. Personal protective equipment for eye and face protection should

comply with European Standard EN166. Wear tight-fitting, chemical splash goggles or face

shield. If inhalation hazards exist, a full-face respirator may be required instead.

Hand protection

Chemical-resistant, impervious gloves complying with an approved standard should be worn if

a risk assessment indicates skin contact is possible. To protect hands from chemicals, gloves

should comply with European Standard EN374. Considering the data specified by the glove

manufacturer, check during use that the gloves are retaining their protective properties and

change them as soon as any deterioration is detected. Frequent changes are recommended.

It is recommended that gloves are made of the following material: Nitrile rubber. Butyl rubber.

Polyvinyl chloride (PVC). Viton rubber (fluoro rubber). The selected gloves should have a

breakthrough time of at least 8 hours. Protective gloves should have a minimum thickness of

0.4 mm. The most suitable glove should be chosen in consultation with the glove

supplier/manufacturer, who can provide information about the breakthrough time of the glove

material.

Other skin and body

protection

Hygiene measures

Appropriate footwear and additional protective clothing complying with an approved standard

should be worn if a risk assessment indicates skin contamination is possible.

Provide eyewash station and safety shower. Contaminated work clothing should not be

allowed out of the workplace. Wash contaminated clothing before reuse. Clean equipment

and the work area every day. Good personal hygiene procedures should be implemented.

Wash at the end of each work shift and before eating, smoking and using the toilet. When

using do not eat, drink or smoke. Preventive industrial medical examinations should be carried

out. Warn cleaning personnel of any hazardous properties of the product.

6/15

>>> page_6


Revision date: 29/07/2020

Revision: 5

Supersedes date: 28/07/2020

## HYDROCHLORIC ACID 1.18 S.G. LRG

## Respiratory protection

Respiratory protection complying with an approved standard should be worn if a risk

assessment indicates inhalation of contaminants is possible. Ensure all respiratory protective

equipment is suitable for its intended use and is ‘CE’-marked. Check that the respirator fits

tightly and the filter is changed regularly. Gas and combination filter cartridges should comply

with European Standard EN14387. Full face mask respirators with replaceable filter cartridges

should comply with European Standard EN136. Half mask and quarter mask respirators with

replaceable filter cartridges should comply with European Standard EN140. Consult with the

supplier as to the compatibility of the equipment with the chemical of concern.

## Environmental exposure

controls

Keep container tightly sealed when not in use. Emissions from ventilation or work process

equipment should be checked to ensure they comply with the requirements of environmental

protection legislation. In some cases, fume scrubbers, filters or engineering modifications to

the process equipment will be necessary to reduce emissions to acceptable levels. Store in a

demarcated bunded area to prevent release to drains and/or watercourses.

## SECTION 9: Physical and chemical properties

## 9.1. Information on basic physical and chemical properties

Appearance

Liquid.

Colour

Colourless.

Odour

Pungent.

pH

pH (concentrated solution): <1

Melting point

Not determined.

Initial boiling point and range

Not determined.

Flash point

Not relevant.

Evaporation rate

Not determined.

Evaporation factor

Not determined.

Flammability (solid, gas)

No.

Upper/lower flammability or

explosive limits

Not relevant.

Vapour pressure

Not determined.

Vapour density

Not determined.

Relative density

Approx. 1.18 @ @ 20°C

Bulk density

Not relevant.

Solubility(ies)

Not determined. Miscible with water.

Partition coefficient

Not applicable. REACH dossier information.

Auto-ignition temperature

Not relevant.

Decomposition Temperature

Not determined.

Viscosity

Not determined.

Explosive properties

Not considered to be explosive.

Explosive under the influence

of a flame

No

Oxidising properties

Does not meet the criteria for classification as oxidising.

7/15

>>> page_7


Revision date: 29/07/2020

Revision: 5

Supersedes date: 28/07/2020

## HYDROCHLORIC ACID 1.18 S.G. LRG

9.2. Other information

Refractive index

Not determined.

Particle size

Not relevant.

Molecular weight

Not relevant.

Volatility

Not determined.

Saturation concentration

Not determined.

Critical temperature

Not relevant.

Volatile organic compound

Not relevant.

## SECTION 10: Stability and reactivity

## 10.1. Reactivity

Reactivity

The following materials may react with the product: Alkalis. Inorganic sulphides. Organic

sulphur compounds. Oxidising agents. Inorganic cyanides. Organic cyanides (nitriles).

## 10.2. Chemical stability

Stability

Stable at normal ambient temperatures and when used as recommended. Stable under the

prescribed storage conditions.

## 10.3. Possibility of hazardous reactions

Possibility of hazardous

reactions

May generate heat. In contact with some metals can generate hydrogen gas, which can form

explosive mixtures with air. Reactions can occur with incompatible materials to produce toxic

or corrosive gases. May produce hydrogen cyanide or hydrogen sulphide.

## 10.4. Conditions to avoid

Conditions to avoid

Avoid heat. Containers can burst violently or explode when heated, due to excessive pressure

build-up.

## 10.5. Incompatible materials

Materials to avoid

Alkalis. Amines. Mild steel. Stainless steel. Aluminium. May be corrosive to metals. Oxidising

agents. Inorganic sulphides. Organic sulphur compounds. Inorganic cyanides. Organic

agents. Inorganic sulphides. Organic sulphur compounds. Inorganic cyanides. Organic

cyanides (nitriles).

## 10.6. Hazardous decomposition products

Hazardous decomposition

products

Does not decompose when used and stored as recommended.

## SECTION 11: Toxicological information

## 11.1. Information on toxicological effects

## Acute toxicity - oral

Notes (oral LD₅₀)

Based on available data the classification criteria are not met.

Acute toxicity - dermal

Notes (dermal LD₅₀)

Based on available data the classification criteria are not met.

Acute toxicity - inhalation

Acute toxicity inhalation (LC₅₀

8.3

Acute toxicity inhalation (LC₅₀

8.3

vapours mg/l)

Notes (inhalation LC₅₀)

Based on available data the classification criteria are not met.

## Skin corrosion/irritation

8/15

>>> page_8


Revision date: 29/07/2020

Revision: 5

Supersedes date: 28/07/2020

## HYDROCHLORIC ACID 1.18 S.G. LRG

Animal data

Skin Corr. 1B - H314 Causes severe burns.

Extreme pH

≤ 2 Corrosive.

Serious eye damage/irritation

Serious eye damage/irritation

Eye Dam. 1 - H318 Corrosive to skin. Corrosivity to eyes is assumed.

Respiratory sensitisation

Respiratory sensitisation

Based on available data the classification criteria are not met.

Skin sensitisation

Skin sensitisation

Based on available data the classification criteria are not met.

Germ cell mutagenicity

Genotoxicity - in vitro

Based on available data the classification criteria are not met.

Genotoxicity - in vivo

Scientifically unjustified.

Carcinogenicity

Carcinogenicity

Based on available data the classification criteria are not met. NOAEL <10 ppm, Inhalation,

Rat

IARC carcinogenicity

None of the ingredients are listed or exempt.

Reproductive toxicity

Reproductive toxicity - fertility

Based on available data the classification criteria are not met.

Reproductive toxicity -

Based on available data the classification criteria are not met.

Reproductive toxicity -

development

Specific target organ toxicity - single exposure

STOT - single exposure

STOT SE 3 - H335 May cause respiratory irritation.

Target organs

Respiratory system, lungs

Specific target organ toxicity - repeated exposure

STOT - repeated exposure

Not classified as a specific target organ toxicant after repeated exposure. NOAEL 20 ppm,

Inhalation, Rat 13 weeks

Target organs

Respiratory system, lungs

Aspiration hazard

Aspiration hazard

Based on available data the classification criteria are not met.

General information

The severity of the symptoms described will vary dependent on the concentration and the

length of exposure.

Inhalation

Corrosive to the respiratory tract. Symptoms following overexposure may include the

following: Severe irritation of nose and throat.

Ingestion

May cause chemical burns in mouth, oesophagus and stomach. Symptoms following

overexposure may include the following: Severe stomach pain. Nausea, vomiting.

Skin contact

Causes severe burns. Symptoms following overexposure may include the following: Pain or

irritation. Redness. Blistering may occur.

Eye contact

Causes serious eye damage. Symptoms following overexposure may include the following:

Pain. Profuse watering of the eyes. Redness.

Route of exposure

Ingestion Inhalation Skin and/or eye contact

9/15

>>> page_9


Revision date: 29/07/2020

Revision: 5

Supersedes date: 28/07/2020

## HYDROCHLORIC ACID 1.18 S.G. LRG

Target organs

Respiratory system, lungs

Toxicological information on ingredients.

## HYDROCHLORIC ACID ...%

Toxicological effects

The toxicity of this substance has been assessed during REACH registration.

Acute toxicity - oral

Notes (oral LD₅₀)

Scientifically unjustified. REACH dossier information.

Acute toxicity - dermal

Notes (dermal LD₅₀)

Scientifically unjustified. REACH dossier information.

Acute toxicity - inhalation

Acute toxicity inhalation

(LC₅₀ dust/mist mg/l)

8.3

Species

Rat

Notes (inhalation LC₅₀)

REACH dossier information. LC50 8.3 mg/l, 30 minutes, Dust/Mist Rat

Skin corrosion/irritation

Animal data

Corrosive to skin. REACH dossier information.

Serious eye damage/irritation

Serious eye

Causes serious eye damage. REACH dossier information.

damage/irritation

Respiratory sensitisation

Respiratory sensitisation

Scientifically unjustified.

Skin sensitisation

Skin sensitisation

Not sensitising. REACH dossier information.

Germ cell mutagenicity

Genotoxicity - in vitro

Negative. REACH dossier information.

Genotoxicity - in vivo

No specific test data are available. REACH dossier information.

Carcinogenicity

Carcinogenicity

NOAEL <10 ppm, Inhalation, Rat Based on available data the classification criteria

are not met.

Reproductive toxicity

Reproductive toxicity -

Scientifically unjustified. REACH dossier information.

fertility

Reproductive toxicity -

This substance has no evidence of toxicity to reproduction.

Reproductive toxicity -

development

Specific target organ toxicity - single exposure

STOT - single exposure

No specific test data are available.

Specific target organ toxicity - repeated exposure

STOT - repeated exposure NOAEL 20 ppm, Inhalation, Rat 13 weeks

Aspiration hazard

10/15

>>> page_10


Revision date: 29/07/2020

Revision: 5

Supersedes date: 28/07/2020

## HYDROCHLORIC ACID 1.18 S.G. LRG

Aspiration hazard

Not anticipated to present an aspiration hazard, based on chemical structure.

Inhalation

Irritating to respiratory system. Burns can occur.

Ingestion

Corrosive. Small amounts may cause serious damage.

Skin contact

Causes burns.

Eye contact

This product is strongly corrosive. Causes serious eye damage.

## SECTION 12: Ecological information

Ecotoxicity

The product may affect the acidity (pH) of water which may have hazardous effects on aquatic

organisms.

## Ecological information on ingredients.

## HYDROCHLORIC ACID ...%

Ecotoxicity

The product may affect the acidity (pH) of water which may have hazardous effects

on aquatic organisms.

## 12.1. Toxicity

Toxicity

Based on available data the classification criteria are not met.

## Ecological information on ingredients.

## HYDROCHLORIC ACID ...%

Acute aquatic toxicity

Acute toxicity - fish

LC₅₀, 96 hours: pH 3.5 - 3.25 , Lepomis macrochirus (Bluegill)

Acute toxicity - aquatic

invertebrates

Acute toxicity - aquatic

Acute toxicity - aquatic

plants

EC₅₀, 72 hours: pH 4.7 , Freshwater algae

Acute toxicity -

microorganisms

EC₅₀, 3 hours: pH 5 - 5.5 , Activated sludge

Acute toxicity - terrestrial

Not available.

Chronic aquatic toxicity

Chronic toxicity - fish early

Not determined.

life stage

Short term toxicity -

Not determined.

embryo and sac fry stages

Chronic toxicity - aquatic

Scientifically unjustified.

invertebrates

## 12.2. Persistence and degradability

Persistence and degradability

The product contains inorganic substances which are not biodegradable.

Phototransformation

Not relevant.

Stability (hydrolysis)

Not relevant.

11/15

>>> page_11


Revision date: 29/07/2020

Revision: 5

Supersedes date: 28/07/2020

## HYDROCHLORIC ACID 1.18 S.G. LRG

Biodegradation

Scientifically unjustified.

Biological oxygen demand

Not relevant.

Chemical oxygen demand

Not relevant.

Ecological information on ingredients.

## HYDROCHLORIC ACID ...%

Persistence and

degradability

The product is expected to be biodegradable.

Phototransformation

Substance is inorganic.

Stability (hydrolysis)

Not relevant.

Biodegradation

Scientifically unjustified.

Biological oxygen demand

Not relevant.

Chemical oxygen demand

Not relevant.

12.3. Bioaccumulative potential

Bioaccumulative potential

Bioaccumulation is unlikely.

Partition coefficient

Not applicable. REACH dossier information.

Ecological information on ingredients.

## HYDROCHLORIC ACID ...%

Bioaccumulative potential

The product is not bioaccumulating.

Partition coefficient

Scientifically unjustified.

12.4. Mobility in soil

Mobility

The product is water-soluble and may spread in water systems. Volatile liquid.

Adsorption/desorption

coefficient

Scientifically unjustified.

Henry's law constant

Not determined.

Surface tension

Not relevant. REACH dossier information.

Ecological information on ingredients.

## HYDROCHLORIC ACID ...%

Mobility

The product is miscible with water and may spread in water systems.

Adsorption/desorption

coefficient

Scientifically unjustified.

Henry's law constant

Not determined.

Surface tension

Scientifically unjustified.

12.5. Results of PBT and vPvB assessment

Results of PBT and vPvB

This product does not contain any substances classified as PBT or vPvB.

assessment

12/15

>>> page_12


Revision date: 29/07/2020

Revision: 5

Supersedes date: 28/07/2020

## HYDROCHLORIC ACID 1.18 S.G. LRG

## Ecological information on ingredients.

## HYDROCHLORIC ACID ...%

Results of PBT and vPvB

assessment

This substance is not classified as PBT or vPvB according to current EU criteria.

assessment

12.6. Other adverse effects

Other adverse effects

None known.

Ecological information on ingredients.

HYDROCHLORIC ACID ...%

Other adverse effects

Not determined.

## SECTION 13: Disposal considerations

## 13.1. Waste treatment methods

General information

The generation of waste should be minimised or avoided wherever possible. Reuse or recycle

products wherever possible. This material and its container must be disposed of in a safe

way. Disposal of this product, process solutions, residues and by-products should at all times

comply with the requirements of environmental protection and waste disposal legislation and

any local authority requirements. When handling waste, the safety precautions applying to

handling of the product should be considered. Care should be taken when handling emptied

containers that have not been thoroughly cleaned or rinsed out. Empty containers or liners

may retain some product residues and hence be potentially hazardous.

Disposal methods

Do not empty into drains. Dispose of surplus products and those that cannot be recycled via a

licensed waste disposal contractor. Waste, residues, empty containers, discarded work

clothes and contaminated cleaning materials should be collected in designated containers,

labelled with their contents. Incineration or landfill should only be considered when recycling is

not feasible.

## SECTION 14: Transport information

General

For limited quantity packaging/limited load information, consult the relevant modal

documentation using the data shown in this section.

14.1. UN number

UN No. (ADR/RID)

1789

UN No. (IMDG)

1789

UN No. (ICAO)

1789

14.2. UN proper shipping name

Proper shipping name

HYDROCHLORIC ACID

(ADR/RID)

Proper shipping name (IMDG) HYDROCHLORIC ACID

Proper shipping name (ICAO)

HYDROCHLORIC ACID

Proper shipping name (ADN)

HYDROCHLORIC ACID

14.3. Transport hazard class(es)

ADR/RID class

8

13/15

>>> page_13


Revision date: 29/07/2020

Revision: 5

Supersedes date: 28/07/2020

## HYDROCHLORIC ACID 1.18 S.G. LRG

IMDG class

8

ICAO class/division

8

## Transport labels


## 14.4. Packing group

ADR/RID packing group

II

IMDG packing group

II

ICAO packing group

II

## 14.5. Environmental hazards

Environmentally hazardous substance/marine pollutant

No.

## 14.6. Special precautions for user

Always transport in closed containers that are upright and secure. Ensure that persons transporting the product know what to

do in the event of an accident or spillage.

EmS

F-A, S-B

Emergency Action Code

2R

Hazard Identification Number

80

(ADR/RID)

(ADR/RID)

Tunnel restriction code

(E)

## 14.7. Transport in bulk according to Annex II of MARPOL and the IBC Code

Transport in bulk according to

Not applicable.

Annex II of MARPOL 73/78

and the IBC Code

and the IBC Code

## SECTION 15: Regulatory information

## 15.1. Safety, health and environmental regulations/legislation specific for the substance or mixture

National regulations

Control of Substances Hazardous to Health Regulations 2002 (as amended).

EU legislation

Regulation (EC) No 1907/2006 of the European Parliament and of the Council of 18

December 2006 concerning the Registration, Evaluation, Authorisation and Restriction of

Chemicals (REACH) (as amended).

Commission Regulation (EU) No 2015/830 of 28 May 2015.

Regulation (EC) No 1272/2008 of the European Parliament and of the Council of 16

December 2008 on classification, labelling and packaging of substances and mixtures (as

amended).

Guidance

Workplace Exposure Limits EH40.

Industry - Dermal; Long term systemic effects 22 mg/kg/day

ECHA Guidance on the compilation of safety data sheets 2014.

## 15.2. Chemical safety assessment

No chemical safety assessment has been carried out.

## Inventories

14/15

>>> page_14


Revision date: 29/07/2020

Revision: 5

Supersedes date: 28/07/2020

## HYDROCHLORIC ACID 1.18 S.G. LRG

## EU - EINECS/ELINCS

None of the ingredients are listed or exempt.

## SECTION 16: Other information

Abbreviations and acronyms

used in the safety data sheet

ADR:  European Agreement concerning the International Carriage of Dangerous Goods by

Road.

ADN:  European Agreement concerning the International Carriage of Dangerous Goods by

ADN:  European Agreement concerning the International Carriage of Dangerous Goods by

Inland Waterways.

Inland Waterways.

RID:  European Agreement concerning the International Carriage of Dangerous Goods by

RID:  European Agreement concerning the International Carriage of Dangerous Goods by

Rail.

Rail.

IATA:  International Air Transport Association.

ICAO:  Technical Instructions for the Safe Transport of Dangerous Goods by Air.

IMDG:  International Maritime Dangerous Goods.

CAS:  Chemical Abstracts Service.

ATE:  Acute Toxicity Estimate.

LC₅₀:  Lethal Concentration to 50 % of a test population.

LD₅₀:  Lethal Dose to 50% of a test population (Median Lethal Dose).

LD₅₀:  Lethal Dose to 50% of a test population (Median Lethal Dose).

EC₅₀:  50% of maximal Effective Concentration.

PBT:  Persistent, Bioaccumulative and Toxic substance.

vPvB:  Very Persistent and Very Bioaccumulative.

Classification abbreviations

Classification abbreviations

and acronyms

Met. Corr. = Corrosive to metals

Eye Dam. = Serious eye damage

Skin Corr. = Skin corrosion

STOT SE = Specific target organ toxicity-single exposure

General information

This datasheet is not intended to be a replacement for a full risk assessment, these should

always be carried out by competent persons. Toxicological and ecotoxicological information

has been taken from the ECHA website of registered substances.

Key literature references and

sources for data

Source: European Chemicals Agency, http://echa.europa.eu/

Classification procedures

according to Regulation (EC)

according to Regulation (EC)

1272/2008

Eye Dam. 1 - H318: Skin Corr. 1B - H314: STOT SE 3 - H335: : Calculation method. Met.

Corr. 1 - H290: : Expert judgement.

Training advice

Only trained personnel should use this material.

Revision comments

Change to section 15

Revision date

29/07/2020

Revision

5

Supersedes date

28/07/2020

SDS number

11757

Risk phrases in full

R34 Causes burns.

R37 Irritating to respiratory system.

Hazard statements in full

H290 May be corrosive to metals.

H314 Causes severe skin burns and eye damage.

H318 Causes serious eye damage.

H335 May cause respiratory irritation.

This information relates only to the specific material designated and may not be valid for such material used in combination

with any other materials or in any process.  Such information is, to the best of the company's knowledge and belief, accurate

and reliable as of the date indicated. However, no warranty, guarantee or representation is made to its accuracy, reliability or

completeness. It is the user's responsibility to satisfy himself as to the suitability of such information for his own particular use.

15/15

"""
        },
        {
            "document_id": "MOCK_MSDS_004",
            "file_name": "output(5).pdf",
            "content": """>>> page_0


3M™ Double Coated Tape GPT-020F, GPT-020


## 물질안전보건자료(MSDS)

저작권,2024, 3M Company. 판권 소유. 본 물질안전보건자료(MSDS)는 3M 제품의 적절한 사용을 위한 목적으로

다음과 같은 제한을 두고 복사 및/혹은 다운로드가 허용됨. (1) 본 물질안전보건자료 내 각종 정보는 3M의

사전 서면 동의가 없이는 변경없이 원본 그대로 배포되어야 함. (2) 복사본 또는 원본이 재판매되거나 재산

상 이득을 얻기 위한 목적으로 배포되서는 안됨.

이 물질안전보건자료(MSDS)는 고객의 요청에 대한 응답으로 제공되었음. 이 제품은 사용 권장 사항을 잘 준

수하거나 비 정상적인 상태/조건 하에서 사용되지 않을 경우 잠재적인 건강영향이나 안전 위험요소가 나타나

지 않으므로 산업안전보건법에 따라 본 제품에 대한 각종 규제사항을 필요로 하지 않음. 하지만 제품의 사용

권장 사항을 따르지 않거나 비 정상적인 상태에서 사용/운용했을 시, 제품의 성능에 영향을 미칠 수 있으며

잠재적인 건강영향이나 안전 위험요소가 나타날 수 있음.

문서 그룹

42-7575-6

버전 번호

1.00

발행일:

2024/11/12

대체일:

초 발행

본 물질안전보건자료(MSDS)는 산업안전보건법에 따라 작성되었음.

## 1. 화학제품과 회사에 관한 정보

## 1.1. 제품명

3M™ Double Coated Tape GPT-020F, GPT-020

1.2. 제품의 권고 용도와 사용상의 제한

## 권장 사용

산업용

## 1.3. 공급자 정보

회사명:

한국쓰리엠

주소:

서울특별시 영등포구 의사당대로 82, 19층 (우)07321

전화:

82-2-3771-4114

웹사이트

www.3m.com/kr

긴급전화번호:

82-80-033-4114

## 2. 유해성 ∙ 위험성

## 2.1. 유해. 위험성 분류

이 제품은 완제품이고 GHS 분류에서 예외이다.

## 2.2. 예방조치문구를 포함한 경고 표지 항목

## 신호어

신호어

해당없음.

신호어

해당없음.

심볼(문자)

페이지: 1 의  11

>>> page_1


3M™ Double Coated Tape GPT-020F, GPT-020

해당 없음.

## 그림문자

해당 없음.

유해▪위험문구

예방조치 문구

2.3. 유해성 ∙ 위험성 분류기준에 포함되지 않는 기타 유해성 ∙ 위험성

알려지지 않음.

## 3. 구성성분의 명칭 및 함유량

이 제품의 물질은 혼합물로 구성

물질안전보건자료에 기재된 구성성분 외에 다른 구성성분은 산업안전보건법 상 유해인자 분류기준에 해당되

지 않음

## 4. 응급조치 요령

## 4.1. 응급조치 요령에 대한 설명

## 눈에 들어갔을 때 :

응급조치 불필요. 만약 증상이 지속된다면, 치료를 받을 것.

## 피부에 접촉했을 때 :

응급조치 불필요.

## 흡입했을 때 :

응급조치가 필수적이지 않음. 증상이 지속되면 신선한 공기를 쏘일 것. 진료를 받으시오.

## 먹었을 때 :

입을 씻어낼 것. 불편하다고 느끼면, 치료를 받을 것.

## 4.2. 가장 중요한 증상과 영향, 급성 과 지연성

심각한 증상이나 영향은 없습니다.섹션 11.1, 독성 영향에 대한 정보를 참조한다.

## 4.3. 즉각적인 의료 행위 및 특별한 치료가 필요한 경우에 대한 지시사항

## 해당없음.

## 5. 폭발 ∙ 화재시 대처방법

## 5.1. 적절한 (및 부적절한) 소화제

화재시 : 물 또는 거품과 같은 일반적인 가연성 물질에 적합한 소화제를 사용하여 소화하십시오.

## 5.2. 화학물질 혹은 혼합물로부터 생기는 특정 유해성 (예, 연소시 발생 유해물질)

이 제품에 내재하지 않음.

페이지: 2 의  11

>>> page_2


3M™ Double Coated Tape GPT-020F, GPT-020

## 5.3. 화재 진압 시 착용할 보호구 및 예방조치

헬멧, 압력 호흡기, 벙커 코트 및 바지, 팔, 허리 및 다리 주변의 밴드, 얼굴 마스크 및 노출된 부위의 보호

덮개를 포함한 완전한 보호의를 착용하십시오.

## 6. 누출 사고 시 대처방법

## 6.1. 인체를 보호하기 위해 필요한 조치 사항 및 보호구

## 해당없음.

해당없음.

## 6.2. 환경을 보호하기 위해 필요한 조치사항

해당없음.

## 6.3. 정화 또는 제거 방법

해당없음.

## 7. 취급 및 저장방법

## 7.1. 안전취급요령

7.1. 안전취급요령

이 제품은 정상 사용시 유해화학물질을 방출하지 않거나 노출이 발생되지 않는 품목으로 고려됨.

## 7.2. 안전한 저장 방법 (피해야 할 조건을 포함함)

해당없음.

## 8. 노출방지 및 개인보호구

## 8.1. 화학물질의 노출기준, 생물학적 노출기준 등

## 작업노출한계

작업노출한계치는 본 물질안전보건자료(MSDS)의 섹션 3에 있는 어떠한 구성성분에 대해서도 없음

## 8.2. 적절한 공학적 관리

공학적인 관리가 필요하지 않음

## 8.3 개인보호구(PPE)

## 눈/얼굴 보호 :

눈 보호구는 불필요.

## 손 보호

화학물질 보호 장갑 불필요

## 

## 신체 보호

해당없음

## 호흡기보호:

호흡기 보호구는 불필요.

페이지: 3 의  11

>>> page_3


3M™ Double Coated Tape GPT-020F, GPT-020

## 9. 물리화학적 특성

## 9.1. 기본적인 물리화학적 특성에 대한 정보

외관(물리적상태)

고체

특정 물리적 형태:

Roll of Tape

색

무색

냄새

Acrylic

냄새 역치

자료 없음.

pH

해당없음.

녹는 점/어는 점

자료 없음.

끓는 점/ 초기 끓는 점/끓는 범위

해당없음.

인화점:

인화점 없음

증발 속도

해당없음.

가연성

해당없음.

인화 또는 폭발 범위(하한)

자료 없음.

인화 또는 폭발 범위(상한)

자료 없음.

증기압

자료 없음.

상대증기밀도

자료 없음.

비중(밀도)

>=1.3 g/cm3

상대 밀도

자료 없음.

용해도:

자료 없음.

용해도-non-water

자료 없음.

n-옥탄올/물 분배계수

자료 없음.

자연발화 온도

자료 없음.

분해 온도

자료 없음.

동적 점성도

자료 없음.

휘발성 유기물

자료 없음.

퍼센트 휘발성

자료 없음.

VOC Less H2O & Exempt Solvents

자료 없음.

분자량

자료 없음.

입자 특성

해당없음.

## 10. 안정성 및 반응성

## 10.1 반응성

이 물질은 정상 사용 조건하에 반응성이 없다고 여겨짐.

## 10.2 화학적 안정성

안정함

## 10.3 유해 반응의 가능성

10.3 유해 반응의 가능성

위험 폴리머화는 발생하지 않음

페이지: 4 의  11

>>> page_4


3M™ Double Coated Tape GPT-020F, GPT-020

## 10.4 피해야 할 조건

알려지지 않음

## 10.5 피해야 할 물질

알려지지 않음

## 10.6 분해 시 생성되는 유해물질

물질

조건

알려지지 않음

권고된 사용 조건하에서, 유해한 분해 반응물들이 발생하지 않음. 유해한 분해 반응물들은 산화, 가열 또는

다른 물질과의 반응 결과로서 발생될 수 있음.

## 11. 독성에 관한 정보

특정 구성성분의 분류가 적절한 근거에 의해 규정될 때, 아래의 정보는 섹션 2 (유해성 위험성)의 GHS 분류

와 일치하지 않을 수 있음. 또한, 구성성분의 독성 정보가 GHS 분류를 위한 역가치 이하의 함량이거나, 구성

성분으로 인한 노출이 가능하지 않을 때, 또는 구성성분 하나 단일물질의 독성 데이터는 제품 전체의 독성정

보가 아니므로 섹션 2 (유해성 위험성) 항목의 정보와/또는 신호어 및 노출 증상 등의 구분에 반영되지 않을

수 있음.

## 11.1 노출 가능 경로 및 독성 영향에 대한 정보

## 노출증상

테스트 데이터나 구성성분에 대한 정보에 기초해서 이 물질은 다음의 건강 영향을 발생시킴

## 흡입했을 때 :

흡입으로 인한 인체에 미치는 악영향은 없는 것으로 예상됨.

## 피부에 접촉했을 때 :

피부접촉으로 인한 인체에 미치는 악영향은 없을 것으로 예상됨.

## 눈에 들어갔을 때 :

눈 접촉으로 인한 인체에 미치는 악영향은 없을 것으로 예상됨.

## 섭취:

물리적 장애: 경련, 복통, 그리고 변비의 증상이 생길 수 있음.

## 추가 정보:

이 제품을 사용법에 따라 사용하면 인체에 유해하지 않습니다. 그러나 사용법에 맞지 않는 방식으로 제품을

사용하거나 운용하면 제품의 성능에 영향을 미칠 수 있으며 잠재적인 건강과 안전에 위험을 초래할 수 있습

니다.

## 독성 데이터

3장의 구성성분의 명칭 및 함유량에는 기재되어 있지만 아래 표에 기재되어 있지 않으면, 데이터가 없거나

분류를 위한 충분한 데이터가 없는 것임.

## 급성 독성

급성 독성

이름

루트

종

값

페이지: 5 의  11

>>> page_5


3M™ Double Coated Tape GPT-020F, GPT-020

제품 전체

섭취

자료 없음; ATE 계산>5,000 mg/kg

## ATE=급성독성예상치

## 피부 부식성 또는 자극성

피부 부식성 또는 자극성

이름

종

값

제품 전체

자료없음

자료가 없거나 분류를 위해서 충분치 않음

## 심한 눈 손상 또는 자극성

심한 눈 손상 또는 자극성

이름

종

값

제품 전체

자료없음

자료가 없거나 분류를 위해서 충분치 않음

## 피부 과민성

피부 과민성

이름

종

값

제품 전체

자료없음

자료가 없거나 분류를 위해서 충분치 않음

## 광민감성

광민감성

이름

종

값

제품 전체

자료없음

자료가 없거나 분류를 위해서 충분치 않음

## 호흡기 과민성

호흡기 과민성

이름

종

값

제품 전체

자료없음

자료가 없거나 분류를 위해서 충분치 않음

## 생식세포 변이원성

생식세포 변이원성

이름

루트

값

제품 전체

자료없음

자료가 없거나 분류를 위해서 충분치 않음

## 발암성

발암성

이름

루트

종

값

제품 전체

자료없음

자료없

자료가 없거나 분류를 위해서 충분치 않음

음

## 생식독성

## 생식, 발생 효과

생식, 발생 효과

이름

루트

값

종

시험결과

노출 정도

제품 전체

자료없음

자료가 없거나 분류를 위해서 충분

자료없음

자료없음

자료없음

치 않음

## 수유

수유

이름

루트

종

값

제품 전체

자료없음

자료없

자료가 없거나 분류를 위해서 충분치 않음

음

## 표적장기효과

## 특정 표적장기 독성-1회 노출

페이지: 6 의  11

페이지: 6 의  11

>>> page_6


3M™ Double Coated Tape GPT-020F, GPT-020

이름

루트

표적장기효과

값

종

시험결과

노출 정도

제품 전체

자료없음

자료없음

자료가 없거나 분류를 위해서

자료없

자료없음

0

충분치 않음

음

## 특정 표적장기독성-반복노출

특정 표적장기독성-반복노출

이름

루트

표적장기효과

값

종

시험결과

노출 정도

제품 전체

자료없음

자료없음

자료가 없거나 분류를 위해서

자료없

자료없음

0

충분치 않음

음

## 흡인 유해성

흡인 유해성

이름

값

제품 전체

자료가 없거나 분류를 위해서 충분치 않음

추가 독성정보가 필요하면 본 물질안전보건자료(MSDS) 첫페이지에 있는 주소나 전화번호로 연락하시오

## 12. 환경에 미치는 영향

특정 구성성분의 분류가 적절한 근거에 의해 규정될 때, 아래의 정보는 섹션 2 (유해성 위험성)의 GHS 분류

와 일치하지 않을 수 있음. 요청에 따라 섹션 2 (유해성 위험성)에서의 물질의 분류와 관련된 추가적인 정보

는 제공 가능함. 또한, 구성성분의 환경에 미치는 영향은 GHS 분류를 위한 역가치 이하의 함량이거나, 구성

성분으로 인한 노출이 가능하지 않을 때, 또는 구성성분 하나 단일물질의 독성 데이터는 제품 전체의 독성정

보가 아니므로 섹션 2 (유해성 위험성) 항목의 정보와/또는 신호어 및 노출 증상 등의 구분에 반영되지 않을

수 있음.

## 12.1 생태독성

## 급성 수생 위험성:

수생생물에 급성 독성이 없음(GHS 분류 기준)

## 만성 수생 위험성:

GHS 분류에 의해 수생생물에 만성독성없음

재료

유기체

타입

노출

테스트 종점

시험결과

제품 전체

자료없음

자료가 없거나

자료없음

자료없음

자료없음

분류를 위해서

충분치 않음

## 12.2. 잔류성 및 분해성

재료

CAS No.

테스트 타입

지속기간

연구 방식

시험결과

방법

제품 전체

None

자료가 없거

자료없음

자료없음

자료없음

자료없음

나 분류를 위

해서 충분치

않음

## 12.3. 생물 농축성(농축가능성)

페이지: 7 의  11

>>> page_7


3M™ Double Coated Tape GPT-020F, GPT-020

재료

CAS No.

테스트 타입

지속기간

연구 방식

시험결과

방법

제품 전체

None

자료가 없거

자료없음

자료없음

자료없음

자료없음

나 분류를 위

해서 충분치

않음

## 12.4. 토양 이동성

자료없음. 상세한 사항은 제조사에 문의하시오.

## 12.5. 기타 유해 영향

재료

CAS No.

오존층 파괴 가능성

지구 온난화 가능성

제품 전체

없음

자료가 없거나 분류를

자료가 없거나 분류를 위해서

위해서 충분치 않음

충분치 않음

## 13. 폐기시 주의사항

## 13.1. 폐기 방법

폐기물 관련 법령에 따라 내용물/용기를 폐기하시오

## 13. 2. 폐기시 주의사항

폐기 전에 적절한 분류를 확인하기 위해 모든 관련 기관과 규정을 참조할 것. 허가된 산업폐기시설에 폐기물

을 폐기할 것. 폐기 대체로써, 허가된 폐기물 소각장에서 소각함. 만약 다른 폐기 방법이 없다면, 폐기물을

산업 폐기물을 위해 고안된 곳에서 처리함.

## 14. 운송에 필요한 정보

## 14. 1 국제규제

UN 번호:

해당 없음.

UN 적정선적명:

해당 없음.

운송에서의 위험성 등급 (IMO):

해당 없음.

운송에서의 위험성 등급 (IATA):

해당 없음.

운송에서의 위험성 등급 (IATA):

용기(포장) 등급:

해당 없음.

해양오염물질:

해당 없음.

사용자가  운송 또는 운송 수단에 관련해 알 필요가 있거나 필요한 특별한 안전 대책:

해당 없음.

## 15. 법적 규제현황

15.1. 안전, 건강, 환경 규제/ 물질 또는 혼합물 특이적인 등록

## 글로벌 인벤토리 상태

이 제품은 TSCA 규정에 의해 정의 된 완제품이며, TSCA 인벤토리 상장 요건에서 제외됩니다.  자세한 사항은

한국쓰리엠에 문의하시오.

자세한 사항은 한국쓰리엠에 문의하시오.

페이지: 8 의  11

>>> page_8


3M™ Double Coated Tape GPT-020F, GPT-020

## 이 제품의 구성 성분들은 다음과 같은 법적 규제사항을 따르고 있음.

## 산업안전보건법에 의한 규제

금지물질:해당없음.

관리대상유해물질:해당없음.

허가물질:해당없음.

특별관리물질:해당없음.

작업환경측정대상물질:해당없음.

특수건강진단대상물질:해당없음.

노출기준설정물질:해당없음.

허용기준설정물질:해당없음.

공정안전보고서(PSM) 제출 대상물질:해당없음.

## 화학물질관리법에 의한 규제

유독물질:해당없음.

유독물질:해당없음.

허가물질:해당없음.

허가물질:해당없음.

제한물질:해당없음.

제한물질:해당없음.

금지물질:해당없음.

금지물질:해당없음.

사고대비물질:해당없음.

## 위험물안전관리법에 의한 규제

위험물로 분류되지 않음

## 폐기물관리법에 의한 규제

사업장 일반폐기물

## 기타 국내 및 외국법에 의한 규제

해당없음.

## 16. 그 밖의 참고사항

## 16.1. 자료의 출처

- 3M test data

- ACGIH(American Conference of Governmental Industrial Hygienists)

- AIHA (American Industrial Hygiene Association)

- ASTDR (Agency for Toxic Substances and Disease Registry)

- CCOHS (Canadian Centre for Occupational Health and Safety)

- ChemIDplus (Chemical Identification/Dictionary)

- CICADs (Concise International Chemical Assessment Documents)

- CRC Handbook

- DOT (Department of Transportation classifications)

- e-Chem Portal

- ECOSAR (Ecological Structure Activity Relationships)

- EHC (Environmental Health Criteria) Monographs

- EPA (Environmental Protection Agency)

- ERG (emergency response guidebook)

페이지: 9 의  11

>>> page_9


3M™ Double Coated Tape GPT-020F, GPT-020

- ESIS (European chemical Substances Information System)

- EU Proposals for Classification

- EU RAR (Risk Assessment Report)

- HSDB (Hazardous Substances Data Bank)

- Summaries and Evaluations

- ICSCs (International Chemical Safety Cards)

- IPCS INCHEM (International Programme on Chemical Safety)

- IRIS (Integrated Risk Information System)

- IUCLID (International Uniform Chemical Information Database)

- Monographs and Evaluations

- 안전보건공단(KOSHA)

- 국립환경과학원 화학물질정보시스템(NCIS)

- NIOSH (National Institute of Occupational Safety and Health) Pocket guide

- NITE (National Institute of Technology and Evaluation)

- NLM (National Library of Medicine)

- NTP (National Toxicity Program)

- Patty’s Toxicology

- PDs (Pesticide Documents)

- PDs (Pesticide Documents)

- PIMs, 1989-2002 (Poisons Information Monographs Archive)

- Pubchem

- QSAR (Quantitative(Qualitative) Structure Activity Relationship)

- REACH (ECHA Registered Substance)

- SIDS (Screening Information Data Set) for High Production Volume Chemicals

- 공급자 test data 및 분류

- TERA (Toxicology Excellence for Risk Assessment)

- Toxic Substances Control Act Test Submissions

- UN RTDG (Recommendations on the Transport of Dangerous Goods)

## 16.2. 최초 작성일자:

## 2024.11.12

## 16.3. 개정 횟수 및 최종 개정일자:

개정 횟수:자료 없음.

최종 개정일자:2024/11/12

16.4. 기타:

해당없음.

면책조항: 본 물질안전보건자료(MSDS)상에 있는 정보는 당사의 경험을 기반으로 작성되었고, 발행일 기준으

로 당사가 아는 한 정확하지만 당사는 본 물질안전보건자료의 사용에 따른 어떠한 손실, 피해 혹은 상해 등

에 대해 어떤 법적 책임(국내법률에서 요구하는 경우를 제외한)을 지지 않습니다. 이 정보들은 본 물질안전

보건자료에 언급되지 않은 용도로의 사용 또는 다른 제품들과 함께 사용하는 경우에 유효하지 않을 수 있습

니다. 이러한 이유들로 고객들 자신이 의도한 용도에 대한 제품의 적합성에 대해 고객들 스스로가 평가하는

것이 중요합니다. 또한 본 물질안전보건자료는 건강 및 안전 정보를 전달하기 위해 제공됩니다. 만일 귀하가

이 제품의 직접 수입자인 경우, 귀하는 제품 허가/신고, 물질 수량 추적 및 물질의 허가/신고 등을 포함하여

수입자로서 해당 국가의 모든 관련 법규의 요구사항들에 대한 책임이 있습니다.

한국쓰리엠의 물질안전보건자료(MSDS)는  www.3m.com/kr 에서 확인 가능함.

페이지: 10 의  11

>>> page_10


3M™ Double Coated Tape GPT-020F, GPT-020

페이지: 11 의  11

"""
        },
        {
            "document_id": "MOCK_MSDS_005",
            "file_name": "output3.pdf",
            "content": """>>> page 1

수소 개정번호   : 제품안전취급서 (MATERIAL SAFETY DATA SHEET)
<img src="images/page_1_img_1.png" alt="image" width="154" height="32" />
<img src="images/page_1_img_2.png" alt="image" width="154" height="7" />


| 제품안전취급서 (MATERIAL SAFETY DATA SHEET) |
| --- |
| 1. 화학제품과 회사에 관한 정보 |
| 가. 제품명 수소 나. 제품의 권고 용도와 사용상의 제한 O 권고용도 산업용 O 사용상의 제한 자료없음 다. 제조자/공급자/유통업자 정보 O 공급회사명 프렉스에어코리아(주) O 주소 본사 : 서울특별시 강남구 대치동 943-19 테헤란로 신안빌 딩 16층 기흥 : 경기도 화성시 동탄면 영천리 506-1 창원 : 경남 창원시 성산구 내동 452-6번지 여수 : 전남 여수시 월래동 1407 탕정 : 충남 아산시 탕정면 명암리 산 4-2 화성 : 경기도 용인시 기흥구 농서동 6-1 O 정보제공 서비스 또는 긴급 연락처 번호 본사 : 02-2188-2200 기흥 : 031-370-8100 창원 : 055- 268-2800 여수 : 061-807-6400 탕정 : 041-537-7300 화성 : 031-260-3000 O 담당부서 S&ES 그룹 |


# 제품안전취급서 (**MATERIAL SAFETY DATA SHEET**)
1.  화학제품과 회사에 관한 정보
가. 제품명
수소
나. 제품의 권고 용도와 사용상의 제한
O 권고용도
산업용
O 사용상의 제한
자료없음
다. 제조자/공급자/유통업자 정보
O 공급회사명
프렉스에어코리아(주)
O 주소
본사 : 서울특별시 강남구 대치동 943-19 테헤란로 신안빌
딩 16층
기흥 : 경기도 화성시 동탄면 영천리 506-1
창원 : 경남 창원시 성산구 내동 452-6번지
여수 : 전남 여수시 월래동 1407
탕정 : 충남 아산시 탕정면 명암리 산 4-2
화성 : 경기도 용인시 기흥구 농서동 6-1
O 정보제공 서비스 또는 긴급 연락처 번호  본사 : 02-2188-2200
기흥 : 031-370-8100
창원 : 055- 268-2800
여수 : 061-807-6400
탕정 : 041-537-7300
화성 : 031-260-3000
O 담당부서
S&ES 그룹
2. 유해 . 위험성
가. 유해 위험성 분류
인화성가스 구분1
고압가스 압축가스
나. 경고 표지 항목
<img src="images/page_1_img_3.png" alt="image" width="55" height="36" />
<img src="images/page_1_img_5.png" alt="image" width="55" height="36" />
O 그림문자
<img src="images/page_1_img_4.png" alt="image" width="55" height="19" />
<img src="images/page_1_img_6.png" alt="image" width="55" height="19" />
O 신호어
위험
O 유해위험 문구
극인화성가스
고압가스 :가열시 폭발할 수 있음
O 예방조치 문구
- 예방
열:스파크·화염·고열로부터 멀리하시오 - 금연
방폭 공구 및 장비를 사용하시오.
실린더 또는 용기가 물리적 충격을 받지 않도록 취급하시오.
가압, 절단, 연마, 가열 등의 물리적인 충격을 피하시오
실린더 벨브를 열때는 서서히 조작하시오.
사용후에는 벨브를 잠그고, 빈 용기일지라도 벨브를 잠궈서 보
관하시오.
피해야할 물질 및 조건에 유의하시오.
- 대응
누출성 가스 화재 시 누출을 안전하게 막을 수 없다면 불을 끄려
하지 마시오.
안전하게 처리하는 것이 가능하면 모든 점화원을 제거하시오.
즉시 모든 직원은 위험지역에서 대피하시오.
필요지역에서는 SCBA(Self-Contained Breathing
Apparatus)를 착용하시오.
지역을 벗어나 안전거리를 유지하여 소화하시오.
파손된 실린더는 날아오를 수 있으니 주의하시오.
- 저장
직사광선을 피하고 환기가 잘 되는 곳에 보관하시오.
저장소나 사용지역에는 "금연 또는 화기엄금 "경고표지를 부착
하시오.
밀폐용기에 저장하시오.
서늘하고 건조한 장소에 저장하시오.
용기는 열에 노출되었을 경우 압력이 올라갈 수 있으므로 열에
1/6
Business Confidential (Printed : -Uncontrolled  2013-08-30Copy)
Praxair Korea Co., Ltd.

>>> pend


>>> page 2

수소 개정번호   : 제품안전취급서 (MATERIAL SAFETY DATA SHEET)
폭로되지 않도록 하시오..
- 폐기
폐기물관리법에 명시된 경우 규정에 따라 내용물 및 용기를 폐
기하시오.
(관련 법규에 명시된 내용에 따라) 내용물 용기를 폐기하시오.
다. 유해 위험성 분류기준에 포함되지 않는 기타 유해 위험성
O NFPA
- 보건
0
- 화재
4
- 반응성
0


| 3. 구성성분의 명칭 및 조성 |  |  |  |
| --- | --- | --- | --- |
| 화학 물질명 | 관용명 | CAS번호 | 함유량 (%) |
| 수소 | HYDROGEN GAS | 1333-74-0 | >99% |


3. 구성성분의 명칭 및 조성
화학 물질명
관용명
CAS번호
함유량 (%)
수소
HYDROGEN GAS
1333-74-0
>99%


| 4. 응급조치 요령 |
| --- |
| 가. 눈에 들어갔을 때 해당없음(상온상압에서 가스상의 물질임) 나. 피부에 접촉했을 때 해당없음(상온상압에서 가스상의 물질임) 다. 흡입했을 때 신선한 공기가 있는 곳으로 옮기시오. 호흡이 중단된 경우 인공호흡실시 하시오. 호흡이 고르지 못할 경우, 자격을 갖춘 사람에 의한 산소 공급가능이 가능하다. 즉시 의사를 부르시오. 라. 먹었을 때 해당없음(상온상압에서 가스상의 물질임) 마. 급성 및 지연성의 가장 중요한 증상/영향 자료없음 바. 응급처치 및 의사의 주의사항 특정한 치료제는 없으며 과도한 노출에 대한 치료는 환 자의 증상이나 상태에 따라 치료하시오. |


4. 응급조치 요령
가. 눈에 들어갔을 때
해당없음(상온상압에서 가스상의 물질임)
나. 피부에 접촉했을 때
해당없음(상온상압에서 가스상의 물질임)
다. 흡입했을 때
신선한 공기가 있는 곳으로 옮기시오.
호흡이 중단된 경우 인공호흡실시 하시오.
호흡이 고르지 못할 경우, 자격을 갖춘 사람에 의한 산소
공급가능이 가능하다.
즉시 의사를 부르시오.
라. 먹었을 때
해당없음(상온상압에서 가스상의 물질임)
마. 급성 및 지연성의 가장 중요한 증상/영향
자료없음
바. 응급처치 및 의사의 주의사항
특정한 치료제는 없으며 과도한 노출에 대한 치료는 환
자의 증상이나 상태에 따라 치료하시오.
5. 폭발 화재시 대처방법
가. 적절한(및 부적절한) 소화재
O 적절한 소화재
이산화탄소, 분말 소화약제, 물분무
O 부적절한 소화재
자료없음
O 대형 화재시
미세한 분무로 대량 살수 할 것
나. 화학물질로부터 생기는 특정
유해성
O열분해 생성물
자료 없음
O화재 및 폭발위험
극인화성 가스
격렬하게 중합반응하여 화재와 폭발을 일으킬 수 있음
가열시 용기가 폭발할 수 있음
공기와 폭발성 혼합물을 형성함
수소(UN No. 1049)/중수소(UN No. 1957)/압축수소메탄혼합물(UN No.
2034)는 화염이 눈에 보이지 않음
열, 스파크, 화염에 의해 쉽게 점화함
증기는 점화원까지 이동하여 역화(flash back)할 수 있음
화재에 노출된 실린더는 가연성 가스를 방출할 수 있음
다. 화재 진압 시 착용할 보호구 및
특정 유해성
모든 인원은 위험지역에서 대피하시오.
누출성 가스 화재 시 누출을 안전하게 막을 수 없다면 불을 끄려하지 마시오.
안전하게 처리하는 것이 가능하면 모든 점화원을 제거하시오.
지역을 벗어나 안전거리를 유지하여 소화하시오
파손된 실린더는 날아오를 수 있으니 주의하시오
누출이 중지되지 않는다면 누출가스화재를 소화하지 마시오
위험하지 않다면 화재지역에서 용기를 옮기시오
탱크 화재시 결빙될 수 있으므로 노출원 또는 안전장치에 직접주수하지 마시
오
탱크 화재시 최대거리에서 소화하거나 무인 소화장비를 이용하시오
탱크 화재시 소화가 진화된 후에도 다량의 물로 용기를 식히시오
탱크 화재시 압력 방출장치에서 고음이 있거나 탱크가 변색할 경우 즉시 물
러나시오
탱크 화재시 화염에 휩싸인 탱크에서 물러나시오
탱크 화재시 대규모 화재의 경우 무인 소화장비를 이용하고 불가능하다면 물
러나 타게 놔두시오
화재에 노출된 실린더는 가연성 가스를 방출할 수 있음
일부 물질은 고농도로 흡입시 자극적일 수 있음
증기는 자각 없이 현기증 또는 질식을 유발할 수 있음
2/6
Business Confidential (Printed : -Uncontrolled  2013-08-30Copy)
Praxair Korea Co., Ltd.

>>> pend


>>> page 3

수소 개정번호   : 제품안전취급서 (MATERIAL SAFETY DATA SHEET)
화재시 자극성, 부식성, 독성 가스를 발생할 수 있음


| 6. 누출 사고시 대처방법 |
| --- |
| 가. 인체를 보호하기 위해 필요한 조치사 위험! 극인화성 고압가스 항 및 보호구 공기와 폭발성 혼합물을 형성함. 즉시 모든 직원은 위험지역에서 대피하시오. 필요지역에서는 SCBA(Self-Contained Breathing Apparatus)를 착 용하시오. 열, 화염, 스파크 또는 기타 점화원과 접촉을 피하시오. 누출된 물질을 만지거나 접촉하지 마시오. 작업자가 위험없이 조치할 수 있다면 누출을 중지시키시오. 작업자가 위험없이 조치할 수 있다면 해당 지역을 환기를 시키거나, 혹은 환기가 잘 되는 지역으로 실린더를 옮기시오. 살수하여 증기의 발생을 감소시키시오. 관계인 외 접근을 막고 위험 지역을 격리하며 출입을 금지하시오. 출입하기 전, 특히 밀폐된 공간에 출입하기 전에는 적절한 기기를 활 용하여 대기 모니터링을 실시하시오. 나. 환경을 보호하기 위해 필요한 조치사 항 O 대기 증기가 하수구, 환기장치, 밀폐공간을 통해 확산되지 않도록 하시 오. O 토양 자료없음 O 수중 자료없음 다. 정화 또는 제거 방법 O 소량 누출시 자료없음 O 다량 누출시 자료없음 |


6. 누출 사고시 대처방법
가. 인체를 보호하기 위해 필요한 조치사
항 및 보호구
위험! 극인화성 고압가스
공기와 폭발성 혼합물을 형성함.
즉시 모든 직원은 위험지역에서 대피하시오.
필요지역에서는 SCBA(Self-Contained Breathing Apparatus)를 착
용하시오.
열, 화염, 스파크 또는 기타 점화원과 접촉을 피하시오.
누출된 물질을 만지거나 접촉하지 마시오.
작업자가 위험없이 조치할 수 있다면 누출을 중지시키시오.
작업자가 위험없이 조치할 수 있다면 해당 지역을 환기를 시키거나,
혹은 환기가 잘 되는 지역으로 실린더를 옮기시오.
살수하여 증기의 발생을 감소시키시오.
관계인 외 접근을 막고 위험 지역을 격리하며 출입을 금지하시오.
출입하기 전, 특히 밀폐된 공간에 출입하기 전에는 적절한 기기를 활
용하여 대기 모니터링을 실시하시오.
나. 환경을 보호하기 위해 필요한 조치사
항
O 대기
증기가 하수구, 환기장치, 밀폐공간을 통해 확산되지 않도록 하시
오.
O 토양
자료없음
O 수중
자료없음
다. 정화 또는 제거 방법
O 소량 누출시
자료없음
O 다량 누출시
자료없음


| 7. 취급 및 저장방법 |
| --- |
| 가. 안전 취급요령 열·스파크·화염·고열로부터 멀리하시오 - 금연 방폭 공구 및 장비를 사용하시오. 실린더 또는 용기가 물리적 충격을 받지 않도록 취급하시오. 가압, 절단, 연마, 가열 등의 물리적인 충격을 피하시오 실린더 벨브를 열때는 서서히 조작하시오. 사용후에는 벨브를 잠그고, 빈 용기일지라도 벨브를 잠궈서 보관하시오. 빈용기내 잔여물질은 위험하므로 안전작업수칙에 따라 용기를 처리하시오. 실린더 손상에 주의 하시오.적절한 이동도구를 사용하고 끌거나,밀거나,굴리거나, 떨어뜨리지 마시오. 절대로 실린더 뚜껑을 잡고 들지 마시오;실린더 뚜껑은 단지 실린더 밸브를 보호 하기 위함이다.절대로 실린더 뚜껑 안에 이 물질(렌치,드라이버 등)을 삽입하지 마 시오; 이것은 밸브의 손상 및 누설을 발생시 킬 수있다.과도하게 잠기거나 녹이슨 뚜껑 을 제거하기 위해서는 적절한 스패너를 사용하시요. 밸브는 천천히 여시오.만약 밸브가 열기가 어렵다면,사용을 중지하고 당신의 공급 처에 연락하시오. 피해야할 물질 및 조건에 유의하시오. 나. 안전한 저장방법 직사광선을 피하고 환기가 잘 되는 곳에 보관하시오. 저장소나 사용지역에는 "금연 또는 화기엄금 "경고표지를 부착하시오. 밀폐용기에 저장하시오. 서늘하고 건조한 장소에 저장하시오. 용기는 열에 노출되었을 경우 압력이 올라갈 수 있으므로 열에 폭로되지 않도록 하시오. 용기의 정전기 발생에 주의하여 저장하시오 저장소는 52℃를 초과하지 않도록 하시오. 용기의 온도를 40℃이하로 유지하시오. 공병과 실병을 구분하여 보관하시오. |


7. 취급 및 저장방법
가. 안전 취급요령
열·스파크·화염·고열로부터 멀리하시오 - 금연
방폭 공구 및 장비를 사용하시오.
실린더 또는 용기가 물리적 충격을 받지 않도록 취급하시오.
가압, 절단, 연마, 가열 등의 물리적인 충격을 피하시오
실린더 벨브를 열때는 서서히 조작하시오.
사용후에는 벨브를 잠그고, 빈 용기일지라도 벨브를 잠궈서 보관하시오.
빈용기내 잔여물질은 위험하므로 안전작업수칙에 따라 용기를 처리하시오.
실린더 손상에 주의 하시오.적절한 이동도구를 사용하고 끌거나,밀거나,굴리거나,
떨어뜨리지 마시오.
절대로 실린더 뚜껑을 잡고 들지 마시오;실린더 뚜껑은 단지 실린더 밸브를 보호
하기 위함이다.절대로 실린더 뚜껑 안에 이 물질(렌치,드라이버 등)을 삽입하지 마
시오;
이것은 밸브의 손상 및 누설을 발생시 킬 수있다.과도하게 잠기거나 녹이슨 뚜껑
을 제거하기 위해서는 적절한 스패너를 사용하시요.
밸브는 천천히 여시오.만약 밸브가 열기가 어렵다면,사용을 중지하고 당신의 공급
처에 연락하시오.
피해야할 물질 및 조건에 유의하시오.
나. 안전한 저장방법
직사광선을 피하고 환기가 잘 되는 곳에 보관하시오.
저장소나 사용지역에는 "금연 또는 화기엄금 "경고표지를 부착하시오.
밀폐용기에 저장하시오.
서늘하고 건조한 장소에 저장하시오.
용기는 열에 노출되었을 경우 압력이 올라갈 수 있으므로 열에 폭로되지 않도록
하시오.
용기의 정전기 발생에 주의하여 저장하시오
저장소는 52℃를 초과하지 않도록 하시오.
용기의 온도를 40℃이하로 유지하시오.
공병과 실병을 구분하여 보관하시오.
8. 노출방지 및 개인보호구
가. 화학물질의 노출기준, 생물학적 노출기준등
O 국내 규정
자료없음
O ACGIH 규정
자료없음
O 생물학적 노출기준
자료없음
나. 적절한 공학적 관리
물질이 폭발농도의 위험이 있을 시 해당 환기장치에 방폭설비를 하시오.
국소배기장치를 설치하시오.
해당 노출기준에 적합한지 확인하시오.
3/6
Business Confidential (Printed : -Uncontrolled  2013-08-30Copy)
Praxair Korea Co., Ltd.

>>> pend


>>> page 4

수소 개정번호   : 제품안전취급서 (MATERIAL SAFETY DATA SHEET)
다. 개인 보호구
O 호흡기 보호
일반적인 사용에서는 필요하지 않음.
밀폐공간 작업시 반드시 송기마스크를 착용하시오.
노출되는 물질의 물리화학적 특성에 맞는 한국산업안전보건공단의 인증을
필한 호흡용 보호구를 착용하시오.
O 눈 보호
실린더 취급시 안전안경을 착용하시오.
노출되는 물질의 물리화학적 특성에 맞는 한국산업안전보건공단의 인증을
필한 안전안경을 선정하시오.
O 손 보호
실린더 취급시 안전장갑을 착용하시오.
노출되는 물질의 물리화학적 특성에 맞는 한국산업안전보건공단의 인증을
필한 안전장갑을 선정하시오.
O 신체보호
실린더 취급시 발등보호 안전화를 착용하시오.
노출되는 물질의 물리화학적 특성에 맞는 한국산업안전보건공단의 인증을
필한 보호의를 선정하시오.


| 9. 물리학적 특성 |
| --- |
| 물리학적 특성 가. 외관 물리적 상태: 압축 가스, 색상: 무색 나. 냄새 무취 다. 냄새 역치 자료없음 라. PH 해당없음 마. 녹는점 / 여는점 -259.2°C 바. 초기 끓는점과 끓는 점 범위 -253.76°C 사. 인화점 인화성가스 아. 증발 속도 해당없음 자. 인화성 (고체, 기체) 인화성가스 차. 인화 또는 폭발 범위의 상한/하한 76 / 4 % 카. 증기압 1240000 ㎜Hg (25℃) 타. 용해도 0.000162 g/100㎖ (21℃) 파. 증기밀도 0.07 하. 비중 0.07 (Air = 1) at 32°F (0°C) and 1 atm 거. n-옥탄올/물 분배 계수 0.45(추정치) 너. 자연발화 온도 566℃ (500-571 ℃) 더. 분해 온도 자료없음 러. 점도 0.008957 cP (26.8℃) 머. 분자량 2.016 |


9. 물리학적 특성
물리학적 특성
가. 외관
물리적 상태: 압축 가스, 색상: 무색
나. 냄새
무취
다. 냄새 역치
자료없음
라. PH
해당없음
마. 녹는점 / 여는점
-259.2°C
바. 초기 끓는점과 끓는 점 범위
-253.76°C
사. 인화점
인화성가스
아. 증발 속도
해당없음
자. 인화성 (고체, 기체)
인화성가스
차. 인화 또는 폭발 범위의 상한/하한
76 / 4 %
카. 증기압
1240000 ㎜Hg (25℃)
타. 용해도
0.000162 g/100㎖ (21℃)
파. 증기밀도
0.07
하. 비중
0.07 (Air = 1) at 32°F (0°C) and 1 atm
거. n-옥탄올/물 분배 계수
0.45(추정치)
너. 자연발화 온도
566℃ (500-571 ℃)
더. 분해 온도
자료없음
러. 점도
0.008957 cP (26.8℃)
머. 분자량
2.016


| 가. 외관 | 물리적 상태: 압축 가스, 색상: 무색 |
| --- | --- |
| 나. 냄새 | 무취 |
| 다. 냄새 역치 | 자료없음 |
| 라. PH | 해당없음 |
| 마. 녹는점 / 여는점 | -259.2°C |
| 바. 초기 끓는점과 끓는 점 범위 | -253.76°C |
| 사. 인화점 | 인화성가스 |
| 아. 증발 속도 | 해당없음 |
| 자. 인화성 (고체, 기체) | 인화성가스 |
| 차. 인화 또는 폭발 범위의 상한/하한 | 76 / 4 % |
| 카. 증기압 | 1240000 ㎜Hg (25℃) |
| 타. 용해도 | 0.000162 g/100㎖ (21℃) |
| 파. 증기밀도 | 0.07 |
| 하. 비중 | 0.07 (Air = 1) at 32°F (0°C) and 1 atm |
| 거. n-옥탄올/물 분배 계수 | 0.45(추정치) |
| 너. 자연발화 온도 | 566℃ (500-571 ℃) |
| 더. 분해 온도 | 자료없음 |
| 러. 점도 | 0.008957 cP (26.8℃) |
| 머. 분자량 | 2.016 |


| 10. 안정성 및 반응성 |
| --- |
| 가. 화학적 안정성 상온 상압에서 안정함 나. 유해 반응의 가능성 가연성 가스, 공기와 산화제 반응으로 폭발할 수 있음. 다. 피해야 할 조건 열·스파크·화염·고열로부터 멀리하시오 - 금연 용기가 열에 노출되면 파열되거나 폭발할 수도 있음. 라. 피해야 할 물질 산화제, 리튬, 할로겐 마. 분해시 생성되는 물질 자극성, 부식성, 독성가스 |


10. 안정성 및 반응성
가. 화학적 안정성
상온 상압에서 안정함
나. 유해 반응의 가능성
가연성 가스, 공기와 산화제 반응으로 폭발할 수 있음.
다. 피해야 할 조건
열·스파크·화염·고열로부터 멀리하시오 - 금연
용기가 열에 노출되면 파열되거나 폭발할 수도 있음.
라. 피해야 할 물질
산화제, 리튬, 할로겐
마. 분해시 생성되는 물질
자극성, 부식성, 독성가스
11. 독성에 관한 정보
가. 가능성이 높은 노출 경로에 관한 정보
O 호흡기를 통한 흡입
구역, 구토, 호흡곤란, 불규칙 심장박동, 두통, 피로, 현기증,
지남력 상실, 감정변화, 얼얼한 느낌, 조정(기능) 손실, 경련,
의식불명, 혼수를 일으킬 수 있음.
O 입을 통한 섭취
가스의 섭취가 발생할 것 같지 않음
O 피부 접촉
자료없음
O 눈 접촉
자료없음
나. 단기 및 장기 노출에 의한 지연, 급성 영향
및 만성 영향
O 급성 독성
- 경구
자료없음
- 경피
자료없음
- 흡입
LC50 > 7500 ppm 4 hr Rat
4/6
Business Confidential (Printed : -Uncontrolled  2013-08-30Copy)
Praxair Korea Co., Ltd.

>>> pend


>>> page 5

수소 개정번호   : 제품안전취급서 (MATERIAL SAFETY DATA SHEET)
O 피부 부식성 또는 자극성
자료없음
O 심한 눈 손상 또는 자극성
자료없음
O 호흡기 과민성
자료없음
O 피부 과민성
자료없음
O 발암성
자료없음
O 생식세포 변이원성
자료없음
O 생식독성
자료없음
O 표적장기 전신독성 물질(1회 노출)
자료없음
O 표적장기 전신독성 물질(반복 노출)
자료없음
O 흡인 유해성
자료없음
다. 독성의 수치적 척도(급성 독성 추정치 등)
자료없음


| 12. 환경에 미치는 영향 |
| --- |
| 가. 수생 육생 생태 독성 O 어류 자료없음 O 갑각류 자료없음 O 조류 자료없음 나. 잔류성 및 분해성 O 잔류성 자료없음 O 분해성 자료없음 다. 생물 농축성 O 생분해성 자료없음 O 농축성 자료없음 라. 토양 이동성 자료없음 마. 기타 유해 영향 자료없음 |


12. 환경에 미치는 영향
가. 수생 육생 생태 독성
O 어류
자료없음
O 갑각류
자료없음
O 조류
자료없음
나. 잔류성 및 분해성
O 잔류성
자료없음
O 분해성
자료없음
다. 생물 농축성
O 생분해성
자료없음
O 농축성
자료없음
라. 토양 이동성
자료없음
마. 기타 유해 영향
자료없음


| 13. 폐기시 주의사항 |
| --- |
| 가. 폐기방법 폐기물 관리법에 명시된 경우 규정에 따라 내용물 용기를 폐기하시오. 나. 폐기시 주의 사항 (관련 법규에 명시된 내용에 따라) 내용물 용기를 폐기하시오. |


13. 폐기시 주의사항
가. 폐기방법
폐기물 관리법에 명시된 경우 규정에 따라 내용물 용기를 폐기하시오.
나. 폐기시 주의 사항
(관련 법규에 명시된 내용에 따라) 내용물 용기를 폐기하시오.


| 14. 운송에 필요한 정보 |
| --- |
| 가. 유엔 번호 1049 나. 유엔 적정 선적명 수소(압축된 것), HYDROGEN, COMPRESSED 다. 운송에서의 위험성 등급 2.1 라. 용기등급 자료없음 마. 해양오염 물질 자료없음 바. 사용자 운송 또는 운송 수단에 관련해 알 필요가 있거든 필요한 특별한 안전대책 O 화재시 비상조치의 종류 F-D O 유출시 비상조치의 종류 S-U |


14. 운송에 필요한 정보
가. 유엔 번호
1049
나. 유엔 적정 선적명
수소(압축된 것), HYDROGEN, COMPRESSED
다. 운송에서의 위험성 등급
2.1
라. 용기등급
자료없음
마. 해양오염 물질
자료없음
바. 사용자 운송 또는 운송 수단에 관련해 알 필요가 있거든 필요한 특별한 안전대책
O 화재시 비상조치의 종류
F-D
O 유출시 비상조치의 종류
S-U


| 15. 법적 규제현황 |
| --- |
| 가. 산업안전보건법에 의한 규제 해당없음 나. 유해화학물질관리법에 의한 규제 해당없음 다. 위험물안전관리법에 의한 규제 해당없음 라. 폐기물관리법에 의한 규제 해당없음 마. 기타 국내 및 외국법에 의한 규제 O 잔류성 유기오염물질 관리법 해당없음 O EU 분류정보 - 확정 분류 결과 F+; R12 - 위험 문구 R12 - 예방조치 문구 S2, S9, S16, S33 O 미국 관리 정보 - OSHA 규정(29CFR1910,119) 해당없음 - CERCLA 103규정(40CFR302,4) 해당없음 - EPCRA 302 규정(40CFR355,30) 해당없음 - EPCRA 304 규정(40CFR355,40) 해당없음 - EPCRA 313 규정(40CFR372,65) 해당없음 O 로테르담 협약 물질 해당없음 O 스톡홀롬 협약 물질 해당없음 O 몬트리올 의정서 물질 해당없음 |


15. 법적 규제현황
가. 산업안전보건법에 의한 규제
해당없음
나. 유해화학물질관리법에 의한 규제
해당없음
다. 위험물안전관리법에 의한 규제
해당없음
라. 폐기물관리법에 의한 규제
해당없음
마. 기타 국내 및 외국법에 의한 규제
O 잔류성 유기오염물질 관리법
해당없음
O EU 분류정보
- 확정 분류 결과
F+; R12
- 위험 문구
R12
- 예방조치 문구
S2, S9, S16, S33
O 미국 관리 정보
- OSHA 규정(29CFR1910,119)
해당없음
- CERCLA 103규정(40CFR302,4)
해당없음
- EPCRA 302 규정(40CFR355,30)
해당없음
- EPCRA 304 규정(40CFR355,40)
해당없음
- EPCRA 313 규정(40CFR372,65)
해당없음
O 로테르담 협약 물질
해당없음
O 스톡홀롬 협약 물질
해당없음
O 몬트리올 의정서 물질
해당없음
5/6
Business Confidential (Printed : -Uncontrolled  2013-08-30Copy)
Praxair Korea Co., Ltd.

>>> pend


>>> page 6

수소 개정번호   : 제품안전취급서 (MATERIAL SAFETY DATA SHEET)


| 16. 기타 참고사항 |
| --- |
| 가. 자료의 출처 미국 PRAXAIR 사 MSDS NO. P-4604-H, 한국 산업 안전 보건 공단 MSDS 제공자료(수 소 2010.08.31) 나. 최초 작성 일자 2008년 3월 20일 다. 개정 횟수 및 최 2013년 5월 07일(3차) 종 개정 일자 라. 기타 |


16. 기타 참고사항
가. 자료의 출처
미국 PRAXAIR 사 MSDS NO. P-4604-H, 한국 산업 안전 보건 공단 MSDS 제공자료(수
소 2010.08.31)
나. 최초 작성 일자&nbsp;&nbsp;2008년 3월 20일
다. 개정 횟수 및 최
종 개정 일자
2013년 5월 07일(3차)
라. 기타
6/6
Business Confidential (Printed : -Uncontrolled  2013-08-30Copy)
Praxair Korea Co., Ltd.

>>> pend"""
        },
                {
            "document_id": "MOCK_MSDS_006",
            "file_name": "output4.pdf",
            "content": """>>> page 1

## **SAFETY DATA SHEET**
According to OSHA Hazard Communication Standard, 29 CFR
1910.1200
# **CARADOL EP500-11**
Version
2.1
Revision Date:
04/25/2018
SDS Number:
800001008935
Print Date: 09/03/2022
Date of last issue: 05/08/2015
**SECTION 1. IDENTIFICATION**
Product name
:
CARADOL EP500-11
Product code
:
U1705
Synonyms
:
Polyol
**Manufacturer or supplier's details**
Company
:**Shell Chemical LP**
PO Box 576
HOUSTON TX  77001
USA
SDS Request
:  1-800-240-6737
Customer Service
:  1-855-697-4355
**Emergency telephone number**
Chemtrec Domestic (24 hr)
:  1-800-424-9300
Chemtrec International (24
hr)
:  1-703-527-3887
**Recommended use of the chemical and restrictions on use**
Recommended use
: Use for the manufacture of polyurethane products.
Restrictions on use
:
This product must not be used in applications other than the
above without first seeking the advice of the supplier.
Other information
: CARADOL is a registered trademark of Shell trademark Man-
agement BV.
**SECTION 2. HAZARDS IDENTIFICATION**
**GHS classification in accordance with 29 CFR 1910.1200**
Based on available data this substance / mixture does not meet the classification criteria.
**GHS label elements**
Hazard pictograms
: No Hazard Symbol required
Signal word
:
No signal word
Hazard statements
:
PHYSICAL HAZARDS:
Not classified as a physical hazard under GHS criteria.
HEALTH HAZARDS:
Not classified as a health hazard under GHS criteria.
ENVIRONMENTAL HAZARDS:
Not classified as an environmental hazard under GHS criteria.
1 / 16

>>> pend


>>> page 2

## **SAFETY DATA SHEET**
According to OSHA Hazard Communication Standard, 29 CFR
1910.1200
# **CARADOL EP500-11**
Version
2.1
Revision Date:
04/25/2018
SDS Number:
800001008935
Print Date: 09/03/2022
Date of last issue: 05/08/2015
Precautionary statements
:
**Prevention:**
No precautionary phrases.
**Response:**
No precautionary phrases.
**Storage:**
No precautionary phrases.
**Disposal:**
No precautionary phrases.
**Other hazards which do not result in classification**
none
The classification of this material is based on OSHA HCS 2012 criteria.
**SECTION 3. COMPOSITION/INFORMATION ON INGREDIENTS**
Substance / Mixture
:  Mixture
**Hazardous components**


|  | Chemical name |  | Synonyms |  |  | CAS-No. |  |  | Concentration (% w/w) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Propoxylated Sorbitol |  |  | D-Glucitol, propoxylated |  | 52625-13-5 |  |  | 50 - 60 |  |
| Propoxylated glycerol |  |  | Glycerol, propoxylated (MW 3000) |  | 25791-96-2 |  |  | 40 - 50 |  |


Chemical name
Synonyms
CAS-No.
Concentration (% w/w)
Propoxylated Sorbitol D-Glucitol,
52625-13-5
50 -60
propoxylated
Propoxylated glycerol Glycerol,
25791-96-2
40 -50
propoxylated
(MW 3000)
**SECTION 4. FIRST-AID MEASURES**
General advice
:
Not expected to be a health hazard when used under normal
conditions.
If inhaled
:
No treatment necessary under normal conditions of use.
If symptoms persist, obtain medical advice.
In case of skin contact
:
Remove contaminated clothing. Flush exposed area with wa-
ter and follow by washing with soap if available.
If persistent irritation occurs, obtain medical attention.
In case of eye contact
:
Flush eye with copious quantities of water.
Remove contact lenses, if present and easy to do. Continue
rinsing.
If persistent irritation occurs, obtain medical attention.
If swallowed
:
In general no treatment is necessary unless large quantities
are swallowed, however, get medical advice.
Most important symptoms
and effects, both acute and
delayed
:
Does not pose an acute hazard under normal conditions of
use.
2 / 16

>>> pend


>>> page 3

## **SAFETY DATA SHEET**
According to OSHA Hazard Communication Standard, 29 CFR
1910.1200
# **CARADOL EP500-11**
Version
2.1
Revision Date:
04/25/2018
SDS Number:
800001008935
Print Date: 09/03/2022
Date of last issue: 05/08/2015
Protection of first-aiders
:
When administering first aid, ensure that you are wearing the
appropriate personal protective equipment according to the
incident, injury and surroundings.
Indication of any immediate
medical attention and special
treatment needed
:
Treat symptomatically. Following cases of gross over-
exposure, investigation of liver, kidney and eye function may
be advisable. Records of such incidents should be maintained
for future reference.
**SECTION 5. FIRE-FIGHTING MEASURES**
Suitable extinguishing media
:
Large fires should only be fought by properly trained fire fight-
ers.
Alcohol-resistant foam, water spray or fog. Dry chemical pow-
der, carbon dioxide, sand or earth may be used for small fires
only.
Unsuitable extinguishing
media
:
Do not use water in a jet.
Specific hazards during fire-
fighting
:
Will only burn if enveloped in a pre-existing fire.
Hazardous combustion products may include:
Carbon dioxide
Unidentified organic and inorganic compounds.
Toxic gases
Carbon monoxide.
Specific extinguishing meth-
ods
:
Standard procedure for chemical fires.
Further information
:
Clear fire area of all non-emergency personnel.
All storage areas should be provided with adequate fire
fighting facilities.
Keep adjacent containers cool by spraying with water.
Special protective equipment
for firefighters
:
Proper protective equipment including chemical resistant
gloves are to be worn; chemical resistant suit is indicated if
large contact with spilled product is expected. Self-Contained
Breathing Apparatus must be worn when approaching a fire in
a confined space. Select fire fighter's clothing approved to
relevant Standards (e.g.  Europe: EN469).
**SECTION 6. ACCIDENTAL RELEASE MEASURES**
Personal precautions, protec-
tive equipment and emer-
gency procedures
:
Observe all relevant local and international regulations.
Avoid contact with skin, eyes and clothing.
Avoid inhaling vapour and/or mists.
Extinguish any naked flames. Do not smoke. Remove ignition
sources. Avoid sparks.
Environmental precautions
:
Remove all possible sources of ignition in the surrounding
3 / 16

>>> pend


>>> page 4

## **SAFETY DATA SHEET**
According to OSHA Hazard Communication Standard, 29 CFR
1910.1200
# **CARADOL EP500-11**
Version
2.1
Revision Date:
04/25/2018
SDS Number:
800001008935
Print Date: 09/03/2022
Date of last issue: 05/08/2015
area.
Prevent from spreading or entering into drains, ditches or riv-
ers by using sand, earth, or other appropriate barriers.
Use appropriate containment to avoid environmental contami-
nation.
Ventilate contaminated area thoroughly.
Methods and materials for
containment and cleaning up
:
For large liquid spills (> 1 drum), transfer by mechanical
means such as vacuum truck to a salvage tank for recovery or
safe disposal. Do not flush away residues with water. Retain
as contaminated waste. Allow residues to evaporate or soak
up with an appropriate absorbent material and dispose of
safely. Remove contaminated soil and dispose of safely
For small liquid spills (< 1 drum), transfer by mechanical
means to a labeled, sealable container for product recovery or
safe disposal. Allow residues to evaporate or soak up with an
appropriate absorbent material and dispose of safely. Remove
contaminated soil and dispose of safely.
Proper disposal should be evaluated based on regulatory
status of this material (refer to Chapter 13), potential contami-
nation from subsequent use and spillage, and regulations
governing disposal in the local area.
Additional advice
: For guidance on selection of personal protective equipment
see Chapter 8 of this Safety Data Sheet.
For guidance on disposal of spilled material see Chapter 13 of
this Safety Data Sheet.
**SECTION 7. HANDLING AND STORAGE**
Technical measures
:
Avoid breathing of or direct contact with material. Only use in
well ventilated areas. Wash thoroughly after handling.  For
guidance on selection of personal protective equipment see
Chapter 8 of this Safety Data Sheet.
Use the information in this data sheet as input to a risk as-
sessment of local circumstances to help determine appropri-
ate controls for safe handling, storage and disposal of this
material.
Ensure that all local regulations regarding handling and stor-
age facilities are followed.
Advice on safe handling
:
In accordance with good industrial hygiene practices, precau-
tions should be taken to avoid breathing of material.
Use local exhaust extraction over processing area.
Avoid unintentional contact with isocyanates to prevent uncon-
trolled polymerisation.
Avoid contact with skin, eyes and clothing.
Air-dry contaminated clothing in a well-ventilated area before
laundering.
Do not empty into drains.
Handling Temperature:
4 / 16

>>> pend


>>> page 5

## **SAFETY DATA SHEET**
According to OSHA Hazard Communication Standard, 29 CFR
1910.1200
# **CARADOL EP500-11**
Version
2.1
Revision Date:
04/25/2018
SDS Number:
800001008935
Print Date: 09/03/2022
Date of last issue: 05/08/2015
Ambient.
When handling product in drums, safety footwear should be
worn and proper handling equipment should be used.
Extinguish any naked flames. Do not smoke. Remove ignition
sources. Avoid sparks.
Avoidance of contact
:
Avoid contact with isocyanates, copper and copper alloys,
zinc, strong oxidizing agents, and water.
Product Transfer
:  Lines should be purged with nitrogen before and after product
transfer. Keep containers closed when not in use.
Conditions for safe storage
:
Refer to section 15 for any additional specific legislation cov-
ering the packaging and storage of this product.
Storage period
:  24 Months
Further information on stor-
age stability
:  Prevent all contact with water and with moist atmosphere.
Tanks must be clean, dry and rust-free.
Prevent ingress of water.
Must be stored in a diked (bunded) well- ventilated area, away
from sunlight, ignition sources and other sources of heat.
Nitrogen blanket recommended for large tanks (capacity 100
m3 or higher).
Drums should be stacked to a maximum of 3 high.
Storage Temperature:
Ambient.
Storage should be handled at temperatures such that viscosi-
ties are less than 500 cSt; typically at 25-50 °C.
Tanks should be fitted with heating coils in areas where the
ambient temperatures are below the recommended product
handling temperatures. Heating coil skin temperatures should
not exceed 100 °C.
Packaging material
:  Suitable material: Stainless steel., For container paints, use
epoxy paint, zinc silicate paint.
Unsuitable material: Copper., Copper alloys.
Specific use(s)
:  Not applicable
Ensure that all local regulations regarding handling and stor-
age facilities are followed.
**SECTION 8. EXPOSURE CONTROLS AND PERSONAL PROTECTION**
**Components with workplace control parameters**
Contains no substances with occupational exposure limit values.
5 / 16

>>> pend


>>> page 6

## **SAFETY DATA SHEET**
According to OSHA Hazard Communication Standard, 29 CFR
1910.1200
# **CARADOL EP500-11**
Version
2.1
Revision Date:
04/25/2018
SDS Number:
800001008935
Print Date: 09/03/2022
Date of last issue: 05/08/2015
**Biological occupational exposure limits**
No biological limit allocated.
**Monitoring Methods**
Monitoring of the concentration of substances in the breathing zone of workers or in the general
workplace may be required to confirm compliance with an OEL and adequacy of exposure con-
trols. For some substances biological monitoring may also be appropriate.
Validated exposure measurement methods should be applied by a competent person and sam-
ples analysed by an accredited laboratory.
Examples of sources of recommended exposure measurement methods are given below or con-
tact the supplier. Further national methods may be available.
National Institute of Occupational Safety and Health (NIOSH), USA: Manual of Analytical Meth-
ods http://www.cdc.gov/niosh/
Occupational Safety and Health Administration (OSHA), USA: Sampling and Analytical Methods
http://www.osha.gov/
Health and Safety Executive (HSE), UK: Methods for the Determination of Hazardous Substanc-
es http://www.hse.gov.uk/
Institut für Arbeitsschutz Deutschen Gesetzlichen Unfallversicherung (IFA) , Germany
http://www.dguv.de/inhalt/index.jsp
L'Institut National de Recherche et de Securité, (INRS), France http://www.inrs.fr/accueil
**Engineering measures**
:
The level of protection and types of controls necessary will
vary depending upon potential exposure conditions. Select
controls based on a risk assessment of local circumstances.
Appropriate measures include:
Where material is heated, sprayed or mist formed, there is
greater potential for airborne concentrations to be generated.
Adequate ventilation to control airborne concentrations.
General Information:
Always observe good personal hygiene measures, such as
washing hands after handling the material and before eating,
drinking, and/or smoking.  Routinely wash work clothing and
protective equipment to remove contaminants.  Discard con-
taminated clothing and footwear that cannot be cleaned.
Practice good housekeeping.
Define procedures for safe handling and maintenance of
controls.
Educate and train workers in the hazards and control
measures relevant to normal activities associated with this
product.
Ensure appropriate selection, testing and maintenance of
equipment used to control exposure, e.g. personal protective
equipment, local exhaust ventilation.
Drain down system prior to equipment break-in or mainte-
nance.
Retain drain downs in sealed storage pending disposal or
subsequent recycle.
**Personal protective equipment**
Respiratory protection
:
No respiratory protection is ordinarily required under normal
6 / 16

>>> pend


>>> page 7

## **SAFETY DATA SHEET**
According to OSHA Hazard Communication Standard, 29 CFR
1910.1200
# **CARADOL EP500-11**
Version
2.1
Revision Date:
04/25/2018
SDS Number:
800001008935
Print Date: 09/03/2022
Date of last issue: 05/08/2015
conditions of use.
In accordance with good industrial hygiene practices, precau-
tions should be taken to avoid breathing of material.
Hand protection
Remarks
:
Where hand contact with the product may occur the use of
gloves approved to relevant standards (e.g. Europe: EN374,
US: F739) made from the following materials may provide
suitable chemical protection. Longer term protection: Nitrile
rubber. Incidental contact/Splash protection: PVC, neoprene
or nitrile rubber gloves For continuous contact we recom-
mend gloves with breakthrough time of more than 240
minutes with preference for > 480 minutes where suitable
gloves can be identified. For short-term/splash protection we
recommend the same, but recognize that suitable gloves
offering this level of protection may not be available and in
this case a lower breakthrough time maybe acceptable so
long as appropriate maintenance and replacement regimes
are followed. Glove thickness is not a good predictor of glove
resistance to a chemical as it is dependent on the exact
composition of the glove material. Glove thickness should be
typically greater than 0.35 mm depending on the glove make
and model. Suitability and durability of a glove is dependent
on usage, e.g. frequency and duration of contact, chemical
resistance of glove material, dexterity. Always seek advice
from glove suppliers. Contaminated gloves should be re-
placed. Personal hygiene is a key element of effective hand
care. Gloves must only be worn on clean hands. After using
gloves, hands should be washed and dried thoroughly. Appli-
cation of a non-perfumed moisturizer is recommended.
Eye protection
:
If material is handled such that it could be splashed into eyes,
protective eyewear is recommended.
Skin and body protection
:
Skin protection is not ordinarily required beyond standard
work clothes.
It is good practice to wear chemical resistant gloves.
Protective measures
:
Personal protective equipment (PPE) should meet recom-
mended national standards. Check with PPE suppliers.
Hygiene measures
:
Wash hands before eating, drinking, smoking and using the
toilet.
Launder contaminated clothing before re-use.
**Environmental exposure controls**
General advice
:  Local guidelines on emission limits for volatile substances
must be observed for the discharge of exhaust air containing
vapour.
Minimise release to the environment. An environmental as-
sessment must be made to ensure compliance with local envi-
ronmental legislation.
Information on accidental release measures are to be found in
7 / 16

>>> pend


>>> page 8

## **SAFETY DATA SHEET**
According to OSHA Hazard Communication Standard, 29 CFR
1910.1200
# **CARADOL EP500-11**
Version
2.1
Revision Date:
04/25/2018
SDS Number:
800001008935
Print Date: 09/03/2022
Date of last issue: 05/08/2015
section 6.
**SECTION 9. PHYSICAL AND CHEMICAL PROPERTIES**
Appearance
:
Viscous liquid.
Colour
:  clear
Odour
:  odourless
Odour Threshold
:  Not relevant
pH
:
ca. 9
Melting point/freezing point
:
Data not available
Boiling point/boiling range
:
Data not available
Flash point
:
> 100 °C / 212 °F
Evaporation rate
:  Data not available
Flammability (solid, gas)
:
Not applicable
Upper explosion limit / upper
flammability limit
:
Data not available
Lower explosion limit / Lower
flammability limit
:
Data not available
Vapour pressure
:
ca. 0.003 Pa (20 °C / 68 °F)
Relative vapour density
:
Data not available
Relative density
:
Data not available
Density
:
ca. 1,108 kg/m3 (20 °C / 68 °F)
Solubility(ies)
Water solubility
:
Miscible.
Partition coefficient: n-
octanol/water
:
log Pow: < 1
Auto-ignition temperature
:
> 300 °C / 572 °F
Decomposition temperature
:  < 300 °C / 572 °F
Viscosity
Viscosity, dynamic
:
5.380 mPa.s (20 °C / 68 °F)
8 / 16

>>> pend


>>> page 9

## **SAFETY DATA SHEET**
According to OSHA Hazard Communication Standard, 29 CFR
1910.1200
# **CARADOL EP500-11**
Version
2.1
Revision Date:
04/25/2018
SDS Number:
800001008935
Print Date: 09/03/2022
Date of last issue: 05/08/2015
Viscosity, kinematic
:
Data not available
Explosive properties
:
Not classified
Oxidizing properties
:
Not applicable
Surface tension
:
Data not available
Conductivity
:  Electrical conductivity: > 10,000 pS/m, A number of factors,
for example liquid temperature, presence of contaminants,
and anti-static additives can greatly influence the conductivity
of a liquid, This material is not expected to be a static accumu-
lator.
Molecular weight
:
Data not available
**SECTION 10. STABILITY AND REACTIVITY**
Reactivity
:  The product does not pose any further reactivity hazards in
addition to those listed in the following sub-paragraph.
Chemical stability
:  No hazardous reaction is expected when handled and stored
according to provisions
Hygroscopic.
Possibility of hazardous reac-
tions
:
Polymerises exothermically with di-isocyanates at ambient
temperatures.
The reaction becomes progressively more vigorous and can
be violent at higher temperatures if the miscibility of reaction
partners is good or is supported by stirring or by the presence
of solvents.
Reacts with strong oxidising agents.
Conditions to avoid
:
Heat, flames, and sparks.
Product cannot ignite due to static electricity.
Incompatible materials
:  Avoid contact with isocyanates, copper and copper alloys,
zinc, strong oxidizing agents, and water.
Hazardous decomposition
products
:   Unknown toxic products may be formed.
**SECTION 11. TOXICOLOGICAL INFORMATION**
Basis for assessment
: Information given is based on product testing, and/or similar
products, and/or components.
**Information on likely routes of exposure**
Exposure may occur via inhalation, ingestion, skin absorption, skin or eye contact, and accidental
ingestion.
**Acute toxicity**
9 / 16

>>> pend


>>> page 10

## **SAFETY DATA SHEET**
According to OSHA Hazard Communication Standard, 29 CFR
1910.1200
# **CARADOL EP500-11**
Version
2.1
Revision Date:
04/25/2018
SDS Number:
800001008935
Print Date: 09/03/2022
Date of last issue: 05/08/2015
**Product****:**
Acute oral toxicity
:  LD50 : > 5000 mg/kg
Remarks: Low toxicity:
Based on available data, the classification criteria are not met.
Acute inhalation toxicity
:  Remarks: Based on available data, the classification criteria
are not met.
Acute dermal toxicity
:  LD50 : > 5000 mg/kg
Remarks: Low toxicity:
Based on available data, the classification criteria are not met.
**Skin corrosion/irritation**
**Product****:**
Remarks: Not irritating to skin.
**Serious eye damage/eye irritation**
**Product****:**
Remarks: Not irritating to eye.
**Respiratory or skin sensitisation**
**Product****:**
Remarks: Not a skin sensitiser.
Based on available data, the classification criteria are not met.
**Germ cell mutagenicity**
**Product****:**
:  Remarks: Not mutagenic.
**Carcinogenicity**
**Product****:**
Remarks: Not a carcinogen., Based on available data, the classification criteria are not met.
**IARC**
No component of this product present at levels greater than or
equal to 0.1% is identified as probable, possible or confirmed
human carcinogen by IARC.
**OSHA**
No component of this product present at levels greater than or
equal to 0.1% is on OSHA’s list of regulated carcinogens.
**NTP**
No component of this product present at levels greater than or
equal to 0.1% is identified as a known or anticipated carcinogen
by NTP.
10 / 16

>>> pend


>>> page 11

## **SAFETY DATA SHEET**
According to OSHA Hazard Communication Standard, 29 CFR
1910.1200
# **CARADOL EP500-11**
Version
2.1
Revision Date:
04/25/2018
SDS Number:
800001008935
Print Date: 09/03/2022
Date of last issue: 05/08/2015
**Reproductive toxicity**
**Product****:**
:
Remarks: Not a developmental toxicant., Based on available
data, the classification criteria are not met., Does not impair
fertility.
**STOT - single exposure**
**Product****:**
Remarks: Based on available data, the classification criteria are not met.
**STOT - repeated exposure**
**Product****:**
Remarks: Based on available data, the classification criteria are not met.
**Aspiration toxicity**
**Product****:**
Not an aspiration hazard.
**Further information**
**Product****:**
Remarks: Classifications by other authorities under varying regulatory frameworks may exist.
**SECTION 12. ECOLOGICAL INFORMATION**
Basis for assessment
:  Incomplete ecotoxicological data are available for this product.
The information given below is based partly on a knowledge of
the components and the ecotoxicology of similar products.
**Ecotoxicity**
**Product:**
Toxicity to fish (Acute toxici-
ty)
:  LC50: > 100 mg/l
Remarks: Practically non toxic:
Toxicity to daphnia and other
aquatic invertebrates (Acute
toxicity)
:  EC50: > 100 mg/l
Remarks: Practically non toxic:
Toxicity to algae (Acute tox-
icity)
:  EC50: > 100 mg/l
Remarks: Practically non toxic:
Toxicity to fish (Chronic tox-
:
Remarks: Data not available
11 / 16

>>> pend


>>> page 12

## **SAFETY DATA SHEET**
According to OSHA Hazard Communication Standard, 29 CFR
1910.1200
# **CARADOL EP500-11**
Version
2.1
Revision Date:
04/25/2018
SDS Number:
800001008935
Print Date: 09/03/2022
Date of last issue: 05/08/2015
icity)
Toxicity to daphnia and other
aquatic invertebrates (Chron-
ic toxicity)
:
Remarks: Data not available
Toxicity to microorganisms
(Acute toxicity)
:
IC50: > 100 mg/l
Remarks: Practically non toxic:
Based on available data, the classification criteria are not met.
**Persistence and degradability**
**Product:**
Biodegradability
:  Remarks: Not readily biodegradable.
Oxidises rapidly by photo-chemical reactions in air.
**Bioaccumulative potential**
**Product:**
Bioaccumulation
:  Remarks: Does not have the potential to bioaccumulate signif-
icantly.
**Mobility in soil**
**Product:**
Mobility
:
Remarks: If the product enters soil, one or more constituents
will or may be mobile and may contaminate groundwater.
**Other adverse effects**
no data available
**SECTION 13. DISPOSAL CONSIDERATIONS**
**Disposal methods**
Waste from residues
:
Recover or recycle if possible.
It is the responsibility of the waste generator to determine the
toxicity and physical properties of the material generated to
determine the proper waste classification and disposal meth-
ods in compliance with applicable regulations.
Do not dispose into the environment, in drains or in water
courses
Waste product should not be allowed to contaminate soil or
water.
Disposal should be in accordance with applicable regional,
national, and local laws and regulations.
Local regulations may be more stringent than regional or na-
tional requirements and must be complied with.
12 / 16

>>> pend


>>> page 13

## **SAFETY DATA SHEET**
According to OSHA Hazard Communication Standard, 29 CFR
1910.1200
# **CARADOL EP500-11**
Version
2.1
Revision Date:
04/25/2018
SDS Number:
800001008935
Print Date: 09/03/2022
Date of last issue: 05/08/2015
Contaminated packaging
:
Drain container thoroughly.
After draining, vent in a safe place away from sparks and fire.
Send to drum recoverer or metal reclaimer.
Dispose in accordance with prevailing regulations, preferably
to a recognized collector or contractor.  The competence of
the collector or contractor should be established beforehand.
**SECTION 14. TRANSPORT INFORMATION**
**National Regulations**
**US Department of Transportation Classification (49 CFR Parts 171-180)**
Not regulated as a dangerous good
**International Regulations**
**IATA-DGR**
Not regulated as a dangerous good
**IMDG-Code**
Not regulated as a dangerous good
**Transport in bulk according to Annex II of MARPOL 73/78 and the IBC Code**
Pollution category
:  Not applicable
Ship type
:  Not applicable
Product name
:  Not applicable
**Special precautions for user**
Remarks
: Special Precautions:  Refer to Chapter 7, Handling & Storage,
for special precautions which a user needs to be aware of or
needs to comply with in connection with transport.
**Additional Information**
**:**This product may be transported under nitrogen blanketing.
Nitrogen is an odourless and invisible gas.  Exposure to nitro-
gen may cause asphyxiation or death. Personnel must ob-
serve strict safety precautions when involved with a confined
space entry.
**SECTION 15. REGULATORY INFORMATION**
**EPCRA - Emergency Planning and Community Right-to-Know Act**
*: This material does not contain any components with a CERCLA RQ.
**SARA 304 Extremely Hazardous Substances Reportable Quantity**
This material does not contain any components with a section 304 EHS RQ.
**SARA 302 Extremely Hazardous Substances Threshold Planning Quantity**
This material does not contain any components with a section 302 EHS TPQ.
**SARA 311/312 Hazards**
:  No SARA Hazards
13 / 16

>>> pend


>>> page 14

## **SAFETY DATA SHEET**
According to OSHA Hazard Communication Standard, 29 CFR
1910.1200
# **CARADOL EP500-11**
Version
2.1
Revision Date:
04/25/2018
SDS Number:
800001008935
Print Date: 09/03/2022
Date of last issue: 05/08/2015
**SARA 313**
:  This material does not contain any chemical components with
known CAS numbers that exceed the threshold (De Minimis)
reporting levels established by SARA Title III, Section 313.
**Clean Water Act**
This product does not contain any Hazardous Chemicals listed under the U.S. CleanWater Act,
Section 311, Table 117.3.
**US State Regulations**
**California Prop. 65**
This product does not contain any chemicals known to State of California to cause cancer, birth
defects, or any other reproductive harm.
**Other regulations:**
The regulatory information is not intended to be comprehensive. Other regulations may apply
to this material.
**The components of this product are reported in the following inventories:**
AICS
:
Listed
DSL
:
Listed
IECSC
:
Listed
ENCS
:
Listed
KECI
:
Listed
NZIoC
:
Listed
PICCS
:
Listed
TSCA
:
Listed
TCSI
:
Listed
**SECTION 16. OTHER INFORMATION**
**Further information**
NFPA Rating (Health, Fire, Reac-
tivity)
0, 1, 0
**Full text of other abbreviations**
Abbreviations and Acronyms
:  The standard abbreviations and acronyms used in this docu-
ment can be looked up in reference literature (e.g. scientific
dictionaries) and/or websites.
14 / 16

>>> pend


>>> page 15

## **SAFETY DATA SHEET**
According to OSHA Hazard Communication Standard, 29 CFR
1910.1200
# **CARADOL EP500-11**
Version
2.1
Revision Date:
04/25/2018
SDS Number:
800001008935
Print Date: 09/03/2022
Date of last issue: 05/08/2015
ACGIH = American Conference of Governmental Industrial
Hygienists
ADR = European Agreement concerning the International
Carriage of Dangerous Goods by Road
AICS = Australian Inventory of Chemical Substances
ASTM = American Society for Testing and Materials
BEL = Biological exposure limits
BTEX =  Benzene, Toluene, Ethylbenzene, Xylenes
CAS = Chemical Abstracts Service
CEFIC = European Chemical Industry Council
CLP = Classification Packaging and Labelling
COC = Cleveland Open-Cup
DIN = Deutsches Institut fur Normung
DMEL = Derived Minimal Effect Level
DNEL = Derived No Effect Level
DSL = Canada Domestic Substance List
EC = European Commission
EC50 = Effective Concentration fifty
ECETOC = European Center on Ecotoxicology and Toxicolo-
gy Of Chemicals
ECHA = European Chemicals Agency
EINECS = The European Inventory of Existing Commercial
Chemical Substances
EL50 = Effective Loading fifty
ENCS = Japanese Existing and New Chemical Substances
Inventory
EWC = European Waste Code
GHS = Globally Harmonised System of Classification and
Labelling of Chemicals
IARC = International Agency for Research on Cancer
IATA = International Air Transport Association
IC50 = Inhibitory Concentration fifty
IL50 = Inhibitory Level fifty
IMDG = International Maritime Dangerous Goods
INV = Chinese Chemicals Inventory
IP346 =  Institute of Petroleum  test method N° 346 for the
determination of polycyclic aromatics DMSO-extractables
KECI = Korea Existing Chemicals Inventory
LC50 = Lethal Concentration fifty
LD50 = Lethal Dose fifty per cent.
LL/EL/IL = Lethal Loading/Effective Loading/Inhibitory loading
LL50 = Lethal Loading fifty
MARPOL = International Convention for the Prevention of
Pollution From Ships
NOEC/NOEL = No Observed Effect Concentration / No Ob-
served Effect Level
OE_HPV = Occupational Exposure - High Production Volume
PBT = Persistent, Bioaccumulative and Toxic
PICCS = Philippine Inventory of Chemicals and Chemical
Substances
PNEC = Predicted No Effect Concentration
REACH = Registration Evaluation And Authorisation Of
Chemicals
15 / 16

>>> pend


>>> page 16

## **SAFETY DATA SHEET**
According to OSHA Hazard Communication Standard, 29 CFR
1910.1200
# **CARADOL EP500-11**
Version
2.1
Revision Date:
04/25/2018
SDS Number:
800001008935
Print Date: 09/03/2022
Date of last issue: 05/08/2015
RID = Regulations Relating to International Carriage of Dan-
gerous Goods by Rail
SKIN_DES = Skin Designation
STEL = Short term exposure limit
TRA = Targeted Risk Assessment
TSCA = US Toxic Substances Control Act
TWA = Time-Weighted Average
vPvB = very Persistent and very Bioaccumulative
A vertical bar (|) in the left margin indicates an amendment from the previous version.
Sources of key data used to
compile the Safety Data
Sheet
:  The quoted data are from, but not limited to, one or more
sources of information (e.g. toxicological data from Shell
Health Services, material suppliers’ data, CONCAWE, EU
IUCLID date base, EC 1272 regulation, etc).
Revision Date
:  04/25/2018
The information provided in this Safety Data Sheet is correct to the best of our knowledge, infor-
mation and belief at the date of its publication. The information given is designed only as a guid-
ance for safe handling, use, processing, storage, transportation, disposal and release and is not
to be considered a warranty or quality specification. The information relates only to the specific
material designated and may not be valid for such material used in combination with any other
materials or in any process, unless specified in the text.
US / EN
16 / 16

>>> pend"""
        },
        {
            "document_id": "MOCK_MSDS_007",
            "file_name": "output(7).pdf",
            "content": """
            >>> page_1

![image](data:image/png;base64,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)

물질안전보건자료 (MSDS)

저작권 ,2020, 3M Company.

문서 그룹

35-7946-3

버전 번호

1.02

발행일 :

2020/03/10

대체일 :

2020/03/10

본 물질안전보건자료 (MSDS) 는 산업안전보건법에 따라 작성되었음 .

1. 화학제품과 회사에 관한 정보

1.1. 제품명

3M PN39527 SHOW CAR PASTE WAX

1.2. 제품의 권고 용도와 사용상의 제한

권장 사용

자동차 용

1.3. 공급자 정보

회사명 :

한국쓰리엠

주소 :

서울특별시 영등포구 의사당대로 82, 19 층 ( 우 )07321

전화 :

82-2-3771-4114

웹사이트

www.3m.com/kr

긴급전화번호 :

82-80-033-4114

2. 유해성 ∙ 위험성

2.1. 유해 . 위험성 분류

특정 표적장기 독성 (1 회 노출 ): 구분 3.

2.2. 예방조치문구를 포함한 경고 표지 항목 신호어

경고 !

그림문자

감탄 부호

그림문자

![image](data:image/png;base64,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)

유해▪위험문구

__________________________________________________________________________________________

페이지

: 1 의 14

>>> page_2

3M PN39527 SHOW CAR PASTE WAX

H336

졸음 또는 현기증을 일으킬 수 있음

예방조치 문구 예방 :

P261

분진 / 흄 / 가스 / 미스트 / 증기 / 스프레이의 흡입을 피하시오 . 옥외 또는 환기가 잘 되는 곳에서만 취급하시오 .

P271

대응 :

P304 + P340

흡입하면 신선한 공기가 있는 곳으로 옮기고 호흡하기 쉬운 자세를 유지 하시오 .

P312

불편함을 느끼면 의료기관 ( 의사 ) 의 진찰을 받으시오 .

저장 :

P403 + P233

용기는 환기가 잘 되는 곳에 단단히 밀폐하여 저장하시오 . 잠금장치가 있는 저장장소에 저장하시오 .

P405

폐기 :

P501

( 관련 법규에 명시된 내용에 따라 ) 내용물 / 용기를 폐기하시오 .

2.3. 유해성 ∙ 위험성 분류기준에 포함되지 않는 기타 유해성 ∙ 위험성

알려지지 않음 .

3. 구성성분의 명칭 및 함유량

이 제품의 물질은 혼합물로 구성

<table>
{"화학물질명": "Light Distillates - Hydrotreated", "관용명": "자료 없음 .", "카스 번호": "64742-47-8", "함유량 (%)": "60 - 70"},
{"화학물질명": "카나우바 왁스", "관용명": "자료 없음 .", "카스 번호": "8015-86-9", "함유량 (%)": "15 - 25"},
{"화학물질명": "SILICONE GREASE", "관용명": "DIMETHYLPOLYSILOXANE", "카스 번호": "63148-62-9", "함유량 (%)": "10 - 20"},
{"화학물질명": "MONTAN-WAX FATTY ACIDS, approx. C24-C34", "관용명": "자료 없음 .", "카스 번호": "68476-03-9", "함유량 (%)": "1 - 10"},
{"화학물질명": "Silicone Resin", "관용명": "자료 없음 .", "카스 번호": "104133-09-7", "함유량 (%)": "0.1 - 5"},
{"화학물질명": "CARNAUBA WAX, ETHOXYLATED PROPOXYLATED", "관용명": "자료 없음 .", "카스 번호": "85712-28-3", "함유량 (%)": "0.1 - 2"},
{"화학물질명": "ETHOXYLATED ALCOHOLS, C16-18", "관용명": "ETHOXYLATED CETOSTEARYL ALCOHOL", "카스 번호": "68439-49-6", "함유량 (%)": "0.1 - 2"}
</table>

4. 응급조치 요령

4.1. 응급조치 요령에 대한 설명

눈에 들어갔을 때 :

대량의 물로 세척 . 가능하면 콘택트렌즈를 제거하시오 . 계속 씻으시오 . 만약 증상이 지속된다면 치료 받을 것 .

피부에 접촉했을 때 :

비누와 물로 즉각 세척하시오 . 오염된 의복을 제거하고 재사용전 세척하시오 . 만약 증상이 발전된다면 , 치료

__________________________________________________________________________________________

>>> page_3

3M PN39527 SHOW CAR PASTE WAX

를 받으시오 .

흡입했을 때 :

신선한 공기를 쏘일 것 . 불편하다고 느끼면 , 치료받을 것 .

먹었을 때 :

입을 씻어낼 것 . 불편하다고 느끼면 , 치료를 받을 것 .

4.2. 가장 중요한 증상과 영향 , 급성 과 지연성

섹션 11.1 독성효과에 대한 정보를 보시오

4.3. 즉각적인 의료 행위 및 특별한 치료가 필요한 경우에 대한 지시사항

해당없음 .

5. 폭발 ∙ 화재시 대처방법

5.1. 적절한 ( 및 부적절한 ) 소화제

화재의 경우 : 물이나 폼과 같은 부식성 물질에 적합한 소화제를 사용할 것

5.2. 화학물질 혹은 혼합물로부터 생기는 특정 유해성 ( 예 , 연소시 발생 유해물질 )

이 제품에 내재하지 않음 .

5.3. 화재 진압 시 착용할 보호구 및 예방조치

화재 진압을위한 특별한 보호 조치는 없을 것으로 예상된다 .

6. 누출 사고 시 대처방법

6.1. 인체를 보호하기 위해 필요한 조치 사항 및 보호구

대피할 것 . 신선한 공기로 환기하시오 . 대량으로 유출되거나 , 밀폐된 공간에서 유출되었을 때 , 최적의 산 업위생 관행에 따라 기계적인 환기를 통해 분산시키거나 증기를 배출시켜야함 . 개인 보호 장비에 관해서는 물질안전보건자료 (MSDS) 의 8 번 항목을 참조하시오 .

6.2. 환경을 보호하기 위해 필요한 조치사항

환경으로 배출하지 마시오 .

6.3. 정화 또는 제거 방법

유출된 물질을 가능한 많이 모으시오 . 적합한 기관에 의해 수송이 승인된 밀폐 용기에 싣을 것 . 잔류물을 처리하시오 . 용기를 밀폐할 것 . 수거된 물질을 최대한 빨리 폐기물법에 따라 지정폐기물로 폐기하시오 .

7. 취급 및 저장방법

7.1. 안전취급요령

사방이 막힌 장소나 공기의 흐름이 거의 없거나 없는 장소에서 사용하지 말 것 . 어린이 손이 닿지 않는 곳 에 보관하시오 . 분진 · 흄 · 가스 · 미스트 · 증기 · 스프레이의 흡입을 피하시오 . 눈 , 피부 , 의복에 묻지 않도 록 하시오 . 이 제품을 사용할 때에는 먹거나 , 마시거나 흡연하지 마시오 . 취급 후에는 취급 부위를 철저히 씻으시오 . 작업장 밖으로 오염된 의복을 반출하지 마시오 . 다시 사용전 오염된 의복은 세척하시오 . 산화 기 ( 예 , 염소 , 크롬산등 ) 와의 접촉을 피할 것 .

7.2. 안전한 저장 방법 ( 피해야 할 조건을 포함함 )

__________________________________________________________________________________________

>>> page_4

3M PN39527 SHOW CAR PASTE WAX

환기가 잘 되는 곳에 보관할 것 . 단단하게 밀폐하여 저장할 것 . 열로부터 멀리 보관할 것 . 산화제로부터 멀 리 보관할 것 .

8. 노출방지 및 개인보호구

8.1. 화학물질의 노출기준 , 생물학적 노출기준 등

작업노출한계

작업노출한계치는 본 물질안전보건자료 (MSDS) 의 섹션 3 에 있는 어떠한 구성성분에 대해서도 없음

8.2. 적절한 공학적 관리

절단 , 분쇄 , 연마 , 기계조작을 위해서 적절한 국소 배기 시설을 제공하시오 . 먼지 , 연기 , 가스 , 안개 , 증 기 , 스프레이 등을 관리하거나 관련 노출 기준 이하의 공기부유물 노출을 관리하기 위해 일반적인 희석 환기 설비 또는 국소 배기 장치를 사용하시오 . 만일 환기가 충분하지 않은 경우 , 호흡기 보호 장비를 사용하시오 .

8.3 개인보호구 (PPE)

눈 / 얼굴 보호 :

눈 / 안면부의 보호를 위한 보호구의 선택 및 사용은 노출평가의 결과를 토대로 할 것 . 눈 / 안면부의 보호는 다 음 추천사항들을 따를 것 :

측면 커버가 부착된 보안경

손 보호

노출평가결과를 바탕으로 피부 접촉을 방지하기 위한 해당지역의 표준에 따라 허용된 장갑과 보호구를 선택 해서 사용하시오 . 노출 수준 , 화학물질 또는 혼합물의 농도 , 사용빈도 , 노출기간 , 극한 온도와 같은 물리적 조건 및 기타 사용 조건등을 근거로 선택하시오 . 적당하고 올바른 장갑과 보호복을 선택하기 위하여 장갑이 나 보호복 제조사에 문의하시오 .

추천된 장갑의 재질

:

니트릴고무

신체 보호

만약 이 제품이 노출이 더 높은 방식 ( 예를 들면 분무 , 고 스플래시 전위 등 ) 으로 사용된다면 , 보호 커버 올의 사용이 필요할 수 있다 노출 평가의 결과에 따라 접촉을 방지하기 위해 신체 보호를 선택하고 사용할 것 . 다음과 같은 보호복 재료가 추천됨 : 앞치마 ( 부분 보호복 ) -니트릴

호흡기보호 :

만약 배기가 과노출을 방지하기 부적절 하다면 호흡 보호구를 착용하시오 . 호흡기가 필요한 경우 노출평가 를 통해 결정할 수 있음 . 호흡기가 필요한 경우에 전체 호흡 보호 프로그램 (Full Respiratory Protection Program) 의 일부분으로 호흡기를 사용할 수 있음 . 흡입 노출을 저감하기 위해 노출평가의 결과를 토대로 호 흡기 종류 ( 타입 ) 들을 선택 할 수 있음 .

방진 겸용 유기화합물용 반면형 또는 전면형 방독 마스크

특성 적용을 위한 적합성에 대한 질문은 호홉용구 제작사와 상의하시오 .

9. 물리화학적 특성

9.1. 기본적인 물리화학적 특성에 대한 정보

__________________________________________________________________________________________

>>> page_5

3M PN39527 SHOW CAR PASTE WAX

외관 ( 물리적상태 )

고체

특정 물리적 형태 :

페이스트

색

옅은 노란색

냄새

코코넛향

냄새 역치

자료 없음 .

pH

자료 없음 .

녹는 점 / 어는 점

95 도

끓는 점 / 초기 끓는 점 / 끓는 범위

150 도

인화점 :

자료 없음 .

증발 속도

자료 없음 .

인화성 ( 고체 , 기체 )

분류되지 않음

인화 또는 폭발 범위 ( 하한 )

자료 없음 .

인화 또는 폭발 범위 ( 상한 )

자료 없음 .

증기압

자료 없음 .

증기 밀도

1  [ Ref Std: AIR=1]

비중 ( 밀도 )

자료 없음 .

상대 밀도

0.8309  [ Ref Std: WATER=1]

용해도 :

자료 없음 .

용해도 -non-water

자료 없음 .

n- 옥탄올 / 물 분배계수

자료 없음 .

자연발화 온도

자료 없음 .

분해 온도

자료 없음 .

점도 :

자료 없음 .

분자량

해당없음 .

퍼센트 휘발성

자료 없음 .

10. 안정성 및 반응성

10.1 반응성

본 물질은 특정 조건 하에 특정 물질들과 반응할수 있음 -이 섹션에서 첫머리를 참고할 것 .

10.2 화학적 안정성

안정함

10.3 유해 반응의 가능성

위험 폴리머화는 발생하지 않음

10.4 피해야 할 조건

스파크 또는 화염 열

10.5 피해야 할 물질

강산화제

10.6 분해 시 생성되는 유해물질

물질

조건

포름알데히드

특정화 되지 않음

__________________________________________________________________________________________

>>> page_6

3M PN39527 SHOW CAR PASTE WAX

일산화 탄소

특정화 되지 않음

이산화 탄소

특정화 되지 않음

11. 독성에 관한 정보

특정 구성성분의 분류가 적절한 근거에 의해 규정될 때 , 아래의 정보는 섹션 2 ( 유해성 위험성 ) 의 GHS 분류 와 일치하지 않을 수 있음 . 또한 , 구성성분의 독성 정보가 GHS 분류를 위한 역가치 이하의 함량이거나 , 구성 성분으로 인한 노출이 가능하지 않을 때 , 또는 구성성분 하나 단일물질의 독성 데이터는 제품 전체의 독성정 보가 아니므로 섹션 2 ( 유해성 위험성 ) 항목의 정보와 / 또는 신호어 및 노출 증상 등의 구분에 반영되지 않을 수 있음 .

11.1 노출 가능 경로 및 독성 영향에 대한 정보

노출증상

테스트 데이터나 구성성분에 대한 정보에 기초해서 이 물질은 다음의 건강 영향을 발생시킴

흡입했을 때 :

호흡기관 자극 : 기침 , 재채기 , 콧물 , 두통 , 목이 쉬거나 , 코와 목의 통증을 일으킬 수 있음 . 다음의 추가적인 건강영향을 초래

피부에 접촉했을 때 :

경도의 피부자극 : 국소 발적 , 부종 , 가려움 과 건조가 나타날 수 있다 . 알레르기성 피부 반응 : 발적 , 팽윤 , 수 포 및 가려움증이 나타날 수 있음 .

눈에 들어갔을 때 :

이 제품을 사용하는 동안 눈과 접촉시 심각한 자극은 예상되지 않음 . 절단 , 연마 , 사상이나 기계가동에 의해 발생한 먼지는 눈 자극을 일으킬 수 있음 . 눈이 충혈되거나 붓고 , 통증 , 눈물 , 그리고 흐릿하고 안개가 낀 것 처럼 보일 수 있음 .

섭취 :

위장관 자극 : 복통 , 위경련 , 구역질 , 구토와 설사 증상이 나타날 수 있음 . 다음의 추가적인 건강영향을 초래

추가적 건강 영향

1 회 노출의 표적장기 영향

중추신경계 억제 : 두통 , 현기증 , 졸음 , 근육불협응 , 구역질 , 반응시간 둔화 , 어눌한 말씨 , 어지러움 , 그리고 의 식불명의 증상을 일으킬 수 있음 .

독성 데이터

3 장의 구성성분의 명칭 및 함유량에는 기재되어 있지만 아래 표에 기재되어 있지 않으면 , 데이터가 없거나 분류를 위한 충분한 데이터가 없는 것임 .

<table>
{"이름": "제품 전체", "루트": "섭취", "종": "자료없 음", "값": "자료 없음 ; ATE 계산 >5,000 mg/kg"},
{"이름": "Light Distillates - Hydrotreated", "루트": "피부", "종": "토끼", "값": "LD50 > 3,160 mg/kg"},
{"이름": "Light Distillates - Hydrotreated", "루트": "흡입 - 먼지 / 미스트 (4 시간 )", "종": "랫트", "값": "LC50 > 3 mg/l"}
</table>

급성 독성

__________________________________________________________________________________________

>>> page_7

<table>
{"col_0": "3M PN39527 SHOW CAR PASTE WAX"}
</table>

<table>
{"col_0": "Light Distillates - Hydrotreated", "col_1": "섭취", "col_2": "랫트", "col_3": "LD50 > 5,000 mg/kg"},
{"col_0": "카나우바 왁스", "col_1": "피부", "col_2": "자료없 음", "col_3": "LD50 이상이 될 것이라 추정됨 5,000 mg/kg"},
{"col_0": "카나우바 왁스", "col_1": "섭취", "col_2": "랫트", "col_3": "LD50 > 8,800 mg/kg"},
{"col_0": "SILICONE GREASE", "col_1": "피부", "col_2": "토끼", "col_3": "LD50 > 19,400 mg/kg"},
{"col_0": "SILICONE GREASE", "col_1": "섭취", "col_2": "랫트", "col_3": "LD50 > 17,000 mg/kg"},
{"col_0": "MONTAN-WAX FATTY ACIDS, approx. C24-C34", "col_1": "피부", "col_2": "랫트", "col_3": "LD50 > 2,000 mg/kg"},
{"col_0": "MONTAN-WAX FATTY ACIDS, approx. C24-C34", "col_1": "섭취", "col_2": "랫트", "col_3": "LD50 > 15,000 mg/kg"},
{"col_0": "Silicone Resin", "col_1": "자료없음", "col_2": "자료없 음", "col_3": "자료가 없거나 분류를 위해서 충분치 않음"}
</table>

ATE= 급성독성예상치

피부 부식성 또는 자극성

<table>
{"제품 전체": "자료없음", "Light Distillates - Hydrotreated": "토끼", "카나우바 왁스": "전문가의 판단", "SILICONE GREASE": "토끼", "MONTAN-WAX FATTY ACIDS, approx. C24-C34": "토끼", "Silicone Resin": "자료없음", "CARNAUBA WAX, ETHOXYLATED PROPOXYLATED": "자료없음", "ETHOXYLATED ALCOHOLS, C16-18": "자료없음"},
{"제품 전체": "자료가 없거나 분류를 위해서 충분치 않음", "Light Distillates - Hydrotreated": "약한 자극제", "카나우바 왁스": "중요한 자극 없음", "SILICONE GREASE": "중요한 자극 없음", "MONTAN-WAX FATTY ACIDS, approx. C24-C34": "중요한 자극 없음", "Silicone Resin": "자료가 없거나 분류를 위해서 충분치 않음", "CARNAUBA WAX, ETHOXYLATED PROPOXYLATED": "자료가 없거나 분류를 위해서 충분치 않음", "ETHOXYLATED ALCOHOLS, C16-18": "자료가 없거나 분류를 위해서 충분치 않음"}
</table>

심한 눈 손상 또는 자극성

<table>
{"col_0": "이름", "col_1": "종", "col_2": "값"},
{"col_0": "제품 전체", "col_1": "자료없음", "col_2": "자료가 없거나 분류를 위해서 충분치 않음"},
{"col_0": "Light Distillates - Hydrotreated", "col_1": "토끼", "col_2": "약한 자극제"},
{"col_0": "카나우바 왁스", "col_1": "전문가의 판단", "col_2": "중요한 자극 없음"},
{"col_0": "SILICONE GREASE", "col_1": "토끼", "col_2": "중요한 자극 없음"},
{"col_0": "MONTAN-WAX FATTY ACIDS, approx. C24-C34", "col_1": "토끼", "col_2": "중요한 자극 없음"},
{"col_0": "Silicone Resin", "col_1": "자료없음", "col_2": "자료가 없거나 분류를 위해서 충분치 않음"},
{"col_0": "CARNAUBA WAX, ETHOXYLATED PROPOXYLATED", "col_1": "자료없음", "col_2": "자료가 없거나 분류를 위해서 충분치 않음"},
{"col_0": "ETHOXYLATED ALCOHOLS, C16-18", "col_1": "자료없음", "col_2": "자료가 없거나 분류를 위해서 충분치 않음"}
</table>

피부 과민성

<table>
{"제품 전체": "자료없음", "Light Distillates - Hydrotreated": "기니피그", "카나우바 왁스": "자료없음", "SILICONE GREASE": "자료없음", "MONTAN-WAX FATTY ACIDS, approx. C24-C34": "마우스", "Silicone Resin": "자료없음", "CARNAUBA WAX, ETHOXYLATED PROPOXYLATED": "자료없음", "ETHOXYLATED ALCOHOLS, C16-18": "자료없음"},
{"제품 전체": "자료가 없거나 분류를 위해서 충분치 않음", "Light Distillates - Hydrotreated": "분류되지 않음", "카나우바 왁스": "자료가 없거나 분류를 위해서 충분치 않음", "SILICONE GREASE": "자료가 없거나 분류를 위해서 충분치 않음", "MONTAN-WAX FATTY ACIDS, approx. C24-C34": "분류되지 않음", "Silicone Resin": "자료가 없거나 분류를 위해서 충분치 않음", "CARNAUBA WAX, ETHOXYLATED PROPOXYLATED": "자료가 없거나 분류를 위해서 충분치 않음", "ETHOXYLATED ALCOHOLS, C16-18": "자료가 없거나 분류를 위해서 충분치 않음"}
</table>

광민감성

<table>
{"col_0": "이름", "col_1": "종", "col_2": "값"},
{"col_0": "제품 전체", "col_1": "자료없음", "col_2": "자료가 없거나 분류를 위해서 충분치 않음"},
{"col_0": "Light Distillates - Hydrotreated", "col_1": "자료없음", "col_2": "자료가 없거나 분류를 위해서 충분치 않음"},
{"col_0": "카나우바 왁스", "col_1": "자료없음", "col_2": "자료가 없거나 분류를 위해서 충분치 않음"},
{"col_0": "SILICONE GREASE", "col_1": "자료없음", "col_2": "자료가 없거나 분류를 위해서 충분치 않음"},
{"col_0": "MONTAN-WAX FATTY ACIDS, approx. C24-C34", "col_1": "자료없음", "col_2": "자료가 없거나 분류를 위해서 충분치 않음"}
</table>

__________________________________________________________________________________________

>>> page_8

<table>
{"col_0": "3M PN39527 SHOW CAR PASTE WAX"}
</table>

<table>
{"CARNAUBA WAX, ETHOXYLATED PROPOXYLATED": "자료없음", "ETHOXYLATED ALCOHOLS, C16-18": "자료없음"},
{"CARNAUBA WAX, ETHOXYLATED PROPOXYLATED": "자료가 없거나 분류를 위해서 충분치 않음", "ETHOXYLATED ALCOHOLS, C16-18": "자료가 없거나 분류를 위해서 충분치 않음"}
</table>

호흡기 과민성

<table>
{"col_0": "이름", "col_1": "종", "col_2": "값"},
{"col_0": "제품 전체", "col_1": "자료없음", "col_2": "자료가 없거나 분류를 위해서 충분치 않음"},
{"col_0": "Light Distillates - Hydrotreated", "col_1": "자료없음", "col_2": "자료가 없거나 분류를 위해서 충분치 않음"},
{"col_0": "카나우바 왁스", "col_1": "자료없음", "col_2": "자료가 없거나 분류를 위해서 충분치 않음"},
{"col_0": "SILICONE GREASE", "col_1": "자료없음", "col_2": "자료가 없거나 분류를 위해서 충분치 않음"},
{"col_0": "MONTAN-WAX FATTY ACIDS, approx. C24-C34", "col_1": "자료없음", "col_2": "자료가 없거나 분류를 위해서 충분치 않음"},
{"col_0": "Silicone Resin", "col_1": "자료없음", "col_2": "자료가 없거나 분류를 위해서 충분치 않음"},
{"col_0": "CARNAUBA WAX, ETHOXYLATED PROPOXYLATED", "col_1": "자료없음", "col_2": "자료가 없거나 분류를 위해서 충분치 않음"},
{"col_0": "ETHOXYLATED ALCOHOLS, C16-18", "col_1": "자료없음", "col_2": "자료가 없거나 분류를 위해서 충분치 않음"}
</table>

생식세포 변이원성

<table>
{"제품 전체": "자료없음", "Light Distillates - Hydrotreated": "In Vitro", "카나우바 왁스": "자료없음", "SILICONE GREASE": "자료없음", "MONTAN-WAX FATTY ACIDS, approx. C24-C34": "In Vitro", "Silicone Resin": "자료없음", "CARNAUBA WAX, ETHOXYLATED PROPOXYLATED": "자료없음", "ETHOXYLATED ALCOHOLS, C16-18": "자료없음"},
{"제품 전체": "자료가 없거나 분류를 위해서 충분치 않음", "Light Distillates - Hydrotreated": "변이원성 아님", "카나우바 왁스": "자료가 없거나 분류를 위해서 충분치 않음", "SILICONE GREASE": "자료가 없거나 분류를 위해서 충분치 않음", "MONTAN-WAX FATTY ACIDS, approx. C24-C34": "변이원성 아님", "Silicone Resin": "자료가 없거나 분류를 위해서 충분치 않음", "CARNAUBA WAX, ETHOXYLATED PROPOXYLATED": "자료가 없거나 분류를 위해서 충분치 않음", "ETHOXYLATED ALCOHOLS, C16-18": "자료가 없거나 분류를 위해서 충분치 않음"}
</table>

발암성

<table>
{"이름": "제품 전체", "루트": "자료없음", "종": "자료없 음", "값": "자료가 없거나 분류를 위해서 충분치 않음"},
{"이름": "Light Distillates - Hydrotreated", "루트": "피부", "종": "마우스", "값": "긍정적인 결과가 있지만 , 그 데이터는 분류를 위해 충분하지 않다"},
{"이름": "카나우바 왁스", "루트": "자료없음", "종": "자료없 음", "값": "자료가 없거나 분류를 위해서 충분치 않음"},
{"이름": "SILICONE GREASE", "루트": "자료없음", "종": "자료없 음", "값": "자료가 없거나 분류를 위해서 충분치 않음"},
{"이름": "MONTAN-WAX FATTY ACIDS, approx. C24-C34", "루트": "자료없음", "종": "자료없 음", "값": "자료가 없거나 분류를 위해서 충분치 않음"},
{"이름": "Silicone Resin", "루트": "자료없음", "종": "자료없 음", "값": "자료가 없거나 분류를 위해서 충분치 않음"},
{"이름": "CARNAUBA WAX, ETHOXYLATED PROPOXYLATED", "루트": "자료없음", "종": "자료없 음", "값": "자료가 없거나 분류를 위해서 충분치 않음"},
{"이름": "ETHOXYLATED ALCOHOLS, C16-18", "루트": "자료없음", "종": "자료없 음", "값": "자료가 없거나 분류를 위해서 충분치 않음"}
</table>

생식독성

생식 , 발생 효과

<table>
{"이름": "제품 전체", "루트": "자료없음", "값": "자료가 없거나 분류를 위해서 충분 치 않음", "종": "자료없음", "시험결과": "자료없음", "노출 정도": "자료없음"},
{"이름": "Light Distillates - Hydrotreated", "루트": "자료없음", "값": "자료가 없거나 분류를 위해서 충분 치 않음", "종": "자료없음", "시험결과": "자료없음", "노출 정도": "자료없음"},
{"이름": "카나우바 왁스", "루트": "자료없음", "값": "자료가 없거나 분류를 위해서 충분 치 않음", "종": "자료없음", "시험결과": "자료없음", "노출 정도": "자료없음"}
</table>

__________________________________________________________________________________________

>>> page_9

3M PN39527 SHOW CAR PASTE WAX

<table>
{"col_0": "SILICONE GREASE", "col_1": "자료없음", "col_2": "자료가 없거나 분류를 위해서 충분 치 않음", "col_3": "자료없음", "col_4": "자료없음", "col_5": "자료없음"},
{"col_0": "MONTAN-WAX FATTY ACIDS, approx. C24-C34", "col_1": "섭취", "col_2": "암컷의 생식에 대한 분류가 데이터 가 없음", "col_3": "랫트", "col_4": "NOAEL 1,000 mg/kg/day", "col_5": "premating into lactation"},
{"col_0": "MONTAN-WAX FATTY ACIDS, approx. C24-C34", "col_1": "섭취", "col_2": "수컷의 생식에 대한 분류가 데이터 가 없음", "col_3": "랫트", "col_4": "NOAEL 1,000 mg/kg/day", "col_5": "28 일"},
{"col_0": "MONTAN-WAX FATTY ACIDS, approx. C24-C34", "col_1": "섭취", "col_2": "발생에 대한 분류 데이터가 없음", "col_3": "랫트", "col_4": "NOAEL 1,000 mg/kg/day", "col_5": "premating into lactation"},
{"col_0": "Silicone Resin", "col_1": "자료없음", "col_2": "자료가 없거나 분류를 위해서 충분 치 않음", "col_3": "자료없음", "col_4": "자료없음", "col_5": "자료없음"},
{"col_0": "CARNAUBA WAX, ETHOXYLATED PROPOXYLATED", "col_1": "자료없음", "col_2": "자료가 없거나 분류를 위해서 충분 치 않음", "col_3": "자료없음", "col_4": "자료없음", "col_5": "자료없음"},
{"col_0": "ETHOXYLATED ALCOHOLS, C16-18", "col_1": "자료없음", "col_2": "자료가 없거나 분류를 위해서 충분 치 않음", "col_3": "자료없음", "col_4": "자료없음", "col_5": "자료없음"}
</table>

수유

<table>
{"이름": "제품 전체", "루트": "자료없음", "종": "자료없 음", "값": "자료가 없거나 분류를 위해서 충분치 않음"},
{"이름": "Light Distillates - Hydrotreated", "루트": "자료없음", "종": "자료없 음", "값": "자료가 없거나 분류를 위해서 충분치 않음"},
{"이름": "카나우바 왁스", "루트": "자료없음", "종": "자료없 음", "값": "자료가 없거나 분류를 위해서 충분치 않음"},
{"이름": "SILICONE GREASE", "루트": "자료없음", "종": "자료없 음", "값": "자료가 없거나 분류를 위해서 충분치 않음"},
{"이름": "MONTAN-WAX FATTY ACIDS, approx. C24-C34", "루트": "자료없음", "종": "자료없 음", "값": "자료가 없거나 분류를 위해서 충분치 않음"},
{"이름": "Silicone Resin", "루트": "자료없음", "종": "자료없 음", "값": "자료가 없거나 분류를 위해서 충분치 않음"},
{"이름": "CARNAUBA WAX, ETHOXYLATED PROPOXYLATED", "루트": "자료없음", "종": "자료없 음", "값": "자료가 없거나 분류를 위해서 충분치 않음"},
{"이름": "ETHOXYLATED ALCOHOLS, C16-18", "루트": "자료없음", "종": "자료없 음", "값": "자료가 없거나 분류를 위해서 충분치 않음"}
</table>

표적장기효과

특정 표적장기 독성 -1 회 노출

<table>
{"이름": "제품 전체", "루트": "자료없음", "표적장기효과": "자료없음", "값": "자료가 없거나 분류를 위해서 충분치 않음", "종": "자료없 음", "시험결과": "자료없음", "노출 정도": "0"},
{"이름": "Light Distillates - Hydrotreated", "루트": "흡입", "표적장기효과": "중추신경계 억제", "값": "졸음 또는 현기증을 일으킬 수 있음", "종": "인간과 동물", "시험결과": "NOAEL 자 료 없음 .", "노출 정도": "자료없음"},
{"이름": "Light Distillates - Hydrotreated", "루트": "흡입", "표적장기효과": "호흡 자극", "값": "긍정적인 결과가 있지만 , 그 데이터는 분류를 위해 충분하 지 않다", "종": "", "시험결과": "NOAEL 자 료 없음 .", "노출 정도": "자료없음"},
{"이름": "Light Distillates - Hydrotreated", "루트": "섭취", "표적장기효과": "중추신경계 억제", "값": "졸음 또는 현기증을 일으킬 수 있음", "종": "전문가 의 판단", "시험결과": "NOAEL 불 가능", "노출 정도": "자료없음"},
{"이름": "카나우바 왁스", "루트": "자료없음", "표적장기효과": "자료없음", "값": "자료가 없거나 분류를 위해서 충분치 않음", "종": "자료없 음", "시험결과": "자료없음", "노출 정도": "0"},
{"이름": "SILICONE GREASE", "루트": "자료없음", "표적장기효과": "자료없음", "값": "자료가 없거나 분류를 위해서 충분치 않음", "종": "자료없 음", "시험결과": "자료없음", "노출 정도": "0"},
{"이름": "MONTAN-WAX FATTY ACIDS, approx. C24-C34", "루트": "자료없음", "표적장기효과": "자료없음", "값": "자료가 없거나 분류를 위해서 충분치 않음", "종": "자료없 음", "시험결과": "자료없음", "노출 정도": "0"},
{"이름": "Silicone Resin", "루트": "자료없음", "표적장기효과": "자료없음", "값": "자료가 없거나 분류를 위해서 충분치 않음", "종": "자료없 음", "시험결과": "자료없음", "노출 정도": "0"},
{"이름": "CARNAUBA WAX, ETHOXYLATED", "루트": "자료없음", "표적장기효과": "자료없음", "값": "자료가 없거나 분류를 위해서 충분치 않음", "종": "자료없 음", "시험결과": "자료없음", "노출 정도": "0"}
</table>

__________________________________________________________________________________________

>>> page_10

<table>
{"col_0": "3M PN39527 SHOW CAR PASTE WAX"}
</table>

<table>
{"ETHOXYLATED": "자료없음", "ALCOHOLS, C16-18": ""},
{"ETHOXYLATED": "자료없음", "ALCOHOLS, C16-18": ""},
{"ETHOXYLATED": "자료가 없거나 분류를 위해서", "ALCOHOLS, C16-18": "충분치 않음"},
{"ETHOXYLATED": "자료없", "ALCOHOLS, C16-18": "음"},
{"ETHOXYLATED": "자료없음", "ALCOHOLS, C16-18": ""},
{"ETHOXYLATED": "0", "ALCOHOLS, C16-18": ""}
</table>

특정 표적장기독성 -반복노출

<table>
{"이름": "제품 전체", "루트": "자료없음", "표적장기효과": "자료없음", "값": "자료가 없거나 분류를 위해서 충분치 않음", "종": "자료없 음", "시험결과": "자료없음", "노출 정도": "0"},
{"이름": "Light Distillates - Hydrotreated", "루트": "자료없음", "표적장기효과": "자료없음", "값": "자료가 없거나 분류를 위해서 충분치 않음", "종": "자료없 음", "시험결과": "자료없음", "노출 정도": "0"},
{"이름": "카나우바 왁스", "루트": "자료없음", "표적장기효과": "자료없음", "값": "자료가 없거나 분류를 위해서 충분치 않음", "종": "자료없 음", "시험결과": "자료없음", "노출 정도": "0"},
{"이름": "SILICONE GREASE", "루트": "자료없음", "표적장기효과": "자료없음", "값": "자료가 없거나 분류를 위해서 충분치 않음", "종": "자료없 음", "시험결과": "자료없음", "노출 정도": "0"},
{"이름": "MONTAN-WAX FATTY ACIDS, approx. C24-C34", "루트": "자료없음", "표적장기효과": "자료없음", "값": "자료가 없거나 분류를 위해서 충분치 않음", "종": "자료없 음", "시험결과": "자료없음", "노출 정도": "0"},
{"이름": "Silicone Resin", "루트": "자료없음", "표적장기효과": "자료없음", "값": "자료가 없거나 분류를 위해서 충분치 않음", "종": "자료없 음", "시험결과": "자료없음", "노출 정도": "0"},
{"이름": "CARNAUBA WAX, ETHOXYLATED PROPOXYLATED", "루트": "자료없음", "표적장기효과": "자료없음", "값": "자료가 없거나 분류를 위해서 충분치 않음", "종": "자료없 음", "시험결과": "자료없음", "노출 정도": "0"},
{"이름": "ETHOXYLATED ALCOHOLS, C16-18", "루트": "자료없음", "표적장기효과": "자료없음", "값": "자료가 없거나 분류를 위해서 충분치 않음", "종": "자료없 음", "시험결과": "자료없음", "노출 정도": "0"}
</table>

흡인 유해성

<table>
{"이름": "제품 전체", "값": "자료가 없거나 분류를 위해서 충분치 않음"},
{"이름": "Light Distillates - Hydrotreated", "값": "흡인 유해성"},
{"이름": "카나우바 왁스", "값": "자료가 없거나 분류를 위해서 충분치 않음"},
{"이름": "SILICONE GREASE", "값": "자료가 없거나 분류를 위해서 충분치 않음"},
{"이름": "MONTAN-WAX FATTY ACIDS, approx. C24-C34", "값": "자료가 없거나 분류를 위해서 충분치 않음"},
{"이름": "Silicone Resin", "값": "자료가 없거나 분류를 위해서 충분치 않음"},
{"이름": "CARNAUBA WAX, ETHOXYLATED PROPOXYLATED", "값": "자료가 없거나 분류를 위해서 충분치 않음"},
{"이름": "ETHOXYLATED ALCOHOLS, C16-18", "값": "자료가 없거나 분류를 위해서 충분치 않음"}
</table>

추가 독성정보가 필요하면 본 물질안전보건자료 (MSDS) 첫페이지에 있는 주소나 전화번호로 연락하시오

12. 환경에 미치는 영향

특정 구성성분의 분류가 적절한 근거에 의해 규정될 때 , 아래의 정보는 섹션 2 ( 유해성 위험성 ) 의 GHS 분류 와 일치하지 않을 수 있음 . 요청에 따라 섹션 2 ( 유해성 위험성 ) 에서의 물질의 분류와 관련된 추가적인 정보 는 제공 가능함 . 또한 , 구성성분의 환경에 미치는 영향은 GHS 분류를 위한 역가치 이하의 함량이거나 , 구성 성분으로 인한 노출이 가능하지 않을 때 , 또는 구성성분 하나 단일물질의 독성 데이터는 제품 전체의 독성정 보가 아니므로 섹션 2 ( 유해성 위험성 ) 항목의 정보와 / 또는 신호어 및 노출 증상 등의 구분에 반영되지 않을 수 있음 .

12.1 생태독성

급성 수생 위험성 :

수생생물에 급성 독성이 없음 (GHS 분류 기준 )

만성 수생 위험성 :

GHS 분류에 의해 수생생물에 만성독성없음

<table>
{"col_0": "재료", "col_1": "유기체", "col_2": "타입", "col_3": "노출", "col_4": "테스트 종점", "col_5": "시험결과"}
</table>

__________________________________________________________________________________________

>>> page_11

3M PN39527 SHOW CAR PASTE WAX

<table>
{"col_0": "제품 전체", "col_1": "자료없음", "col_2": "자료가 없거나 분류 를 위해서 충분치 않음 자료없음", "col_3": "자료없음", "col_4": "자료없음"}
</table>

<table>
{"재료": "Silicone Resin", "Cas #": "104133-09-7", "유기체": "자료없음", "타입": "자료가 없거나 분류를 위해서 충분치 않음", "노출": "자료없음", "테스트 종점": "자료없음", "시험결과": "자료없음"},
{"재료": "SILICONE GREASE", "Cas #": "63148-62-9", "유기체": "자료없음", "타입": "자료가 없거나 분류를 위해서 충분치 않음", "노출": "자료없음", "테스트 종점": "자료없음", "시험결과": "자료없음"},
{"재료": "Light Distillates - Hydrotreated", "Cas #": "64742-47-8", "유기체": "녹조류", "타입": "추정됨", "노출": "72 시간", "테스트 종점": "효과 농도 50%", "시험결과": "1 mg/l"},
{"재료": "Light Distillates - Hydrotreated", "Cas #": "64742-47-8", "유기체": "녹조류", "타입": "추정됨", "노출": "72 시간", "테스트 종점": "유효수준 관찰되지 않음", "시험결과": "1 mg/l"},
{"재료": "Light Distillates - Hydrotreated", "Cas #": "64742-47-8", "유기체": "무지개 송어", "타입": "추정됨", "노출": "96 시간", "테스트 종점": "50% 치사량", "시험결과": "2 mg/l"},
{"재료": "Light Distillates - Hydrotreated", "Cas #": "64742-47-8", "유기체": "물벼룩", "타입": "추정됨", "노출": "21 일", "테스트 종점": "유효수준 관찰되지 않음", "시험결과": "0.48 mg/l"},
{"재료": "Light Distillates - Hydrotreated", "Cas #": "64742-47-8", "유기체": "물벼룩", "타입": "추정됨", "노출": "48 시간", "테스트 종점": "유효수준 50%", "시험결과": "1.4 mg/l"},
{"재료": "ETHOXYLATED ALCOHOLS, C16-18", "Cas #": "68439-49-6", "유기체": "자료없음", "타입": "자료가 없거나 분류를 위해서 충분치 않음", "노출": "자료없음", "테스트 종점": "자료없음", "시험결과": "자료없음"},
{"재료": "MONTAN-WAX FATTY ACIDS, approx. C24-C34", "Cas #": "68476-03-9", "유기체": "제브라피쉬", "타입": "실험", "노출": "96 시간", "테스트 종점": "치사농도 50%", "시험결과": ">500 mg/l"},
{"재료": "카나우바 왁스", "Cas #": "8015-86-9", "유기체": "자료없음", "타입": "자료가 없거나 분류를 위해서 충분치 않음", "노출": "자료없음", "테스트 종점": "자료없음", "시험결과": "자료없음"},
{"재료": "CARNAUBA WAX, ETHOXYLATED PROPOXYLATED", "Cas #": "85712-28-3", "유기체": "자료없음", "타입": "자료가 없거나 분류를 위해서 충분치 않음", "노출": "자료없음", "테스트 종점": "자료없음", "시험결과": "자료없음"}
</table>

12.2. 잔류성 및 분해성

<table>
{"재료": "제품 전체", "CAS No.": "None", "테스트 타입": "자료가 없거나 분 류를 위해서 충분 치 않음", "지속기간": "자료없음", "연구 방식": "자료없음", "시험결과": "자료없음", "방법": "자료없음"},
{"재료": "Silicone Resin", "CAS No.": "104133-09-7", "테스트 타입": "자료가 없거나 분 류를 위해서 충분 치 않음", "지속기간": "자료없음", "연구 방식": "자료없음", "시험결과": "자료없음", "방법": "자료없음"},
{"재료": "SILICONE GREASE", "CAS No.": "63148-62-9", "테스트 타입": "Data not availbl- insufficient", "지속기간": "자료없음", "연구 방식": "자료없음", "시험결과": "N/A", "방법": "자료없음"},
{"재료": "Light Distillates - Hydrotreated", "CAS No.": "64742-47-8", "테스트 타입": "Data not availbl- insufficient", "지속기간": "자료없음", "연구 방식": "자료없음", "시험결과": "N/A", "방법": "자료없음"},
{"재료": "ETHOXYLATED ALCOHOLS, C16-18", "CAS No.": "68439-49-6", "테스트 타입": "실험 Biodegradation", "지속기간": "28 일", "연구 방식": "이산화 탄소 진 화", "시험결과": "85.3 %weight", "방법": "OECD 301B - Mod. Sturm or CO2"},
{"재료": "MONTAN-WAX FATTY ACIDS, approx. C24-C34", "CAS No.": "68476-03-9", "테스트 타입": "Data not availbl- insufficient", "지속기간": "자료없음", "연구 방식": "자료없음", "시험결과": "N/A", "방법": "자료없음"},
{"재료": "카나우바 왁스", "CAS No.": "8015-86-9", "테스트 타입": "추정됨 Biodegradation", "지속기간": "28 일", "연구 방식": "이산화 탄소 진 화", "시험결과": "96 %weight", "방법": "OECD 301B - Mod. Sturm or CO2"},
{"재료": "CARNAUBA WAX, ETHOXYLATED PROPOXYLATED", "CAS No.": "85712-28-3", "테스트 타입": "Data not availbl- insufficient", "지속기간": "자료없음", "연구 방식": "자료없음", "시험결과": "N/A", "방법": "자료없음"}
</table>

12.3. 생물 농축성 ( 농축가능성 )

__________________________________________________________________________________________

>>> page_12

3M PN39527 SHOW CAR PASTE WAX

<table>
{"재료": "제품 전체", "CAS No.": "None", "테스트 타입": "자료가 없거나 분 류를 위해서 충분 치 않음", "지속기간": "자료없음", "연구 방식": "자료없음", "시험결과": "자료없음", "방법": "자료없음"},
{"재료": "Silicone Resin", "CAS No.": "104133-09-7", "테스트 타입": "자료가 없거나 분 류를 위해서 충분 치 않음", "지속기간": "자료없음", "연구 방식": "자료없음", "시험결과": "자료없음", "방법": "자료없음"},
{"재료": "SILICONE GREASE", "CAS No.": "63148-62-9", "테스트 타입": "자료가 없거나 분 류를 위해서 충분 치 않음", "지속기간": "자료없음", "연구 방식": "자료없음", "시험결과": "N/A", "방법": "자료없음"},
{"재료": "Light Distillates - Hydrotreated", "CAS No.": "64742-47-8", "테스트 타입": "자료가 없거나 분 류를 위해서 충분 치 않음", "지속기간": "자료없음", "연구 방식": "자료없음", "시험결과": "N/A", "방법": "자료없음"},
{"재료": "ETHOXYLATED ALCOHOLS, C16-18", "CAS No.": "68439-49-6", "테스트 타입": "실험 BCF - Fathead Mi", "지속기간": "72 시간", "연구 방식": "생축적성 인자", "시험결과": "387.5", "방법": "다른 방법"},
{"재료": "MONTAN-WAX FATTY ACIDS, approx. C24-C34", "CAS No.": "68476-03-9", "테스트 타입": "자료가 없거나 분 류를 위해서 충분 치 않음", "지속기간": "자료없음", "연구 방식": "자료없음", "시험결과": "N/A", "방법": "자료없음"},
{"재료": "카나우바 왁스", "CAS No.": "8015-86-9", "테스트 타입": "추정됨 Bioconcentration", "지속기간": "자료없음", "연구 방식": "생축적성 인자", "시험결과": "7.4", "방법": "Est: 생물농축 계수"},
{"재료": "CARNAUBA WAX, ETHOXYLATED PROPOXYLATED", "CAS No.": "85712-28-3", "테스트 타입": "자료가 없거나 분 류를 위해서 충분 치 않음", "지속기간": "자료없음", "연구 방식": "자료없음", "시험결과": "N/A", "방법": "자료없음"}
</table>

12.4. 토양 이동성

자료없음 . 상세한 사항은 제조사에 문의하시오 .

12.5. 기타 유해 영향

<table>
{"재료": "제품 전체", "CAS No.": "없음", "오존층 파괴 가능성": "자료가 없거나 분류를 위해서 충분치 않음", "지구 온난화 가능성": "자료가 없거나 분류를 위해서 충분치 않음"},
{"재료": "Silicone Resin", "CAS No.": "104133-09-7", "오존층 파괴 가능성": "자료가 없거나 분류를 위해서 충분치 않음", "지구 온난화 가능성": "자료가 없거나 분류를 위해서 충분치 않음"},
{"재료": "SILICONE GREASE", "CAS No.": "63148-62-9", "오존층 파괴 가능성": "자료가 없거나 분류를 위해서 충분치 않음", "지구 온난화 가능성": "자료가 없거나 분류를 위해서 충분치 않음"},
{"재료": "Light Distillates - Hydrotreated", "CAS No.": "64742-47-8", "오존층 파괴 가능성": "자료가 없거나 분류를 위해서 충분치 않음", "지구 온난화 가능성": "자료가 없거나 분류를 위해서 충분치 않음"},
{"재료": "ETHOXYLATED ALCOHOLS, C16-18", "CAS No.": "68439-49-6", "오존층 파괴 가능성": "자료가 없거나 분류를 위해서 충분치 않음", "지구 온난화 가능성": "자료가 없거나 분류를 위해서 충분치 않음"},
{"재료": "MONTAN-WAX FATTY ACIDS, approx. C24-C34", "CAS No.": "68476-03-9", "오존층 파괴 가능성": "자료가 없거나 분류를 위해서 충분치 않음", "지구 온난화 가능성": "자료가 없거나 분류를 위해서 충분치 않음"},
{"재료": "카나우바 왁스", "CAS No.": "8015-86-9", "오존층 파괴 가능성": "자료가 없거나 분류를 위해서 충분치 않음", "지구 온난화 가능성": "자료가 없거나 분류를 위해서 충분치 않음"},
{"재료": "CARNAUBA WAX, ETHOXYLATED PROPOXYLATED", "CAS No.": "85712-28-3", "오존층 파괴 가능성": "자료가 없거나 분류를 위해서 충분치 않음", "지구 온난화 가능성": "자료가 없거나 분류를 위해서 충분치 않음"}
</table>

13. 폐기시 주의사항

13.1. 폐기 방법

( 관련 법규에 명시된 내용에 따라 ) 내용물 / 용기를 폐기하시오 .

13. 2. 폐기시 고려사항

__________________________________________________________________________________________

>>> page_13

3M PN39527 SHOW CAR PASTE WAX

허가된 폐기물 소각장에서 소각하시오 . 적절한 파괴는 소각 과정에서 추가 연료의 사용이 필요하다 . 폐기 대 체로써 , 허용되는 허가된 폐기물처리시설을 사용함 . 적절한 폐기물 법규에 의해 정의되지 않았을 경우 운반 과 위험화학물질 ( 적절한 규제에 따라 위험물로 분류되는 화학물질 / 혼합물 / 조제물 ) 을 다루기 위해 사용된 빈 용기는 위험폐기물로서 고려되어 보관되고 다루어져서 폐기되어져야 한다 .

14. 운송에 필요한 정보

국제규제

UN 번호 :

해당없음 .

UN 적정선적명 :

해당없음 .

운송에서의 위험성 등급 (IMO):

해당없음 .

운송 분류 (IATA):

해당없음 .

용기 ( 포장 ) 등급 :

해당없음 .

해양오염물질 :

해당없음 .

사용자가 운송 또는 운송 수단에 관련해 알 필요가 있거나 필요한 특별한 안전 대책 : 해당없음 .

15. 법적 규제현황

15.1. 안전 , 건강 , 환경 규제 / 물질 또는 혼합물 특이적인 등록

글로벌 인벤토리 상태

자세한 사항은 한국쓰리엠에 문의하시오 . 이 제품은 새로운 화학 물질의 환경 관리에 관한 조치를 준수한 다 . 모든 성분은 중국 IECSC 규정을 준수하고 있거나 면제 대상이다 . 자세한 사항은 한국쓰리엠에 문의하시오 .

이 제품의 구성 성분들은 다음과 같은 법적 규제사항을 따르고 있음 .

화학물질관리법 :

모든 성분은 기존화학 물질에 해당함

산업안전보건법 :

이 제품은 작업환경측정 대상 유해인자에 해당하는 화학물질을 포함하고 있음

산업안전보건법

이

제품은 특수건강진단 대상 유해인자에 해당하는 화학물질을 포함하고 있음

위험물안전관리법 :

자세한 사항은 한국쓰리엠 ( 주 ) 에 문의하시오 .

폐기물관리법 :

지정 폐기물

기타 국내 및 외국법에 의한 규제 :

해당 없음 .

16. 그 밖의 참고사항

16.1. 자료의 출처

16.2. 최초 작성일자 : 자료 없음 .

16.3. 개정 횟수 및 최종 개정일자 :

개정 횟수 : 자료 없음 .

최종 개정일자 :2020/03/10

16.4. 기타 : 해당없음 .

면책조항 : 본 물질안전보건자료 (MSDS) 상에 있는 정보는 당사의 경험을 기반으로 하며 발행일시의 가장 정확 한 지식들을 토대로 작성되었으나 , 당사는 본 물질안전보건자료의 사용에 따른 어떠한 손실 , 피해 혹은 부상 등에 대해 어떤 법적 책임 ( 국내 관련법에 의한 요구사항을 제외한 ) 을 지지 않음 . 본 물질안전보건자료의 정 보는 기재된 해당 제품의 사용 목적 이외에 다른 용도로 사용되거나 다른 물질과 함께 ( 섞어서 ) 사용하는 것

__________________________________________________________________________________________

>>> page_14

3M PN39527 SHOW CAR PASTE WAX

에 대해서 유효하지 않을 수 있음 . 이러한 이유들로 , 고객이 본 제품에 대해서 고객의 의도된 사용 목적에 따라 제품의 적합성을 직접 테스트하는 것은 매우 중요함 .

한국쓰리엠의 물질안전보건자료 (MSDS) 는 www.3m.com/kr 에서 확인 가능함 .

__________________________________________________________________________________________
            """
        }
    ]

    result = collection.insert_many(mock_documents)
    print(f"Mock 데이터 {len(result.inserted_ids)}개 삽입 완료")

    return mock_documents


def verify_mock_data(mongodb):
    """
    생성된 Mock Markdown 문서를 조회·요약 출력하여 정상 삽입 여부를 확인합니다.

    document_id가 'MOCK_'로 시작하는 문서를 대상으로 식별자와 파일명을 출력하고,
    본문(content) 첫 100자를 미리보기로 제공합니다. 콘솔 확인용 유틸리티입니다.

    Args:
        mongodb (pymongo.database.Database): 조회 대상 MongoDB 데이터베이스 핸들.
            - 사용 컬렉션: 'markdown_collection'  # 생성 함수의 컬렉션명과 다른 점에 유의

    Returns:
        None

    동작 개요:
        1) 'markdown_collection'에서 document_id 정규식 '^MOCK_'로 문서를 조회합니다.
        2) 각 문서의 document_id, file_name과 content 앞 100자를 출력합니다.

    주의:
        - 컬렉션명 불일치: create_mock_markdown_db는 'msds_markdown_collection'을 사용하고,
          verify_mock_data는 'markdown_collection'을 사용합니다. 동일 컬렉션을 조회하도록
          맞추는 것을 권장합니다.
        - 미리보기 길이: content가 매우 짧거나 비어 있을 수 있으니 길이 체크를 고려하세요.

    Examples:
        >>> verify_mock_data(mongodb)  # 콘솔에 Mock 문서 목록을 출력
    """
    collection = mongodb['markdown_collection']

    print("\n저장된 Mock 문서:")
    for doc in collection.find({'document_id': {'$regex': '^MOCK_'}}):
        print(f"  - {doc['document_id']}: {doc['file_name']}")
        # 첫 100자만 출력
        content_preview = doc['content'][:100].replace('\n', ' ')
        print(f"    내용: {content_preview}...")



print("=" * 50)
print("Mock Markdown DB 생성")
print("=" * 50)

mongodb = get_mongodb()

if mongodb is not None:
    mock_docs = create_mock_markdown_db(mongodb)
    verify_mock_data(mongodb)

    print("=" * 50)
    print(f"\n총 {len(mock_docs)}개 Mock 문서 준비 완료")
    print("\n다음 단계: python extractor.py 실행")
    print("=" * 50)