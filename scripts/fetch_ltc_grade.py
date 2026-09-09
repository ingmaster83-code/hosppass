#!/usr/bin/env python3
"""
fetch_ltc_grade.py - 장기요양기관 평가등급(A~E) 수집
국민건강보험공단_장기요양기관 평가 결과(data.go.kr id 15104801, 파일데이터 CSV,
로그인/활용신청 불필요)를 내려받아 longTermAdminSym 기준으로 최신 평가만 남긴다.

⚠ CSV의 "장기요양기관기호"는 "1-11560-00018" 형식(하이픈 포함)이고,
NHIS API의 longTermAdminSym은 "11156000018"(하이픈 없는 숫자)이다.
하이픈만 제거하면 그대로 일치함 — 실측 확인(2026-09-09).

같은 기관이 여러 연도에 걸쳐 평가받은 행이 있을 수 있어 평가일자 기준 최신 1건만 보관.

사용법:
  python scripts/fetch_ltc_grade.py
"""
import csv
import io
import json
import sys
from datetime import datetime
from pathlib import Path

import requests

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
OUT_FILE = DATA_DIR / "ltc_grades.json"

PUBLIC_DATA_PK = "15104801"
PUBLIC_DATA_DETAIL_PK = "uddi:894abcb2-822d-4e53-87a3-9d805e5c915d"


def _get_atch_file_id() -> tuple[str, str]:
    resp = requests.post(
        "https://www.data.go.kr/tcs/dss/selectFileDataDownload.do",
        data={
            "publicDataDetailPk": PUBLIC_DATA_DETAIL_PK,
            "publicDataPk": PUBLIC_DATA_PK,
            "atchFileId": "",
            "fileDetailSn": "1",
            "publicDataTyCode": "PR0051",
        },
        timeout=30,
    )
    resp.raise_for_status()
    j = resp.json()
    if not j.get("status"):
        raise SystemExit(f"파일 다운로드 준비 실패: {j}")
    return j["atchFileId"], j["dataSetFileDetailInfo"]["dataNm"]


def _download_csv(atch_file_id: str, data_nm: str) -> bytes:
    resp = requests.get(
        "https://www.data.go.kr/cmm/cmm/fileDownload.do",
        params={"atchFileId": atch_file_id, "fileDetailSn": "1", "dataNm": data_nm},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.content


def main():
    print("장기요양기관 평가결과 파일 다운로드 준비...")
    atch_file_id, data_nm = _get_atch_file_id()
    raw = _download_csv(atch_file_id, data_nm)
    print(f"  다운로드 완료: {len(raw):,} bytes")

    text = raw.decode("cp949", errors="replace")
    reader = csv.DictReader(io.StringIO(text))

    grades: dict[int, dict] = {}
    total_rows = 0
    for row in reader:
        total_rows += 1
        code_raw = (row.get("장기요양기관기호") or "").strip()
        sym_str = code_raw.replace("-", "")
        if not sym_str.isdigit():
            continue
        sym = int(sym_str)

        eval_date = (row.get("평가일자") or "").strip()
        existing = grades.get(sym)
        if existing and existing["evalDate"] >= eval_date:
            continue  # 이미 더 최신(또는 동일) 평가 보관 중

        grades[sym] = {
            "evalType": (row.get("평가구분") or "").strip(),
            "benefitType": (row.get("급여종류") or "").strip(),
            "evalDate": eval_date,
            "grade": (row.get("평가등급") or "").strip(),
            "totalScore": (row.get("평가총점") or "").strip(),
        }

    print(f"  원본 {total_rows:,}행 → 기관별 최신 평가 {len(grades):,}건")

    DATA_DIR.mkdir(exist_ok=True)
    OUT_FILE.write_text(
        json.dumps(
            {"total": len(grades), "updated_at": datetime.now().isoformat(), "items": grades},
            ensure_ascii=False, separators=(",", ":"),
        ),
        encoding="utf-8",
    )
    print(f"저장 완료: {OUT_FILE}")


if __name__ == "__main__":
    main()
