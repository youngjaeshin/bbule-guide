(() => {
  "use strict";

  const routes = [
    { hash: "#glossary", tab: "용어", sub: '.gl-pill[data-gl="abbr"]' },
    {
      hash: "#combat-mechanics",
      tab: "용어",
      sub: '.gl-pill[data-gl="combat"]',
    },
    { hash: "#enemy-debuffs", tab: "용어", sub: '.gl-pill[data-gl="debuff"]' },
    {
      hash: "#difficulties",
      tab: "용어",
      sub: '.gl-pill[data-gl="difficulty"]',
    },
    { hash: "#game-systems", tab: "용어", sub: '.gl-pill[data-gl="system"]' },
    { hash: "#monsters", tab: "몬스터", view: "regions" },
    { hash: "#monster-search", tab: "몬스터", view: "monsters" },
    { hash: "#monster-attacks", tab: "몬스터", view: "attacks" },
    { hash: "#mercenaries", tab: "용병" },
    { hash: "#equipment", tab: "장비" },
    { hash: "#artifacts", tab: "아티팩트" },
    { hash: "#random-mercenaries", tab: "랜덤용병" },
    {
      hash: "#subslots",
      tab: "보조슬롯",
      sub: '.research-pill[data-rsub="slots"]',
    },
    {
      hash: "#research-gold",
      tab: "보조슬롯",
      sub: '.research-pill[data-rsub="gold"]',
    },
    {
      hash: "#research-coins",
      tab: "보조슬롯",
      sub: '.research-pill[data-rsub="coin"]',
    },
    {
      hash: "#medal-perks",
      tab: "보조슬롯",
      sub: '.research-pill[data-rsub="medal"]',
    },
    {
      hash: "#essence-perks",
      tab: "보조슬롯",
      sub: '.research-pill[data-rsub="essence"]',
    },
    {
      hash: "#shard-miracles",
      tab: "보조슬롯",
      sub: '.research-pill[data-rsub="piece"]',
    },
    {
      hash: "#invader-rewards",
      tab: "허수",
      sub: '.si-pill[data-si="invader"]',
    },
    {
      hash: "#invader-debuffs",
      tab: "허수",
      sub: '.si-pill[data-si="debuff"]',
    },
    { hash: "#scarecrow-bbule", tab: "허수", sub: '.si-pill[data-si="bbule"]' },
    {
      hash: "#scarecrow-transform",
      tab: "허수",
      sub: '.si-pill[data-si="transform"]',
    },
    { hash: "#commanders", tab: "지휘관", sub: '.cmd-pill[data-cmd="merc"]' },
    {
      hash: "#commander-levels",
      tab: "지휘관",
      sub: '.cmd-pill[data-cmd="levelup"]',
    },
    { hash: "#suggestions", tab: "건의" },
  ];
  const byHash = new Map(routes.map((route) => [route.hash, route]));
  let selectingRoute = false;

  function setHash(hash, replace = false) {
    if (selectingRoute || !byHash.has(hash) || location.hash === hash) return;
    if (replace) history.replaceState(null, "", hash);
    else history.pushState(null, "", hash);
  }

  function currentRoute() {
    const tab = document.querySelector(".nav-tab.active")?.dataset.tab;
    const candidates = routes.filter((route) => route.tab === tab);
    return (
      candidates.find((route) => {
        const selector = route.view
          ? '#monster-guide [data-view="' + route.view + '"]'
          : route.sub;
        const button = selector && document.querySelector(selector);
        return (
          button &&
          (button.classList.contains("active") ||
            button.getAttribute("aria-selected") === "true")
        );
      }) || candidates[0]
    );
  }

  async function navigate(hash, { replace = false } = {}) {
    const route = byHash.get(hash);
    if (!route) return;
    setHash(hash, replace);
    selectingRoute = true;
    let ready;
    try {
      const button = document.querySelector(
        '.nav-tab[data-tab="' + route.tab + '"]',
      );
      button.click();
      if (route.sub) document.querySelector(route.sub).click();
      if (route.view) ready = window.MonsterGuide.show(route.view);
      if (hash === "#invader-debuffs") ready = window.showInvaderDebuffs();
      button.scrollIntoView({ block: "nearest", inline: "nearest" });
    } finally {
      selectingRoute = false;
    }
    await ready;
  }

  window.GuideNavigation = { navigate, setHash };

  document.addEventListener("click", (event) => {
    const button = event.target.closest(
      ".nav-tab:not(.disabled), .gl-pill, .research-pill, .si-pill, .cmd-pill, #monster-guide [data-view]",
    );
    if (!button || selectingRoute) return;
    const route = currentRoute();
    if (route) setHash(route.hash);
  });

  window.addEventListener("hashchange", () => navigate(location.hash));
  navigate(byHash.has(location.hash) ? location.hash : currentRoute().hash, {
    replace: true,
  });
})();
