#!/usr/bin/env python3
"""Build the redesigned 지휘관 tab with mercenary info + level-up XP table."""

import json, re

# ── MERCENARY DATA ──
MERC_DATA = [
    # 평범함 등급
    {"name":"폴드런","grade":"평범함","str":57,"int":32,"luck":34,"charm":32,"gender":"남성",
     "phys":[0.58,1.15],"magic":[0.32,0.65],"chaos":[0.34,0.69],"click":[0.32,0.65],
     "skill":"크리티컬 배수 + [뿔 플레이트] 용병 수 x0.25"},
    {"name":"풀레","grade":"평범함","str":47,"int":17,"luck":46,"charm":28,"gender":"남성",
     "phys":[0.47,0.95],"magic":[0.17,0.34],"chaos":[0.46,0.93],"click":[0.28,0.57],
     "skill":"[새] 용병 최종댐 + 용병 수 x0.8%"},
    {"name":"언서튼","grade":"평범함","str":38,"int":26,"luck":70,"charm":20,"gender":"불확실",
     "phys":[0.38,0.77],"magic":[0.26,0.53],"chaos":[0.71,1.41],"click":[0.2,0.4],
     "skill":"[언데드] 용병 최종댐 + 용병 수 x0.5%"},
    {"name":"브라이언 킴","grade":"평범함","str":57,"int":29,"luck":43,"charm":25,"gender":"남성",
     "phys":[0.58,1.15],"magic":[0.29,0.59],"chaos":[0.43,0.87],"click":[0.25,0.51],
     "skill":"[인간] 용병 최종댐 + 용병 수 x0.5%"},
    {"name":"아유해피","grade":"평범함","str":36,"int":45,"luck":50,"charm":22,"gender":"남성",
     "phys":[0.36,0.73],"magic":[0.45,0.91],"chaos":[0.51,1.01],"click":[0.22,0.44],
     "skill":"골드 획득량 + [미들랜드] 용병 수 x5%"},
    {"name":"발리언트","grade":"평범함","str":63,"int":36,"luck":30,"charm":23,"gender":"남성",
     "phys":[0.64,1.27],"magic":[0.36,0.73],"chaos":[0.3,0.61],"click":[0.23,0.46],
     "skill":"[무신론자] 용병 최종댐 + 용병 수 x1%"},
    {"name":"에바","grade":"평범함","str":25,"int":37,"luck":44,"charm":50,"gender":"여성",
     "phys":[0.25,0.51],"magic":[0.37,0.75],"chaos":[0.44,0.89],"click":[0.51,1.01],
     "skill":"[여성] 용병 최종댐 + 용병 수 x0.3%"},
    {"name":"쿠미스","grade":"평범함","str":28,"int":37,"luck":34,"charm":56,"gender":"남성",
     "phys":[0.28,0.57],"magic":[0.37,0.75],"chaos":[0.34,0.69],"click":[0.57,1.13],
     "skill":"[슬라임] 용병 최종댐 + 용병 수 x1.5%"},
    {"name":"히데요시","grade":"평범함","str":38,"int":45,"luck":47,"charm":17,"gender":"남성",
     "phys":[0.38,0.77],"magic":[0.45,0.91],"chaos":[0.47,0.95],"click":[0.17,0.34],
     "skill":"골드 저장량 + [남성] 용병 수 x7%"},
    {"name":"아반도나","grade":"평범함","str":30,"int":73,"luck":14,"charm":32,"gender":"여성",
     "phys":[0.3,0.61],"magic":[0.74,1.47],"chaos":[0.14,0.28],"click":[0.32,0.65],
     "skill":"[델로어 마법학교] 용병 최종댐 + 용병 수 x0.7%"},
    {"name":"패니키","grade":"평범함","str":37,"int":30,"luck":28,"charm":27,"gender":"불확실",
     "phys":None,"magic":None,"chaos":None,"click":None,
     "skill":"공포 극복 확률 +1.5%"},
    {"name":"도므릭스","grade":"평범함","str":35,"int":36,"luck":22,"charm":33,"gender":"남성",
     "phys":None,"magic":None,"chaos":None,"click":None,
     "skill":"아티팩트 드랍확률 +16%"},
    {"name":"바이티","grade":"평범함","str":24,"int":25,"luck":20,"charm":18,"gender":"불확실",
     "phys":None,"magic":None,"chaos":None,"click":None,
     "skill":"공격 무효화 관통 +2%"},

    # 훌륭함 등급
    {"name":"언더더씨","grade":"훌륭함","str":34,"int":29,"luck":44,"charm":33,"gender":"남성",
     "phys":[0.34,0.69],"magic":[0.29,0.59],"chaos":[0.3,0.89],"click":[0.33,0.67],
     "skill":"루비 드랍 확률 +25%"},
    {"name":"사오 일나런 홀트","grade":"훌륭함","str":36,"int":28,"luck":60,"charm":20,"gender":"남성",
     "phys":[0.36,0.73],"magic":[0.28,0.57],"chaos":[0.61,1.21],"click":[0.2,0.4],
     "skill":"토파즈 드랍 확률 +25%"},
    {"name":"디나 다이크너","grade":"훌륭함","str":33,"int":28,"luck":40,"charm":55,"gender":"여성",
     "phys":[0.33,0.67],"magic":[0.28,0.57],"chaos":[0.4,0.81],"click":[0.56,1.11],
     "skill":"사파이어 드랍 확률 +25%"},
    {"name":"프록스먼","grade":"훌륭함","str":29,"int":48,"luck":34,"charm":40,"gender":"남성",
     "phys":[0.29,0.59],"magic":[0.48,0.97],"chaos":[0.34,0.69],"click":[0.4,0.81],
     "skill":"에메랄드 드랍 확률 +25%"},
    {"name":"아델레이드","grade":"훌륭함","str":30,"int":41,"luck":35,"charm":44,"gender":"여성",
     "phys":[0.3,0.61],"magic":[0.41,0.83],"chaos":[0.35,0.71],"click":[0.44,0.89],
     "skill":"자수정 드랍 확률 +25%"},
    {"name":"그루터기","grade":"훌륭함","str":56,"int":48,"luck":32,"charm":37,"gender":"남성",
     "phys":[0.57,1.13],"magic":[0.48,0.97],"chaos":[0.32,0.65],"click":[0.37,0.75],
     "skill":"[식물] 용병 최종댐 + 용병 수 x0.7%"},
    {"name":"치즈코이","grade":"훌륭함","str":61,"int":20,"luck":60,"charm":29,"gender":"남성",
     "phys":[0.62,1.23],"magic":[0.21,0.42],"chaos":[0.61,1.21],"click":[0.29,0.59],
     "skill":"[개] 용병 최종댐 + 용병 수 x1%"},
    {"name":"예거","grade":"훌륭함","str":18,"int":12,"luck":16,"charm":20,"gender":"남성",
     "phys":[0.36,None],"magic":[0.24,None],"chaos":[0.32,None],"click":[0.4,None],
     "skill":"회피 확률 감소 + [정규군] 용병 수 x0.6%"},
    {"name":"알버트","grade":"훌륭함","str":14,"int":13,"luck":16,"charm":17,"gender":"여성",
     "phys":[0.28,None],"magic":[0.26,None],"chaos":[0.32,None],"click":[0.34,None],
     "skill":"클릭 크리티컬 확률 + [인간] 용병 수 x0.12%"},
    {"name":"말론","grade":"훌륭함","str":31,"int":31,"luck":21,"charm":31,"gender":"불확실",
     "phys":None,"magic":None,"chaos":None,"click":None,
     "skill":"[정령] 용병 행운 배수 + 용병 수 x0.05"},
    {"name":"알리제","grade":"훌륭함","str":56,"int":51,"luck":38,"charm":55,"gender":"여성",
     "phys":[None,1.13],"magic":[None,1.03],"chaos":[None,0.77],"click":[None,1.11],
     "skill":"흡수 확률 감소 +1.5%"},

    # 영웅 등급
    {"name":"우바루","grade":"영웅","str":34,"int":17,"luck":20,"charm":18,"gender":"남성",
     "phys":[0.68,2.36],"magic":[0.34,1.7],"chaos":[0.4,1.65],"click":[0.36,1.91],
     "skill":"[오크] 종족 강타배수 + 오크 용병 수 x0.05"},
    {"name":"마그나","grade":"영웅","str":36,"int":11,"luck":24,"charm":7,"gender":"불확실",
     "phys":[0.72,1.88],"magic":[0.22,0.77],"chaos":[0.48,1.03],"click":[0.14,0.67],
     "skill":"[골렘] 종족 강타배수 + [골렘] 용병 수 x0.06"},
    {"name":"미케니코스","grade":"영웅","str":25,"int":25,"luck":25,"charm":25,"gender":"불확실",
     "phys":[0.5,2.15],"magic":[0.5,2.17],"chaos":[0.5,2.03],"click":[0.5,1.87],
     "skill":"[기계] 종족 강타배수 + [기계] 용병 수 x0.05"},
    {"name":"파우다","grade":"영웅","str":16,"int":14,"luck":37,"charm":17,"gender":"여성",
     "phys":[0.32,None],"magic":[0.28,None],"chaos":[0.74,None],"click":[0.34,None],
     "skill":"카오스 취약성 +1.3%"},
    {"name":"벨라","grade":"영웅","str":34,"int":18,"luck":13,"charm":22,"gender":"여성",
     "phys":[0.68,None],"magic":[0.36,None],"chaos":[0.26,None],"click":[0.44,None],
     "skill":"물리 저항력 감소 +3%"},
    {"name":"베드로","grade":"영웅","str":27,"int":26,"luck":21,"charm":26,"gender":"남성",
     "phys":[0.54,None],"magic":[0.52,None],"chaos":[0.42,None],"click":[0.52,None],
     "skill":"[뿔레교] 종교 행운배수 + [뿔레교] 용병 수 x0.03"},
    {"name":"릴리안","grade":"영웅","str":13,"int":35,"luck":16,"charm":21,"gender":"여성",
     "phys":[0.26,None],"magic":[0.7,None],"chaos":[0.32,None],"click":[0.42,None],
     "skill":"마법 저항력 감소 +4%"},
    {"name":"제노시스","grade":"영웅","str":30,"int":30,"luck":30,"charm":9,"gender":"남성",
     "phys":[0.6,None],"magic":[0.6,None],"chaos":[0.6,None],"click":[0.18,None],
     "skill":"[혐오체] 종족 치명타 딜레이 감소 + [혐오체] 용병 수 x1.2%"},
    {"name":"다케다","grade":"영웅","str":23,"int":24,"luck":22,"charm":28,"gender":"남성",
     "phys":[0.46,2.19],"magic":[0.48,2.18],"chaos":[0.44,2.17],"click":[0.56,2.05],
     "skill":"[쿠로 마을] 지역 행운배수 + [쿠로 마을] 용병 수 x0.06"},
    {"name":"골드루그","grade":"영웅","str":38,"int":41,"luck":21,"charm":33,"gender":"남성",
     "phys":[None,2.88],"magic":[None,1.87],"chaos":[None,1.84],"click":[None,1.99],
     "skill":"[악마] 종족 행운 배수 + [악마] 용병 수 x0.05"},
]

