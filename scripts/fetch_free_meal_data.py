#!/usr/bin/env python3
"""
fetch_free_meal_data.py - 전국무료급식소표준데이터 수집 (지자체)
결식우려 노인 등을 위한 무료급식소 정보 - data/free_meals.json 생성

사용법:
  python scripts/fetch_free_meal_data.py
"""
import sys, json, time
from pathlib import Path
import requests

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).parent.parent
PUBLIC_DATA_PK = "15013107"
SVC_TABLE = "tn_pubr_public_free_mlsv_svc"
COLUMNS = [
    "FCLTY_NM", "RDNMADR", "LNMADR", "OPER_INSTITUTION_NM", "PHONE_NUMBER",
    "MLSV_PLACE", "MLSV_TRGET", "MLSV_TIME", "MLSV_DATE",
    "OPER_OPEN_DATE", "OPER_CLOSE_DATE", "LATITUDE", "LONGITUDE", "REFERENCE_DATE",
]
RAW_FILE = ROOT / "data" / "free_meal_raw.json"
OUT_FILE = ROOT / "data" / "free_meals.json"
PER_PAGE = 10000

# 시군구 접미어보다 먼저 매칭돼야 하는 시도 접두어(긴 것부터, hosppass 지역 페이지와 동일한 축약형 사용)
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
    print("=== 전국무료급식소표준데이터 수집 시작 ===")
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
        if not name or not addr:
            continue
        sido_nm, sggu_nm = guess_sido_sggu(addr)
        if not sido_nm or not sggu_nm:
            continue

        # 폐쇄 여부: 종료일자(OPER_CLOSE_DATE)가 채워져 있으면 운영종료로 간주하고 제외
        close_date = (d.get("OPER_CLOSE_DATE") or "").strip()
        if close_date:
            continue

        stores.append({
            "name": name,
            "addr": addr,
            "sido_nm": sido_nm,
            "sggu_nm": sggu_nm,
            "x": (d.get("LONGITUDE") or "").strip(),
            "y": (d.get("LATITUDE") or "").strip(),
            "place": (d.get("MLSV_PLACE") or "").strip(),
            "target": (d.get("MLSV_TRGET") or "").strip(),
            "mealTime": (d.get("MLSV_TIME") or "").strip(),
            "mealDate": (d.get("MLSV_DATE") or "").strip(),
            "openDate": (d.get("OPER_OPEN_DATE") or "").strip(),
            "institution": (d.get("OPER_INSTITUTION_NM") or "").strip(),
            "tel": (d.get("PHONE_NUMBER") or "").strip(),
            "refDate": (d.get("REFERENCE_DATE") or "").strip(),
        })

    print(f"최종 저장 {len(stores):,}건 (원본 {len(all_items):,}건 중 지역매칭 실패/운영종료 {len(all_items)-len(stores)}건 제외)")

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
