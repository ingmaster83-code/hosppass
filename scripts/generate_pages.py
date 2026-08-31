"""
hosppass.kr 페이지 자동 생성 스크립트

생성 대상:
  docs/지역/[시도]/index.html       — 시도 전체 목록
  docs/지역/[시도]/[시군구].html     — 시군구별 병원+약국
  docs/진료과목/[과목].html          — 진료과목별 전국 목록
  docs/요양병원/[시도]/[시군구].html — 요양병원 지역별
  docs/요양병원/투석.html            — 투석 가능 요양병원
  docs/요양병원/간호등급.html        — 간호등급 안내
  docs/sitemap.xml
"""

import os
import sys
import json
import html
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from urllib.parse import quote

ROOT     = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
DOCS_DIR = ROOT / "docs"

KAKAO_MAP_KEY = os.getenv("KAKAO_MAP_KEY", "78e249ab403b2955e4ca71e71f658549")
SITE_URL      = "https://hosppass.wooahouse.com"
CSS_VERSION   = "4"
JS_VERSION    = "2"

# ── 유틸 ───────────────────────────────────────────────────

def load_json(path: Path):
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def save_html(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

def esc(s):
    return html.escape(str(s or ""), quote=True)

def json_embed(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))

# ── 공통 HTML 부품 ─────────────────────────────────────────

def header_html(title: str, desc: str, canonical: str, depth: int = 1, keywords: str = "") -> str:
    root = "../" * depth
    kw_tag = f'\n  <meta name="keywords" content="{esc(keywords)}">' if keywords else ""
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(desc)}">{kw_tag}
  <meta name="naver-site-verification" content="d3f493285e1981adb0b98fa3772bd8ad2441ac9e" />
  <meta property="og:title" content="{esc(title)}">
  <meta property="og:description" content="{esc(desc)}">
  <meta property="og:type" content="website">
  <meta property="og:url" content="{SITE_URL}/{canonical}">
  <link rel="canonical" href="{SITE_URL}/{canonical}">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="{root}css/style.css?v={CSS_VERSION}">
  <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-6464921081676309" crossorigin="anonymous"></script>
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-9ZGENFSXWC"></script>
  <script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','G-9ZGENFSXWC');</script>
</head>
<body>
<header class="site-header">
  <div class="header-inner">
    <a href="{root}index.html" class="logo">hosp<span>pass</span></a>
    <div class="header-search">
      <input type="search" placeholder="병원, 약국, 진료과목 검색" id="hsi" autocomplete="off">
      <button class="btn-search" aria-label="검색" onclick="doSearch()">
        <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
        </svg>
      </button>
    </div>
    <nav class="header-nav">
      <a href="{root}hospital.html">병원</a>
      <a href="{root}pharmacy.html">약국</a>
      <a href="{root}emergency.html">응급실</a>
      <a href="{root}night.html">야간진료</a>
      <a href="{root}yoyang.html">요양병원</a>
      <a href="{root}dementia.html">치매안심센터</a>
      <a href="{root}postpartum.html">산후조리원</a>
      <a href="{root}otc-medicine.html">안전상비의약품</a>
      <a href="{root}transport.html">교통약자이동지원</a>
      <a href="{root}wheelchair-charger.html">전동휠체어충전기</a>
      <a href="{root}free-meal.html">무료급식소</a>
    </nav>
  </div>
</header>
<script src="{root}js/wooa-sites-bar.js"></script>
<script src="{root}js/ad-dev-placeholder.js"></script>
<script>
document.getElementById('hsi').addEventListener('keydown',function(e){{
  if(e.key==='Enter'){{var q=e.target.value.trim();if(q)location.href='{root}hospital.html?q='+encodeURIComponent(q);}}
}});
function doSearch(){{var q=document.getElementById('hsi').value.trim();if(q)location.href='{root}hospital.html?q='+encodeURIComponent(q);}}
</script>"""

def footer_html(root: str = "../") -> str:
    return f"""
<footer class="site-footer">
  <div class="footer-inner">
    <div class="footer-logo">hosppass</div>
    <div class="footer-links">
      <a href="{root}privacy.html">개인정보처리방침</a>
      <a href="https://bojopass.kr" target="_blank" rel="noopener">정부지원 의료비 혜택 → bojopass</a>
    </div>
    <p class="footer-copy">
      본 서비스는 건강보험심사평가원·국립중앙의료원 공공데이터를 활용합니다.<br>
      의료기관 정보는 실제와 다를 수 있으므로 방문 전 반드시 전화로 확인하세요.<br>
      &copy; {datetime.now().year} hosppass.wooahouse.com
    </p>
  </div>
</footer>
</body></html>"""

ADSENSE_PUB  = "ca-pub-6464921081676309"
ADSENSE_SIDE = "1419180025"   # 사이드바 (300×600)
ADSENSE_OTHER = "7080296704"  # 상단·중간 배너

def ad_banner(cls: str) -> str:
    slot = ADSENSE_SIDE if cls == "ad-side" else ADSENSE_OTHER
    return (
        f'<div class="ad-banner {cls}">'
        f'<ins class="adsbygoogle" style="display:block"'
        f' data-ad-client="{ADSENSE_PUB}"'
        f' data-ad-slot="{slot}"'
        f' data-ad-format="auto"'
        f' data-full-width-responsive="true"></ins>'
        f'<script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script>'
        f'</div>'
    )

# ── 1. 지역별 페이지 ────────────────────────────────────────

DEPT_TABS = ["내과", "소아과", "정형외과", "산부인과", "치과", "한의원"]

SIDO_NAME_MAP = {
    "110000": "서울", "210000": "부산", "220000": "인천", "230000": "대구",
    "240000": "광주", "250000": "대전", "260000": "울산", "290000": "세종",
    "310000": "경기", "320000": "강원", "330000": "충북", "340000": "충남",
    "350000": "전북", "360000": "전남", "370000": "경북", "380000": "경남",
    "390000": "제주",
}

def generate_region_pages(hospitals: list, pharmacies: list):
    print("[1/4] 지역별 페이지 생성")

    # 시도+시군구별 그룹핑
    hosp_by_region = defaultdict(list)
    for h in hospitals:
        key = (h.get("sido_nm", ""), h.get("sggu_nm", ""))
        hosp_by_region[key].append(h)

    pharm_by_region = defaultdict(list)
    for p in pharmacies:
        key = (p.get("sido_nm", ""), p.get("sggu_nm", ""))
        pharm_by_region[key].append(p)

    all_keys = set(hosp_by_region.keys()) | set(pharm_by_region.keys())
    count = 0

    for (sido_nm, sggu_nm) in sorted(all_keys):
        if not sido_nm or not sggu_nm:
            continue

        h_list = hosp_by_region[(sido_nm, sggu_nm)]
        p_list = pharm_by_region[(sido_nm, sggu_nm)]

        # 병원: 풍부한 정보를 최대한 노출 (필터/카드/상세에 사용)
        _keep_h = {
            "name","cl_nm","tel","url","x","y","addr","emd_nm","dr_cnt",
            "departments","hours","er_day","er_night","er_day_tel","er_night_tel",
            "lunch_weekday","lunch_sat","closed_sun","closed_holiday",
            "parking_available","parking_count","parking_fee","parking_note","location_note",
            "equipment","transit","nursing","special_treatments","specialized_fields","meal","beds",
            "sido_nm","sggu_nm",
        }
        _keep_p = {"name","cl_nm","tel","url","x","y","addr","emd_nm","sido_nm","sggu_nm"}
        h_embed = [{k:v for k,v in h.items() if k in _keep_h and v not in (None, "", [], {})} for h in h_list]
        p_embed = [{k:v for k,v in p.items() if k in _keep_p} for p in p_list]

        canonical = f"지역/{sido_nm}/{sggu_nm}.html"
        title = (f"{sggu_nm} 병원 — 야간진료·내과·소아과·정형외과 찾기 | hosppass")
        desc  = (
            f"{sggu_nm} 병원, 약국, 야간진료 정보를 한눈에 확인하세요. "
            f"{sggu_nm} 내과, {sggu_nm} 소아과, {sggu_nm} 정형외과, "
            f"{sggu_nm} 야간진료 병원, {sggu_nm} 24시간 약국, {sggu_nm} 토요일 진료 병원을 빠르게 찾을 수 있습니다."
        )
        keywords = (
            f"{sggu_nm} 병원, {sggu_nm} 약국, {sggu_nm} 야간진료, "
            f"{sggu_nm} 내과, {sggu_nm} 소아과, {sggu_nm} 정형외과, "
            f"{sggu_nm} 산부인과, {sggu_nm} 치과, {sggu_nm} 한의원, "
            f"{sggu_nm} 24시간 약국, {sggu_nm} 토요일 진료, {sggu_nm} 응급실, "
            f"{sido_nm} {sggu_nm} 병원, {sggu_nm} 의원"
        )

        page = _render_region_page(
            sido_nm, sggu_nm, h_embed, p_embed, title, desc, canonical, keywords
        )
        out = DOCS_DIR / "지역" / sido_nm / f"{sggu_nm}.html"
        save_html(out, page)
        # 병원/약국/응급실 페이지의 "내 위치로 찾기"가 재사용할 수 있도록 동일 데이터를 JSON으로도 저장
        json_out = DOCS_DIR / "지역" / sido_nm / f"{sggu_nm}.json"
        json_out.parent.mkdir(parents=True, exist_ok=True)
        with open(json_out, "w", encoding="utf-8") as f:
            json.dump({"sido": sido_nm, "sggu": sggu_nm, "hospitals": h_embed, "pharmacies": p_embed}, f, ensure_ascii=False, separators=(",", ":"))
        count += 1

    # 시도 index 생성
    for sido_cd, sido_nm in SIDO_NAME_MAP.items():
        _generate_sido_index(sido_nm, hosp_by_region, pharm_by_region)

    print(f"  → {count}개 시군구 페이지 생성")


def _facility_card_html(item: dict, is_pharm: bool, root: str = "") -> str:
    """병원/약국 카드 HTML (초기 SSR 렌더링용).
    운영중/야간진료중 같은 실시간 상태는 페이지 로드 후 JS가 다시 그리며 갱신하므로,
    여기서는 시점에 따라 달라지지 않는 정적 정보만 렌더링한다."""
    name  = esc(item.get("name", ""))
    cl_nm = esc(item.get("cl_nm", "") or ("약국" if is_pharm else ""))
    emd   = item.get("emd_nm", "")
    addr  = f'{esc(emd)} · {esc(item.get("addr", ""))}' if emd else esc(item.get("addr", ""))

    if is_pharm:
        depts = '<span class="tag tag-dept">약국</span>'
    else:
        dept_parts = []
        for d in (item.get("departments") or [])[:4]:
            spc = d.get("specialist_cnt")
            suffix = f"(전문의{spc})" if spc else ""
            dept_parts.append(f'<span class="tag tag-dept">{esc(d.get("name",""))}{suffix}</span>')
        depts = "".join(dept_parts)

    er_tag = (
        '<span class="tag tag-emrg">🚨 야간응급</span>' if item.get("er_night")
        else ('<span class="tag tag-emrg">🚨 주간응급</span>' if item.get("er_day") else "")
    )
    nursing_list = item.get("nursing") or []
    nursing_tag  = f'<span class="tag tag-grade">🏅 간호{esc(nursing_list[0].get("grade",""))}등급</span>' if nursing_list else ""
    spcl_tags    = "".join(f'<span class="tag tag-grade">🏆 {esc(s)}전문병원</span>' for s in (item.get("specialized_fields") or [])[:2])
    special_tags = "".join(f'<span class="tag tag-dept">{esc(s)}</span>' for s in (item.get("special_treatments") or [])[:2])

    dr    = f'<span>👨‍⚕️ 의사 {item["dr_cnt"]}명</span>' if item.get("dr_cnt") else ""
    equip = f'<span>🩻 장비 {len(item["equipment"])}종</span>' if item.get("equipment") else ""
    transit_list = item.get("transit") or []
    transit = f'<span>🚇 {esc(transit_list[0].get("stop",""))} {esc(transit_list[0].get("distance",""))}</span>' if transit_list else ""
    parking = ""
    if item.get("parking_available"):
        fee = "(유료)" if item.get("parking_fee") else "(무료)"
        parking = f'<span>🅿️ 주차 {esc(item.get("parking_count",""))}대{fee}</span>'
    extra_row = (
        f'<div style="margin-top:5px;font-size:.8rem;color:var(--text-light);display:flex;gap:10px;flex-wrap:wrap;">{dr}{equip}{transit}{parking}</div>'
        if (dr or equip or transit or parking) else ""
    )

    hours = item.get("hours") or {}
    order = ["월", "화", "수", "목", "금", "토", "일"]
    h_sum = " · ".join(f'{d} {hours[d]["start"]}~{hours[d]["end"]}' for d in order if hours.get(d) and hours[d].get("start"))
    if h_sum:
        hours_row = f'<div style="margin-top:7px;font-size:.82rem;color:var(--text-secondary);">🕐 {esc(h_sum)} <span style="margin-left:6px;color:var(--warning);font-size:.76rem;">· 방문 전 전화 확인 권장</span></div>'
    elif not is_pharm:
        hours_row = '<div style="margin-top:7px;font-size:.78rem;color:var(--text-light);">🕐 진료시간 미제공 — 전화로 확인해주세요</div>'
    else:
        hours_row = ""

    tel_btn = f'<a href="tel:{esc(item["tel"])}" class="btn-call">📞 {esc(item["tel"])}</a>' if item.get("tel") else ""
    url_btn = f'<a href="{esc(item["url"])}" target="_blank" rel="noopener" class="btn-call">🌐 홈페이지</a>' if item.get("url") else ""
    map_btn = (
        f'<a href="{root}map.html?x={item["x"]}&y={item["y"]}&name={quote(str(item.get("name","")))}" '
        f'onclick="openMapPopup(this.href);return false;" rel="noopener" class="btn-call">🗺️ 지도보기</a>'
        if item.get("x") and item.get("y") else ""
    )
    status_label = "약국" if is_pharm else (cl_nm or "병원")

    return (
        f'<div class="facility-card"><div class="facility-card-body">'
        f'<div class="facility-name">{name}</div>'
        f'<div class="facility-meta"><span>🏥 {cl_nm}</span><span>📍 {addr}</span></div>'
        f'<div class="facility-tags">{depts}{er_tag}{nursing_tag}{spcl_tags}{special_tags}</div>'
        f'{extra_row}{hours_row}</div>'
        f'<div class="facility-card-right">'
        f'<span class="status-badge status-open">{status_label}</span>'
        f'{tel_btn}{map_btn}{url_btn}</div></div>'
    )


def _render_region_page(sido, sggu, hospitals, pharmacies, title, desc, canonical, keywords=""):
    depth = 2
    root  = "../../"
    dept_btns = "".join(
        f'<button class="tab-btn" data-dept="{d}" onclick="filterDept(\'{d}\')">{d}</button>'
        for d in DEPT_TABS
    )
    nearby_sggus = _get_nearby_sggus(sido, sggu)
    nearby_html  = "".join(
        f'<a href="{esc(s)}.html" style="font-size:.85rem;color:var(--text-secondary);padding:6px 8px;border-radius:var(--radius-sm);display:block;" '
        f'onmouseover="this.style.background=\'var(--primary-light)\'" onmouseout="this.style.background=\'\'">{esc(s)}</a>'
        for s in nearby_sggus
    )

    # 초기 SSR 카드 (검색엔진·JS 로드 전 사용자에게 실제 콘텐츠 노출용, JS가 로드되면 renderPage(1)이 즉시 대체함)
    _initial_items = (
        [(h, False) for h in hospitals] + [(p, True) for p in pharmacies]
    )[:10]
    _initial_cards = "".join(_facility_card_html(it, is_p, root) for it, is_p in _initial_items)

    return f"""{header_html(title, desc, canonical, depth, keywords)}

