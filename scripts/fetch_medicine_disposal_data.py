#!/usr/bin/env python3
"""
fetch_medicine_disposal_data.py - 전국폐의약품수거함표준데이터 수집
지자체가 관리하는 폐의약품(유효기간 경과·복용하지 않는 약) 수거함 정보 - data/medicine_disposal.json 생성

publicDataPk=15129445, svcTableNm=tn_pubr_public_lung_medicine_svc
컬럼: 설치장소명, 시도명, 시군구명, 도로명주소, 지번주소, 위도, 경도, 실제위치, 관리기관명, 관리기관전화번호, 기준일자
※ INSTT_CODE/INSTT_NM(제공기관코드/명)은 서버가 응답에 항상 자동으로 붙여주는 필드라
   colNmList에 명시적으로 다시 넣으면 API가 200/빈바디로 조용히 실패함 — 요청에서 제외.

사용법:
  python scripts/fetch_medicine_disposal_data.py
"""
import sys, json, time
from pathlib import Path
import requests

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).parent.parent
PUBLIC_DATA_PK = "15129445"
SVC_TABLE = "tn_pubr_public_lung_medicine_svc"
COLUMNS = [
    "INSTL_PLC_NM", "CTPV_NM", "SGG_NM", "LCTN_ROAD_NM", "LCTN_LOTNO_ADDR",
    "LAT", "LOT", "ACTL_PSTN", "MNG_INST_NM", "MNG_INST_TELNO", "CRTR_YMD",
]
RAW_FILE = ROOT / "data" / "medicine_disposal_raw.json"
OUT_FILE = ROOT / "data" / "medicine_disposal.json"
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
    print("=== 전국폐의약품수거함표준데이터 수집 시작 ===")
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
        name = (d.get("INSTL_PLC_NM") or "").strip()
        addr = (d.get("LCTN_ROAD_NM") or "").strip() or (d.get("LCTN_LOTNO_ADDR") or "").strip()
        do_full = (d.get("CTPV_NM") or "").strip()
        sggu_nm = (d.get("SGG_NM") or "").strip()
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
            "x": (d.get("LOT") or "").strip(),
            "y": (d.get("LAT") or "").strip(),
            "actualPosition": (d.get("ACTL_PSTN") or "").strip(),
            "institution": (d.get("MNG_INST_NM") or "").strip(),
            "institutionTel": (d.get("MNG_INST_TELNO") or "").strip(),
            "refDate": (d.get("CRTR_YMD") or "").strip(),
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