# ── LEVEL-UP XP DATA ──
LEVELUP_DATA = [
    100,160,230,310,400,500,610,730,860,1000,
    1150,1310,1480,1660,1850,2050,2260,2480,2710,2950,
    3200,3460,3730,4010,4300,4600,4910,5230,5560,5900,
    6250,6610,6980,7360,7750,8150,8560,8980,9410,9850,
    10300,10760,11230,11710,12200,12700,13210,13730,14260,14800,
    15350,15910,16480,17060,17650,18250,18860,19480,20110,20750,
    21400,22060,22730,23410,24100,24800,25510,26230,26960,27700,
    28450,29210,29980,30760,31550,32350,33160,33980,34810,35650,
    36500,37360,38230,39110,40000,40900,41810,42730,43660,44600,
    45550,46510,47480,48460,49450,50450,51460,52480,53510,54550,
]

# ── BUILD NEW HTML TAB ──
def build_tab_html():
    return '''<div id="tab-지휘관" class="tab-content">
  <div class="cmd-pills">
    <button class="cmd-pill active" data-cmd="merc">용병 정보</button>
    <button class="cmd-pill" data-cmd="levelup">레벨업 경험치</button>
  </div>
  <div id="cmd-content"></div>
</div>'''

# ── BUILD CSS ──
def build_css():
    return '''
/* ── COMMANDER TAB ── */
.cmd-pills{display:flex;gap:6px;margin-bottom:14px;flex-wrap:wrap}
.cmd-pill{padding:7px 16px;border-radius:20px;border:1px solid var(--border);background:var(--bg);color:var(--text-muted);font-size:.78rem;cursor:pointer;transition:all .2s}
.cmd-pill.active{background:#6366f1;color:#fff;border-color:#6366f1}
.cmd-pill:hover:not(.active){background:var(--bg-hover)}

.cmd-grade-btns{display:flex;gap:5px;margin-bottom:10px;flex-wrap:wrap}
.cmd-grade-btn{padding:5px 12px;border-radius:14px;border:1px solid var(--border);background:var(--bg);color:var(--text-muted);font-size:.72rem;cursor:pointer;transition:all .2s}
.cmd-grade-btn.active{color:#fff}
.cmd-grade-btn[data-g="전체"].active{background:#6366f1;border-color:#6366f1}
.cmd-grade-btn[data-g="평범함"].active{background:#71717a;border-color:#71717a}
.cmd-grade-btn[data-g="훌륭함"].active{background:#0ea5e9;border-color:#0ea5e9}
.cmd-grade-btn[data-g="영웅"].active{background:#f59e0b;border-color:#f59e0b}

.cmd-search-row{display:flex;align-items:center;gap:8px;margin-bottom:12px;flex-wrap:wrap}
.cmd-search-row .search-input{flex:1;min-width:180px}
.cmd-search-row .result-count{font-size:.75rem;color:var(--text-muted);white-space:nowrap}

.merc-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:10px}
@media(max-width:400px){.merc-grid{grid-template-columns:1fr}}

.merc-card{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:12px;transition:transform .15s,box-shadow .15s}
.merc-card:hover{transform:translateY(-2px);box-shadow:0 4px 12px rgba(0,0,0,.15)}

.merc-hdr{display:flex;align-items:center;gap:8px;margin-bottom:8px}
.merc-name{font-weight:700;font-size:.88rem;color:var(--text)}
.merc-badge{font-size:.65rem;padding:2px 8px;border-radius:10px;color:#fff;font-weight:600}
.merc-badge.평범함{background:#71717a}
.merc-badge.훌륭함{background:#0ea5e9}
.merc-badge.영웅{background:#f59e0b}
.merc-gender{font-size:.7rem;color:var(--text-muted);margin-left:auto}

.merc-stats{display:grid;grid-template-columns:repeat(4,1fr);gap:4px;margin-bottom:8px}
.merc-stat{text-align:center;background:var(--bg);border-radius:6px;padding:4px 2px}
.merc-stat-val{font-weight:700;font-size:.82rem;color:var(--text)}
.merc-stat-label{font-size:.6rem;color:var(--text-muted)}

.merc-dmg{width:100%;border-collapse:collapse;margin-bottom:8px;font-size:.75rem}
.merc-dmg th{padding:3px 6px;text-align:center;color:var(--text-muted);font-weight:600;font-size:.65rem;border-bottom:1px solid var(--border)}
.merc-dmg td{padding:3px 6px;text-align:center;color:var(--text-dim)}
.merc-dmg td:first-child{text-align:left;font-weight:600;color:var(--text-muted);font-size:.7rem}
.merc-dmg .phys-col{color:#ef4444}
.merc-dmg .magic-col{color:#8b5cf6}
.merc-dmg .chaos-col{color:#10b981}
.merc-dmg .click-col{color:#f59e0b}
.merc-dmg .na{color:var(--text-muted);opacity:.5;font-style:italic}

.merc-skill{background:var(--bg);border-radius:6px;padding:6px 8px;font-size:.73rem;color:var(--accent);line-height:1.4}

/* level-up xp table */
.lvl-table-wrap{overflow-x:auto;-webkit-overflow-scrolling:touch}
.lvl-table{width:100%;border-collapse:collapse;font-size:.78rem}
.lvl-table th{padding:8px 10px;background:var(--bg);color:var(--text-muted);font-weight:600;font-size:.7rem;border-bottom:2px solid var(--border);position:sticky;top:0;text-align:center}
.lvl-table td{padding:6px 10px;border-bottom:1px solid var(--border);text-align:center}
.lvl-table td:nth-child(odd){color:var(--text-muted);font-weight:600;font-size:.72rem;background:rgba(99,102,241,.04)}
.lvl-table td:nth-child(even){color:var(--text)}
.lvl-table tr:hover td{background:rgba(99,102,241,.06)}
.lvl-summary{display:flex;gap:12px;margin-top:12px;flex-wrap:wrap;justify-content:center}
.lvl-summary-box{background:var(--card);border:1px solid var(--border);border-radius:8px;padding:8px 14px;text-align:center}
.lvl-summary-box .val{font-weight:700;font-size:1rem;color:var(--accent)}
.lvl-summary-box .lbl{font-size:.65rem;color:var(--text-muted)}
'''

