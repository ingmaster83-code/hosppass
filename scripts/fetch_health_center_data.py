#!/usr/bin/env python3
"""
fetch_health_center_data.py - 전국건강생활지원센터표준데이터 수집 (보건복지부)
건강생활지원센터(지역보건법) 정보 - data/health_centers.json 생성

사용법:
  python scripts/fetch_health_center_data.py
"""
import sys, json, time
from pathlib import Path
import requests

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).parent.parent
PUBLIC_DATA_PK = "15100059"
SVC_TABLE = "tn_pubr_public_hl_cnter_api"
COLUMNS = [
    "HL_CNTER_NM", "HL_CNTER_TYPE", "LCTN_ROAD_NM_ADDR", "LATITUDE", "LONGITUDE",
    "OPER_OPEN_HHMM", "OPER_COLSE_HHMM", "RSTDE_INFO", "HP_CNTER_JOB", "ETC_USE_IFNO",
    "DOCTR_CO", "NURSE_CO", "NTRST_CO", "PHYACT_CO", "PHY_THERA_CO", "SCRCS_CO",
    "NURSE_ASSIST_CO", "ETC_HNF_STTUS",
    "HP_EQUIP_CU", "FITNESS_EQUIP_CU", "EXERCISE_EQUIP_CU", "NO_SMOKE_EQUIP_CU",
    "NUTRI_EQUIP_CU", "TEMPERANCE_EQUIP_CU", "REHAB_EQUIP_CU", "HELTH_EDU_CU",
    "INFEC_DIS_EQUIP_CU",
    "INST_TELNO", "INSTITUTION_NM", "REFERENCE_DATE",
]
RAW_FILE = ROOT / "data" / "health_center_raw.json"
OUT_FILE = ROOT / "data" / "health_centers.json"
PER_PAGE = 10000

# 이 데이터셋엔 시도/시군구 컬럼이 따로 없어 주소 문자열에서 직접 파싱 (긴 접두어부터 매칭)
SIDO_PREFIXES = [
    ("서울특별시", "서울"), ("부산광역시", "부산"), ("인천광역시", "인천"),
    ("대구광역시", "대구"), ("광주광역시", "광주"), ("대전광역시", "대전"),
    ("울산광역시", "울산"), ("세종특별자치시", "세종"),
    ("경기도", "경기"),
    ("강원특별자치도", "강원"), ("강원도", "강원"),
    ("충청북도", "충북"), ("충청남도", "충남"),
    ("전북특별자치도", "전북"), ("전라북도", "전북"), ("전라남도", "전남"),
    ("경상북도", "경북"), ("경상남도", "경남"),
    ("제주특별자치도", "제주"), ("제주도", "제주"),
]


def guess_sido_sggu(addr: str):
    text = addr or ""
    # "전남광주통합특별시" — 광주+전남 통합 행정구역명. 시군구명이 "구"로 끝나면
    # (광주 자치구: 동/서/남/북/광산구) 광주, 그 외(전남 시/군)는 전남으로 재분류.
    UNIFIED_PREFIX = "전남광주통합특별시"
    if text.startswith(UNIFIED_PREFIX):
        rest = text[len(UNIFIED_PREFIX):].strip()
        sggu = rest.split()[0] if rest else ""
        short = "광주" if sggu.endswith("구") else "전남"
        return short, sggu
    for prefix, short in SIDO_PREFIXES:
        if text.startswith(prefix):
            rest = text[len(prefix):].strip()
            sggu = rest.split()[0] if rest else ""
            return short, sggu
    return "", ""


def fetch_page(page: int) -> list:
    params = [("publicDataPk", PUBLIC_DATA_PK)]
    params += [("colNmList", c) for c in COLUMNS]
    params += [
        ("totalCount", "99999"),
        ("svcTableNm", SVC_TABLE),
        ("perPage", str(PER_PAGE)),
        ("page", str(page)),
    ]
    resp = requests.get(
        "https://www.data.go.kr/download/standard.json",
        params=params, timeout=60,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, dict):
        return []
    return data


