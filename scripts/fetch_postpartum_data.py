"""
hosppass.kr 산후조리원 데이터 수집 스크립트
보건복지부_전국 산후조리원 현황(2023-12-31 기준, 1회성 데이터) CSV를 내려받아
data/postpartum_centers.json으로 정규화한다.

원본이 "수시(1회성)" 갱신이라 매일 돌릴 필요는 없지만, 재수집이 필요하면
python scripts/fetch_postpartum_data.py 로 다시 받을 수 있다.
"""
import csv
import io
import json
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
RAW_PATH = DATA_DIR / "postpartum_raw.csv"
OUT_PATH = DATA_DIR / "postpartum_centers.json"

# data.go.kr 파일 다운로드 (2026-08-15 기준 확인된 첨부파일 ID)
DOWNLOAD_URL = "https://www.data.go.kr/cmm/cmm/fileDownload.do?atchFileId=FILE_000000003155385&fileDetailSn=1"

OPERATOR_MAP = {
    "지자체": "공공",
    "민간": "민간",
}


def download():
    resp = requests.get(DOWNLOAD_URL, timeout=30)
    resp.raise_for_status()
    if len(resp.content) < 1000:
        raise SystemExit("다운로드 실패로 추정 — 응답 크기가 너무 작음")
    DATA_DIR.mkdir(exist_ok=True)
    RAW_PATH.write_bytes(resp.content)
    print(f"다운로드 완료: {RAW_PATH} ({len(resp.content)} bytes)")


def parse():
    with open(RAW_PATH, encoding="cp949") as f:
        reader = csv.reader(f)
        rows = list(reader)

    records = []
    for r in rows[1:]:
        if len(r) < 9:
            continue
        num, sido, sggu, operator, name, addr, tel, general_room, special_room = r[:9]
        records.append({
            "name": name.strip(),
            "operator": OPERATOR_MAP.get(operator.strip(), operator.strip()),
            "sido_nm": sido.strip(),
            "sggu_nm": sggu.strip(),
            "addr": addr.strip(),
            "tel": tel.strip(),
            "general_room_price": general_room.strip(),
            "special_room_price": special_room.strip(),
        })
    return records


def main():
    if not RAW_PATH.exists():
        print("원본 CSV 없음 — 다운로드 시도")
        download()

    records = parse()
    print(f"총 {len(records)}건 파싱 완료")
    public_cnt = sum(1 for r in records if r["operator"] == "공공")
    print(f"공공 {public_cnt}건 / 민간 {len(records) - public_cnt}건")

    OUT_PATH.write_text(
        json.dumps({"items": records}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"저장 완료: {OUT_PATH}")


if __name__ == "__main__":
    main()
