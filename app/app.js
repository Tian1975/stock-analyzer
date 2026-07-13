// ============================================
// Stock Analyzer PWA — app.js
// Sense frameworks, sense build step. Llegeix data/scores.json
// (generat diàriament per GitHub Actions) i el mostra.
// ============================================

const DATA_URL = "data/scores.json";
const FAVORITES_KEY = "stock-analyzer:favorites";

let SCORES = null; // contingut carregat de scores.json
let CURRENT_HORIZON = "mid_term";
let CURRENT_REGION = "all";

// ---------- Utilitats ----------

function getFavorites() {
  try {
    return new Set(JSON.parse(localStorage.getItem(FAVORITES_KEY) || "[]"));
  } catch (e) {
    return new Set();
  }
}

function saveFavorites(set) {
  localStorage.setItem(FAVORITES_KEY, JSON.stringify(Array.from(set)));
}

function toggleFavorite(ticker) {
  const favs = getFavorites();
  if (favs.has(ticker)) favs.delete(ticker);
  else favs.add(ticker);
  saveFavorites(favs);
  return favs.has(ticker);
}

function qualityBand(score) {
  if (score === null || score === undefined) return "unknown";
  if (score >= 66) return "good";
  if (score >= 40) return "ok";
  return "bad";
}

function formatDelta(rankChange) {
  if (rankChange === null || rankChange === undefined) return null;
  if (rankChange > 0) return { text: `▲ +${rankChange}`, cls: "delta-up" };
  if (rankChange < 0) return { text: `▼ ${rankChange}`, cls: "delta-down" };
  return { text: "—", cls: "" };
}