<section style="background:linear-gradient(135deg,var(--primary) 0%,#0891B2 100%);color:#fff;padding:32px 16px;">
  <div class="container">
    <nav class="breadcrumb" style="color:rgba(255,255,255,.7);margin-bottom:12px;">
      <a href="{root}index.html" style="color:rgba(255,255,255,.8)">홈</a>
      <span class="sep">›</span>
      <a href="index.html" style="color:rgba(255,255,255,.8)">{esc(sido)}</a>
      <span class="sep">›</span>
      <span style="color:#fff">{esc(sggu)}</span>
    </nav>
    <h1 style="font-size:1.7rem;font-weight:800;margin-bottom:6px;">{esc(sggu)} 병원 · 약국 찾기</h1>
    <p style="opacity:.88;font-size:.95rem;">{esc(sggu)} 의료기관 정보 — 야간진료, 24시 약국, 응급실까지 한눈에</p>
  </div>
</section>

<div class="container" style="padding-top:20px">{ad_banner('ad-top')}</div>

<div class="container section">
  <div class="layout-with-sidebar">
    <div class="layout-main">
      <div class="tab-filter" id="typeFilter">
        <button class="tab-btn active" data-type="all"   onclick="filterType('all')">전체</button>
        <button class="tab-btn" data-type="hosp"         onclick="filterType('hosp')">병원·의원</button>
        <button class="tab-btn" data-type="pharm"        onclick="filterType('pharm')">약국</button>
        <button class="tab-btn" data-type="night"        onclick="filterType('night')">야간진료</button>
      </div>
      <div class="tab-filter" id="deptFilter" style="margin-top:-4px;">
        <button class="tab-btn active" data-dept="all" onclick="filterDept('all')">전체과목</button>
        {dept_btns}
      </div>
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
        <span style="font-size:.88rem;color:var(--text-secondary);">
          <strong id="resultCount" style="color:var(--primary)">0</strong>개 의료기관
        </span>
        <span style="font-size:.78rem;color:var(--text-light);">매일 새벽 2시 자동 갱신</span>
      </div>
      <div class="facility-list" id="facilityList">{_initial_cards}</div>
      <div class="pagination" id="pagination"></div>
      {ad_banner('ad-mid')}
      <div style="margin-top:32px;">
        <h2 class="section-title">{esc(sggu)} 의료기관 지도</h2>
        <div class="map-wrap"><div id="map"></div></div>
      </div>
      <div style="margin-top:40px;padding:28px;background:var(--primary-light);border-radius:var(--radius);font-size:.9rem;line-height:1.9;color:var(--text-secondary);">
        <h2 style="font-size:1.05rem;font-weight:700;color:var(--text-primary);margin-bottom:14px;">{esc(sggu)} 병원 · 약국 찾기 안내</h2>
        <p>
          <strong>{esc(sggu)} 병원</strong> 정보를 진료과목별로 확인할 수 있습니다.
          <strong>{esc(sggu)} 내과</strong>, <strong>{esc(sggu)} 소아과</strong>,
          <strong>{esc(sggu)} 정형외과</strong>, <strong>{esc(sggu)} 산부인과</strong>,
          <strong>{esc(sggu)} 치과</strong>, <strong>{esc(sggu)} 한의원</strong> 등
          다양한 진료과목의 의료기관 정보를 제공합니다.
        </p>
        <p style="margin-top:10px;">
          <strong>{esc(sggu)} 야간진료 병원</strong>과 <strong>{esc(sggu)} 토요일 진료 병원</strong>은
          필터 기능으로 빠르게 확인할 수 있습니다.
          <strong>{esc(sggu)} 24시간 약국</strong> 및 <strong>{esc(sggu)} 야간 약국</strong>도
          약국 탭에서 확인하세요.
        </p>
        <p style="margin-top:10px;">
          <strong>{esc(sido)} {esc(sggu)} 응급실</strong>이 필요한 경우 상단 응급실 메뉴를 이용하세요.
          응급실 실시간 병상 현황을 확인할 수 있습니다.
        </p>
        <p style="margin-top:10px;font-size:.82rem;color:var(--text-light);">
          ※ 진료시간은 변경될 수 있으므로 방문 전 반드시 전화로 확인하시기 바랍니다.
          본 정보는 건강보험심사평가원 공공데이터를 기반으로 매일 새벽 자동 갱신됩니다.
        </p>
      </div>
      <div style="margin:16px 0 8px;">
        <a href="https://wooatown.wooahouse.com/지역/{esc(sido)}.html" target="_blank" rel="noopener"
           style="display:block;text-align:center;padding:12px 16px;border:1px dashed var(--border);border-radius:var(--radius);color:var(--text-secondary);font-size:.85rem;font-weight:600;text-decoration:none;">
          🏠 {esc(sido)} 다른 생활정보 보기 (우아동네) →
        </a>
      </div>
    </div>
    <aside>
      <div class="sidebar-sticky">
        {ad_banner('ad-side')}
        <div style="background:var(--card-bg);border:1px solid var(--border);border-radius:var(--radius);padding:16px;margin-top:20px;">
          <h3 style="font-size:.9rem;font-weight:700;margin-bottom:12px;">{esc(sido)} 인근 지역</h3>
          <div style="display:flex;flex-direction:column;gap:4px;">
            {nearby_html}
            <a href="index.html" style="font-size:.85rem;color:var(--primary);font-weight:600;padding:6px 8px;margin-top:4px;">{esc(sido)} 전체 보기 →</a>
          </div>
        </div>
        <div id="recentRegionBox" style="background:var(--card-bg);border:1px solid var(--border);border-radius:var(--radius);padding:16px;margin-top:20px;display:none;">
          <h3 style="font-size:.9rem;font-weight:700;margin-bottom:12px;">🕑 최근 본 지역</h3>
          <div id="recentRegionList" style="display:flex;flex-direction:column;gap:4px;"></div>
        </div>
      </div>
    </aside>
  </div>
</div>

<script type="text/javascript" src="//dapi.kakao.com/v2/maps/sdk.js?appkey={KAKAO_MAP_KEY}&libraries=services"></script>
<script src="{root}js/facility-render.js?v={JS_VERSION}"></script>
<script>
const PAGE_DATA={{
  sido:{json_embed(sido)},sggu:{json_embed(sggu)},
  hospitals:{json_embed(hospitals)},
  pharmacies:{json_embed(pharmacies)}
}};
function buildPagination(page,total){{
  if(total<=1)return'';
  const W=10;
  let s=Math.max(1,page-Math.floor(W/2)),e=Math.min(total,s+W-1);
  if(e-s+1<W)s=Math.max(1,e-W+1);
  let h=`<button class="page-btn"${{page===1?' disabled':''}} onclick="renderPage(${{page-1}})">&#9664;</button>`;
  for(let i=s;i<=e;i++)h+=`<button class="page-btn${{i===page?' active':''}}" onclick="renderPage(${{i}})">${{i}}</button>`;
  h+=`<button class="page-btn"${{page===total?' disabled':''}} onclick="renderPage(${{page+1}})">&#9654;</button>`;
  return h;
}}
let allItems=[],filtered=[],curType='all',curDept='all',curPage=1;
const PAGE_SIZE=10;

document.addEventListener('DOMContentLoaded',()=>{{
  buildItems();
  const h=(location.hash||'').replace('#','');
  if(['hosp','pharm','night'].includes(h)){{curType=h;document.querySelectorAll('#typeFilter .tab-btn').forEach(b=>b.classList.toggle('active',b.dataset.type===h));}}
  applyFilter();initMap();
}});

// hasDept/isNightCareNow/isOpenNow/hoursSummary/renderFacilityCard는 js/facility-render.js 공용 파일 사용
function buildItems(){{
  allItems=[
    ...PAGE_DATA.hospitals.map(h=>{{return{{...h,_type:'hosp'}}}}),
    ...PAGE_DATA.pharmacies.map(p=>{{return{{...p,_type:'pharm',cl_nm:'약국'}}}})
  ];
}}
function filterType(t){{curType=t;curPage=1;document.querySelectorAll('#typeFilter .tab-btn').forEach(b=>b.classList.toggle('active',b.dataset.type===t));applyFilter();}}
function filterDept(d){{curDept=d;curPage=1;document.querySelectorAll('#deptFilter .tab-btn').forEach(b=>b.classList.toggle('active',b.dataset.dept===d));applyFilter();}}
function applyFilter(){{
  filtered=allItems.filter(item=>{{
    if(curType==='hosp'&&item._type!=='hosp')return false;
    if(curType==='pharm'&&item._type!=='pharm')return false;
    if(curType==='night'&&!isNightCareNow(item))return false;
    if(curDept!=='all'&&!hasDept(item,curDept))return false;
    return true;
  }});
  document.getElementById('resultCount').textContent=filtered.length;
  renderPage(1);
}}
function renderPage(page){{
  curPage=page;
  const start=(page-1)*PAGE_SIZE,items=filtered.slice(start,start+PAGE_SIZE);
  const list=document.getElementById('facilityList');
  if(!items.length){{list.innerHTML='<div style="text-align:center;padding:40px;color:var(--text-light);">해당하는 의료기관이 없습니다.</div>';document.getElementById('pagination').innerHTML='';return;}}
  list.innerHTML=renderCardsWithAd(items,item=>renderFacilityCard(item,"{root}"));
  initInlineAds(list);
  const total=Math.ceil(filtered.length/PAGE_SIZE);
  document.getElementById('pagination').innerHTML=buildPagination(curPage,total);
}}
function initMap(){{
  if(typeof kakao==='undefined')return;
  const map=new kakao.maps.Map(document.getElementById('map'),{{center:new kakao.maps.LatLng(PAGE_DATA.hospitals[0]?.y||37.5,PAGE_DATA.hospitals[0]?.x||127.0),level:5}});
  [...PAGE_DATA.hospitals,...PAGE_DATA.pharmacies].forEach(item=>{{
    if(!item.x||!item.y)return;
    const marker=new kakao.maps.Marker({{map,position:new kakao.maps.LatLng(parseFloat(item.y),parseFloat(item.x)),title:item.name}});
    const iw=new kakao.maps.InfoWindow({{content:`<div style="padding:8px 10px;font-size:13px;font-weight:600;">${{item.name}}</div>`}});
    kakao.maps.event.addListener(marker,'click',()=>iw.open(map,marker));
  }});
}}
</script>

<script>
// 최근 본 지역 (localStorage)
(() => {{
  const KEY = 'hosppass_recent';
  const current = {{ sido: {json_embed(sido)}, sggu: {json_embed(sggu)},
    href: `/지역/${{encodeURIComponent({json_embed(sido)})}}/${{encodeURIComponent({json_embed(sggu)})}}.html` }};
  let list = [];
  try {{ list = JSON.parse(localStorage.getItem(KEY) || '[]'); }} catch (e) {{}}

  const others = list.filter(r => !(r.sido === current.sido && r.sggu === current.sggu));
  if (others.length > 0) {{
    document.getElementById('recentRegionList').innerHTML = others.slice(0, 6).map(r => `
      <a href="${{r.href}}" style="font-size:.85rem;color:var(--text-secondary);padding:6px 8px;border-radius:var(--radius-sm);display:block;"
         onmouseover="this.style.background='var(--primary-light)'" onmouseout="this.style.background=''">${{r.sido}} ${{r.sggu}}</a>`).join('');
    document.getElementById('recentRegionBox').style.display = 'block';
  }}

  const updated = [current, ...others].slice(0, 8);
  try {{ localStorage.setItem(KEY, JSON.stringify(updated)); }} catch (e) {{}}
}})();
</script>
{footer_html(root)}"""


def _get_nearby_sggus(sido: str, sggu: str) -> list:
    """같은 시도의 다른 시군구 목록 (최대 6개)."""
    region_dir = DOCS_DIR / "지역" / sido
    if not region_dir.exists():
        return []
    names = [p.stem for p in region_dir.glob("*.html") if p.stem != "index" and p.stem != sggu]
    return names[:6]


def _generate_sido_index(sido_nm: str, hosp_by_region, pharm_by_region):
    """시도 전체 index.html 생성."""
    sggus = sorted(set(
        k[1] for k in list(hosp_by_region.keys()) + list(pharm_by_region.keys())
        if k[0] == sido_nm and k[1]
    ))
    if not sggus:
        return

    links = "".join(
        f'<a href="{esc(s)}.html" class="tab-btn" style="text-align:center;">{esc(s)}</a>'
        for s in sggus
    )
    title    = f"{sido_nm} 병원 찾기 — 시군구별 야간진료·약국 | hosppass"
    desc     = f"{sido_nm} 병원, 약국, 야간진료 정보를 시군구별로 확인하세요. {sido_nm} 내과, 소아과, 정형외과 등 진료과목별 의료기관 안내."
    keywords = f"{sido_nm} 병원, {sido_nm} 약국, {sido_nm} 야간진료, {sido_nm} 내과, {sido_nm} 소아과, {sido_nm} 응급실"
    canonical = f"지역/{sido_nm}/index.html"
    root     = "../../"

    sido_intro = (
        f"{sido_nm}의 병원, 약국, 야간진료, 응급실, 요양병원 정보를 {len(sggus)}개 시·군·구별로 안내합니다. "
        f"내과, 소아과, 정형외과, 이비인후과, 피부과 등 진료과목별로 가까운 의료기관을 찾을 수 있습니다. "
        f"야간에 진료하는 병원이나 응급실 위치도 한눈에 확인하세요. "
        f"모든 의료기관 정보는 건강보험심사평가원 공공데이터를 기반으로 제공됩니다."
    )
    page = f"""{header_html(title, desc, canonical, 2, keywords)}