# ── BUILD JS ──
def build_js(merc_json, levelup_json):
    return f'''
// ════════════════════════════════════════
// ── COMMANDER TAB (redesigned) ──
// ════════════════════════════════════════
const MERC_INFO={merc_json};
const CMD_LEVELUP={levelup_json};
let cmdRendered=false,cmdMercSearch='',cmdMercGrade='전체';

function fmtDmg(arr){{
  if(!arr) return '<span class="na">제보</span>';
  const v1=arr[0]!==null?arr[0]:'?';
  const v2=arr[1]!==null?arr[1]:'?';
  if(v2==='?'&&v1!=='?') return String(v1);
  if(v1==='?'&&v2!=='?') return '? / '+v2;
  return v1+' / '+v2;
}}

function filterMercs(){{
  return MERC_INFO.filter(m=>{{
    if(cmdMercGrade!=='전체'&&m.grade!==cmdMercGrade) return false;
    if(cmdMercSearch){{
      const q=cmdMercSearch.toLowerCase();
      if(!m.name.toLowerCase().includes(q)&&!m.skill.toLowerCase().includes(q)) return false;
    }}
    return true;
  }});
}}

function renderMercTab(){{
  const wrap=document.getElementById('cmd-content');
  const filtered=filterMercs();
  const countEl=document.getElementById('merc-count');
  if(countEl) countEl.textContent=filtered.length+'명';

  const listEl=document.getElementById('merc-list');
  if(!listEl) return;

  if(!filtered.length){{listEl.innerHTML='<div class="no-results">검색 결과가 없습니다.</div>';return;}}

  listEl.innerHTML=filtered.map(m=>{{
    const genderIcon=m.gender==='남성'?'♂':m.gender==='여성'?'♀':'⚪';
    const dmgRows=[
      ['물리','phys-col',m.phys],
      ['마법','magic-col',m.magic],
      ['카오스','chaos-col',m.chaos],
      ['클릭','click-col',m.click]
    ].map(([label,cls,arr])=>{{
      const txt=fmtDmg(arr);
      if(!arr) return `<tr><td class="${{cls}}">${{label}}</td><td colspan="2" class="na">제보</td></tr>`;
      const v1=arr[0]!==null?arr[0]:'?';
      const v2=arr[1]!==null?arr[1]:null;
      if(v2===null) return `<tr><td class="${{cls}}">${{label}}</td><td>${{v1}}</td><td class="na">-</td></tr>`;
      return `<tr><td class="${{cls}}">${{label}}</td><td>${{v1==='?'?'<span class=na>?</span>':v1}}</td><td>${{v2}}</td></tr>`;
    }}).join('');

    return `<div class="merc-card">
      <div class="merc-hdr">
        <span class="merc-name">${{esc(m.name)}}</span>
        <span class="merc-badge ${{m.grade}}">${{m.grade}}</span>
        <span class="merc-gender">${{genderIcon}} ${{m.gender}}</span>
      </div>
      <div class="merc-stats">
        <div class="merc-stat"><div class="merc-stat-val">${{m.str}}</div><div class="merc-stat-label">힘</div></div>
        <div class="merc-stat"><div class="merc-stat-val">${{m.int}}</div><div class="merc-stat-label">지능</div></div>
        <div class="merc-stat"><div class="merc-stat-val">${{m.luck}}</div><div class="merc-stat-label">운</div></div>
        <div class="merc-stat"><div class="merc-stat-val">${{m.charm}}</div><div class="merc-stat-label">매력</div></div>
      </div>
      <table class="merc-dmg">
        <tr><th></th><th>1Lv</th><th>100Lv</th></tr>
        ${{dmgRows}}
      </table>
      <div class="merc-skill">${{esc(m.skill)}}</div>
    </div>`;
  }}).join('');
}}

function renderLevelupTab(){{
  const wrap=document.getElementById('cmd-content');
  // Build 5-column layout: lv|xp|lv|xp|lv|xp|lv|xp|lv|xp
  const rows=[];
  const totalXP=CMD_LEVELUP.reduce((s,v)=>s+v,0);
  for(let r=0;r<20;r++){{
    let cells='';
    for(let c=0;c<5;c++){{
      const lv=r+c*20;
      if(lv<CMD_LEVELUP.length){{
        cells+=`<td>${{lv}}</td><td>${{CMD_LEVELUP[lv].toLocaleString()}}</td>`;
      }} else if(lv===100){{
        cells+=`<td>100</td><td style="color:var(--accent);font-weight:700">MAX</td>`;
      }} else {{
        cells+=`<td></td><td></td>`;
      }}
    }}
    rows.push(`<tr>${{cells}}</tr>`);
  }}

  wrap.innerHTML=`
    <div class="lvl-table-wrap">
      <table class="lvl-table">
        <tr><th>Lv</th><th>필요경험치</th><th>Lv</th><th>필요경험치</th><th>Lv</th><th>필요경험치</th><th>Lv</th><th>필요경험치</th><th>Lv</th><th>필요경험치</th></tr>
        ${{rows.join('')}}
      </table>
    </div>
    <div class="lvl-summary">
      <div class="lvl-summary-box"><div class="val">${{totalXP.toLocaleString()}}</div><div class="lbl">0→99 총 필요경험치</div></div>
      <div class="lvl-summary-box"><div class="val">100</div><div class="lbl">최대 레벨</div></div>
    </div>`;
}}

function initCMDTab(){{
  const wrap=document.getElementById('cmd-content');

  // Show merc tab initially
  wrap.innerHTML=`
    <div class="cmd-grade-btns" id="merc-grade-btns">
      <button class="cmd-grade-btn active" data-g="전체">전체</button>
      <button class="cmd-grade-btn" data-g="평범함">평범함</button>
      <button class="cmd-grade-btn" data-g="훌륭함">훌륭함</button>
      <button class="cmd-grade-btn" data-g="영웅">영웅</button>
    </div>
    <div class="cmd-search-row">
      <input type="text" class="search-input" id="merc-search" placeholder="용병 이름/스킬 검색...">
      <span class="result-count" id="merc-count"></span>
    </div>
    <div class="merc-grid" id="merc-list"></div>`;

  renderMercTab();

  // Grade filter
  document.querySelectorAll('#merc-grade-btns .cmd-grade-btn').forEach(btn=>{{
    btn.addEventListener('click',()=>{{
      document.querySelectorAll('#merc-grade-btns .cmd-grade-btn').forEach(b=>b.classList.remove('active'));
      btn.classList.add('active');
      cmdMercGrade=btn.dataset.g;
      renderMercTab();
    }});
  }});

  // Search
  const inp=document.getElementById('merc-search');
  if(inp){{let t;inp.addEventListener('input',()=>{{clearTimeout(t);t=setTimeout(()=>{{cmdMercSearch=inp.value.trim();renderMercTab();}},200);}});}}

  // Sub-tab pill handlers
  let currentCmdPill='merc';
  document.querySelectorAll('.cmd-pill').forEach(pill=>{{
    pill.addEventListener('click',()=>{{
      if(pill.dataset.cmd===currentCmdPill) return;
      document.querySelectorAll('.cmd-pill').forEach(p=>p.classList.remove('active'));
      pill.classList.add('active');
      currentCmdPill=pill.dataset.cmd;
      if(currentCmdPill==='merc'){{
        wrap.innerHTML=`
          <div class="cmd-grade-btns" id="merc-grade-btns">
            <button class="cmd-grade-btn active" data-g="전체">전체</button>
            <button class="cmd-grade-btn" data-g="평범함">평범함</button>
            <button class="cmd-grade-btn" data-g="훌륭함">훌륭함</button>
            <button class="cmd-grade-btn" data-g="영웅">영웅</button>
          </div>
          <div class="cmd-search-row">
            <input type="text" class="search-input" id="merc-search" placeholder="용병 이름/스킬 검색...">
            <span class="result-count" id="merc-count"></span>
          </div>
          <div class="merc-grid" id="merc-list"></div>`;
        cmdMercSearch='';cmdMercGrade='전체';
        renderMercTab();
        document.querySelectorAll('#merc-grade-btns .cmd-grade-btn').forEach(btn=>{{
          btn.addEventListener('click',()=>{{
            document.querySelectorAll('#merc-grade-btns .cmd-grade-btn').forEach(b=>b.classList.remove('active'));
            btn.classList.add('active');
            cmdMercGrade=btn.dataset.g;
            renderMercTab();
          }});
        }});
        const inp2=document.getElementById('merc-search');
        if(inp2){{let t;inp2.addEventListener('input',()=>{{clearTimeout(t);t=setTimeout(()=>{{cmdMercSearch=inp2.value.trim();renderMercTab();}},200);}});}}
      }} else {{
        renderLevelupTab();
      }}
    }});
  }});
}}
'''


