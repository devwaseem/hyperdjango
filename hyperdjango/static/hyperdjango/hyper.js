const Hyper = (() => {
  let pendingRequests = 0;
  const loadingTimers = new WeakMap();
  const originalDisabledState = new WeakMap();
  const inFlightRequests = new Map();
  let activeGlobalRequests = 0;
  const activeByKey = new Map();
  const activeByAction = new Map();
  const activeByTarget = new Map();
  const loadedModuleScripts = new Map();
  const config = {
    strictTargets: false,
  };

  function emitEvent(name, detail) {
    window.dispatchEvent(new CustomEvent(name, { detail }));
  }

  function configure(next = {}) {
    if (!next || typeof next !== "object") {
      return { ...config };
    }
    if (Object.prototype.hasOwnProperty.call(next, "strictTargets")) {
      config.strictTargets = Boolean(next.strictTargets);
    }
    return { ...config };
  }

  function strictTargetsEnabled(local = undefined) {
    if (typeof local === "boolean") {
      return local;
    }
    const attr = (document.body && document.body.getAttribute("hyper-strict-targets")) || "";
    if (attr) {
      return ["1", "true", "yes", "on"].includes(attr.toLowerCase());
    }
    return Boolean(config.strictTargets);
  }

  function normalizeSyncMode(mode) {
    const value = String(mode || "replace").toLowerCase();
    if (value === "block") {
      return "block";
    }
    if (value === "none") {
      return "none";
    }
    return "replace";
  }

  function resolveRequestKey({ key = null, hookMeta = {}, url = "" }) {
    if (key) {
      return String(key);
    }
    if (hookMeta.kind === "action" && hookMeta.action) {
      return `action:${hookMeta.action}`;
    }
    if (hookMeta.kind === "visit") {
      return `visit:${hookMeta.target || "body"}`;
    }
    if (hookMeta.kind === "nav-form") {
      return `nav-form:${hookMeta.target || "body"}`;
    }
    return url || "global";
  }

  function loadingElements() {
    return Array.from(document.querySelectorAll("[hyper-loading]"));
  }

  function loadingDisableElements() {
    return Array.from(document.querySelectorAll("[hyper-loading-disable]"));
  }

  function incrementMapCount(map, key) {
    if (!key) {
      return;
    }
    map.set(key, (map.get(key) || 0) + 1);
  }

  function targetBusyElements() {
    return Array.from(document.querySelectorAll("[hyper-target-busy]"));
  }

  function setTargetBusyStates() {
    for (const [selector, count] of activeByTarget.entries()) {
      const el = document.querySelector(selector);
      if (!el) {
        continue;
      }
      if (count > 0) {
        el.setAttribute("aria-busy", "true");
      } else {
        el.removeAttribute("aria-busy");
      }
    }

    for (const el of targetBusyElements()) {
      const selector = (el.getAttribute("hyper-target-busy") || "").trim();
      if (!selector) {
        continue;
      }
      const busy = (activeByTarget.get(selector) || 0) > 0;
      if (busy) {
        el.setAttribute("aria-busy", "true");
      } else {
        el.removeAttribute("aria-busy");
      }
    }
  }

  function decrementMapCount(map, key) {
    if (!key) {
      return;
    }
    const next = (map.get(key) || 0) - 1;
    if (next <= 0) {
      map.delete(key);
      return;
    }
    map.set(key, next);
  }

  function parseLoadingScope(el, baseAttr) {
    const explicitKey = (el.getAttribute(`${baseAttr}-key`) || "").trim();
    const explicitAction = (el.getAttribute(`${baseAttr}-action`) || "").trim();
    const raw = (el.getAttribute(baseAttr) || "").trim();

    const key = explicitKey || (raw && raw.toLowerCase() !== "global" ? raw : "");
    const action = explicitAction;

    return {
      key,
      action,
      global: !key && !action,
    };
  }

  function parseDisableScope(el) {
    const explicitKey = (el.getAttribute("hyper-loading-disable-key") || "").trim();
    const raw = (el.getAttribute("hyper-loading-disable") || "").trim();
    const key = explicitKey || (raw && raw.toLowerCase() !== "global" ? raw : "");
    return {
      key,
      global: !key,
    };
  }

  function attrBool(el, name, fallback = false) {
    if (!el.hasAttribute(name)) {
      return fallback;
    }
    const raw = (el.getAttribute(name) || "").trim().toLowerCase();
    if (!raw) {
      return true;
    }
    if (["1", "true", "yes", "on"].includes(raw)) {
      return true;
    }
    if (["0", "false", "no", "off"].includes(raw)) {
      return false;
    }
    return fallback;
  }

  function navEnabled(el) {
    if (!el || typeof el.hasAttribute !== "function") {
      return false;
    }
    if (el.hasAttribute("hyper-no-nav")) {
      return false;
    }
    if (!el.hasAttribute("hyper-nav")) {
      return false;
    }
    return attrBool(el, "hyper-nav", true);
  }

  function formActionName(form) {
    const explicit = (form.getAttribute("hyper-action") || "").trim();
    if (explicit) {
      return explicit;
    }
    const hidden = form.querySelector('input[name="_action"]');
    return hidden && hidden.value ? String(hidden.value).trim() : "";
  }

  function formToKwargs(formData) {
    const out = {};
    for (const [key, value] of formData.entries()) {
      if (key === "_action" || key === "csrfmiddlewaretoken") {
        continue;
      }
      out[key] = value;
    }
    return out;
  }

  function resolveForm(form) {
    if (!form) {
      return null;
    }
    if (form instanceof HTMLFormElement) {
      return form;
    }
    if (typeof form === "string") {
      const resolved = document.querySelector(form);
      return resolved instanceof HTMLFormElement ? resolved : null;
    }
    return null;
  }

  function appendDataToFormData(formData, data) {
    if (!data || typeof data !== "object") {
      return formData;
    }
    for (const [key, value] of Object.entries(data)) {
      formData.delete(key);
      if (Array.isArray(value)) {
        for (const item of value) {
          formData.append(key, item == null ? "" : item);
        }
        continue;
      }
      formData.append(key, value == null ? "" : value);
    }
    return formData;
  }

  function applyFormDisableScope(form, key) {
    if (!form.hasAttribute("hyper-form-disable")) {
      return;
    }
    const controls = form.querySelectorAll(
      'button, input[type="submit"], input[type="button"]'
    );
    for (const el of controls) {
      if (el.hasAttribute("hyper-loading-disable")) {
        continue;
      }
      if (key) {
        el.setAttribute("hyper-loading-disable", key);
      } else {
        el.setAttribute("hyper-loading-disable", "");
      }
    }
  }

  function isScopeActive(scope) {
    if (scope.action) {
      return (activeByAction.get(scope.action) || 0) > 0;
    }
    if (scope.key) {
      return (activeByKey.get(scope.key) || 0) > 0;
    }
    return activeGlobalRequests > 0;
  }

  function loadingDelay(el) {
    const raw = el.getAttribute("hyper-loading-delay") || "";
    const parsed = Number.parseInt(raw, 10);
    if (Number.isNaN(parsed) || parsed < 0) {
      return 0;
    }
    return parsed;
  }

  function hideLoadingElements() {
    for (const el of loadingElements()) {
      const timer = loadingTimers.get(el);
      if (timer) {
        window.clearTimeout(timer);
        loadingTimers.delete(el);
      }
      el.hidden = true;
      el.setAttribute("aria-hidden", "true");
    }
    for (const el of loadingDisableElements()) {
      if (!originalDisabledState.has(el)) {
        originalDisabledState.set(el, Boolean(el.disabled));
      }
      const wasDisabled = originalDisabledState.get(el);
      el.disabled = Boolean(wasDisabled);
      if (el.disabled) {
        el.setAttribute("aria-disabled", "true");
      } else {
        el.removeAttribute("aria-disabled");
      }
    }
  }

  function setLoadingElementsVisible() {
    for (const el of loadingElements()) {
      const timer = loadingTimers.get(el);
      if (timer) {
        window.clearTimeout(timer);
        loadingTimers.delete(el);
      }

      const scope = parseLoadingScope(el, "hyper-loading");
      const visible = isScopeActive(scope);
      if (visible) {
        const delay = loadingDelay(el);
        if (delay > 0) {
          const id = window.setTimeout(() => {
            el.hidden = false;
            el.removeAttribute("aria-hidden");
            loadingTimers.delete(el);
          }, delay);
          loadingTimers.set(el, id);
          continue;
        }
        el.hidden = false;
        el.removeAttribute("aria-hidden");
        continue;
      }

      el.hidden = true;
      el.setAttribute("aria-hidden", "true");
    }

    for (const el of loadingDisableElements()) {
      if (!originalDisabledState.has(el)) {
        originalDisabledState.set(el, Boolean(el.disabled));
      }
      const scope = parseDisableScope(el);
      const shouldDisable = scope.key
        ? (activeByKey.get(scope.key) || 0) > 0
        : activeGlobalRequests > 0;

      if (shouldDisable) {
        el.disabled = true;
        el.setAttribute("aria-disabled", "true");
        continue;
      }

      const wasDisabled = originalDisabledState.get(el);
      el.disabled = Boolean(wasDisabled);
      if (el.disabled) {
        el.setAttribute("aria-disabled", "true");
      } else {
        el.removeAttribute("aria-disabled");
      }
    }
  }

  function setLoading(isLoading, context = {}) {
    pendingRequests = Math.max(0, pendingRequests + (isLoading ? 1 : -1));

    if (isLoading) {
      activeGlobalRequests += 1;
      incrementMapCount(activeByKey, context.key || "");
      incrementMapCount(activeByAction, context.action || "");
      incrementMapCount(activeByTarget, context.target || "");
    } else {
      activeGlobalRequests = Math.max(0, activeGlobalRequests - 1);
      decrementMapCount(activeByKey, context.key || "");
      decrementMapCount(activeByAction, context.action || "");
      decrementMapCount(activeByTarget, context.target || "");
    }

    const busy = pendingRequests > 0;
    document.documentElement.toggleAttribute("hyper-loading", busy);
    if (busy) {
      document.documentElement.setAttribute("aria-busy", "true");
      if (document.body) {
        document.body.setAttribute("aria-busy", "true");
      }
    } else {
      document.documentElement.removeAttribute("aria-busy");
      if (document.body) {
        document.body.removeAttribute("aria-busy");
      }
    }
    setTargetBusyStates();
    setLoadingElementsVisible();

    window.dispatchEvent(
      new CustomEvent(busy ? "hyper:request:start" : "hyper:request:end")
    );
  }

  function updateHistory({ pushUrl = null, replaceUrl = null } = {}) {
    if (replaceUrl) {
      history.replaceState({}, "", replaceUrl);
      return;
    }
    if (pushUrl) {
      history.pushState({}, "", pushUrl);
    }
  }

  function redirectTo(url, { replace = false } = {}) {
    if (!url) {
      return;
    }
    if (replace) {
      window.location.replace(url);
      return;
    }
    window.location.assign(url);
  }

  function ensureModuleScript(src) {
    if (!src) {
      return Promise.resolve();
    }
    if (loadedModuleScripts.has(src)) {
      return loadedModuleScripts.get(src);
    }
    const existing = document.querySelector(`script[type="module"][src="${CSS.escape(src)}"]`);
    if (existing) {
      const promise = Promise.resolve();
      loadedModuleScripts.set(src, promise);
      return promise;
    }

    const promise = new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.type = "module";
      script.src = src;
      script.addEventListener("load", () => resolve());
      script.addEventListener("error", () => reject(new Error(`Failed to load module: ${src}`)));
      document.body.appendChild(script);
    });

    loadedModuleScripts.set(src, promise);
    return promise;
  }

  function csrfTokenFromCookie() {
    const cookie = document.cookie
      .split(";")
      .map((entry) => entry.trim())
      .find((entry) => entry.startsWith("csrftoken="));
    if (!cookie) {
      return "";
    }
    return decodeURIComponent(cookie.slice("csrftoken=".length));
  }

  function csrfTokenFromDOM() {
    const input = document.querySelector(
      "#hyper-csrf-token input[name='csrfmiddlewaretoken']"
    );
    if (input && input.value) {
      return input.value;
    }

    const meta = document.querySelector("meta[name='csrf-token']");
    if (meta && meta.content) {
      return meta.content;
    }

    return "";
  }

  async function request(url, options = {}) {
    const method = (options.method || "GET").toUpperCase();
    const headers = {
      "X-Requested-With": "XMLHttpRequest",
      ...(options.headers || {}),
    };
    const hookMeta = options.hookMeta || {};
    const requestId = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
    const syncMode = normalizeSyncMode(options.sync || "replace");
    const requestKey = resolveRequestKey({
      key: options.key || null,
      hookMeta,
      url,
    });

    if (syncMode !== "none") {
      const active = inFlightRequests.get(requestKey);
      if (active) {
        if (syncMode === "block") {
          emitEvent("hyper:requestBlocked", {
            id: requestId,
            key: requestKey,
            mode: syncMode,
            url,
            method,
            ...hookMeta,
          });
          return {
            kind: "blocked",
            data: null,
            response: null,
            blocked: true,
            aborted: false,
          };
        }

        active.controller.abort();
        emitEvent("hyper:requestReplaced", {
          id: requestId,
          replacedId: active.id,
          key: requestKey,
          mode: syncMode,
          url,
          method,
          ...hookMeta,
        });
      }
    }

    if (method !== "GET" && method !== "HEAD") {
      const csrf = csrfTokenFromCookie() || csrfTokenFromDOM();
      if (csrf && !headers["X-CSRFToken"]) {
        headers["X-CSRFToken"] = csrf;
      }
    }

    const controller = new AbortController();
    if (syncMode !== "none") {
      inFlightRequests.set(requestKey, { id: requestId, controller });
    }

    setLoading(true, {
      key: requestKey,
      action: hookMeta.action || "",
      target: hookMeta.target || "",
    });
    emitEvent("hyper:beforeRequest", {
      id: requestId,
      url,
      method,
      ...hookMeta,
    });

    let response;
    let aborted = false;
    try {
      response = await fetch(url, {
        ...options,
        credentials: "same-origin",
        headers,
        signal: controller.signal,
      });

      if (response.ok) {
        emitEvent("hyper:requestSuccess", {
          id: requestId,
          url,
          method,
          status: response.status,
          response,
          ...hookMeta,
        });
      } else {
        emitEvent("hyper:requestError", {
          id: requestId,
          url,
          method,
          status: response.status,
          response,
          ...hookMeta,
        });
      }
    } catch (error) {
      if (error && error.name === "AbortError") {
        aborted = true;
        emitEvent("hyper:requestAborted", {
          id: requestId,
          key: requestKey,
          mode: syncMode,
          url,
          method,
          ...hookMeta,
        });
      } else {
        emitEvent("hyper:requestException", {
          id: requestId,
          key: requestKey,
          mode: syncMode,
          url,
          method,
          error,
          ...hookMeta,
        });
        throw error;
      }
    } finally {
      if (syncMode !== "none") {
        const active = inFlightRequests.get(requestKey);
        if (active && active.id === requestId) {
          inFlightRequests.delete(requestKey);
        }
      }

      emitEvent("hyper:afterRequest", {
        id: requestId,
        key: requestKey,
        mode: syncMode,
        url,
        method,
        status: response ? response.status : null,
        ok: response ? response.ok : false,
        aborted,
        response: response || null,
        ...hookMeta,
      });
      setLoading(false, {
        key: requestKey,
        action: hookMeta.action || "",
        target: hookMeta.target || "",
      });
    }

    if (aborted) {
      return {
        kind: "aborted",
        data: null,
        response: null,
        blocked: false,
        aborted: true,
      };
    }

    const contentType = response.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
      return { kind: "json", data: await response.json(), response };
    }
    return { kind: "html", data: await response.text(), response };
  }

  function applySignals(payload, { syncStore = true } = {}) {
    if (!payload || !payload.signals) {
      return;
    }

    const patches = splitSignalPatches(payload.signals);

    if (
      syncStore &&
      window.Alpine &&
      typeof window.Alpine.store === "function" &&
      Object.keys(patches.global).length > 0
    ) {
      const store = ensureHyperStore();
      if (!store) {
        return;
      }
      mergeInto(store, patches.global);
    }

    window.dispatchEvent(new CustomEvent("hyper:signals", { detail: payload.signals }));
  }

  function applyToasts(toasts) {
    if (!Array.isArray(toasts) || toasts.length === 0) {
      return;
    }

    for (const toast of toasts) {
      window.dispatchEvent(new CustomEvent("hyper:toast", { detail: toast }));
    }
  }

  function swapHTML(target, html) {
    const el = typeof target === "string" ? document.querySelector(target) : target;
    if (!el) {
      return;
    }
    el.innerHTML = html;
  }

  function getMorphdom() {
    if (typeof window.morphdom === "function") {
      return window.morphdom;
    }
    return null;
  }

  function toElement(html) {
    const template = document.createElement("template");
    template.innerHTML = html.trim();
    const first = template.content.firstElementChild;
    return first || null;
  }

  function morphInner(el, html) {
    const morphdom = getMorphdom();
    if (!morphdom) {
      swapHTML(el, html);
      return;
    }

    const shadow = document.createElement(el.tagName.toLowerCase());
    shadow.innerHTML = html;
    morphdom(el, shadow, { childrenOnly: true });
  }

  function morphOuter(el, html) {
    const morphdom = getMorphdom();
    if (!morphdom) {
      el.outerHTML = html;
      return;
    }

    const next = toElement(html);
    if (!next) {
      el.remove();
      return;
    }
    morphdom(el, next);
  }

  function normalizeSwap(swap) {
    const value = String(swap || "inner").toLowerCase();
    const aliases = {
      inner: "inner",
      innerhtml: "inner",
      outer: "outer",
      outerhtml: "outer",
      before: "before",
      beforebegin: "before",
      after: "after",
      afterend: "after",
      prepend: "prepend",
      afterbegin: "prepend",
      append: "append",
      beforeend: "append",
      replace: "outer",
      delete: "delete",
      none: "none",
    };
    return aliases[value] || "inner";
  }

  function applySwap(target, html, swap = "inner") {
    const el = typeof target === "string" ? document.querySelector(target) : target;
    if (!el) {
      return false;
    }

    const mode = normalizeSwap(swap);

    if (mode === "none") {
      return true;
    }
    if (mode === "delete") {
      el.remove();
      return true;
    }
    if (mode === "outer") {
      morphOuter(el, html);
      return true;
    }
    if (mode === "before") {
      el.insertAdjacentHTML("beforebegin", html);
      return true;
    }
    if (mode === "after") {
      el.insertAdjacentHTML("afterend", html);
      return true;
    }
    if (mode === "prepend") {
      el.insertAdjacentHTML("afterbegin", html);
      return true;
    }
    if (mode === "append") {
      el.insertAdjacentHTML("beforeend", html);
      return true;
    }

    morphInner(el, html);
    return true;
  }

  function resolveElement(target) {
    if (!target) {
      return null;
    }
    return typeof target === "string" ? document.querySelector(target) : target;
  }

  function parseDelay(value, fallback = 0) {
    if (value === undefined || value === null || value === "") {
      return fallback;
    }
    const parsed = Number.parseInt(String(value), 10);
    if (Number.isNaN(parsed) || parsed < 0) {
      return fallback;
    }
    return parsed;
  }

  function sleep(ms) {
    if (!ms || ms <= 0) {
      return Promise.resolve();
    }
    return new Promise((resolve) => window.setTimeout(resolve, ms));
  }

  function captureFocusState() {
    const active = document.activeElement;
    if (!active || !(active instanceof HTMLElement)) {
      return null;
    }

    return {
      id: active.id || "",
      name: active.getAttribute("name") || "",
      value:
        active instanceof HTMLInputElement || active instanceof HTMLTextAreaElement
          ? active.value
          : null,
    };
  }

  function resolveFocusElement(policy, target, focusState) {
    if (!policy || policy === "preserve") {
      if (focusState && focusState.id) {
        const byId = document.getElementById(focusState.id);
        if (byId) {
          return byId;
        }
      }
      if (focusState && focusState.name) {
        const root = resolveElement(target) || document;
        const escaped =
          typeof CSS !== "undefined" && typeof CSS.escape === "function"
            ? CSS.escape(focusState.name)
            : focusState.name.replace(/"/g, '\\"');
        const byName = root.querySelector(`[name="${escaped}"]`);
        if (byName) {
          return byName;
        }
      }
      return null;
    }

    if (policy === "first-invalid") {
      const root = resolveElement(target) || document;
      return (
        root.querySelector(
          '[aria-invalid="true"], .errorlist + input, .errorlist + textarea, .errorlist + select'
        ) || null
      );
    }

    if (typeof policy === "string") {
      return document.querySelector(policy);
    }

    return null;
  }

  function applyFocus(policy, target, focusState) {
    const node = resolveFocusElement(policy, target, focusState);
    if (!node || typeof node.focus !== "function") {
      return;
    }
    node.focus({ preventScroll: false });
    if (
      focusState &&
      focusState.value !== null &&
      (node instanceof HTMLInputElement || node instanceof HTMLTextAreaElement)
    ) {
      const len = String(node.value || "").length;
      node.setSelectionRange(len, len);
    }
  }

  function applyViewNames(root = document) {
    if (!root || typeof root.querySelectorAll !== "function") {
      return;
    }
    const nodes = root.querySelectorAll("[hyper-view-name]");
    for (const node of nodes) {
      const name = (node.getAttribute("hyper-view-name") || "").trim();
      if (!name) {
        node.style.viewTransitionName = "";
        continue;
      }
      node.style.viewTransitionName = name;
    }
  }

  async function applySwapLifecycle({
    target,
    swapDelay = 0,
    settleDelay = 0,
    focus = "preserve",
    mutate,
    detail = {},
  }) {
    const el = resolveElement(target);
    const focusState = captureFocusState();
    if (!el) {
      await mutate();
      applyViewNames(document);
      applyFocus(focus, target, focusState);
      return;
    }

    el.classList.add("hyper-swapping");
    emitEvent("hyper:swap:start", { target, ...detail });

    try {
      await sleep(swapDelay);
      await mutate();
      applyViewNames(resolveElement(target) || document);
      applyFocus(focus, target, focusState);
      emitEvent("hyper:swap:end", { target, ...detail });
      el.classList.remove("hyper-swapping");
      el.classList.add("hyper-settling");
      await sleep(settleDelay);
    } finally {
      el.classList.remove("hyper-swapping");
      el.classList.remove("hyper-settling");
      emitEvent("hyper:settle:end", { target, ...detail });
    }
  }

  function supportsViewTransitions() {
    return typeof document !== "undefined" && typeof document.startViewTransition === "function";
  }

  async function withViewTransition(enabled, updateFn) {
    if (!enabled || !supportsViewTransitions()) {
      await updateFn();
      return;
    }

    emitEvent("hyper:transition:start", {
      supported: true,
    });

    const transition = document.startViewTransition(() => {
      return updateFn();
    });

    try {
      await transition.finished;
    } catch {
      // no-op
    } finally {
      emitEvent("hyper:transition:end", {
        supported: true,
      });
    }
  }

  function normalizeOOBOperation(entry) {
    if (!entry || typeof entry !== "object") {
      return null;
    }

    const target = String(entry.target || entry.selector || "").trim();
    if (!target) {
      return null;
    }

    const swap = String(entry.swap || "inner").trim();

    return {
      target,
      swap: swap || "inner",
      html: typeof entry.html === "string" ? entry.html : "",
      order: Number.isFinite(entry.order) ? Number(entry.order) : null,
    };
  }

  function normalizeOOBOperations(oob) {
    if (!oob) {
      return [];
    }

    if (Array.isArray(oob)) {
      const ops = [];
      for (const item of oob) {
        const op = normalizeOOBOperation(item);
        if (op) {
          ops.push(op);
        }
      }
      return ops;
    }

    if (typeof oob === "object") {
      const ops = [];
      for (const [selector, entry] of Object.entries(oob)) {
        if (!selector) {
          continue;
        }

        if (typeof entry === "string") {
          ops.push({ target: selector, swap: "inner", html: entry, order: null });
          continue;
        }

        if (!entry || typeof entry !== "object") {
          continue;
        }

        const op = normalizeOOBOperation({ ...entry, target: selector });
        if (op) {
          ops.push(op);
        }
      }

      const ordered = ops.filter((op) => op.order !== null);
      const unordered = ops.filter((op) => op.order === null);
      ordered.sort((a, b) => a.order - b.order);
      return [...ordered, ...unordered];
    }

    return [];
  }

  function applyOOB(oob, { strict = false } = {}) {
    const operations = normalizeOOBOperations(oob);
    for (const op of operations) {
      const ok = applySwap(op.target, op.html, op.swap);
      if (!ok && strict) {
        throw new Error(`Hyper OOB target not found: ${op.target}`);
      }
    }
  }

  function deepMerge(target, patch) {
    if (patch == null || typeof patch !== "object" || Array.isArray(patch)) {
      return patch;
    }
    const output = { ...(target || {}) };
    for (const [key, value] of Object.entries(patch)) {
      if (value != null && typeof value === "object" && !Array.isArray(value)) {
        output[key] = deepMerge(output[key], value);
      } else {
        output[key] = value;
      }
    }
    return output;
  }

  function mergeInto(target, patch) {
    if (!target || !patch || typeof patch !== "object") {
      return;
    }
    const merged = deepMerge(target, patch);
    for (const [key, value] of Object.entries(merged)) {
      target[key] = value;
    }
  }

  function splitSignalPatches(signals) {
    const local = {};
    const global = {};
    if (!signals || typeof signals !== "object") {
      return { local, global };
    }
    for (const [key, value] of Object.entries(signals)) {
      if (key.startsWith("$") && key.length > 1) {
        global[key.slice(1)] = value;
      } else {
        local[key] = value;
      }
    }
    return { local, global };
  }

  function ensureHyperStore() {
    if (!window.Alpine || typeof window.Alpine.store !== "function") {
      return null;
    }
    let store = window.Alpine.store("hyper");
    if (!store) {
      const initial =
        typeof window.Alpine.reactive === "function"
          ? window.Alpine.reactive({})
          : {};
      window.Alpine.store("hyper", initial);
      store = window.Alpine.store("hyper");
    }
    return store;
  }

  function resolveAutoBindTarget() {
    if (!window.Alpine || typeof window.Alpine.$data !== "function") {
      return null;
    }

    const active = document.activeElement;
    if (!active || typeof active.closest !== "function") {
      return null;
    }

    const root = active.closest("[x-data]");
    if (!root) {
      return null;
    }

    try {
      return window.Alpine.$data(root);
    } catch {
      return null;
    }
  }

  async function runAction({
    url,
    action,
    target,
    method = "POST",
    body = null,
    syncStore = true,
    bind = null,
    kwargs = null,
    swap = "inner",
    transition = false,
    push = false,
    replace = false,
    sync = "replace",
    key = null,
    strictTargets = undefined,
    swapDelay = 0,
    settleDelay = 0,
    focus = "preserve",
  }) {
    const resolvedUrl = url || window.location.pathname;
    const headers = {
      "X-Hyper-Action": action,
    };
    if (kwargs && typeof kwargs === "object") {
      headers["X-Hyper-Signals"] = JSON.stringify(kwargs);
    }
    if (target) {
      headers["X-Hyper-Target"] = target;
    }

    const result = await request(resolvedUrl, {
      method,
      headers,
      body,
      hookMeta: {
        kind: "action",
        action,
        target: target || null,
      },
      sync,
      key,
    });

    if (result.blocked || result.aborted) {
      return result;
    }

    if (!result.response.ok) {
      throw new Error(
        `Hyper action '${action}' failed: ${result.response.status} ${result.response.statusText}`
      );
    }

    if (result.kind === "json") {
      if (result.data.redirect_to) {
        redirectTo(result.data.redirect_to, {
          replace: Boolean(result.data.replace_url) && result.data.replace_url === result.data.redirect_to,
        });
        return result.data;
      }

      applySignals(result.data, { syncStore });
      applyToasts(result.data.toasts);
      if (result.data.signals) {
        const patches = splitSignalPatches(result.data.signals);
        const targetBind = bind || resolveAutoBindTarget();
        if (targetBind) {
          mergeInto(targetBind, patches.local);
        }
      }
      const resolvedTarget = target || result.data.target || null;
      const resolvedSwap = result.data.swap || swap || "inner";
      const resolvedTransition =
        result.data.transition === undefined ? transition : Boolean(result.data.transition);
      const resolvedFocus = result.data.focus || focus || "preserve";
      const resolvedSwapDelay = parseDelay(result.data.swap_delay, parseDelay(swapDelay, 0));
      const resolvedSettleDelay = parseDelay(
        result.data.settle_delay,
        parseDelay(settleDelay, 0)
      );
      const strict = strictTargetsEnabled(
        result.data.strict_targets === undefined
          ? strictTargets
          : Boolean(result.data.strict_targets)
      );

      updateHistory({
        replaceUrl: result.data.replace_url || (replace ? resolvedUrl : null),
        pushUrl: result.data.push_url || (push ? resolvedUrl : null),
      });

      const swapMode = normalizeSwap(resolvedSwap);
      const hasHtml = typeof result.data.html === "string";
      const canSwapWithoutHtml = swapMode === "delete" || swapMode === "none";

      await applySwapLifecycle({
        target: resolvedTarget,
        swapDelay: resolvedSwapDelay,
        settleDelay: resolvedSettleDelay,
        detail: {
          action,
          swap: resolvedSwap,
        },
        focus: resolvedFocus,
        mutate: async () => {
          await withViewTransition(resolvedTransition, () => {
            if (resolvedTarget && (hasHtml || canSwapWithoutHtml)) {
              const ok = applySwap(resolvedTarget, hasHtml ? result.data.html : "", resolvedSwap);
              if (!ok && strict) {
                throw new Error(`Hyper target not found: ${resolvedTarget}`);
              }
            }
            applyOOB(result.data.oob, { strict });
          });
        },
      });
      await ensureModuleScript(result.data.js || null);
      return result.data;
    }

    if (target) {
      const strict = strictTargetsEnabled(strictTargets);
      await applySwapLifecycle({
        target,
        swapDelay: parseDelay(swapDelay, 0),
        settleDelay: parseDelay(settleDelay, 0),
        detail: { action, swap },
        focus,
        mutate: async () => {
          await withViewTransition(transition, () => {
            const ok = applySwap(target, result.data, swap);
            if (!ok && strict) {
              throw new Error(`Hyper target not found: ${target}`);
            }
          });
        },
      });
    }
    return result.data;
  }

  async function visit({
    url,
    target,
    push = true,
    sync = "replace",
    key = null,
    swap = "inner",
    transition = false,
    swapDelay = 0,
    settleDelay = 0,
    strictTargets = undefined,
    focus = "preserve",
  }) {
    const result = await request(url, {
      method: "GET",
      hookMeta: {
        kind: "visit",
        target: target || null,
      },
      sync,
      key,
    });

    if (result.blocked || result.aborted) {
      return result;
    }

    const strict = strictTargetsEnabled(strictTargets);
    const resolvedSwapDelay = parseDelay(swapDelay, 0);
    const resolvedSettleDelay = parseDelay(settleDelay, 0);

    if (result.kind === "json") {
      applySignals(result.data);
      const resolvedTarget = target || result.data.target || null;
      const resolvedSwap = result.data.swap || swap || "inner";
      const resolvedTransition =
        result.data.transition === undefined ? transition : Boolean(result.data.transition);
      const resolvedFocus = result.data.focus || focus || "preserve";
      await applySwapLifecycle({
        target: resolvedTarget,
        swapDelay: parseDelay(result.data.swap_delay, resolvedSwapDelay),
        settleDelay: parseDelay(result.data.settle_delay, resolvedSettleDelay),
        detail: { kind: "visit", swap: resolvedSwap },
        focus: resolvedFocus,
        mutate: async () => {
          await withViewTransition(resolvedTransition, () => {
            if (resolvedTarget && result.data.html) {
              const ok = applySwap(resolvedTarget, result.data.html, resolvedSwap);
              if (!ok && strict) {
                throw new Error(`Hyper target not found: ${resolvedTarget}`);
              }
            }
            applyOOB(result.data.oob, { strict });
          });
        },
      });
    } else if (target) {
      await applySwapLifecycle({
        target,
        swapDelay: resolvedSwapDelay,
        settleDelay: resolvedSettleDelay,
        detail: { kind: "visit", swap },
        focus,
        mutate: async () => {
          await withViewTransition(transition, () => {
            const ok = applySwap(target, result.data, swap);
            if (!ok && strict) {
              throw new Error(`Hyper target not found: ${target}`);
            }
          });
        },
      });
    }

    if (push) {
      history.pushState({}, "", url);
    }
  }

  async function navigate(
    url,
    {
      target = "body",
      push = true,
      sync = "replace",
      key = null,
      swap = "inner",
      transition = false,
      swapDelay = 0,
      settleDelay = 0,
      strictTargets = undefined,
      focus = "preserve",
    } = {}
  ) {
    return visit({
      url,
      target,
      push,
      sync,
      key,
      swap,
      transition,
      swapDelay,
      settleDelay,
      strictTargets,
      focus,
    });
  }

  function initNavigation() {
    document.addEventListener("click", (event) => {
      const node = event.target;
      if (!(node instanceof Element)) {
        return;
      }

      const link = node.closest("a[hyper-nav]");
      if (!link) {
        return;
      }
      if (!navEnabled(link)) {
        return;
      }
      if (event.defaultPrevented || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
        return;
      }

      if (link.hasAttribute("download") || link.getAttribute("target")) {
        return;
      }

      const href = link.getAttribute("href");
      if (
        !href ||
        href.startsWith("#") ||
        href.startsWith("mailto:") ||
        href.startsWith("tel:") ||
        href.startsWith("javascript:")
      ) {
        return;
      }

      if (href.startsWith("http")) {
        try {
          const parsed = new URL(href, window.location.origin);
          if (parsed.origin !== window.location.origin) {
            return;
          }
        } catch {
          return;
        }
      }

      event.preventDefault();
      const target = link.getAttribute("hyper-target") || "body";
      const transition = attrBool(link, "hyper-transition", false);
      const swapDelay = parseDelay(link.getAttribute("hyper-swap-delay"), 0);
      const settleDelay = parseDelay(link.getAttribute("hyper-settle-delay"), 0);
      const focus = link.getAttribute("hyper-focus") || "preserve";
      navigate(href, {
        target,
        push: true,
        sync: link.getAttribute("hyper-sync") || "replace",
        key: link.getAttribute("hyper-key") || null,
        transition,
        swapDelay,
        settleDelay,
        focus,
      });
    });

    document.addEventListener("submit", (event) => {
      const form = event.target;
      if (!(form instanceof HTMLFormElement)) {
        return;
      }
      if (form.hasAttribute("hyper-form")) {
        return;
      }
      if (!navEnabled(form)) {
        return;
      }

      event.preventDefault();
      const method = (form.getAttribute("method") || "GET").toUpperCase();
      const action = form.getAttribute("action") || window.location.pathname;
      const target = form.getAttribute("hyper-target") || "body";
      const transition = attrBool(form, "hyper-transition", false);
      const swapDelay = parseDelay(form.getAttribute("hyper-swap-delay"), 0);
      const settleDelay = parseDelay(form.getAttribute("hyper-settle-delay"), 0);
      const focus = form.getAttribute("hyper-focus") || "preserve";

      if (method === "GET") {
        const params = new URLSearchParams(new FormData(form)).toString();
        const url = params ? `${action}?${params}` : action;
        navigate(url, {
          target,
          push: true,
          sync: form.getAttribute("hyper-sync") || "replace",
          key: form.getAttribute("hyper-key") || null,
          transition,
          swapDelay,
          settleDelay,
          focus,
        });
        return;
      }

      request(action, {
        method,
        body: new FormData(form),
        hookMeta: { kind: "nav-form", target },
        sync: form.getAttribute("hyper-sync") || "replace",
        key: form.getAttribute("hyper-key") || null,
      }).then((result) => {
        if (result.blocked || result.aborted) {
          return;
        }
        if (result.kind === "html") {
          applySwapLifecycle({
            target,
            swapDelay,
            settleDelay,
            focus,
            detail: { kind: "nav-form", swap: "inner" },
            mutate: async () => {
              await withViewTransition(transition, () => {
                applySwap(target, result.data, "inner");
              });
            },
          }).then(() => {
            history.pushState({}, "", action);
          });
        }
      });
    });

    window.addEventListener("popstate", () => {
      const target = document.body.getAttribute("hyper-pop-target") || "body";
      navigate(window.location.pathname + window.location.search, { target, push: false });
    });
  }

  function initForms() {
    document.addEventListener("submit", (event) => {
      const form = event.target;
      if (!(form instanceof HTMLFormElement)) {
        return;
      }
      if (!form.hasAttribute("hyper-form")) {
        return;
      }

      event.preventDefault();

      const action = formActionName(form);
      if (!action) {
        emitEvent("hyper:form:error", {
          form,
          reason: "missing-action",
        });
        return;
      }

      const method = (form.getAttribute("method") || "POST").toUpperCase();
      const url = form.getAttribute("action") || window.location.pathname;
      const target = form.getAttribute("hyper-target") || null;
      const swap = form.getAttribute("hyper-swap") || "inner";
      const transition = attrBool(form, "hyper-transition", false);
      const sync = form.getAttribute("hyper-sync") || "block";
      const key = (form.getAttribute("hyper-key") || action).trim();
      const strictTargets = attrBool(form, "hyper-strict-targets", false);
      const swapDelay = parseDelay(form.getAttribute("hyper-swap-delay"), 0);
      const settleDelay = parseDelay(form.getAttribute("hyper-settle-delay"), 0);
      const focus = form.getAttribute("hyper-focus") || "preserve";

      const req = actionRequest(
        action,
        {},
        {
          form,
          method,
          url,
          target,
          swap,
          transition,
          sync,
          key,
          strictTargets,
          swapDelay,
          settleDelay,
          focus,
          onBeforeSubmit: () => {
            applyFormDisableScope(form, key);
            emitEvent("hyper:form:beforeSubmit", {
              action,
              method,
              url,
              target,
              key,
            });
          },
        }
      );

      req
        .then((result) => {
          if (result && result.blocked) {
            emitEvent("hyper:form:blocked", { action, method, url, target, key });
            return;
          }
          if (result && result.aborted) {
            emitEvent("hyper:form:aborted", { action, method, url, target, key });
            return;
          }
          emitEvent("hyper:form:success", { action, method, url, target, key, result });
        })
        .catch((error) => {
          emitEvent("hyper:form:error", {
            action,
            method,
            url,
            target,
            key,
            error,
          });
        });
    });
  }

  async function actionRequest(action, data = {}, options = {}) {
    const form = resolveForm(options.form || null);
    const inferredMethod = form ? (form.getAttribute("method") || "GET").toUpperCase() : "GET";
    const method = String(options.method || inferredMethod || "GET").toUpperCase();
    const url =
      options.url ||
      (form ? form.getAttribute("action") || window.location.pathname : window.location.pathname);
    const target = options.target ?? null;
    const transition = options.transition || false;
    const swap = options.swap || "inner";
    const sync = options.sync || (form ? "block" : "replace");
    const key = options.key || null;
    const strictTargets = options.strictTargets;
    const swapDelay = options.swapDelay;
    const settleDelay = options.settleDelay;
    const focus = options.focus || "preserve";
    const syncStore = options.syncStore ?? true;
    const bind = options.bind || null;
    const extraData = data && typeof data === "object" ? data : null;

    if (typeof options.onBeforeSubmit === "function") {
      options.onBeforeSubmit();
    }

    if (form) {
      const payload = appendDataToFormData(new FormData(form), extraData);
      if (!payload.has("_action")) {
        payload.append("_action", action);
      }
      if (method === "GET") {
        return runAction({
          url,
          action,
          method: "GET",
          target,
          swap,
          transition,
          sync,
          key,
          strictTargets,
          swapDelay,
          settleDelay,
          focus,
          syncStore,
          bind,
          kwargs: formToKwargs(payload),
        });
      }
      return runAction({
        url,
        action,
        method,
        target,
        swap,
        transition,
        sync,
        key,
        strictTargets,
        swapDelay,
        settleDelay,
        focus,
        syncStore,
        bind,
        body: payload,
      });
    }

    return runAction({
      url,
      action,
      method,
      target,
      syncStore,
      bind,
      kwargs: extraData,
      swap,
      transition,
      push: options.push || false,
      replace: options.replace || false,
      sync,
      key,
      strictTargets,
      swapDelay,
      settleDelay,
      focus,
    });
  }

  async function get(action, kwargs = {}, options = {}) {
    return actionRequest(action, kwargs, { ...options, method: "GET" });
  }

  async function post(action, kwargs = {}, options = {}) {
    return actionRequest(action, kwargs, { ...options, method: "POST" });
  }

  function initLoadingIndicators() {
    hideLoadingElements();
    applyViewNames(document);
  }

  return {
    runAction,
    action: actionRequest,
    get,
    post,
    visit,
    applySignals,
    swapHTML,
    applySwap,
    initLoadingIndicators,
    initNavigation,
    initForms,
    navigate,
    configure,
    applyViewNames,
    ensureHyperStore,
  };
})();

window.Hyper = Hyper;
window.action = Hyper.action;
window.get = Hyper.get;
window.post = Hyper.post;

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => {
    Hyper.initLoadingIndicators();
    Hyper.initNavigation();
    Hyper.initForms();
  });
} else {
  Hyper.initLoadingIndicators();
  Hyper.initNavigation();
  Hyper.initForms();
}

function registerAlpineMagicHelpers() {
  if (!window.Alpine || typeof window.Alpine.magic !== "function") {
    return;
  }
  window.Alpine.magic("action", () => Hyper.action);
  window.Alpine.magic("get", () => Hyper.get);
  window.Alpine.magic("post", () => Hyper.post);
  window.Alpine.magic("hyper", () => {
    return Hyper.ensureHyperStore() || {};
  });
}

if (window.Alpine) {
  registerAlpineMagicHelpers();
}

document.addEventListener("alpine:init", () => {
  registerAlpineMagicHelpers();
});