<section style="background:linear-gradient(135deg,var(--primary) 0%,#0891B2 100%);color:#fff;padding:32px 16px;">
  <div class="container">
    <h1 style="font-size:1.7rem;font-weight:800;">{esc(sido_nm)} 병원 · 약국 찾기</h1>
    <p style="opacity:.88;margin-top:6px;">시군구를 선택하세요</p>
  </div>
</section>
<div class="container section">
  <p style="color:#374151;line-height:1.75;margin-bottom:16px;font-size:.95rem;">{sido_intro}</p>
  <h2 style="font-size:1rem;font-weight:700;margin-bottom:12px;">{esc(sido_nm)} 시·군·구 ({len(sggus)}개)</h2>
  <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:8px;">{links}</div>
  <div style="margin-top:28px;background:#F9FAFB;border-radius:12px;padding:20px 24px;">
    <h2 style="font-size:1rem;font-weight:700;margin-bottom:12px;">자주 묻는 질문</h2>
    <details style="margin-bottom:10px;">
      <summary style="cursor:pointer;font-weight:600;padding:6px 0;">{esc(sido_nm)} 야간진료 병원은 어떻게 찾나요?</summary>
      <p style="padding:6px 0 4px;color:#374151;line-height:1.7;">위 시·군·구를 선택한 후 '야간진료' 탭을 클릭하면 해당 지역의 야간 및 주말 진료 병원 목록을 확인할 수 있습니다. 응급 상황에는 응급실 탭도 활용하세요.</p>
    </details>
    <details>
      <summary style="cursor:pointer;font-weight:600;padding:6px 0;">의료기관 정보가 실제와 다를 수 있나요?</summary>
      <p style="padding:6px 0 4px;color:#374151;line-height:1.7;">건강보험심사평가원 데이터를 기반으로 하지만, 진료 시간이나 운영 여부가 변경될 수 있습니다. 방문 전에 반드시 해당 의료기관에 전화로 확인하시기 바랍니다.</p>
    </details>
  </div>
</div>
{footer_html(root)}"""

    save_html(DOCS_DIR / "지역" / sido_nm / "index.html", page)


# ── 2. 진료과목별 페이지 ────────────────────────────────────

SPECIALTIES = [
    ("내과",       "01"), ("소아과",     "10"), ("정형외과",   "11"),
    ("산부인과",   "12"), ("치과",       "49"), ("한의원",     "80"),
    ("안과",       "13"), ("이비인후과", "14"), ("피부과",     "15"),
    ("정신건강의학과", "17"), ("신경과",  "16"), ("비뇨기과",  "18"),
    ("재활의학과", "21"), ("성형외과",   "20"), ("흉부외과",  "08"),
]

def generate_specialty_pages(hospitals: list):
    print("[2/4] 진료과목별 페이지 생성")
    (DOCS_DIR / "진료과목").mkdir(exist_ok=True)

    # 정신건강의학과 등 진료과목코드명 표기 편차 대응
    name_alias = {"정신건강의학과": ["정신건강의학과", "정신과", "신경정신과"]}
    _card_keep = {
        "name","cl_nm","tel","url","x","y","addr","emd_nm","dr_cnt",
        "departments","hours","er_day","er_night","er_day_tel","er_night_tel",
        "lunch_weekday","lunch_sat","closed_sun","closed_holiday",
        "parking_available","parking_count","parking_fee","parking_note","location_note",
        "equipment","transit","nursing","special_treatments","specialized_fields","meal","beds",
        "sido_nm","sggu_nm",
    }
    for dept_nm, _ in SPECIALTIES:
        aliases = name_alias.get(dept_nm, [dept_nm])
        matched = [
            h for h in hospitals
            if any(a in (d.get("name") or "") for d in (h.get("departments") or []) for a in aliases)
        ]
        filtered = [{k: v for k, v in h.items() if k in _card_keep and v not in (None, "", [], {})} for h in matched[:300]]
        if not filtered:
            continue

        title    = f"{dept_nm} 병원 찾기 — 가까운 {dept_nm} 의원 전화번호·진료시간 | hosppass"
        desc     = (
            f"전국 {dept_nm} 병원·의원 정보를 확인하세요. "
            f"지역별 {dept_nm} 진료시간, 토요일 {dept_nm}, 야간 {dept_nm}, "
            f"{dept_nm} 의원 전화번호·위치를 빠르게 찾을 수 있습니다."
        )
        keywords = (
            f"{dept_nm} 병원, {dept_nm} 의원, {dept_nm} 찾기, "
            f"가까운 {dept_nm}, 토요일 {dept_nm}, 야간 {dept_nm}, "
            f"{dept_nm} 진료시간, {dept_nm} 전화번호, {dept_nm} 예약"
        )
        canonical = f"진료과목/{dept_nm}.html"
        root     = "../"

        dept_btns_html = "".join(
            f'<button class="tab-btn{"  active" if d == dept_nm else ""}" onclick="doSido(\'\')">{esc(d)}</button>'
            for d, _ in SPECIALTIES
        )

        # 초기 SSR 카드 (검색엔진·JS 로드 전 사용자에게 실제 콘텐츠 노출용, JS가 로드되면 즉시 대체함)
        _initial_cards = "".join(_facility_card_html(h, False, root) for h in filtered[:15])

        page = f"""{header_html(title, desc, canonical, 1, keywords)}
<section style="background:linear-gradient(135deg,var(--primary) 0%,#0891B2 100%);color:#fff;padding:32px 16px;">
  <div class="container">
    <h1 style="font-size:1.7rem;font-weight:800;">{esc(dept_nm)} 병원 찾기</h1>
    <p style="opacity:.88;margin-top:6px;">전국 {esc(dept_nm)} 의료기관 목록</p>
  </div>
</section>
<div class="container" style="padding-top:20px">{ad_banner('ad-top')}</div>
<div class="container section">
  <div class="layout-with-sidebar">
    <div class="layout-main">
      <div class="tab-filter" style="margin-bottom:16px;" id="sidoFilter">
        <button class="tab-btn active" onclick="filterSido('')">전체</button>
        {"".join(f'<button class="tab-btn" onclick="filterSido(\'{esc(s)}\')">{esc(s)}</button>' for s in SIDO_NAME_MAP.values())}
      </div>
      <div style="margin-bottom:12px;font-size:.88rem;color:var(--text-secondary);">
        <strong id="resultCount" style="color:var(--primary)">0</strong>개 병원
      </div>
      <div class="facility-list" id="facilityList">{_initial_cards}</div>
      <div class="pagination" id="pagination"></div>
      {ad_banner('ad-mid')}
    </div>
    <aside>
      <div class="sidebar-sticky">
        {ad_banner('ad-side')}
      </div>
    </aside>
  </div>
</div>
<script src="{root}js/facility-render.js?v={JS_VERSION}"></script>
<script>
function buildPagination(page,total){{
  if(total<=1)return'';
  const W=10;
  let s=Math.max(1,page-Math.floor(W/2)),e=Math.min(total,s+W-1);
  if(e-s+1<W)s=Math.max(1,e-W+1);
  let h=`<button class="page-btn"${{page===1?' disabled':''}} onclick="renderPage(${{page-1}})">&#9664;</button>`;
  for(let i=s;i<=e;i++)h+=`<button class="page-btn${{i===page?' active':''}}" onclick="renderPage(${{i}})">${{i}}</button>`;
  h+=`<button class="page-btn"${{page===total?' disabled':''}} onclick="renderPage(${{page+1}})">&#9654;</button>`;
  return h;
}}
const ALL_DATA={json_embed(filtered)};
let filtered2=[...ALL_DATA],curSido='',curPage=1;
const PAGE_SIZE=15;
document.addEventListener('DOMContentLoaded',()=>{{applyFilter();}});
function filterSido(sido){{curSido=sido;curPage=1;document.querySelectorAll('#sidoFilter .tab-btn').forEach(b=>b.classList.toggle('active',b.textContent===(sido||'전체')));applyFilter();}}
function applyFilter(){{
  filtered2=ALL_DATA.filter(h=>!curSido||h.sido_nm===curSido);
  document.getElementById('resultCount').textContent=filtered2.length;
  renderPage(1);
}}
function renderPage(page){{
  curPage=page;
  const items=filtered2.slice((page-1)*PAGE_SIZE,page*PAGE_SIZE);
  const list=document.getElementById('facilityList');
  if(!items.length){{list.innerHTML='<div style="text-align:center;padding:40px;color:var(--text-light);">해당하는 병원이 없습니다.</div>';document.getElementById('pagination').innerHTML='';return;}}
  list.innerHTML=renderCardsWithAd(items,h=>renderFacilityCard({{...h,_type:'hosp'}},"{root}"));
  initInlineAds(list);
  const total=Math.ceil(filtered2.length/PAGE_SIZE);
  document.getElementById('pagination').innerHTML=buildPagination(page,total);
}}
</script>
{footer_html(root)}"""

        save_html(DOCS_DIR / "진료과목" / f"{dept_nm}.html", page)

    print(f"  → {len(SPECIALTIES)}개 진료과목 페이지 생성")


# ── 3. 요양병원 지역별 페이지 ──────────────────────────────

def generate_nursing_pages(nursing: list):
    print("[3/4] 요양병원 페이지 생성")

    by_region = defaultdict(list)
    for h in nursing:
        key = (h.get("sido_nm", ""), h.get("sggu_nm", ""))
        by_region[key].append(h)

    count = 0
    for (sido_nm, sggu_nm), hospitals in sorted(by_region.items()):
        if not sido_nm or not sggu_nm or not hospitals:
            continue
        # 투석 가능 먼저, 간호등급 좋은 순
        hospitals.sort(key=lambda x: (
            0 if x.get("dialysis") else 1,
            x.get("nursing_grade", "9등급"),
        ))
        _generate_nursing_region_page(sido_nm, sggu_nm, hospitals)
        count += 1

    # 투석 전문 페이지 — 투석 데이터 없으면 전체 목록으로 fallback
    dialysis = [h for h in nursing if h.get("dialysis")] or nursing
    _generate_dialysis_page(dialysis)

    # 간호등급 안내 페이지
    _generate_nursing_grade_page(nursing)

    print(f"  → {count}개 요양병원 지역 페이지 + 투석·간호등급 페이지 생성")


def _generate_nursing_region_page(sido, sggu, hospitals):
    root      = "../../"
    canonical = f"요양병원/{sido}/{sggu}.html"
    title     = f"{sggu} 요양병원 — 투석 가능 간호등급 비교 | hosppass"
    desc      = f"{sggu} 요양병원 목록과 상세 정보를 확인하세요. 투석 가능 여부, 간호등급, 병상 수, 평가등급 비교."

    _page_hospitals = hospitals[:50]
    _card_htmls = [_nursing_card_html(h, root) for h in _page_hospitals]
    if len(_card_htmls) > 9:
        _card_htmls.insert(8, ad_banner('ad-inline'))
    cards = "".join(_card_htmls)

    page = f"""{header_html(title, desc, canonical, 2)}
<section style="background:linear-gradient(135deg,#7C3AED 0%,#0D9488 100%);color:#fff;padding:32px 16px;">
  <div class="container">
    <nav class="breadcrumb" style="color:rgba(255,255,255,.7);margin-bottom:12px;">
      <a href="{root}index.html" style="color:rgba(255,255,255,.8)">홈</a>
      <span class="sep">›</span>
      <a href="{root}yoyang.html" style="color:rgba(255,255,255,.8)">요양병원</a>
      <span class="sep">›</span>
      <span style="color:#fff">{esc(sggu)}</span>
    </nav>
    <h1 style="font-size:1.7rem;font-weight:800;margin-bottom:6px;">{esc(sggu)} 요양병원 찾기</h1>
    <p style="opacity:.88;font-size:.95rem;">투석 가능 여부, 간호등급, 병상 수까지 한눈에 비교</p>
  </div>
</section>
<div class="container" style="padding-top:20px">{ad_banner('ad-top')}</div>
<div class="container section">
  <div class="layout-with-sidebar">
    <div class="layout-main">
      <div class="tab-filter" id="nursingFilter">
        <button class="tab-btn active" onclick="filterNursing('all')">전체</button>
        <button class="tab-btn" onclick="filterNursing('dialysis')">💉 투석 가능</button>
        <button class="tab-btn" onclick="filterNursing('grade1')">⭐ 1등급 간호</button>
      </div>
      <div style="margin-bottom:12px;font-size:.88rem;color:var(--text-secondary);">
        <strong id="resultCount" style="color:var(--primary)">{len(hospitals)}</strong>개 요양병원
      </div>
      <div class="facility-list" id="nursingList">{cards}</div>
      <div class="pagination" id="pagination"></div>
      {ad_banner('ad-mid')}
      <div style="margin-top:40px;padding:24px;background:var(--primary-light);border-radius:var(--radius);font-size:.9rem;line-height:1.8;color:var(--text-secondary);">
        <h2 style="font-size:1rem;font-weight:700;color:var(--text-primary);margin-bottom:8px;">{esc(sggu)} 요양병원 선택 가이드</h2>
        <p><strong>간호등급</strong>은 간호사 1인당 환자 수 기준으로, 1등급이 최우수입니다. 환자 케어의 질과 직결되므로 반드시 확인하세요.</p>
        <p style="margin-top:8px;"><strong>투석 가능 요양병원</strong>은 인공신장기를 보유해 혈액투석을 받으며 입원 치료를 받을 수 있습니다.</p>
        <p style="margin-top:8px;">{esc(sggu)} {esc(sido)} 요양병원 정보는 매일 새벽 자동 갱신됩니다. 입원 전 반드시 전화로 확인하세요.</p>
      </div>
    </div>
    <aside>
      <div class="sidebar-sticky">
        {ad_banner('ad-side')}
        <div style="background:var(--card-bg);border:1px solid var(--border);border-radius:var(--radius);padding:16px;margin-top:20px;">
          <h3 style="font-size:.9rem;font-weight:700;margin-bottom:12px;">관련 페이지</h3>
          <div style="display:flex;flex-direction:column;gap:6px;">
            <a href="{root}요양병원/투석.html" style="font-size:.85rem;color:var(--text-secondary);padding:6px 8px;border-radius:var(--radius-sm);">💉 투석 가능 요양병원</a>
            <a href="{root}요양병원/간호등급.html" style="font-size:.85rem;color:var(--text-secondary);padding:6px 8px;border-radius:var(--radius-sm);">🏅 간호등급 안내</a>
            <a href="{root}yoyang.html" style="font-size:.85rem;color:var(--primary);font-weight:600;padding:6px 8px;margin-top:4px;">전국 요양병원 보기 →</a>
          </div>
        </div>
      </div>
    </aside>
  </div>
