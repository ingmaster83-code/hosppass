"""
hosppass.kr 치매안심센터 데이터 수집 스크립트
공공데이터포털 전국치매센터표준데이터 API에서 전체 데이터를 받아 data/dementia_centers.json으로 저장.

실행: python scripts/fetch_dementia_data.py
"""
import os
import sys
import io
import json
import time
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
OUT_PATH = DATA_DIR / "dementia_centers.json"

load_dotenv(ROOT / ".env")
API_KEY = os.getenv("API_KEY") or os.getenv("DATA_GO_KR_API_KEY")
if not API_KEY:
    sys.exit("❌ API 키 없음: .env에 API_KEY 또는 DATA_GO_KR_API_KEY 설정 필요")

API_URL = "https://api.data.go.kr/openapi/tn_pubr_public_imbclty_cnter_api"
NUM_OF_ROWS = 1000

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


def guess_sido_sggu(addr: str, instt_nm: str):
    text = addr or instt_nm or ""
    for prefix, short in SIDO_PREFIXES:
        if text.startswith(prefix):
            rest = text[len(prefix):].strip()
            sggu = rest.split()[0] if rest else ""
            return short, sggu
    # instt_nm이 "경기도 이천시" 같은 단순 2단어 구조인 경우 폴백
    parts = (instt_nm or "").split()
    if len(parts) >= 2:
        for prefix, short in SIDO_PREFIXES:
            if parts[0] == prefix:
                return short, parts[1]
    return "", ""


def fetch_all():
    all_records = []
    page = 1
    while True:
        params = {
            "serviceKey": API_KEY,
            "pageNo": page,
            "numOfRows": NUM_OF_ROWS,
            "type": "json",
        }
        resp = requests.get(API_URL, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        header = data.get("header", {})
        if header.get("resultCode") not in (None, "00"):
            raise SystemExit(f"API 오류: {header}")

        body = data.get("body", {})
        items = body.get("items", [])
        if isinstance(items, dict):
            items = items.get("item", [])
        if isinstance(items, dict):
            items = [items]

        if not items:
            break

        all_records.extend(items)
        print(f"  {page}페이지 완료 (누적 {len(all_records)}건)")

        total = int(body.get("totalCount", 0))
        if len(all_records) >= total or len(items) < NUM_OF_ROWS:
            break
        page += 1
        time.sleep(0.2)

    return all_records


def normalize(item):
    addr = item.get("rdnmadr") or item.get("lnmadr") or ""
    sido, sggu = guess_sido_sggu(addr, item.get("insttNm", ""))
    return {
        "name": item.get("cnterNm", ""),
        "type": item.get("cnterSe", ""),
        "addr": addr,
        "x": item.get("longitude", ""),
        "y": item.get("latitude", ""),
        "found_ym": item.get("fondYm", ""),
        "facilities": item.get("etcFclty", ""),
        "doctor_cnt": item.get("doctrCo", ""),
        "nurse_cnt": item.get("nurseCo", ""),
        "social_worker_cnt": item.get("scrcsCo", ""),
        "oper_org": item.get("operInstitutionNm", ""),
        "oper_tel": item.get("operPhoneNumber", ""),
        "programs": item.get("imbcltyIntrcn", ""),
        "tel": item.get("phoneNumber", ""),
        "manage_org": item.get("institutionNm", ""),
        "reference_date": item.get("referenceDate", ""),
        "sido_nm": sido,
        "sggu_nm": sggu,
    }


def main():
    print("치매안심센터 데이터 수집 시작...")
    raw = fetch_all()
    print(f"총 {len(raw)}건 수집 완료")

    records = [normalize(it) for it in raw]
    no_region = sum(1 for r in records if not r["sido_nm"] or not r["sggu_nm"])
    print(f"지역 매칭 실패: {no_region}건")

    if OUT_PATH.exists():
        existing = json.loads(OUT_PATH.read_text(encoding="utf-8")).get("items", [])
        if len(records) < len(existing) * 0.5:
            raise SystemExit(
                f"수집 건수({len(records)}건)가 기존 데이터({len(existing)}건)의 절반 미만입니다. "
                "API 오류로 판단하여 저장을 중단합니다."
            )

    DATA_DIR.mkdir(exist_ok=True)
    OUT_PATH.write_text(
        json.dumps({"items": records}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"저장 완료: {OUT_PATH}")


if __name__ == "__main__":
    main()
