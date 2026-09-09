#!/usr/bin/env python3
"""
fetch_ltc_list.py - 전국 장기요양기관(노인요양원 등) 목록 수집
국민건강보험공단_장기요양기관 검색 서비스(B550928/searchLtcInsttService02)를
17개 시도별로 순회 수집해 data/ltc_list.json 생성.

⚠ 이 API의 시도코드는 hosppass의 기존 SIDO_CODES(심평원 코드)와 다른
국토부 표준 법정동코드 체계다 (예: 경기=41, 세종=36, 부산=26).
data/bjd_code_map.json(scripts/build_bjd_code_map.py로 생성)으로 이름 매핑.

⚠ 딱 하나 예외: 광주광역시는 표준코드(29)를 안 쓰고 siDoCd=12 하나에
전라남도(표준코드 46)와 섞여 들어있다. siGunGuCd 27종(광주 5구+전남 22시군)을
우편번호 역조회로 실측해 GWANGJU_JEONNAM_OVERRIDE에 하드코딩— siDoCd="12"인
행은 표준 코드맵을 안 쓰고 이 오버라이드로만 처리한다(2026-09-09 확인).

응답은 (시설 × 급여종류) 조합 단위라 longTermAdminSym(장기요양기관코드) 기준으로
중복 제거해야 시설 수가 된다. adminPttnCd(기관유형코드)는 상세조회 API 호출에
필요해 대표값 하나만 보관.

사용법:
  python scripts/fetch_ltc_list.py
"""
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
API_KEY = os.getenv("API_KEY") or os.getenv("DATA_GO_KR_API_KEY")
if not API_KEY:
    sys.exit("❌ API 키 없음: .env에 API_KEY 설정 필요")

LIST_BASE = "https://apis.data.go.kr/B550928/searchLtcInsttService02/getLtcInsttSeachList02"
NUM_ROWS = 1000
TIMEOUT = 30
MAX_RETRY = 3
CALL_DELAY = 0.3

CODE_MAP_FILE = DATA_DIR / "bjd_code_map.json"
OUT_FILE = DATA_DIR / "ltc_list.json"

# siDoCd=12는 표준 법정동코드에 없는 NHIS 자체 레거시 코드로, 광주광역시(5개 구)와
# 전라남도(22개 시군)가 뒤섞여 나온다. 우편번호 역조회 + 기관명 자체 확인으로
# siGunGuCd 27종 전부 실측 완료(2026-09-09).
GWANGJU_JEONNAM_OVERRIDE = {
    # 광주광역시
    "210": ("광주", "동구"),
    "240": ("광주", "서구"),
    "270": ("광주", "남구"),
    "300": ("광주", "북구"),
    "330": ("광주", "광산구"),
    # 전라남도
    "110": ("전남", "목포시"),
    "130": ("전남", "여수시"),
    "150": ("전남", "순천시"),
    "170": ("전남", "나주시"),
    "190": ("전남", "광양시"),
    "710": ("전남", "담양군"),
    "720": ("전남", "곡성군"),
    "730": ("전남", "구례군"),
    "740": ("전남", "고흥군"),
    "750": ("전남", "보성군"),
    "760": ("전남", "화순군"),
    "770": ("전남", "장흥군"),
    "780": ("전남", "강진군"),
    "790": ("전남", "해남군"),
    "800": ("전남", "영암군"),
    "810": ("전남", "무안군"),
    "820": ("전남", "함평군"),
    "830": ("전남", "영광군"),
    "840": ("전남", "장성군"),
    "850": ("전남", "완도군"),
    "860": ("전남", "진도군"),
    "870": ("전남", "신안군"),
}

# 기타 표준 코드맵에 없던 (siDoCd, siGunGuCd) 조합 — 우편번호/기관명 역조회로 실측 확인.
# 경기 591/593/595/597: 전부 화성시 우편번호대(18xxx)로 확인 — 화성시 옛 출장소별 코드로 추정.
# 인천 125/275: 2026-07-01 인천 행정체제 개편(중구→제물포구/영종구, 서구→서해구/검단구)
# 직후라 표준 코드맵이 아직 못 따라감. hosppass 기존 병원 데이터가 여전히 옛 구명(서구·중구)을
# 쓰고 있어 사이트 전체 일관성을 위해 신설구 이름 대신 옛 구명으로 매핑.
EXTRA_OVERRIDE = {
    ("41", "591"): ("경기", "화성시"),
    ("41", "593"): ("경기", "화성시"),
    ("41", "595"): ("경기", "화성시"),
    ("41", "597"): ("경기", "화성시"),
    ("28", "125"): ("인천", "중구"),   # 2026-07 제물포구로 개편, 옛 구명 유지
    ("28", "155"): ("인천", "중구"),   # 표준코드(110)와 별개로 쓰이는 두번째 중구 코드(영종·무의도 등 도서권 추정)
    ("28", "275"): ("인천", "서구"),   # 2026-07 검단구로 개편, 옛 구명 유지
    ("28", "290"): ("인천", "서구"),   # 표준코드(260)와 별개로 쓰이는 두번째 서구 코드
}


def _load_code_map() -> dict:
    if not CODE_MAP_FILE.exists():
        sys.exit(f"❌ {CODE_MAP_FILE} 없음 — 먼저 python scripts/build_bjd_code_map.py 실행")
    return json.loads(CODE_MAP_FILE.read_text(encoding="utf-8"))


