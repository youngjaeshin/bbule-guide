(() => {
  'use strict';

  const SORT_FIELDS = [
    ['growthDamage', '성장 데미지'], ['baseDamage', '기본 데미지'],
    ['growthDPS', '성장 DPS'], ['baseDPS', '기본 DPS'],
    ['growthClickDamage', '성장 클릭 데미지'], ['baseClickDamage', '기본 클릭 데미지'],
    ['attackCooldown', '공격 쿨타임'], ['grade', '등급'], ['name', '이름'],
  ];
  const TARGETS = [
    ['self', '자신'], ['all', '모든 용병'], ['group', '특정 집단'],
    ['named', '특정 용병'], ['enemy', '적'], ['account', '계정·기타'],
  ];
  const GRADES = ['P', 'O', 'H', 'X', 'G', 'S', 'A', 'B', 'C', 'D', 'E'];
  const collator = new Intl.Collator('ko', { numeric: true });
  const state = { family: '', conditions: [], sorts: [] };
  let data = null;
  let mercenaries = [];
  let changed = () => {};
  let nextId = 1;

  const escape = value => String(value ?? '').replace(/[&<>"']/g, char => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]
  ));
  const normalize = value => String(value).replace(/\s/g, '').toLocaleLowerCase();
  const entries = mercenary => data?.mercenaries[String(mercenary.id)] || [];
  const familyMatches = (entry, family) => family === 'any' ? entry.families.length > 0 : entry.families.includes(family);
  const sourceEffect = (mercenary, entry) => mercenary.skills.find(skill => skill.slot === entry.slot)?.effectsResolved[entry.index];
  const activeCondition = condition => condition.kind || condition.query || condition.targets.length || condition.activation !== 'any' || condition.source !== 'any';

  function conditionMatches(mercenary, entry, condition) {
    const effect = sourceEffect(mercenary, entry);
    return entry.beneficial
      && (!condition.query || Boolean(condition.kind))
      && (!condition.kind || entry.kinds.includes(condition.kind))
      && (!condition.targets.length || condition.targets.includes(entry.target))
      && (condition.activation === 'any'
        || (condition.activation === 'unconditional' && !entry.condition)
        || (condition.activation === 'conditional' && Boolean(entry.condition))
        || familyMatches(entry, condition.activation))
      && (condition.source === 'any'
        || (condition.source === 'skill' && effect?.scope === 'skill')
        || (condition.source === 'permanent' && effect?.scope?.startsWith('permanent_')));
  }

  function matches(mercenary) {
    const effects = entries(mercenary);
    return (!state.family || effects.some(entry => familyMatches(entry, state.family)))
      && state.conditions.filter(activeCondition).every(condition => (
        effects.some(entry => conditionMatches(mercenary, entry, condition))
      ));
  }

  function sortValue(mercenary, field) {
    if (field === 'grade') return GRADES.length - GRADES.indexOf(mercenary.grade);
    if (field === 'name') return mercenary.name;
    const value = mercenary[field];
    return value === null || value === undefined || value === '' ? null : Number(value);
  }

  function sort(rows) {
    if (!state.sorts.length) return rows;
    return [...rows].sort((left, right) => {
      for (const criterion of state.sorts) {
        const a = sortValue(left, criterion.field);
        const b = sortValue(right, criterion.field);
        const missingA = a === null || (typeof a === 'number' && !Number.isFinite(a));
        const missingB = b === null || (typeof b === 'number' && !Number.isFinite(b));
        if (missingA !== missingB) return missingA ? 1 : -1;
        if (missingA) continue;
        const difference = typeof a === 'string' ? collator.compare(a, b) : a - b;
        if (difference) return criterion.direction === 'asc' ? difference : -difference;
      }
      return GRADES.indexOf(left.grade) - GRADES.indexOf(right.grade)
        || collator.compare(left.name, right.name) || left.id - right.id;
    });
  }

  function familyBadges(mercenary) {
    const families = new Set(entries(mercenary).flatMap(entry => entry.families));
    return [...families].map(family => `<span class="mf-family-badge" title="${escape(data.families[family].description)}">${escape(data.families[family].label)}</span>`).join('');
  }

  function rowExtras(mercenary) {
    const metrics = state.sorts.map((criterion, index) => {
      const label = SORT_FIELDS.find(([field]) => field === criterion.field)[1];
      const value = mercenary[criterion.field];
      const display = typeof value === 'number' ? value.toLocaleString('ko-KR', { maximumFractionDigits: 4 }) : value ?? '—';
      return `<span class="mf-metric${index === 0 ? ' mf-metric-primary' : ''}">${escape(label)} <strong>${escape(display)}${criterion.field === 'attackCooldown' ? '초' : ''}</strong></span>`;
    }).join('');
    const matching = entries(mercenary).filter(entry => (
      (state.family && familyMatches(entry, state.family))
      || state.conditions.filter(activeCondition).some(condition => conditionMatches(mercenary, entry, condition))
    ));
    const reasons = matching.map(entry => {
      const effect = sourceEffect(mercenary, entry);
      const source = effect.scope?.startsWith('permanent_') ? '고용 패시브' : `${entry.slot}번 스킬`;
      return `<div class="mf-match"><span>${escape(source)}</span> ${escape(effect.description)}</div>`;
    }).join('');
    const badges = familyBadges(mercenary);
    return (metrics ? `<div class="mf-metrics">${metrics}</div>` : '')
      + (badges ? `<div class="mf-family-badges">${badges}</div>` : '')
      + (reasons ? `<div class="mf-matches" aria-label="검색 조건에 해당하는 효과">${reasons}</div>` : '');
  }

  function modalSection(mercenary) {
    const relevant = entries(mercenary).filter(entry => entry.families.length);
    if (!relevant.length) return '';
    return `<div class="modal-section mf-modal-section"><h3>퓨어 스킬</h3>
      <div class="mf-family-badges">${familyBadges(mercenary)}</div>
      ${relevant.map(entry => {
        const skill = mercenary.skills.find(item => item.slot === entry.slot);
        return `<div class="mf-modal-effect"><strong>${entry.slot}번 · ${escape(skill['이름'])}</strong>
          <div>${escape(sourceEffect(mercenary, entry).description)}</div></div>`;
      }).join('')}</div>`;
  }

  function activationOptions(selected) {
    const options = [['any', '발동 조건 전체'], ['unconditional', '추가 발동 조건 없음'], ['conditional', '조건부 효과']]
      .concat(Object.entries(data.families).map(([id, family]) => [id, family.label + ' 조건']));
    return options.map(([value, label]) => `<option value="${value}"${selected === value ? ' selected' : ''}>${escape(label)}</option>`).join('');
  }

  function closeSuggestions(input) {
    input.setAttribute('aria-expanded', 'false');
    input.removeAttribute('aria-activedescendant');
    input.nextElementSibling.hidden = true;
  }

  function chooseEffect(condition, input, item) {
    condition.kind = item.id;
    condition.query = item.label;
    input.value = item.label;
    input.removeAttribute('aria-invalid');
    closeSuggestions(input);
    changed();
  }

  function showSuggestions(condition, input) {
    const query = normalize(input.value);
    const suggestions = data.catalogue.filter(item => (
      [item.label, ...item.aliases].some(label => normalize(label).includes(query))
    )).slice(0, 30);
    const list = input.nextElementSibling;
    list.innerHTML = suggestions.length ? suggestions.map((item, index) => (
      `<button type="button" role="option" id="mf-option-${condition.id}-${index}" data-kind="${escape(item.id)}" aria-selected="false">
        <span>${escape(item.label)}</span><small>${item.mercenaries}명</small></button>`
    )).join('') : '<div class="mf-suggestion-empty">해당 효과가 없습니다.</div>';
    list.hidden = false;
    input.setAttribute('aria-expanded', 'true');
    list.querySelectorAll('button').forEach(button => {
      button.addEventListener('pointerdown', event => event.preventDefault());
      button.addEventListener('click', () => {
        chooseEffect(condition, input, data.catalogue.find(item => item.id === button.dataset.kind));
        input.focus();
        closeSuggestions(input);
      });
    });
  }

  function bindEffectInput(condition, row) {
    const input = row.querySelector('.mf-effect-input');
    input.addEventListener('focus', () => showSuggestions(condition, input));
    input.addEventListener('input', () => {
      condition.query = input.value.trim();
      const exact = data.catalogue.find(item => normalize(item.label) === normalize(condition.query));
      condition.kind = exact?.id || '';
      input.removeAttribute('aria-invalid');
      showSuggestions(condition, input);
      changed();
    });
    input.addEventListener('keydown', event => {
      const options = [...input.nextElementSibling.querySelectorAll('button')];
      const selected = options.findIndex(option => option.getAttribute('aria-selected') === 'true');
      if (event.key === 'Escape') closeSuggestions(input);
      if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
        event.preventDefault();
        if (input.nextElementSibling.hidden) showSuggestions(condition, input);
        const step = event.key === 'ArrowDown' ? 1 : -1;
        const index = Math.max(0, Math.min(options.length - 1, selected + step));
        options.forEach((option, position) => option.setAttribute('aria-selected', String(position === index)));
        if (options[index]) {
          input.setAttribute('aria-activedescendant', options[index].id);
          options[index].scrollIntoView({ block: 'nearest' });
        }
      }
      if (event.key === 'Enter' && options.length && !input.nextElementSibling.hidden) {
        event.preventDefault();
        const button = options[Math.max(0, selected)];
        chooseEffect(condition, input, data.catalogue.find(item => item.id === button.dataset.kind));
      }
    });
    input.addEventListener('blur', event => {
      if (input.parentElement.contains(event.relatedTarget)) return;
      if (condition.query && !condition.kind) input.setAttribute('aria-invalid', 'true');
    });
  }

  function renderConditions(focusId = null) {
    const host = document.getElementById('mf-condition-list');
    host.innerHTML = state.conditions.map(condition => `<div class="mf-condition-row" data-condition="${condition.id}">
      <div class="mf-effect-picker">
        <input class="mf-effect-input" type="text" role="combobox" aria-autocomplete="list" autocomplete="off"
          aria-label="효과 검색" aria-expanded="false" aria-controls="mf-options-${condition.id}"
          placeholder="효과 검색 또는 선택" value="${escape(condition.query)}">
        <div class="mf-suggestions" id="mf-options-${condition.id}" role="listbox" aria-label="효과 목록" hidden></div>
        <span class="mf-invalid-message">목록에서 효과를 선택해 주세요.</span>
      </div>
      <details class="mf-target-picker"><summary>대상 구분 없이</summary><div class="mf-target-options">
        ${TARGETS.map(([value, label]) => `<label><input type="checkbox" value="${value}"${condition.targets.includes(value) ? ' checked' : ''}>${label}</label>`).join('')}
        <small>여러 대상 선택 시 하나라도 만족</small>
      </div></details>
      <select class="mf-activation" aria-label="효과 발동 조건">${activationOptions(condition.activation)}</select>
      <select class="mf-source" aria-label="효과 출처">
        <option value="any">스킬·고용 패시브</option><option value="skill">전투 스킬</option><option value="permanent">고용 패시브</option>
      </select>
      <button type="button" class="mf-remove" aria-label="효과 조건 삭제">삭제</button>
    </div>`).join('');
    host.querySelectorAll('.mf-condition-row').forEach(row => {
      const condition = state.conditions.find(item => item.id === Number(row.dataset.condition));
      bindEffectInput(condition, row);
      const targetSummary = row.querySelector('.mf-target-picker summary');
      const updateTargetSummary = () => {
        targetSummary.textContent = condition.targets.length
          ? TARGETS.filter(([value]) => condition.targets.includes(value)).map(([, label]) => label).join(' · ')
          : '대상 구분 없이';
        targetSummary.title = targetSummary.textContent;
      };
      updateTargetSummary();
      row.querySelectorAll('.mf-target-options input').forEach(input => input.addEventListener('change', () => {
        condition.targets = [...row.querySelectorAll('.mf-target-options input:checked')].map(item => item.value);
        updateTargetSummary();
        changed();
      }));
      const activation = row.querySelector('.mf-activation');
      activation.addEventListener('change', () => { condition.activation = activation.value; changed(); });
      const source = row.querySelector('.mf-source');
      source.value = condition.source;
      source.addEventListener('change', () => { condition.source = source.value; changed(); });
      row.querySelector('.mf-remove').addEventListener('click', () => {
        state.conditions = state.conditions.filter(item => item.id !== condition.id);
        renderConditions();
        document.getElementById('mf-add-condition').focus();
        changed();
      });
    });
    if (focusId !== null) host.querySelector(`[data-condition="${focusId}"] .mf-effect-input`)?.focus();
  }

  function renderSorts() {
    const host = document.getElementById('mf-sort-list');
    const rows = state.sorts.length ? state.sorts : [{ field: '', direction: 'desc' }];
    const multiple = state.sorts.length > 1;
    document.querySelector('.mf-sort-section').classList.toggle('mf-multiple', multiple);
    host.innerHTML = rows.map((criterion, index) => `<div class="mf-sort-row" data-sort="${index}">
      ${multiple ? `<span class="mf-sort-priority">${index + 1}순위</span>` : ''}
      <select class="mf-sort-field" aria-label="${index + 1}순위 정렬 기준">
        ${state.sorts.length < 2 ? '<option value="">등급별 기본 보기</option>' : ''}
        ${SORT_FIELDS.map(([value, label]) => `<option value="${value}"${criterion.field === value ? ' selected' : ''}${state.sorts.some((item, position) => position !== index && item.field === value) ? ' disabled' : ''}>${label}</option>`).join('')}
      </select>
      ${criterion.field ? `<select class="mf-sort-direction" aria-label="${index + 1}순위 정렬 방향">
        <option value="desc"${criterion.direction === 'desc' ? ' selected' : ''}>${criterion.field === 'name' ? '이름 역순' : criterion.field === 'attackCooldown' ? '긴 순' : '높은 순'}</option>
        <option value="asc"${criterion.direction === 'asc' ? ' selected' : ''}>${criterion.field === 'name' ? '이름 순' : criterion.field === 'attackCooldown' ? '짧은 순' : '낮은 순'}</option>
      </select>` : ''}
      ${multiple ? `<div class="mf-sort-actions">
        <button type="button" class="mf-sort-up" aria-label="${index + 1}순위 기준 위로"${index === 0 ? ' disabled' : ''}>↑</button>
        <button type="button" class="mf-sort-down" aria-label="${index + 1}순위 기준 아래로"${index >= state.sorts.length - 1 ? ' disabled' : ''}>↓</button>
        <button type="button" class="mf-sort-remove" aria-label="${index + 1}순위 정렬 삭제">×</button>
      </div>` : ''}
    </div>`).join('');
    host.querySelectorAll('.mf-sort-row').forEach(row => {
      const index = Number(row.dataset.sort);
      row.querySelector('.mf-sort-field').addEventListener('change', event => {
        const field = event.target.value;
        if (!field) state.sorts.splice(index, 1);
        else state.sorts[index] = { field, direction: ['name', 'attackCooldown'].includes(field) ? 'asc' : 'desc' };
        renderSorts();
        host.querySelector(`[data-sort="${index}"] .mf-sort-field`)?.focus();
        changed();
      });
      row.querySelector('.mf-sort-direction')?.addEventListener('change', event => {
        state.sorts[index].direction = event.target.value;
        changed();
      });
      row.querySelector('.mf-sort-remove')?.addEventListener('click', () => {
        state.sorts.splice(index, 1);
        renderSorts();
        changed();
      });
      for (const [selector, offset] of [['.mf-sort-up', -1], ['.mf-sort-down', 1]]) {
        row.querySelector(selector)?.addEventListener('click', () => {
          const destination = index + offset;
          [state.sorts[index], state.sorts[destination]] = [state.sorts[destination], state.sorts[index]];
          renderSorts();
          host.querySelector(`[data-sort="${destination}"] .mf-sort-field`).focus();
          changed();
        });
      }
    });
    const addSort = document.getElementById('mf-add-sort');
    addSort.hidden = !state.sorts.length;
    addSort.disabled = state.sorts.length === SORT_FIELDS.length;
    const hint = document.getElementById('mf-sort-hint');
    hint.hidden = state.sorts.length < 2;
    hint.textContent = '앞 순위의 값이 같으면 다음 정렬 기준을 적용합니다.';
  }

  function renderControls() {
    const host = document.getElementById('merc-explorer');
    host.innerHTML = `<section class="mf-sort-section" aria-label="정렬 우선순위">
      <div class="mf-sort-toolbar"><h3>정렬</h3><div id="mf-sort-list"></div><button type="button" id="mf-add-sort">+ 다음 기준</button></div>
      <p class="mf-hint" id="mf-sort-hint" hidden></p>
    </section>
    <section class="mf-effect-section" aria-label="복수 효과 조건">
      <div class="mf-section-heading"><h3>효과 조건</h3><span>모두 만족</span><button type="button" id="mf-add-condition">+ 조건 추가</button></div>
      <div id="mf-condition-list"></div>
    </section>`;
    const familySelect = document.getElementById('mf-family');
    familySelect.innerHTML = '<option value="">퓨어</option><option value="any">퓨어전체</option>'
      + Object.entries(data.families).map(([id, family]) => `<option value="${id}">${escape(id === 'trinity' ? family.label : family.label.replace(/\s/g, ''))}</option>`).join('');
    familySelect.value = state.family;
    familySelect.onchange = () => {
      state.family = familySelect.value;
      familySelect.title = data.families[state.family]?.description || '네 퓨어 분류 중 하나라도 해당하는 스킬 보유 용병';
      changed();
    };
    document.getElementById('mf-add-condition').addEventListener('click', () => {
      const condition = { id: nextId++, kind: '', query: '', targets: [], activation: 'any', source: 'any' };
      state.conditions.push(condition);
      renderConditions(condition.id);
    });
    document.getElementById('mf-add-sort').addEventListener('click', () => {
      const field = SORT_FIELDS.find(([value]) => !state.sorts.some(item => item.field === value))[0];
      state.sorts.push({ field, direction: ['name', 'attackCooldown'].includes(field) ? 'asc' : 'desc' });
      renderSorts();
      changed();
    });
    renderConditions();
    renderSorts();
  }

  function reset(notify = true) {
    state.family = '';
    state.conditions = [];
    state.sorts = [];
    if (data) renderControls();
    if (notify) changed();
  }

  async function init(rows, onChange) {
    mercenaries = rows;
    changed = onChange;
    const host = document.getElementById('merc-explorer');
    try {
      const response = await fetch('data_mercenary_filters.json');
      if (!response.ok) throw new Error('Search index request failed');
      const candidate = await response.json();
      if (candidate.schema_version !== 2 || candidate.mercenary_count !== mercenaries.length
        || mercenaries.some(mercenary => !candidate.mercenaries[String(mercenary.id)])) {
        throw new Error('Search index does not match the mercenary data');
      }
      data = candidate;
      renderControls();
      changed();
    } catch (error) {
      host.innerHTML = '<p class="mf-load-error" role="alert">효과 정보를 불러오지 못했습니다. <button type="button">다시 불러오기</button></p>';
      host.querySelector('button').addEventListener('click', () => init(rows, onChange));
    }
  }

  document.addEventListener('click', event => {
    document.querySelectorAll('.mf-effect-input').forEach(input => {
      if (!input.parentElement.contains(event.target)) closeSuggestions(input);
    });
    document.querySelectorAll('.mf-target-picker[open]').forEach(picker => {
      if (!picker.contains(event.target)) picker.open = false;
    });
  });

  window.MercenaryExplorer = {
    init, matches, sort, isSorted: () => Boolean(state.sorts.length), rowExtras, modalSection, reset,
  };
})();
