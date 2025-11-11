"""
[핵심] 물성 항목 사전 (Dictionary)

역할:
- TDS에서 추출 가능한 23개 물성 정의
- 물성별 이름 패턴 (한글, 영문, 약어)
- 허용 단위 목록 정의

구조:
    PROPERTY_PATTERNS = {
        'Tg': {
            'names': ['Tg', '유리전이온도', 'Glass Transition', ...],
            'units': ['℃', 'K', '°C', 'C'],
            'keywords': ['유리전이', 'glass transition']
        },
        ...
    }

지원 물성 (23개):
    열적: Tg, Tm, Td, HDT
    전기: DC, Eg
    기계: YS, YM, BS, Tensile_Strength, Elongation_Rate, Hardness
    투과: He/H2/O2/N2/CO2/CH4_permeability
    기타: Viscosity, Thermal_Conductivity, Density, Thixotropic_index

확장:
    add_dynamic_property() 함수로 새 물성 동적 추가 가능
"""

PROPERTY_PATTERNS = {
    'Tg': {
        'names': ['Tg', '유리전이온도', 'Glass Transition', '유리 전이 온도', 'Glass Transition Temperature'],
        'units': ['℃', 'K', '°C', 'C'],
        'keywords': ['유리전이', 'glass transition']
    },
    'Tm': {
        'names': ['Tm', '용융온도', 'Melting Temperature', 'Melting Point', 'TDS', 'LDS', 'Tm(TDS/LDS)'],
        'units': ['℃', 'K', '°C', 'C'],
        'keywords': ['용융', 'melting']
    },
    'Td': {
        'names': ['Td', '열분해온도', 'Decomposition Temperature', 'Td(TDS/LDS)'],
        'units': ['℃', 'K', '°C', 'C'],
        'keywords': ['열분해', 'decomposition']
    },
    'DC': {
        'names': ['DC', '유전상수', 'Dielectric Constant'],
        'units': ['', '-', 'F/m'],
        'keywords': ['유전상수', 'dielectric']
    },
    'Eg': {
        'names': ['Eg', '에너지 밴드갭', 'Energy Band Gap', 'Band Gap'],
        'units': ['eV', 'electronvolt'],
        'keywords': ['밴드갭', 'band gap', 'energy']
    },
    'PL': {
        'names': ['PL', 'Photoluminescence'],
        'units': ['nm', 'a.u.', ''],
        'keywords': ['photoluminescence', 'PL']
    },
    'YS': {
        'names': ['YS', '항복강도', 'Yield Strength'],
        'units': ['MPa', 'N/mm2', 'N/mm²', 'ksi', 'psi'],
        'keywords': ['항복강도', 'yield strength']
    },
    'YM': {
        'names': ['YM', '영률', "Young's Modulus", 'Modulus', 'Elastic Modulus'],
        'units': ['MPa', 'GPa', 'psi', 'ksi'],
        'keywords': ['영률', 'modulus', "young's", 'elastic']
    },
    'BS': {
        'names': ['BS', '굽힘강도', 'Bending Strength', 'Flexural Strength'],
        'units': ['Nm2', 'Nm²', 'Pam3', 'Pam³', 'MPa'],
        'keywords': ['굽힘강도', 'bending', 'flexural']
    },
    'He_permeability': {
        'names': ['He투과율', 'He 투과율', 'He barrier', 'He permeability', 'He'],
        'units': ['cm³/m²', 'cc/m2', 'cm3/m2·day', 'barrier'],
        'keywords': ['He', '헬륨', 'helium', '투과']
    },
    'H2_permeability': {
        'names': ['H2투과율', 'H2 투과율', 'H2 barrier', 'H2 permeability', 'H2'],
        'units': ['cm³/m²', 'cc/m2', 'cm3/m2·day', 'barrier'],
        'keywords': ['H2', '수소', 'hydrogen', '투과']
    },
    'O2_permeability': {
        'names': ['O2투과율', 'O2 투과율', 'O2 barrier', 'O2 permeability', 'O2'],
        'units': ['cm³/m²', 'cc/m2', 'cm3/m2·day', 'barrier'],
        'keywords': ['O2', '산소', 'oxygen', '투과']
    },
    'N2_permeability': {
        'names': ['N2투과율', 'N2 투과율', 'N2 barrier', 'N2 permeability', 'N2'],
        'units': ['cm³/m²', 'cc/m2', 'cm3/m2·day', 'barrier'],
        'keywords': ['N2', '질소', 'nitrogen', '투과']
    },
    'CO2_permeability': {
        'names': ['CO2투과율', 'CO2 투과율', 'CO2 barrier', 'CO2 permeability', 'CO2'],
        'units': ['cm³/m²', 'cc/m2', 'cm3/m2·day', 'barrier'],
        'keywords': ['CO2', '이산화탄소', 'carbon dioxide', '투과']
    },
    'CH4_permeability': {
        'names': ['CH4투과율', 'CH4 투과율', 'CH4 barrier', 'CH4 permeability', 'CH4'],
        'units': ['cm³/m²', 'cc/m2', 'cm3/m2·day', 'barrier'],
        'keywords': ['CH4', '메탄', 'methane', '투과']
    },
    'Viscosity': {
        'names': ['점도', 'Viscosity'],
        'units': ['cP', 'Pa·s', 'mPa·s', 'cps'],
        'keywords': ['점도', 'viscosity']
    },
    'Hardness': {
        'names': ['Hardness', 'Shore A', 'Shore D', '경도'],
        'units': ['Shore A', 'Shore D', 'HV', 'HB', ''],
        'keywords': ['hardness', '경도', 'shore']
    },
    'Tensile_Strength': {
        'names': ['Tensile Strength', '인장강도', 'Tensile'],
        'units': ['MPa', 'psi', 'N/mm²', 'ksi'],
        'keywords': ['tensile', '인장강도']
    },
    'Elongation_Rate': {
        'names': ['Elongation Rate', '연신율', 'Elongation'],
        'units': ['%', 'percent'],
        'keywords': ['elongation', '연신율']
    },
    'Thixotropic_index': {
        'names': ['Thixotropic index', '요변지수', 'Thixotropy'],
        'units': ['', '-'],
        'keywords': ['thixotropic', '요변']
    },
    'HDT': {
        'names': ['HDT', 'Heat Deflection Temperature', '열변형온도'],
        'units': ['℃', '°C', 'K'],
        'keywords': ['HDT', 'heat deflection', '열변형']
    },
    'Thermal_Conductivity': {
        'names': ['Thermal Conductivity', '열전도도', '열전도율'],
        'units': ['W/m·K', 'W/mK', 'W/(m·K)'],
        'keywords': ['thermal conductivity', '열전도']
    },
    'Density': {
        'names': ['Density', '밀도', '비중'],
        'units': ['g/cm³', 'g/cm3', 'kg/m³', 'kg/m3'],
        'keywords': ['density', '밀도', '비중']
    }
}


# 동적으로 추가된 항목 저장
DYNAMIC_PROPERTIES = {}


def add_dynamic_property(property_key, names, units=None):
    """
    새로운 물성 항목 동적 추가

    Args:
        property_key: 물성 키 (예: 'NewProperty')
        names: 항목명 리스트
        units: 단위 리스트 (선택)
    """
    DYNAMIC_PROPERTIES[property_key] = {
        'names': names,
        'units': units or [''],
        'keywords': []
    }
    print(f"✅ 새 물성 항목 추가: {property_key}")


def get_all_properties():
    """
    모든 물성 항목 반환 (정의된 것 + 동적 추가된 것)
    """
    all_props = PROPERTY_PATTERNS.copy()
    all_props.update(DYNAMIC_PROPERTIES)
    return all_props


if __name__ == "__main__":
    print("=" * 50)
    print("정의된 물성 항목")
    print("=" * 50)

    for prop_key, prop_info in PROPERTY_PATTERNS.items():
        print(f"\n{prop_key}:")
        print(f"  이름: {', '.join(prop_info['names'][:3])}...")
        print(f"  단위: {', '.join(prop_info['units'])}")

    print(f"\n총 {len(PROPERTY_PATTERNS)}개 물성 항목 정의됨")