</div>
<script src="{root}js/facility-render.js?v={JS_VERSION}"></script>
<script>
const ALL_NURSING={json_embed(hospitals[:200])};
let cur='all';
function filterNursing(f){{
  cur=f;
  document.querySelectorAll('#nursingFilter .tab-btn').forEach(b=>b.classList.toggle('active',b.textContent.includes(f==='all'?'전체':f==='dialysis'?'투석':'1등급')));
  const filtered=ALL_NURSING.filter(h=>{{
    if(f==='dialysis')return h.dialysis;
    if(f==='grade1')return h.nursing_grade==='1등급';
    return true;
  }});
  document.getElementById('resultCount').textContent=filtered.length;
  const list=document.getElementById('nursingList');
  let html=filtered.map(h=>nursingCard(h));
  if(html.length>9)html.splice(8,0,'<div class="ad-banner ad-inline"><ins class="adsbygoogle" style="display:block" data-ad-client="ca-pub-6464921081676309" data-ad-slot="7080296704" data-ad-format="auto" data-full-width-responsive="true"></ins></div>');
  list.innerHTML=html.join('');
  list.querySelectorAll('.ad-inline .adsbygoogle:not([data-adsbygoogle-status])').forEach(()=>{{try{{(window.adsbygoogle=window.adsbygoogle||[]).push({{}});}}catch(e){{}}}});
}}
function nursingCard(h){{
  const dialysisTag=h.dialysis?'<span class="tag" style="background:#EDE9FE;color:#6D28D9;">💉 투석가능</span>':'';
  const gradeTag=h.nursing_grade?`<span class="tag tag-grade">🏅 간호 ${{h.nursing_grade}}</span>`:'';
  const bedTag=h.bed_cnt?`<span class="tag" style="background:#F0FDFA;color:#0F766E;">🛏️ ${{h.bed_cnt}}병상</span>`:'';
  const depts=(h.dgsbj_list||[]).slice(0,3).map(d=>`<span class="tag tag-dept">${{d}}</span>`).join('');
  const mapBtn=(h.x&&h.y)?`<a href="{root}map.html?x=${{h.x}}&y=${{h.y}}&name=${{encodeURIComponent(h.name)}}" onclick="openMapPopup(this.href);return false;" rel="noopener" class="btn-call">🗺️ 지도보기</a>`:'';
  const urlBtn=h.url?`<a href="${{h.url}}" target="_blank" rel="noopener" class="btn-call">🌐 홈페이지</a>`:'';
  return `<div class="facility-card"><div class="facility-card-body"><div class="facility-name">${{h.name}}</div><div class="facility-meta"><span>📍 ${{h.addr||''}}</span><span>👨‍⚕️ 의사 ${{h.dr_cnt||0}}명</span></div><div class="facility-tags">${{dialysisTag}}${{gradeTag}}${{bedTag}}${{depts}}</div></div><div class="facility-card-right"><span class="status-badge status-open">요양병원</span>${{h.tel?`<a href="tel:${{h.tel}}" class="btn-call">📞 ${{h.tel}}</a>`:''}}${{mapBtn}}${{urlBtn}}</div></div>`;
}}
</script>
{footer_html(root)}"""

    save_html(DOCS_DIR / "요양병원" / sido / f"{sggu}.html", page)


def _nursing_card_html(h: dict, root: str = "") -> str:
    dialysis = '<span class="tag" style="background:#EDE9FE;color:#6D28D9;">💉 투석가능</span>' if h.get("dialysis") else ""
    grade    = f'<span class="tag tag-grade">🏅 간호 {esc(h["nursing_grade"])}</span>' if h.get("nursing_grade") else ""
    bed      = f'<span class="tag" style="background:#F0FDFA;color:#0F766E;">🛏️ {h["bed_cnt"]}병상</span>' if h.get("bed_cnt") else ""
    depts    = "".join(f'<span class="tag tag-dept">{esc(d)}</span>' for d in (h.get("dgsbj_list") or [])[:3])
    map_btn = (
        f'<a href="{root}map.html?x={h["x"]}&y={h["y"]}&name={quote(str(h.get("name","")))}" '
        f'onclick="openMapPopup(this.href);return false;" rel="noopener" class="btn-call">🗺️ 지도보기</a>'
        if h.get("x") and h.get("y") else ""
    )
    url_btn = f'<a href="{esc(h["url"])}" target="_blank" rel="noopener" class="btn-call">🌐 홈페이지</a>' if h.get("url") else ""
    return f"""<div class="facility-card">
  <div class="facility-card-body">
    <div class="facility-name">{esc(h.get("name",""))}</div>
    <div class="facility-meta"><span>📍 {esc(h.get("addr",""))}</span><span>👨‍⚕️ 의사 {h.get("dr_cnt",0)}명</span></div>
    <div class="facility-tags">{dialysis}{grade}{bed}{depts}</div>
  </div>
  <div class="facility-card-right">
    <span class="status-badge status-open">요양병원</span>
    {f'<a href="tel:{esc(h["tel"])}" class="btn-call">📞 {esc(h["tel"])}</a>' if h.get("tel") else ""}
    {map_btn}
    {url_btn}
  </div>
</div>"""


def _generate_dialysis_page(hospitals: list):
    root      = "../"
    canonical = "요양병원/투석.html"
    title     = "투석 가능 요양병원 — 전국 혈액투석 요양병원 찾기 | hosppass"
    desc      = "투석 치료를 받으면서 입원 가능한 요양병원을 찾아보세요. 인공신장기 보유 대수, 신장내과 전문의 정보 제공."

    sido_filter = "".join(
        f'<button class="tab-btn" onclick="filterSido(\'{esc(s)}\')">{esc(s)}</button>'
        for s in SIDO_NAME_MAP.values()
    )
    _page_hospitals = hospitals[:100]
    _card_htmls = [_nursing_card_html(h, root) for h in _page_hospitals]
    if len(_card_htmls) > 9:
        _card_htmls.insert(8, ad_banner('ad-inline'))
    cards = "".join(_card_htmls)

    page = f"""{header_html(title, desc, canonical, 1)}
<section style="background:linear-gradient(135deg,#7C3AED 0%,#0D9488 100%);color:#fff;padding:40px 16px;text-align:center;">
  <div class="container">
    <h1 style="font-size:1.9rem;font-weight:800;margin-bottom:8px;">💉 투석 가능 요양병원</h1>
    <p style="opacity:.88;">인공신장기를 보유해 혈액투석을 받으며 입원 가능한 요양병원</p>
  </div>
</section>
<div class="container" style="padding-top:20px">{ad_banner('ad-top')}</div>
<div class="container section">
  <div class="layout-with-sidebar">
    <div class="layout-main">
      <div style="background:var(--primary-light);border-radius:var(--radius);padding:16px;margin-bottom:20px;font-size:.9rem;line-height:1.7;">
        <strong>혈액투석(HD)</strong>: 인공신장기로 혈액을 정화하는 방법. 주 3회, 회당 4시간 소요.<br>
        <strong>복막투석(PD)</strong>: 복막을 이용해 가정에서도 가능한 투석 방법.
      </div>
      <div class="tab-filter" id="sidoFilter">
        <button class="tab-btn active" onclick="filterSido('')">전체</button>
        {sido_filter}
      </div>
      <div style="margin-bottom:12px;font-size:.88rem;color:var(--text-secondary);">
        <strong id="resultCount" style="color:var(--primary)">{len(hospitals)}</strong>개 투석 가능 요양병원
      </div>
      <div class="facility-list" id="dialysisList">{cards}</div>
      {ad_banner('ad-mid')}
    </div>
    <aside>
      <div class="sidebar-sticky">
        {ad_banner('ad-side')}
      </div>
    </aside>
  </div>
</div>
<script src="{root}js/facility-render.js?v={JS_VERSION}"></script>
<script>
const ALL_D={json_embed(hospitals)};
function filterSido(sido){{
  document.querySelectorAll('#sidoFilter .tab-btn').forEach(b=>b.classList.toggle('active',b.textContent===(sido||'전체')));
  const f=sido?ALL_D.filter(h=>h.sido_nm===sido):ALL_D;
  document.getElementById('resultCount').textContent=f.length;
  const list=document.getElementById('dialysisList');
  let html=f.slice(0,100).map(h=>{{
    const grade=h.nursing_grade?`<span class="tag tag-grade">🏅 간호 ${{h.nursing_grade}}</span>`:'';
    const bed=h.bed_cnt?`<span class="tag" style="background:#F0FDFA;color:#0F766E;">🛏️ ${{h.bed_cnt}}병상</span>`:'';
    const mc=h.dialysis_machine_cnt?`<span class="tag" style="background:#EDE9FE;color:#6D28D9;">💉 인공신장기 ${{h.dialysis_machine_cnt}}대</span>`:'<span class="tag" style="background:#EDE9FE;color:#6D28D9;">💉 투석가능</span>';
    const mapBtn=(h.x&&h.y)?`<a href="{root}map.html?x=${{h.x}}&y=${{h.y}}&name=${{encodeURIComponent(h.name)}}" onclick="openMapPopup(this.href);return false;" rel="noopener" class="btn-call">🗺️ 지도보기</a>`:'';
    const urlBtn=h.url?`<a href="${{h.url}}" target="_blank" rel="noopener" class="btn-call">🌐 홈페이지</a>`:'';
    return `<div class="facility-card"><div class="facility-card-body"><div class="facility-name">${{h.name}}</div><div class="facility-meta"><span>📍 ${{h.sido_nm}} ${{h.sggu_nm}}</span></div><div class="facility-tags">${{mc}}${{grade}}${{bed}}</div></div><div class="facility-card-right"><span class="status-badge status-open">요양병원</span>${{h.tel?`<a href="tel:${{h.tel}}" class="btn-call">📞 ${{h.tel}}</a>`:''}}${{mapBtn}}${{urlBtn}}</div></div>`;
  }});
  if(html.length>9)html.splice(8,0,'<div class="ad-banner ad-inline"><ins class="adsbygoogle" style="display:block" data-ad-client="ca-pub-6464921081676309" data-ad-slot="7080296704" data-ad-format="auto" data-full-width-responsive="true"></ins></div>');
  list.innerHTML=html.join('');
  list.querySelectorAll('.ad-inline .adsbygoogle:not([data-adsbygoogle-status])').forEach(()=>{{try{{(window.adsbygoogle=window.adsbygoogle||[]).push({{}});}}catch(e){{}}}});
}}
</script>
{footer_html(root)}"""

    save_html(DOCS_DIR / "요양병원" / "투석.html", page)


def _generate_nursing_grade_page(hospitals: list):
    root      = "../"
    canonical = "요양병원/간호등급.html"
    title     = "요양병원 간호등급 뜻 — 1등급 요양병원 찾기 | hosppass"
    desc      = "요양병원 간호등급 기준과 의미를 알아보세요. 간호등급 1등급 요양병원 목록을 지역별로 확인할 수 있습니다."

    grade_data = [
        ("1등급", "2.0 미만", "최우수"),
        ("2등급", "2.0~2.5", "우수"),
        ("3등급", "2.5~3.0", "양호"),
        ("4등급", "3.0~3.5", "보통"),
        ("5등급", "3.5~4.0", "보통"),
        ("6등급", "4.0~4.5", "주의"),
        ("7등급", "4.5 이상", "주의"),
    ]
    grade_rows = "".join(
        f'<tr><td style="font-weight:700;color:{"var(--primary)" if i<2 else "var(--text-primary)"}">{g}</td>'
        f'<td>{r}명</td><td><span class="tag {"tag-grade" if i<2 else "tag-closed"}">{l}</span></td></tr>'
        for i, (g, r, l) in enumerate(grade_data)
    )
    grade1 = [h for h in hospitals if h.get("nursing_grade") == "1등급"]
    _grade1_page = grade1[:50]
    _grade1_htmls = [_nursing_card_html(h, root) for h in _grade1_page]
    if len(_grade1_htmls) > 9:
        _grade1_htmls.insert(8, ad_banner('ad-inline'))
    grade1_cards = "".join(_grade1_htmls)

    page = f"""{header_html(title, desc, canonical, 1)}
<section style="background:linear-gradient(135deg,#7C3AED 0%,#0D9488 100%);color:#fff;padding:40px 16px;text-align:center;">
  <div class="container">
    <h1 style="font-size:1.9rem;font-weight:800;margin-bottom:8px;">🏅 요양병원 간호등급 안내</h1>
    <p style="opacity:.88;">간호등급은 요양병원 선택의 가장 중요한 기준입니다</p>
  </div>
</section>
<div class="container section">
  <div class="layout-with-sidebar">
    <div class="layout-main">
      {ad_banner('ad-top')}
      <h2 class="section-title" style="margin-top:24px;">간호등급 기준표</h2>
      <div style="overflow-x:auto;">
        <table style="width:100%;border-collapse:collapse;font-size:.9rem;">
          <thead>
            <tr style="background:var(--primary);color:#fff;">
              <th style="padding:10px 14px;text-align:left;">등급</th>
              <th style="padding:10px 14px;text-align:left;">간호사 1인당 환자 수</th>
              <th style="padding:10px 14px;text-align:left;">평가</th>
            </tr>
          </thead>
          <tbody>{grade_rows}</tbody>
        </table>
      </div>
      <div style="margin-top:24px;padding:20px;background:var(--primary-light);border-radius:var(--radius);font-size:.9rem;line-height:1.8;">
        <strong>간호등급이 중요한 이유</strong><br>
        간호등급은 입원 환자 1명당 간호사가 얼마나 배치되어 있는지를 나타냅니다.
        1등급일수록 간호사 수가 많아 환자 케어의 질이 높습니다.
        욕창 예방, 투약 관리, 응급 대응 등 모든 면에서 차이가 납니다.
      </div>
      <h2 class="section-title" style="margin-top:32px;">간호등급 1등급 요양병원 ({len(grade1)}개)</h2>
      <div class="facility-list">{grade1_cards}</div>
      {ad_banner('ad-mid')}
    </div>
    <aside>
      <div class="sidebar-sticky">
        {ad_banner('ad-side')}
      </div>
    </aside>
  </div>
