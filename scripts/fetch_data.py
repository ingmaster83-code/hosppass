"""
hosppass.kr 데이터 수집 스크립트
전국 병원/약국/응급의료기관 데이터를 공공데이터 API에서 수집해 JSON으로 저장.

실행: python scripts/fetch_data.py
재실행 시 이미 완료된 시도는 건너뜀 (--force 옵션으로 강제 재수집 가능)
"""

import os
import sys
import io
import json
import time
import argparse
import traceback
from pathlib import Path

# Windows 콘솔 UTF-8 강제 설정
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
from datetime import datetime

import requests
from dotenv import load_dotenv
from tqdm import tqdm

# ── 경로 설정 ──────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
REGIONS_DIR = DATA_DIR / "regions"
DATA_DIR.mkdir(exist_ok=True)
REGIONS_DIR.mkdir(exist_ok=True)

load_dotenv(ROOT / ".env")
API_KEY = os.getenv("API_KEY") or os.getenv("DATA_GO_KR_API_KEY")
if not API_KEY:
    sys.exit("❌ API 키 없음: .env에 API_KEY 또는 DATA_GO_KR_API_KEY 설정 필요")

# ── 시도 코드 ──────────────────────────────────────────────
SIDO_CODES = {
    "110000": "서울",
    "210000": "부산",
    "220000": "인천",
    "230000": "대구",
    "240000": "광주",
    "250000": "대전",
    "260000": "울산",
    "290000": "세종",
    "310000": "경기",
    "320000": "강원",
    "330000": "충북",
    "340000": "충남",
    "350000": "전북",
    "360000": "전남",
    "370000": "경북",
    "380000": "경남",
    "390000": "제주",
}

# ── API Base URLs ──────────────────────────────────────────
HOSP_BASE   = "https://apis.data.go.kr/B551182/hospInfoServicev2"
PHARM_BASE  = "https://apis.data.go.kr/B551182/pharmacyInfoService"
EMRG_BASE   = "https://apis.data.go.kr/B552657/ErmctInfoInqireService"
DETAIL_BASE = "https://apis.data.go.kr/B551182/MadmDtlInfoService2.8"
EVAL_BASE   = "https://apis.data.go.kr/B551182/hospAsmInfoService"

CALL_DELAY = 0.5   # API 호출 간격(초)
NUM_ROWS   = 1000  # 한 번에 가져올 최대 건수
TIMEOUT    = 30    # 요청 타임아웃(초)
MAX_RETRY  = 3     # 실패 시 재시도 횟수


# ── 공통 유틸 ──────────────────────────────────────────────

def _get(url: str, params: dict, retry: int = MAX_RETRY) -> dict | None:
    """GET 요청 + 재시도. 실패 시 None 반환."""
    params = {"serviceKey": API_KEY, "_type": "json", **params}
    for attempt in range(1, retry + 1):
        try:
            resp = requests.get(url, params=params, timeout=TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            # 공공데이터 공통 에러 응답 처리
            result_code = (
                data.get("response", {})
                    .get("header", {})
                    .get("resultCode", "00")
            )
            if result_code not in ("00", "0000"):
                result_msg = data["response"]["header"].get("resultMsg", "")
                print(f"\n  ⚠ API 오류 [{result_code}] {result_msg} — {url}")
                return None
            return data
        except requests.exceptions.RequestException as e:
            if attempt < retry:
                time.sleep(2 ** attempt)
            else:
                print(f"\n  ❌ 요청 실패 (시도 {attempt}/{retry}): {e}")
                return None
        finally:
            time.sleep(CALL_DELAY)


def _extract_items(data: dict) -> list:
    """공공데이터 표준 응답에서 item 리스트 추출."""
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


def _paginate(url: str, endpoint: str, base_params: dict, label: str) -> list:
    """전체 페이지를 순회해 모든 아이템 수집."""
    first = _get(url + endpoint, {**base_params, "pageNo": 1, "numOfRows": NUM_ROWS})
    if not first:
        return []

    total = _total_count(first)
    items = _extract_items(first)
    if total <= NUM_ROWS:
        return items

    total_pages = (total + NUM_ROWS - 1) // NUM_ROWS
    for page in tqdm(range(2, total_pages + 1), desc=f"  {label} 페이지", leave=False):
        data = _get(url + endpoint, {**base_params, "pageNo": page, "numOfRows": NUM_ROWS})
        if data:
            items.extend(_extract_items(data))

    return items


def _save_json(path: Path, data) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))


def _load_json(path: Path):
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return None


# ── 1. 병원 수집 ───────────────────────────────────────────

