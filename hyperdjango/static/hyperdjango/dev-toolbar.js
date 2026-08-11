(function () {
  "use strict";

  const script = document.currentScript;
  const initialId = script && script.dataset.recordId;
  const historyUrl = script && script.dataset.historyUrl;
  const viteUrl = script && script.dataset.viteUrl;
  const stylesUrl =
    (script && script.dataset.stylesUrl) ||
    (script && new URL("dev-toolbar.css", script.src).href);

  if (window.__hyperdjangoDevtools) {
    if (initialId) window.__hyperdjangoDevtools.select(initialId);
    return;
  }

  const state = {
    open: localStorage.getItem("hyperdjango.debug.open") === "true",
    activeTab: localStorage.getItem("hyperdjango.debug.tab") || "overview",
    currentId: initialId || null,
    history: [],
    record: null,
    query: "",
    loading: false,
    pollTimer: null,
    selectionVersion: 0,
    paused: false,
    filter: "all",
    fullscreen: false,
    launcherX: null,
    suppressLauncherClick: false,
    tabsMarkup: "",
    panelMarkup: "",
  };

  const tabs = [
    ["overview", "Overview"],
    ["route", "Route"],
    ["action", "Action"],
    ["output", "Output"],
    ["timeline", "Timeline"],
    ["database", "Database"],
    ["request", "Request / Response"],
    ["exceptions", "Errors / Logs"],
  ];

  const legacyTabs = {
    flow: "timeline",
    dom: "output",
    diagnostics: "overview",
    client: "output",
    lifecycle: "timeline",
    logs: "exceptions",
    raw: "overview",
    renders: "output",
    results: "output",
  };
  state.activeTab = legacyTabs[state.activeTab] || state.activeTab;

  const host = document.createElement("hyperdjango-debug-toolbar");
  host.setAttribute("data-hyperdjango-devtools", "");
  host.style.setProperty("all", "initial", "important");
  host.style.setProperty("contain", "style", "important");
  host.style.setProperty("visibility", "hidden", "important");
  let stylesheetReady = false;
  let pageReady = document.readyState === "complete";
  let toolbarReady = false;
  const revealHostWhenReady = () => {
    if (!stylesheetReady || !pageReady || !toolbarReady) return;
    requestAnimationFrame(() => {
      host.style.setProperty("visibility", "visible", "important");
    });
  };
  if (!pageReady) {
    window.addEventListener(
      "load",
      () => {
        pageReady = true;
        revealHostWhenReady();
      },
      { once: true },
    );
  }
  const shadow = host.attachShadow({ mode: "open" });
  const stylesheet = document.createElement("link");
  stylesheet.rel = "stylesheet";
  stylesheet.href = stylesUrl;
  if (script && script.nonce) stylesheet.nonce = script.nonce;
  stylesheet.addEventListener(
    "load",
    () => {
      stylesheetReady = true;
      revealHostWhenReady();
    },
    { once: true },
  );
  stylesheet.addEventListener(
    "error",
    () => console.error("HyperDjango debug toolbar stylesheet failed to load", stylesUrl),
    { once: true },
  );
  shadow.appendChild(stylesheet);

  const root = document.createElement("section");
  root.id = "hd-debug-toolbar";
  root.setAttribute("aria-label", "HyperDjango debug toolbar");
  root.innerHTML = `
    <div class="hdd-launcher" data-slot="launcher">
      <button class="hdd-launcher-grip" type="button" data-slot="launcher-grip" aria-label="Move toolbar horizontally. Use the left and right arrow keys." title="Drag to move">⠿</button>
      <button class="hdd-launcher-open" type="button" data-action="toggle" aria-label="Open HyperDjango debug toolbar" aria-expanded="false">
        <span class="hdd-launcher-count" data-slot="launcher-count" title="Captured traces">0</span>
        <span class="hdd-launcher-copy"><b>HYPERDJANGO</b></span>
        <span class="hdd-launcher-summary" data-slot="launcher-summary">WAITING FOR TRACE</span>
        <span class="hdd-launcher-toggle" aria-hidden="true">↑</span>
      </button>
    </div>
    <div class="hdd-console" aria-hidden="true">
      <header class="hdd-header">
        <div class="hdd-brand"><div><b>HYPERDJANGO</b><small>REQUEST INSPECTOR</small></div></div>
        <div class="hdd-live" data-slot="live"><i></i> TRACE READY</div>
        <div class="hdd-header-metrics" data-slot="header-metrics"></div>
        <button class="hdd-icon-button" type="button" data-action="fullscreen" data-slot="fullscreen" aria-label="Expand toolbar to full screen" aria-pressed="false" title="Expand toolbar to full screen">⤢</button>
        <button class="hdd-icon-button" type="button" data-action="refresh" aria-label="Refresh request history" title="Refresh request history">↻</button>
        <button class="hdd-icon-button" type="button" data-action="toggle" aria-label="Close HyperDjango debug toolbar" title="Close toolbar">×</button>
      </header>
      <div class="hdd-workspace">
        <aside class="hdd-history">
          <div class="hdd-section-label"><span>REQUEST TAPE</span><span class="hdd-tape-controls"><button type="button" data-action="pause">PAUSE</button><button type="button" data-action="clear">CLEAR</button><b data-slot="history-count">0</b></span></div>
          <label class="hdd-search"><span aria-hidden="true">⌕</span><input type="search" aria-label="Filter request path or action" placeholder="FILTER PATH / ACTION" data-slot="search"><select data-slot="filter" aria-label="Filter traces"><option value="all">ALL</option><option value="action">ACTIONS</option><option value="sse">SSE</option><option value="errors">ERRORS</option></select></label>
          <div class="hdd-history-list" data-slot="history"></div>
        </aside>
        <main class="hdd-inspector">
          <div class="hdd-tabbar" data-slot="tabbar">
            <button class="hdd-tab-scroll" type="button" data-action="tab-prev" data-slot="tab-prev" aria-label="Show previous trace tabs">←</button>
            <nav class="hdd-tabs" role="tablist" aria-label="Trace sections" data-slot="tabs"></nav>
            <button class="hdd-tab-scroll" type="button" data-action="tab-next" data-slot="tab-next" aria-label="Show more trace tabs">→</button>
            <label class="hdd-tab-picker"><span>VIEW</span><select data-slot="tab-select" aria-label="Trace section"></select></label>
          </div>
          <div class="hdd-panel" id="hdd-trace-panel" role="tabpanel" aria-label="Selected trace details" tabindex="0" data-slot="panel"></div>
        </main>
      </div>
    </div>`;
  shadow.appendChild(root);
  document.documentElement.appendChild(host);

  const slots = Object.fromEntries(
    [...root.querySelectorAll("[data-slot]")].map((element) => [
      element.dataset.slot,
      element,
    ]),
  );
  const launcherGrip = root.querySelector("[data-slot='launcher-grip']");

  function esc(value) {
    return String(value ?? "—")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function display(value) {
    if (value === null || value === undefined || value === "") return "—";
    if (typeof value === "object") return JSON.stringify(value);
    return String(value);
  }

  function badge(value, tone) {
    return `<span class="hdd-badge ${tone ? `is-${tone}` : ""}">${esc(value)}</span>`;
  }

  function copyButton(value, label = "Copy value") {
    if (value === null || value === undefined || value === "") return "";
    return `<button class="hdd-copy-button" type="button" data-action="copy" data-copy-value="${esc(value)}" aria-label="${esc(label)}" title="${esc(label)}"><svg viewBox="0 0 16 16" aria-hidden="true"><rect x="5" y="5" width="8" height="8"></rect><path d="M3 11H2V2h9v1"></path></svg></button>`;
  }

  function sourceLink(source, label = "OPEN SOURCE") {
    if (!source?.file) return `<span class="hdd-source-missing">SOURCE UNAVAILABLE</span>`;
    const line = Number(source.line) || 1;
    const href = `vscode://file${encodeURI(String(source.file))}:${line}`;
    const location = `${source.file}:${line}`;
    return `<span class="hdd-source-ref"><a class="hdd-source-link" href="${esc(href)}" title="${esc(location)}">${esc(label)} ↗</a><code>${esc(source.display_file || source.file)}:${line}${source.symbol ? ` · ${esc(source.symbol)}` : ""}</code>${copyButton(location, "Copy source location")}</span>`;
  }

  const domReferenceKeys = new Set([
    "target",
    "trigger_element",
    "trigger_target",
    "final_focus",
    "focus_before",
    "focus_after",
  ]);

  function domLocateButton(selector, label = "Locate DOM element") {
    return `<button type="button" data-action="highlight-dom" data-dom-selector="${esc(selector)}" aria-label="${esc(label)}" title="Scroll to and highlight DOM element"><svg viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="3.5"></circle><path d="M8 1v3M8 12v3M1 8h3M12 8h3"></path></svg></button>`;
  }

  function domReference(value, selector = value) {
    const shown = display(value);
    const canLocate = typeof selector === "string" &&
      selector &&
      !["—", "inherited", "document (observed)"].includes(selector);
    return `<span class="hdd-dom-reference"><code>${esc(shown)}</code>${
      canLocate
        ? `${domLocateButton(selector)}${copyButton(selector, "Copy DOM selector")}`
        : ""
    }</span>`;
  }

  function statusTone(status) {
    if (!status) return "muted";
    if (status >= 500) return "error";
    if (status >= 400) return "warning";
    if (status >= 300) return "info";
    return "success";
  }

  function methodTone(method) {
    return method === "GET" ? "info" : method === "POST" ? "accent" : "muted";
  }

  function table(headers, rows, empty = "NO DATA RECORDED") {
    if (!rows.length) return emptyState(empty);
    return `<div class="hdd-table-wrap"><table><thead><tr>${headers
      .map((header) => `<th>${esc(header)}</th>`)
      .join("")}</tr></thead><tbody>${rows
      .map((row) => `<tr>${row.map((cell) => `<td>${cell}</td>`).join("")}</tr>`)
      .join("")}</tbody></table></div>`;
  }

  function keyValueRows(object) {
    if (!object || typeof object !== "object") return [];
    return Object.entries(object).filter(([key]) => !key.endsWith("_selector")).map(([key, value]) => [
      `<b class="hdd-key">${esc(key)}</b>`,
      domReferenceKeys.has(key)
        ? domReference(value, object[`${key}_selector`] || value)
        : `<code>${esc(display(value))}</code>`,
    ]);
  }

  function section(title, eyebrow, content, count) {
    return `<section class="hdd-section"><div class="hdd-section-head"><div><small>${esc(
      eyebrow,
    )}</small><h3>${esc(title)}</h3></div>${
      count === undefined ? "" : `<span>${esc(count)}</span>`
    }</div>${content}</section>`;
  }

  function emptyState(message) {
    return `<div class="hdd-empty"><b>[ EMPTY ]</b><span>${esc(message)}</span></div>`;
  }

  function metric(label, value, unit = "") {
    return `<div class="hdd-metric"><small>${esc(label)}</small><b>${esc(value)}</b>${
      unit ? `<span>${esc(unit)}</span>` : ""
    }</div>`;
  }

  function renderShellState() {
    root.classList.toggle("is-open", state.open);
    root.classList.toggle("is-fullscreen", state.fullscreen);
    const launcherButton = root.querySelector(".hdd-launcher-open");
    const consoleElement = root.querySelector(".hdd-console");
    const fullscreenButton = slots.fullscreen;
    launcherButton.setAttribute("aria-expanded", String(state.open));
    consoleElement.setAttribute("aria-hidden", String(!state.open));
    root.querySelector(".hdd-launcher-toggle").textContent = state.open ? "↓" : "↑";
    fullscreenButton.setAttribute("aria-pressed", String(state.fullscreen));
    fullscreenButton.setAttribute(
      "title",
      state.fullscreen ? "Restore toolbar to half screen" : "Expand toolbar to full screen",
    );
    fullscreenButton.setAttribute(
      "aria-label",
      state.fullscreen ? "Restore toolbar to half screen" : "Expand toolbar to full screen",
    );
    fullscreenButton.textContent = state.fullscreen ? "⤡" : "⤢";
    localStorage.setItem("hyperdjango.debug.open", String(state.open));
  }

  function setToolbarOpen(open, { restoreFocus = true } = {}) {
    state.open = open;
    renderShellState();
    if (state.open) {
      slots.tabs.querySelector(".is-active")?.focus({ preventScroll: true });
    } else if (restoreFocus) {
      root.querySelector(".hdd-launcher-open")?.focus({ preventScroll: true });
    }
  }

  function setLauncherX(value, { persist = false } = {}) {
    const width = slots.launcher.getBoundingClientRect().width;
    const maximum = Math.max(8, window.innerWidth - width - 8);
    state.launcherX = Math.min(maximum, Math.max(8, Number(value) || 8));
    slots.launcher.style.setProperty("--hdd-launcher-x", `${state.launcherX}px`);
    if (persist) localStorage.setItem("hyperdjango.debug.launcherX", String(state.launcherX));
  }

  function restoreLauncherX() {
    const saved = Number(localStorage.getItem("hyperdjango.debug.launcherX"));
    const fallback = window.innerWidth - slots.launcher.getBoundingClientRect().width - 16;
    setLauncherX(Number.isFinite(saved) && saved > 0 ? saved : fallback);
  }

  function renderTabs() {
    const markup = tabs
      .map(
        ([id, label]) => {
          const active = state.activeTab === id;
          return `<button id="hdd-tab-${id}" type="button" role="tab" aria-selected="${active}" aria-controls="hdd-trace-panel" tabindex="${active ? "0" : "-1"}" data-tab="${id}" class="${active ? "is-active" : ""}">${esc(label)}${tabCount(id)}</button>`;
        },
      )
      .join("");
    if (state.tabsMarkup !== markup) {
      slots.tabs.innerHTML = markup;
      state.tabsMarkup = markup;
    }
    slots["tab-select"].innerHTML = tabs.map(([id, label]) => {
      const count = tabCountValue(id);
      return `<option value="${esc(id)}">${esc(label)}${count ? ` (${count})` : ""}</option>`;
    }).join("");
    slots["tab-select"].value = state.activeTab;
    const activeTab = slots.tabs.querySelector(".is-active");
    if (activeTab) {
      const tabStart = activeTab.offsetLeft;
      const tabEnd = tabStart + activeTab.offsetWidth;
      const visibleStart = slots.tabs.scrollLeft;
      const visibleEnd = visibleStart + slots.tabs.clientWidth;
      if (tabStart < visibleStart) slots.tabs.scrollLeft = tabStart;
      if (tabEnd > visibleEnd) slots.tabs.scrollLeft = tabEnd - slots.tabs.clientWidth;
    }
    slots.panel.setAttribute("aria-labelledby", `hdd-tab-${state.activeTab}`);
    requestAnimationFrame(updateTabOverflow);
  }

  function updateTabOverflow() {
    const overflowing = slots.tabs.scrollWidth > slots.tabs.clientWidth + 1;
    slots.tabbar.classList.toggle("has-overflow", overflowing);
    slots["tab-prev"].disabled = !overflowing || slots.tabs.scrollLeft <= 1;
    slots["tab-next"].disabled = !overflowing ||
      slots.tabs.scrollLeft + slots.tabs.clientWidth >= slots.tabs.scrollWidth - 1;
  }

  function activateTab(tab, { focus = true } = {}) {
    state.activeTab = tab;
    localStorage.setItem("hyperdjango.debug.tab", tab);
    renderRecord();
    if (focus) {
      slots.tabs
        .querySelector(`[data-tab="${tab}"]`)
        ?.focus({ preventScroll: true });
    }
  }

  function tabCountValue(id) {
    const record = state.record || {};
    const counts = {
      overview: diagnosticsFor(record).filter((item) =>
        ["error", "warning"].includes(item.severity),
      ).length,
      output: (record.results || []).reduce(
        (total, result) => total + (result.items || []).length,
        0,
      ) + (record.renders || []).length +
        (record.client?.events || []).filter((item) => item.kind === "DOM swap").length,
      timeline: lifecycleMilestones(record).length,
      database: (record.sql || []).length,
      exceptions: (record.exceptions || []).length + (record.logs || []).length,
    };
    return counts[id] || 0;
  }

  function tabCount(id) {
    const count = tabCountValue(id);
    return count ? `<span>${count}</span>` : "";
  }

  function renderHistory() {
    const query = state.query.toLowerCase();
    const records = state.history.filter((record) => {
      const matchesQuery = `${record.method} ${record.path} ${record.action || ""} ${record.handler || ""}`
        .toLowerCase()
        .includes(query);
      const matchesType =
        state.filter === "all" ||
        (state.filter === "action" && record.action) ||
        (state.filter === "sse" && record.streaming) ||
        (state.filter === "errors" && (record.status >= 400 || record.exceptions));
      return matchesQuery && matchesType;
    });
    slots["history-count"].textContent = state.history.length;
    slots["launcher-count"].textContent = state.history.length;
    root.querySelector(".hdd-launcher-open").setAttribute(
      "aria-label",
      `Open HyperDjango debug toolbar · ${state.history.length} captured ${state.history.length === 1 ? "trace" : "traces"}`,
    );
    const pauseButton = root.querySelector("[data-action='pause']");
    pauseButton.classList.toggle("is-active", state.paused);
    pauseButton.textContent = state.paused ? "RESUME" : "PAUSE";
    slots.history.innerHTML = records.length
      ? records
          .map(
            (record) => `<div class="hdd-history-entry ${record.pinned ? "is-pinned" : ""}"><button type="button" class="hdd-history-row ${
              record.id === state.currentId ? "is-active" : ""
            }" data-request-id="${esc(record.id)}">
              <span class="hdd-history-top">${badge(record.method, methodTone(record.method))}${badge(
                record.status || "…",
                statusTone(record.status),
              )}<time>${esc(formatTime(record.started_at))}</time></span>
              <b title="${esc(record.path)}">${esc(record.path)}</b>
              <span class="hdd-history-bottom"><em>${esc(
                record.action ? `action:${record.action}` : record.handler || "django",
              )}</em><small>${esc(formatDuration(record.duration_ms))}</small></span>
              ${
                record.streaming
                  ? `<span class="hdd-stream-state">SSE / ${esc(record.stream_status || "pending")}</span>`
                  : ""
              }
            </button><button type="button" class="hdd-history-pin ${record.pinned ? "is-active" : ""}" data-action="pin-request" data-pin-request-id="${esc(record.id)}" aria-label="${record.pinned ? "Unpin" : "Pin"} trace ${esc(record.method)} ${esc(record.path)}" title="${record.pinned ? "Unpin trace" : "Pin trace"}"><svg viewBox="0 0 16 16" aria-hidden="true"><path d="M5 2h6l-1 4 2 2v1H9v5l-1 1-1-1V9H4V8l2-2-1-4Z"></path></svg></button></div>`,
          )
          .join("")
      : emptyState(state.query ? "NO REQUESTS MATCH THIS FILTER" : "MAKE A REQUEST TO START THE TAPE");
  }

  function formatTime(value) {
    if (!value) return "--:--:--";
    const date = new Date(value);
    return Number.isNaN(date.valueOf()) ? value : date.toLocaleTimeString([], { hour12: false });
  }

  function formatDuration(value) {
    return value === null || value === undefined ? "—" : `${Number(value).toFixed(2)} ms`;
  }

  function formatBytes(value) {
    if (value === null || value === undefined) return "—";
    const bytes = Number(value);
    if (bytes < 1024) return `${bytes} B`;
    return `${(bytes / 1024).toFixed(2)} KB`;
  }

  function traceActions(record) {
    if (!record.action?.name) return "";
    return `<div class="hdd-trace-actions"><button type="button" data-action="replay">REPLAY ACTION</button></div>`;
  }

  function updatePanel(markup, { preserveState = false } = {}) {
    if (state.panelMarkup === markup) return false;
    const scrollTop = preserveState ? slots.panel.scrollTop : 0;
    const restoreFocus = preserveState &&
      (shadow.activeElement === slots.panel || slots.panel.contains(shadow.activeElement));
    slots.panel.innerHTML = markup;
    state.panelMarkup = markup;
    if (preserveState) slots.panel.scrollTop = scrollTop;
    if (restoreFocus) slots.panel.focus({ preventScroll: true });
    return true;
  }

  function renderRecord({ preservePanelState = false } = {}) {
    renderTabs();
    if (state.loading) {
      updatePanel(`<div class="hdd-loading"><i></i><b>READING TRACE</b><span>Resolving request-local diagnostics…</span></div>`);
      return;
    }
    if (!state.record) {
      updatePanel(emptyState("SELECT A REQUEST FROM THE TAPE"));
      return;
    }
    const renderers = {
      overview: renderOverview,
      route: renderRoute,
      action: renderAction,
      output: renderOutputWorkspace,
      timeline: renderTimelineWorkspace,
      database: renderDatabase,
      request: renderRequestResponse,
      exceptions: renderProblems,
    };
    updatePanel((renderers[state.activeTab] || renderOverview)(state.record), {
      preserveState: preservePanelState,
    });
    renderHeader(state.record);
  }

  function renderHeader(record) {
    const request = record.request || {};
    const response = record.response || {};
    const route = record.route || {};
    slots["launcher-summary"].innerHTML = `${badge(request.method, methodTone(request.method))} <b>${esc(
      request.path,
    )}</b> ${badge(response.status || "…", statusTone(response.status))}`;
    slots.live.innerHTML = `<i></i> ${response.stream_status === "failed" ? "STREAM FAILED" : "TRACE READY"}`;
    slots["header-metrics"].innerHTML = [
      `<span><small>ROUTE</small><b>${esc(route.name || route.pattern || "—")}</b></span>`,
      `<span><small>ACTION</small><b>${esc(record.action?.name || "—")}</b></span>`,
      `<span><small>TOTAL</small><b>${esc(formatDuration(response.request_duration_ms))}</b></span>`,
      `<span><small>TRACE</small><b>${esc((request.id || "").slice(0, 8))}</b></span>`,
    ].join("");
  }

  function renderOverview(record) {
    const request = record.request || {};
    const response = record.response || {};
    const route = record.route || {};
    const costs = record.costs || {};
    return `${traceActions(record)}
      <div class="hdd-title-block"><small>ROUTE / ${esc(route.name || "UNNAMED")} · ${esc((request.id || "").slice(0, 12))}</small><div class="hdd-title-path"><h2>${esc(
        request.path,
      )}</h2>${copyButton(request.path, "Copy request path")}</div><p class="hdd-route-identity"><b>${esc(route.details?.relative_directory || route.pattern || "No file route resolved")}</b><span>${esc(route.handler || "Django handler")}</span></p></div>
      <div class="hdd-metrics">
        ${metric("STATUS", response.status || "…")}
        ${metric("TOTAL", response.request_duration_ms ?? "—", "ms")}
        ${metric("DISPATCH", record.total_ms ?? "—", "ms")}
        ${metric("RENDERS", (record.renders || []).length)}
        ${metric("ITEMS", (record.results || []).reduce((n, result) => n + (result.items || []).length, 0))}
        ${metric("ERRORS", (record.exceptions || []).length)}
      </div>
      ${renderOverviewDiagnostics(record)}
      ${section("Payload and execution costs", "RESOURCE LEDGER", table(["Metric", "Value"], [
        ["Request bytes", `<b>${esc(formatBytes(costs.request_bytes))}</b>`],
        ["Response bytes", `<b>${esc(formatBytes(costs.response_bytes))}</b>`],
        ["SSE payload", `<b>${esc(formatBytes(costs.sse_payload_bytes))}</b>`],
        ["SSE items / chunks", `<code>${esc(costs.sse_items || 0)} / ${esc(costs.stream_chunks || 0)}</code>`],
        ["Time to first byte", `<b>${esc(formatDuration(response.time_to_first_byte_ms))}</b>`],
        ["Time to first SSE item", `<b>${esc(formatDuration(costs.time_to_first_sse_item_ms))}</b>`],
        ["SQL", `<code>${esc(costs.sql_queries || 0)} queries / ${esc(formatDuration(costs.sql_ms || 0))}</code>`],
        ["Render output", `<code>${esc(formatBytes(costs.render_bytes))} / ${esc(costs.render_operations || 0)} operations</code>`],
        ["Log records", `<code>${esc(costs.log_records || 0)}</code>`],
      ]))}
      ${renderCostWarnings(record)}
      ${renderAlertStrip(record)}`;
  }

  function observedAssetState(url) {
    if (!url) return badge("unresolved", "warning");
    let absolute;
    try {
      absolute = new URL(url, window.location.href).href;
    } catch {
      return badge("invalid URL", "error");
    }
    const declared = [...document.querySelectorAll("script[src], link[href]")].some((element) => {
      const value = element.getAttribute("src") || element.getAttribute("href");
      try {
        return new URL(value, window.location.href).href === absolute;
      } catch {
        return false;
      }
    });
    if (declared) return badge("in document", "success");
    const requested = performance.getEntriesByType("resource").some((entry) => entry.name === absolute);
    return requested ? badge("requested", "info") : badge("not observed", "warning");
  }

  function renderRoute(record) {
    const request = record.request || {};
    const route = record.route || {};
    const details = route.details || {};
    const action = record.action || {};
    if (!route.page_class) return emptyState("THIS REQUEST DID NOT RESOLVE A HYPERDJANGO FILE ROUTE");
    const template = details.template || {};
    const fileRows = [
      [badge("page", "accent"), `<code>${esc(details.page_file || route.source?.display_file || "—")}</code>`, route.source ? sourceLink(route.source, "OPEN") : "—"],
      [badge("template", "muted"), `<code>${esc(template.name || "—")}</code>`, template.source ? sourceLink(template.source, "OPEN") : "—"],
      ...(details.layouts || []).map((layout) => [badge("layout", "info"), `<code>${esc(layout.class)}</code>`, layout.source ? sourceLink(layout.source, "OPEN") : "—"]),
    ];
    const selectedSource = action.source || route.handler_source || route.source;
    const dispatchRows = [
      ["Request method", badge(request.method || "—", methodTone(request.method))],
      [action.name ? "Selected action" : "Selected handler", `<b>${esc(action.name || route.handler || "—")}</b>`],
      ["Execution mode", badge(action.mode || route.handler_mode || "unknown", (action.mode || route.handler_mode || "").includes("stream") ? "info" : "muted")],
      ...(action.name ? [["Target", domReference(action.target || "inherited")]] : []),
      ["Source", selectedSource ? sourceLink(selectedSource, "OPEN") : "—"],
    ];
    const entryRows = (details.assets?.entries || []).map((entry) => [
      badge(entry.scope, entry.scope === "route" ? "accent" : "info"),
      `<code>${esc(entry.section)}</code>`,
      `<code>${esc(entry.relative_file || entry.file)}</code>`,
      entry.source ? sourceLink(entry.source, "OPEN") : "—",
    ]);
    const resolvedRows = (details.assets?.resolved || []).map((asset) => [
      badge(asset.section, "muted"),
      `<code>${esc(asset.type)}</code>`,
      `<code>${esc(asset.url)}</code>`,
      observedAssetState(asset.url),
    ]);
    const diagnosticRows = (details.diagnostics || []).map((diagnostic) => [
      badge(diagnostic.severity, diagnostic.severity === "error" ? "error" : "warning"),
      `<span>${esc(diagnostic.message)}</span>`,
    ]);
    return `${traceActions(record)}
      <div class="hdd-title-block hdd-route-title"><small>FILE ROUTE / ${esc(route.name || "UNNAMED")}</small><div class="hdd-title-path"><h2>${esc(request.path)}</h2>${copyButton(request.path, "Copy request path")}</div><p class="hdd-route-identity"><b>${esc(details.relative_directory || details.directory || route.pattern || "—")}</b><span>${esc(route.handler || "—")}</span></p></div>
      ${section("URL to filesystem", "ROUTE RESOLUTION", table(["Field", "Value"], keyValueRows({ name: route.name, pattern: route.pattern, namespace: route.namespace, parameters: route.parameters, directory: details.directory, page_class: route.page_class })))}
      ${section("Selected request dispatch", action.name ? "MATCHED HYPER ACTION" : "MATCHED HTTP HANDLER", table(["Field", "Value"], dispatchRows), dispatchRows.length)}
      ${section("Route files and layout chain", "SOURCE MAP", table(["Role", "File / Class", "Source"], fileRows), fileRows.length)}
      ${section("Declared entry files", `VITE / ${String(details.assets?.environment || "unknown").toUpperCase()}`, table(["Scope", "Placement", "Entry", "Source"], entryRows, "THIS ROUTE AND ITS LAYOUTS DECLARE NO ENTRY FILES"), entryRows.length)}
      ${section("Resolved browser assets", "CURRENT DOCUMENT OBSERVATION", table(["Placement", "Type", "URL", "Browser state"], resolvedRows, "NO RESOLVED ASSETS WERE RECORDED"), resolvedRows.length)}
      ${section("Route diagnostics", "FILES / TEMPLATES / ASSETS", diagnosticRows.length ? table(["Severity", "Finding"], diagnosticRows) : `<div class="hdd-route-ok">${badge("passed", "success")}<span>Route source, template, and asset resolution produced no server-side diagnostics.</span></div>`, diagnosticRows.length)}`;
  }

  function renderCostWarnings(record) {
    const warnings = [];
    (record.timings || []).filter((timing) => Number(timing.duration_ms) >= 100).forEach((timing) => warnings.push(["Slow phase", `<code>${esc(timing.phase)} — ${esc(formatDuration(timing.duration_ms))}</code>`]));
    (record.sql || []).filter((query) => Number(query.duration_ms) >= 50).forEach((query) => warnings.push(["Slow query", `<code>${esc(query.sql)}</code>`]));
    if (Number(record.costs?.response_bytes) >= 500000) warnings.push(["Large response", `<code>${esc(formatBytes(record.costs.response_bytes))}</code>`]);
    return warnings.length ? section("Performance warnings", "THRESHOLDS", table(["Warning", "Detail"], warnings), warnings.length) : "";
  }

  function renderAlertStrip(record) {
    const exceptions = record.exceptions || [];
    const streaming = (record.results || []).find((result) => result.streaming);
    if (exceptions.length) {
      return `<button class="hdd-alert is-error" data-tab="exceptions"><b>${exceptions.length} EXCEPTION${
        exceptions.length === 1 ? "" : "S"
      }</b><span>${esc(exceptions[0].type)} — ${esc(exceptions[0].message)}</span><i>VIEW →</i></button>`;
    }
    if (streaming) {
      return `<button class="hdd-alert" data-tab="output"><b>SSE ${esc(
        streaming.iteration_status || "PENDING",
      )}</b><span>${esc(streaming.note || "Streaming response observed")}</span><i>VIEW →</i></button>`;
    }
    return "";
  }

  function renderAction(record) {
    const action = record.action || {};
    if (!action.name) return emptyState("NO HYPER ACTION WAS DISPATCHED FOR THIS REQUEST");
    return `${traceActions(record)}${section("Action identity", "DISPATCH", table(["Field", "Value"], keyValueRows({ name: action.name, target: action.target })))}${section("Action source", "PYTHON LOCATION", action.source ? `<div class="hdd-source-block">${sourceLink(action.source)}</div>` : emptyState("ACTION SOURCE COULD NOT BE RESOLVED"))}
      ${section("Sanitized arguments", "INPUT", table(["Argument", "Value"], keyValueRows(action.arguments || {})), Object.keys(action.arguments || {}).length)}`;
  }

  function renderResults(record) {
    const results = record.results || [];
    const rows = [];
    results.forEach((result, resultIndex) => {
      const items = result.items || [];
      if (!items.length) {
        rows.push([
          `<b>${resultIndex + 1}</b>`,
          `<code>${esc(result.kind)}</code>`,
          `<code>${esc((result.item_types || []).join(", ") || "—")}</code>`,
          badge(result.iteration_status || "known", result.iteration_status === "failed" ? "error" : "muted"),
          "—",
          "—",
          "—",
          "—",
          "—",
          "—",
          "—",
          "—",
          "—",
          `<span>${esc(result.note || "—")}</span>`,
        ]);
        return;
      }
      items.forEach((item, itemIndex) => {
        rows.push([
          `<b>${resultIndex + 1}.${itemIndex + 1}</b>`,
          `<code>${esc(result.kind)}</code>`,
          badge(item.type, "accent"),
          badge(result.iteration_status || "known", result.iteration_status === "failed" ? "error" : "success"),
          domReference(item.target || "—"),
          `<code>${esc(item.swap || "—")}</code>`,
          `<code>${esc(item.event || "—")}</code>`,
          `<code>${esc(item.event_id || "—")}</code>`,
          badge(item.delivered === false ? "resumed / skipped" : "delivered", item.delivered === false ? "warning" : "success"),
          `<code>${esc(formatDuration(item.at_ms))}</code>`,
          `<code>${esc(formatDuration(item.gap_ms))}</code>`,
          `<code>${esc(formatBytes(item.payload_bytes))}</code>`,
          item.content || item.html || item.js
            ? `<div class="hdd-copy-block"><pre class="hdd-content-preview">${esc(item.content || item.html || item.js)}</pre>${copyButton(item.content || item.html || item.js, "Copy result content")}</div>`
            : "—",
          (item.details || []).length
            ? item.details.map((detail) => `<div class="hdd-detail"><b>${esc(detail.label)}</b><code>${esc(display(detail.value))}</code></div>`).join("")
            : "—",
        ]);
      });
    });
    return section(
      "Action results and SSE",
      "OUTPUT TAPE",
      table(["#", "Result", "Item", "Stream", "Target", "Swap", "Event", "Event ID", "Delivery", "At", "Gap", "Bytes", "Content", "Metadata"], rows, "NO ACTION RESULT WAS RECORDED"),
      rows.length,
    );
  }

  function renderSseWaterfall(results) {
    const items = results.flatMap((result) => (result.items || []).filter((item) => item.at_ms !== undefined));
    if (!items.length) return "";
    const total = Math.max(...items.map((item) => Number(item.at_ms) || 0), 0.001);
    const rows = items.map((item) => {
      const left = Math.min(100, ((Number(item.at_ms) || 0) / total) * 100);
      return `<div class="hdd-sse-timing"><b>${esc(item.sequence || "—")}</b><code>${esc(item.event || item.type)}</code><div><i style="--hdd-left:${left}%"></i></div><span>${esc(formatDuration(item.gap_ms))}</span><span>${esc(formatBytes(item.payload_bytes))}</span></div>`;
    });
    return section("SSE item waterfall", "EVENT PACING / TIME TO FIRST EVENT", `<div class="hdd-sse-waterfall">${rows.join("")}</div>`, items.length);
  }

  function parseDiffItem(value, tone) {
    const raw = String(value || "");
    const divider = raw.indexOf(" · ");
    const path = divider >= 0 ? raw.slice(0, divider) : raw;
    const detail = divider >= 0 ? raw.slice(divider + 3) : raw;
    if (tone !== "changed") {
      return {
        path,
        element: detail || path,
        change: tone === "added" ? "Element added" : "Element removed",
        before: tone === "removed" ? detail : null,
        after: tone === "added" ? detail : null,
      };
    }

    const arrow = detail.indexOf(" → ");
    const left = arrow >= 0 ? detail.slice(0, arrow) : detail;
    const after = arrow >= 0 ? detail.slice(arrow + 3) : "—";
    const colon = left.indexOf(": ");
    let element = path;
    let description = left;
    if (colon >= 0 && !left.startsWith("attribute ")) {
      element = left.slice(0, colon);
      description = left.slice(colon + 2);
    }
    let change = "DOM value changed";
    let before = description;
    if (description.startsWith("attributes ")) {
      change = "Attributes changed";
      before = description.slice("attributes ".length);
    } else if (description.startsWith("attribute ")) {
      const attributeColon = description.indexOf(": ");
      change = attributeColon >= 0
        ? `${description.slice(0, attributeColon)} changed`
        : "Attribute changed";
      before = attributeColon >= 0
        ? description.slice(attributeColon + 2)
        : description;
    } else if (description.startsWith("text ")) {
      change = "Text changed";
      before = description.slice("text ".length);
    }
    return { path, element, change, before, after };
  }

  function diffList(label, values, tone, target) {
    const items = values || [];
    return `<div class="hdd-diff-group is-${tone}"><header><b>${esc(label)}</b><span>${items.length}</span></header>${items.length ? `<ol>${items.map((item) => {
      const parsed = parseDiffItem(item, tone);
      const path = parsed.path;
      const selector = label === "REMOVED"
        ? null
        : path === ":scope"
          ? target
          : target && `${target} ${path}`;
      return `<li class="hdd-diff-item"><div class="hdd-diff-identity"><b>${esc(parsed.change)}</b><code>${esc(parsed.element)}</code><small>${esc(parsed.path)}</small></div>${parsed.before === null ? "" : `<div class="hdd-diff-value"><small>BEFORE</small><code>${esc(parsed.before)}</code></div>`}${parsed.after === null ? "" : `<div class="hdd-diff-value"><small>AFTER</small><code>${esc(parsed.after)}</code></div>`}${selector ? `<span class="hdd-dom-reference hdd-diff-locate">${domLocateButton(selector, `Locate ${parsed.path}`)}</span>` : ""}</li>`;
    }).join("")}</ol>` : `<p>NO ${esc(label)} NODES</p>`}</div>`;
  }

  function renderDomDiff(record) {
    const swaps = (record.client?.events || []).filter((item) => item.kind === "DOM swap");
    if (!swaps.length) return emptyState("NO CLIENT DOM SWAP HAS BEEN CORRELATED WITH THIS TRACE");
    return swaps.map((swap, index) => {
      const targetSelector = swap.target_selector || swap.target;
      const metrics = `<div class="hdd-diff-metrics"><span><small>TARGET</small><b>${domReference(swap.target || "—", targetSelector)}</b></span><span><small>MODE</small><b>${esc(swap.swap || "—")}</b></span><span><small>MATCHES</small><b>${esc(swap.target_matches_before || 0)} → ${esc(swap.target_matches_after || 0)}</b></span><span><small>DOM BYTES</small><b>${esc(formatBytes(swap.bytes_before))} → ${esc(formatBytes(swap.bytes_after))}</b></span><span><small>FOCUS BEFORE</small><b>${domReference(swap.focus_before || "—", swap.focus_before_selector || swap.focus_before)}</b></span><span><small>FOCUS AFTER</small><b>${domReference(swap.focus_after || "—", swap.focus_after_selector || swap.focus_after)}</b></span></div>`;
      const duplicates = (swap.duplicate_ids || []).length ? `<div class="hdd-contract-inline is-error"><b>DUPLICATE IDS</b><code>${esc((swap.duplicate_ids || []).join(", "))}</code></div>` : "";
      const truncated = swap.diff_truncated ? `<div class="hdd-contract-inline is-warning"><b>BOUNDED DIFF</b><span>The target exceeded the ${DOM_SNAPSHOT_LIMIT}-node snapshot limit.</span></div>` : "";
      return section(`Swap ${index + 1} · ${swap.target || "unknown target"}`, `ACTUAL DOM OUTCOME · ${formatDuration(swap.duration_ms)}`, `${metrics}${duplicates}${truncated}<div class="hdd-diff-grid">${diffList("ADDED", swap.added_nodes, "added", targetSelector)}${diffList("REMOVED", swap.removed_nodes, "removed", targetSelector)}${diffList("CHANGED", swap.changed_nodes, "changed", targetSelector)}</div>`, (swap.added_total || 0) + (swap.removed_total || 0) + (swap.changed_total || 0));
    }).join("");
  }

  function diagnosticsFor(record) {
    const diagnostics = [];
    const events = record.client?.events || [];
    const swaps = events.filter((item) => item.kind === "DOM swap");
    const streamEvents = events.filter((item) => item.kind === "stream event");
    const resultItems = (record.results || []).flatMap((result) => result.items || []);
    const validSwaps = new Set(["inner", "innerhtml", "outer", "outerhtml", "before", "beforebegin", "after", "afterend", "prepend", "afterbegin", "append", "beforeend", "replace", "delete", "none", "observed"]);
    const add = (severity, code, title, detail, source = null) => diagnostics.push({ severity, code, title, detail, source });
    (record.exceptions || []).forEach((exception) => add("error", "EXCEPTION", exception.type, exception.message, exception.frames?.[0]));
    swaps.forEach((swap) => {
      if (!swap.target_existed_before && !swap.target_existed_after) add("error", "TARGET_MISSING", "Swap target was not found", swap.target || "No target selector");
      if ((swap.target_matches_before || 0) > 1) add("warning", "TARGET_AMBIGUOUS", "Target selector matched multiple nodes", `${swap.target} matched ${swap.target_matches_before} nodes`);
      if (swap.error) add("error", "DOM_ERROR", "DOM inspection failed", swap.error);
      if ((swap.duplicate_ids || []).length) add("error", "DUPLICATE_ID", "Swap introduced duplicate IDs", swap.duplicate_ids.join(", "));
      if (!(swap.added_total || swap.removed_total || swap.changed_total) && swap.bytes_before === swap.bytes_after) add("warning", "NO_OP_SWAP", "Swap produced no observable DOM change", `${swap.swap || "swap"} ${swap.target || "—"}`);
      if ((swap.added_total || 0) + (swap.removed_total || 0) + (swap.changed_total || 0) > 500) add("warning", "LARGE_SWAP", "Swap changed more than 500 nodes", swap.target || "—");
    });
    resultItems.forEach((item) => {
      if (item.swap && !validSwaps.has(String(item.swap).toLowerCase())) add("warning", "SWAP_NORMALIZED", "Unknown swap mode will fall back to inner", item.swap);
    });
    streamEvents.filter((item) => item.target && ["patch_html", "html"].includes(String(item.event).toLowerCase())).forEach((item) => {
      if (!swaps.some((swap) => swap.source_sequence === item.sequence)) add("error", "TARGET_NO_OUTCOME", "Stream item produced no observed DOM outcome", `Item ${item.sequence} targeted ${item.target}, but no completed swap was correlated.`);
    });
    const hasHtml = resultItems.some((item) => item.type === "HTML");
    if (record.action?.name && hasHtml && !resultItems.some((item) => item.target) && !record.action.target) add("warning", "TARGET_IMPLICIT", "HTML result has no explicit target", "The runtime must inherit a target from the triggering element.");
    if (resultItems.some((item) => item.type === "Redirect") && resultItems.some((item) => item.type === "History")) add("warning", "NAV_CONFLICT", "Redirect and history updates were returned together", "Prefer one navigation outcome per action.");
    const streaming = (record.results || []).find((result) => result.streaming);
    if (streaming) {
      if (["closed", "failed"].includes(streaming.iteration_status)) add("error", "STREAM_INCOMPLETE", `Stream ${streaming.iteration_status}`, streaming.note || "Stream did not complete normally.");
      const terminal = streamEvents.some((item) => ["end", "redirect", "switch_action"].includes(item.event));
      if (record.client?.summary && !terminal) add("error", "TERMINAL_EVENT_MISSING", "Client did not observe an SSE terminal event", "Expected end or redirect before stream completion.");
      const ids = (streaming.items || []).map((item) => item.event_id).filter(Boolean);
      if (new Set(ids).size !== ids.length) add("error", "DUPLICATE_EVENT_ID", "Duplicate SSE event IDs detected", ids.join(", "));
      (streaming.items || []).filter((item) => Number(item.gap_ms) >= 2000).forEach((item) => add("warning", "STREAM_STALL", "Long gap between SSE items", `${formatDuration(item.gap_ms)} before item ${item.sequence}`));
    }
    events.filter((item) => item.kind === "stream retry").forEach((item) => add("warning", "STREAM_RETRY", "SSE connection retried", `Attempt ${item.attempt} after ${formatDuration(item.delay)}`));
    events.filter((item) => item.kind === "retries failed").forEach((item) => add("error", "STREAM_RETRIES_FAILED", "SSE reconnect attempts exhausted", item.error || "Connection failed"));
    events.filter((item) => ["request aborted", "request replaced"].includes(item.kind)).forEach((item) => add("warning", "STREAM_CANCELLED", "Request stopped before normal completion", item.mode || item.kind));
    events.filter((item) => ["request blocked", "request exception", "request error"].includes(item.kind)).forEach((item) => add("error", "CLIENT_REQUEST_ERROR", "Browser request failed", item.error || item.kind));
    if (!diagnostics.length) add("success", "CONTRACT_OK", "No HyperDjango contract violations detected", "Targets, swaps, stream completion, and DOM outcomes look consistent.");
    return diagnostics;
  }

  function renderOverviewDiagnostics(record) {
    const diagnostics = diagnosticsFor(record);
    const counts = Object.fromEntries(["error", "warning", "success", "info"].map((severity) => [severity, diagnostics.filter((item) => item.severity === severity).length]));
    const issueCount = counts.error + counts.warning;
    const streamCount = (record.client?.events || []).filter((item) => item.kind === "stream event").length;
    const health = counts.error ? "error" : counts.warning ? "warning" : "success";
    const healthLabel = counts.error ? "FAILED" : counts.warning ? "CHECK" : "HEALTHY";
    const rows = diagnostics.map((item) => `<article class="hdd-diagnostic is-${esc(item.severity)}"><header>${badge(item.severity, item.severity === "error" ? "error" : item.severity === "warning" ? "warning" : "success")}<code>${esc(item.code)}</code></header><div class="hdd-diagnostic-copy"><b>${esc(item.title)}</b><p>${esc(item.detail)}</p></div>${item.source ? `<footer>${sourceLink(item.source)}</footer>` : ""}</article>`).join("");
    const content = `<div class="hdd-health-strip is-${health}"><div class="hdd-health-state"><i aria-hidden="true">${health === "success" ? "✓" : "!"}</i><span><small>REQUEST HEALTH</small><b>${healthLabel}</b></span></div><div class="hdd-health-facts"><span><b>${counts.error}</b><small>ERRORS</small></span><span><b>${counts.warning}</b><small>WARNINGS</small></span><span><b>${streamCount}</b><small>STREAM EVENTS</small></span></div></div><div class="hdd-diagnostics">${rows}</div>`;
    return section(
      "Diagnostics",
      "AUTOMATED CHECKS",
      content,
      issueCount || undefined,
    );
  }

  function renderOutputWorkspace(record) {
    const hasSwaps = (record.client?.events || []).some((item) => item.kind === "DOM swap");
    const hasResults = (record.results || []).length > 0;
    return `${hasResults ? renderResults(record) : ""}${renderRenders(record)}${hasSwaps ? renderDomDiff(record) : ""}${renderClient(record)}`;
  }

  function renderClient(record) {
    const events = record.client?.events || [];
    const summary = record.client?.summary || {};
    const rows = events.map((event, index) => [
      `<b>${index + 1}</b>`,
      `<code>${esc(formatDuration(event.at_ms))}</code>`,
      badge(event.kind || "event", event.error ? "error" : "info"),
      domReference(event.target || "—", event.target_selector || event.target),
      `<code>${esc(event.swap || "—")}</code>`,
      `<code>${esc(event.duration_ms === undefined ? "—" : formatDuration(event.duration_ms))}</code>`,
      `<code>${esc(event.added_total ?? "—")} / ${esc(event.removed_total ?? "—")} / ${esc(event.changed_total ?? "—")}</code>`,
      `<span class="hdd-focus-pair">${domReference(event.focus_before || "—", event.focus_before_selector || event.focus_before)}<span>→</span>${domReference(event.focus_after || "—", event.focus_after_selector || event.focus_after)}</span>`,
      `<code>${esc(event.error || event.event || "—")}</code>`,
    ]);
    return `${section("Browser outcome", "ACTUAL DOM / FOCUS / ERRORS", table(["#", "At", "Kind", "Target", "Swap", "Duration", "+ / − / Δ nodes", "Focus", "Detail"], rows, "NO CLIENT OUTCOME HAS BEEN POSTED FOR THIS TRACE"), events.length)}${section("Client summary", "OBSERVED RESULT", table(["Field", "Value"], keyValueRows(summary)))}`;
  }

  function renderDatabase(record) {
    const queries = record.sql || [];
    const counts = new Map();
    queries.forEach((query) => counts.set(query.fingerprint, (counts.get(query.fingerprint) || 0) + 1));
    const repeated = [...counts.values()].filter((count) => count > 1).reduce((total, count) => total + count, 0);
    const nPlusOne = [...counts.values()].filter((count) => count >= 3).length;
    const rows = queries.map((query, index) => {
      const count = counts.get(query.fingerprint) || 1;
      const sql = String(query.sql || "");
      const preview = sql.length > 120 ? `${sql.slice(0, 119)}…` : sql;
      const queryDetails = `<details class="hdd-query-disclosure"><summary><code>${esc(preview)}</code><b><span>EXPAND</span><span>COLLAPSE</span></b></summary><div><span class="hdd-copy-label"><small>FULL SQL</small>${copyButton(sql, "Copy SQL")}</span><pre>${esc(sql)}</pre><span class="hdd-copy-label"><small>SANITIZED PARAMETERS</small>${copyButton(display(query.params), "Copy SQL parameters")}</span><pre>${esc(display(query.params))}</pre></div></details>`;
      return [
        `<b>${index + 1}</b>`,
        `<code>${esc(formatDuration(query.at_ms))}</code>`,
        `<b>${esc(formatDuration(query.duration_ms))}</b>`,
        `<code>${esc(query.alias)}</code>`,
        `<code>${esc(query.phase || "—")}</code>`,
        badge(query.transaction ? "atomic" : "autocommit", query.transaction ? "warning" : "muted"),
        count >= 3 ? badge(`N+1 ×${count}`, "error") : count > 1 ? badge(`duplicate ×${count}`, "warning") : "—",
        queryDetails,
      ];
    });
    return `<div class="hdd-scope-note"><b>HYPERDJANGO SQL CONTEXT</b><span>Queries are correlated with dispatch, action, and render phases. Use Django Debug Toolbar for comprehensive SQL inspection.</span></div><div class="hdd-metrics">${metric("QUERIES", queries.length)}${metric("SQL TIME", record.costs?.sql_ms || 0, "ms")}${metric("REPEATED", repeated)}${metric("N+1 GROUPS", nPlusOne)}${metric("TRANSACTIONS", queries.filter((query) => query.transaction).length)}${metric("ERRORS", queries.filter((query) => query.error).length)}</div>${section("Database queries", "HYPERDJANGO PHASE / DUPLICATES / N+1", table(["#", "At", "Time", "DB", "Phase", "Transaction", "Diagnosis", "Query"], rows, "NO DATABASE QUERIES WERE CAPTURED"), queries.length)}`;
  }

  function renderTimelineWorkspace(record) {
    return `${renderTimeline(record)}${renderSseWaterfall(record.results || [])}${renderLifecycle(record)}`;
  }

  function renderLogs(record) {
    const logs = record.logs || [];
    const rows = logs.map((log, index) => [
      `<b>${index + 1}</b>`,
      `<code>${esc(formatDuration(log.at_ms))}</code>`,
      badge(log.level, ["ERROR", "CRITICAL"].includes(log.level) ? "error" : log.level === "WARNING" ? "warning" : "muted"),
      `<code>${esc(log.logger)}</code>`,
      `<span>${esc(log.message)}</span>`,
      `<code>${esc(log.display_file || log.file)}:${esc(log.line)} ${esc(log.function)}</code>`,
    ]);
    return section("Request-scoped server logs", "PYTHON LOGGING", table(["#", "At", "Level", "Logger", "Message", "Source"], rows, "NO LOG RECORDS WERE EMITTED"), logs.length);
  }

  function renderProblems(record) {
    const exceptions = record.exceptions || [];
    const exceptionContent = exceptions.length
      ? renderExceptions(record)
      : section("Exceptions", "HYPERDJANGO", emptyState("NO HYPERDJANGO EXCEPTIONS WERE CAPTURED"), 0);
    return `${exceptionContent}${renderLogs(record)}`;
  }

  function lifecycleMilestones(record) {
    const server = record.lifecycle || [];
    const client = record.client?.events || [];
    const firstServer = (kind) => server.find((event) => event.kind === kind);
    const lastServer = (kind) => [...server].reverse().find((event) => event.kind === kind);
    const lastClient = (kind) => [...client].reverse().find((event) => event.kind === kind);
    const milestones = [];
    const add = (title, detail, source, event, meta = "") => {
      if (!event && source !== "summary") return;
      milestones.push({ title, detail, source, at_ms: event?.at_ms, meta });
    };

    const request = record.request || {};
    const route = record.route || {};
    const action = record.action || {};
    const results = record.results || [];
    const streamResult = results.find((result) => result.streaming);
    const swaps = client.filter((event) => event.kind === "DOM swap");
    const requestStarted = firstServer("request started");
    const routeResolved = firstServer("route resolved");
    const actionDispatched = firstServer("action dispatched");
    const resultPrepared = firstServer("result prepared");
    const firstStreamItem = firstServer("SSE item");
    const streamFinished = lastServer("stream finished") || lastServer("response stream finished");
    const responsePrepared = lastServer("response prepared");
    const clientCompleted = lastClient("request completed");

    add(
      "Request received",
      `${request.method || "REQUEST"} ${request.full_path || request.path || "—"}`,
      "server",
      requestStarted,
    );
    add(
      "Route matched",
      `${route.name || "Unnamed route"} · ${route.handler || "Django handler"}`,
      "server",
      routeResolved,
    );
    if (action.name) {
      add(
        "Action selected",
        `${action.name}${action.target ? ` → ${action.target}` : ""}`,
        "server",
        actionDispatched,
      );
    }
    add(
      "Result prepared",
      streamResult
        ? `Streaming ${streamResult.kind || "result"}`
        : (results.flatMap((result) => result.item_types || []).join(", ") || "Django response"),
      "server",
      resultPrepared || responsePrepared,
    );
    if (streamResult) {
      const items = streamResult.items || [];
      add(
        streamFinished ? "Stream completed" : "Stream in progress",
        `${items.length} ${items.length === 1 ? "item" : "items"} · ${streamResult.iteration_status || "pending"}${firstStreamItem ? ` · first item ${formatDuration(firstStreamItem.at_ms)}` : ""}`,
        "server",
        streamFinished || firstStreamItem || resultPrepared,
      );
    }
    if (swaps.length) {
      add(
        "Browser updated the page",
        `${swaps.length} ${swaps.length === 1 ? "swap" : "swaps"} · +${swaps.reduce((sum, item) => sum + (item.added_total || 0), 0)} / −${swaps.reduce((sum, item) => sum + (item.removed_total || 0), 0)} / Δ${swaps.reduce((sum, item) => sum + (item.changed_total || 0), 0)} nodes`,
        "browser",
        swaps.at(-1),
      );
    }
    add(
      clientCompleted ? "Browser finished the request" : "Response ready",
      clientCompleted
        ? `${clientCompleted.event || "complete"}${responsePrepared ? ` · server response ${formatDuration(responsePrepared.at_ms)}` : ""}`
        : `${record.response?.status || "—"} response returned`,
      clientCompleted ? "browser" : "server",
      clientCompleted || responsePrepared,
    );
    return milestones;
  }

  function renderLifecycle(record) {
    const milestones = lifecycleMilestones(record);
    const rawCount = (record.lifecycle || []).length + (record.client?.events || []).length;
    const content = milestones.length
      ? `<div class="hdd-journey-note"><b>HOW TO READ THIS</b><span>Follow top to bottom. Server and browser clocks each start at their own request boundary, so compare order within a source—not milliseconds across sources.</span></div><ol class="hdd-journey">${milestones.map((milestone, index) => `<li><span class="hdd-journey-step">${index + 1}</span><div><small>${esc(milestone.source)}${milestone.at_ms === undefined ? "" : ` · ${esc(formatDuration(milestone.at_ms))}`}</small><b>${esc(milestone.title)}</b><p>${esc(milestone.detail)}</p></div></li>`).join("")}</ol>`
      : emptyState("NO REQUEST MILESTONES WERE CAPTURED");
    return section(
      "Request journey",
      `SERVER INTENT → BROWSER OUTCOME · ${rawCount} LOW-LEVEL EVENTS SUMMARIZED`,
      content,
      milestones.length,
    );
  }

  function renderRenders(record) {
    const renders = record.renders || [];
    const rows = renders.map((render, index) => [
      `<b>${index + 1}</b>`,
      badge(render.kind, "muted"),
      `<code>${esc(render.template)}</code>`,
      `<code>${esc(render.block || render.relative_template || "—")}</code>`,
      `<code>${esc(formatBytes(render.bytes))}</code>`,
      `<code>${esc(render.context_keys ?? "—")}</code>`,
      `<b>${esc(formatDuration(render.duration_ms))}</b>`,
      render.source ? sourceLink(render.source, "OPEN") : "—",
    ]);
    return section("Template operations", "RENDER TRACE", table(["#", "Kind", "Template", "Block / Relative", "Bytes", "Context keys", "Time", "Source"], rows, "NO TEMPLATE RENDERING WAS RECORDED"), renders.length);
  }

  function renderTimeline(record) {
    const timings = [...(record.timings || [])]
      .map((timing, index) => ({ ...timing, _index: index }))
      .sort((left, right) => {
        const startDifference = (Number(left.start_ms) || 0) - (Number(right.start_ms) || 0);
        return startDifference || (Number(right.duration_ms) || 0) - (Number(left.duration_ms) || 0);
      });
    let fallbackStart = 0;
    const positioned = timings.map((timing) => {
      const duration = Number(timing.duration_ms) || 0;
      const hasStart = Number.isFinite(Number(timing.start_ms));
      const start = hasStart ? Number(timing.start_ms) : fallbackStart;
      fallbackStart = Math.max(fallbackStart, start + duration);
      const end = Number.isFinite(Number(timing.end_ms)) ? Number(timing.end_ms) : start + duration;
      return { ...timing, _start: start, _end: end, _duration: duration };
    });
    const total = Math.max(
      Number(record.response?.request_duration_ms) || 0,
      ...positioned.map((timing) => timing._start + timing._duration),
      0.001,
    );
    const requestTiming = {
      phase: "request",
      parent: "—",
      depth: 0,
      _start: 0,
      _end: total,
      _duration: total,
      duration_ms: total,
      _request: true,
    };
    const dispatchTiming = positioned.find((timing) => timing.phase === "dispatch");
    const streamTiming = positioned.find((timing) => timing.phase === "stream iteration");
    const responseReady = Math.min(
      total,
      Math.max(
        dispatchTiming?._end || 0,
        Number(record.response?.response_ready_ms) || dispatchTiming?._end || total,
      ),
    );
    const contextIntervals = [];
    const addContextInterval = (phase, start, end, relation) => {
      if (!Number.isFinite(start) || !Number.isFinite(end) || end - start < 0.01) return;
      contextIntervals.push({
        phase,
        parent: "request",
        depth: 1,
        _start: start,
        _end: end,
        _duration: end - start,
        duration_ms: end - start,
        _context: true,
        _relation: relation,
      });
    };
    if (dispatchTiming) {
      addContextInterval(
        "django request pipeline",
        0,
        dispatchTiming._start,
        "middleware + URL resolution before HyperDjango dispatch",
      );
      addContextInterval(
        "django response pipeline",
        dispatchTiming._end,
        responseReady,
        "response middleware after HyperDjango dispatch",
      );
    }
    if (streamTiming) {
      addContextInterval(
        "stream handoff",
        responseReady,
        streamTiming._start,
        "response ready; waiting for the server to consume the stream",
      );
      addContextInterval(
        "request finalization",
        streamTiming._end,
        total,
        "post-stream instrumentation and cleanup",
      );
    } else if (record.response?.streaming && responseReady < total) {
      addContextInterval(
        "stream pending",
        responseReady,
        total,
        "response ready; exact stream iteration interval appears after completion",
      );
    } else if (responseReady < total) {
      addContextInterval(
        "request finalization",
        responseReady,
        total,
        "response instrumentation and cleanup",
      );
    }
    const phaseIntervals = [...positioned, ...contextIntervals].sort((left, right) => {
      const startDifference = left._start - right._start;
      return startDifference || right._duration - left._duration;
    });
    const topLevelCoverage = positioned
      .filter((timing) => (Number(timing.depth) || 1) === 1)
      .map((timing) => [timing._start, timing._end])
      .sort((left, right) => left[0] - right[0])
      .reduce((merged, interval) => {
        const previous = merged.at(-1);
        if (!previous || interval[0] > previous[1]) merged.push([...interval]);
        else previous[1] = Math.max(previous[1], interval[1]);
        return merged;
      }, []);
    const instrumentedMs = topLevelCoverage.reduce(
      (sum, interval) => sum + Math.max(0, interval[1] - interval[0]),
      0,
    );
    const coverage = Math.min(100, (instrumentedMs / total) * 100);
    const streamItems = (record.results || []).flatMap((result) => result.items || []).filter((item) => item.at_ms !== undefined);
    const scale = `<div class="hdd-waterfall-scale"><span>#</span><b>PHASE / PARENT</b><div><span>0</span><span>${esc(formatDuration(total / 2))}</span><span>${esc(formatDuration(total))}</span></div><code>START</code><code>END</code><code>DURATION</code></div>`;
    const rows = [requestTiming, ...phaseIntervals].map((timing, index) => {
      const left = Math.min(100, (timing._start / total) * 100);
      const width = Math.min(100 - left, (timing._duration / total) * 100);
      const recordedDepth = Math.max(0, Number(timing.depth) || 0);
      const containingTimings = timing._request || timing._context
        ? []
        : phaseIntervals
          .filter((candidate) =>
            candidate !== timing &&
            candidate._duration > timing._duration &&
            candidate._start <= timing._start &&
            candidate._end >= timing._end,
          )
          .sort((left, right) => left._duration - right._duration);
      const parentTiming = containingTimings.find(
        (candidate) => candidate.phase === timing.parent,
      ) || containingTimings[0] || null;
      const depth = parentTiming
        ? Math.max(recordedDepth, (Number(parentTiming.depth) || 1) + 1)
        : recordedDepth;
      const parentLeft = parentTiming ? Math.min(100, (parentTiming._start / total) * 100) : 0;
      const parentWidth = parentTiming
        ? Math.min(100 - parentLeft, (parentTiming._duration / total) * 100)
        : 0;
      const markers = timing.phase === "stream iteration"
        ? streamItems.map((item) => {
          const markerLeft = Math.min(100, Math.max(0, ((Number(item.at_ms) || 0) / total) * 100));
          return `<span class="hdd-waterfall-event" style="--hdd-event-left:${markerLeft}%" title="SSE ${esc(item.sequence || "—")} · ${esc(item.event || item.type || "item")} · ${esc(formatDuration(item.at_ms))}"></span>`;
        }).join("")
        : "";
      const relation = timing._request
        ? "complete middleware lifetime"
        : timing._relation || (parentTiming
          ? `inside ${parentTiming.phase}${parentTiming.phase === timing.parent ? "" : " (time containment)"}`
          : `inside ${timing.parent || "request"}`);
      return `<div class="hdd-timing"><span>${String(index + 1).padStart(2, "0")}</span><b style="--hdd-depth:${depth}"><span>${depth ? "↳ " : ""}${esc(
        timing.phase,
      )}</span><small title="${esc(relation)}">${esc(relation)}</small></b><div class="hdd-waterfall-track" title="${esc(timing.phase)}: ${esc(formatDuration(timing._start))} → ${esc(formatDuration(timing._end))}">${parentTiming ? `<span class="hdd-parent-interval" style="--hdd-parent-left:${parentLeft}%;--hdd-parent-width:${parentWidth}%"></span>` : ""}<i class="${timing._request ? "is-request" : timing._context ? "is-context" : ""}" style="--hdd-left:${left}%;--hdd-width:${width}%"></i>${markers}</div><code>${esc(formatDuration(timing._start))}</code><code>${esc(formatDuration(timing._end))}</code><code>${esc(formatDuration(timing.duration_ms))}</code></div>`;
    });
    const legend = `<div class="hdd-waterfall-legend"><span><i class="is-phase"></i>HYPERDJANGO PHASE</span><span><i class="is-context"></i>DJANGO / SERVER CONTEXT</span><span><i class="is-parent"></i>PARENT INTERVAL</span><b>${esc(coverage.toFixed(1))}% DIRECTLY INSTRUMENTED · ${esc((100 - coverage).toFixed(1))}% PIPELINE CONTEXT</b></div>`;
    return section("Execution waterfall", "EXPLICIT REQUEST-RELATIVE INTERVALS", positioned.length ? `<div class="hdd-waterfall">${legend}${scale}${rows.join("")}</div>` : emptyState("NO PHASE TIMINGS WERE RECORDED"), phaseIntervals.length);
  }

  function renderRequestResponse(record) {
    const request = record.request || {};
    const response = record.response || {};
    const requestSummary = {
      method: request.method,
      full_path: request.full_path,
      scheme: request.scheme,
      host: request.host,
      user: request.user,
      content_type: request.content_type,
      content_length: request.content_length,
      started_at: request.started_at,
    };
    const responseSummary = {
      status: response.status,
      content_type: response.content_type,
      content_length: response.content_length,
      streaming: response.streaming,
      stream_status: response.stream_status,
      request_duration_ms: response.request_duration_ms,
    };
    return `<div class="hdd-two-col">${section("Request", "INBOUND", table(["Field", "Value"], keyValueRows(requestSummary)))}${section(
      "Response",
      "OUTBOUND",
      table(["Field", "Value"], keyValueRows(responseSummary)),
    )}</div>${section("Query parameters", "SANITIZED", table(["Key", "Value"], keyValueRows(request.query || {})))}<div class="hdd-two-col">${section(
      "Request headers",
      "SANITIZED",
      table(["Header", "Value"], keyValueRows(request.headers || {})),
    )}${section("Response headers", "SANITIZED", table(["Header", "Value"], keyValueRows(response.headers || {})))}</div>`;
  }

  function renderExceptions(record) {
    const exceptions = record.exceptions || [];
    if (!exceptions.length) return emptyState("NO HYPERDJANGO EXCEPTIONS WERE CAPTURED");
    return exceptions.map((exception, index) => {
      const frames = exception.frames || [];
      const rows = frames.map((frame, frameIndex) => [
        `<b>${frameIndex + 1}</b>`,
        sourceLink(frame, "OPEN"),
        `<code>${esc(frame.function)}</code>`,
        `<pre class="hdd-code-frame">${esc(frame.source || "—")}</pre>`,
        `<code>${esc(display(frame.locals || {}))}</code>`,
      ]);
      return `${section(`Exception ${index + 1}`, exception.phase, table(["Field", "Value"], [
        ["Type", `<code>${esc(exception.type)}</code>`],
        ["Message", `<span>${esc(exception.message)}</span>`],
        ["Template", `<code>${esc(display(exception.template || {}))}</code>`],
      ]))}${section("Traceback frames", "SOURCE / SAFE LOCALS", table(["#", "Location", "Function", "Source", "Locals"], rows, "NO TRACEBACK FRAMES"), frames.length)}`;
    }).join("");
  }

  function detailUrl(id) {
    return `${historyUrl.replace(/history\/?$/, "requests/")}${encodeURIComponent(id)}/`;
  }

  function debugUrl(path) {
    return `${historyUrl.replace(/history\/?$/, "")}${path}`;
  }

  async function postJSON(url, value = {}) {
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(value),
    });
    if (!response.ok) throw new Error(`Debug endpoint returned ${response.status}`);
    return response.json();
  }

  async function togglePin(requestId) {
    if (!requestId) return;
    const record = state.history.find((item) => item.id === requestId);
    const previous = Boolean(record?.pinned);
    if (record) {
      record.pinned = !previous;
      renderHistory();
    }
    try {
      const result = await postJSON(debugUrl(`requests/${encodeURIComponent(requestId)}/pin/`));
      const current = state.history.find((item) => item.id === requestId);
      if (current) current.pinned = Boolean(result.pinned);
      renderHistory();
    } catch (error) {
      const current = state.history.find((item) => item.id === requestId);
      if (current) current.pinned = previous;
      renderHistory();
      console.error("HyperDjango trace pin failed", error);
    }
  }

  async function togglePause() {
    const result = await postJSON(debugUrl("controls/pause/"));
    state.paused = Boolean(result.paused);
    renderHistory();
  }

  async function clearHistory() {
    await postJSON(debugUrl("controls/clear/"));
    const current = state.history.find((item) => item.id === state.currentId);
    if (!current?.pinned) {
      state.currentId = null;
      state.record = null;
    }
    await loadHistory();
    renderRecord();
  }

  async function replayAction() {
    const record = state.record;
    if (!record?.action?.name || !window.Hyper?.action) return;
    const method = record.request?.method || "POST";
    const mutating = !["GET", "HEAD", "OPTIONS"].includes(method);
    const hasRedactions = JSON.stringify(record.action.arguments || {}).includes("[redacted]");
    const warning = `${mutating ? "This will repeat a mutating request. " : ""}${hasRedactions ? "Redacted values will be replayed as placeholders. " : ""}Replay ${record.action.name}?`;
    if (!window.confirm(warning)) return;
    await window.Hyper.action(record.action.name, record.action.arguments || {}, {
      url: record.request.full_path || record.request.path,
      method,
    });
  }

  function highlightDomElement(selector, button) {
    let matches;
    try {
      matches = document.querySelectorAll(selector);
    } catch {
      matches = [];
    }
    if (matches.length !== 1) {
      const previous = button.innerHTML;
      const previousLabel = button.getAttribute("aria-label");
      const previousTitle = button.title;
      button.innerHTML = '<span aria-hidden="true">!</span>';
      const message = matches.length
        ? `${matches.length} DOM elements match; exact element unavailable`
        : "DOM element not found";
      button.setAttribute("aria-label", message);
      button.title = message;
      button.disabled = true;
      window.setTimeout(() => {
        button.innerHTML = previous;
        button.setAttribute("aria-label", previousLabel);
        button.title = previousTitle;
        button.disabled = false;
      }, 1400);
      return;
    }
    const [element] = matches;

    setToolbarOpen(false);
    const closeDuration = window.matchMedia("(prefers-reduced-motion: reduce)").matches
      ? 0
      : 240;
    window.setTimeout(() => {
      const currentMatches = element.isConnected ? [element] : document.querySelectorAll(selector);
      const currentElement = currentMatches.length === 1 ? currentMatches[0] : null;
      if (!currentElement) return;
      currentElement.scrollIntoView({ behavior: "auto", block: "center", inline: "center" });
      const rect = currentElement.getBoundingClientRect();
      const marker = document.createElement("div");
      marker.setAttribute("data-hyperdjango-dom-highlight", "");
      Object.assign(marker.style, {
        position: "fixed",
        zIndex: "2147482999",
        pointerEvents: "none",
        left: `${Math.max(0, rect.left - 5)}px`,
        top: `${Math.max(0, rect.top - 5)}px`,
        width: `${Math.max(10, rect.width + 10)}px`,
        height: `${Math.max(10, rect.height + 10)}px`,
        border: "3px solid #1764d7",
        background: "transparent",
        outline: "2px solid white",
        boxShadow: "0 0 0 5px rgba(23, 100, 215, 0.35), 0 0 0 9999px rgba(0, 0, 0, 0.58)",
        opacity: "1",
        transition: "opacity 180ms linear",
      });
      document.documentElement.appendChild(marker);
      window.setTimeout(() => { marker.style.opacity = "0"; }, 1200);
      window.setTimeout(() => marker.remove(), 1450);
    }, closeDuration);
  }

  async function copyToClipboard(value, button) {
    if (!button || value === undefined) return;
    const previous = button.innerHTML;
    const previousLabel = button.getAttribute("aria-label");
    const previousTitle = button.title;
    try {
      if (navigator.clipboard?.writeText && window.isSecureContext) {
        await navigator.clipboard.writeText(value);
      } else {
        const textarea = document.createElement("textarea");
        textarea.value = value;
        textarea.setAttribute("readonly", "");
        Object.assign(textarea.style, { position: "fixed", opacity: "0", pointerEvents: "none" });
        root.appendChild(textarea);
        textarea.select();
        const copied = document.execCommand("copy");
        textarea.remove();
        if (!copied) throw new Error("Copy command was rejected");
      }
      button.classList.add("is-copied");
      button.innerHTML = '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="m3 8 3 3 7-7"></path></svg>';
      button.setAttribute("aria-label", "Copied");
      button.title = "Copied";
    } catch {
      button.classList.add("is-copy-error");
      button.innerHTML = '<span aria-hidden="true">!</span>';
      button.setAttribute("aria-label", "Copy failed");
      button.title = "Copy failed";
    }
    window.setTimeout(() => {
      button.classList.remove("is-copied", "is-copy-error");
      button.innerHTML = previous;
      button.setAttribute("aria-label", previousLabel);
      button.title = previousTitle;
    }, 1200);
  }

  async function loadHistory() {
    if (!historyUrl) return;
    try {
      const response = await fetch(historyUrl, { headers: { Accept: "application/json" } });
      if (!response.ok) throw new Error(`History returned ${response.status}`);
      const payload = await response.json();
      state.history = payload.records || [];
      state.paused = Boolean(payload.paused);
      renderHistory();
    } catch (error) {
      slots.history.innerHTML = emptyState(error.message);
    }
  }

  function streamIsPending(record) {
    const terminal = ["completed", "closed", "failed"];
    if (
      record?.response?.streaming &&
      !terminal.includes(record.response.stream_status)
    ) {
      return true;
    }
    return (record?.results || []).some(
      (result) =>
        result.streaming &&
        !terminal.includes(result.iteration_status),
    );
  }

  async function select(id, { background = false } = {}) {
    if (!id || !historyUrl) return;
    window.clearTimeout(state.pollTimer);
    state.pollTimer = null;
    const selectionVersion = ++state.selectionVersion;
    state.currentId = id;
    state.loading = !background;
    renderHistory();
    if (!background) renderRecord();
    try {
      const response = await fetch(detailUrl(id), { headers: { Accept: "application/json" } });
      if (!response.ok) throw new Error(`Trace returned ${response.status}`);
      if (selectionVersion !== state.selectionVersion) return;
      state.record = (await response.json()).record;
    } catch (error) {
      if (selectionVersion !== state.selectionVersion) return;
      state.record = null;
      updatePanel(emptyState(error.message));
    } finally {
      if (selectionVersion !== state.selectionVersion) return;
      state.loading = false;
      await loadHistory();
      if (selectionVersion !== state.selectionVersion) return;
      renderRecord({ preservePanelState: background });
      if (streamIsPending(state.record)) {
        state.pollTimer = window.setTimeout(
          () => select(id, { background: true }),
          350,
        );
      }
    }
  }

  root.addEventListener("click", (event) => {
    const action = event.target.closest("[data-action]")?.dataset.action;
    const tab = event.target.closest("[data-tab]")?.dataset.tab;
    const requestId = event.target.closest("[data-request-id]")?.dataset.requestId;
    const pinRequestId = event.target.closest("[data-pin-request-id]")?.dataset.pinRequestId;
    if (action === "toggle") {
      if (state.suppressLauncherClick) return;
      setToolbarOpen(!state.open);
    } else if (action === "fullscreen") {
      state.fullscreen = !state.fullscreen;
      renderShellState();
    } else if (action === "refresh") {
      loadHistory();
      if (state.currentId) select(state.currentId);
    } else if (action === "pause") {
      togglePause();
    } else if (action === "clear") {
      clearHistory();
    } else if (action === "pin-request") {
      togglePin(pinRequestId);
    } else if (action === "replay") {
      replayAction();
    } else if (action === "highlight-dom") {
      const button = event.target.closest("[data-dom-selector]");
      highlightDomElement(button?.dataset.domSelector, button);
    } else if (action === "copy") {
      const button = event.target.closest("[data-copy-value]");
      copyToClipboard(button?.dataset.copyValue, button);
    } else if (action === "tab-prev" || action === "tab-next") {
      const direction = action === "tab-next" ? 1 : -1;
      slots.tabs.scrollBy({ left: direction * Math.max(160, slots.tabs.clientWidth * 0.65) });
      requestAnimationFrame(updateTabOverflow);
    } else if (tab) {
      activateTab(tab);
    } else if (requestId) {
      select(requestId);
    }
  });

  slots.search.addEventListener("input", (event) => {
    state.query = event.target.value;
    renderHistory();
  });

  slots.filter.addEventListener("change", (event) => {
    state.filter = event.target.value;
    renderHistory();
  });

  slots["tab-select"].addEventListener("change", (event) => {
    activateTab(event.target.value, { focus: false });
  });

  slots.tabs.addEventListener("wheel", (event) => {
    if (!event.deltaY || event.deltaX) return;
    event.preventDefault();
    slots.tabs.scrollLeft += event.deltaY;
    updateTabOverflow();
  }, { passive: false });

  slots.tabs.addEventListener("scroll", updateTabOverflow, { passive: true });

  slots.tabs.addEventListener("keydown", (event) => {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    const buttons = [...slots.tabs.querySelectorAll("[role='tab']")];
    const current = buttons.indexOf(event.target.closest("[role='tab']"));
    if (current < 0) return;
    event.preventDefault();
    const next = event.key === "Home"
      ? 0
      : event.key === "End"
        ? buttons.length - 1
        : (current + (event.key === "ArrowRight" ? 1 : -1) + buttons.length) % buttons.length;
    const tab = buttons[next]?.dataset.tab;
    if (!tab) return;
    activateTab(tab);
  });

  let launcherDrag = null;
  launcherGrip.addEventListener("pointerdown", (event) => {
    if (event.button !== 0) return;
    const rect = slots.launcher.getBoundingClientRect();
    launcherDrag = { pointerId: event.pointerId, startX: event.clientX, left: rect.left };
    launcherGrip.setPointerCapture(event.pointerId);
    slots.launcher.classList.add("is-dragging");
    event.preventDefault();
  });

  launcherGrip.addEventListener("pointermove", (event) => {
    if (!launcherDrag || launcherDrag.pointerId !== event.pointerId) return;
    setLauncherX(launcherDrag.left + event.clientX - launcherDrag.startX);
  });

  function finishLauncherDrag(event) {
    if (!launcherDrag || launcherDrag.pointerId !== event.pointerId) return;
    setLauncherX(state.launcherX, { persist: true });
    slots.launcher.classList.remove("is-dragging");
    launcherDrag = null;
    state.suppressLauncherClick = true;
    window.setTimeout(() => { state.suppressLauncherClick = false; }, 0);
  }

  launcherGrip.addEventListener("pointerup", finishLauncherDrag);
  launcherGrip.addEventListener("pointercancel", finishLauncherDrag);
  launcherGrip.addEventListener("keydown", (event) => {
    if (!['ArrowLeft', 'ArrowRight'].includes(event.key)) return;
    event.preventDefault();
    setLauncherX(state.launcherX + (event.key === 'ArrowLeft' ? -24 : 24), { persist: true });
  });
  window.addEventListener("resize", () => {
    setLauncherX(state.launcherX);
    updateTabOverflow();
  });

  window.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && state.fullscreen) {
      state.fullscreen = false;
      renderShellState();
      return;
    }
    if (event.key === "Escape" && state.open) {
      setToolbarOpen(false);
      return;
    }
    if (event.ctrlKey && event.shiftKey && event.key.toLowerCase() === "h") {
      event.preventDefault();
      setToolbarOpen(!state.open);
    }
  });

  const clientRequests = new Map();
  const actionSwitchLinks = new Map();

  function activeClientRequest(action = null) {
    const requests = [...clientRequests.values()].reverse();
    return requests.find((request) => !action || request.action === action) || requests[0] || null;
  }

  function clientAt(request) {
    return Math.round((performance.now() - request.started) * 1000) / 1000;
  }

  function focusLabel() {
    const active = document.activeElement;
    if (!active) return null;
    return active.id ? `#${active.id}` : active.getAttribute?.("name") || active.tagName?.toLowerCase();
  }

  function uniqueElementSelector(element) {
    if (!(element instanceof Element) || element.closest("hyperdjango-debug-toolbar")) return null;
    const unique = (selector) => {
      try {
        return document.querySelectorAll(selector).length === 1;
      } catch {
        return false;
      }
    };
    if (element.id) {
      const idSelector = `#${CSS.escape(element.id)}`;
      if (unique(idSelector)) return idSelector;
    }
    const parts = [];
    let current = element;
    while (current && current !== document.documentElement) {
      if (current.id) {
        const idSelector = `#${CSS.escape(current.id)}`;
        if (unique(idSelector)) {
          parts.unshift(idSelector);
          break;
        }
      }
      const parent = current.parentElement;
      let part = current.tagName.toLowerCase();
      if (parent) {
        const siblings = [...parent.children].filter((sibling) => sibling.tagName === current.tagName);
        if (siblings.length > 1) part += `:nth-of-type(${siblings.indexOf(current) + 1})`;
      }
      parts.unshift(part);
      current = parent;
    }
    const selector = parts.join(" > ");
    return selector && unique(selector) ? selector : null;
  }

  function focusSelector() {
    return uniqueElementSelector(document.activeElement);
  }

  const DOM_SNAPSHOT_LIMIT = 160;
  const DOM_DIFF_LIMIT = 30;

  function boundedClientText(value, limit = 240) {
    const text = String(value || "");
    return text.length > limit ? `${text.slice(0, limit - 1)}…` : text;
  }

  function elementLabel(element) {
    if (!(element instanceof Element)) return null;
    const id = element.id ? `#${CSS.escape(element.id)}` : "";
    const classes = [...element.classList].filter((name) => !name.startsWith("hyper-")).slice(0, 3).map((name) => CSS.escape(name));
    return `${element.tagName.toLowerCase()}${id}${classes.length ? `.${classes.join(".")}` : ""}`;
  }

  function nodePath(node, rootElement) {
    if (node === rootElement) return ":scope";
    const parts = [];
    let current = node;
    while (current && current !== rootElement) {
      const parent = current.parentElement;
      if (!parent) break;
      parts.unshift(`${current.tagName.toLowerCase()}:nth-child(${[...parent.children].indexOf(current) + 1})`);
      current = parent;
    }
    return parts.join(" > ");
  }

  function snapshotTree(element) {
    if (!element) return { nodes: [], truncated: false };
    const all = [element, ...element.querySelectorAll("*")];
    const nodes = all.slice(0, DOM_SNAPSHOT_LIMIT).map((node) => {
      const attributes = [...node.attributes]
        .flatMap((attribute) => {
          if (attribute.name !== "class") return [`${attribute.name}=${JSON.stringify(attribute.value)}`];
          const value = attribute.value.split(/\s+/).filter((name) => name && !name.startsWith("hyper-")).join(" ");
          return value ? [`class=${JSON.stringify(value)}`] : [];
        })
        .sort();
      const text = boundedClientText(
        [...node.childNodes].filter((child) => child.nodeType === Node.TEXT_NODE).map((child) => child.textContent).join(" ").replace(/\s+/g, " ").trim(),
        100,
      );
      return {
        key: nodePath(node, element),
        label: elementLabel(node),
        tag: node.tagName.toLowerCase(),
        attributes: attributes.join(" "),
        text,
      };
    });
    return { nodes, truncated: all.length > DOM_SNAPSHOT_LIMIT };
  }

  function duplicateIds(element) {
    if (!element) return [];
    const counts = new Map();
    [element, ...element.querySelectorAll("[id]")].slice(0, 500).forEach((node) => {
      if (node.id) counts.set(node.id, (counts.get(node.id) || 0) + 1);
    });
    return [...counts.entries()].filter(([, count]) => count > 1).map(([id, count]) => `#${id} ×${count}`).slice(0, DOM_DIFF_LIMIT);
  }

  function targetSnapshot(target) {
    if (!target || typeof target !== "string") return { exists: false, matches: 0, nodes: 0, bytes: 0, tree: { nodes: [], truncated: false }, duplicate_ids: [] };
    try {
      const matches = document.querySelectorAll(target);
      const element = matches[0] || null;
      return { ...elementSnapshot(element), matches: matches.length, selector: uniqueElementSelector(element) };
    } catch (error) {
      return { exists: false, matches: 0, nodes: 0, bytes: 0, tree: { nodes: [], truncated: false }, duplicate_ids: [], error: error.message };
    }
  }

  function elementSnapshot(element) {
    return {
      exists: Boolean(element),
      matches: element ? 1 : 0,
      nodes: element ? element.querySelectorAll("*").length + 1 : 0,
      bytes: element ? new TextEncoder().encode(element.outerHTML || "").length : 0,
      tree: snapshotTree(element),
      duplicate_ids: duplicateIds(element),
    };
  }

  function diffSnapshots(before, after) {
    const beforeNodes = new Map((before?.tree?.nodes || []).map((node) => [node.key, node]));
    const afterNodes = new Map((after?.tree?.nodes || []).map((node) => [node.key, node]));
    const added = [];
    const removed = [];
    const changed = [];
    afterNodes.forEach((node, key) => {
      if (!beforeNodes.has(key)) {
        added.push(`${key} · ${node.label}`);
        return;
      }
      const previous = beforeNodes.get(key);
      const differences = [];
      if (previous.tag !== node.tag) differences.push(`tag <${previous.tag}> → <${node.tag}>`);
      if (previous.attributes !== node.attributes) differences.push(`attributes ${previous.attributes || "∅"} → ${node.attributes || "∅"}`);
      if (previous.text !== node.text) differences.push(`text ${JSON.stringify(previous.text)} → ${JSON.stringify(node.text)}`);
      if (differences.length) changed.push(`${key} · ${node.label}: ${differences.join("; ")}`);
    });
    beforeNodes.forEach((node, key) => {
      if (!afterNodes.has(key)) removed.push(`${key} · ${node.label}`);
    });
    return {
      added_total: added.length,
      removed_total: removed.length,
      changed_total: changed.length,
      added_nodes: added.slice(0, DOM_DIFF_LIMIT),
      removed_nodes: removed.slice(0, DOM_DIFF_LIMIT),
      changed_nodes: changed.slice(0, DOM_DIFF_LIMIT),
      diff_truncated: Boolean(before?.tree?.truncated || after?.tree?.truncated || added.length > DOM_DIFF_LIMIT || removed.length > DOM_DIFF_LIMIT || changed.length > DOM_DIFF_LIMIT),
    };
  }

  function mutationPath(node) {
    const element = node instanceof Element ? node : node?.parentElement;
    if (!element || element.closest("hyperdjango-debug-toolbar")) return null;
    return nodePath(element, document.documentElement) || elementLabel(element);
  }

  function observeRequestMutations(request) {
    const mutations = {
      added_total: 0,
      removed_total: 0,
      changed_total: 0,
      added_nodes: [],
      removed_nodes: [],
      changed_nodes: [],
    };
    request.mutations = mutations;
    const collect = (records) => {
      records.forEach((record) => {
        const path = mutationPath(record.target);
        if (!path) return;
        if (record.type === "childList") {
          record.addedNodes.forEach((node) => {
            if (node.nodeType === Node.TEXT_NODE && !String(node.textContent || "").trim()) return;
            mutations.added_total += 1;
            if (mutations.added_nodes.length < DOM_DIFF_LIMIT) mutations.added_nodes.push(`${path} · ${node instanceof Element ? elementLabel(node) : `text ${JSON.stringify(boundedClientText(node.textContent, 100))}`}`);
          });
          record.removedNodes.forEach((node) => {
            if (node.nodeType === Node.TEXT_NODE && !String(node.textContent || "").trim()) return;
            mutations.removed_total += 1;
            if (mutations.removed_nodes.length < DOM_DIFF_LIMIT) mutations.removed_nodes.push(`${path} · ${node instanceof Element ? elementLabel(node) : `text ${JSON.stringify(boundedClientText(node.textContent, 100))}`}`);
          });
        } else if (record.type === "attributes") {
          const normalizeAttribute = (value) => record.attributeName === "class" && value
            ? value.split(/\s+/).filter((name) => name && !name.startsWith("hyper-")).join(" ")
            : value;
          const current = normalizeAttribute(record.target.getAttribute(record.attributeName));
          const previous = normalizeAttribute(record.oldValue);
          if (previous === current) return;
          mutations.changed_total += 1;
          if (mutations.changed_nodes.length < DOM_DIFF_LIMIT) mutations.changed_nodes.push(`${path} · attribute ${record.attributeName}: ${JSON.stringify(previous)} → ${JSON.stringify(current)}`);
        } else if (record.type === "characterData") {
          const current = boundedClientText(record.target.textContent, 100);
          const previous = boundedClientText(record.oldValue, 100);
          if (previous === current) return;
          mutations.changed_total += 1;
          if (mutations.changed_nodes.length < DOM_DIFF_LIMIT) mutations.changed_nodes.push(`${path} · text ${JSON.stringify(previous)} → ${JSON.stringify(current)}`);
        }
      });
    };
    request.collectMutations = collect;
    request.observer = new MutationObserver(collect);
    request.observer.observe(document.documentElement, {
      subtree: true,
      childList: true,
      attributes: true,
      attributeOldValue: true,
      characterData: true,
      characterDataOldValue: true,
    });
  }

  function pushClientEvent(request, value) {
    if (!request || request.events.length >= 200) return;
    request.events.push({ at_ms: clientAt(request), ...value });
  }

  window.addEventListener("hyper:beforeRequest", (event) => {
    const detail = event.detail || {};
    const request = {
      id: detail.id,
      action: detail.action || null,
      started: performance.now(),
      events: [],
      swaps: [],
      streamSequence: 0,
      trigger_kind: detail.kind || "request",
      trigger_element: elementLabel(detail.sourceEl),
      trigger_element_selector: uniqueElementSelector(detail.sourceEl),
      target: detail.target || null,
      method: detail.method || null,
      url: detail.url || null,
      initialFocus: focusLabel(),
      initialFocusSelector: focusSelector(),
      initialTargetSnapshot: detail.target ? targetSnapshot(detail.target) : null,
      action_chain: actionSwitchLinks.get(detail.id) || null,
    };
    const reactiveRoot = detail.sourceEl?.closest?.("[x-data]");
    request.scopeElement = reactiveRoot?.parentElement || detail.sourceEl?.closest?.("section, form, li") || document.body;
    request.initialScopeSnapshot = elementSnapshot(request.scopeElement);
    clientRequests.set(detail.id, request);
    observeRequestMutations(request);
    pushClientEvent(request, {
      kind: "browser trigger",
      event: detail.kind || "request",
      action: detail.action || null,
      target: detail.target || null,
      source: elementLabel(detail.sourceEl),
      source_selector: uniqueElementSelector(detail.sourceEl),
    });
  });

  window.addEventListener("hyper:streamEvent", (event) => {
    const detail = event.detail || {};
    const request = clientRequests.get(detail.requestId) || activeClientRequest(detail.action);
    if (!request) return;
    request.streamSequence += 1;
    request.lastStreamSequence = request.streamSequence;
    const data = detail.data || {};
    pushClientEvent(request, {
      kind: "stream event",
      event: detail.event,
      sequence: request.streamSequence,
      target: data.target || null,
      swap: data.swap || null,
      name: data.name || null,
      url: data.url || null,
      content_bytes: typeof data.content === "string" ? new TextEncoder().encode(data.content).length : 0,
      payload_bytes: new TextEncoder().encode(JSON.stringify(data)).length,
    });
  });

  window.addEventListener("hyper:actionSwitch", (event) => {
    const detail = event.detail || {};
    const link = {
      parent_request_id: detail.originalRequestId || null,
      request_id: detail.newRequestId || null,
      source_action: detail.originalAction || null,
      destination_action: detail.destinationAction || null,
      key: detail.key || null,
      method: detail.method || null,
      url: detail.url || null,
      retry: Boolean(detail.retry),
      switch_depth: detail.depth || 0,
    };
    if (link.request_id) actionSwitchLinks.set(link.request_id, link);
    const request = clientRequests.get(link.parent_request_id);
    pushClientEvent(request, {
      kind: "action switch",
      event: `${link.source_action || "?"} → ${link.destination_action || "?"} · ${link.parent_request_id || "?"} → ${link.request_id || "?"}`,
      ...link,
    });
  });

  window.addEventListener("hyper:swap:start", (event) => {
    const detail = event.detail || {};
    const request = activeClientRequest(detail.action);
    if (!request) return;
    request.swaps.push({
      target: detail.target,
      swap: detail.swap,
      started: performance.now(),
      before: targetSnapshot(detail.target),
      focus: focusLabel(),
      focus_selector: focusSelector(),
    });
  });

  window.addEventListener("hyper:swap:end", (event) => {
    const detail = event.detail || {};
    const request = activeClientRequest(detail.action);
    if (!request) return;
    const swap = [...request.swaps].reverse().find((item) => item.target === detail.target && !item.finished);
    const after = targetSnapshot(detail.target);
    if (swap) swap.finished = true;
    const diff = diffSnapshots(swap?.before, after);
    pushClientEvent(request, {
      kind: "DOM swap",
      target: detail.target,
      target_selector: after.selector || swap?.before.selector || null,
      swap: detail.swap,
      source_sequence: request.lastStreamSequence || null,
      target_existed_before: Boolean(swap?.before.exists),
      target_existed_after: Boolean(after.exists),
      target_matches_before: swap?.before.matches || 0,
      target_matches_after: after.matches || 0,
      duration_ms: swap ? Math.round((performance.now() - swap.started) * 1000) / 1000 : null,
      ...diff,
      bytes_before: swap?.before.bytes || 0,
      bytes_after: after.bytes,
      duplicate_ids: after.duplicate_ids,
      focus_before: swap?.focus || null,
      focus_before_selector: swap?.focus_selector || null,
      focus_after: focusLabel(),
      focus_after_selector: focusSelector(),
      error: after.error || swap?.before.error || null,
    });
  });

  window.addEventListener("hyper:requestError", (event) => {
    const detail = event.detail || {};
    const request = clientRequests.get(detail.id) || activeClientRequest(detail.action);
    pushClientEvent(request, {
      kind: "request error",
      target: detail.target,
      error: detail.error?.message || detail.message || `HTTP ${detail.status || "error"}`,
    });
    if (Number(detail.status) >= 500) showDjangoErrorOverlay(detail);
  });

  async function showDjangoErrorOverlay(detail) {
    if (!viteUrl || document.querySelector("vite-error-overlay")) return;
    const requestId = detail.response?.headers?.get("X-HyperDjango-Debug-ID");
    if (!requestId) return;
    try {
      const [traceResponse, viteClient] = await Promise.all([
        fetch(detailUrl(requestId), { headers: { Accept: "application/json" } }),
        import(`${viteUrl}@vite/client`),
      ]);
      if (!traceResponse.ok || !viteClient.ErrorOverlay) return;
      const record = (await traceResponse.json()).record || {};
      const exception = (record.exceptions || []).at(-1);
      if (!exception) return;
      const frames = exception.frames || [];
      const firstFrame = frames[0] || {};
      const stack = frames.map((frame) =>
        `${frame.file || frame.display_file || "unknown"}:${frame.line || 1}:1 in ${frame.function || "<module>"}`,
      ).join("\n");
      const overlay = new viteClient.ErrorOverlay({
        message: `${exception.type}: ${exception.message}`,
        stack,
        plugin: "hyperdjango",
        id: firstFrame.file || firstFrame.display_file || "Django request",
        loc: firstFrame.file ? {
          file: firstFrame.file,
          line: Number(firstFrame.line) || 1,
          column: 1,
        } : undefined,
      });
      document.body.appendChild(overlay);
    } catch (error) {
      console.warn("HyperDjango could not show the Vite error overlay", error);
    }
  }

  const runtimeEventKinds = {
    "hyper:requestRetry": "stream retry",
    "hyper:requestRetriesFailed": "retries failed",
    "hyper:requestAborted": "request aborted",
    "hyper:requestBlocked": "request blocked",
    "hyper:requestReplaced": "request replaced",
    "hyper:requestException": "request exception",
  };
  Object.entries(runtimeEventKinds).forEach(([eventName, kind]) => {
    window.addEventListener(eventName, (event) => {
      const detail = event.detail || {};
      const request = clientRequests.get(detail.id) || activeClientRequest(detail.action);
      pushClientEvent(request, {
        kind,
        action: detail.action || null,
        target: detail.target || null,
        attempt: detail.attempt ?? detail.attempts ?? null,
        delay: detail.delay ?? null,
        error: detail.error?.message || null,
        mode: detail.mode || null,
      });
    });
  });

  window.addEventListener("hyper:afterRequest", async (event) => {
    const detail = event.detail || {};
    const id = event.detail?.response?.headers?.get("X-HyperDjango-Debug-ID");
    const request = clientRequests.get(detail.id);
    if (id && request) {
      await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      request.collectMutations?.(request.observer?.takeRecords() || []);
      request.observer?.disconnect();
      const observed = request.mutations || {};
      const finalScope = request.scopeElement?.isConnected ? request.scopeElement : document.body;
      const finalScopeSnapshot = elementSnapshot(finalScope);
      const snapshotDiff = diffSnapshots(request.initialScopeSnapshot, finalScopeSnapshot);
      const fallbackDiff = (observed.added_total || observed.removed_total || observed.changed_total) ? observed : snapshotDiff;
      if (!request.events.some((item) => item.kind === "DOM swap") && (fallbackDiff.added_total || fallbackDiff.removed_total || fallbackDiff.changed_total)) {
        const finalTargetSnapshot = request.target ? targetSnapshot(request.target) : null;
        pushClientEvent(request, {
          kind: "DOM swap",
          target: request.target || elementLabel(finalScope) || "document (observed)",
          target_selector: finalTargetSnapshot?.selector || uniqueElementSelector(finalScope),
          swap: "observed",
          target_existed_before: request.initialTargetSnapshot ? request.initialTargetSnapshot.exists : true,
          target_existed_after: finalTargetSnapshot ? finalTargetSnapshot.exists : true,
          target_matches_before: request.initialTargetSnapshot ? request.initialTargetSnapshot.matches : 1,
          target_matches_after: finalTargetSnapshot ? finalTargetSnapshot.matches : 1,
          duration_ms: clientAt(request),
          ...fallbackDiff,
          bytes_before: request.initialScopeSnapshot.bytes,
          bytes_after: finalScopeSnapshot.bytes,
          duplicate_ids: finalScopeSnapshot.duplicate_ids,
          focus_before: request.initialFocus || null,
          focus_before_selector: request.initialFocusSelector || null,
          focus_after: focusLabel(),
          focus_after_selector: focusSelector(),
          observed_fallback: true,
        });
      }
      pushClientEvent(request, {
        kind: "request completed",
        event: detail.aborted ? "aborted" : detail.ok ? "success" : "failed",
      });
      const swaps = request.events.filter((item) => item.kind === "DOM swap");
      try {
        await postJSON(debugUrl(`requests/${encodeURIComponent(id)}/client/`), {
          events: request.events,
          summary: {
            duration_ms: clientAt(request),
            swaps: swaps.length,
            nodes_added: swaps.reduce((total, item) => total + (item.added_total || 0), 0),
            nodes_removed: swaps.reduce((total, item) => total + (item.removed_total || 0), 0),
            nodes_changed: swaps.reduce((total, item) => total + (item.changed_total || 0), 0),
            errors: request.events.filter((item) => item.error).length,
            final_focus: focusLabel(),
            final_focus_selector: focusSelector(),
            trigger_kind: request.trigger_kind,
            trigger_element: request.trigger_element,
            trigger_element_selector: request.trigger_element_selector,
            trigger_action: request.action,
            trigger_target: request.target,
            request_method: request.method,
            request_url: request.url,
            action_chain: request.action_chain,
          },
        });
      } catch (error) {
        console.error("HyperDjango debug client trace failed", error);
      }
      clientRequests.delete(detail.id);
    }
    if (id) select(id);
  });

  window.__hyperdjangoDevtools = { select, refresh: loadHistory };
  async function initializeToolbar() {
    restoreLauncherX();
    renderShellState();
    renderTabs();
    renderHistory();
    renderRecord();
    if (initialId) {
      await select(initialId);
    } else {
      await loadHistory();
    }
    toolbarReady = true;
    revealHostWhenReady();
  }
  initializeToolbar();
})();
