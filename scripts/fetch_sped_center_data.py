#!/usr/bin/env python3
"""
fetch_sped_center_data.py - 교육부 국립특수교육원_특수교육지원센터현황 수집
data.go.kr id 15052681 (197개소, 2026-06-19 갱신), CSV 파일데이터(CP949).
다운로드: https://www.data.go.kr/cmm/cmm/fileDownload.do?atchFileId=FILE_000000003659115&fileDetailSn=1&insertDataPrcus=N
컬럼: 시도/교육청/센터명/우편번호/기관주소/전화번호/팩스번호/설치된기관/누리집주소/기준일자
좌표는 원본에 없어 카카오 지오코딩으로 보강 -> data/sped_centers.json

사용법:
  python scripts/fetch_sped_center_data.py
"""
import csv
import hashlib
import json
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path

import requests

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).parent.parent
RAW_CSV = ROOT / "data" / "sped_center_raw.csv"
GEO_CACHE = ROOT / "data" / "sped_center_geo_cache.json"
OUT_FILE = ROOT / "data" / "sped_centers.json"

# .env 로드 (KAKAO_REST_KEY)
env_path = ROOT / ".env"
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

KAKAO_REST_KEY = os.getenv("KAKAO_REST_KEY")
if not KAKAO_REST_KEY:
    sys.exit("❌ .env에 KAKAO_REST_KEY 없음")

KAKAO_SEARCH_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"
KAKAO_HEADERS = {"Authorization": f"KakaoAK {KAKAO_REST_KEY}"}

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
GWANGJU_CITY_HINTS = ("동구", "서구", "남구", "북구", "광산구")


def guess_sido_sggu(addr: str):
    text = addr or ""
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


def search_kakao(query: str, attempt: int = 1) -> dict:
    try:
        resp = requests.get(KAKAO_SEARCH_URL, params={"query": query, "size": 1},
                             headers=KAKAO_HEADERS, timeout=15)
        if resp.status_code == 429:
            if attempt >= 5:
                return {}
            time.sleep(2 * attempt)
            return search_kakao(query, attempt + 1)
        resp.raise_for_status()
        docs = resp.json().get("documents", [])
        return docs[0] if docs else {}
    except requests.exceptions.RequestException:
        if attempt >= 3:
            return {}
        time.sleep(1.5 * attempt)
        return search_kakao(query, attempt + 1)


def main():
    rows = list(csv.reader(RAW_CSV.read_text(encoding="cp949", errors="replace").splitlines()))
    header, data_rows = rows[0], rows[1:]
    print("header:", header)

    geo_cache = json.loads(GEO_CACHE.read_text(encoding="utf-8")) if GEO_CACHE.exists() else {}

    out = []
    skipped = 0
    geocoded_now = 0

    for r in data_rows:
        if len(r) < 9:
            skipped += 1
            continue
        sido_raw, edu_office, name, zipcode, addr, tel, fax, host_org, homepage = (c.strip() for c in r[:9])
        if not name or not addr:
            skipped += 1
            continue

        sido, sggu = guess_sido_sggu(addr)
        if not sido:
            skipped += 1
            continue

        geo_query = re.sub(r"\s*\([^)]*\)\s*$", "", addr).strip() or addr
        if addr in geo_cache and geo_cache[addr].get("x"):
            x, y = geo_cache[addr]["x"], geo_cache[addr]["y"]
        else:
            doc = search_kakao(geo_query)
            x, y = doc.get("x", ""), doc.get("y", "")
            if x:
                geo_cache[addr] = {"x": x, "y": y}
                geocoded_now += 1
                if geocoded_now % 50 == 0:
                    print(f"  geocoded {geocoded_now}...")

        h = hashlib.md5(f"{name}|{addr}".encode("utf-8")).hexdigest()[:6]
        out.append({
            "name": name,
            "sido_nm": sido,
            "sggu_nm": sggu,
            "addr": addr,
            "tel": tel,
            "fax": fax,
            "hostOrg": host_org,
            "homepage": homepage,
            "eduOffice": edu_office,
            "x": x,
            "y": y,
            "id": h,
        })

    GEO_CACHE.write_text(json.dumps(geo_cache, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_FILE.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    geo_ok = sum(1 for o in out if o["x"])
    print(f"총 {len(data_rows)}건 중 {len(out)}개 저장, {skipped}개 스킵 -> {OUT_FILE}")
    print(f"좌표 확보: {geo_ok}/{len(out)} ({geo_ok*100//max(len(out),1)}%)")
    region_count = Counter(o["sido_nm"] for o in out)
    print("지역별:", dict(region_count))


if __name__ == "__main__":
    main()