def fetch_hospitals(force: bool = False) -> list:
    """전국 병원 목록 수집. data/regions/[시도코드].json에 시도별 저장."""
    print("\n[1/3] 병원 데이터 수집")
    all_hospitals = []

    for sido_cd, sido_nm in tqdm(SIDO_CODES.items(), desc="시도별 병원"):
        region_file = REGIONS_DIR / f"{sido_cd}.json"

        if not force and region_file.exists():
            cached = _load_json(region_file)
            if cached and cached.get("hospitals"):
                tqdm.write(f"  ✓ {sido_nm} 캐시 사용 ({len(cached['hospitals'])}개)")
                all_hospitals.extend(cached["hospitals"])
                continue

        tqdm.write(f"  → {sido_nm} 수집 중...")
        items = _paginate(
            HOSP_BASE, "/getHospBasisList",
            {"sidoCd": sido_cd},
            sido_nm,
        )

        if not items:
            tqdm.write(f"  ⚠ {sido_nm} 데이터 없음 (기존 파일 유지)")
            continue

        # 필드 정리
        cleaned = [_clean_hospital(h) for h in items]
        tqdm.write(f"  ✓ {sido_nm} {len(cleaned)}개")

        # 시도별 저장 (기존 약국 데이터와 병합)
        region_data = _load_json(region_file) or {}
        region_data["hospitals"] = cleaned
        region_data["sido_cd"] = sido_cd
        region_data["sido_nm"] = sido_nm
        region_data["updated_at"] = datetime.now().isoformat()
        _save_json(region_file, region_data)

        all_hospitals.extend(cleaned)

    _save_json(DATA_DIR / "hospitals.json", {
        "total": len(all_hospitals),
        "updated_at": datetime.now().isoformat(),
        "items": all_hospitals,
    })
    print(f"  → 전국 병원 합계: {len(all_hospitals)}개")
    return all_hospitals


def _clean_hospital(h: dict) -> dict:
    return {
        "ykiho":     h.get("ykiho", ""),
        "name":      h.get("yadmNm", ""),
        "addr":      h.get("addr", ""),
        "tel":       h.get("telno", ""),
        "url":       h.get("hospUrl", ""),
        "sido_cd":   str(h.get("sidoCd", "")),
        "sido_nm":   h.get("sidoCdNm", ""),
        "sggu_cd":   str(h.get("sgguCd", "")),
        "sggu_nm":   h.get("sgguCdNm", ""),
        "emd_nm":    h.get("emdongNm", ""),
        "cl_cd":     str(h.get("clCd", "")),
        "cl_nm":     h.get("clCdNm", ""),
        "dgsbj":     h.get("dgsbjtCdNm", ""),   # 진료과목명 (쉼표 구분)
        "dr_cnt":    h.get("drTotCnt", 0),
        "sdr_cnt":   h.get("mdeptSdrCnt", 0),
        "x":         h.get("XPos", ""),          # 경도
        "y":         h.get("YPos", ""),          # 위도
        "estb_dd":   h.get("estbDd", ""),
    }


# ── 2. 약국 수집 ───────────────────────────────────────────

def fetch_pharmacies(force: bool = False) -> list:
    """전국 약국 목록 수집. data/regions/[시도코드].json에 병합 저장."""
    print("\n[2/3] 약국 데이터 수집")
    all_pharmacies = []

    for sido_cd, sido_nm in tqdm(SIDO_CODES.items(), desc="시도별 약국"):
        region_file = REGIONS_DIR / f"{sido_cd}.json"

        if not force and region_file.exists():
            cached = _load_json(region_file)
            if cached and cached.get("pharmacies"):
                tqdm.write(f"  ✓ {sido_nm} 캐시 사용 ({len(cached['pharmacies'])}개)")
                all_pharmacies.extend(cached["pharmacies"])
                continue

        tqdm.write(f"  → {sido_nm} 수집 중...")
        items = _paginate(
            PHARM_BASE, "/getParmacyBasisList",
            {"sidoCd": sido_cd},
            sido_nm,
        )

        if not items:
            tqdm.write(f"  ⚠ {sido_nm} 데이터 없음")
            continue

        cleaned = [_clean_pharmacy(p) for p in items]
        tqdm.write(f"  ✓ {sido_nm} {len(cleaned)}개")

        region_data = _load_json(region_file) or {}
        region_data["pharmacies"] = cleaned
        region_data.setdefault("sido_cd", sido_cd)
        region_data.setdefault("sido_nm", sido_nm)
        region_data["updated_at"] = datetime.now().isoformat()
        _save_json(region_file, region_data)

        all_pharmacies.extend(cleaned)

    _save_json(DATA_DIR / "pharmacies.json", {
        "total": len(all_pharmacies),
        "updated_at": datetime.now().isoformat(),
        "items": all_pharmacies,
    })
    print(f"  → 전국 약국 합계: {len(all_pharmacies)}개")
    return all_pharmacies