</div>
<script src="{root}js/facility-render.js?v={JS_VERSION}"></script>
{footer_html(root)}"""

    save_html(DOCS_DIR / "요양병원" / "간호등급.html", page)


# ── 3.5 치매안심센터 지역별 페이지 ──────────────────────────

def _dementia_card_html(c: dict, root: str = "") -> str:
    staff_parts = []
    if c.get("doctor_cnt") and c["doctor_cnt"] != "0":
        staff_parts.append(f'👨‍⚕️ 의사 {c["doctor_cnt"]}명')
    if c.get("nurse_cnt") and c["nurse_cnt"] != "0":
        staff_parts.append(f'👩‍⚕️ 간호사 {c["nurse_cnt"]}명')
    if c.get("social_worker_cnt") and c["social_worker_cnt"] != "0":
        staff_parts.append(f'🧑‍💼 사회복지사 {c["social_worker_cnt"]}명')
    staff_row = (
        f'<div style="margin-top:5px;font-size:.8rem;color:var(--text-light);">{" · ".join(staff_parts)}</div>'
        if staff_parts else ""
    )
    programs = (c.get("programs") or "").split("+")
    program_tags = "".join(f'<span class="tag tag-dept">{esc(p.strip())}</span>' for p in programs[:3] if p.strip())
    map_btn = (
        f'<a href="{root}map.html?x={esc(c["x"])}&y={esc(c["y"])}&name={quote(str(c.get("name","")))}" '
        f'onclick="openMapPopup(this.href);return false;" rel="noopener" class="btn-call">🗺️ 지도보기</a>'
        if c.get("x") and c.get("y") else ""
    )
    return f"""<div class="facility-card">
  <div class="facility-card-body">
    <div class="facility-name">{esc(c.get("name",""))}</div>
    <div class="facility-meta"><span>📍 {esc(c.get("addr",""))}</span></div>
    <div class="facility-tags">{program_tags}</div>
    {staff_row}
  </div>
  <div class="facility-card-right">
    <span class="status-badge status-open">치매안심센터</span>
    {f'<a href="tel:{esc(c["tel"])}" class="btn-call">📞 {esc(c["tel"])}</a>' if c.get("tel") else ""}
    {map_btn}
  </div>
</div>"""


def generate_dementia_pages(centers: list):
    print("[3.5/4] 치매안심센터 페이지 생성")

    by_region = defaultdict(list)
    for c in centers:
        key = (c.get("sido_nm", ""), c.get("sggu_nm", ""))
        by_region[key].append(c)

    sido_map = defaultdict(list)
    count = 0
    for (sido_nm, sggu_nm), items in sorted(by_region.items()):
        if not sido_nm or not sggu_nm:
            continue
        sido_map[sido_nm].append(sggu_nm)
        _generate_dementia_region_page(sido_nm, sggu_nm, items)
        count += 1

    for sido_nm, sggus in sido_map.items():
        _generate_dementia_sido_index(sido_nm, sorted(sggus), by_region)

    print(f"  → {count}개 치매안심센터 지역 페이지 생성")


def _generate_dementia_region_page(sido, sggu, centers):
    root      = "../../"
    canonical = f"치매안심센터/{sido}/{sggu}.html"
    title     = f"{sggu} 치매안심센터 — 위치·전화번호·프로그램 안내 | hosppass"
    desc      = f"{sggu} 치매안심센터 위치, 전화번호, 운영기관, 치매관리 프로그램을 확인하세요."
    keywords  = f"{sggu} 치매안심센터, {sido} {sggu} 치매센터, {sggu} 치매검사, {sggu} 치매상담"

    cards = "".join(_dementia_card_html(c, root) for c in centers)

    page = f"""{header_html(title, desc, canonical, 2, keywords)}
<section style="background:linear-gradient(135deg,#7C3AED 0%,#0D9488 100%);color:#fff;padding:32px 16px;">
  <div class="container">
    <nav class="breadcrumb" style="color:rgba(255,255,255,.7);margin-bottom:12px;">
      <a href="{root}index.html" style="color:rgba(255,255,255,.8)">홈</a>
      <span class="sep">›</span>
      <a href="{root}dementia.html" style="color:rgba(255,255,255,.8)">치매안심센터</a>
      <span class="sep">›</span>
      <span style="color:#fff">{esc(sggu)}</span>
    </nav>
    <h1 style="font-size:1.7rem;font-weight:800;margin-bottom:6px;">{esc(sggu)} 치매안심센터</h1>
    <p style="opacity:.88;font-size:.95rem;">위치, 전화번호, 치매관리 프로그램을 확인하세요</p>
  </div>
</section>
<div class="container" style="padding-top:20px">{ad_banner('ad-top')}</div>
<div class="container section">
  <div class="layout-with-sidebar">
    <div class="layout-main">
      <div style="margin-bottom:12px;font-size:.88rem;color:var(--text-secondary);">
        <strong>{len(centers)}</strong>개 치매안심센터
      </div>
      <div class="facility-list">{cards}</div>
      {ad_banner('ad-mid')}
      <div style="margin-top:32px;">
        <h2 class="section-title">{esc(sggu)} 치매안심센터 지도</h2>
        <div class="map-wrap"><div id="map"></div></div>
      </div>
      <div style="margin-top:32px;padding:24px;background:var(--primary-light);border-radius:var(--radius);font-size:.9rem;line-height:1.8;color:var(--text-secondary);">
        <h2 style="font-size:1rem;font-weight:700;color:var(--text-primary);margin-bottom:8px;">치매안심센터란?</h2>
        <p>보건복지부와 지방자치단체가 설치·운영하는 치매 전담 기관으로, 치매 조기검진, 상담, 치매치료관리비 지원, 치매환자 가족 교육, 인지강화 프로그램 등을 무료로 제공합니다.</p>
        <p style="margin-top:8px;">※ 프로그램 및 운영시간은 변경될 수 있으므로 방문 전 반드시 전화로 확인하시기 바랍니다.</p>
      </div>
      <div style="margin:16px 0 8px;">
        <a href="https://wooatown.wooahouse.com/지역/{esc(sido)}.html" target="_blank" rel="noopener"
           style="display:block;text-align:center;padding:12px 16px;border:1px dashed var(--border);border-radius:var(--radius);color:var(--text-secondary);font-size:.85rem;font-weight:600;text-decoration:none;">
          🏠 {esc(sido)} 다른 생활정보 보기 (우아동네) →
        </a>
      </div>
    </div>
    <aside>
      <div class="sidebar-sticky">
        {ad_banner('ad-side')}
      </div>
    </aside>
  </div>
</div>
<script type="text/javascript" src="//dapi.kakao.com/v2/maps/sdk.js?appkey={KAKAO_MAP_KEY}&libraries=services"></script>
<script>
const CENTERS={json_embed([{"name":c.get("name",""),"x":c.get("x",""),"y":c.get("y","")} for c in centers])};
function initMap(){{
  if(typeof kakao==='undefined')return;
  const first=CENTERS.find(c=>c.x&&c.y);
  const map=new kakao.maps.Map(document.getElementById('map'),{{center:new kakao.maps.LatLng(first?.y||37.5,first?.x||127.0),level:5}});
  CENTERS.forEach(c=>{{
    if(!c.x||!c.y)return;
    const marker=new kakao.maps.Marker({{map,position:new kakao.maps.LatLng(parseFloat(c.y),parseFloat(c.x)),title:c.name}});
    const iw=new kakao.maps.InfoWindow({{content:`<div style="padding:8px 10px;font-size:13px;font-weight:600;">${{c.name}}</div>`}});
    kakao.maps.event.addListener(marker,'click',()=>iw.open(map,marker));
  }});
}}
document.addEventListener('DOMContentLoaded',initMap);
</script>
{footer_html(root)}"""

    save_html(DOCS_DIR / "치매안심센터" / sido / f"{sggu}.html", page)


def _generate_dementia_sido_index(sido_nm, sggus, by_region):
    root      = "../"
    canonical = f"치매안심센터/{sido_nm}/index.html"
    title     = f"{sido_nm} 치매안심센터 찾기 — 시군구별 목록 | hosppass"
    desc      = f"{sido_nm} 치매안심센터를 시군구별로 확인하세요."
    total     = sum(len(by_region[(sido_nm, sg)]) for sg in sggus)

    links = "".join(
        f'<a href="{esc(s)}.html" class="tab-btn" style="text-align:center;">{esc(s)}</a>'
        for s in sggus
    )
    page = f"""{header_html(title, desc, canonical, 2)}
<section style="background:linear-gradient(135deg,#7C3AED 0%,#0D9488 100%);color:#fff;padding:32px 16px;">
  <div class="container">
    <h1 style="font-size:1.7rem;font-weight:800;">{esc(sido_nm)} 치매안심센터</h1>
    <p style="opacity:.88;margin-top:6px;">시군구를 선택하세요 ({total}개 센터)</p>
  </div>
</section>
<div class="container section">
  <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:8px;">{links}</div>
</div>
{footer_html(root)}"""

    save_html(DOCS_DIR / "치매안심센터" / sido_nm / "index.html", page)


# ── 3.6 산후조리원 지역별 페이지 ────────────────────────────

def _price_fmt(v):
    if not v:
        return ""
    try:
        n = float(v)
        return f"{n:,.0f}만원" if n == int(n) else f"{n:,.1f}만원"
    except ValueError:
        return v


def _postpartum_card_html(c: dict) -> str:
    is_public = c.get("operator") == "공공"
    badge = (
        '<span class="tag" style="background:#DCFCE7;color:#15803D;">🏛️ 공공</span>' if is_public
        else '<span class="tag tag-dept">🏠 민간</span>'
    )
    gp = _price_fmt(c.get("general_room_price"))
    sp = _price_fmt(c.get("special_room_price"))
    price_parts = []
    if gp:
        price_parts.append(f"일반실 {gp}")
    if sp:
        price_parts.append(f"특실 {sp}")
    price_row = (
        f'<div style="margin-top:5px;font-size:.8rem;color:var(--text-light);">💰 {" · ".join(price_parts)} (14일 기준)</div>'
        if price_parts else ""
    )
    return f"""<div class="facility-card">
  <div class="facility-card-body">
    <div class="facility-name">{esc(c.get("name",""))}</div>
    <div class="facility-meta"><span>📍 {esc(c.get("addr",""))}</span></div>
    <div class="facility-tags">{badge}</div>
    {price_row}
  </div>
  <div class="facility-card-right">
    <span class="status-badge status-open">산후조리원</span>
    {f'<a href="tel:{esc(c["tel"])}" class="btn-call">📞 {esc(c["tel"])}</a>' if c.get("tel") else ""}
  </div>
</div>"""


def generate_postpartum_pages(centers: list):
    print("[3.6/4] 산후조리원 페이지 생성")

    by_region = defaultdict(list)
    for c in centers:
        key = (c.get("sido_nm", ""), c.get("sggu_nm", ""))
        by_region[key].append(c)

    sido_map = defaultdict(list)
    count = 0
    for (sido_nm, sggu_nm), items in sorted(by_region.items()):
        if not sido_nm or not sggu_nm:
            continue
        sido_map[sido_nm].append(sggu_nm)
        _generate_postpartum_region_page(sido_nm, sggu_nm, items)
        count += 1

    for sido_nm, sggus in sido_map.items():
        _generate_postpartum_sido_index(sido_nm, sorted(sggus), by_region)

    print(f"  → {count}개 산후조리원 지역 페이지 생성")


def _generate_postpartum_region_page(sido, sggu, centers):
    root      = "../../"
    canonical = f"산후조리원/{sido}/{sggu}.html"
    public_cnt = sum(1 for c in centers if c.get("operator") == "공공")
    title     = f"{sggu} 산후조리원 — 공공·민간 가격 비교 | hosppass"
    desc      = f"{sggu} 산후조리원 목록과 가격을 확인하세요. 공공산후조리원 {public_cnt}곳 포함, 일반실·특실 가격 비교."
    keywords  = f"{sggu} 산후조리원, {sido} {sggu} 공공산후조리원, {sggu} 산후조리원 가격, {sggu} 산후조리원 비용"

    # 공공 우선 정렬
    sorted_centers = sorted(centers, key=lambda c: 0 if c.get("operator") == "공공" else 1)
    cards = "".join(_postpartum_card_html(c) for c in sorted_centers)

    page = f"""{header_html(title, desc, canonical, 2, keywords)}
<section style="background:linear-gradient(135deg,#7C3AED 0%,#0D9488 100%);color:#fff;padding:32px 16px;">
  <div class="container">
    <nav class="breadcrumb" style="color:rgba(255,255,255,.7);margin-bottom:12px;">
      <a href="{root}index.html" style="color:rgba(255,255,255,.8)">홈</a>
      <span class="sep">›</span>
      <a href="{root}postpartum.html" style="color:rgba(255,255,255,.8)">산후조리원</a>
      <span class="sep">›</span>
      <span style="color:#fff">{esc(sggu)}</span>
    </nav>
    <h1 style="font-size:1.7rem;font-weight:800;margin-bottom:6px;">{esc(sggu)} 산후조리원</h1>
    <p style="opacity:.88;font-size:.95rem;">{len(centers)}곳{f" (공공 {public_cnt}곳 포함)" if public_cnt else ""} · 가격은 14일 이용 기준 참고용</p>
  </div>
</section>
<div class="container" style="padding-top:20px">{ad_banner('ad-top')}</div>
<div class="container section">
  <div class="layout-with-sidebar">
    <div class="layout-main">
      <div class="facility-list">{cards}</div>
      {ad_banner('ad-mid')}
      <div style="margin-top:32px;padding:24px;background:var(--primary-light);border-radius:var(--radius);font-size:.9rem;line-height:1.8;color:var(--text-secondary);">
        <h2 style="font-size:1rem;font-weight:700;color:var(--text-primary);margin-bottom:8px;">공공산후조리원이란?</h2>
        <p>지방자치단체가 직접 운영하는 산후조리원으로, 민간 대비 저렴한 비용으로 이용할 수 있습니다. 지역 거주자 우선, 소득 기준 등 자격 조건이 있을 수 있으니 신청 전 해당 지자체에 문의하세요.</p>
        <p style="margin-top:8px;">※ 가격은 2023년 12월 기준 자료로, 실제 비용과 다를 수 있습니다. 예약 전 반드시 전화로 최신 가격을 확인하세요.</p>
      </div>
    </div>
    <aside>
      <div class="sidebar-sticky">
        {ad_banner('ad-side')}
      </div>
    </aside>
  </div>
