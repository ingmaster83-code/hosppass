# -*- coding: utf-8 -*-
"""
HIRA 전국 병의원 및 약국 현황(2026.3) 12개 xlsx 파일을 병합해
병원 하나당 풍부한 통합 프로필(data/hospitals.json)을 생성한다.
API 호출 없이 다운로드한 파일만으로 처리 — 사용자가 data.go.kr에서 수동 다운로드한 파일 사용.
"""
import sys, json, time
sys.stdout.reconfigure(encoding='utf-8')
import openpyxl
from pathlib import Path
from collections import defaultdict

BASE = Path(r"C:\Users\ingma\Downloads\전국 병의원 및 약국 현황 2026.3\전국 병의원 및 약국 현황 2026.3")
OUT_DIR = Path(r"C:\개인\wooahouse\hosppass\data")

F_HOSP      = BASE / "1.병원정보서비스(2026.3.).xlsx"
F_PHARM     = BASE / "2.약국정보서비스(2026.3.).xlsx"
F_FACILITY  = BASE / "3.의료기관별상세정보서비스_01_시설정보(2026.3.).xlsx"
F_DETAIL    = BASE / "4.의료기관별상세정보서비스_02_세부정보(2026.3.).xlsx"
F_DEPT      = BASE / "5.의료기관별상세정보서비스_03_진료과목정보(2026.3.).xlsx"
F_TRANSIT   = BASE / "6.의료기관별상세정보서비스_04_교통정보(2026.3.).xlsx"
F_EQUIP     = BASE / "7.의료기관별상세정보서비스_05_의료장비정보(2026.3.).xlsx"
F_MEAL      = BASE / "8.의료기관별상세정보서비스_06_식대가산정보(2026.3.).xlsx"
F_NURSING   = BASE / "9.의료기관별상세정보서비스_07_간호등급정보(2026.3.).xlsx"
F_SPECIAL   = BASE / "10.의료기관별상세정보서비스_08_특수진료정보서비스(2026.3.).xlsx"
F_SPCHOSP   = BASE / "11.의료기관별상세정보서비스_09_전문병원지정분야(2026.3.).xlsx"
F_STAFF     = BASE / "12.의료기관별상세정보서비스_10_기타인력정보(2026.3.).xlsx"


def rows(path, header_map=None):
    """openpyxl read_only 순회, header 이름 -> 인덱스 매핑으로 dict 반환"""
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    it = ws.iter_rows(values_only=True)
    header = next(it)
    idx = {h: i for i, h in enumerate(header)}
    for row in it:
        yield {h: row[i] for h, i in idx.items()}
    wb.close()


def s(v):
    if v is None:
        return ""
    return str(v).strip()


def hhmm(v):
    """엑셀에서 900, 1800 같은 숫자 또는 문자열 -> 'HH:MM' """
    v = s(v)
    if not v or v == "0":
        return ""
    v = v.zfill(4)
    return f"{v[:2]}:{v[2:]}"


def yn(v):
    return s(v).upper() == "Y"


print("[1/12] 시설정보(병상) 로드 중...")
t0 = time.time()
beds_map = {}
for r in rows(F_FACILITY):
    k = r["암호화요양기호"]
    beds_map[k] = {
        "general_upper": r.get("일반입원실상급병상수") or 0,
        "general":       r.get("일반입원실일반병상수") or 0,
        "icu_adult":     r.get("성인중환자병상수") or 0,
        "icu_child":     r.get("소아중환자병상수") or 0,
        "icu_newborn":   r.get("신생아중환자병상수") or 0,
        "delivery":      r.get("분만실병상수") or 0,
        "operating":     r.get("수술실병상수") or 0,
        "er":            r.get("응급실병상수") or 0,
        "physical_therapy": r.get("물리치료실병상수") or 0,
        "isolation":     r.get("격리병실병상수") or 0,
    }
print(f"   {len(beds_map)}건 ({time.time()-t0:.1f}s)")