def _clean_pharmacy(p: dict) -> dict:
    return {
        "ykiho":   p.get("ykiho", ""),
        "name":    p.get("yadmNm", ""),
        "addr":    p.get("addr", ""),
        "tel":     p.get("telno", ""),
        "sido_cd": str(p.get("sidoCd", "")),
        "sido_nm": p.get("sidoCdNm", ""),
        "sggu_cd": str(p.get("sgguCd", "")),
        "sggu_nm": p.get("sgguCdNm", ""),
        "emd_nm":  p.get("emdongNm", ""),
        "x":       p.get("XPos", ""),
        "y":       p.get("YPos", ""),
    }


# ── 3. 응급의료기관 목록 추출 ───────────────────────────────
# getEgytBassInfoInqire는 전체 의료기관을 반환해 수집 시간이 너무 오래 걸림.
# 대신 이미 수집한 hospitals.json에서 종별코드(clCd)로 필터링.
# clCd 1=상급종합, 11=종합병원 → 응급실 보유 가능성 높은 기관만 추출.

def fetch_emergency(force: bool = False) -> list:
    """응급의료기관 목록을 hospitals.json에서 필터링해 추출."""
    print("\n[3/3] 응급의료기관 목록 추출")
    emrg_file = DATA_DIR / "emergency.json"

    if not force and emrg_file.exists():
        cached = _load_json(emrg_file)
        if cached and cached.get("items"):
            print(f"  ✓ 캐시 사용 ({cached['total']}개)")
            return cached["items"]

    hosp_file = DATA_DIR / "hospitals.json"
    if not hosp_file.exists():
        print("  [오류] hospitals.json 없음 — fetch_hospitals 먼저 실행 필요")
        return []

    hospitals = _load_json(hosp_file).get("items", [])
    # 상급종합(1) + 종합병원(11) 필터
    emrg_list = [h for h in hospitals if str(h.get("cl_cd", "")) in ("1", "11")]

    _save_json(emrg_file, {
        "total": len(emrg_list),
        "updated_at": datetime.now().isoformat(),
        "items": emrg_list,
    })
    print(f"  → 응급 가능 기관 합계: {len(emrg_list)}개 (상급종합+종합병원)")
    return emrg_list


# ── 4. 요양병원 상세 수집 ──────────────────────────────────

def fetch_nursing_hospitals(force: bool = False) -> list:
    """요양병원(clCd=28) 목록 + 상세정보(간호등급/투석/진료과목) 수집."""
    print("\n[4/4] 요양병원 데이터 수집")
    out_file = DATA_DIR / "nursing_hospitals.json"

    # 기존 파일에서 완료된 ykiho 목록 로드 (재실행 시 이어받기)
    existing = {}
    if not force and out_file.exists():
        cached = _load_json(out_file)
        if cached and cached.get("items"):
            existing = {h["ykiho"]: h for h in cached["items"] if h.get("_detail_done")}
            print(f"  기존 완료: {len(existing)}개 — 미완료분만 수집")

    # 전국 요양병원 기본 목록
    all_nursing = []
    for sido_cd, sido_nm in tqdm(SIDO_CODES.items(), desc="시도별 요양병원"):
        items = _paginate(
            HOSP_BASE, "/getHospBasisList",
            {"sidoCd": sido_cd, "clCd": "28"},
            sido_nm,
        )
        all_nursing.extend(items)

    print(f"  전국 요양병원 기본 목록: {len(all_nursing)}개")

    # 상세정보 수집 (ykiho별)
    results = []
    for item in tqdm(all_nursing, desc="상세정보 수집"):
        base = _clean_hospital(item)
        ykiho = base["ykiho"]

        if ykiho in existing:
            results.append(existing[ykiho])
            continue

        detail = _fetch_nursing_detail(ykiho)
        base.update(detail)
        base["_detail_done"] = True
        results.append(base)

        # 100건마다 중간 저장
        if len(results) % 100 == 0:
            _save_json(out_file, {
                "total": len(results),
                "updated_at": datetime.now().isoformat(),
                "items": results,
            })

    _save_json(out_file, {
        "total": len(results),
        "updated_at": datetime.now().isoformat(),
        "items": results,
    })
    print(f"  → 요양병원 합계: {len(results)}개")
    return results