</div>
{footer_html(root)}"""

    save_html(DOCS_DIR / "산후조리원" / sido / f"{sggu}.html", page)


def _generate_postpartum_sido_index(sido_nm, sggus, by_region):
    root      = "../"
    canonical = f"산후조리원/{sido_nm}/index.html"
    title     = f"{sido_nm} 산후조리원 찾기 — 시군구별 목록 | hosppass"
    desc      = f"{sido_nm} 산후조리원을 시군구별로 확인하세요."
    total     = sum(len(by_region[(sido_nm, sg)]) for sg in sggus)

    links = "".join(
        f'<a href="{esc(s)}.html" class="tab-btn" style="text-align:center;">{esc(s)}</a>'
        for s in sggus
    )
    page = f"""{header_html(title, desc, canonical, 2)}
<section style="background:linear-gradient(135deg,#7C3AED 0%,#0D9488 100%);color:#fff;padding:32px 16px;">
  <div class="container">
    <h1 style="font-size:1.7rem;font-weight:800;">{esc(sido_nm)} 산후조리원</h1>
    <p style="opacity:.88;margin-top:6px;">시군구를 선택하세요 ({total}곳)</p>
  </div>
</section>
<div class="container section">
  <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:8px;">{links}</div>
</div>
{footer_html(root)}"""

    save_html(DOCS_DIR / "산후조리원" / sido_nm / "index.html", page)


# ── 3.7 안전상비의약품 판매업소 지역별 페이지 ──────────────────

OTC_FOLDER = "안전상비의약품판매업소"


def _otc_card_html(c: dict, root: str = "") -> str:
    map_btn = (
        f'<a href="{root}map.html?x={esc(c["x"])}&y={esc(c["y"])}&name={quote(str(c.get("name","")))}" '
        f'onclick="openMapPopup(this.href);return false;" rel="noopener" class="btn-call">🗺️ 지도보기</a>'
        if c.get("x") and c.get("y") else ""
    )
    return f"""<div class="facility-card">
  <div class="facility-card-body">
    <div class="facility-name">{esc(c.get("name",""))}</div>
    <div class="facility-meta"><span>📍 {esc(c.get("addr",""))}</span></div>
    <div class="facility-tags"><span class="tag tag-dept">안전상비의약품</span></div>
  </div>
  <div class="facility-card-right">
    <span class="status-badge status-open">영업중</span>
    {f'<a href="tel:{esc(c["tel"])}" class="btn-call">📞 {esc(c["tel"])}</a>' if c.get("tel") else ""}
    {map_btn}
  </div>
</div>"""


def generate_otc_pages(stores: list):
    print("[3.7/4] 안전상비의약품 판매업소 페이지 생성")

    by_region = defaultdict(list)
    for c in stores:
        key = (c.get("sido_nm", ""), c.get("sggu_nm", ""))
        by_region[key].append(c)

    sido_map = defaultdict(list)
    count = 0
    for (sido_nm, sggu_nm), items in sorted(by_region.items()):
        if not sido_nm or not sggu_nm:
            continue
        sido_map[sido_nm].append(sggu_nm)
        _generate_otc_region_page(sido_nm, sggu_nm, items)
        count += 1

    for sido_nm, sggus in sido_map.items():
        _generate_otc_sido_index(sido_nm, sorted(sggus), by_region)

    print(f"  → {count}개 안전상비의약품 판매업소 지역 페이지 생성")


def _generate_otc_region_page(sido, sggu, stores):
    root      = "../../"
    canonical = f"{OTC_FOLDER}/{sido}/{sggu}.html"
    title     = f"{sggu} 안전상비의약품 판매업소 — 심야 편의점 상비약 구입처 | hosppass"
    desc      = f"{sggu}에서 약국이 문을 닫았을 때 타이레놀 등 안전상비의약품을 살 수 있는 편의점 {len(stores)}곳의 위치와 주소를 확인하세요."
    keywords  = (
        f"{sggu} 안전상비의약품, {sggu} 편의점 상비약, {sggu} 심야약국, "
        f"{sggu} 타이레놀 파는곳, {sido} {sggu} 안전상비의약품 판매업소, {sggu} 24시간 약"
    )

    cards = "".join(_otc_card_html(c, root) for c in stores)

    page = f"""{header_html(title, desc, canonical, 2, keywords)}
<section style="background:linear-gradient(135deg,#7C3AED 0%,#0D9488 100%);color:#fff;padding:32px 16px;">
  <div class="container">
    <nav class="breadcrumb" style="color:rgba(255,255,255,.7);margin-bottom:12px;">
      <a href="{root}index.html" style="color:rgba(255,255,255,.8)">홈</a>
      <span class="sep">›</span>
      <a href="{root}otc-medicine.html" style="color:rgba(255,255,255,.8)">안전상비의약품 판매업소</a>
      <span class="sep">›</span>
      <span style="color:#fff">{esc(sggu)}</span>
    </nav>
    <h1 style="font-size:1.7rem;font-weight:800;margin-bottom:6px;">{esc(sggu)} 안전상비의약품 판매업소</h1>
    <p style="opacity:.88;font-size:.95rem;">약국이 문을 닫은 밤·주말에도 타이레놀 등 상비약을 살 수 있는 편의점을 확인하세요</p>
  </div>
</section>
<div class="container" style="padding-top:20px">{ad_banner('ad-top')}</div>
<div class="container section">
  <div class="layout-with-sidebar">
    <div class="layout-main">
      <div style="margin-bottom:12px;font-size:.88rem;color:var(--text-secondary);">
        <strong>{len(stores)}</strong>곳의 안전상비의약품 판매업소
      </div>
      <div class="facility-list">{cards}</div>
      {ad_banner('ad-mid')}
      <div style="margin-top:32px;">
        <h2 class="section-title">{esc(sggu)} 안전상비의약품 판매업소 지도</h2>
        <div class="map-wrap"><div id="map"></div></div>
      </div>
      <div style="margin-top:32px;padding:24px;background:var(--primary-light);border-radius:var(--radius);font-size:.9rem;line-height:1.8;color:var(--text-secondary);">
        <h2 style="font-size:1rem;font-weight:700;color:var(--text-primary);margin-bottom:8px;">안전상비의약품 판매업소란?</h2>
        <p>「약사법」에 따라 약국이 아닌 편의점 등에서도 해열진통제(타이레놀 등), 감기약, 소화제, 파스 등 20개 품목의 안전상비의약품을 판매할 수 있도록 지정된 곳입니다. 약국 운영시간 외(심야·주말·공휴일)에 급하게 상비약이 필요할 때 이용할 수 있습니다.</p>
        <p style="margin-top:8px;">※ 매장별 재고·취급 품목은 다를 수 있으므로 방문 전 전화로 확인하시기 바랍니다.</p>
      </div>
      <div style="margin:16px 0 8px;">
        <a href="https://wooatown.wooahouse.com/지역/{esc(sido)}.html" target="_blank" rel="noopener"
           style="display:block;text-align:center;padding:12px 16px;border:1px dashed var(--border);border-radius:var(--radius);color:var(--text-secondary);font-size:.85rem;font-weight:600;text-decoration:none;">
          🏠 {esc(sido)} 다른 생활정보 보기 (우아동네) →
        </a>
      </div>
    </div>
    <aside>
      <div class="sidebar-sticky">
        {ad_banner('ad-side')}
      </div>
    </aside>
  </div>
</div>
<script type="text/javascript" src="//dapi.kakao.com/v2/maps/sdk.js?appkey={KAKAO_MAP_KEY}&libraries=services"></script>
<script>
const CENTERS={json_embed([{"name":c.get("name",""),"x":c.get("x",""),"y":c.get("y","")} for c in stores if c.get("x") and c.get("y")])};
function initMap(){{
  if(typeof kakao==='undefined')return;
  if(!CENTERS.length){{document.getElementById('map').innerHTML='<p style="padding:20px;text-align:center;color:var(--text-light);">지도에 표시할 위치 정보가 없습니다.</p>';return;}}
  const first=CENTERS[0];
  const map=new kakao.maps.Map(document.getElementById('map'),{{center:new kakao.maps.LatLng(first.y,first.x),level:6}});
  CENTERS.forEach(c=>{{
    const marker=new kakao.maps.Marker({{map,position:new kakao.maps.LatLng(parseFloat(c.y),parseFloat(c.x)),title:c.name}});
    const iw=new kakao.maps.InfoWindow({{content:`<div style="padding:8px 10px;font-size:13px;font-weight:600;">${{c.name}}</div>`}});
    kakao.maps.event.addListener(marker,'click',()=>iw.open(map,marker));
  }});
}}
document.addEventListener('DOMContentLoaded',initMap);
</script>
{footer_html(root)}"""

    save_html(DOCS_DIR / OTC_FOLDER / sido / f"{sggu}.html", page)


def _generate_otc_sido_index(sido_nm, sggus, by_region):
    root      = "../"
    canonical = f"{OTC_FOLDER}/{sido_nm}/index.html"
    title     = f"{sido_nm} 안전상비의약품 판매업소 찾기 — 시군구별 목록 | hosppass"
    desc      = f"{sido_nm} 안전상비의약품 판매업소(심야 상비약 편의점)를 시군구별로 확인하세요."
    total     = sum(len(by_region[(sido_nm, sg)]) for sg in sggus)

    links = "".join(
        f'<a href="{esc(s)}.html" class="tab-btn" style="text-align:center;">{esc(s)}</a>'
        for s in sggus
    )
    page = f"""{header_html(title, desc, canonical, 2)}
<section style="background:linear-gradient(135deg,#7C3AED 0%,#0D9488 100%);color:#fff;padding:32px 16px;">
  <div class="container">
    <h1 style="font-size:1.7rem;font-weight:800;">{esc(sido_nm)} 안전상비의약품 판매업소</h1>
    <p style="opacity:.88;margin-top:6px;">시군구를 선택하세요 ({total}곳)</p>
  </div>
</section>
<div class="container section">
  <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:8px;">{links}</div>
</div>
{footer_html(root)}"""

    save_html(DOCS_DIR / OTC_FOLDER / sido_nm / "index.html", page)


# ── 3.8 교통약자 이동지원센터 지역별 페이지 ──────────────────

TRANSPORT_FOLDER = "교통약자이동지원센터"


def _fmt_time_range(open_t: str, close_t: str) -> str:
    if not open_t or not close_t:
        return "정보 없음"
    return f"{open_t} ~ {close_t}"


def generate_transport_pages(centers: list):
    print("[3.8/4] 교통약자 이동지원센터 페이지 생성")

    by_region = defaultdict(list)
    for c in centers:
        key = (c.get("sido_nm", ""), c.get("sggu_nm", ""))
        by_region[key].append(c)

    sido_map = defaultdict(list)
    count = 0
    for (sido_nm, sggu_nm), items in sorted(by_region.items()):
        if not sido_nm or not sggu_nm:
            continue
        sido_map[sido_nm].append(sggu_nm)
        _generate_transport_region_page(sido_nm, sggu_nm, items)
        count += 1

    for sido_nm, sggus in sido_map.items():
        _generate_transport_sido_index(sido_nm, sorted(sggus), by_region)

    print(f"  → {count}개 교통약자 이동지원센터 지역 페이지 생성")


def _transport_card_html(c: dict, root: str = "") -> str:
    map_btn = (
        f'<a href="{root}map.html?x={esc(c["x"])}&y={esc(c["y"])}&name={quote(str(c.get("name","")))}" '
        f'onclick="openMapPopup(this.href);return false;" rel="noopener" class="btn-call">🗺️ 지도보기</a>'
        if c.get("x") and c.get("y") else ""
    )
    reserve_btn = (
        f'<a href="tel:{esc(c["reserveTel"])}" class="btn-call" style="background:var(--primary);color:#fff;">'
        f'📞 예약전화 {esc(c["reserveTel"])}</a>'
        if c.get("reserveTel") else ""
    )
    vehicle_bits = []
    if c.get("carHoldCo"):
        vehicle_bits.append(f'차량 {esc(c["carHoldCo"])}대')
    if c.get("slopeCo") and c["slopeCo"] != "0":
        vehicle_bits.append(f'슬로프형 {esc(c["slopeCo"])}대')
    if c.get("liftCo") and c["liftCo"] != "0":
        vehicle_bits.append(f'리프트형 {esc(c["liftCo"])}대')
    vehicle_line = " · ".join(vehicle_bits)

    detail_rows = []
    if c.get("useTarget"):
        detail_rows.append(f'<div class="facility-meta"><span>👤 이용대상: {esc(c["useTarget"])}</span></div>')
    if c.get("useCharge"):
        detail_rows.append(f'<div class="facility-meta"><span>💰 요금: {esc(c["useCharge"])}</span></div>')
    if c.get("weekdayReserveOpen"):
        detail_rows.append(
            f'<div class="facility-meta"><span>🕐 평일 예약접수 {_fmt_time_range(c.get("weekdayReserveOpen",""), c.get("weekdayReserveClose",""))}'
            f'{" · 주말 " + _fmt_time_range(c.get("weekendReserveOpen",""), c.get("weekendReserveClose","")) if c.get("weekendReserveOpen") else ""}</span></div>'
        )
    if c.get("insideArea") or c.get("outsideArea"):
        area = " / ".join(x for x in [c.get("insideArea",""), c.get("outsideArea","")] if x)
        detail_rows.append(f'<div class="facility-meta"><span>🗺️ 운행지역: {esc(area)}</span></div>')

    return f"""<div class="facility-card">
  <div class="facility-card-body">
    <div class="facility-name">{esc(c.get("name",""))}</div>
    <div class="facility-meta"><span>📍 {esc(c.get("addr",""))}</span></div>
    {f'<div class="facility-meta"><span>🚐 {esc(vehicle_line)}</span></div>' if vehicle_line else ""}
    {"".join(detail_rows)}
    <div class="facility-tags"><span class="tag tag-dept">교통약자 이동지원</span></div>
  </div>
  <div class="facility-card-right">
    {reserve_btn}
    {f'<a href="tel:{esc(c["tel"])}" class="btn-call">📞 대표 {esc(c["tel"])}</a>' if c.get("tel") and c.get("tel") != c.get("reserveTel") else ""}
    {map_btn}
  </div>
