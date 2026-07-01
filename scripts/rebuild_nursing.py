# -*- coding: utf-8 -*-
"""새 hospitals.json(HIRA 병합본)에서 요양병원(cl_nm=요양병원)만 추려
data/nursing_hospitals.json 재생성 (간호등급·투석 정보를 새 벌크 데이터에서 뽑아 채움).

기존 nursing_hospitals.json은 구 라이브 API(getNursigGrdInfo2.8)로 수집했으나
해당 API가 거의 항상 빈 값을 반환해 간호등급 데이터가 사실상 없었음(1281건 중 1229건 공백).
새 HIRA 벌크 파일에는 간호등급정보가 별도 파일로 포함되어 있어 이를 대신 사용한다.
"""
import sys, json
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path

SRC = Path(r"C:\개인\wooahouse\hosppass\data\hospitals.json")
OUT = Path(r"C:\개인\wooahouse\hosppass\data\nursing_hospitals.json")

with open(SRC, encoding='utf-8') as f:
    data = json.load(f)

items = data['items']
yoyang = [h for h in items if h.get('cl_nm') == '요양병원']
print(f"요양병원 추출: {len(yoyang)}건 (전체 {len(items)}건 중)")


def nursing_grade(h):
    for n in (h.get('nursing') or []):
        if n.get('type') == '간호인력' and n.get('grade'):
            return f"{n['grade']}등급"
    return ""


def is_dialysis(h):
    if any('신장' in (e.get('name') or '') or '투석' in (e.get('name') or '') for e in (h.get('equipment') or [])):
        return True
    if any('투석' in s for s in (h.get('special_treatments') or [])):
        return True
    return False


def dialysis_machine_cnt(h):
    total = 0
    for e in (h.get('equipment') or []):
        if '신장' in (e.get('name') or '') or '투석' in (e.get('name') or ''):
            total += e.get('count') or 0
    return total


def bed_cnt(h):
    beds = h.get('beds') or {}
    return sum(v for v in beds.values() if isinstance(v, (int, float))) or None


out_items = []
for h in yoyang:
    out_items.append({
        "ykiho": h.get("ykiho"),
        "name": h.get("name"),
        "addr": h.get("addr"),
        "tel": h.get("tel"),
        "url": h.get("url"),
        "sido_nm": h.get("sido_nm"),
        "sggu_nm": h.get("sggu_nm"),
        "emd_nm": h.get("emd_nm"),
        "cl_cd": h.get("cl_cd"),
        "cl_nm": h.get("cl_nm"),
        "dr_cnt": h.get("dr_cnt"),
        "x": h.get("x"),
        "y": h.get("y"),
        "estb_dd": h.get("estb_dd"),
        "dgsbj_list": [d.get("name") for d in (h.get("departments") or []) if d.get("name")],
        "dialysis": is_dialysis(h),
        "dialysis_machine_cnt": dialysis_machine_cnt(h),
        "nursing_grade": nursing_grade(h),
        "bed_cnt": bed_cnt(h),
    })

OUT.parent.mkdir(parents=True, exist_ok=True)
with open(OUT, 'w', encoding='utf-8') as f:
    json.dump({"total": len(out_items), "updated_at": "2026-03", "items": out_items}, f, ensure_ascii=False, separators=(",", ":"))

print(f"저장 완료: {OUT}")

from collections import Counter
c = Counter(i["nursing_grade"] for i in out_items if i["nursing_grade"])
print("간호등급 분포:", sorted(c.items()))
print("투석 가능:", sum(1 for i in out_items if i["dialysis"]))