def _fetch_nursing_detail(ykiho: str) -> dict:
    """요양병원 1개의 상세정보를 API 6종으로 수집."""
    detail = {}
    params = {"ykiho": ykiho, "pageNo": 1, "numOfRows": 100}

    # 1. 진료과목
    d = _get(DETAIL_BASE + "/getDgsbjtInfo2.8", params)
    if d:
        items = _extract_items(d)
        detail["dgsbj_list"] = [i.get("dgsbjtCdNm", "") for i in items if i.get("dgsbjtCdNm")]

    # 2. 의료장비 (투석기 확인)
    d = _get(DETAIL_BASE + "/getMedOftInfo2.8", params)
    if d:
        items = _extract_items(d)
        dialysis_cnt = 0
        for i in items:
            nm = i.get("medOftCdNm", "")
            cnt = i.get("medOftCnt", 0)
            if "인공신장기" in nm or "투석" in nm:
                try:
                    dialysis_cnt += int(cnt)
                except (ValueError, TypeError):
                    pass
        detail["dialysis"] = dialysis_cnt > 0
        detail["dialysis_machine_cnt"] = dialysis_cnt

    # 3. 특수진료 (혈액투석/복막투석)
    d = _get(DETAIL_BASE + "/getSpclDiagInfo2.8", params)
    if d:
        items = _extract_items(d)
        spcl = [i.get("spclDiagCdNm", "") for i in items if i.get("spclDiagCdNm")]
        detail["spcl_diag_list"] = spcl
        if not detail.get("dialysis"):
            detail["dialysis"] = any("투석" in s for s in spcl)

    # 4. 전문과목별 전문의수
    d = _get(DETAIL_BASE + "/getSpcSbjtSdrInfo2.8", params)
    if d:
        items = _extract_items(d)
        specialists = {}
        for i in items:
            nm = i.get("dgsbjtCdNm", "")
            cnt = i.get("sdrCnt", 0)
            if nm:
                specialists[nm] = int(cnt) if str(cnt).isdigit() else 0
        detail["specialist_map"] = specialists

    # 5. 간호등급
    d = _get(DETAIL_BASE + "/getNursigGrdInfo2.8", params)
    if d:
        items = _extract_items(d)
        if items:
            grade = items[0].get("nursingGrdCdNm", "") or items[0].get("nursingGrpCdNm", "")
            detail["nursing_grade"] = grade

    # 6. 세부정보 (병상수, 운영시간)
    d = _get(DETAIL_BASE + "/getDtlInfo2.8", params)
    if d:
        items = _extract_items(d)
        if items:
            i = items[0]
            detail["bed_cnt"]    = i.get("totBedCnt", 0)
            detail["hours"]      = _parse_hours(i)

    return detail


def _parse_hours(item: dict) -> str:
    """세부정보 응답에서 운영시간 문자열 조합."""
    parts = []
    mapping = [
        ("trmtMonStart", "trmtMonEnd",  "월"),
        ("trmtTueStart", "trmtTueEnd",  "화"),
        ("trmtWedStart", "trmtWedEnd",  "수"),
        ("trmtThuStart", "trmtThuEnd",  "목"),
        ("trmtFriStart", "trmtFriEnd",  "금"),
        ("trmtSatStart", "trmtSatEnd",  "토"),
        ("trmtSunStart", "trmtSunEnd",  "일"),
    ]
    for s_key, e_key, label in mapping:
        s = str(item.get(s_key, "") or "").strip()
        e = str(item.get(e_key, "") or "").strip()
        if s and e and s != "0" and e != "0":
            parts.append(f"{label} {s[:2]}:{s[2:]}~{e[:2]}:{e[2:]}")
        elif s == "0" or e == "0":
            parts.append(f"{label} 휴무")
    return " · ".join(parts) if parts else ""


# ── 메인 ───────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="hosppass 데이터 수집")
    parser.add_argument("--force", action="store_true", help="캐시 무시하고 전체 재수집")
    parser.add_argument("--only", choices=["hospitals", "pharmacies", "emergency", "nursing"],
                        help="특정 데이터만 수집")
    args = parser.parse_args()

    start = time.time()
    print(f"[hosppass] 데이터 수집 시작 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
    print(f"   API KEY: {API_KEY[:8]}...")

    try:
        if args.only == "hospitals":
            fetch_hospitals(force=args.force)
        elif args.only == "pharmacies":
            fetch_pharmacies(force=args.force)
        elif args.only == "emergency":
            fetch_emergency(force=args.force)
        elif args.only == "nursing":
            fetch_nursing_hospitals(force=args.force)
        else:
            fetch_hospitals(force=args.force)
            fetch_pharmacies(force=args.force)
            fetch_emergency(force=args.force)
            fetch_nursing_hospitals(force=args.force)

    except KeyboardInterrupt:
        print("\n\n[중단] 완료된 시도 데이터는 저장되어 있습니다.")
        print("   재실행 시 중단 지점부터 이어서 수집합니다.")
        sys.exit(0)
    except Exception:
        traceback.print_exc()
        sys.exit(1)

    elapsed = time.time() - start
    print(f"\n[완료] 소요시간: {elapsed/60:.1f}분")


if __name__ == "__main__":
    main()
