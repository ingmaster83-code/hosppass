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

ROOT     = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
DOCS_DIR = ROOT / "docs"

KAKAO_MAP_KEY = os.getenv("KAKAO_MAP_KEY", "__KAKAO_MAP_KEY__")
SITE_URL      = "https://hosp.wooahouse.com"

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
  <meta property="og:title" content="{esc(title)}">
  <meta property="og:description" content="{esc(desc)}">
  <meta property="og:type" content="website">
  <meta property="og:url" content="{SITE_URL}/{canonical}">
  <link rel="canonical" href="{SITE_URL}/{canonical}">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="{root}css/style.css">
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
    </nav>
  </div>
</header>
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
      &copy; {datetime.now().year} hosppass.kr
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

        # 데이터 임베딩용 (상위 300개로 제한)
        h_embed = h_list[:300]
        p_embed = p_list[:100]

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
        count += 1

    # 시도 index 생성
    for sido_cd, sido_nm in SIDO_NAME_MAP.items():
        _generate_sido_index(sido_nm, hosp_by_region, pharm_by_region)

    print(f"  → {count}개 시군구 페이지 생성")


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
      <div class="facility-list" id="facilityList"><div class="loading"><div class="spinner"></div> 불러오는 중...</div></div>
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
      </div>
    </aside>
  </div>
</div>

<script type="text/javascript" src="//dapi.kakao.com/v2/maps/sdk.js?appkey={KAKAO_MAP_KEY}&libraries=services"></script>
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

document.addEventListener('DOMContentLoaded',()=>{{buildItems();applyFilter();initMap();}});