def _get(params: dict, retry: int = MAX_RETRY) -> dict | None:
    params = {"serviceKey": API_KEY, "_type": "json", **params}
    for attempt in range(1, retry + 1):
        try:
            resp = requests.get(LIST_BASE, params=params, timeout=TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            result_code = data.get("response", {}).get("header", {}).get("resultCode", "00")
            if result_code not in ("00", "0000"):
                msg = data["response"]["header"].get("resultMsg", "")
                print(f"\n  ⚠ API 오류 [{result_code}] {msg}")
                return None
            return data
        except requests.exceptions.RequestException as e:
            if attempt < retry:
                time.sleep(2 ** attempt)
            else:
                print(f"\n  ❌ 요청 실패: {e}")
                return None
        finally:
            time.sleep(CALL_DELAY)


def _extract_items(data: dict) -> list:
    try:
        items = data["response"]["body"]["items"]["item"]
        return items if isinstance(items, list) else [items]
    except (KeyError, TypeError):
        return []


def _total_count(data: dict) -> int:
    try:
        return int(data["response"]["body"]["totalCount"])
    except (KeyError, TypeError, ValueError):
        return 0


def fetch_sido(sido_cd: str, sido_nm: str) -> list:
    first = _get({"siDoCd": sido_cd, "pageNo": 1, "numOfRows": NUM_ROWS})
    if not first:
        return []
    total = _total_count(first)
    items = _extract_items(first)
    if total <= NUM_ROWS:
        return items

    total_pages = (total + NUM_ROWS - 1) // NUM_ROWS
    for page in tqdm(range(2, total_pages + 1), desc=f"  {sido_nm} 페이지", leave=False):
        data = _get({"siDoCd": sido_cd, "pageNo": page, "numOfRows": NUM_ROWS})
        if data:
            items.extend(_extract_items(data))
    return items


def main():
    code_map = _load_code_map()
    std_sido = code_map["sido"]
    sggu_map = code_map["sggu"]

    # 실제 API 조회 대상 시도코드: 표준 매핑에서 광주(29)·전남(46)은 늘 0건이라 빼고,
    # 그 둘이 뒤섞여 들어있는 레거시 통합 코드 "12"를 대신 넣는다(실측 확인, 2026-09-09).
    fetch_targets = {cd: nm for cd, nm in std_sido.items() if cd not in ("29", "46")}
    fetch_targets["12"] = "광주·전남"

    print(f"[hosppass] 장기요양기관 목록 수집 시작 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")

    by_code: dict[int, dict] = {}
    for sido_cd, sido_nm in tqdm(fetch_targets.items(), desc="시도별 수집"):
        raw_items = fetch_sido(sido_cd, sido_nm)
        tqdm.write(f"  → {sido_nm}({sido_cd}) {len(raw_items)}행 수집")
        for it in raw_items:
            sym = it.get("longTermAdminSym")
            if not sym:
                continue
            sym = int(sym)
            if sym in by_code:
                continue  # 같은 기관의 다른 급여종류 행 — 첫 값만 사용
            sido_cd_s = str(it.get("siDoCd", "")).zfill(2)
            sggu_cd_s = str(it.get("siGunGuCd", "")).zfill(3)

            if sido_cd_s == "12":  # 광주+전남 레거시 통합 코드 — 오버라이드 전용 처리
                override = GWANGJU_JEONNAM_OVERRIDE.get(sggu_cd_s)
                item_sido_nm = override[0] if override else ""
                item_sggu_nm = override[1] if override else ""
            elif (sido_cd_s, sggu_cd_s) in EXTRA_OVERRIDE:
                item_sido_nm, item_sggu_nm = EXTRA_OVERRIDE[(sido_cd_s, sggu_cd_s)]
            else:
                item_sido_nm = std_sido.get(sido_cd_s, "")
                item_sggu_nm = sggu_map.get(sido_cd_s + sggu_cd_s, "")

            by_code[sym] = {
                "longTermAdminSym": sym,
                "adminPttnCd": it.get("adminPttnCd", ""),
                "adminNm": it.get("adminNm", ""),
                "siDoCd": sido_cd_s,
                "siGunGuCd": sggu_cd_s,
                "sido_nm": item_sido_nm,
                "sggu_nm": item_sggu_nm,
                "longTermPeribRgtDt": it.get("longTermPeribRgtDt", ""),
                "stpRptDt": it.get("stpRptDt", ""),
            }

    items = list(by_code.values())
    unmatched = sum(1 for i in items if not i["sggu_nm"])
    print(f"\n  전국 장기요양기관(중복제거) 합계: {len(items):,}개")
    if unmatched:
        print(f"  ⚠ 시군구명 매칭 실패: {unmatched}개 (bjd_code_map.json 갱신 필요할 수 있음)")

    DATA_DIR.mkdir(exist_ok=True)
    OUT_FILE.write_text(
        json.dumps(
            {"total": len(items), "updated_at": datetime.now().isoformat(), "items": items},
            ensure_ascii=False, separators=(",", ":"),
        ),
        encoding="utf-8",
    )
    print(f"저장 완료: {OUT_FILE}")


if __name__ == "__main__":
    main()