</div>"""


def _generate_transport_region_page(sido, sggu, centers):
    root      = "../../"
    canonical = f"{TRANSPORT_FOLDER}/{sido}/{sggu}.html"
    title     = f"{sggu} 교통약자 이동지원센터 — 장애인콜택시 예약전화 | hosppass"
    desc      = f"{sggu} 교통약자(장애인·노약자) 이동지원센터 {len(centers)}곳의 예약전화, 이용대상, 요금, 운행시간을 확인하세요."
    keywords  = (
        f"{sggu} 장애인콜택시, {sggu} 교통약자이동지원센터, {sggu} 장애인 이동지원, "
        f"{sido} {sggu} 특별교통수단, {sggu} 휠체어 콜택시 예약"
    )

    cards = "".join(_transport_card_html(c, root) for c in centers)

    page = f"""{header_html(title, desc, canonical, 2, keywords)}
<section style="background:linear-gradient(135deg,#7C3AED 0%,#0D9488 100%);color:#fff;padding:32px 16px;">
  <div class="container">
    <nav class="breadcrumb" style="color:rgba(255,255,255,.7);margin-bottom:12px;">
      <a href="{root}index.html" style="color:rgba(255,255,255,.8)">홈</a>
      <span class="sep">›</span>
      <a href="{root}transport.html" style="color:rgba(255,255,255,.8)">교통약자 이동지원센터</a>
      <span class="sep">›</span>
      <span style="color:#fff">{esc(sggu)}</span>
    </nav>
    <h1 style="font-size:1.7rem;font-weight:800;margin-bottom:6px;">{esc(sggu)} 교통약자 이동지원센터</h1>
    <p style="opacity:.88;font-size:.95rem;">휠체어 탑승 가능한 특별교통차량 예약전화와 이용 안내를 확인하세요</p>
  </div>
</section>
<div class="container" style="padding-top:20px">{ad_banner('ad-top')}</div>
<div class="container section">
  <div class="layout-with-sidebar">
    <div class="layout-main">
      <div style="margin-bottom:12px;font-size:.88rem;color:var(--text-secondary);">
        <strong>{len(centers)}</strong>곳의 교통약자 이동지원센터
      </div>
      <div class="facility-list">{cards}</div>
      {ad_banner('ad-mid')}
      <div style="margin-top:32px;">
        <h2 class="section-title">{esc(sggu)} 교통약자 이동지원센터 지도</h2>
        <div class="map-wrap"><div id="map"></div></div>
      </div>
      <div style="margin-top:32px;padding:24px;background:var(--primary-light);border-radius:var(--radius);font-size:.9rem;line-height:1.8;color:var(--text-secondary);">
        <h2 style="font-size:1rem;font-weight:700;color:var(--text-primary);margin-bottom:8px;">교통약자 이동지원센터란?</h2>
        <p>「교통약자의 이동편의 증진법」에 따라 휠체어 탑승설비가 장착된 특별교통차량(장애인콜택시 등)을 운영해, 대중교통 이용이 어려운 교통약자에게 이동 서비스를 제공하는 곳입니다. 대부분 사전 예약제로 운영되며, 관내·관외 운행지역과 이용대상이 지역마다 다를 수 있습니다.</p>
        <p style="margin-top:8px;">※ 이용대상·요금·운행시간은 변경될 수 있으니 예약 전 반드시 전화로 확인하시기 바랍니다.</p>
      </div>
      <div style="margin:16px 0 8px;">
        <a href="https://wooatown.wooahouse.com/지역/{esc(sido)}.html" target="_blank" rel="noopener"
           style="display:block;text-align:center;padding:12px 16px;border:1px dashed var(--border);border-radius:var(--radius);color:var(--text-secondary);font-size:.85rem;font-weight:600;text-decoration:none;">
          🏠 {esc(sido)} 다른 생활정보 보기 (우아동네) →
        </a>
      </div>
    </div>
    <aside>
      <div class="sidebar-sticky">
        {ad_banner('ad-side')}
      </div>
    </aside>
  </div>
</div>
<script type="text/javascript" src="//dapi.kakao.com/v2/maps/sdk.js?appkey={KAKAO_MAP_KEY}&libraries=services"></script>
<script>
const CENTERS={json_embed([{"name":c.get("name",""),"x":c.get("x",""),"y":c.get("y","")} for c in centers if c.get("x") and c.get("y")])};
function initMap(){{
  if(typeof kakao==='undefined')return;
  if(!CENTERS.length){{document.getElementById('map').innerHTML='<p style="padding:20px;text-align:center;color:var(--text-light);">지도에 표시할 위치 정보가 없습니다.</p>';return;}}
  const first=CENTERS[0];
  const map=new kakao.maps.Map(document.getElementById('map'),{{center:new kakao.maps.LatLng(first.y,first.x),level:6}});
  CENTERS.forEach(c=>{{
    const marker=new kakao.maps.Marker({{map,position:new kakao.maps.LatLng(parseFloat(c.y),parseFloat(c.x)),title:c.name}});
    const iw=new kakao.maps.InfoWindow({{content:`<div style="padding:8px 10px;font-size:13px;font-weight:600;">${{c.name}}</div>`}});
    kakao.maps.event.addListener(marker,'click',()=>iw.open(map,marker));
  }});
}}
document.addEventListener('DOMContentLoaded',initMap);
</script>
{footer_html(root)}"""

    save_html(DOCS_DIR / TRANSPORT_FOLDER / sido / f"{sggu}.html", page)


def _generate_transport_sido_index(sido_nm, sggus, by_region):
    root      = "../"
    canonical = f"{TRANSPORT_FOLDER}/{sido_nm}/index.html"
    title     = f"{sido_nm} 교통약자 이동지원센터 찾기 — 시군구별 목록 | hosppass"
    desc      = f"{sido_nm} 교통약자 이동지원센터(장애인콜택시)를 시군구별로 확인하세요."
    total     = sum(len(by_region[(sido_nm, sg)]) for sg in sggus)

    links = "".join(
        f'<a href="{esc(s)}.html" class="tab-btn" style="text-align:center;">{esc(s)}</a>'
        for s in sggus
    )
    page = f"""{header_html(title, desc, canonical, 2)}
<section style="background:linear-gradient(135deg,#7C3AED 0%,#0D9488 100%);color:#fff;padding:32px 16px;">
  <div class="container">
    <h1 style="font-size:1.7rem;font-weight:800;">{esc(sido_nm)} 교통약자 이동지원센터</h1>
    <p style="opacity:.88;margin-top:6px;">시군구를 선택하세요 ({total}곳)</p>
  </div>
</section>
<div class="container section">
  <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:8px;">{links}</div>
</div>
{footer_html(root)}"""

    save_html(DOCS_DIR / TRANSPORT_FOLDER / sido_nm / "index.html", page)


# ── 3.9 전동휠체어급속충전기 지역별 페이지 ──────────────────

WHEELCHAIR_FOLDER = "전동휠체어급속충전기"


def generate_wheelchair_pages(chargers: list):
    print("[3.9/4] 전동휠체어급속충전기 페이지 생성")

    by_region = defaultdict(list)
    for c in chargers:
        key = (c.get("sido_nm", ""), c.get("sggu_nm", ""))
        by_region[key].append(c)

    sido_map = defaultdict(list)
    count = 0
    for (sido_nm, sggu_nm), items in sorted(by_region.items()):
        if not sido_nm or not sggu_nm:
            continue
        sido_map[sido_nm].append(sggu_nm)
        _generate_wheelchair_region_page(sido_nm, sggu_nm, items)
        count += 1

    for sido_nm, sggus in sido_map.items():
        _generate_wheelchair_sido_index(sido_nm, sorted(sggus), by_region)

    print(f"  → {count}개 전동휠체어급속충전기 지역 페이지 생성")


def _wheelchair_card_html(c: dict, root: str = "") -> str:
    map_btn = (
        f'<a href="{root}map.html?x={esc(c["x"])}&y={esc(c["y"])}&name={quote(str(c.get("name","")))}" '
        f'onclick="openMapPopup(this.href);return false;" rel="noopener" class="btn-call">🗺️ 지도보기</a>'
        if c.get("x") and c.get("y") else ""
    )
    tel_btn = (
        f'<a href="tel:{esc(c["institutionTel"])}" class="btn-call" style="background:var(--primary);color:#fff;">'
        f'📞 {esc(c["institutionTel"])}</a>'
        if c.get("institutionTel") else ""
    )
    detail_rows = []
    if c.get("installLoc"):
        detail_rows.append(f'<div class="facility-meta"><span>📌 설치장소: {esc(c["installLoc"])}</span></div>')
    if c.get("weekdayOpen"):
        detail_rows.append(
            f'<div class="facility-meta"><span>🕐 평일 {_fmt_time_range(c.get("weekdayOpen",""), c.get("weekdayClose",""))}</span></div>'
        )
    features = []
    if c.get("simultUseCount") and c["simultUseCount"] not in ("0", ""):
        features.append(f'동시사용 {esc(c["simultUseCount"])}대')
    if c.get("airInjector"):
        features.append("공기주입 가능")
    if c.get("mobileCharge"):
        features.append("휴대폰 충전 가능")
    if features:
        detail_rows.append(f'<div class="facility-meta"><span>⚡ {" · ".join(features)}</span></div>')

    return f"""<div class="facility-card">
  <div class="facility-card-body">
    <div class="facility-name">{esc(c.get("name",""))}</div>
    <div class="facility-meta"><span>📍 {esc(c.get("addr",""))}</span></div>
    {"".join(detail_rows)}
    <div class="facility-tags"><span class="tag tag-dept">전동휠체어 급속충전기</span></div>
  </div>
  <div class="facility-card-right">
    {tel_btn}
    {map_btn}
  </div>
</div>"""


def _generate_wheelchair_region_page(sido, sggu, items):
    root      = "../../"
    canonical = f"{WHEELCHAIR_FOLDER}/{sido}/{sggu}.html"
    title     = f"{sggu} 전동휠체어 급속충전기 위치 — 설치장소·운영시간 | hosppass"
    desc      = f"{sggu} 전동휠체어·전동스쿠터 급속충전기 {len(items)}곳의 설치장소, 운영시간을 확인하세요."
    keywords  = f"{sggu} 전동휠체어 충전기, {sggu} 전동스쿠터 충전, {sido} {sggu} 휠체어 급속충전기 위치"

    cards = "".join(_wheelchair_card_html(c, root) for c in items)

    page = f"""{header_html(title, desc, canonical, 2, keywords)}
<section style="background:linear-gradient(135deg,#7C3AED 0%,#0D9488 100%);color:#fff;padding:32px 16px;">
  <div class="container">
    <nav class="breadcrumb" style="color:rgba(255,255,255,.7);margin-bottom:12px;">
      <a href="{root}index.html" style="color:rgba(255,255,255,.8)">홈</a>
      <span class="sep">›</span>
      <a href="{root}wheelchair-charger.html" style="color:rgba(255,255,255,.8)">전동휠체어급속충전기</a>
      <span class="sep">›</span>
      <span style="color:#fff">{esc(sggu)}</span>
    </nav>
    <h1 style="font-size:1.7rem;font-weight:800;margin-bottom:6px;">{esc(sggu)} 전동휠체어 급속충전기</h1>
    <p style="opacity:.88;font-size:.95rem;">전동휠체어·전동스쿠터 급속충전기 설치 위치와 이용 안내를 확인하세요</p>
  </div>
</section>
<div class="container" style="padding-top:20px">{ad_banner('ad-top')}</div>
<div class="container section">
  <div class="layout-with-sidebar">
    <div class="layout-main">
      <div style="margin-bottom:12px;font-size:.88rem;color:var(--text-secondary);">
        <strong>{len(items)}</strong>곳의 전동휠체어 급속충전기
      </div>
      <div class="facility-list">{cards}</div>
      {ad_banner('ad-mid')}
      <div style="margin-top:32px;">
        <h2 class="section-title">{esc(sggu)} 전동휠체어 급속충전기 지도</h2>
        <div class="map-wrap"><div id="map"></div></div>
      </div>
      <div style="margin-top:32px;padding:24px;background:var(--primary-light);border-radius:var(--radius);font-size:.9rem;line-height:1.8;color:var(--text-secondary);">
        <h2 style="font-size:1rem;font-weight:700;color:var(--text-primary);margin-bottom:8px;">전동휠체어 급속충전기란?</h2>
        <p>전동휠체어·전동스쿠터 이용자가 외출 중 배터리가 부족할 때 무료로 충전할 수 있도록 지자체가 행정복지센터·복지관 등에 설치한 급속충전 설비입니다. 시설별로 동시사용 가능 대수, 공기주입·휴대폰 충전 지원 여부가 다를 수 있습니다.</p>
        <p style="margin-top:8px;">※ 운영시간·설치 여부는 변경될 수 있으니 방문 전 관리기관에 확인하시기 바랍니다.</p>
      </div>
      <div style="margin:16px 0 8px;">
        <a href="https://wooatown.wooahouse.com/지역/{esc(sido)}.html" target="_blank" rel="noopener"
           style="display:block;text-align:center;padding:12px 16px;border:1px dashed var(--border);border-radius:var(--radius);color:var(--text-secondary);font-size:.85rem;font-weight:600;text-decoration:none;">
          🏠 {esc(sido)} 다른 생활정보 보기 (우아동네) →
        </a>
      </div>
    </div>
    <aside>
      <div class="sidebar-sticky">
        {ad_banner('ad-side')}
      </div>
    </aside>
  </div>
</div>
<script type="text/javascript" src="//dapi.kakao.com/v2/maps/sdk.js?appkey={KAKAO_MAP_KEY}&libraries=services"></script>
<script>
const CENTERS={json_embed([{"name":c.get("name",""),"x":c.get("x",""),"y":c.get("y","")} for c in items if c.get("x") and c.get("y")])};
function initMap(){{
  if(typeof kakao==='undefined')return;
  if(!CENTERS.length){{document.getElementById('map').innerHTML='<p style="padding:20px;text-align:center;color:var(--text-light);">지도에 표시할 위치 정보가 없습니다.</p>';return;}}
  const first=CENTERS[0];
  const map=new kakao.maps.Map(document.getElementById('map'),{{center:new kakao.maps.LatLng(first.y,first.x),level:6}});
  CENTERS.forEach(c=>{{
    const marker=new kakao.maps.Marker({{map,position:new kakao.maps.LatLng(parseFloat(c.y),parseFloat(c.x)),title:c.name}});
    const iw=new kakao.maps.InfoWindow({{content:`<div style="padding:8px 10px;font-size:13px;font-weight:600;">${{c.name}}</div>`}});
    kakao.maps.event.addListener(marker,'click',()=>iw.open(map,marker));
  }});
}}
document.addEventListener('DOMContentLoaded',initMap);
</script>
{footer_html(root)}"""

    save_html(DOCS_DIR / WHEELCHAIR_FOLDER / sido / f"{sggu}.html", page)


def _generate_wheelchair_sido_index(sido_nm, sggus, by_region):
    root      = "../"
    canonical = f"{WHEELCHAIR_FOLDER}/{sido_nm}/index.html"
    title     = f"{sido_nm} 전동휠체어 급속충전기 찾기 — 시군구별 목록 | hosppass"
    desc      = f"{sido_nm} 전동휠체어·전동스쿠터 급속충전기를 시군구별로 확인하세요."
    total     = sum(len(by_region[(sido_nm, sg)]) for sg in sggus)

    links = "".join(
        f'<a href="{esc(s)}.html" class="tab-btn" style="text-align:center;">{esc(s)}</a>'
        for s in sggus
    )
    page = f"""{header_html(title, desc, canonical, 2)}
