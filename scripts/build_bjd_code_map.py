#!/usr/bin/env python3
"""
build_bjd_code_map.py - 법정동코드(행정표준코드) 시도/시군구 매핑 테이블 생성
국토교통부_법정동코드 파일데이터(data.go.kr publicDataPk=15123287)를 내려받아
NHIS 장기요양기관 API가 사용하는 시도코드(2자리)/시군구코드(5자리) 체계를
사람이 읽을 수 있는 이름으로 매핑한 data/bjd_code_map.json을 생성한다.

⚠ 주의 1: 이 시도코드 체계는 hosppass/scripts/fetch_data.py의 SIDO_CODES(심평원 자체 코드,
예: 경기=31)와 다르다. NHIS 장기요양기관 API는 대체로 국토부 표준 법정동코드를 쓴다
(예: 경기=41, 세종=36). 실제 API 응답으로 실측 확인함(2026-09-09).

⚠ 주의 2: 딱 하나 예외가 있다 — 광주광역시는 표준코드(29)가 전혀 쓰이지 않고,
전라남도(표준코드 46)와 뒤섞인 채로 siDoCd=12 하나에 함께 들어있다(레거시 코드로 추정).
siGunGuCd로 27개 하위지역(광주 5개 구 + 전남 22개 시군)이 섞여 나오는데, 표준
법정동코드표에는 이 조합이 없어서 우편번호 역조회로 27건을 일일이 실측 확인했다.
이 특수 케이스는 fetch_ltc_list.py의 GWANGJU_JEONNAM_OVERRIDE에 하드코딩되어 있다 —
이 파일(build_bjd_code_map.py)이 만드는 표준 매핑과는 별도로 유지·적용됨.

행정구역 개편(강원특별자치도/전북특별자치도 전환 등)이 있을 때만 재실행하면 됨 —
평소에는 자동 갱신 대상이 아님.

사용법:
  python scripts/build_bjd_code_map.py
"""
import csv
import io
import json
import sys
from pathlib import Path

import requests

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).parent.parent
OUT_FILE = ROOT / "data" / "bjd_code_map.json"

PUBLIC_DATA_PK = "15123287"
PUBLIC_DATA_DETAIL_PK = "uddi:d6c67241-a722-48c4-8041-d66ff243cf57"

# NHIS 장기요양기관 API가 실제로 쓰는 표준 시도코드 (API 응답으로 실측 확인)
STD_SIDO = {
    "11": "서울", "26": "부산", "27": "대구", "28": "인천", "29": "광주",
    "30": "대전", "31": "울산", "36": "세종", "41": "경기", "51": "강원",
    "43": "충북", "44": "충남", "52": "전북", "46": "전남", "47": "경북",
    "48": "경남", "50": "제주",
}


def _get_atch_file_id() -> tuple[str, str]:
    """selectFileDataDownload.do 호출로 실제 다운로드에 필요한 atchFileId 취득."""
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
    data_nm = j["dataSetFileDetailInfo"]["dataNm"]
    return j["atchFileId"], data_nm


def _download_csv(atch_file_id: str, data_nm: str) -> bytes:
    resp = requests.get(
        "https://www.data.go.kr/cmm/cmm/fileDownload.do",
        params={"atchFileId": atch_file_id, "fileDetailSn": "1", "dataNm": data_nm},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.content


def main():
    print("법정동코드 파일 다운로드 준비...")
    atch_file_id, data_nm = _get_atch_file_id()
    print(f"  atchFileId={atch_file_id}")

    raw = _download_csv(atch_file_id, data_nm)
    print(f"  다운로드 완료: {len(raw):,} bytes")

    text = raw.decode("cp949", errors="replace")
    reader = csv.reader(io.StringIO(text))
    next(reader)  # header

    sggu_map: dict[str, str] = {}
    for row in reader:
        if len(row) < 3:
            continue
        code, name, status = row[0].strip(), row[1].strip(), row[2].strip()
        if status != "존재" or len(code) != 10:
            continue
        sido2 = code[:2]
        if sido2 not in STD_SIDO:
            continue
        if code[5:] != "00000" or code[2:5] == "000":
            continue  # 시군구 레벨만 (시도 자체 행, 읍면동 이하 행 제외)
        key = code[:5]
        parts = name.split(" ", 1)
        sggu_map[key] = parts[1] if len(parts) > 1 else parts[0]

    print(f"  시군구 {len(sggu_map)}개 매핑 완료")

    OUT_FILE.parent.mkdir(exist_ok=True)
    OUT_FILE.write_text(
        json.dumps({"sido": STD_SIDO, "sggu": sggu_map}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    print(f"저장 완료: {OUT_FILE}")


if __name__ == "__main__":
    main()
