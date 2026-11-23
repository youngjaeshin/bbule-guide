(() => {
  "use strict";
  const root = document.getElementById("monster-guide");
  const routes = {
    regions: "#monsters",
    monsters: "#monster-search",
    attacks: "#monster-attacks",
  };
  let loading = null;
  let requestedView = "regions";

  function updateRoute(view) {
    if (document.getElementById("tab-몬스터").classList.contains("active")) {
      window.GuideNavigation.setHash(routes[view]);
    }
  }

  async function load() {
    root.innerHTML = '<p role="status">몬스터 자료를 불러오고 있습니다.</p>';
    const response = await fetch("data_monsters.json");
    if (!response.ok) throw new Error("몬스터 자료 응답 " + response.status);
    const DATA = await response.json();
    root.innerHTML = /* HTML */ `<div class="heading">
        <h1>몬스터</h1>
        <span class="source">몬스터 자료 v.1890 TEST_6 · 2026년 11월 23일</span>
      </div>
      <nav class="tabs" role="tablist" aria-label="몬스터 정보">
        <button role="tab" data-view="regions" aria-selected="true">
          구간별</button
        ><button role="tab" data-view="monsters" aria-selected="false">
          몬스터 찾기
        </button>
        <button role="tab" data-view="attacks" aria-selected="false">
          공격 설명
        </button>
      </nav>
      <div id="monster-common-tools" class="tools">
        <div class="field">
          <label for="monster-tier">난이도</label
          ><select id="monster-tier"></select>
        </div>
        <div class="field floor-field">
          <label for="monster-floor">실제 층수로 찾기</label>
          <div class="floor-group">
            <input
              id="monster-floor"
              inputmode="numeric"
              placeholder="예 3992"
              aria-describedby="monster-floor-error"
            /><button id="monster-find-floor" class="primary">찾기</button
            ><button id="monster-clear-floor">층수 해제</button>
          </div>
        </div>
        <p id="monster-floor-error" class="error" role="status"></p>
      </div>
      <section id="monster-regions-view" role="tabpanel"></section>
      <section id="monster-monsters-view" role="tabpanel" hidden>
        <details class="search-options" id="monster-monster-filters" open>
          <summary>이름·종류로 좁혀보기</summary>
          <div class="filter-row">
            <div class="field grow">
              <label for="monster-search">몬스터 이름</label
              ><input id="monster-search" placeholder="예 티어도르" />
            </div>
            <div class="field">
              <label for="monster-kind">종류</label
              ><select id="monster-kind">
                <option value="">일반·보스 전체</option>
                <option>일반</option>
                <option>보스</option>
              </select>
            </div>
            <div class="field">
              <label for="monster-sort">정렬</label
              ><select id="monster-sort">
                <option value="stage">출현층 순</option>
                <option value="null">공무 높은 순</option>
                <option value="name">이름순</option>
              </select>
            </div>
            <label class="toggle"
              ><input id="monster-only-highlights" type="checkbox" />특징 몬스터
              25개</label
            ><button id="monster-reset-filters">조건 지우기</button>
          </div>
        </details>
        <p class="note">
          선택한 난이도의 보정이 반영된 랜덤 가산 전 기본값입니다. 몬스터를
          누르면 고유값과 계산 근거를 볼 수 있습니다.
        </p>
        <div id="monster-monster-results"></div>
      </section>

      <section id="monster-attacks-view" role="tabpanel" hidden></section>
      <details class="source-details">
        <summary>분석 기준과 자료</summary>
        <p>
          몬스터 자료는 v.1890 TEST_6의 APK 코드와 원본 데이터를 기준으로
          정리했습니다.
        </p>
        <p>
          일반 387개·보스 109개 원본 항목을 사용합니다. 실제 단말 화면 전수
          대조와 무작위 발생 빈도 측정은 추가 확인 항목입니다.
        </p>
        <a href="data_monsters.json" download>몬스터 자료 받기</a>
      </details>`;
    return initialize(DATA);
  }

  function initialize(DATA) {
    const LABELS = {
      seal: "봉인",
      disable: "무력화",
      reflect: "반사",
      immune: "피해 면제",
      revive: "부활",
      shield: "방어막",
      null: "공격 무효화",
      eva: "회피",
      fear: "공포",
      abs: "흡수",
      weak: "약화",
      slow: "둔화",
    };
    const RES = {
      physical: "물리 저항",
      magical: "마법 저항",
      click: "클릭 저항",
    };
    const state = {
      view: requestedView,
      tier: 0,
      search: "",
      kind: "",
      sort: "stage",
      floor: null,
      highlights: false,
      page: 1,
      boss: false,
      bossAttackSetting: "rules",
    };
    const byKey = new Map(DATA.monsters.map((x) => [x.key, x]));
    const $ = (id) => document.getElementById("monster-" + id);
    const esc = (x) =>
      String(x).replace(
        /[&<>"']/g,
        (c) =>
          ({
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#39;",
          })[c],
      );
    const n = (x) =>
      Number(Number(x).toFixed(6)).toLocaleString("ko-KR", {
        maximumFractionDigits: 6,
      });
    const pct = (x) => n(x) + "%";
    const tier = () => DATA.tiers[state.tier];
    function ranges(values) {
      let groups = [],
        start = values[0],
        previous = start;
      for (const v of values.slice(1)) {
        if (v === previous + 1) {
          previous = v;
          continue;
        }
        groups.push(
          start === previous ? String(start) : start + "~" + previous,
        );
        start = previous = v;
      }
      groups.push(start === previous ? String(start) : start + "~" + previous);
      return groups.join("·");
    }
    function stages(m) {
      return m.positions.map((p) => tier().start + p - 1);
    }
    function attackText(m) {
      if (m.interval > 0)
        return "전체 공격 " + pct(m.all_attack) + "·" + n(m.interval) + "초";
      return m.kind === "보스" || tier().difficulty >= 8
        ? "출현 시 9종 중 선택"
        : "기본 주기 공격 비활성";
    }
    function calculate(m) {
      const t = tier(),
        bonus =
          m.kind === "보스"
            ? m.interval > 0
              ? t.boss_fixed
              : t.boss_zero
            : {};
      const stats = {};
      for (const key of Object.keys(LABELS))
        stats[key] =
          t.statuses[key].base +
          (bonus[key] || 0) +
          (key === "null" ? m.null : 0);
      const resistance = {};
      for (const key of Object.keys(RES))
        resistance[key] = m.resistance[key] + t.resistance[key];
      return { stats, resistance };
    }
    function cell(label, value, sub = "", active = true, id = "") {
      return (
        '<div class="stat"><div class="label">' +
        esc(label) +
        '</div><div class="value"' +
        (id ? ' id="monster-' + id + '"' : "") +
        ">" +
        (active ? pct(value) : "—") +
        "</div>" +
        (sub ? '<div class="sub">' + esc(sub) + "</div>" : "") +
        "</div>"
      );
    }
    function statusGrid(stats, config, idPrefix = "", bossBonus = {}) {
      const inactive = [];
      const cells = [];
      for (const key of Object.keys(LABELS)) {
        const raw = stats[key];
        const cap = config.statuses[key].maximum_count;
        const step = config.statuses[key].step;
        const display = raw;
        if (display === 0 && cap === 0) {
          inactive.push(LABELS[key]);
          continue;
        }
        let sub =
          raw < 0
            ? "원본 " + pct(raw) + "에 가산 후 효과 계산"
            : cap > 0
              ? "랜덤 +" + step + "%p·최대 " + cap + "회"
              : "추가 후보 0회";
        if (bossBonus[key] > 0) {
          sub = "보스 보정 +" + n(bossBonus[key]) + "%p · " + sub;
        }
        cells.push(
          cell(
            LABELS[key],
            display,
            sub,
            true,
            key === "null" && idPrefix ? idPrefix + "null" : "",
          ),
        );
      }
      let html = cells.length
        ? '<div class="stats" style="--columns:' +
          Math.min(4, cells.length) +
          '">' +
          cells.join("") +
          "</div>"
        : '<p class="hint">현재 조건의 기본 디버프와 추가 횟수는 0입니다.</p>';
      if (inactive.length) {
        html +=
          "<details><summary>비활성 항목 " +
          inactive.length +
          '개</summary><p class="hint">' +
          inactive.join("·") +
          "</p></details>";
      }
      return html;
    }
    function resistanceGrid(values, prefix = "") {
      return (
        '<div class="resist-strip">' +
        Object.keys(RES)
          .map((key) =>
            cell(RES[key], values[key], "", true, prefix ? prefix + key : ""),
          )
          .join("") +
        "</div>"
      );
    }
    function showView(view) {
      requestedView = view;
      state.view = view;
      render();
    }
    function render() {
      requestedView = state.view;
      updateRoute(state.view);
      for (const button of root.querySelectorAll("[data-view]"))
        button.setAttribute(
          "aria-selected",
          String(button.dataset.view === state.view),
        );
      for (const view of ["regions", "monsters", "attacks"])
        $(view + "-view").hidden = state.view !== view;
      $("tier").value = String(state.tier);
      $("floor").value = state.floor === null ? "" : state.floor;
      if (state.view === "regions") renderRegions();
      if (state.view === "monsters") renderMonsters();
      if (state.view === "attacks") renderAttacks();
    }
    function renderRegions() {
      const t = tier(),
        max = t.statuses.null.base + 115 + 30;
      const hasBossVariants = Object.keys(LABELS).some(
        (key) => t.boss_zero[key] !== t.boss_fixed[key],
      );
      const bossBonus = state.boss
        ? state.bossAttackSetting === "fixed"
          ? t.boss_fixed
          : t.boss_zero
        : {};
      const priority = [
        "보스:31",
        "일반:299",
        "보스:83",
        "일반:352",
        "보스:104",
      ];
      $("regions-view").innerHTML =
        '<div class="panel"><div class="section-top"><h2>구간 공통 기본값</h2><label class="toggle"><input id="monster-boss-mode" type="checkbox" ' +
        (state.boss ? "checked" : "") +
        ">보스 보정 적용</label></div>" +
        (state.boss && hasBossVariants
          ? '<div class="field" style="margin-bottom:14px"><label for="monster-boss-attack-setting">보스 공격 설정</label><select id="monster-boss-attack-setting"><option value="rules" ' +
            (state.bossAttackSetting === "rules" ? "selected" : "") +
            '>구간 규칙 — 원본 공격 간격 미지정</option><option value="fixed" ' +
            (state.bossAttackSetting === "fixed" ? "selected" : "") +
            ">공격 간격 지정 — 공격 설정에 숫자가 있는 보스</option></select></div>"
          : "") +
        statusGrid(
          Object.fromEntries(
            Object.entries(t.statuses).map(([k, v]) => [
              k,
              v.base + (bossBonus[k] || 0),
            ]),
          ),
          t,
          "",
          bossBonus,
        ) +
        '<div class="facts"><span>전체 추가 옵션 <strong>' +
        t.draws +
        "회</strong></span><span>피격 시간 감소 효과 <strong>" +
        pct(t.recovery_rate * 100) +
        " 적용</strong></span></div><h3>몬스터 고유 저항에 더하는 보정</h3>" +
        resistanceGrid(t.resistance) +
        '<p class="scope">몬스터 고유값과 랜덤 가산 전 기준입니다. 공격 무효화에는 몬스터 고유 공무를 더하며, 개체 상세에서 자동 계산합니다.</p></div>' +
        '<div class="panel maximum-summary"><h2>' +
        esc(t.name) +
        ' 구간 전체 최대 공무 <span id="monster-region-maximum">' +
        pct(max) +
        "</span></h2><p>공통 " +
        t.statuses.null.base +
        " + 피의 돌격병(일반) 고유 115 + 랜덤 가산 30</p></div>" +
        '<div class="panel"><div class="section-top"><h2>특징 있는 몬스터</h2><button data-action="all-highlights">25개 모두 보기</button></div><div class="feature-list">' +
        priority
          .map((key) => {
            const m = byKey.get(key);
            return (
              '<button data-monster="' +
              esc(key) +
              '"><strong>' +
              esc(m.name) +
              '</strong> <span class="kind">' +
              m.kind +
              " · " +
              ranges(stages(m)) +
              "층</span><small>" +
              esc(DATA.highlights[key]) +
              "</small></button>"
            );
          })
          .join("") +
        "</div></div>";
    }
    function matchedMonsters() {
      let list = DATA.monsters.filter(
        (m) =>
          (!state.search || m.name.includes(state.search)) &&
          (!state.kind || m.kind === state.kind) &&
          (!state.highlights || Object.hasOwn(DATA.highlights, m.key)) &&
          (state.floor === null || stages(m).includes(state.floor)),
      );
      list.sort((a, b) =>
        state.sort === "name"
          ? a.name.localeCompare(b.name, "ko")
          : state.sort === "null"
            ? calculate(b).stats.null - calculate(a).stats.null
            : stages(a)[0] - stages(b)[0],
      );
      return list;
    }
    function renderMonsters() {
      $("search").value = state.search;
      $("kind").value = state.kind;
      $("sort").value = state.sort;
      $("only-highlights").checked = state.highlights;
      const all = matchedMonsters(),
        pageCount = Math.max(1, Math.ceil(all.length / 50));
      state.page = Math.min(state.page, pageCount);
      const list = all.slice((state.page - 1) * 50, state.page * 50);
      const where =
        state.floor === null
          ? tier().name + " " + tier().start + "~" + tier().end + "층"
          : state.floor + "층의 출현 후보";
      const conditions = [
        state.search ? "이름 “" + state.search + "”" : "",
        state.kind,
        state.highlights ? "특징 몬스터" : "",
      ].filter(Boolean);
      $("monster-filters").querySelector("summary").textContent =
        "이름·종류로 좁혀보기" +
        (conditions.length ? " · " + conditions.length + "개 조건 적용" : "");
      let html =
        '<p class="result-meta">' +
        esc(where) +
        " · " +
        all.length +
        "개 원본 항목" +
        (conditions.length ? " · " + esc(conditions.join(" · ")) : "") +
        "</p>";
      if (!list.length) {
        const gap =
          state.floor !== null && state.floor - tier().start + 1 === 499;
        html +=
          '<div class="empty"><p>' +
          (gap
            ? "원본 후보 등록을 확인해야 하는 층입니다. 몬스터 이름으로도 찾아볼 수 있습니다."
            : "검색 조건에 맞는 항목을 찾지 못했습니다. 조건을 지우고 다시 찾아보세요.") +
          '</p><button data-action="reset">검색 조건 지우기</button></div>';
        $("monster-results").innerHTML = html;
        return;
      }
      html +=
        '<div class="desktop-list table-wrap"><table id="monster-monster-table"><thead><tr><th>실제 출현층</th><th>종류</th><th>몬스터</th><th>공무</th><th>물리</th><th>마법</th><th>클릭</th><th>공격 설정</th></tr></thead><tbody>' +
        list
          .map((m) => {
            const c = calculate(m),
              stage =
                state.floor === null ? ranges(stages(m)) : String(state.floor);
            return (
              '<tr data-record="' +
              esc(m.key) +
              '"><td class="stage-cell">' +
              stage +
              '</td><td class="kind">' +
              m.kind +
              '</td><td><button class="name-button" data-monster="' +
              esc(m.key) +
              '">' +
              esc(m.name) +
              '</button></td><td class="num">' +
              pct(c.stats.null) +
              "</td>" +
              Object.keys(RES)
                .map((k) => '<td class="num">' + pct(c.resistance[k]) + "</td>")
                .join("") +
              '<td class="attack-cell">' +
              esc(attackText(m)) +
              "</td></tr>"
            );
          })
          .join("") +
        "</tbody></table></div>";
      html +=
        '<div class="mobile-list">' +
        list
          .map((m) => {
            const c = calculate(m);
            return (
              '<article class="monster-card"><div class="card-head"><button class="name-button" data-monster="' +
              esc(m.key) +
              '">' +
              esc(m.name) +
              '</button><span class="kind">' +
              m.kind +
              '</span></div><div class="card-stage">' +
              (state.floor === null ? ranges(stages(m)) : state.floor) +
              '층</div><div class="card-values">' +
              [
                ["공무", c.stats.null],
                ["물리 저항", c.resistance.physical],
                ["마법 저항", c.resistance.magical],
                ["클릭 저항", c.resistance.click],
              ]
                .map(
                  ([k, v]) =>
                    "<div><span>" +
                    k +
                    "</span><strong>" +
                    pct(v) +
                    "</strong></div>",
                )
                .join("") +
              '</div><div class="card-attack">' +
              esc(attackText(m)) +
              "</div></article>"
            );
          })
          .join("") +
        '</div><div class="pager"><button data-page="-1" ' +
        (state.page === 1 ? "disabled" : "") +
        ">이전</button><span>" +
        state.page +
        " / " +
        pageCount +
        '</span><button data-page="1" ' +
        (state.page === pageCount ? "disabled" : "") +
        ">다음</button></div>";
      $("monster-results").innerHTML = html;
    }
    let previousFocus = null;
    function openMonster(key) {
      const m = byKey.get(key),
        t = tier(),
        c = calculate(m);
      previousFocus = document.activeElement;
      let html =
        '<h3 style="margin-top:0">공격 설정</h3><p id="monster-detail-attack"><strong>' +
        esc(attackText(m)) +
        "</strong></p>";
      if (m.interval === 0)
        html +=
          '<p class="hint">' +
          (m.kind === "일반" && t.difficulty < 8
            ? "추가 옵션 " +
              t.draws +
              "회 중 공격 항목이 선택되면 주기 공격이 붙습니다."
            : "출현 시 유형을 먼저 고르고, 추가 옵션 " +
              t.draws +
              "회를 별도로 진행합니다.") +
          "</p>";
      html +=
        "<h3>디버프 기본값</h3>" +
        statusGrid(c.stats, t, "detail-") +
        "<h3>저항 기본값</h3>" +
        resistanceGrid(c.resistance, "detail-res-") +
        '<p class="note">공무 가산 +30%p가 붙으면 최대 <strong id="monster-detail-maximum">' +
        pct(c.stats.null + 30) +
        "</strong>입니다. 전체 추가 옵션 " +
        t.draws +
        '회에는 다른 디버프·체력·저항 후보도 포함됩니다.</p><details open><summary>고유값과 계산 근거</summary><div class="calc-line">공무 ' +
        t.statuses.null.base +
        " + 고유 " +
        n(m.null) +
        " = " +
        pct(c.stats.null) +
        "</div>" +
        Object.keys(RES)
          .map(
            (k) =>
              '<div class="calc-line">' +
              RES[k] +
              " 고유 " +
              n(m.resistance[k]) +
              " + 구간 보정 " +
              t.resistance[k] +
              " = " +
              pct(c.resistance[k]) +
              "</div>",
          )
          .join("") +
        '<div class="calc-line">기준 위치 ' +
        ranges(m.positions) +
        " · 원본 번호 " +
        m.id +
        "</div>" +
        (m.kind === "보스"
          ? '<div class="calc-line">이 보스의 원본 공격 설정에 맞는 보정을 자동 적용했습니다.</div>'
          : "") +
        "</details>";
      openModal(
        '<div class="modal-title monster-guide"><h2 id="monster-detail-title">' +
          esc(m.name) +
          "</h2><p>" +
          esc(m.kind + " · " + t.name + " · " + ranges(stages(m)) + "층") +
          '</p></div><button class="modal-close" aria-label="몬스터 상세 닫기">×</button>',
        '<div class="monster-guide"><div class="dialog-body">' +
          html +
          "</div></div>",
      );
      const overlay = document.getElementById("modal-overlay");
      overlay.setAttribute("aria-labelledby", "monster-detail-title");
      overlay.querySelector(".modal-close").focus();
    }
    function renderAttacks() {
      const t = tier(),
        duration = 1.5 * (1 - 0.8 * t.recovery_rate);
      $("attacks-view").innerHTML =
        '<div class="panel"><h2>' +
        esc(t.name) +
        '의 공격 방식</h2><p>공격 설정에 간격·확률이 지정된 개체는 그 원본 설정을 사용합니다. 스크리머는 전체 공격 10%·1초입니다.</p><div class="flow"><article><h3>원본 간격 0인 일반 몬스터</h3><p>' +
        (t.difficulty < 8
          ? "기본 주기 공격 비활성 → 추가 옵션에서 공격 항목 선택 → 9종 중 하나 부여"
          : "출현 시 공격 유형 선택 → 추가 옵션 7회 별도 추첨") +
        "</p></article><article><h3>원본 간격 0인 보스</h3><p>출현 시 9종 중 하나를 선택합니다. " +
        (t.difficulty < 8
          ? "추가 옵션에서 공격 항목이 뽑히면 다시 선택할 수 있습니다."
          : "추가 옵션 7회는 별도로 진행됩니다.") +
        '</p></article></div><p class="hint">주기 공격과 반사 등 다른 피격 효과는 각각의 조건으로 계산합니다.</p></div><div class="panel"><h2>피격 지속시간 감소 효과</h2><p>' +
        esc(t.name) +
        "에서는 원래 효과의 <strong>" +
        pct(t.recovery_rate * 100) +
        '</strong>를 적용합니다.</p><p class="note">감소 능력치 80%의 예시에서는 실제 적용량 ' +
        pct(80 * t.recovery_rate) +
        ", 한 번의 일반 피격으로 더해지는 기본 대기시간은 <strong>" +
        n(duration) +
        '초</strong>입니다.</p></div><div class="panel"><h2>선택 가능한 공격 유형 9종</h2><p class="hint">선택 비중은 가중치를 합계 35로 나눈 계산값입니다.</p><div class="table-wrap"><table><thead><tr><th>전체 공격 확률</th><th>공격 간격</th><th>유형 선택 비중</th></tr></thead><tbody>' +
        DATA.types
          .map(
            (x) =>
              "<tr><td>" +
              pct(x.all_attack_percent) +
              "</td><td>" +
              n(x.interval_seconds) +
              "초</td><td>약 " +
              ((x.relative_weight / 35) * 100).toFixed(1) +
              "%</td></tr>",
          )
          .join("") +
        "</tbody></table></div></div>";
    }
    function clearFilters() {
      state.search = "";
      state.kind = "";
      state.floor = null;
      state.highlights = false;
      state.page = 1;
      $("floor-error").textContent = "";
      $("floor").removeAttribute("aria-invalid");
      $("monster-filters").open = true;
      render();
    }
    function applyFloor() {
      const value = $("floor").value.trim(),
        stage = Number(value);
      if (!/^\d+$/.test(value) || stage < 501 || stage > 5500) {
        $("floor-error").textContent =
          "501~5500 사이의 실제 층수를 입력해주세요.";
        $("floor").setAttribute("aria-invalid", "true");
        return;
      }
      state.tier = DATA.tiers.findIndex(
        (x) => x.start <= stage && x.end >= stage,
      );
      state.search = "";
      state.kind = "";
      state.highlights = false;
      state.floor = stage;
      state.page = 1;
      state.view = "monsters";
      $("floor-error").textContent = "";
      $("floor").removeAttribute("aria-invalid");
      $("monster-filters").open = false;
      render();
    }
    $("tier").innerHTML = DATA.tiers
      .map(
        (t, i) =>
          '<option value="' +
          i +
          '">' +
          esc(t.name) +
          " " +
          t.start +
          "~" +
          t.end +
          "층</option>",
      )
      .join("");
    root
      .querySelectorAll("[data-view]")
      .forEach((button) =>
        button.addEventListener("click", () => showView(button.dataset.view)),
      );
    $("tier").addEventListener("change", () => {
      const old = tier(),
        position = state.floor === null ? null : state.floor - old.start + 1;
      state.tier = Number($("tier").value);
      if (position !== null) state.floor = tier().start + position - 1;
      state.page = 1;
      render();
    });
    $("find-floor").addEventListener("click", applyFloor);
    $("floor").addEventListener("keydown", (event) => {
      if (event.key === "Enter") applyFloor();
    });
    $("clear-floor").addEventListener("click", () => {
      state.floor = null;
      state.page = 1;
      $("floor-error").textContent = "";
      $("floor").removeAttribute("aria-invalid");
      render();
    });
    let searchTimer;
    $("search").addEventListener("input", () => {
      clearTimeout(searchTimer);
      searchTimer = setTimeout(() => {
        state.search = $("search").value.trim();
        if (state.search) {
          state.floor = null;
          $("floor").value = "";
          $("floor-error").textContent = "";
          $("floor").removeAttribute("aria-invalid");
        }
        state.page = 1;
        renderMonsters();
      }, 200);
    });
    $("kind").addEventListener("change", () => {
      state.kind = $("kind").value;
      state.page = 1;
      renderMonsters();
    });
    $("sort").addEventListener("change", () => {
      state.sort = $("sort").value;
      state.page = 1;
      renderMonsters();
    });
    $("only-highlights").addEventListener("change", () => {
      state.highlights = $("only-highlights").checked;
      state.page = 1;
      renderMonsters();
    });
    root.addEventListener("change", (event) => {
      if (event.target.id === "monster-boss-mode") {
        state.boss = event.target.checked;
        renderRegions();
        $("boss-mode").focus({ preventScroll: true });
      }
      if (event.target.id === "monster-boss-attack-setting") {
        state.bossAttackSetting = event.target.value;
        renderRegions();
        $("boss-attack-setting").focus({ preventScroll: true });
      }
    });
    $("reset-filters").addEventListener("click", clearFilters);
    root.addEventListener("click", (event) => {
      const item = event.target.closest("[data-monster]");
      if (item) {
        openMonster(item.dataset.monster);
        return;
      }
      const page = event.target.closest("[data-page]");
      if (page) {
        state.page += Number(page.dataset.page);
        renderMonsters();
        return;
      }
      const action = event.target.closest("[data-action]")?.dataset.action;

      if (action === "reset") clearFilters();
      if (action === "all-highlights") {
        clearFilters();
        state.view = "monsters";
        state.highlights = true;
        render();
      }
    });
    document
      .getElementById("modal-overlay")
      .addEventListener("guide-modal-close", () => {
        if (previousFocus?.isConnected) previousFocus.focus();
        previousFocus = null;
      });
    document.addEventListener("keydown", (event) => {
      const overlay = document.getElementById("modal-overlay");
      if (
        event.key !== "Tab" ||
        !overlay.classList.contains("open") ||
        !overlay.querySelector("#monster-detail-title")
      )
        return;
      const focusable = [
        ...overlay.querySelectorAll(
          "button, a[href], input, select, summary, [tabindex='0']",
        ),
      ].filter((element) => element.getClientRects().length);
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    });
    render();
    return { show: showView };
  }

  window.MonsterGuide = {
    async show(view) {
      if (view) requestedView = view;
      try {
        loading ||= load();
        const guide = await loading;
        guide.show(requestedView);
      } catch (error) {
        loading = null;
        root.innerHTML =
          '<p role="status">몬스터 자료를 불러오지 못했습니다.</p><button class="monster-entry" id="monster-retry">다시 불러오기</button>';
        document
          .getElementById("monster-retry")
          .addEventListener("click", () => window.MonsterGuide.show());
        console.error(error);
      }
    },
  };

  window.openMonsterGuide = (view = "regions") => {
    return window.GuideNavigation.navigate(routes[view]);
  };
})();
