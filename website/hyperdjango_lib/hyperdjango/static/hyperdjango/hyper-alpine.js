(function () {
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
      const initial = typeof window.Alpine.reactive === "function" ? window.Alpine.reactive({}) : {};
      window.Alpine.store("hyper", initial);
      store = window.Alpine.store("hyper");
    }
    return store;
  }

  function resolveBindTarget(sourceEl) {
    if (!window.Alpine || typeof window.Alpine.$data !== "function") {
      return null;
    }
    const element = sourceEl instanceof Element ? sourceEl : document.activeElement;
    if (!element || typeof element.closest !== "function") {
      return null;
    }
    const root = element.closest("[x-data]");
    if (!root) {
      return null;
    }
    try {
      return window.Alpine.$data(root);
    } catch {
      return null;
    }
  }

  function registerSignalBridge() {
    if (window.__hyperAlpineSignalsInstalled) {
      return;
    }
    window.__hyperAlpineSignalsInstalled = true;
    window.addEventListener("hyper:streamEvent", (event) => {
      if (event.detail.event !== "patch_signals") {
        return;
      }

      const patches = splitSignalPatches(event.detail.data);
      if (Object.keys(patches.global).length > 0) {
        const store = ensureHyperStore();
        if (store) {
          mergeInto(store, patches.global);
        }
      }
      if (Object.keys(patches.local).length > 0) {
        const target = resolveBindTarget(event.detail.sourceEl || null);
        if (target) {
          mergeInto(target, patches.local);
        }
      }

      window.dispatchEvent(
        new CustomEvent("hyper:signals", {
          detail: event.detail.data,
        })
      );
    });
  }

  function registerAlpineMagicHelpers() {
    if (!window.Alpine || typeof window.Alpine.magic !== "function" || !window.Hyper) {
      return;
    }
    window.Alpine.magic("action", (el) => {
      return (name, data = {}, options = {}) => {
        return window.Hyper.action(name, data, { ...options, sourceEl: el });
      };
    });
  }

  function install() {
    registerSignalBridge();
    registerAlpineMagicHelpers();
  }

  if (window.Alpine) {
    install();
  }

  document.addEventListener("alpine:init", () => {
    install();
  });
})();