function timeAgoLabel(isoString) {
  if (!isoString) return "";
  const d = new Date(isoString);
  const opts = { year: "numeric", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" };
  return d.toLocaleString("ca-ES", opts);
}

function isStale(isoString) {
  if (!isoString) return true;
  const diffHours = (Date.now() - new Date(isoString).getTime()) / 36e5;
  return diffHours > 48; // més de 2 dies sense actualitzar-se
}

// ---------- Component: anell circular (SVG) ----------

function renderRing(score, size = 44, strokeWidth = 4) {
  const band = qualityBand(score);
  const r = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * r;
  const pct = score === null || score === undefined ? 0 : Math.max(0, Math.min(100, score));
  const offset = circumference * (1 - pct / 100);
  const displayScore = score === null || score === undefined ? "—" : Math.round(score);

  return `
    <div class="ring-wrap ring--${band}" style="width:${size}px;height:${size}px">
      <svg viewBox="0 0 ${size} ${size}">
        <circle class="ring-track" cx="${size / 2}" cy="${size / 2}" r="${r}" stroke-width="${strokeWidth}" />
        <circle class="ring-value" cx="${size / 2}" cy="${size / 2}" r="${r}" stroke-width="${strokeWidth}"
          stroke-dasharray="${circumference}" stroke-dashoffset="${offset}" />
      </svg>
      <div class="ring-number">${displayScore}</div>
    </div>
  `;
}

// ---------- Càrrega de dades ----------

async function loadScores() {
  const res = await fetch(DATA_URL, { cache: "no-store" });
  if (!res.ok) throw new Error(`No s'ha pogut carregar ${DATA_URL} (${res.status})`);
  return res.json();
}

function tickerRegionGroup(region) {
  // El camp region ja ve com US/EU/ES des del pipeline
  return region;
}

// ---------- Renderitzat: pantalla d'inici ----------

function renderHome() {
  const favs = getFavorites();
  const results = SCORES.results;

  document.getElementById("freshness").textContent =
    `Última actualització ${timeAgoLabel(SCORES.generated_at)}`;
  document.getElementById("freshness").classList.toggle("stale", isStale(SCORES.generated_at));

  // Favorits
  const favSection = document.getElementById("favorites-section");
  const favList = document.getElementById("favorites-list");
  const favResults = results.filter((r) => favs.has(r.ticker));
  if (favResults.length > 0) {
    favSection.hidden = false;
    favList.innerHTML = favResults
      .map((r) => {
        const delta = formatDelta(r.rank_change);
        const score = r.scores.mid_term;
        return `
          <div class="compact-row" data-ticker="${r.ticker}">
            ${renderRing(score, 38, 4)}
            <div class="ticker-info">
              <div class="ticker-symbol">${r.ticker}</div>
              <div class="ticker-delta ${delta ? delta.cls : ""}">${delta ? delta.text : "Nou seguiment"}</div>
            </div>
          </div>
        `;
      })
      .join("");
  } else {
    favSection.hidden = true;
  }

  // Top 10
  const top10 = Array.from(results)
    .filter((r) => r.scores.mid_term !== null)
    .sort((a, b) => b.scores.mid_term - a.scores.mid_term)
    .slice(0, 10);

  document.getElementById("top10-list").innerHTML = top10.map((r, i) => renderRankedRow(r, i + 1)).join("");

  attachRowHandlers(document.getElementById("top10-list"));
  attachRowHandlers(favList);
}

function renderRankedRow(r, rank) {
  const midTermScore = r.scores.mid_term;
  const horizonScore = r.scores[CURRENT_HORIZON];
  const score = (horizonScore === null || horizonScore === undefined) ? midTermScore : horizonScore;
  const scoreChange = r.score_change_mid_term;
  let scoreChangeHtml = "";
  if (!r.is_new_entry && scoreChange !== null && scoreChange !== undefined) {
    const cls = scoreChange > 0 ? "delta-up" : scoreChange < 0 ? "delta-down" : "";
    const sign = scoreChange > 0 ? "+" : "";
    scoreChangeHtml = `<div class="score-change ${cls}">${sign}${scoreChange}</div>`;
  }

  const delta = formatDelta(r.rank_change);
  let rankDeltaHtml = "";
  if (r.is_new_entry) {
    rankDeltaHtml = `<span class="new-badge">NOU</span>`;
  } else if (delta) {
    rankDeltaHtml = `<span class="ticker-delta ${delta.cls}" style="margin-left:6px">${delta.text}</span>`;
  }

  return `
    <div class="ranked-row" data-ticker="${r.ticker}">
      <div class="rank-number ${rank <= 3 ? "top3" : ""}">${rank}</div>
      ${renderRing(score, 40, 4)}
      <div class="ticker-block">
        <div class="ticker-symbol">
          ${r.ticker}
          ${r.is_new_top10 && !r.is_new_entry ? '<span class="new-badge">TOP10</span>' : ""}
          ${rankDeltaHtml}
        </div>
        <div class="ticker-sub">Risc: ${r.risk_label}</div>
      </div>
      <div class="score-block">
        <div class="score-value">${score !== null ? score.toFixed(1) : "—"}</div>
        ${scoreChangeHtml}
      </div>
    </div>
  `;
}

function attachRowHandlers(container) {
  if (!container) return;
  container.querySelectorAll("[data-ticker]").forEach((el) => {
    el.addEventListener("click", () => navigateTo("detail", el.dataset.ticker));
  });
}

// ---------- Renderitzat: rànquing complet ----------

function renderRanking(searchTerm = "") {
  const favs = getFavorites();
  let results = Array.from(SCORES.results);

  if (CURRENT_REGION === "favorites") {
    results = results.filter((r) => favs.has(r.ticker));
  } else if (CURRENT_REGION !== "all") {
    results = results.filter((r) => tickerRegionGroup(r.region) === CURRENT_REGION);
  }

  if (searchTerm.trim()) {
    const term = searchTerm.trim().toUpperCase();
    results = results.filter((r) => r.ticker.toUpperCase().includes(term));
  }

  results = results
    .filter((r) => r.scores[CURRENT_HORIZON] !== null)
    .sort((a, b) => b.scores[CURRENT_HORIZON] - a.scores[CURRENT_HORIZON]);

  const listEl = document.getElementById("ranking-list");
  if (results.length === 0) {
    listEl.innerHTML = `<div class="empty-note">Cap resultat amb aquests filtres.</div>`;
    return;
  }

  listEl.innerHTML = results.map((r, i) => renderRankedRow(r, i + 1)).join("");
  attachRowHandlers(listEl);
}

// ---------- Renderitzat: detall d'empresa ----------

function renderSparkline(series, width = 280, height = 56) {
  const values = series.map((p) => p.mid_term).filter((v) => v !== null && v !== undefined);
  if (values.length < 2) {
    return `<div class="empty-note">Encara no hi ha prou historial per mostrar l'evolució.</div>`;
  }
  const min = Math.min.apply(null, values);
  const max = Math.max.apply(null, values);
  const range = max - min || 1;
  const stepX = width / (series.length - 1);

  const points = series
    .map((p, i) => {
      const v = p.mid_term === null || p.mid_term === undefined ? null : p.mid_term;
      if (v === null) return null;
      const x = i * stepX;
      const y = height - ((v - min) / range) * height;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .filter((p) => p !== null)
    .join(" ");

  const trendUp = values[values.length - 1] >= values[0];
  const color = trendUp ? "var(--green)" : "var(--red)";

  return `
    <svg class="sparkline" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none">
      <polyline points="${points}" fill="none" stroke="${color}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" />
    </svg>
  `;
}

function renderEvolutionBox(r) {
  const parts = [];

  if (r.days_in_top10 && r.days_in_top10 > 0) {
    parts.push(`<div class="evolution-stat">📅 Fa <strong>${r.days_in_top10}</strong> ${r.days_in_top10 === 1 ? "dia" : "dies"} al Top 10</div>`);
  }

  if (r.rank_change_7d !== null && r.rank_change_7d !== undefined) {
    const cls = r.rank_change_7d > 0 ? "delta-up" : r.rank_change_7d < 0 ? "delta-down" : "";
    const verb = r.rank_change_7d > 0 ? "Ha pujat" : r.rank_change_7d < 0 ? "Ha baixat" : "Es manté";
    const amount = Math.abs(r.rank_change_7d);
    const text = amount > 0 ? `${verb} ${amount} ${amount === 1 ? "posició" : "posicions"} aquesta setmana` : "Es manté estable aquesta setmana";
    parts.push(`<div class="evolution-stat ${cls}">📊 ${text}</div>`);
  }

  const sparklineHtml = r.history_series ? renderSparkline(r.history_series) : "";

  return `
    ${parts.length ? `<div class="evolution-stats">${parts.join("")}</div>` : ""}
    ${sparklineHtml}
  `;
}

function renderDetail(ticker) {
  const r = SCORES.results.find((x) => x.ticker === ticker);
  if (!r) {
    navigateTo("home");
    return;
  }

  document.getElementById("detail-ticker").textContent = r.ticker;
  document.getElementById("detail-price").textContent =
    r.last_close !== null ? `${r.last_close.toFixed(2)}` : "—";
  document.getElementById("detail-updated").textContent = `Dades del ${r.as_of || "—"}`;

  document.getElementById("evolution-box").innerHTML = renderEvolutionBox(r);

  document.getElementById("detail-ring").outerHTML = renderRing(r.scores.mid_term, 128, 8)
    .replace('class="ring-wrap', 'id="detail-ring" class="ring-wrap ring-wrap--large');

  const favs = getFavorites();
  const starBtn = document.getElementById("btn-toggle-favorite");
  starBtn.textContent = favs.has(r.ticker) ? "★" : "☆";
  starBtn.classList.toggle("active", favs.has(r.ticker));
  starBtn.onclick = () => {
    const isFav = toggleFavorite(r.ticker);
    starBtn.textContent = isFav ? "★" : "☆";
    starBtn.classList.toggle("active", isFav);
  };

  const horizonLabels = { short_term: "Curt termini", mid_term: "Mitjà termini", long_term: "Llarg termini" };
  document.getElementById("detail-horizons").innerHTML = Object.entries(horizonLabels)
    .map(([key, label]) => {
      const val = r.scores[key];
      const band = qualityBand(val);
      const color = band === "good" ? "var(--green)" : band === "ok" ? "var(--amber)" : "var(--red)";
      const pct = val !== null ? val : 0;
      return `
        <div class="horizon-bar-row">
          <div class="horizon-label">${label}</div>
          <div class="horizon-track"><div class="horizon-fill" style="width:${pct}%;background:${color}"></div></div>
          <div class="horizon-value">${val !== null ? val.toFixed(0) : "—"}</div>
        </div>
      `;
    })
    .join("");

  const subscoreLabels = {
    momentum: "Momentum", trend: "Tendència", valuation: "Valoració",
    quality: "Qualitat", growth: "Creixement", risk: "Risc (seguretat)",
  };
  document.getElementById("detail-subscores").innerHTML = Object.entries(subscoreLabels)
    .map(([key, label]) => {
      const val = r.subscores[key];
      return `
        <div class="subscore-cell">
          <div class="subscore-value">${val !== null ? val.toFixed(0) : "—"}</div>
          <div class="subscore-label">${label}</div>
        </div>
      `;
    })
    .join("");

  document.getElementById("detail-risk").textContent = `Risc: ${r.risk_label}`;
  document.getElementById("detail-risk").className = `risk-chip risk-chip--${r.risk_label}`;
  document.getElementById("detail-confidence").textContent = `Confiança de dades: ${r.confidence_pct}%`;

  const explEl = document.getElementById("detail-explanation");
  if (r.explanation && r.explanation.length > 0) {
    explEl.innerHTML = r.explanation.map((line) => `<li>${line}</li>`).join("");
  } else {
    explEl.innerHTML = `<li>Sense prou dades per generar una explicació detallada.</li>`;
  }
}

// ---------- Router senzill ----------

function navigateTo(screen, param = null) {
  document.querySelectorAll(".screen").forEach((el) => (el.hidden = true));
  document.getElementById(`screen-${screen}`).hidden = false;

  if (screen === "detail" && param) {
    renderDetail(param);
    window.location.hash = `#/ticker/${param}`;
  } else if (screen === "ranking") {
    renderRanking();
    window.location.hash = "#/ranking";
  } else {
    renderHome();
    window.location.hash = "#/";
  }
  window.scrollTo(0, 0);
}

function handleHashRoute() {
  const hash = window.location.hash;
  if (hash.startsWith("#/ticker/")) {
    const ticker = decodeURIComponent(hash.replace("#/ticker/", ""));
    navigateTo("detail", ticker);
  } else if (hash === "#/ranking") {
    navigateTo("ranking");
  } else {
    navigateTo("home");
  }
}

// ---------- Inicialització ----------

function setupEventListeners() {
  document.getElementById("btn-view-all").addEventListener("click", () => navigateTo("ranking"));
  document.getElementById("btn-back-from-ranking").addEventListener("click", () => navigateTo("home"));
  document.getElementById("btn-back-from-detail").addEventListener("click", () => {
    history.length > 1 ? history.back() : navigateTo("home");
  });

  document.getElementById("search-input-home").addEventListener("input", (e) => {
    if (e.target.value.trim()) {
      navigateTo("ranking");
      document.getElementById("search-input-ranking").value = e.target.value;
      renderRanking(e.target.value);
    }
  });

  document.getElementById("search-input-ranking").addEventListener("input", (e) => {
    renderRanking(e.target.value);
  });

  document.querySelectorAll("#filter-horizon .chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      document.querySelectorAll("#filter-horizon .chip").forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");
      CURRENT_HORIZON = chip.dataset.horizon;
      renderRanking(document.getElementById("search-input-ranking").value);
    });
  });

  document.querySelectorAll("#filter-region .chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      document.querySelectorAll("#filter-region .chip").forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");
      CURRENT_REGION = chip.dataset.region;
      renderRanking(document.getElementById("search-input-ranking").value);
    });
  });

  window.addEventListener("hashchange", handleHashRoute);
}

async function init() {
  const overlay = document.getElementById("state-overlay");
  const stateMsg = document.getElementById("state-message");

  try {
    overlay.hidden = false;
    stateMsg.textContent = "Carregant dades...";
    SCORES = await loadScores();
    overlay.hidden = true;

    setupEventListeners();
    handleHashRoute();
  } catch (err) {
    stateMsg.textContent = `No s'han pogut carregar les dades. Comprova la connexió i torna-ho a provar. (${err.message})`;
  }
}

init();

// ---------- Service Worker (instal·lable + cache bàsica) ----------
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("sw.js").catch(() => {
      /* silenciós: la PWA funciona igualment sense SW */
    });
  });
}
