#!/usr/bin/env python3
"""
fetch_wheelchair_charger_data.py - 전국전동휠체어급속충전기표준데이터 수집 (지자체)
전동휠체어·전동스쿠터 급속충전기 정보 - data/wheelchair_chargers.json 생성

사용법:
  python scripts/fetch_wheelchair_charger_data.py
"""
import sys, json, time
from pathlib import Path
import requests

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).parent.parent
PUBLIC_DATA_PK = "15034533"
SVC_TABLE = "tn_pubr_public_electr_whlchairhgh_spdchrgr_svc"
COLUMNS = [
    "FCLTY_NM", "CTPRVN_NM", "SIGNGU_NM", "SIGNGU_CODE", "RDNMADR", "LNMADR",
    "LATITUDE", "LONGITUDE", "INSTL_LC_DESC",
    "WEEKDAY_OPER_OPEN_HHMM", "WEEKDAY_OPER_COLSE_HHMM",
    "SAT_OPER_OPER_OPEN_HHMM", "SAT_OPER_CLOSE_HHMM",
    "HOLIDAY_OPER_OPEN_HHMM", "HOLIDAY_CLOSE_OPEN_HHMM",
    "SMTM_USE_CO", "AIR_INJECTOR_YN", "MOBLPHON_CHRSTN_YN",
    "INSTITUTION_NM", "INSTITUTION_PHONE_NUMBER", "REFERENCE_DATE",
]
RAW_FILE = ROOT / "data" / "wheelchair_charger_raw.json"
OUT_FILE = ROOT / "data" / "wheelchair_chargers.json"
PER_PAGE = 10000

DO_MAP = {
    "서울특별시": "서울", "부산광역시": "부산", "대구광역시": "대구",
    "인천광역시": "인천", "광주광역시": "광주", "대전광역시": "대전",
    "울산광역시": "울산", "세종특별자치시": "세종", "경기도": "경기",
    "강원특별자치도": "강원", "강원도": "강원",
    "충청북도": "충북", "충청남도": "충남",
    "전북특별자치도": "전북", "전라북도": "전북", "전라남도": "전남",
    "경상북도": "경북", "경상남도": "경남", "제주특별자치도": "제주", "제주도": "제주",
}


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
    print("=== 전국전동휠체어급속충전기표준데이터 수집 시작 ===")
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

    stores = []
    for d in all_items:
        name = (d.get("FCLTY_NM") or "").strip()
        addr = (d.get("RDNMADR") or "").strip() or (d.get("LNMADR") or "").strip()
        do_full = (d.get("CTPRVN_NM") or "").strip()
        sggu_nm = (d.get("SIGNGU_NM") or "").strip()
        if not name or not addr:
            continue
        sido_nm = DO_MAP.get(do_full, "")
        if not sido_nm or not sggu_nm:
            continue

        stores.append({
            "name": name,
            "addr": addr,
            "sido_nm": sido_nm,
            "sggu_nm": sggu_nm,
            "x": (d.get("LONGITUDE") or "").strip(),
            "y": (d.get("LATITUDE") or "").strip(),
            "installLoc": (d.get("INSTL_LC_DESC") or "").strip(),
            "weekdayOpen": (d.get("WEEKDAY_OPER_OPEN_HHMM") or "").strip(),
            "weekdayClose": (d.get("WEEKDAY_OPER_COLSE_HHMM") or "").strip(),
            "satOpen": (d.get("SAT_OPER_OPER_OPEN_HHMM") or "").strip(),
            "satClose": (d.get("SAT_OPER_CLOSE_HHMM") or "").strip(),
            "holidayOpen": (d.get("HOLIDAY_OPER_OPEN_HHMM") or "").strip(),
            "holidayClose": (d.get("HOLIDAY_CLOSE_OPEN_HHMM") or "").strip(),
            "simultUseCount": (d.get("SMTM_USE_CO") or "").strip(),
            "airInjector": (d.get("AIR_INJECTOR_YN") or "").strip() == "Y",
            "mobileCharge": (d.get("MOBLPHON_CHRSTN_YN") or "").strip() == "Y",
            "institution": (d.get("INSTITUTION_NM") or "").strip(),
            "institutionTel": (d.get("INSTITUTION_PHONE_NUMBER") or "").strip(),
            "refDate": (d.get("REFERENCE_DATE") or "").strip(),
        })

    print(f"최종 저장 {len(stores):,}건 (원본 {len(all_items):,}건 중 지역매칭 실패 {len(all_items)-len(stores)}건 제외)")

    if OUT_FILE.exists():
        existing = json.loads(OUT_FILE.read_text(encoding="utf-8")).get("items", [])
        if existing and len(stores) < len(existing) * 0.5:
            raise SystemExit(
                f"수집 건수({len(stores)}건)가 기존 데이터({len(existing)}건)의 절반 미만입니다. "
                "다운로드 오류로 판단하여 저장을 중단합니다."
            )

    OUT_FILE.parent.mkdir(exist_ok=True)
    OUT_FILE.write_text(
        json.dumps({"items": stores}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"저장 완료: {OUT_FILE}")


if __name__ == "__main__":
    main()
