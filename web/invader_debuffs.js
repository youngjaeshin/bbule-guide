(() => {
  "use strict";
  const root = document.getElementById("invader-debuff-guide");
  let loading = null;

  async function load() {
    root.innerHTML = '<p role="status">침략자 자료를 불러오고 있습니다.</p>';
    const response = await fetch("data_invader_debuffs.json");
    if (!response.ok) throw new Error("침략자 자료 응답 " + response.status);
    const DATA = await response.json();
    root.innerHTML = /* HTML */ `<div class="heading">
        <h1>침략자 디버프</h1>
        <span class="source">자료 기준 v.1890 TEST_6 · 2026년 11월 23일</span>
      </div>

      <div class="tools">
        <div class="field">
          <label for="invader-debuff-invader-type">침략자 종류</label
          ><select id="invader-debuff-invader-type"></select>
        </div>
        <div class="field">
          <label for="invader-debuff-invader-level">화면 표시 레벨</label
          ><input
            id="invader-debuff-invader-level"
            type="number"
            min="1"
            max="150"
            value="150"
            style="width:110px"
          />
        </div>
        <button id="invader-debuff-level-150">150레벨 보기</button>
        <p id="invader-debuff-invader-error" class="error" role="status"></p>
      </div>
      <div id="invader-debuff-invader-results"></div>
      <details class="source-details">
        <summary>분석 기준과 자료</summary>
        <p>
          침략자 7종의 화면 표시 1~150레벨을 APK 코드로 확인한 자료입니다. 화면
          표시 레벨과 내부 계산 번호의 차이를 반영했습니다.
        </p>
        <a href="data_invader_debuffs.json" download>침략자 디버프 자료 받기</a>
      </details>`;
    initialize(DATA);
  }

  function initialize(DATA) {
    const state = { invader: 0, level: 150 };
    const $ = (id) => document.getElementById("invader-debuff-" + id);
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
    const baselineColumns = [...Object.entries(LABELS), ...Object.entries(RES)];
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

    function cell(label, value, sub = "") {
      return (
        '<div class="stat"><div class="label">' +
        esc(label) +
        '</div><div class="value">' +
        pct(value) +
        "</div>" +
        (sub ? '<div class="sub">' + esc(sub) + "</div>" : "") +
        "</div>"
      );
    }
    function statusGrid(stats, config) {
      const inactive = [];
      const cells = [];
      for (const key of Object.keys(LABELS)) {
        const raw = stats[key];
        const cap = config.additional_caps[key];
        const step = config.increase_steps_percent_points[key];
        const display = key === "disable" ? Math.max(0, raw) : raw;
        if (display === 0 && cap === 0) {
          inactive.push(LABELS[key]);
          continue;
        }
        const sub =
          raw < 0
            ? "원본 " + pct(raw) + "에 가산 후 효과 계산"
            : "랜덤 +" + step + "%p·최대 " + cap + "회";
        cells.push(cell(LABELS[key], display, sub));
      }
      return (
        '<div class="stats">' +
        cells.join("") +
        "</div>" +
        (inactive.length
          ? "<details><summary>비활성 항목 " +
            inactive.length +
            '개</summary><p class="hint">' +
            inactive.join("·") +
            "</p></details>"
          : "")
      );
    }
    function resistanceGrid(values) {
      return (
        '<div class="resist-strip">' +
        Object.keys(RES)
          .map((key) => cell(RES[key], values[key]))
          .join("") +
        "</div>"
      );
    }
    function invaderProfile() {
      const inv = DATA.invaders.find((x) => x.id === state.invader);
      return {
        inv,
        range: inv.ranges.find(
          (x) => x.first_level <= state.level && x.last_level >= state.level,
        ),
      };
    }
    function renderInvaders() {
      const { inv, range } = invaderProfile(),
        v = range.values;
      $("invader-type").value = String(state.invader);
      $("invader-level").value = String(state.level);
      let html =
        "<h2>" +
        esc(inv.name) +
        " 침략자 · " +
        state.level +
        '레벨</h2><p class="hint">전체 추가 옵션 ' +
        v.additional_option_draws +
        "회 · 피격 시간 감소 효과 " +
        pct(inv.recovery_rate * 100) +
        ' 적용</p><div class="panel"><h2>추가 옵션 전 기본값</h2>' +
        statusGrid(v.base_stats, v) +
        resistanceGrid(v.base_resistance_percent) +
        '<p class="note">' +
        esc(v.attack_rule) +
        ' · 조사 범위는 화면 표시 1~150레벨입니다.</p><p class="hint">각 항목의 추가 상한은 전체 추첨 횟수 안에서 배분됩니다. 부활·방어막은 조사한 7종에서 기본값과 후보가 모두 0입니다.</p>' +
        (v.base_stats.disable < 0
          ? '<p class="hint">무력화 원본값은 ' +
            pct(v.base_stats.disable) +
            "입니다. 대응 감소가 0일 때의 감소 효과는 0이며, 원본값에 가산한 뒤 효과를 계산합니다.</p>"
          : "") +
        '<details><summary>항목별 최대값과 전투 특성</summary><div class="table-wrap"><table><thead><tr><th>항목</th><th>코드 기본값</th><th>최대 추가 횟수</th><th>개별 최대</th></tr></thead><tbody>' +
        Object.keys(LABELS)
          .map(
            (k) =>
              "<tr><td>" +
              LABELS[k] +
              "</td><td>" +
              pct(v.base_stats[k]) +
              "</td><td>" +
              v.additional_caps[k] +
              "회</td><td>" +
              pct(v.maximum_by_field[k]) +
              "</td></tr>",
          )
          .join("") +
        '</tbody></table></div><p class="hint">유효 일반 피해 보정 분기의 추가 계수는 ' +
        n(inv.damage_factor) +
        '배입니다. 전체 피해식·클릭 가능 여부는 각자의 전투 경로로 확인할 항목입니다.</p></details></div><div class="panel"><h2>레벨별 기본값과 추가 옵션 추첨 횟수</h2><p class="hint">수치는 추가 옵션 추첨 전 기본값입니다. 표를 좌우로 움직여 디버프 12항목과 저항 3종을 확인할 수 있습니다.</p><div class="table-wrap"><table id="invader-debuff-ranges"><thead><tr><th scope="col">화면 레벨</th>' +
        baselineColumns
          .map(([, label]) => '<th scope="col">' + esc(label) + "</th>")
          .join("") +
        '<th scope="col">추가 옵션 추첨 횟수</th></tr></thead><tbody>' +
        inv.ranges
          .map(
            (r) =>
              "<tr" +
              (r.first_level <= state.level && state.level <= r.last_level
                ? ' class="current" aria-current="true"'
                : "") +
              "><td>" +
              r.first_level +
              "~" +
              r.last_level +
              "</td>" +
              baselineColumns
                .map(([key]) => {
                  const raw =
                    r.values.base_stats[key] ??
                    r.values.base_resistance_percent[key];
                  const display = key === "disable" ? Math.max(0, raw) : raw;
                  return (
                    '<td class="num">' +
                    pct(display) +
                    (key === "disable" && raw < 0
                      ? " (원본 " + pct(raw) + ")"
                      : "") +
                    "</td>"
                  );
                })
                .join("") +
              "<td>" +
              r.values.additional_option_draws +
              "회</td></tr>",
          )
          .join("") +
        "</tbody></table></div>" +
        (inv.ranges.some((r) => r.values.base_stats.disable < 0)
          ? '<p class="hint">무력화의 음수 원본값은 괄호 안에 표시했습니다. 원본값에 추가 옵션을 더한 뒤 감소 효과를 계산하며, 음수인 기본 감소 효과는 0으로 처리됩니다.</p>'
          : "") +
        "</div>";
      $("invader-results").innerHTML = html;
    }
    $("invader-type").innerHTML = DATA.invaders
      .map(
        (x) =>
          '<option value="' + x.id + '">' + esc(x.name) + " 침략자</option>",
      )
      .join("");
    $("invader-type").addEventListener("change", () => {
      state.invader = Number($("invader-type").value);
      renderInvaders();
    });
    $("invader-level").addEventListener("input", () => {
      const value = Number($("invader-level").value);
      if (!Number.isInteger(value) || value < 1 || value > 150) {
        $("invader-error").textContent =
          "조사 범위인 1~150레벨을 입력해주세요.";
        return;
      }
      $("invader-error").textContent = "";
      state.level = value;
      renderInvaders();
    });
    $("level-150").addEventListener("click", () => {
      state.level = 150;
      $("invader-error").textContent = "";
      renderInvaders();
    });

    renderInvaders();
  }

  window.showInvaderDebuffs = async () => {
    if (document.getElementById("tab-허수").classList.contains("active")) {
      window.GuideNavigation.setHash("#invader-debuffs");
    }
    try {
      loading ||= load();
      await loading;
    } catch (error) {
      loading = null;
      root.innerHTML =
        '<p role="status">침략자 자료를 불러오지 못했습니다.</p><button class="monster-entry" id="invader-debuff-retry">다시 불러오기</button>';
      document
        .getElementById("invader-debuff-retry")
        .addEventListener("click", window.showInvaderDebuffs);
      console.error(error);
    }
  };
})();
