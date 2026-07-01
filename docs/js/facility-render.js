/**
 * hosppass 공용 시설 카드 렌더링 로직
 * 지역별 페이지(generate_pages.py 생성)와 병원/약국/응급실 페이지가 동일한 카드 UI를 쓰도록 공유.
 */
const DAY_KEYS = ['일', '월', '화', '수', '목', '금', '토'];

function openMapPopup(url) {
  const w = 480, h = 640;
  const left = (window.screen.width - w) / 2, top = (window.screen.height - h) / 2;
  window.open(url, 'hosppassMap', `width=${w},height=${h},left=${left},top=${top},menubar=no,toolbar=no,location=no,status=no,scrollbars=yes,resizable=yes`);
}

function haversine(lat1, lon1, lat2, lon2) {
  const R = 6371000, toRad = d => d * Math.PI / 180;
  const dLat = toRad(lat2 - lat1), dLon = toRad(lon2 - lon1);
  const a = Math.sin(dLat / 2) ** 2 + Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function fmtDist(m) {
  if (m == null) return '';
  return m < 1000 ? `${Math.round(m)}m` : `${(m / 1000).toFixed(1)}km`;
}

function hasDept(item, d) {
  if (item._type && item._type !== 'hosp') return false;
  const list = item.departments || [];
  if (d === '정신건강의학과') return list.some(x => /정신/.test(x.name || ''));
  return list.some(x => (x.name || '').includes(d));
}

function isNightCareNow(item) {
  if (item._type && item._type !== 'hosp') return false;
  if (item.er_night) return true;
  const h = item.hours || {};
  const today = DAY_KEYS[new Date().getDay()];
  const d = h[today];
  if (!d || !d.start || !d.end) return false;
  const now = new Date(), curHM = now.getHours() * 100 + now.getMinutes();
  const sN = parseInt(d.start.replace(':', ''), 10), eN = parseInt(d.end.replace(':', ''), 10);
  if (isNaN(sN) || isNaN(eN)) return false;
  const isLate = eN >= 2100 || eN < sN;
  if (!isLate) return false;
  return eN < sN ? (curHM >= sN || curHM <= eN) : (curHM >= sN && curHM <= eN);
}

function isOpenNow(item) {
  if (item._type && item._type !== 'hosp') return null;
  const h = item.hours || {};
  const today = DAY_KEYS[new Date().getDay()];
  const d = h[today];
  if (!d || !d.start || !d.end) return null;
  const now = new Date(), curHM = now.getHours() * 100 + now.getMinutes();
  const sN = parseInt(d.start.replace(':', ''), 10), eN = parseInt(d.end.replace(':', ''), 10);
  if (isNaN(sN) || isNaN(eN)) return null;
  return eN < sN ? (curHM >= sN || curHM <= eN) : (curHM >= sN && curHM <= eN);
}

function hoursSummary(item) {
  const h = item.hours;
  if (!h || !Object.keys(h).length) return '';
  const order = ['월', '화', '수', '목', '금', '토', '일'];
  return order.filter(k => h[k]).map(k => `${k} ${h[k].start}~${h[k].end}`).join(' · ');
}

/**
 * item: 병원/약국 데이터 객체 (_type: 'hosp'|'pharm', distMeters?: 거리(m) 선택)
 * mapRoot: 현재 페이지 기준 hosppass 루트까지의 상대경로 (예: '', '../../')
 */
function renderFacilityCard(item, mapRoot) {
  mapRoot = mapRoot || '';
  let scls = 'status-closed', stxt = '정보없음';
  if (!item._type || item._type === 'hosp') {
    const night = isNightCareNow(item), open = isOpenNow(item);
    if (night) { scls = 'status-night'; stxt = '야간진료중'; }
    else if (open === true) { scls = 'status-open'; stxt = '운영중'; }
    else if (open === false) { scls = 'status-closed'; stxt = '운영종료'; }
    else { scls = 'status-closed'; stxt = '정보없음'; }
  } else {
    scls = 'status-open'; stxt = '약국';
  }
  const depts = (item._type === 'pharm')
    ? '<span class="tag tag-dept">약국</span>'
    : (item.departments || []).slice(0, 4).map(d => `<span class="tag tag-dept">${d.name}${d.specialist_cnt ? `(전문의${d.specialist_cnt})` : ''}</span>`).join('');
  const erTag = item.er_night ? '<span class="tag tag-emrg">🚨 야간응급</span>' : (item.er_day ? '<span class="tag tag-emrg">🚨 주간응급</span>' : '');
  const nursingTag = (item.nursing || []).length ? `<span class="tag tag-grade">🏅 간호${item.nursing[0].grade}등급</span>` : '';
  const spclTags = (item.specialized_fields || []).slice(0, 2).map(s => `<span class="tag tag-grade">🏆 ${s}전문병원</span>`).join('');
  const specialTags = (item.special_treatments || []).slice(0, 2).map(s => `<span class="tag tag-dept">${s}</span>`).join('');
  const addr = item.emd_nm ? `${item.emd_nm} · ${(item.addr || '').replace(/^[가-힣]+시\s*[가-힣]+구\s*/, '')}` : (item.addr || '');
  const dr = item.dr_cnt ? `<span>👨‍⚕️ 의사 ${item.dr_cnt}명</span>` : '';
  const equip = (item.equipment || []).length ? `<span>🩻 장비 ${item.equipment.length}종</span>` : '';
  const transit = (item.transit && item.transit[0]) ? `<span>🚇 ${item.transit[0].stop || ''} ${item.transit[0].distance || ''}</span>` : '';
  const parking = item.parking_available ? `<span>🅿️ 주차 ${item.parking_count || ''}대${item.parking_fee ? '(유료)' : '(무료)'}</span>` : '';
  const distTag = item.distMeters != null ? `<span>🚶 ${fmtDist(item.distMeters)}</span>` : '';
  const hSum = hoursSummary(item);
  const hoursRow = hSum
    ? `<div style="margin-top:7px;font-size:.82rem;color:var(--text-secondary);">🕐 ${hSum} <span style="margin-left:6px;color:var(--warning);font-size:.76rem;">· 방문 전 전화 확인 권장</span></div>`
    : (item._type === 'pharm' ? '' : `<div style="margin-top:7px;font-size:.78rem;color:var(--text-light);">🕐 진료시간 미제공 — 전화로 확인해주세요</div>`);
  const extraRow = (equip || transit || parking || distTag) ? `<div style="margin-top:5px;font-size:.8rem;color:var(--text-light);display:flex;gap:10px;flex-wrap:wrap;">${dr}${distTag}${equip}${transit}${parking}</div>` : (dr ? `<div style="margin-top:5px;font-size:.8rem;color:var(--text-light);">${dr}</div>` : '');
  const urlBtn = item.url ? `<a href="${item.url}" target="_blank" rel="noopener" class="btn-call">🌐 홈페이지</a>` : '';
  const mapBtn = (item.x && item.y) ? `<a href="${mapRoot}map.html?x=${item.x}&y=${item.y}&name=${encodeURIComponent(item.name)}" onclick="openMapPopup(this.href);return false;" rel="noopener" class="btn-call">🗺️ 지도보기</a>` : '';
  return `<div class="facility-card"><div class="facility-card-body"><div class="facility-name">${item.name}</div><div class="facility-meta"><span>🏥 ${item.cl_nm || (item._type === 'pharm' ? '약국' : '')}</span><span>📍 ${addr}</span></div><div class="facility-tags">${depts}${erTag}${nursingTag}${spclTags}${specialTags}</div>${extraRow}${hoursRow}</div><div class="facility-card-right"><span class="status-badge ${scls}">${stxt}</span>${item.tel ? `<a href="tel:${item.tel}" class="btn-call">📞 ${item.tel}</a>` : ''}${mapBtn}${urlBtn}</div></div>`;
}

/**
 * 리스트가 9개를 넘으면 8번째 카드 뒤에 광고 배너 삽입.
 * items: 원본 배열, cardFn: item -> 카드 HTML 문자열
 */
function renderCardsWithAd(items, cardFn) {
  let out = '';
  items.forEach((item, i) => {
    out += cardFn(item);
    if (i === 7 && items.length > 9) out += INLINE_AD_HTML;
  });
  return out;
}

const INLINE_AD_HTML = '<div class="ad-banner ad-inline"><ins class="adsbygoogle" style="display:block" data-ad-client="ca-pub-6464921081676309" data-ad-slot="7080296704" data-ad-format="auto" data-full-width-responsive="true"></ins></div>';

/**
 * innerHTML로 삽입된 .adsbygoogle 엘리먼트는 <script>가 실행되지 않으므로
 * 카드 리스트를 렌더링한 직후 이 함수를 호출해 광고를 활성화한다.
 */
function initInlineAds(container) {
  (container || document).querySelectorAll('.ad-inline .adsbygoogle:not([data-adsbygoogle-status])').forEach(() => {
    try { (window.adsbygoogle = window.adsbygoogle || []).push({}); } catch (e) {}
  });
}