def main():
    print("=== 전국건강생활지원센터표준데이터 수집 시작 ===")
    all_items = []
    page = 1
    while True:
        items = fetch_page(page)
        if not items:
            break
        all_items.extend(items)
        print(f"  페이지 {page}: {len(items)}개 (누적 {len(all_items)})")
        if len(items) < PER_PAGE:
            break
        page += 1
        time.sleep(0.3)

    if not all_items:
        raise SystemExit("수집된 데이터가 없습니다.")

    RAW_FILE.parent.mkdir(parents=True, exist_ok=True)
    RAW_FILE.write_text(json.dumps(all_items, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"원본 저장: {RAW_FILE} ({len(all_items)}건)")

    centers = []
    for d in all_items:
        name = (d.get("HL_CNTER_NM") or "").strip()
        addr = (d.get("LCTN_ROAD_NM_ADDR") or "").strip()
        if not name or not addr:
            continue
        sido_nm, sggu_nm = guess_sido_sggu(addr)
        if not sido_nm or not sggu_nm:
            continue

        equip_fields = [
            ("건강검진장비", d.get("HP_EQUIP_CU")),
            ("체력측정장비", d.get("FITNESS_EQUIP_CU")),
            ("운동장비", d.get("EXERCISE_EQUIP_CU")),
            ("금연사업장비", d.get("NO_SMOKE_EQUIP_CU")),
            ("영양사업장비", d.get("NUTRI_EQUIP_CU")),
            ("절주사업장비", d.get("TEMPERANCE_EQUIP_CU")),
            ("재활사업장비", d.get("REHAB_EQUIP_CU")),
            ("보건교육장비", d.get("HELTH_EDU_CU")),
            ("감염병예방장비", d.get("INFEC_DIS_EQUIP_CU")),
        ]
        equipment = [f"{label}({val.strip()})" for label, val in equip_fields if (val or "").strip() and (val or "").strip() not in ("0", "없음")]

        staff_fields = [
            ("의사", d.get("DOCTR_CO")), ("간호사", d.get("NURSE_CO")),
            ("영양사", d.get("NTRST_CO")), ("신체활동전문인력", d.get("PHYACT_CO")),
            ("물리/작업치료사", d.get("PHY_THERA_CO")), ("사회복지사", d.get("SCRCS_CO")),
            ("간호조무사", d.get("NURSE_ASSIST_CO")),
        ]
        staff = [f"{label} {val.strip()}명" for label, val in staff_fields if (val or "").strip() not in ("", "0")]

        centers.append({
            "name": name,
            "type": (d.get("HL_CNTER_TYPE") or "").strip(),
            "addr": addr,
            "sido_nm": sido_nm,
            "sggu_nm": sggu_nm,
            "x": (d.get("LONGITUDE") or "").strip(),
            "y": (d.get("LATITUDE") or "").strip(),
            "openTime": (d.get("OPER_OPEN_HHMM") or "").strip(),
            "closeTime": (d.get("OPER_COLSE_HHMM") or "").strip(),
            "closedInfo": (d.get("RSTDE_INFO") or "").strip(),
            "programs": (d.get("HP_CNTER_JOB") or "").strip(),
            "etcInfo": (d.get("ETC_USE_IFNO") or "").strip(),
            "staff": staff,
            "equipment": equipment,
            "tel": (d.get("INST_TELNO") or "").strip(),
            "institution": (d.get("INSTITUTION_NM") or "").strip(),
            "refDate": (d.get("REFERENCE_DATE") or "").strip(),
        })

    print(f"최종 저장 {len(centers):,}건 (원본 {len(all_items):,}건 중 지역매칭 실패 {len(all_items)-len(centers)}건 제외)")

    OUT_FILE.parent.mkdir(exist_ok=True)
    OUT_FILE.write_text(
        json.dumps({"items": centers}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"저장 완료: {OUT_FILE}")


if __name__ == "__main__":
    main()
