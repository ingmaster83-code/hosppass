#!/usr/bin/env python3
"""
fetch_pharmacy_hours.py - 국립중앙의료원 전국 약국 정보 조회 서비스(요일별 진료시간)를
수집해, 기존 data/pharmacies.json(HIRA 기반, 요일별 시간 없음)의 각 약국과 좌표 최근접
매칭 후 data/pharmacy_hours.json(ykiho -> hours)을 생성한다.

운영시간은 자주 바뀌지 않으므로 일일 cron이 아니라 필요할 때 수동 실행한다.

사용법:
  python scripts/fetch_pharmacy_hours.py
"""
import json
import math
import os
import sys
import time
from pathlib import Path

import requests

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).parent.parent
PHARMACIES_FILE = ROOT / "data" / "pharmacies.json"
OUT_FILE = ROOT / "data" / "pharmacy_hours.json"
RAW_FILE = ROOT / "data" / "pharmacy_hours_raw.json"

BASE = "https://apis.data.go.kr/B552657/ErmctInsttInfoInqireService/getParmacyFullDown"
SERVICE_KEY = os.environ.get("DATA_GO_KR_API_KEY") or "9490b1d34e92aa9e25b32a4cff1438fc7b9c71e5d332413916a391e867f61e86"
PER_PAGE = 1000

DAY_KEYS_KR = ["월", "화", "수", "목", "금", "토", "일"]
MAX_MATCH_DIST_M = 150  # 좌표 기준, 같은 약국이면 이 정도 이내로 붙음


def fetch_all():
    items = []
    page = 1
    while True:
        r = requests.get(BASE, params={"ServiceKey": SERVICE_KEY, "pageNo": page, "numOfRows": PER_PAGE, "_type": "json"}, timeout=60)
        r.raise_for_status()
        d = r.json()["response"]
        if d["header"]["resultCode"] not in ("00", "0"):
            raise SystemExit(f"API 오류: {d['header']}")
        body = d["body"]
        batch = body.get("items", {}).get("item") or []
        if isinstance(batch, dict):
            batch = [batch]
        if not batch:
            break
        items.extend(batch)
        print(f"  페이지 {page}: {len(batch)}개 (누적 {len(items)}/{body.get('totalCount')})")
        if len(items) >= body.get("totalCount", 0):
            break
        page += 1
        time.sleep(0.15)
    return items


def to_hhmm(v):
    s = str(v or "").strip().zfill(4)
    if len(s) != 4 or not s.isdigit():
        return None
    return f"{s[:2]}:{s[2:]}"


def build_hours(raw_item):
    hours = {}
    for i, day in enumerate(DAY_KEYS_KR, start=1):
        s = to_hhmm(raw_item.get(f"dutyTime{i}s"))
        e = to_hhmm(raw_item.get(f"dutyTime{i}c"))
        if s and e:
            hours[day] = {"start": s, "end": e}
    return hours


def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def main():
    print("=== 국립중앙의료원 약국 진료시간 수집 시작 ===")
    if RAW_FILE.exists():
        raw = json.loads(RAW_FILE.read_text(encoding="utf-8"))
        print(f"  캐시 사용: {len(raw)}건")
    else:
        raw = fetch_all()
        RAW_FILE.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
        print(f"원본 저장: {RAW_FILE} ({len(raw)}건)")

    # 좌표 기준 그리드 인덱스(0.01도 ~ 1km 단위)로 매칭 속도 확보
    grid = {}
    for r in raw:
        try:
            lat, lon = float(r.get("wgs84Lat")), float(r.get("wgs84Lon"))
        except (TypeError, ValueError):
            continue
        if not lat or not lon:
            continue
        r["wgs84Lat"], r["wgs84Lon"] = lat, lon
        key = (round(lat, 2), round(lon, 2))
        grid.setdefault(key, []).append(r)

    pharmacies_data = json.loads(PHARMACIES_FILE.read_text(encoding="utf-8"))
    pharmacies = pharmacies_data.get("items", pharmacies_data) if isinstance(pharmacies_data, dict) else pharmacies_data

    result = {}
    matched = 0
    for p in pharmacies:
        try:
            px, py = float(p.get("x")), float(p.get("y"))  # x=lon, y=lat (hosppass 관례)
        except (TypeError, ValueError):
            continue
        gy, gx = round(py, 2), round(px, 2)
        candidates = []
        for dy in (-0.01, 0, 0.01):
            for dx in (-0.01, 0, 0.01):
                candidates.extend(grid.get((round(gy + dy, 2), round(gx + dx, 2)), []))
        if not candidates:
            continue

        best, best_d = None, None
        for c in candidates:
            d = haversine_m(py, px, c["wgs84Lat"], c["wgs84Lon"])
            if best_d is None or d < best_d:
                best, best_d = c, d
        if best is None or best_d > MAX_MATCH_DIST_M:
            continue

        hours = build_hours(best)
        if not hours:
            continue
        result[p["ykiho"]] = hours
        matched += 1

    OUT_FILE.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    print(f"\n완료: 전체 약국 {len(pharmacies)}곳 중 {matched}곳 진료시간 매칭 -> {OUT_FILE}")


if __name__ == "__main__":
    main()