print("[2/12] 세부정보(진료시간/야간응급) 로드 중...")
t0 = time.time()
detail_map = {}
DAYS = [("월", "월요일"), ("화", "화요일"), ("수", "수요일"), ("목", "목요일"),
        ("금", "금요일"), ("토", "토요일"), ("일", "일요일")]
for r in rows(F_DETAIL):
    k = r["암호화요양기호"]
    hours = {}
    for label, full in DAYS:
        st = r.get(f"진료시작시간_{full}")
        et = r.get(f"진료종료시간_{full}")
        if st or et:
            hours[label] = {"start": hhmm(st), "end": hhmm(et)}
    detail_map[k] = {
        "hours": hours,
        "lunch_weekday": s(r.get("점심시간_평일")),
        "lunch_sat": s(r.get("점심시간_토요일")),
        "reception_weekday": s(r.get("접수시간_평일")),
        "reception_sat": s(r.get("접수시간_토요일")),
        "closed_sun": s(r.get("휴진안내_일요일")),
        "closed_holiday": s(r.get("휴진안내_공휴일")),
        "er_day": yn(r.get("응급실_주간_운영여부")),
        "er_day_tel": [t for t in [s(r.get("응급실_주간_전화번호1")), s(r.get("응급실_주간_전화번호2"))] if t],
        "er_night": yn(r.get("응급실_야간_운영여부")),
        "er_night_tel": [t for t in [s(r.get("응급실_야간_전화번호1")), s(r.get("응급실_야간_전화번호2"))] if t],
        "location_note": " ".join(filter(None, [s(r.get("위치_공공건물(장소)명")), s(r.get("위치_방향")), s(r.get("위치_거리"))])),
        "parking_available": s(r.get("주차_가능대수")) not in ("", "0"),
        "parking_count": r.get("주차_가능대수") or 0,
        "parking_fee": s(r.get("주차_비용 부담여부")).upper() == "Y",
        "parking_note": s(r.get("주차_기타 안내사항")),
    }
print(f"   {len(detail_map)}건 ({time.time()-t0:.1f}s)")

print("[3/12] 진료과목정보 로드 중...")
t0 = time.time()
dept_map = defaultdict(list)
for r in rows(F_DEPT):
    k = r["암호화요양기호"]
    dept_map[k].append({
        "code": s(r.get("진료과목코드")),
        "name": s(r.get("진료과목코드명")),
        "specialist_cnt": r.get("과목별 전문의수") or 0,
    })
print(f"   {len(dept_map)}개 기관, 총 항목 다수 ({time.time()-t0:.1f}s)")

print("[4/12] 교통정보 로드 중...")
t0 = time.time()
transit_map = defaultdict(list)
for r in rows(F_TRANSIT):
    k = r["암호화요양기호"]
    transit_map[k].append({
        "type": s(r.get("교통편명")),
        "line": s(r.get("노선번호")),
        "stop": s(r.get("하차지점")),
        "direction": s(r.get("방향")),
        "distance": s(r.get("거리")),
        "note": s(r.get("비고")),
    })
print(f"   {len(transit_map)}개 기관 ({time.time()-t0:.1f}s)")

print("[5/12] 의료장비정보 로드 중...")
t0 = time.time()
equip_map = defaultdict(list)
for r in rows(F_EQUIP):
    k = r["암호화요양기호"]
    equip_map[k].append({
        "code": s(r.get("장비코드")),
        "name": s(r.get("장비코드명")),
        "count": r.get("장비대수") or 0,
    })
print(f"   {len(equip_map)}개 기관 ({time.time()-t0:.1f}s)")

print("[6/12] 식대가산정보 로드 중...")
t0 = time.time()
meal_map = defaultdict(list)
for r in rows(F_MEAL):
    k = r["암호화요양기호"]
    meal_map[k].append({
        "type": s(r.get("유형코드명")),
        "addl_fee": s(r.get("일반식 가산여부")).upper() == "Y",
        "staff_cnt": r.get("산정인원수") or 0,
        "grade": s(r.get("치료식 등급")),
    })
