/*
 * Erick Wei research-site analytics bridge.
 *
 * Privacy model:
 * - no cookies
 * - no IP collection in the browser payload
 * - anonymous session id stored in localStorage
 * - sends only page path, referrer host, viewport, language, and named events
 *
 * Configure before loading this file:
 * window.SITE_ANALYTICS_CONFIG = {
 *   site: "usdcny-tracker",
 *   endpoint: "https://YOUR-WORKER.workers.dev/collect",
 *   enabled: true
 * };
 */
(function () {
  "use strict";

  const cfg = window.SITE_ANALYTICS_CONFIG || {};
  const endpoint = String(cfg.endpoint || "").trim();
  const enabled = cfg.enabled !== false && /^https?:\/\//.test(endpoint) && !/YOUR-WORKER|example/i.test(endpoint);
  const site = String(cfg.site || location.hostname || "research-site");
  const sessionKey = "ew_analytics_session_v1";
  const seenSections = new Set();

  function getSessionId() {
    try {
      let id = localStorage.getItem(sessionKey);
      if (!id) {
        id = "s_" + Math.random().toString(36).slice(2) + Date.now().toString(36);
        localStorage.setItem(sessionKey, id);
      }
      return id;
    } catch (_) {
      return "s_no_storage";
    }
  }

  function referrerHost() {
    try {
      return document.referrer ? new URL(document.referrer).hostname : "";
    } catch (_) {
      return "";
    }
  }

  function clean(value, maxLen) {
    return String(value == null ? "" : value)
      .replace(/[\u0000-\u001f\u007f]/g, "")
      .slice(0, maxLen || 160);
  }

  function payload(event, props) {
    return {
      site,
      event: clean(event || "event", 80),
      path: clean(location.pathname, 180),
      title: clean(document.title, 160),
      referrer_host: clean(referrerHost(), 120),
      lang: clean(document.documentElement.lang || navigator.language || "", 24),
      viewport: `${window.innerWidth || 0}x${window.innerHeight || 0}`,
      session_id: getSessionId(),
      ts: new Date().toISOString(),
      props: props || {}
    };
  }

  function send(event, props) {
    const body = JSON.stringify(payload(event, props));

    if (enabled) {
      try {
        if (navigator.sendBeacon) {
          const ok = navigator.sendBeacon(endpoint, new Blob([body], { type: "application/json" }));
          if (ok) return;
        }
      } catch (_) {}
      try {
        fetch(endpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body,
          keepalive: true,
          mode: "cors"
        }).catch(function () {});
      } catch (_) {}
    } else if (cfg.debug) {
      console.info("[site-analytics disabled]", event, props || {});
    }

    if (window.umami && typeof window.umami.track === "function") {
      try { window.umami.track(event, props || {}); } catch (_) {}
    }
    if (typeof window.gtag === "function") {
      try { window.gtag("event", event, props || {}); } catch (_) {}
    }
  }

  function eventNameFromElement(el) {
    if (el.dataset && el.dataset.track) return el.dataset.track;
    if (el.id) return "click_" + el.id.replace(/[^a-z0-9]+/gi, "_").toLowerCase();
    const href = el.getAttribute && el.getAttribute("href");
    if (href) {
      if (el.hasAttribute("download")) return "download_" + clean(el.getAttribute("download") || href, 80);
      if (/data\.json/i.test(href)) return "download_data_json";
      if (/xlsx/i.test(href)) return "download_excel";
      if (/ipynb/i.test(href)) return "download_notebook";
      return "click_link";
    }
    return "click";
  }

  function describeElement(el) {
    const href = el.getAttribute && el.getAttribute("href");
    return {
      text: clean((el.innerText || el.textContent || "").replace(/\s+/g, " "), 100),
      href: clean(href || "", 180),
      id: clean(el.id || "", 80),
      class: clean(el.className || "", 120)
    };
  }

  function bindClicks() {
    document.addEventListener("click", function (e) {
      const target = e.target && e.target.closest
        ? e.target.closest("a,button,[data-track]")
        : null;
      if (!target) return;
      send(eventNameFromElement(target), describeElement(target));
    }, { passive: true });
  }

  function bindSections() {
    if (!("IntersectionObserver" in window)) return;
    const candidates = Array.from(document.querySelectorAll("section[id], .chapter[id], [data-track-section]"));
    const observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting || entry.intersectionRatio < 0.45) return;
        const el = entry.target;
        const section = el.dataset.trackSection || el.id || "section";
        if (seenSections.has(section)) return;
        seenSections.add(section);
        send("view_section", { section: clean(section, 80) });
      });
    }, { threshold: [0.45, 0.7] });
    candidates.forEach(function (el) { observer.observe(el); });
  }

  window.siteTrack = send;

  document.addEventListener("DOMContentLoaded", function () {
    send("page_view", { search: clean(location.search, 120) });
    bindClicks();
    bindSections();
  });
})();