<section style="background:linear-gradient(135deg,#7C3AED 0%,#0D9488 100%);color:#fff;padding:32px 16px;">
  <div class="container">
    <h1 style="font-size:1.7rem;font-weight:800;">{esc(sido_nm)} 전동휠체어 급속충전기</h1>
    <p style="opacity:.88;margin-top:6px;">시군구를 선택하세요 ({total}곳)</p>
  </div>
</section>
<div class="container section">
  <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:8px;">{links}</div>
</div>
{footer_html(root)}"""

    save_html(DOCS_DIR / WHEELCHAIR_FOLDER / sido_nm / "index.html", page)


# ── 3.10 무료급식소 지역별 페이지 ──────────────────

FREEMEAL_FOLDER = "무료급식소"


def generate_freemeal_pages(meals: list):
    print("[3.10/4] 무료급식소 페이지 생성")

    by_region = defaultdict(list)
    for c in meals:
        key = (c.get("sido_nm", ""), c.get("sggu_nm", ""))
        by_region[key].append(c)

    sido_map = defaultdict(list)
    count = 0
    for (sido_nm, sggu_nm), items in sorted(by_region.items()):
        if not sido_nm or not sggu_nm:
            continue
        sido_map[sido_nm].append(sggu_nm)
        _generate_freemeal_region_page(sido_nm, sggu_nm, items)
        count += 1

    for sido_nm, sggus in sido_map.items():
        _generate_freemeal_sido_index(sido_nm, sorted(sggus), by_region)

    print(f"  → {count}개 무료급식소 지역 페이지 생성")


def _freemeal_card_html(c: dict, root: str = "") -> str:
    map_btn = (
        f'<a href="{root}map.html?x={esc(c["x"])}&y={esc(c["y"])}&name={quote(str(c.get("name","")))}" '
        f'onclick="openMapPopup(this.href);return false;" rel="noopener" class="btn-call">🗺️ 지도보기</a>'
        if c.get("x") and c.get("y") else ""
    )
    tel_btn = (
        f'<a href="tel:{esc(c["tel"])}" class="btn-call" style="background:var(--primary);color:#fff;">'
        f'📞 {esc(c["tel"])}</a>'
        if c.get("tel") else ""
    )
    detail_rows = []
    if c.get("target"):
        detail_rows.append(f'<div class="facility-meta"><span>👤 이용대상: {esc(c["target"])}</span></div>')
    if c.get("mealDate") or c.get("mealTime"):
        when = " ".join(x for x in [c.get("mealDate",""), c.get("mealTime","")] if x)
        detail_rows.append(f'<div class="facility-meta"><span>🕐 배식: {esc(when)}</span></div>')
    if c.get("institution"):
        detail_rows.append(f'<div class="facility-meta"><span>🏛️ 운영기관: {esc(c["institution"])}</span></div>')

    return f"""<div class="facility-card">
  <div class="facility-card-body">
    <div class="facility-name">{esc(c.get("name",""))}</div>
    <div class="facility-meta"><span>📍 {esc(c.get("addr",""))}</span></div>
    {"".join(detail_rows)}
    <div class="facility-tags"><span class="tag tag-dept">무료급식소</span></div>
  </div>
  <div class="facility-card-right">
    {tel_btn}
    {map_btn}
  </div>
</div>"""


def _generate_freemeal_region_page(sido, sggu, items):
    root      = "../../"
    canonical = f"{FREEMEAL_FOLDER}/{sido}/{sggu}.html"
    title     = f"{sggu} 무료급식소 — 배식시간·이용대상 | hosppass"
    desc      = f"{sggu} 무료급식소 {len(items)}곳의 배식 요일·시간, 이용대상, 연락처를 확인하세요."
    keywords  = f"{sggu} 무료급식소, {sggu} 경로식당, {sido} {sggu} 무료급식, {sggu} 결식우려노인 급식"

    cards = "".join(_freemeal_card_html(c, root) for c in items)

    page = f"""{header_html(title, desc, canonical, 2, keywords)}
<section style="background:linear-gradient(135deg,#7C3AED 0%,#0D9488 100%);color:#fff;padding:32px 16px;">
  <div class="container">
    <nav class="breadcrumb" style="color:rgba(255,255,255,.7);margin-bottom:12px;">
      <a href="{root}index.html" style="color:rgba(255,255,255,.8)">홈</a>
      <span class="sep">›</span>
      <a href="{root}free-meal.html" style="color:rgba(255,255,255,.8)">무료급식소</a>
      <span class="sep">›</span>
      <span style="color:#fff">{esc(sggu)}</span>
    </nav>
    <h1 style="font-size:1.7rem;font-weight:800;margin-bottom:6px;">{esc(sggu)} 무료급식소</h1>
    <p style="opacity:.88;font-size:.95rem;">결식 우려가 있는 어르신 등을 위한 무료급식소 위치와 배식 시간을 확인하세요</p>
  </div>
</section>
<div class="container" style="padding-top:20px">{ad_banner('ad-top')}</div>
<div class="container section">
  <div class="layout-with-sidebar">
    <div class="layout-main">
      <div style="margin-bottom:12px;font-size:.88rem;color:var(--text-secondary);">
        <strong>{len(items)}</strong>곳의 무료급식소
      </div>
      <div class="facility-list">{cards}</div>
      {ad_banner('ad-mid')}
      <div style="margin-top:32px;">
        <h2 class="section-title">{esc(sggu)} 무료급식소 지도</h2>
        <div class="map-wrap"><div id="map"></div></div>
      </div>
      <div style="margin-top:32px;padding:24px;background:var(--primary-light);border-radius:var(--radius);font-size:.9rem;line-height:1.8;color:var(--text-secondary);">
        <h2 style="font-size:1rem;font-weight:700;color:var(--text-primary);margin-bottom:8px;">무료급식소란?</h2>
        <p>결식 우려가 있는 노인·저소득층 등을 대상으로 지자체·복지관·종교시설 등이 무료 또는 저렴한 비용으로 식사를 제공하는 곳입니다. 배식 요일·시간, 이용대상이 시설마다 다르므로 방문 전 확인이 필요합니다.</p>
        <p style="margin-top:8px;">※ 운영 여부·배식시간은 변경될 수 있으니 방문 전 반드시 전화로 확인하시기 바랍니다.</p>
      </div>
      <div style="margin:16px 0 8px;">
        <a href="https://wooatown.wooahouse.com/지역/{esc(sido)}.html" target="_blank" rel="noopener"
           style="display:block;text-align:center;padding:12px 16px;border:1px dashed var(--border);border-radius:var(--radius);color:var(--text-secondary);font-size:.85rem;font-weight:600;text-decoration:none;">
          🏠 {esc(sido)} 다른 생활정보 보기 (우아동네) →
        </a>
      </div>
    </div>
    <aside>
      <div class="sidebar-sticky">
        {ad_banner('ad-side')}
      </div>
    </aside>
  </div>
</div>
<script type="text/javascript" src="//dapi.kakao.com/v2/maps/sdk.js?appkey={KAKAO_MAP_KEY}&libraries=services"></script>
<script>
const CENTERS={json_embed([{"name":c.get("name",""),"x":c.get("x",""),"y":c.get("y","")} for c in items if c.get("x") and c.get("y")])};
function initMap(){{
  if(typeof kakao==='undefined')return;
  if(!CENTERS.length){{document.getElementById('map').innerHTML='<p style="padding:20px;text-align:center;color:var(--text-light);">지도에 표시할 위치 정보가 없습니다.</p>';return;}}
  const first=CENTERS[0];
  const map=new kakao.maps.Map(document.getElementById('map'),{{center:new kakao.maps.LatLng(first.y,first.x),level:6}});
  CENTERS.forEach(c=>{{
    const marker=new kakao.maps.Marker({{map,position:new kakao.maps.LatLng(parseFloat(c.y),parseFloat(c.x)),title:c.name}});
    const iw=new kakao.maps.InfoWindow({{content:`<div style="padding:8px 10px;font-size:13px;font-weight:600;">${{c.name}}</div>`}});
    kakao.maps.event.addListener(marker,'click',()=>iw.open(map,marker));
  }});
}}
document.addEventListener('DOMContentLoaded',initMap);
</script>
{footer_html(root)}"""

    save_html(DOCS_DIR / FREEMEAL_FOLDER / sido / f"{sggu}.html", page)


def _generate_freemeal_sido_index(sido_nm, sggus, by_region):
    root      = "../"
    canonical = f"{FREEMEAL_FOLDER}/{sido_nm}/index.html"
    title     = f"{sido_nm} 무료급식소 찾기 — 시군구별 목록 | hosppass"
    desc      = f"{sido_nm} 무료급식소를 시군구별로 확인하세요."
    total     = sum(len(by_region[(sido_nm, sg)]) for sg in sggus)

    links = "".join(
        f'<a href="{esc(s)}.html" class="tab-btn" style="text-align:center;">{esc(s)}</a>'
        for s in sggus
    )
    page = f"""{header_html(title, desc, canonical, 2)}
<section style="background:linear-gradient(135deg,#7C3AED 0%,#0D9488 100%);color:#fff;padding:32px 16px;">
  <div class="container">
    <h1 style="font-size:1.7rem;font-weight:800;">{esc(sido_nm)} 무료급식소</h1>
    <p style="opacity:.88;margin-top:6px;">시군구를 선택하세요 ({total}곳)</p>
  </div>
</section>
<div class="container section">
  <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:8px;">{links}</div>
</div>
{footer_html(root)}"""

    save_html(DOCS_DIR / FREEMEAL_FOLDER / sido_nm / "index.html", page)


# ── 4. sitemap.xml ─────────────────────────────────────────

def _encode_url(path: str) -> str:
    # 슬래시는 유지, 나머지 비ASCII 문자 퍼센트 인코딩
    return "/".join(quote(seg, safe="") for seg in path.split("/"))

def generate_sitemap(pages: list):
    print("[4/4] sitemap.xml 생성")
    urls = "\n".join(
        f"  <url><loc>{SITE_URL}/{_encode_url(p)}</loc><changefreq>weekly</changefreq><priority>0.8</priority></url>"
        for p in pages
    )
    sitemap = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>{SITE_URL}/</loc><changefreq>daily</changefreq><priority>1.0</priority></url>
{urls}
</urlset>"""
    (DOCS_DIR / "sitemap.xml").write_text(sitemap, encoding="utf-8")
    print(f"  → {len(pages)+1}개 URL 등록")


# ── 메인 ───────────────────────────────────────────────────

def main():
    print(f"[hosppass] 페이지 생성 시작 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")

    hospitals = (load_json(DATA_DIR / "hospitals.json") or {}).get("items", [])
    pharmacies = (load_json(DATA_DIR / "pharmacies.json") or {}).get("items", [])
    nursing    = (load_json(DATA_DIR / "nursing_hospitals.json") or {}).get("items", [])
    dementia   = (load_json(DATA_DIR / "dementia_centers.json") or {}).get("items", [])
    postpartum = (load_json(DATA_DIR / "postpartum_centers.json") or {}).get("items", [])
    otc_medicine = (load_json(DATA_DIR / "otc_medicine_stores.json") or {}).get("items", [])
    transport  = (load_json(DATA_DIR / "transport_centers.json") or {}).get("items", [])
    wheelchair = (load_json(DATA_DIR / "wheelchair_chargers.json") or {}).get("items", [])
    freemeal   = (load_json(DATA_DIR / "free_meals.json") or {}).get("items", [])

    print(f"  병원 {len(hospitals)}개 / 약국 {len(pharmacies)}개 / 요양병원 {len(nursing)}개 / 치매안심센터 {len(dementia)}개 / 산후조리원 {len(postpartum)}개 / 안전상비의약품 판매업소 {len(otc_medicine)}개 / 교통약자 이동지원센터 {len(transport)}개 / 전동휠체어급속충전기 {len(wheelchair)}개 / 무료급식소 {len(freemeal)}개 로드")

    generate_region_pages(hospitals, pharmacies)
    generate_specialty_pages(hospitals)
    if nursing:
        generate_nursing_pages(nursing)
    else:
        print("[3/4] 요양병원 데이터 없음 — 건너뜀")
    if dementia:
        generate_dementia_pages(dementia)
    else:
        print("[3.5/4] 치매안심센터 데이터 없음 — 건너뜀")
    if postpartum:
        generate_postpartum_pages(postpartum)
    else:
        print("[3.6/4] 산후조리원 데이터 없음 — 건너뜀")
    if otc_medicine:
        generate_otc_pages(otc_medicine)
    else:
        print("[3.7/4] 안전상비의약품 판매업소 데이터 없음 — 건너뜀")
    if transport:
        generate_transport_pages(transport)
    else:
        print("[3.8/4] 교통약자 이동지원센터 데이터 없음 — 건너뜀")
    if wheelchair:
        generate_wheelchair_pages(wheelchair)
    else:
        print("[3.9/4] 전동휠체어급속충전기 데이터 없음 — 건너뜀")
    if freemeal:
        generate_freemeal_pages(freemeal)
    else:
        print("[3.10/4] 무료급식소 데이터 없음 — 건너뜀")

    # sitemap용 URL 목록 수집 (noindex 페이지는 제외 — 검색엔진에 소프트 404로 잡히는 것 방지)
    pages = []
    for f in DOCS_DIR.rglob("*.html"):
        rel = f.relative_to(DOCS_DIR).as_posix()
        if rel in ("index.html", "404.html"):
            continue
        if "noindex" in f.read_text(encoding="utf-8"):
            continue
        pages.append(rel)
    generate_sitemap(pages)

    print("\n[완료] 페이지 생성 완료")


if __name__ == "__main__":
    main()