function buildItems(){{
  allItems=[
    ...PAGE_DATA.hospitals.map(h=>{{return{{...h,_type:'hosp'}}}}),
    ...PAGE_DATA.pharmacies.map(p=>{{return{{...p,_type:'pharm',cl_nm:'약국',dgsbj:'약국'}}}})
  ];
}}
function filterType(t){{curType=t;curPage=1;document.querySelectorAll('#typeFilter .tab-btn').forEach(b=>b.classList.toggle('active',b.dataset.type===t));applyFilter();}}
function filterDept(d){{curDept=d;curPage=1;document.querySelectorAll('#deptFilter .tab-btn').forEach(b=>b.classList.toggle('active',b.dataset.dept===d));applyFilter();}}
function applyFilter(){{
  filtered=allItems.filter(item=>{{
    if(curType==='hosp'&&item._type!=='hosp')return false;
    if(curType==='pharm'&&item._type!=='pharm')return false;
    if(curType==='night'&&item.status!=='night')return false;
    if(curDept!=='all'&&!(item.dgsbj||'').includes(curDept))return false;
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
  list.innerHTML=items.map(renderCard).join('');
  const total=Math.ceil(filtered.length/PAGE_SIZE);
  document.getElementById('pagination').innerHTML=buildPagination(curPage,total);
}}
function renderCard(item){{
  const smap={{open:['status-open','운영중'],night:['status-night','야간진료'],busy:['status-busy','혼잡'],full:['status-full','만석'],closed:['status-closed','운영종료']}};
  const [scls,stxt]=smap[item.status]||smap.closed;
  const depts=(item.dgsbj||'').split(',').filter(Boolean).slice(0,4).map(d=>`<span class="tag tag-dept">${{d.trim()}}</span>`).join('');
  const grade=item.grade?`<span class="tag tag-grade">⭐ ${{item.grade}}</span>`:'';
  const is24=item.is24h?'<span class="tag tag-open">24시간</span>':'';
  const addr=item.emd_nm?`${{item.emd_nm}} · ${{(item.addr||'').replace(/^[가-힣]+시\\s*[가-힣]+구\\s*/,'')}}`:item.addr||'';
  const dr=item.dr_cnt?`<span>👨‍⚕️ 의사 ${{item.dr_cnt}}명${{item.sdr_cnt?` (전문의 ${{item.sdr_cnt}}명)`:''}}</span>`:'';
  const hoursRow=item.hours
    ?`<div style="margin-top:7px;font-size:.82rem;color:var(--text-secondary);">🕐 ${{item.hours}} <span style="margin-left:6px;color:var(--warning);font-size:.76rem;">· 방문 전 전화 확인 권장</span></div>`
    :`<div style="margin-top:7px;font-size:.78rem;color:var(--text-light);">🕐 진료시간 미제공 — 전화로 확인해주세요</div>`;
  const urlBtn=item.url?`<a href="${{item.url}}" target="_blank" rel="noopener" class="btn-call">🌐 홈페이지</a>`:'';
  return `<div class="facility-card"><div class="facility-card-body"><div class="facility-name">${{item.name}}</div><div class="facility-meta"><span>🏥 ${{item.cl_nm||''}}</span><span>📍 ${{addr}}</span>${{dr}}</div><div class="facility-tags">${{depts}}${{is24}}${{grade}}</div>${{hoursRow}}</div><div class="facility-card-right"><span class="status-badge ${{scls}}">${{stxt}}</span>${{item.tel?`<a href="tel:${{item.tel}}" class="btn-call">📞 ${{item.tel}}</a>`:''}}</div></div>`;
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

    page = f"""{header_html(title, desc, canonical, 2, keywords)}
<section style="background:linear-gradient(135deg,var(--primary) 0%,#0891B2 100%);color:#fff;padding:32px 16px;">
  <div class="container">
    <h1 style="font-size:1.7rem;font-weight:800;">{esc(sido_nm)} 병원 · 약국 찾기</h1>
    <p style="opacity:.88;margin-top:6px;">시군구를 선택하세요</p>
  </div>
</section>
<div class="container section">
  <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:8px;">{links}</div>
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

    for dept_nm, _ in SPECIALTIES:
        filtered = [h for h in hospitals if dept_nm in (h.get("dgsbj") or "")][:300]
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
      <div class="facility-list" id="facilityList"><div class="loading"><div class="spinner"></div> 불러오는 중...</div></div>
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
  list.innerHTML=items.map(h=>`
    <div class="facility-card">
      <div class="facility-card-body">
        <div class="facility-name">${{h.name}}</div>
        <div class="facility-meta"><span>🏥 ${{h.cl_nm||''}}</span><span>📍 ${{h.sido_nm}} ${{h.sggu_nm}} ${{h.emd_nm||''}}</span></div>
      </div>
      <div class="facility-card-right">
        ${{h.tel?`<a href="tel:${{h.tel}}" class="btn-call">📞 ${{h.tel}}</a>`:''}}
      </div>
    </div>`).join('');
  const total=Math.ceil(filtered2.length/PAGE_SIZE);
  document.getElementById('pagination').innerHTML=total<=1?'':Array.from({{length:total}},(_,i)=>`<button class="page-btn${{i+1===page?' active':''}}" onclick="renderPage(${{i+1}})">${{i+1}}</button>`).join('');
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

    # 투석 전문 페이지
    dialysis = [h for h in nursing if h.get("dialysis")]
    _generate_dialysis_page(dialysis)

    # 간호등급 안내 페이지
    _generate_nursing_grade_page(nursing)

    print(f"  → {count}개 요양병원 지역 페이지 + 투석·간호등급 페이지 생성")


def _generate_nursing_region_page(sido, sggu, hospitals):
    root      = "../../"
    canonical = f"요양병원/{sido}/{sggu}.html"
    title     = f"{sggu} 요양병원 — 투석 가능 간호등급 비교 | hosppass"
    desc      = f"{sggu} 요양병원 목록과 상세 정보를 확인하세요. 투석 가능 여부, 간호등급, 병상 수, 평가등급 비교."

    cards = "".join(_nursing_card_html(h) for h in hospitals[:50])

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
  document.getElementById('nursingList').innerHTML=filtered.map(h=>nursingCard(h)).join('');
}}
function nursingCard(h){{
  const dialysisTag=h.dialysis?'<span class="tag" style="background:#EDE9FE;color:#6D28D9;">💉 투석가능</span>':'';
  const gradeTag=h.nursing_grade?`<span class="tag tag-grade">🏅 간호 ${{h.nursing_grade}}</span>`:'';
  const bedTag=h.bed_cnt?`<span class="tag" style="background:#F0FDFA;color:#0F766E;">🛏️ ${{h.bed_cnt}}병상</span>`:'';
  const depts=(h.dgsbj_list||[]).slice(0,3).map(d=>`<span class="tag tag-dept">${{d}}</span>`).join('');
  return `<div class="facility-card"><div class="facility-card-body"><div class="facility-name">${{h.name}}</div><div class="facility-meta"><span>📍 ${{h.addr||''}}</span><span>👨‍⚕️ 의사 ${{h.dr_cnt||0}}명</span></div><div class="facility-tags">${{dialysisTag}}${{gradeTag}}${{bedTag}}${{depts}}</div></div><div class="facility-card-right"><span class="status-badge status-open">요양병원</span>${{h.tel?`<a href="tel:${{h.tel}}" class="btn-call">📞 ${{h.tel}}</a>`:''}}</div></div>`;
}}
</script>
{footer_html(root)}"""

    save_html(DOCS_DIR / "요양병원" / sido / f"{sggu}.html", page)


def _nursing_card_html(h: dict) -> str:
    dialysis = '<span class="tag" style="background:#EDE9FE;color:#6D28D9;">💉 투석가능</span>' if h.get("dialysis") else ""
    grade    = f'<span class="tag tag-grade">🏅 간호 {esc(h["nursing_grade"])}</span>' if h.get("nursing_grade") else ""
    bed      = f'<span class="tag" style="background:#F0FDFA;color:#0F766E;">🛏️ {h["bed_cnt"]}병상</span>' if h.get("bed_cnt") else ""
    depts    = "".join(f'<span class="tag tag-dept">{esc(d)}</span>' for d in (h.get("dgsbj_list") or [])[:3])
    return f"""<div class="facility-card">
  <div class="facility-card-body">
    <div class="facility-name">{esc(h.get("name",""))}</div>
    <div class="facility-meta"><span>📍 {esc(h.get("addr",""))}</span><span>👨‍⚕️ 의사 {h.get("dr_cnt",0)}명</span></div>
    <div class="facility-tags">{dialysis}{grade}{bed}{depts}</div>
  </div>
  <div class="facility-card-right">
    <span class="status-badge status-open">요양병원</span>
    {f'<a href="tel:{esc(h["tel"])}" class="btn-call">📞 {esc(h["tel"])}</a>' if h.get("tel") else ""}
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
    cards = "".join(_nursing_card_html(h) for h in hospitals[:100])

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
<script>
const ALL_D={json_embed(hospitals)};
function filterSido(sido){{
  document.querySelectorAll('#sidoFilter .tab-btn').forEach(b=>b.classList.toggle('active',b.textContent===(sido||'전체')));
  const f=sido?ALL_D.filter(h=>h.sido_nm===sido):ALL_D;
  document.getElementById('resultCount').textContent=f.length;
  document.getElementById('dialysisList').innerHTML=f.slice(0,100).map(h=>{{
    const grade=h.nursing_grade?`<span class="tag tag-grade">🏅 간호 ${{h.nursing_grade}}</span>`:'';
    const bed=h.bed_cnt?`<span class="tag" style="background:#F0FDFA;color:#0F766E;">🛏️ ${{h.bed_cnt}}병상</span>`:'';
    const mc=h.dialysis_machine_cnt?`<span class="tag" style="background:#EDE9FE;color:#6D28D9;">💉 인공신장기 ${{h.dialysis_machine_cnt}}대</span>`:'<span class="tag" style="background:#EDE9FE;color:#6D28D9;">💉 투석가능</span>';
    return `<div class="facility-card"><div class="facility-card-body"><div class="facility-name">${{h.name}}</div><div class="facility-meta"><span>📍 ${{h.sido_nm}} ${{h.sggu_nm}}</span><span>📞 ${{h.tel||''}}</span></div><div class="facility-tags">${{mc}}${{grade}}${{bed}}</div></div><div class="facility-card-right"><span class="status-badge status-open">요양병원</span>${{h.tel?`<a href="tel:${{h.tel}}" class="btn-call">📞 ${{h.tel}}</a>`:''}}</div></div>`;
  }}).join('');
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
    grade1_cards = "".join(_nursing_card_html(h) for h in grade1[:50])

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
{footer_html(root)}"""

    save_html(DOCS_DIR / "요양병원" / "간호등급.html", page)


# ── 4. sitemap.xml ─────────────────────────────────────────

def generate_sitemap(pages: list):
    print("[4/4] sitemap.xml 생성")
    urls = "\n".join(
        f"  <url><loc>{SITE_URL}/{p}</loc><changefreq>weekly</changefreq><priority>0.8</priority></url>"
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

    print(f"  병원 {len(hospitals)}개 / 약국 {len(pharmacies)}개 / 요양병원 {len(nursing)}개 로드")

    generate_region_pages(hospitals, pharmacies)
    generate_specialty_pages(hospitals)
    if nursing:
        generate_nursing_pages(nursing)
    else:
        print("[3/4] 요양병원 데이터 없음 — 건너뜀")

    # sitemap용 URL 목록 수집
    pages = []
    for f in DOCS_DIR.rglob("*.html"):
        rel = f.relative_to(DOCS_DIR).as_posix()
        if rel not in ("index.html", "404.html"):
            pages.append(rel)
    generate_sitemap(pages)

    print("\n[완료] 페이지 생성 완료")


if __name__ == "__main__":
    main()
