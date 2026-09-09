#!/usr/bin/env python3
"""
fetch_nonpayment_data.py - 건강보험심사평가원 비급여진료비정보(병원급 이상)를 요양기호별로 수집.

병원급 이상(종합병원/병원/요양병원/정신병원/한방병원/치과병원/상급종합)만 비급여 데이터를
등록하므로 hospitals.json에서 해당 종별만 걸러 대상으로 삼는다. (의원급은 API 자체에
데이터가 없음을 실측 확인함)

출력: data/nonpayment.json  - {ykiho: [항목...]}
"""
import json, os, sys, time, argparse
import requests

sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOSPITALS_PATH = os.path.join(ROOT, "data", "hospitals.json")
OUT_PATH = os.path.join(ROOT, "data", "nonpayment.json")

SERVICE_KEY = os.environ.get("DATA_GO_KR_API_KEY") or "9490b1d34e92aa9e25b32a4cff1438fc7b9c71e5d332413916a391e867f61e86"
BASE = "https://apis.data.go.kr/B551182/nonPaymentDamtInfoService/getNonPaymentItemHospDtlList"

# 병원급 이상만 비급여 정보를 등록함 (실측: 의원급은 totalCount 0)
HOSPITAL_TIER_CODES = {"01", "11", "21", "28", "29", "41", "92"}  # 상급종합/종합병원/병원/요양병원/정신병원/치과병원/한방병원

DEFAULT_LIMIT = 4500


def fetch_all_pages(ykiho, attempt=1):
    rows = []
    page = 1
    while True:
        params = {
            "serviceKey": SERVICE_KEY, "pageNo": page, "numOfRows": 100, "ykiho": ykiho,
        }
        try:
            # 이 API는 요청당 16~50초 이상 걸리는 이례적으로 느린 응답속도가 실측됨(다른 공공
            # API는 보통 1초 내). 짧은 timeout은 정상 응답을 실패로 오판하게 만들어 넉넉히 잡음.
            r = requests.get(BASE, params=params, timeout=90)
            r.raise_for_status()
            # XML 응답 -> 간단 파싱 (표준 라이브러리만 사용)
            import xml.etree.ElementTree as ET
            root = ET.fromstring(r.content)
            total = int((root.findtext(".//totalCount") or "0"))
            items = root.findall(".//item")
            for it in items:
                rows.append({child.tag: (child.text or "") for child in it})
            if len(rows) >= total or not items:
                break
            page += 1
            if page > 20:
                break
        except Exception as e:
            if attempt >= 3:
                return None
            time.sleep(2)
            return fetch_all_pages(ykiho, attempt + 1)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    args = ap.parse_args()

    hospitals = json.load(open(HOSPITALS_PATH, encoding="utf-8"))["items"]
    targets = [h for h in hospitals if h.get("cl_cd") in HOSPITAL_TIER_CODES and h.get("ykiho")]
    print(f"병원급 이상 대상: {len(targets)}개")

    cache = {}
    if os.path.exists(OUT_PATH):
        cache = json.load(open(OUT_PATH, encoding="utf-8"))

    remaining = [h for h in targets if h["ykiho"] not in cache]
    print(f"확보 {len(cache)}개 / 남음 {len(remaining)}개")
    if not remaining:
        print("완료!")
        return

    todo = remaining[: args.limit]
    print(f"이번 실행에서 {len(todo)}개 처리...")

    ok, empty, fail = 0, 0, 0
    for i, h in enumerate(todo, 1):
        rows = fetch_all_pages(h["ykiho"])
        if rows is None:
            fail += 1
        elif not rows:
            cache[h["ykiho"]] = []
            empty += 1
        else:
            cache[h["ykiho"]] = rows
            ok += 1
        if i % 300 == 0:
            print(f"  진행 {i}/{len(todo)} (성공 {ok}, 데이터없음 {empty}, 실패 {fail})")
            with open(OUT_PATH, "w", encoding="utf-8") as f:
                json.dump(cache, f, ensure_ascii=False)
        time.sleep(0.05)

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False)
    print(f"\n완료: 성공 {ok} / 데이터없음 {empty} / 실패 {fail}")
    print(f"누적 확보: {len(cache)} / {len(targets)} ({len(cache)*100//len(targets)}%)")


if __name__ == "__main__":
    main()
