# -*- coding: utf-8 -*-
"""새 hospitals.json(HIRA 병합본)에서 응급의료기관만 추려 docs/data/emergency.json 재생성 (풍부한 필드 포함)"""
import sys, json
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path

SRC = Path(r"C:\개인\wooahouse\hosppass\data\hospitals.json")
OUT = Path(r"C:\개인\wooahouse\hosppass\docs\data\emergency.json")

with open(SRC, encoding='utf-8') as f:
    data = json.load(f)

items = data['items']

def is_er(h):
    if h.get('er_day') or h.get('er_night'):
        return True
    beds = h.get('beds') or {}
    if (beds.get('er') or 0) > 0:
        return True
    if any('응급의료기관' in s for s in (h.get('special_treatments') or [])):
        return True
    return False

er_list = [h for h in items if is_er(h)]
print(f"응급의료기관 추출: {len(er_list)}건 (전체 {len(items)}건 중)")

OUT.parent.mkdir(parents=True, exist_ok=True)
with open(OUT, 'w', encoding='utf-8') as f:
    json.dump({"total": len(er_list), "updated_at": "2026-03", "items": er_list}, f, ensure_ascii=False, separators=(",", ":"))

print(f"저장 완료: {OUT}")
