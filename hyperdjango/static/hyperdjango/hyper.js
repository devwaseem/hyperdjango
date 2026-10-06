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
  const elementRequestKeys = new WeakMap();
  let nextElementRequestKey = 0;
  let networkOnline = typeof navigator === "undefined" ? true : navigator.onLine;
  let networkInitialized = false;
  const lazyActionElements = new WeakSet();
  let lazyActionObserver = null;
  let managedHeadNodes = new Set(Array.from(document.head.children).filter(isHeadAsset));
  let preserveSlotCounter = 0;
  const config = {
    strictTargets: false,
    sseRetry: true,
    sseRetryInterval: 1000,
    sseRetryScaler: 2,
    sseRetryMaxWait: 30000,
    sseRetryMaxCount: 10,
    switchActionMaxDepth: 4,
  };

  function emitEvent(name, detail) {
    window.dispatchEvent(new CustomEvent(name, { detail }));
  }

  function emitHistoryRestoreEvent(name, detail) {
    const eventInit = { detail };
    window.dispatchEvent(new CustomEvent(name, eventInit));
    document.dispatchEvent(new CustomEvent(name, eventInit));
  }

  function applyNetworkState(root = document) {
    if (!root || typeof root.querySelectorAll !== "function") {
      return;
    }
    for (const el of root.querySelectorAll("[hyper-online]")) {
      el.hidden = !networkOnline;
      el.setAttribute("aria-hidden", String(!networkOnline));
    }
    for (const el of root.querySelectorAll("[hyper-offline]")) {
      el.hidden = networkOnline;
      el.setAttribute("aria-hidden", String(networkOnline));
    }
    for (const el of root.querySelectorAll("[hyper-online-class]")) {
      for (const className of parseClassList(el.getAttribute("hyper-online-class"))) {
        el.classList.toggle(className, networkOnline);
      }
    }
    for (const el of root.querySelectorAll("[hyper-online-remove-class]")) {
      for (const className of parseClassList(el.getAttribute("hyper-online-remove-class"))) {
        el.classList.toggle(className, !networkOnline);
      }
    }
    for (const el of root.querySelectorAll("[hyper-offline-class]")) {
      for (const className of parseClassList(el.getAttribute("hyper-offline-class"))) {
        el.classList.toggle(className, !networkOnline);
      }
    }
    for (const el of root.querySelectorAll("[hyper-offline-remove-class]")) {
      for (const className of parseClassList(el.getAttribute("hyper-offline-remove-class"))) {
        el.classList.toggle(className, networkOnline);
      }
    }
  }

  function setNetworkState(online) {
    const nextOnline = Boolean(online);
    const changed = nextOnline !== networkOnline;
    networkOnline = nextOnline;
    applyNetworkState(document);
    if (!changed) {
      return;
    }

    const detail = { online: networkOnline, offline: !networkOnline };
    emitEvent("hyper:network:change", detail);
    emitEvent(networkOnline ? "hyper:network:online" : "hyper:network:offline", detail);
  }

  function initNetwork() {
    if (networkInitialized) {
      applyNetworkState(document);
      return;
    }
    networkInitialized = true;
    networkOnline = typeof navigator === "undefined" ? true : navigator.onLine;
    applyNetworkState(document);
    window.addEventListener("online", () => setNetworkState(true));
    window.addEventListener("offline", () => setNetworkState(false));
  }

  const network = Object.freeze({
    get online() {
      return networkOnline;
    },
    get offline() {
      return !networkOnline;
    },
    refresh() {
      setNetworkState(typeof navigator === "undefined" ? true : navigator.onLine);
      return networkOnline;
    },
  });

  function configure(next = {}) {
    if (!next || typeof next !== "object") {
      return { ...config };
    }
    if (Object.prototype.hasOwnProperty.call(next, "strictTargets")) {
      config.strictTargets = Boolean(next.strictTargets);
    }
    if (Object.prototype.hasOwnProperty.call(next, "sseRetry")) {
      config.sseRetry = Boolean(next.sseRetry);
    }
    for (const key of [
      "sseRetryInterval",
      "sseRetryScaler",
      "sseRetryMaxWait",
      "sseRetryMaxCount",
      "switchActionMaxDepth",
    ]) {
      if (Object.prototype.hasOwnProperty.call(next, key)) {
        const value = Number(next[key]);
        if (Number.isFinite(value) && value >= 0) {
          config[key] = value;
        }
      }
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

  function normalizeMethod(method, fallback = "GET") {
    return String(method || fallback).trim().toUpperCase();
  }

  function resolveSSERetry(method, explicitRetry = undefined) {
    if (typeof explicitRetry === "boolean") {
      return explicitRetry;
    }
    return normalizeMethod(method) === "GET" && config.sseRetry;
  }

  function elementRequestKey(el) {
    if (!(el instanceof Element)) {
      return "";
    }
    let existing = elementRequestKeys.get(el);
    if (existing) {
      return existing;
    }
    nextElementRequestKey += 1;
    existing = `el:${nextElementRequestKey}`;
    elementRequestKeys.set(el, existing);
    return existing;
  }

  function resolveRequestKey({ key = null, hookMeta = {}, url = "" }) {
    if (key) {
      return String(key);
    }
    if (hookMeta.kind === "action" && hookMeta.action) {
      if (hookMeta.sourceEl) {
        return `action:${hookMeta.action}:${elementRequestKey(hookMeta.sourceEl)}`;
      }
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
    return Array.from(document.querySelectorAll(
      "[hyper-loading], [hyper-loading-key], [hyper-loading-action]"
    )).filter(
      (el) => el !== document.documentElement
    );
  }

  function loadingDisableElements() {
    return Array.from(document.querySelectorAll(
      "[hyper-loading-disable], [hyper-loading-disable-key]"
    ));
  }

  function loadingClassElements() {
    return Array.from(document.querySelectorAll("[hyper-loading-class]"));
  }

  function loadingRemoveClassElements() {
    return Array.from(document.querySelectorAll("[hyper-loading-remove-class]"));
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
    const explicitKey = (
      el.getAttribute(`${baseAttr}-key`) || el.getAttribute("hyper-loading-key") || ""
    ).trim();
    const explicitAction = (
      el.getAttribute(`${baseAttr}-action`) || el.getAttribute("hyper-loading-action") || ""
    ).trim();
    const raw = (el.getAttribute(baseAttr) || "").trim();

    const key = explicitKey || (raw && raw.toLowerCase() !== "global" ? raw : "");
    const action = explicitAction;

    return {
      key,
      action,
      global: !key && !action,
    };
  }

  function parseSharedLoadingScope(el) {
    const hasBase = el.hasAttribute("hyper-loading");
    const explicitKey = (el.getAttribute("hyper-loading-key") || "").trim();
    const explicitAction = (el.getAttribute("hyper-loading-action") || "").trim();

    if (!hasBase && !explicitKey && !explicitAction) {
      return null;
    }

    const raw = hasBase ? (el.getAttribute("hyper-loading") || "").trim() : "";
    const key = explicitKey || (raw && raw.toLowerCase() !== "global" ? raw : "");

    return {
      key,
      action: explicitAction,
      global: !key && !explicitAction,
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

  function parseClassList(value) {
    if (!value) {
      return [];
    }
    return String(value)
      .split(/\s+/)
      .map((item) => item.trim())
      .filter(Boolean);
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

  function resolveSourceEl(sourceEl) {
    if (sourceEl instanceof Element) {
      return sourceEl;
    }
    if (typeof sourceEl === "string") {
      const resolved = document.querySelector(sourceEl);
      return resolved instanceof Element ? resolved : null;
    }
    const active = document.activeElement;
    return active instanceof Element ? active : null;
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

  function buildActionSearchParams(action, data) {
    const params = new URLSearchParams();
    params.set("_action", action);
    if (!data || typeof data !== "object") {
      return params;
    }
    for (const [key, value] of Object.entries(data)) {
      if (Array.isArray(value)) {
        params.delete(key);
        for (const item of value) {
          params.append(key, item == null ? "" : String(item));
        }
        continue;
      }
      params.set(key, value == null ? "" : String(value));
    }
    return params;
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

    for (const el of loadingClassElements()) {
      for (const className of parseClassList(el.getAttribute("hyper-loading-class"))) {
        el.classList.remove(className);
      }
    }

    for (const el of loadingRemoveClassElements()) {
      for (const className of parseClassList(el.getAttribute("hyper-loading-remove-class"))) {
        el.classList.add(className);
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

    for (const el of loadingClassElements()) {
      const scope = parseSharedLoadingScope(el);
      const active = scope ? isScopeActive(scope) : false;
      for (const className of parseClassList(el.getAttribute("hyper-loading-class"))) {
        el.classList.toggle(className, active);
      }
    }

    for (const el of loadingRemoveClassElements()) {
      const scope = parseSharedLoadingScope(el);
      const active = scope ? isScopeActive(scope) : false;
      for (const className of parseClassList(el.getAttribute("hyper-loading-remove-class"))) {
        el.classList.toggle(className, !active);
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

  function transferLoading(workflow, nextContext) {
    const previous = workflow.loadingContext;
    decrementMapCount(activeByKey, previous.key || "");
    decrementMapCount(activeByAction, previous.action || "");
    decrementMapCount(activeByTarget, previous.target || "");
    incrementMapCount(activeByKey, nextContext.key || "");
    incrementMapCount(activeByAction, nextContext.action || "");
    incrementMapCount(activeByTarget, nextContext.target || "");
    workflow.loadingContext = nextContext;
    setTargetBusyStates();
    setLoadingElementsVisible();
  }

  function updateHistory({ pushUrl = null, replaceUrl = null, state = {} } = {}) {
    if (replaceUrl) {
      history.replaceState(state, "", replaceUrl);
      return;
    }
    if (pushUrl) {
      history.pushState(state, "", pushUrl);
    }
  }

  function redirectTo(url) {
    if (!url) {
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
      const nonce = currentScriptNonce();
      if (nonce) {
        script.nonce = nonce;
      }
      script.addEventListener("load", () => resolve());
      script.addEventListener("error", () => reject(new Error(`Failed to load module: ${src}`)));
      document.body.appendChild(script);
    });

    loadedModuleScripts.set(src, promise);
    return promise;
  }

  function currentScriptNonce() {
    return document.querySelector("script[nonce]")?.nonce || "";
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

  function csrfTokenFromBody(body) {
    if (!body) {
      return "";
    }
    if (body instanceof FormData) {
      const token = body.get("csrfmiddlewaretoken");
      return typeof token === "string" ? token : "";
    }
    if (body instanceof URLSearchParams) {
      return body.get("csrfmiddlewaretoken") || "";
    }
    return "";
  }

  function parseXHRHeaders(rawHeaders) {
    const headers = new Headers();
    if (!rawHeaders) {
      return headers;
    }
    for (const line of rawHeaders.trim().split(/\r?\n/)) {
      const index = line.indexOf(":");
      if (index === -1) {
        continue;
      }
      const key = line.slice(0, index).trim();
      const value = line.slice(index + 1).trim();
      if (key) {
        headers.append(key, value);
      }
    }
    return headers;
  }

  function createXHRResponse(xhr) {
    const headers = parseXHRHeaders(xhr.getAllResponseHeaders());
    const bodyText = xhr.responseText || "";
    return {
      ok: xhr.status >= 200 && xhr.status < 300,
      status: xhr.status,
      statusText: xhr.statusText,
      headers,
      text: async () => bodyText,
      json: async () => JSON.parse(bodyText),
    };
  }

  function requestWithXHR(url, options, meta) {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      let streamedLength = 0;
      let sseBuffer = "";
      let streamQueue = Promise.resolve();
      xhr.open(meta.method, url, true);
      xhr.withCredentials = true;

      for (const [key, value] of Object.entries(meta.headers)) {
        xhr.setRequestHeader(key, value);
      }

      if (typeof options.onUploadProgress === "function" && xhr.upload) {
        xhr.upload.addEventListener("progress", (event) => {
          const detail = {
            id: meta.requestId,
            key: meta.requestKey,
            url,
            method: meta.method,
            loaded: event.loaded,
            total: event.total,
            lengthComputable: event.lengthComputable,
            progress: event.lengthComputable && event.total > 0 ? event.loaded / event.total : null,
            ...meta.hookMeta,
          };
          options.onUploadProgress(detail);
          emitEvent("hyper:uploadProgress", detail);
        });
      }

      xhr.addEventListener("progress", () => {
        if (!meta.expectSSE) {
          return;
        }
        const chunk = xhr.responseText.slice(streamedLength);
        streamedLength = xhr.responseText.length;
        if (!chunk) {
          return;
        }
        streamQueue = streamQueue.then(() => consumeSSEChunk(chunk, {
          buffer: sseBuffer,
          onEvent: options.onSSEEvent,
        })).then((nextBuffer) => {
          sseBuffer = nextBuffer;
        });
      });

      xhr.addEventListener("load", () => {
        streamQueue
          .then(() => consumeSSEChunk("", {
            buffer: sseBuffer,
            onEvent: options.onSSEEvent,
            flush: true,
          }))
          .then(() => resolve(createXHRResponse(xhr)))
          .catch(reject);
      });
      xhr.addEventListener("error", () => reject(new Error(`Hyper request failed: ${meta.method} ${url}`)));
      xhr.addEventListener("abort", () => reject(new DOMException("The operation was aborted.", "AbortError")));

      meta.controller.xhr = xhr;
      xhr.send(options.body);
    });
  }

  async function consumeSSEChunk(chunk, { buffer = "", onEvent = null, flush = false } = {}) {
    let pending = buffer + chunk;
    while (true) {
      const boundary = /\r\n\r\n|\n\n|\r\r/.exec(pending);
      if (!boundary) {
        break;
      }
      const rawEvent = pending.slice(0, boundary.index);
      pending = pending.slice(boundary.index + boundary[0].length);
      const parsed = parseSSEEvent(rawEvent);
      if (parsed && typeof onEvent === "function") {
        await onEvent(parsed);
      }
    }
    if (flush && pending.trim()) {
      const parsed = parseSSEEvent(pending);
      if (parsed && typeof onEvent === "function") {
        await onEvent(parsed);
      }
      pending = "";
    }
    return pending;
  }

  function parseSSEEvent(rawEvent) {
    const lines = rawEvent.split(/\r\n|\r|\n/);
    let eventName = "message";
    const dataLines = [];
    let id = "";
    let idPresent = false;
    let retry = null;
    let controlFieldSeen = false;
    for (const line of lines) {
      if (!line || line.startsWith(":")) {
        continue;
      }
      if (line.startsWith("event:")) {
        eventName = line.slice(6).trim();
        continue;
      }
      if (line.startsWith("id:")) {
        controlFieldSeen = true;
        idPresent = true;
        const nextId = line.slice(3).trimStart();
        if (!nextId.includes("\0")) {
          id = nextId;
        }
        continue;
      }
      if (line.startsWith("retry:")) {
        controlFieldSeen = true;
        const nextRetry = line.slice(6).trim();
        if (/^\d+$/.test(nextRetry)) {
          retry = Number(nextRetry);
        }
        continue;
      }
      if (line.startsWith("data:")) {
        const value = line.slice(5);
        dataLines.push(value.startsWith(" ") ? value.slice(1) : value);
      }
    }
    if (!dataLines.length) {
      return controlFieldSeen ? {
        event: eventName,
        data: null,
        id,
        idPresent,
        retry,
        controlOnly: true,
      } : null;
    }
    return {
      event: eventName,
      data: JSON.parse(dataLines.join("\n") || "{}"),
      id,
      idPresent,
      retry,
    };
  }

  async function readSSEStream(response, onEvent) {
    if (!response.body) {
      return;
    }
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { value, done } = await reader.read();
      if (done) {
        break;
      }
      buffer = await consumeSSEChunk(decoder.decode(value, { stream: true }), {
        buffer,
        onEvent,
      });
    }
    await consumeSSEChunk(decoder.decode(), { buffer, onEvent, flush: true });
  }

  function waitForRetry(delay, signal) {
    return new Promise((resolve, reject) => {
      if (signal.aborted) {
        reject(new DOMException("The operation was aborted.", "AbortError"));
        return;
      }
      const timer = setTimeout(() => {
        signal.removeEventListener("abort", onAbort);
        resolve();
      }, delay);
      const onAbort = () => {
        clearTimeout(timer);
        reject(new DOMException("The operation was aborted.", "AbortError"));
      };
      signal.addEventListener("abort", onAbort, { once: true });
    });
  }

  function waitForNetwork(signal) {
    return new Promise((resolve, reject) => {
      if (signal.aborted) {
        reject(new DOMException("The operation was aborted.", "AbortError"));
        return;
      }
      if (networkOnline) {
        resolve();
        return;
      }

      const cleanup = () => {
        window.removeEventListener("hyper:network:online", onOnline);
        signal.removeEventListener("abort", onAbort);
      };
      const onOnline = () => {
        cleanup();
        resolve();
      };
      const onAbort = () => {
        cleanup();
        reject(new DOMException("The operation was aborted.", "AbortError"));
      };
      window.addEventListener("hyper:network:online", onOnline, { once: true });
      signal.addEventListener("abort", onAbort, { once: true });
    });
  }

  function waitForVisibility(signal) {
    return new Promise((resolve, reject) => {
      if (signal.aborted) {
        reject(new DOMException("The operation was aborted.", "AbortError"));
        return;
      }
      if (!document.hidden) {
        resolve();
        return;
      }

      const cleanup = () => {
        document.removeEventListener("visibilitychange", onVisibility);
        signal.removeEventListener("abort", onAbort);
      };
      const onVisibility = () => {
        if (document.hidden) {
          return;
        }
        cleanup();
        resolve();
      };
      const onAbort = () => {
        cleanup();
        reject(new DOMException("The operation was aborted.", "AbortError"));
      };
      document.addEventListener("visibilitychange", onVisibility);
      signal.addEventListener("abort", onAbort, { once: true });
    });
  }

  async function request(url, options = {}) {
    const method = normalizeMethod(options.method);
    const headers = {
      "X-Requested-With": "XMLHttpRequest",
      ...(options.headers || {}),
    };
    const hookMeta = options.hookMeta || {};
    const requestId = options.requestId || newRequestId();
    const workflow = options.workflow || {
      loadingContext: {
        key: null,
        action: hookMeta.action || "",
        target: hookMeta.target || "",
      },
    };
    const isHandoff = options.handoff === true;
    const syncMode = normalizeSyncMode(options.sync || "replace");
    const requestKey = resolveRequestKey({
      key: options.key || null,
      hookMeta,
      url,
    });

    if (syncMode !== "none" && !isHandoff) {
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
      const csrf = csrfTokenFromCookie() || csrfTokenFromDOM() || csrfTokenFromBody(options.body);
      if (csrf && !headers["X-CSRFToken"]) {
        headers["X-CSRFToken"] = csrf;
      }
    }

    const controller = new AbortController();
    let attemptController = null;
    const requestControl = {
      xhr: null,
      abort() {
        controller.abort();
        if (attemptController) {
          attemptController.abort();
        }
        if (this.xhr) {
          this.xhr.abort();
        }
      },
    };
    if (syncMode !== "none") {
      inFlightRequests.set(requestKey, { id: requestId, controller: requestControl });
    }

    const loadingContext = {
      key: requestKey,
      action: hookMeta.action || "",
      target: hookMeta.target || "",
    };
    if (isHandoff) {
      transferLoading(workflow, loadingContext);
    } else {
      workflow.loadingContext = loadingContext;
      setLoading(true, loadingContext);
    }
    emitEvent("hyper:beforeRequest", {
      id: requestId,
      url,
      method,
      ...hookMeta,
    });

    let response;
    let aborted = false;
    try {
      try {
        const expectSSE = headers["X-Hyper-Action"] && typeof options.onSSEEvent === "function";
        const canTrackUpload =
          typeof options.onUploadProgress === "function" && method !== "GET" && method !== "HEAD" && options.body;
        let retryInterval = Number(options.sseRetryInterval ?? config.sseRetryInterval);
        const retryScaler = Number(options.sseRetryScaler ?? config.sseRetryScaler);
        const retryMaxWait = Number(options.sseRetryMaxWait ?? config.sseRetryMaxWait);
        const retryMaxCount = Number(options.sseRetryMaxCount ?? config.sseRetryMaxCount);
        const retryEnabled = resolveSSERetry(method, options.sseRetry);
        let retryCount = 0;
        let terminalEventSeen = false;
        let pauseCurrentAttempt = null;

        if (expectSSE && !headers.Accept && !headers.accept) {
          headers.Accept = "text/event-stream";
        }
        if (expectSSE && !headers["X-Hyper-Request-ID"]) {
          headers["X-Hyper-Request-ID"] = requestId;
        }

        const onSSEEvent = async (event) => {
          if (Number.isFinite(event.retry) && event.retry >= 0) {
            retryInterval = event.retry;
          }
          if (event.event === "end" || event.event === "redirect" || event.event === "switch_action") {
            terminalEventSeen = true;
          }
          if (event.controlOnly) {
            const checkpointPrefix = `${requestId}:checkpoint:`;
            const checkpointName = typeof event.id === "string" && event.id.startsWith(checkpointPrefix)
              ? event.id.slice(checkpointPrefix.length)
              : "";
            if (
              event.event === "checkpoint" &&
              event.idPresent &&
              /^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$/.test(checkpointName)
            ) {
              headers["Last-Event-ID"] = event.id;
              if (pauseCurrentAttempt) {
                pauseCurrentAttempt();
              }
            }
            return;
          }
          try {
            await options.onSSEEvent(event);
          } catch (error) {
            if (error && typeof error === "object") {
              error.hyperSSEHandlerError = true;
            }
            throw error;
          }
        };

        while (true) {
          terminalEventSeen = false;
          let hiddenPause = false;
          const currentAttemptController = new AbortController();
          attemptController = currentAttemptController;
          const abortAttempt = () => currentAttemptController.abort();
          const pauseOnHidden = Boolean(
            options.pauseWhenHidden &&
            retryEnabled &&
            expectSSE &&
            method === "GET"
          );
          const pauseAttempt = () => {
            if (
              pauseOnHidden &&
              document.hidden &&
              headers["Last-Event-ID"] &&
              !controller.signal.aborted
            ) {
              hiddenPause = true;
              currentAttemptController.abort();
            }
          };
          controller.signal.addEventListener("abort", abortAttempt, { once: true });
          if (pauseOnHidden) {
            document.addEventListener("visibilitychange", pauseAttempt);
          }
          pauseCurrentAttempt = pauseAttempt;

          try {
            const attemptOptions = expectSSE ? { ...options, onSSEEvent } : options;
            response = canTrackUpload
              ? await requestWithXHR(url, attemptOptions, {
                  method,
                  headers,
                  hookMeta,
                  requestId,
                  requestKey,
                  controller: requestControl,
                  expectSSE,
                })
              : await fetch(url, {
                  ...attemptOptions,
                  credentials: "same-origin",
                  headers,
                  signal: currentAttemptController.signal,
                });

            const contentType = response.headers.get("content-type") || "";
            if (expectSSE && contentType.includes("text/event-stream")) {
              if (!canUseXHRResponse(response)) {
                await readSSEStream(response, onSSEEvent);
              }
              if (!terminalEventSeen) {
                const error = new Error("Hyper SSE stream closed before a terminal event.");
                error.name = "SSEConnectionError";
                throw error;
              }
            }
            break;
          } catch (error) {
            if (
              hiddenPause &&
              error &&
              error.name === "AbortError" &&
              !controller.signal.aborted
            ) {
              emitEvent("hyper:requestPaused", {
                id: requestId,
                key: requestKey,
                url,
                method,
                reason: "hidden",
                ...hookMeta,
              });
              await waitForVisibility(controller.signal);
              emitEvent("hyper:requestResumed", {
                id: requestId,
                key: requestKey,
                url,
                method,
                reason: "visible",
                ...hookMeta,
              });
              continue;
            }
            if (terminalEventSeen && !(error && error.hyperSSEHandlerError)) {
              break;
            }
            const retryable = retryEnabled && expectSSE &&
              !(error && (error.name === "AbortError" || error.name === "SyntaxError" || error.hyperSSEHandlerError));
            if (retryable && !networkOnline) {
              await waitForNetwork(controller.signal);
              continue;
            }
            if (!retryable || retryCount >= retryMaxCount) {
              if (retryable) {
                emitEvent("hyper:requestRetriesFailed", {
                  id: requestId,
                  key: requestKey,
                  url,
                  method,
                  attempts: retryCount,
                  error,
                  ...hookMeta,
                });
              }
              throw error;
            }

            const delay = Math.min(retryInterval, retryMaxWait);
            retryCount += 1;
            emitEvent("hyper:requestRetry", {
              id: requestId,
              key: requestKey,
              url,
              method,
              attempt: retryCount,
              delay,
              error,
              ...hookMeta,
            });
            await waitForRetry(delay, controller.signal);
            retryInterval = Math.min(retryInterval * retryScaler, retryMaxWait);
          } finally {
            controller.signal.removeEventListener("abort", abortAttempt);
            if (pauseOnHidden) {
              document.removeEventListener("visibilitychange", pauseAttempt);
            }
            if (attemptController === currentAttemptController) {
              attemptController = null;
            }
            if (pauseCurrentAttempt === pauseAttempt) {
              pauseCurrentAttempt = null;
            }
          }
        }

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
      }

      let result;
      if (aborted) {
        result = {
          kind: "aborted",
          data: null,
          response: null,
          blocked: false,
          aborted: true,
        };
      } else {
        const contentType = response.headers.get("content-type") || "";
        if (contentType.includes("text/event-stream")) {
          result = { kind: "sse", data: null, response };
        } else if (contentType.includes("application/json")) {
          result = { kind: "json", data: await response.json(), response };
        } else {
          result = { kind: "html", data: await response.text(), response };
        }
      }

      if (typeof options.afterResponse === "function") {
        return await options.afterResponse(result);
      }
      return result;
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
      if (!isHandoff) {
        setLoading(false, workflow.loadingContext);
      }
    }
  }

  function newRequestId() {
    if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
      return crypto.randomUUID();
    }
    return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  }

  function switchError(message, context) {
    const error = new Error(message);
    error.name = "SwitchActionError";
    emitEvent("hyper:requestError", {
      id: context.requestId,
      key: context.key || null,
      url: context.url,
      method: context.method,
      status: 400,
      ok: false,
      response: null,
      kind: "switch_action",
      action: context.action,
      target: context.target || null,
      message,
      error,
    });
    return error;
  }

  function normalizeSwitchPayload(payload, context) {
    if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
      throw switchError("Malformed SwitchAction payload: expected an object.", context);
    }
    const name = typeof payload.name === "string" ? payload.name.trim() : "";
    if (!name) {
      throw switchError("Malformed SwitchAction payload: name is required.", context);
    }
    if (payload.data !== undefined && (
      payload.data === null || typeof payload.data !== "object" || Array.isArray(payload.data)
    )) {
      throw switchError("Malformed SwitchAction payload: data must be an object.", context);
    }
    const method = normalizeMethod(payload.method);
    if (method !== "GET" && method !== "POST") {
      throw switchError("Malformed SwitchAction payload: method must be GET or POST.", context);
    }
    if (payload.key !== undefined && payload.key !== null && typeof payload.key !== "string") {
      throw switchError("Malformed SwitchAction payload: key must be a string.", context);
    }
    let url = context.url;
    if (payload.url !== undefined && payload.url !== null) {
      if (typeof payload.url !== "string" || !payload.url.trim()) {
        throw switchError("Malformed SwitchAction payload: url must be a non-empty string.", context);
      }
      const parsed = new URL(payload.url, window.location.href);
      if (parsed.origin !== window.location.origin) {
        throw switchError("SwitchAction URL must use the current origin.", context);
      }
      url = `${parsed.pathname}${parsed.search}${parsed.hash}`;
    }
    return {
      name,
      data: payload.data || {},
      method,
      url,
      key: payload.key == null || payload.key === "" ? context.key : payload.key,
    };
  }

  function canUseXHRResponse(response) {
    return !response.body && typeof response.text === "function";
  }

  function dispatchStreamEvent(event, context) {
    const streamEvent = new CustomEvent("hyper:streamEvent", {
      detail: {
        event: event.event,
        data: event.data || {},
        action: context.action || null,
        key: context.key || null,
        requestId: context.requestId || null,
        switchDepth: context.switchDepth || 0,
        sourceEl: context.sourceEl || null,
      },
    });
    window.dispatchEvent(streamEvent);
  }

  function applyToasts(toasts) {
    if (!Array.isArray(toasts) || toasts.length === 0) {
      return;
    }

    for (const toast of toasts) {
      window.dispatchEvent(new CustomEvent("hyper:toast", { detail: toast }));
    }
  }

  async function handleActionStreamEvent(event, context) {
    const payload = event.data || {};
    dispatchStreamEvent(event, context);
    switch (event.event) {
      case "patch_signals":
      case "init_signals": {
        return;
      }
      case "toast": {
        applyToasts([payload]);
        return;
      }
      case "dispatch_event": {
        const eventTarget = payload.target ? document.querySelector(payload.target) : window;
        if (!eventTarget) {
          return;
        }
        eventTarget.dispatchEvent(
          new CustomEvent(payload.name, {
            detail: payload.payload || {},
            bubbles: true,
          })
        );
        return;
      }
      case "history": {
        updateHistory({
          pushUrl: payload.push_url || null,
          replaceUrl: payload.replace_url || null,
        });
        return;
      }
      case "patch_html": {
        const resolvedTarget = payload.target || context.target || null;
        const resolvedSwap = payload.swap || context.swap || "outer";
        const resolvedStrategy = payload.strategy || context.strategy || "auto";
        const resolvedTransition =
          payload.transition === undefined ? context.transition : Boolean(payload.transition);
        const resolvedFocus = payload.focus || context.focus || "preserve";
        const resolvedSwapDelay = parseDelay(payload.swap_delay, parseDelay(context.swapDelay, 0));
        const resolvedSettleDelay = parseDelay(
          payload.settle_delay,
          parseDelay(context.settleDelay, 0)
        );
        const strict = strictTargetsEnabled(
          payload.strict_targets === undefined ? context.strictTargets : Boolean(payload.strict_targets)
        );
        const swapMode = normalizeSwap(resolvedSwap);
        const hasHtml = typeof payload.content === "string";
        const canSwapWithoutHtml = swapMode === "delete" || swapMode === "none";
        await applySwapLifecycle({
          target: resolvedTarget,
          swapDelay: resolvedSwapDelay,
          settleDelay: resolvedSettleDelay,
          detail: {
            action: context.action,
            swap: resolvedSwap,
            strategy: resolvedStrategy,
          },
          focus: resolvedFocus,
          mutate: async () => {
            await withViewTransition(resolvedTransition, async () => {
              if (resolvedTarget && (hasHtml || canSwapWithoutHtml)) {
                const ok = await applySwap(
                  resolvedTarget,
                  hasHtml ? payload.content : "",
                  resolvedSwap,
                  { strategy: resolvedStrategy }
                );
                if (!ok && strict) {
                  throw new Error(`Hyper target not found: ${resolvedTarget}`);
                }
              }
            });
          },
        });
        return;
      }
      case "load_js": {
        await ensureModuleScript(payload.src || null);
        return;
      }
      case "error": {
        window.dispatchEvent(
          new CustomEvent("hyper:requestError", {
            detail: {
              id: null,
              key: context.key || null,
              url: context.url || window.location.pathname,
              method: context.method || "GET",
              status: payload.status || null,
              ok: false,
              response: null,
              kind: "action",
              action: context.action,
              target: context.target || null,
              message: payload.message || "",
            },
          })
        );
        return;
      }
      case "redirect": {
        redirectTo(payload.url);
        return;
      }
      case "end":
      default:
        return;
    }
  }

  function swapHTML(target, html) {
    const el = typeof target === "string" ? document.querySelector(target) : target;
    if (!el) {
      return;
    }
    el.innerHTML = html;
  }

  function getMorpher() {
    if (window.Alpine && typeof window.Alpine.morph === "function") {
      return {
        inner(el, html) {
          const shadow = el.cloneNode(false);
          shadow.innerHTML = html;
          window.Alpine.morph(el, shadow.outerHTML);
        },
        outer(el, html) {
          window.Alpine.morph(el, html);
        },
      };
    }

    if (typeof window.morphdom === "function") {
      return {
        inner(el, html) {
          const shadow = document.createElement(el.tagName.toLowerCase());
          shadow.innerHTML = html;
          window.morphdom(el, shadow, { childrenOnly: true });
        },
        outer(el, html) {
          const next = toElement(html);
          if (!next) {
            el.remove();
            return;
          }
          window.morphdom(el, next);
        },
      };
    }

    return null;
  }

  function toElement(html) {
    const template = document.createElement("template");
    template.innerHTML = html.trim();
    const first = template.content.firstElementChild;
    return first || null;
  }

  function parseFullDocument(html, baseUrl = window.location.href) {
    if (typeof html !== "string" || !/<(?:!doctype|html|head|body)[\s>]/i.test(html)) {
      return null;
    }
    const parser = new DOMParser();
    const doc = parser.parseFromString(html, "text/html");
    if (!doc || !doc.body) {
      return null;
    }
    doc.__hyperBaseUrl = baseUrl;
    return doc;
  }

  function selectResponseFragment(doc, selector, swap = "inner") {
    if (!selector) {
      return null;
    }
    let matches;
    try {
      matches = doc.querySelectorAll(selector);
    } catch (error) {
      throw new Error(`Invalid hyper-select selector "${selector}".`, { cause: error });
    }
    if (matches.length !== 1) {
      throw new Error(
        `Expected hyper-select "${selector}" to match exactly one response element; found ${matches.length}.`
      );
    }
    return normalizeSwap(swap) === "inner" ? matches[0].innerHTML : matches[0].outerHTML;
  }

  function isHeadAsset(node) {
    return node instanceof Element && node.matches("base, meta, link, style, script");
  }

  function absoluteHeadUrl(node, attribute) {
    const value = node.getAttribute(attribute);
    if (!value) {
      return "";
    }
    const baseUrl = node.ownerDocument.__hyperBaseUrl || node.ownerDocument.baseURI || window.location.href;
    try {
      return new URL(value, baseUrl).href;
    } catch (_error) {
      return value;
    }
  }

  function headAssetIdentity(node) {
    const tag = node.tagName.toLowerCase();
    if (tag === "script") {
      const src = absoluteHeadUrl(node, "src");
      return src
        ? `script:${node.getAttribute("type") || ""}:${src}`
        : `script:inline:${node.getAttribute("type") || ""}:${node.textContent || ""}`;
    }
    if (tag === "link") {
      return [
        "link",
        node.getAttribute("rel") || "",
        absoluteHeadUrl(node, "href"),
        node.getAttribute("as") || "",
        node.getAttribute("media") || "",
      ].join(":");
    }
    if (tag === "meta") {
      return [
        "meta",
        node.getAttribute("charset") || "",
        node.getAttribute("name") || "",
        node.getAttribute("property") || "",
        node.getAttribute("http-equiv") || "",
        node.getAttribute("content") || "",
      ].join(":");
    }
    if (tag === "base") {
      return `base:${absoluteHeadUrl(node, "href")}`;
    }
    return `${tag}:${node.getAttribute("type") || ""}:${node.textContent || ""}`;
  }

  function cloneHeadAsset(node) {
    if (node.tagName.toLowerCase() === "script") {
      const script = document.createElement("script");
      copyScriptAttributes(node, script);
      if (node.hasAttribute("src")) {
        script.src = absoluteHeadUrl(node, "src");
      }
      script.textContent = node.textContent || "";
      return script;
    }
    const clone = document.importNode(node, true);
    if (node.hasAttribute("href")) {
      clone.setAttribute("href", absoluteHeadUrl(node, "href"));
    }
    return clone;
  }

  function appendHeadAsset(node) {
    const waitsForLoad =
      (node.tagName.toLowerCase() === "script" && node.hasAttribute("src")) ||
      (node.tagName.toLowerCase() === "link" && node.rel.toLowerCase() === "stylesheet");
    if (!waitsForLoad) {
      document.head.appendChild(node);
      return Promise.resolve();
    }
    return new Promise((resolve) => {
      node.addEventListener("load", resolve, { once: true });
      node.addEventListener("error", resolve, { once: true });
      document.head.appendChild(node);
    });
  }

  async function reconcileHead(doc) {
    if (!doc || !doc.head) {
      return;
    }
    const mode = (doc.head.getAttribute("hyper-head") || "merge").trim().toLowerCase();
    if (mode === "ignore") {
      return;
    }
    if (!["merge", "append"].includes(mode)) {
      throw new Error(`Unsupported hyper-head mode "${mode}".`);
    }


    document.title = doc.title;
    const currentByIdentity = new Map();
    for (const node of Array.from(document.head.children).filter(isHeadAsset)) {
      const identity = headAssetIdentity(node);
      const nodes = currentByIdentity.get(identity) || [];
      nodes.push(node);
      currentByIdentity.set(identity, nodes);
    }

    const kept = new Set();
    const nextManaged = mode === "append" ? new Set(managedHeadNodes) : new Set();
    const added = [];
    const keptIdentities = [];
    for (const incoming of Array.from(doc.head.children).filter(isHeadAsset)) {
      const identity = headAssetIdentity(incoming);
      const matches = currentByIdentity.get(identity);
      const existing = matches && matches.shift();
      if (existing) {
        kept.add(existing);
        nextManaged.add(existing);
        keptIdentities.push(identity);
        continue;
      }
      const clone = cloneHeadAsset(incoming);
      await appendHeadAsset(clone);
      nextManaged.add(clone);
      added.push(identity);
    }

    const removed = [];
    if (mode === "merge") {
      for (const node of managedHeadNodes) {
        if (!kept.has(node) && node.isConnected && !node.hasAttribute("hyper-preserve")) {
          removed.push(headAssetIdentity(node));
          node.remove();
        } else if (node.isConnected && node.hasAttribute("hyper-preserve")) {
          nextManaged.add(node);
        }
      }
    }
    managedHeadNodes = nextManaged;
    emitEvent("hyper:head:reconciled", {
      mode,
      added,
      kept: keptIdentities,
      removed,
    });
  }

  function syncAttributes(el, nextEl) {
    for (const attr of Array.from(el.attributes)) {
      el.removeAttribute(attr.name);
    }
    for (const attr of Array.from(nextEl.attributes)) {
      el.setAttribute(attr.name, attr.value);
    }
  }

  function normalizeBodySwapHTML(el, html, mode, fullDocument = null) {
    if (el !== document.body || mode !== "inner") {
      return { html, activateScripts: false };
    }
    const doc = fullDocument || parseFullDocument(html);
    if (!doc) {
      return { html, activateScripts: false };
    }
    syncAttributes(document.body, doc.body);
    return { html: doc.body.innerHTML, activateScripts: true };
  }

  function scriptSrcs(root = document) {
    return new Set(
      Array.from(root.querySelectorAll("script[src]")).map((script) => script.src)
    );
  }

  function isExecutableScript(script) {
    const type = (script.getAttribute("type") || "").trim().toLowerCase();
    return [
      "",
      "module",
      "text/javascript",
      "application/javascript",
      "text/ecmascript",
      "application/ecmascript",
    ].includes(type);
  }

  function copyScriptAttributes(fromScript, toScript) {
    for (const attr of Array.from(fromScript.attributes)) {
      if (attr.name.toLowerCase() === "nonce") {
        continue;
      }
      toScript.setAttribute(attr.name, attr.value);
    }

    // Browsers intentionally hide nonce values from getAttribute() in some
    // contexts, but expose them through the nonce property for CSP propagation.
    const nonce = fromScript.nonce || currentScriptNonce();
    if (nonce) {
      toScript.nonce = nonce;
    }
  }

  function activateScripts(root, previousSrcs = new Set()) {
    const scripts = Array.from(root.querySelectorAll("script"));
    for (const inertScript of scripts) {
      if (!isExecutableScript(inertScript)) {
        continue;
      }
      if (inertScript.src && previousSrcs.has(inertScript.src)) {
        continue;
      }

      const script = document.createElement("script");
      copyScriptAttributes(inertScript, script);
      script.textContent = inertScript.textContent || "";
      inertScript.replaceWith(script);
    }
  }

  function morphInner(el, html, strategy = "auto") {
    // Automatic full-page visits preserve the body node and delegated runtime
    // listeners. An explicit morph strategy delegates body handling to the
    // installed adapter.
    if (strategy === "replace" || (el === document.body && strategy === "auto")) {
      swapHTML(el, html);
      return;
    }

    const morpher = getMorpher();
    if (!morpher) {
      if (strategy === "morph") {
        throw new Error("Hyper morph strategy requires Alpine Morph or morphdom.");
      }
      swapHTML(el, html);
      return;
    }
    morpher.inner(el, html);
  }

  function morphOuter(el, html, strategy = "auto") {
    if (strategy === "replace") {
      el.outerHTML = html;
      return;
    }
    const morpher = getMorpher();
    if (!morpher) {
      if (strategy === "morph") {
        throw new Error("Hyper morph strategy requires Alpine Morph or morphdom.");
      }
      el.outerHTML = html;
      return;
    }
    morpher.outer(el, html);
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


  function normalizeStrategy(strategy) {
    const value = String(strategy || "auto").trim().toLowerCase();
    if (!["auto", "morph", "replace"].includes(value)) {
      throw new Error(`Unsupported Hyper patch strategy "${value}".`);
    }
    return value;
  }

  function preparePreservedIslands(el, html, mode) {
    if (!["inner", "outer"].includes(mode)) {
      return { html, restore() {}, skip: false };
    }

    const incomingRoot = document.createElement("template");
    incomingRoot.innerHTML = html;
    if (
      el.matches("[hyper-preserve][id]") &&
      incomingRoot.content.firstElementChild &&
      incomingRoot.content.firstElementChild.id === el.id
    ) {
      return { html, restore() {}, skip: true };
    }

    const preserved = Array.from(el.querySelectorAll("[hyper-preserve][id]"));
    const records = [];
    for (const node of preserved) {
      const incoming = incomingRoot.content.querySelector(`#${CSS.escape(node.id)}`);
      if (!incoming) {
        continue;
      }
      const slot = `hyper-preserve-${preserveSlotCounter++}`;
      const currentMarker = document.createElement("template");
      currentMarker.dataset.hyperPreserveSlot = slot;
      const incomingMarker = document.createElement("template");
      incomingMarker.dataset.hyperPreserveSlot = slot;
      node.replaceWith(currentMarker);
      incoming.replaceWith(incomingMarker);
      records.push({ node, currentMarker, slot });
    }

    return {
      html: incomingRoot.innerHTML,
      skip: false,
      restore() {
        for (const record of records) {
          const selector = `template[data-hyper-preserve-slot="${record.slot}"]`;
          const liveMarker = document.querySelector(selector);
          if (liveMarker) {
            liveMarker.replaceWith(record.node);
          } else if (record.currentMarker.isConnected) {
            record.currentMarker.replaceWith(record.node);
          }
        }
      },
    };
  }
  async function applySwap(target, html, swap = "inner", options = {}) {
    const el = typeof target === "string" ? document.querySelector(target) : target;
    if (!el) {
      return false;
    }

    const mode = normalizeSwap(swap);
    const strategy = normalizeStrategy(options.strategy);
    const fullDocument = options.document || parseFullDocument(html, options.responseUrl);
    if (fullDocument) {
      await reconcileHead(fullDocument);
    }
    const normalized = normalizeBodySwapHTML(el, html, mode, fullDocument);
    const previousScriptSrcs = normalized.activateScripts ? scriptSrcs() : new Set();

    if (mode === "none") {
      return true;
    }
    if (mode === "delete") {
      el.remove();
      return true;
    }

    const preserved = preparePreservedIslands(el, normalized.html, mode);
    if (preserved.skip) {
      return true;
    }
    try {
      if (mode === "outer") {
        morphOuter(el, preserved.html, strategy);
        return true;
      }
      if (mode === "before") {
        el.insertAdjacentHTML("beforebegin", normalized.html);
        return true;
      }
      if (mode === "after") {
        el.insertAdjacentHTML("afterend", normalized.html);
        return true;
      }
      if (mode === "prepend") {
        el.insertAdjacentHTML("afterbegin", normalized.html);
        return true;
      }
      if (mode === "append") {
        el.insertAdjacentHTML("beforeend", normalized.html);
        return true;
      }

      morphInner(el, preserved.html, strategy);
      if (normalized.activateScripts) {
        activateScripts(el, previousScriptSrcs);
      }
      return true;
    } finally {
      preserved.restore();
    }
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
    const nodes = root.querySelectorAll("[hyper-view-transition-name], [hyper-view-name]");
    for (const node of nodes) {
      const name = (
        node.getAttribute("hyper-view-transition-name") ||
        node.getAttribute("hyper-view-name") ||
        ""
      ).trim();
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
      applyNetworkState(document);
      applyFocus(focus, target, focusState);
      initLazyActions(document);
      return;
    }

    el.classList.add("hyper-swapping");
    emitEvent("hyper:swap:start", { target, ...detail });

    try {
      await sleep(swapDelay);
      await mutate();
      applyViewNames(resolveElement(target) || document);
      applyNetworkState(document);
      applyFocus(focus, target, focusState);
      emitEvent("hyper:swap:end", { target, ...detail });
      el.classList.remove("hyper-swapping");
      el.classList.add("hyper-settling");
      initLazyActions(resolveElement(target) || document);
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

  async function handleActionResult(result, context) {
    const {
      action,
      key,
      resolvedUrl,
      target,
      swap,
      strategy,
      transition,
      push,
      replace,
      strictTargets,
      swapDelay,
      settleDelay,
      focus,
      sourceEl,
      streamedEvents,
    } = context;

    if (result.blocked || result.aborted) {
      return result;
    }

    if (result.kind === "sse") {
      if (!result.response.ok && streamedEvents.length === 0) {
        throw new Error(
          `Hyper action '${action}' failed: ${result.response.status} ${result.response.statusText}`
        );
      }
      return { events: streamedEvents, ok: result.response.ok, status: result.response.status };
    }

    if (result.kind === "json") {
      if (result.data.redirect_to) {
        redirectTo(result.data.redirect_to);
        return result.data;
      }

      if (result.data.signals) {
        dispatchStreamEvent(
          { event: "patch_signals", data: result.data.signals },
          { sourceEl, action, key }
        );
      }
      applyToasts(result.data.toasts);
      const inferredTarget = result.data.target ? null : inferTargetFromHTML(result.data.html);
      const resolvedTarget = target || result.data.target || inferredTarget || null;
      const resolvedSwap = result.data.swap || swap || "outer";
      const resolvedStrategy = result.data.strategy || strategy || "auto";
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
          strategy: resolvedStrategy,
        },
        focus: resolvedFocus,
        mutate: async () => {
          await withViewTransition(resolvedTransition, async () => {
            if (resolvedTarget && (hasHtml || canSwapWithoutHtml)) {
              const ok = await applySwap(
                resolvedTarget,
                hasHtml ? result.data.html : "",
                resolvedSwap,
                { strategy: resolvedStrategy }
              );
              if (!ok && strict) {
                throw new Error(`Hyper target not found: ${resolvedTarget}`);
              }
            }
          });
        },
      });
      await ensureModuleScript(result.data.js || null);
      const handled = Boolean(
        result.data.redirect_to ||
          result.data.signals ||
          result.data.toasts ||
          result.data.html ||
          result.data.js ||
          result.data.push_url ||
          result.data.replace_url ||
          resolvedTarget
      );

      if (!result.response.ok && !handled) {
        throw new Error(
          `Hyper action '${action}' failed: ${result.response.status} ${result.response.statusText}`
        );
      }

      return result.data;
    }

    if (target) {
      const strict = strictTargetsEnabled(strictTargets);
      await applySwapLifecycle({
        target,
        swapDelay: parseDelay(swapDelay, 0),
        settleDelay: parseDelay(settleDelay, 0),
        detail: { action, swap, strategy },
        focus,
        mutate: async () => {
          await withViewTransition(transition, async () => {
            const ok = await applySwap(target, result.data, swap, { strategy });
            if (!ok && strict) {
              throw new Error(`Hyper target not found: ${target}`);
            }
          });
        },
      });
      return result.data;
    }

    if (!result.response.ok) {
      throw new Error(
        `Hyper action '${action}' failed: ${result.response.status} ${result.response.statusText}`
      );
    }

    return result.data;
  }

  async function runAction({
    url,
    action,
    target,
    method = "POST",
    body = null,
    sourceEl = null,
    kwargs = null,
    swap = "inner",
    strategy = "auto",
    transition = false,
    push = false,
    replace = false,
    sync = "replace",
    key = null,
    strictTargets = undefined,
    swapDelay = 0,
    settleDelay = 0,
    focus = "preserve",
    onUploadProgress = null,
    retry = undefined,
    pauseWhenHidden = false,
    requestId = null,
    switchDepth = 0,
    workflow = null,
    handoff = false,
  }) {
    method = normalizeMethod(method, "POST");
    const resolvedUrl = url || window.location.pathname;
    const resolvedRequestId = requestId || newRequestId();
    const resolvedWorkflow = workflow || { loadingContext: {} };
    const resolvedKey = key || resolveRequestKey({
      key: null,
      hookMeta: { kind: "action", action, sourceEl },
      url: resolvedUrl,
    });
    const streamedEvents = [];
    let switchedAction = null;
    const headers = {
      "X-Hyper-Action": action,
    };
    if (switchDepth > 0) {
      headers["X-Hyper-Switch-Depth"] = String(switchDepth);
    }
    if (kwargs && typeof kwargs === "object") {
      headers["X-Hyper-Data"] = JSON.stringify(kwargs);
    }
    if (target) {
      headers["X-Hyper-Target"] = target;
    }

    return request(resolvedUrl, {
      method,
      headers,
      body,
      sseRetry: retry,
      pauseWhenHidden,
      onUploadProgress,
      onSSEEvent: async (event) => {
        streamedEvents.push(event);
        if (event.event === "switch_action") {
          if (switchedAction) {
            throw switchError("Malformed action stream: more than one SwitchAction was received.", {
              requestId: resolvedRequestId,
              action,
              key: resolvedKey,
              url: resolvedUrl,
              method,
              target,
            });
          }
          switchedAction = normalizeSwitchPayload(event.data, {
            requestId: resolvedRequestId,
            action,
            key: resolvedKey,
            url: resolvedUrl,
            method,
            target,
          });
        }
        await handleActionStreamEvent(event, {
          action,
          key: resolvedKey,
          url: resolvedUrl,
          method,
          target,
          swap,
          strategy,
          transition,
          focus,
          swapDelay,
          settleDelay,
          strictTargets,
          sourceEl,
          requestId: resolvedRequestId,
          switchDepth,
        });
      },
      hookMeta: {
        kind: "action",
        action,
        target: target || null,
        sourceEl,
      },
      sync,
      key: resolvedKey,
      requestId: resolvedRequestId,
      workflow: resolvedWorkflow,
      handoff,
      afterResponse: async (result) => {
        const handled = await handleActionResult(result, {
          action,
          key: resolvedKey,
          resolvedUrl,
          target,
          swap,
          strategy,
          transition,
          push,
          replace,
          strictTargets,
          swapDelay,
          settleDelay,
          focus,
          sourceEl,
          streamedEvents,
        });
        if (!switchedAction || result.blocked || result.aborted) {
          return handled;
        }

        const nextDepth = switchDepth + 1;
        if (nextDepth > config.switchActionMaxDepth) {
          throw switchError("Hyper action switch depth limit exceeded.", {
            requestId: resolvedRequestId,
            action,
            key: resolvedKey,
            url: resolvedUrl,
            method,
            target,
          });
        }
        const nextRequestId = newRequestId();
        emitEvent("hyper:actionSwitch", {
          originalAction: action,
          destinationAction: switchedAction.name,
          originalRequestId: resolvedRequestId,
          newRequestId: nextRequestId,
          key: switchedAction.key || null,
          method: switchedAction.method,
          url: switchedAction.url,
          retry: resolveSSERetry(switchedAction.method),
          depth: nextDepth,
        });
        return runAction({
          url: switchedAction.url,
          action: switchedAction.name,
          method: switchedAction.method,
          kwargs: switchedAction.data,
          body: switchedAction.method === "POST"
            ? buildActionSearchParams(switchedAction.name, switchedAction.data)
            : null,
          sourceEl,
          target,
          swap,
          strategy,
          transition,
          push: false,
          replace: false,
          sync,
          key: switchedAction.key,
          strictTargets,
          swapDelay,
          settleDelay,
          focus,
          pauseWhenHidden: switchedAction.method === "GET" ? pauseWhenHidden : false,
          requestId: nextRequestId,
          switchDepth: nextDepth,
          workflow: resolvedWorkflow,
          handoff: true,
        });
      },
    });
  }

  async function handleVisitResult(result, {
    url,
    target,
    push,
    swap,
    strategy,
    select,
    transition,
    swapDelay,
    settleDelay,
    strictTargets,
    focus,
  }) {
    if (result.blocked || result.aborted) {
      return result;
    }

    const strict = strictTargetsEnabled(strictTargets);
    const resolvedSwapDelay = parseDelay(swapDelay, 0);
    const resolvedSettleDelay = parseDelay(settleDelay, 0);

    if (result.kind === "json") {
      if (result.data.signals) {
        dispatchStreamEvent(
          { event: "patch_signals", data: result.data.signals },
          { sourceEl: null, action: null, key: null }
        );
      }
      const resolvedTarget = target || result.data.target || null;
      const resolvedSwap = result.data.swap || swap || "inner";
      const resolvedStrategy = result.data.strategy || strategy || "auto";
      const resolvedTransition =
        result.data.transition === undefined ? transition : Boolean(result.data.transition);
      const resolvedFocus = result.data.focus || focus || "preserve";
      const fullDocument = parseFullDocument(
        result.data.html,
        result.response.url || url
      );
      const selectedHTML = select
        ? selectResponseFragment(fullDocument || document.implementation.createHTMLDocument(), select, resolvedSwap)
        : result.data.html;
      await applySwapLifecycle({
        target: resolvedTarget,
        swapDelay: parseDelay(result.data.swap_delay, resolvedSwapDelay),
        settleDelay: parseDelay(result.data.settle_delay, resolvedSettleDelay),
        detail: { kind: "visit", swap: resolvedSwap, strategy: resolvedStrategy, select },
        focus: resolvedFocus,
        mutate: async () => {
          await withViewTransition(resolvedTransition, async () => {
            if (resolvedTarget && typeof selectedHTML === "string") {
              const ok = await applySwap(resolvedTarget, selectedHTML, resolvedSwap, {
                strategy: resolvedStrategy,
                document: fullDocument,
                responseUrl: result.response.url || url,
              });
              if (!ok && strict) {
                throw new Error(`Hyper target not found: ${resolvedTarget}`);
              }
            }
          });
        },
      });
    } else if (target) {
      const fullDocument = parseFullDocument(result.data, result.response.url || url);
      const selectedHTML = select
        ? selectResponseFragment(fullDocument || document.implementation.createHTMLDocument(), select, swap)
        : result.data;
      await applySwapLifecycle({
        target,
        swapDelay: resolvedSwapDelay,
        settleDelay: resolvedSettleDelay,
        detail: { kind: "visit", swap, strategy, select },
        focus,
        mutate: async () => {
          await withViewTransition(transition, async () => {
            const ok = await applySwap(target, selectedHTML, swap, {
              strategy,
              document: fullDocument,
              responseUrl: result.response.url || url,
            });
            if (!ok && strict) {
              throw new Error(`Hyper target not found: ${target}`);
            }
          });
        },
      });
    }

    if (push) {
      history.pushState({
        hyper: {
          target,
          select,
          swap,
          strategy,
          transition,
          swapDelay,
          settleDelay,
          focus,
        },
      }, "", url);
    }
  }


  async function visit({
    url,
    target,
    push = true,
    sync = "replace",
    key = null,
    swap = "inner",
    strategy = "auto",
    select = null,
    transition = false,
    swapDelay = 0,
    settleDelay = 0,
    strictTargets = undefined,
    focus = "preserve",
  }) {
    return request(url, {
      method: "GET",
      hookMeta: {
        kind: "visit",
        target: target || null,
      },
      sync,
      key,
      afterResponse: async (result) => handleVisitResult(result, {
        url,
        target,
        push,
        swap,
        strategy,
        select,
        transition,
        swapDelay,
        settleDelay,
        strictTargets,
        focus,
      }),
    });
  }

  async function navigate(
    url,
    {
      target = "body",
      push = true,
      sync = "replace",
      key = null,
      swap = "inner",
      strategy = "auto",
      select = null,
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
      strategy,
      select,
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
      const select = link.getAttribute("hyper-select") || null;
      const swap = link.getAttribute("hyper-swap") || "inner";
      const strategy = link.getAttribute("hyper-strategy") || "auto";
      const transition = attrBool(link, "hyper-transition", false);
      const swapDelay = parseDelay(link.getAttribute("hyper-swap-delay"), 0);
      const settleDelay = parseDelay(link.getAttribute("hyper-settle-delay"), 0);
      const focus = link.getAttribute("hyper-focus") || "preserve";
      navigate(href, {
        target,
        push: true,
        sync: link.getAttribute("hyper-sync") || "replace",
        key: link.getAttribute("hyper-key") || null,
        select,
        swap,
        strategy,
        strictTargets: link.hasAttribute("hyper-strict-targets")
          ? attrBool(link, "hyper-strict-targets", true)
          : undefined,
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
      const select = form.getAttribute("hyper-select") || null;
      const swap = form.getAttribute("hyper-swap") || "inner";
      const strategy = form.getAttribute("hyper-strategy") || "auto";
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
          select,
          swap,
          strategy,
          strictTargets: form.hasAttribute("hyper-strict-targets")
            ? attrBool(form, "hyper-strict-targets", true)
            : undefined,
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
        afterResponse: async (result) => {
          if (result.blocked || result.aborted) {
            return result;
          }
          if (result.kind === "html") {
            const fullDocument = parseFullDocument(result.data, result.response.url || action);
            const selectedHTML = select
              ? selectResponseFragment(
                  fullDocument || document.implementation.createHTMLDocument(),
                  select,
                  swap
                )
              : result.data;
            await applySwapLifecycle({
              target,
              swapDelay,
              settleDelay,
              focus,
              detail: { kind: "nav-form", swap, strategy, select },
              mutate: async () => {
                await withViewTransition(transition, async () => {
                  await applySwap(target, selectedHTML, swap, {
                    strategy,
                    document: fullDocument,
                    responseUrl: result.response.url || action,
                  });
                });
              },
            });
            history.pushState({
              hyper: { target, select, swap, strategy, transition, swapDelay, settleDelay, focus },
            }, "", action);
          }
          return result;
        },
      });
    });

    window.addEventListener("popstate", async (event) => {
      const restored = event.state && event.state.hyper ? event.state.hyper : {};
      const target =
        restored.target || document.body.getAttribute("hyper-pop-target") || "body";
      const url = window.location.pathname + window.location.search;
      const detail = { url, target, state: event.state };
      emitHistoryRestoreEvent("hyper:history:restore:before", detail);
      try {
        await navigate(url, { ...restored, target, push: false });
        emitHistoryRestoreEvent("hyper:history:restore:after", { ...detail, success: true });
      } catch (error) {
        emitHistoryRestoreEvent("hyper:history:restore:after", {
          ...detail,
          success: false,
          error,
        });
        throw error;
      }
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
      const strategy = form.getAttribute("hyper-strategy") || "auto";
      const transition = attrBool(form, "hyper-transition", false);
      const sync = form.getAttribute("hyper-sync") || "block";
      const key = (form.getAttribute("hyper-key") || action).trim();
      const strictTargets = attrBool(form, "hyper-strict-targets", false);
      const swapDelay = parseDelay(form.getAttribute("hyper-swap-delay"), 0);
      const settleDelay = parseDelay(form.getAttribute("hyper-settle-delay"), 0);
      const focus = form.getAttribute("hyper-focus") || "preserve";
      const pauseWhenHidden = attrBool(form, "hyper-pause-when-hidden", false);

      const req = actionRequest(
        action,
        {},
        {
          form,
          method,
          url,
          target,
          swap,
          strategy,
          transition,
          sync,
          key,
          strictTargets,
          swapDelay,
          settleDelay,
          focus,
          pauseWhenHidden,
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
    const inferredMethod = form ? form.getAttribute("method") || "GET" : "GET";
    const method = normalizeMethod(options.method, inferredMethod);
    const url =
      options.url ||
      (form ? form.getAttribute("action") || window.location.pathname : window.location.pathname);
    const sync = options.sync || (form ? "block" : "replace");
    const key = options.key || null;
    const sourceEl = resolveSourceEl(options.sourceEl || null);
    const onUploadProgress = options.onUploadProgress || null;
    const retry = typeof options.retry === "boolean"
      ? options.retry
      : typeof options.sseRetry === "boolean" ? options.sseRetry : undefined;
    const extraData = data && typeof data === "object" ? data : null;
    const actionOptions = {
      target: options.target || null,
      swap: options.swap || "inner",
      strategy: options.strategy || "auto",
      transition: Boolean(options.transition),
      push: Boolean(options.push),
      replace: Boolean(options.replace),
      strictTargets: options.strictTargets,
      swapDelay: options.swapDelay || 0,
      settleDelay: options.settleDelay || 0,
      focus: options.focus || "preserve",
      retry,
      pauseWhenHidden: Boolean(options.pauseWhenHidden),
    };

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
          sync,
          key,
          sourceEl,
          onUploadProgress,
          kwargs: formToKwargs(payload),
          ...actionOptions,
        });
      }
      return runAction({
        url,
        action,
        method,
        sync,
        key,
        sourceEl,
        onUploadProgress,
        body: payload,
        ...actionOptions,
      });
    }

    if (method !== "GET" && method !== "HEAD") {
      return runAction({
        url,
        action,
        method,
        sourceEl,
        kwargs: extraData,
        body: buildActionSearchParams(action, extraData),
        sync,
        key,
        onUploadProgress,
        ...actionOptions,
      });
    }

    return runAction({
      url,
      action,
      method,
      sourceEl,
      kwargs: extraData,
      sync,
      key,
      onUploadProgress,
      ...actionOptions,
    });
  }

  function lazyActionData(el) {
    const raw = el.getAttribute("hyper-action-data");
    if (!raw) {
      return {};
    }
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      throw new Error("hyper-action-data must be a JSON object.");
    }
    return parsed;
  }

  async function loadLazyAction(el) {
    const action = (el.getAttribute("hyper-action") || "").trim();
    if (!action) {
      return;
    }
    const target = el.getAttribute("hyper-target") || (el.id ? `#${CSS.escape(el.id)}` : null);
    if (!target) {
      throw new Error("Visible hyper-actions require an id or hyper-target.");
    }
    el.setAttribute("hyper-lazy-state", "loading");
    emitEvent("hyper:lazy:start", { action, target, element: el });
    try {
      const result = await actionRequest(action, lazyActionData(el), {
        method: "GET",
        sourceEl: el,
        target,
        swap: el.getAttribute("hyper-swap") || "inner",
        strategy: el.getAttribute("hyper-strategy") || "auto",
        transition: attrBool(el, "hyper-transition", false),
        sync: el.getAttribute("hyper-sync") || "replace",
        key: el.getAttribute("hyper-key") || action,
        strictTargets: el.hasAttribute("hyper-strict-targets")
          ? attrBool(el, "hyper-strict-targets", true)
          : undefined,
        swapDelay: parseDelay(el.getAttribute("hyper-swap-delay"), 0),
        settleDelay: parseDelay(el.getAttribute("hyper-settle-delay"), 0),
        focus: el.getAttribute("hyper-focus") || "preserve",
        retry: el.hasAttribute("hyper-retry")
          ? attrBool(el, "hyper-retry", true)
          : undefined,
        pauseWhenHidden: attrBool(el, "hyper-pause-when-hidden", false),
      });
      el.setAttribute("hyper-lazy-state", "loaded");
      emitEvent("hyper:lazy:success", { action, target, element: el, result });
    } catch (error) {
      el.setAttribute("hyper-lazy-state", "error");
      emitEvent("hyper:lazy:error", { action, target, element: el, error });
      throw error;
    }
  }

  function initLazyActions(root = document) {
    if (typeof IntersectionObserver !== "function") {
      return;
    }
    if (!lazyActionObserver) {
      lazyActionObserver = new IntersectionObserver((entries) => {
        for (const entry of entries) {
          if (!entry.isIntersecting) {
            continue;
          }
          lazyActionObserver.unobserve(entry.target);
          loadLazyAction(entry.target).catch(() => {});
        }
      }, { rootMargin: "0px 0px 200px 0px" });
    }

    const candidates = [];
    if (
      root instanceof Element &&
      root.matches("[hyper-action][hyper-trigger]")
    ) {
      candidates.push(root);
    }
    if (root && typeof root.querySelectorAll === "function") {
      candidates.push(...root.querySelectorAll("[hyper-action][hyper-trigger]"));
    }
    for (const el of candidates) {
      const triggers = (el.getAttribute("hyper-trigger") || "").split(/\s+/);
      if (!triggers.includes("visible") || lazyActionElements.has(el)) {
        continue;
      }
      lazyActionElements.add(el);
      lazyActionObserver.observe(el);
    }
  }

  function initLoadingIndicators() {
    hideLoadingElements();
    applyViewNames(document);
  }

  return {
    runAction,
    action: actionRequest,
    visit,
    dispatchStreamEvent,
    swapHTML,
    applySwap,
    initLoadingIndicators,
    initNetwork,
    initNavigation,
    initForms,
    initLazyActions,
    navigate,
    configure,
    applyViewNames,
    network,
  };
})();

window.Hyper = Hyper;
window.action = Hyper.action;

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => {
    Hyper.initLoadingIndicators();
    Hyper.initNetwork();
    Hyper.initNavigation();
    Hyper.initForms();
    Hyper.initLazyActions();
  });
} else {
  Hyper.initLoadingIndicators();
  Hyper.initNetwork();
  Hyper.initNavigation();
  Hyper.initForms();
  Hyper.initLazyActions();
}