def main():
    merc_json = json.dumps(MERC_DATA, ensure_ascii=False)
    levelup_json = json.dumps(LEVELUP_DATA)

    with open('/Users/shin542/Desktop/Code/bbule/web/index.html', 'r') as f:
        html = f.read()

    # 1. Replace tab HTML
    old_tab_start = '<div id="tab-지휘관" class="tab-content">'
    # Find the end of the tab div (before </main> or before next section)
    idx_start = html.find(old_tab_start)
    if idx_start < 0:
        print("ERROR: Could not find tab-지휘관 div")
        return

    # Find the closing </div> that ends the tab content
    # The tab has: <div id="tab-지휘관">...<div>...</div>...</div>
    # We need to find the matching closing </div>
    depth = 0
    i = idx_start
    while i < len(html):
        if html[i:i+4] == '<div':
            depth += 1
        elif html[i:i+6] == '</div>':
            depth -= 1
            if depth == 0:
                idx_end = i + 6
                break
        i += 1

    old_tab = html[idx_start:idx_end]
    new_tab = build_tab_html()
    html = html[:idx_start] + new_tab + html[idx_end:]
    print(f"Replaced tab HTML ({len(old_tab)} → {len(new_tab)} chars)")

    # 2. Remove old CMD_DATA
    cmd_data_start = html.find('const CMD_DATA=')
    if cmd_data_start > 0:
        cmd_data_end = html.find('];', cmd_data_start) + 2
        old_cmd_data = html[cmd_data_start:cmd_data_end]
        html = html[:cmd_data_start] + html[cmd_data_end:]
        print(f"Removed old CMD_DATA ({len(old_cmd_data)} chars)")
    else:
        print("WARNING: CMD_DATA not found")

    # 3. Replace old CMD JS code
    old_js_marker = "// ════════════════════════════════════════\n// ── COMMANDER TAB ──\n// ════════════════════════════════════════"
    idx_js = html.find(old_js_marker)
    if idx_js < 0:
        # try without exact whitespace
        old_js_marker = "// ── COMMANDER TAB ──"
        idx_js = html.find(old_js_marker)
        if idx_js > 0:
            # go back to include the decoration line
            search_back = html.rfind('// ═', max(0, idx_js-80), idx_js)
            if search_back > 0:
                idx_js = search_back

    if idx_js > 0:
        # Find end: the LAZY TAB INIT section
        lazy_marker = "// ── LAZY TAB INIT"
        idx_js_end = html.find(lazy_marker, idx_js)
        if idx_js_end < 0:
            print("ERROR: Could not find LAZY TAB INIT marker")
            return

        old_js = html[idx_js:idx_js_end]
        new_js = build_js(merc_json, levelup_json) + '\n\n'
        html = html[:idx_js] + new_js + html[idx_js_end:]
        print(f"Replaced CMD JS ({len(old_js)} → {len(new_js)} chars)")
    else:
        print("ERROR: Could not find COMMANDER TAB JS marker")
        return

    # 4. Update lazy loader: change renderCMD to initCMDTab
    html = html.replace(
        "if(t==='지휘관'&&!cmdRendered){renderCMD();cmdRendered=true;}",
        "if(t==='지휘관'&&!cmdRendered){initCMDTab();cmdRendered=true;}"
    )
    print("Updated lazy loader")

    # 5. Add CSS (before the first </style> or after existing cmd CSS)
    css = build_css()
    # Find existing cmd-grid CSS or just add before </style>
    old_cmd_css_marker = '.cmd-grid'
    idx_css = html.find(old_cmd_css_marker)
    if idx_css > 0:
        # Find the start of .cmd-grid rule
        rule_start = html.rfind('\n', max(0, idx_css-200), idx_css)
        # Find end of cmd-related CSS block - look for next non-cmd rule
        # Just find several closing braces after
        pos = idx_css
        brace_count = 0
        last_close = idx_css
        while pos < len(html) and pos < idx_css + 3000:
            if html[pos] == '{':
                brace_count += 1
            elif html[pos] == '}':
                brace_count -= 1
                last_close = pos + 1
                # Check if next significant text starts with a non-cmd selector
                rest = html[pos+1:pos+100].strip()
                if rest and not rest.startswith('.cmd') and not rest.startswith('/*') and brace_count <= 0:
                    break
            pos += 1

        # Remove old cmd CSS and replace
        old_css_section = html[rule_start:last_close]
        html = html[:rule_start] + css + html[last_close:]
        print(f"Replaced CMD CSS ({len(old_css_section)} → {len(css)} chars)")
    else:
        # Just add before first </style>
        style_end = html.find('</style>')
        if style_end > 0:
            html = html[:style_end] + css + '\n' + html[style_end:]
            print("Added CSS before </style>")

    with open('/Users/shin542/Desktop/Code/bbule/web/index.html', 'w') as f:
        f.write(html)

    print("\nDone! 지휘관 tab redesigned with mercenary info + level-up XP.")
    print(f"  - {len(MERC_DATA)} mercenaries (평범함:{sum(1 for m in MERC_DATA if m['grade']=='평범함')}, 훌륭함:{sum(1 for m in MERC_DATA if m['grade']=='훌륭함')}, 영웅:{sum(1 for m in MERC_DATA if m['grade']=='영웅')})")
    print(f"  - Level-up XP: 0-99 ({len(LEVELUP_DATA)} levels)")


if __name__ == '__main__':
    main()
