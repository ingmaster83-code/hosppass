#!/usr/bin/env python3
"""
fetch_transport_data.py - 전국교통약자이동지원센터정보표준데이터 수집 (국토교통부/지자체)
장애인콜택시 등 특별교통차량 예약센터 정보 - data/transport_centers.json 생성

사용법:
  python scripts/fetch_transport_data.py
"""
import sys, json, re, time
from pathlib import Path
import requests

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).parent.parent
PUBLIC_DATA_PK = "15028207"
SVC_TABLE = "tn_pubr_public_tfcwker_mvmn_cnter_svc"
COLUMNS = [
    "TFCWKER_MVMN_CNTER_NM", "RDNMADR", "LNMADR", "LATITUDE", "LONGITUDE",
    "CAR_HOLD_CO", "CAR_HOLD_KND", "SLOPE_VHCLE_CO", "LIFT_VHCLE_CO",
    "RCEPT_PHONE_NUMBER", "RCEPT_ITNADR", "APP_SVC_NM",
    "WEEKDAY_RCEPT_OPEN_HHMM", "WEEKDAY_RCEPT_COLSE_HHMM",
    "WKEND_RCEPT_OPEN_HHMM", "WKEND_RCEPT_CLOSE_HHMM",
    "WEEKDAY_OPER_OPEN_HHMM", "WEEKDAY_OPER_COLSE_HHMM",
    "WKEND_OPER_OPEN_HHMM", "WKEND_OPER_CLOSE_HHMM",
    "BEFFAT_RESVE_PD", "USE_LMTT", "INSIDE_OPRAT_AREA", "OUTSIDE_OPRAT_AREA",
    "USE_TRGET", "USE_CHARGE", "INSTITUTION_NM", "PHONE_NUMBER", "REFERENCE_DATE",
]
RAW_FILE = ROOT / "data" / "transport_raw.json"
OUT_FILE = ROOT / "data" / "transport_centers.json"
PER_PAGE = 10000

# guess_sido_sggu()와 동일한 방식(fetch_otc_medicine_data.py 참고) - 주소 접두어 매칭
SIDO_PREFIXES = [
    ("서울특별시", "서울"), ("부산광역시", "부산"), ("대구광역시", "대구"),
    ("인천광역시", "인천"), ("광주광역시", "광주"), ("대전광역시", "대전"),
    ("울산광역시", "울산"), ("세종특별자치시", "세종"),
    ("경기도", "경기"), ("강원특별자치도", "강원"), ("강원도", "강원"),
    ("충청북도", "충북"), ("충청남도", "충남"),
    ("전북특별자치도", "전북"), ("전라북도", "전북"), ("전라남도", "전남"),
    ("경상북도", "경북"), ("경상남도", "경남"), ("제주특별자치도", "제주"),
    ("전남광주통합특별시", "광주"),
]
FULL_SIDO_NM = {
    "서울": "서울특별시", "부산": "부산광역시", "대구": "대구광역시", "인천": "인천광역시",
    "광주": "광주광역시", "대전": "대전광역시", "울산": "울산광역시", "세종": "세종특별자치시",
    "경기": "경기도", "강원": "강원특별자치도", "충북": "충청북도", "충남": "충청남도",
    "전북": "전북특별자치도", "전남": "전라남도", "경북": "경상북도", "경남": "경상남도",
    "제주": "제주특별자치도",
}


def guess_sido_sggu(addr: str):
    if not addr:
        return "", ""
    for full, short in SIDO_PREFIXES:
        if addr.startswith(full):
            rest = addr[len(full):].strip()
            sggu = rest.split()[0] if rest else ""
            return FULL_SIDO_NM.get(short, full), sggu
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
    print("=== 전국교통약자이동지원센터정보표준데이터 수집 시작 ===")
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
        name = (d.get("TFCWKER_MVMN_CNTER_NM") or "").strip()
        addr = (d.get("RDNMADR") or "").strip() or (d.get("LNMADR") or "").strip()
        if not name or not addr:
            continue
        sido_nm, sggu_nm = guess_sido_sggu(addr)
        if not sido_nm or not sggu_nm:
            continue

        stores.append({
            "name": name,
            "addr": addr,
            "sido_nm": sido_nm,
            "sggu_nm": sggu_nm,
            "x": (d.get("LONGITUDE") or "").strip(),
            "y": (d.get("LATITUDE") or "").strip(),
            "carHoldCo": (d.get("CAR_HOLD_CO") or "").strip(),
            "carHoldKnd": (d.get("CAR_HOLD_KND") or "").strip(),
            "slopeCo": (d.get("SLOPE_VHCLE_CO") or "").strip(),
            "liftCo": (d.get("LIFT_VHCLE_CO") or "").strip(),
            "reserveTel": (d.get("RCEPT_PHONE_NUMBER") or "").strip(),
            "reserveUrl": (d.get("RCEPT_ITNADR") or "").strip(),
            "appName": (d.get("APP_SVC_NM") or "").strip(),
            "weekdayReserveOpen": (d.get("WEEKDAY_RCEPT_OPEN_HHMM") or "").strip(),
            "weekdayReserveClose": (d.get("WEEKDAY_RCEPT_COLSE_HHMM") or "").strip(),
            "weekendReserveOpen": (d.get("WKEND_RCEPT_OPEN_HHMM") or "").strip(),
            "weekendReserveClose": (d.get("WKEND_RCEPT_CLOSE_HHMM") or "").strip(),
            "weekdayOperOpen": (d.get("WEEKDAY_OPER_OPEN_HHMM") or "").strip(),
            "weekdayOperClose": (d.get("WEEKDAY_OPER_COLSE_HHMM") or "").strip(),
            "weekendOperOpen": (d.get("WKEND_OPER_OPEN_HHMM") or "").strip(),
            "weekendOperClose": (d.get("WKEND_OPER_CLOSE_HHMM") or "").strip(),
            "reservePeriod": (d.get("BEFFAT_RESVE_PD") or "").strip(),
            "useLimit": (d.get("USE_LMTT") or "").strip(),
            "insideArea": (d.get("INSIDE_OPRAT_AREA") or "").strip(),
            "outsideArea": (d.get("OUTSIDE_OPRAT_AREA") or "").strip(),
            "useTarget": (d.get("USE_TRGET") or "").strip(),
            "useCharge": (d.get("USE_CHARGE") or "").strip(),
            "institution": (d.get("INSTITUTION_NM") or "").strip(),
            "tel": (d.get("PHONE_NUMBER") or "").strip(),
            "refDate": (d.get("REFERENCE_DATE") or "").strip(),
        })

    if OUT_FILE.exists():
        existing = json.loads(OUT_FILE.read_text(encoding="utf-8"))
        existing_items = existing.get("items", []) if isinstance(existing, dict) else existing
        if len(stores) < len(existing_items) * 0.5:
            raise SystemExit(
                f"수집 건수({len(stores)}건)가 기존 데이터({len(existing_items)}건)의 절반 미만입니다. "
                "오류로 판단하여 저장을 중단합니다."
            )

    OUT_FILE.write_text(json.dumps({"items": stores}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n완료: {OUT_FILE}")
    print(f"  총 {len(stores)}개 교통약자이동지원센터 저장 (원본 {len(all_items)}건 중 지역매칭 실패 {len(all_items)-len(stores)}건 제외)")


if __name__ == "__main__":
    main()