print(f"   {len(meal_map)}개 기관 ({time.time()-t0:.1f}s)")

print("[7/12] 간호등급정보 로드 중...")
t0 = time.time()
nursing_map = defaultdict(list)
for r in rows(F_NURSING):
    k = r["암호화요양기호"]
    nursing_map[k].append({
        "type": s(r.get("유형코드명")),
        "grade": r.get("간호등급"),
    })
print(f"   {len(nursing_map)}개 기관 ({time.time()-t0:.1f}s)")

print("[8/12] 특수진료정보 로드 중...")
t0 = time.time()
special_map = defaultdict(list)
for r in rows(F_SPECIAL):
    k = r["암호화요양기호"]
    special_map[k].append(s(r.get("검색코드명")))
print(f"   {len(special_map)}개 기관 ({time.time()-t0:.1f}s)")

print("[9/12] 전문병원지정분야 로드 중...")
t0 = time.time()
spchosp_map = defaultdict(list)
for r in rows(F_SPCHOSP):
    k = r["암호화요양기호"]
    spchosp_map[k].append(s(r.get("검색코드명")))
print(f"   {len(spchosp_map)}개 기관 ({time.time()-t0:.1f}s)")

print("[10/12] 기타인력정보 로드 중...")
t0 = time.time()
staff_map = defaultdict(list)
for r in rows(F_STAFF):
    k = r["암호화요양기호"]
    staff_map[k].append({
        "code": s(r.get("기타인력코드")),
        "name": s(r.get("기타인력코드명")),
        "count": r.get("기타인력수") or 0,
    })
print(f"   {len(staff_map)}개 기관 ({time.time()-t0:.1f}s)")

print("[11/12] 병원 마스터 병합 중...")
t0 = time.time()
hospitals = []
for r in rows(F_HOSP):
    k = r["암호화요양기호"]
    item = {
        "ykiho":   k,
        "name":    s(r.get("요양기관명")),
        "cl_cd":   s(r.get("종별코드")),
        "cl_nm":   s(r.get("종별코드명")),
        "sido_cd": s(r.get("시도코드")),
        "sido_nm": s(r.get("시도코드명")),
        "sggu_cd": s(r.get("시군구코드")),
        "sggu_nm": s(r.get("시군구코드명")),
        "emd_nm":  s(r.get("읍면동")),
        "zipcode": s(r.get("우편번호")),
        "addr":    s(r.get("주소")),
        "tel":     s(r.get("전화번호")),
        "url":     s(r.get("병원홈페이지")),
        "estb_dd": str(r.get("개설일자") or ""),
        "dr_cnt":  r.get("총의사수") or 0,
        "x": r.get("좌표(X)"), "y": r.get("좌표(Y)"),
        "beds": beds_map.get(k),
        "departments": dept_map.get(k, []),
        "transit": transit_map.get(k, []),
        "equipment": equip_map.get(k, []),
        "meal": meal_map.get(k, []),
        "nursing": nursing_map.get(k, []),
        "special_treatments": special_map.get(k, []),
        "specialized_fields": spchosp_map.get(k, []),
        "other_staff": staff_map.get(k, []),
    }
    d = detail_map.get(k)
    if d:
        item.update(d)
    hospitals.append(item)
print(f"   {len(hospitals)}건 병합 완료 ({time.time()-t0:.1f}s)")

print("[12/12] 저장 중...")
OUT_DIR.mkdir(parents=True, exist_ok=True)
with open(OUT_DIR / "hospitals.json", "w", encoding="utf-8") as f:
    json.dump({"total": len(hospitals), "updated_at": "2026-03", "source": "HIRA 전국 병의원 및 약국 현황 2026.3", "items": hospitals}, f, ensure_ascii=False)
print(f"완료: data/hospitals.json ({len(hospitals)}건)")
