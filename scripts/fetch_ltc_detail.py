#!/usr/bin/env python3
"""
fetch_ltc_detail.py - 장기요양기관 주소·전화번호·좌표 보강 (카카오 로컬 키워드 검색)

NHIS 장기요양기관 API(상세조회 서비스)는 도로명 텍스트 주소나 좌표를 주지 않고
우편번호+도로명코드+건물번호 등 구조화된 필드만 준다(2026-09-09 실측 확인 —
docs/hosppass CLAUDE.md 세션 메모 참고). 도로명코드→도로명 텍스트 변환용 표준 데이터셋을
새로 구축하는 대신, 카카오 로컬 키워드 검색 API로 "시도 시군구 기관명"을 검색해
지번/도로명 주소, 전화번호, 좌표를 한 번에 얻는다 — 다른 카테고리(병원/약국 등)와
동일한 수준의 지도 마커·주소 표시를 위해서다.

data/ltc_list.json(fetch_ltc_list.py로 생성)을 읽어 longTermAdminSym별로
data/ltc_detail.json에 보강 정보를 누적 저장. 재실행 시 이미 처리된 기관은 건너뛰고
새 기관만 이어서 처리(카카오 무료 쿼터는 넉넉하지만, 혹시 모를 중단에 대비한
증분 캐시 — wooaapt의 fetch_apt_detail.py와 동일한 패턴).

검색 결과가 없는 기관(재가센터 등 카카오맵 미등록)은 matched=false로 저장해
주소/좌표 없이도 우편번호·시군구 정보만으로 페이지가 만들어지게 한다.

사용법:
  python scripts/fetch_ltc_detail.py            # 미완료분만 이어서 수집
  python scripts/fetch_ltc_detail.py --limit 500  # 테스트용 소량 수집
  python scripts/fetch_ltc_detail.py --force     # 전체 재수집
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv
from tqdm import tqdm

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"

load_dotenv(ROOT / ".env")
KAKAO_REST_KEY = os.getenv("KAKAO_REST_KEY")
if not KAKAO_REST_KEY:
    sys.exit("❌ .env에 KAKAO_REST_KEY 없음")

LIST_FILE = DATA_DIR / "ltc_list.json"
OUT_FILE = DATA_DIR / "ltc_detail.json"

SEARCH_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"
HEADERS = {"Authorization": f"KakaoAK {KAKAO_REST_KEY}"}
TIMEOUT = 15
CALL_DELAY = 0.08
MAX_RETRY = 3
SAVE_EVERY = 500


def _load_json(path: Path):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def _save_json(path: Path, data) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )


def search_kakao(query: str) -> dict | None:
    for attempt in range(1, MAX_RETRY + 1):
        try:
            resp = requests.get(
                SEARCH_URL, params={"query": query, "size": 1},
                headers=HEADERS, timeout=TIMEOUT,
            )
            if resp.status_code == 429:  # 쿼터 초과
                time.sleep(3 * attempt)
                continue
            resp.raise_for_status()
            data = resp.json()
            docs = data.get("documents", [])
            return docs[0] if docs else {}
        except requests.exceptions.RequestException:
            if attempt < MAX_RETRY:
                time.sleep(1.5 * attempt)
            else:
                return None
        finally:
            time.sleep(CALL_DELAY)
    return None


def main():
    parser = argparse.ArgumentParser(description="장기요양기관 주소 보강 (카카오)")
    parser.add_argument("--force", action="store_true", help="전체 재수집")
    parser.add_argument("--limit", type=int, default=0, help="이번 실행에서 처리할 최대 건수(0=무제한)")
    args = parser.parse_args()

    facilities = _load_json(LIST_FILE)
    if not facilities:
        sys.exit(f"❌ {LIST_FILE} 없음 — 먼저 python scripts/fetch_ltc_list.py 실행")
    items = facilities["items"]

    existing = {} if args.force else (_load_json(OUT_FILE) or {})
    todo = [it for it in items if str(it["longTermAdminSym"]) not in existing]

    print(f"[hosppass] 장기요양기관 주소 보강 시작 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
    print(f"  전체 {len(items):,}개 / 완료 {len(existing):,}개 / 남은 {len(todo):,}개")

    if args.limit:
        todo = todo[: args.limit]
        print(f"  이번 실행 처리 예정: {len(todo):,}개(--limit)")

    if not todo:
        print("  더 처리할 항목이 없습니다.")
        return

    matched_cnt = 0
    processed = 0
    try:
        for it in tqdm(todo, desc="주소 보강"):
            sym = str(it["longTermAdminSym"])
            query = f"{it.get('sido_nm','')} {it.get('sggu_nm','')} {it.get('adminNm','')}".strip()
            doc = search_kakao(query)

            if doc:
                existing[sym] = {
                    "matched": True,
                    "place_name": doc.get("place_name", ""),
                    "address": doc.get("address_name", ""),
                    "road_address": doc.get("road_address_name", ""),
                    "phone": doc.get("phone", ""),
                    "x": doc.get("x", ""),
                    "y": doc.get("y", ""),
                }
                matched_cnt += 1
            else:
                existing[sym] = {"matched": False}

            processed += 1
            if processed % SAVE_EVERY == 0:
                _save_json(OUT_FILE, existing)
    except KeyboardInterrupt:
        print("\n\n[중단] 지금까지 수집분 저장 중...")
    finally:
        _save_json(OUT_FILE, existing)

    print(f"\n  이번 실행 처리: {processed:,}개 (매칭 {matched_cnt:,}개)")
    print(f"  누적 완료: {len(existing):,}/{len(items):,}개")
    print(f"저장 완료: {OUT_FILE}")


if __name__ == "__main__":
    main()
