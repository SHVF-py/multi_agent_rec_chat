/**
 * Quiribot Widget Loader  v2
 * ==========================
 * Merchants paste this single script tag into their site.
 *
 * STATES
 *   ready   â€” products indexed, normal chat button
 *   setup   â€” site key exists but no sync yet; pulsing button + badge
 *   syncing â€” sync job is running; spinner ring on button
 *
 * Usage:
 *   <script src="http://localhost:7000/widget/loader.js"
 *           data-site-key="YOUR_SITE_KEY"
 *           data-api="http://localhost:8080"
 *           data-shell="http://localhost:7000/widget/shell"></script>
 */
(function () {
  "use strict";

  // currentScript is null when the tag uses `defer` â€” fall back to a src match
  var script = document.currentScript ||
    document.querySelector('script[data-site-key]') ||
    (function () {
      var tags = document.querySelectorAll('script[src*="loader.js"]');
      return tags[tags.length - 1] || null;
    }());

  if (!script) {
    console.warn("[Quiribot] Could not locate loader script tag.");
    return;
  }

  var SITE_KEY  = script.getAttribute("data-site-key") || "";
  var API_URL   = (script.getAttribute("data-api")   || "http://localhost:8080").replace(/\/$/, "");
  var SHELL_URL = (script.getAttribute("data-shell") || "http://localhost:7000/widget/shell");

  if (!SITE_KEY) {
    console.warn("[Quiribot] No data-site-key provided â€” widget disabled.");
    return;
  }

  var config = {
    bot_name:      "Quiribot",
    greeting:      "Hi! How can I help you find the perfect product?",
    primary_color: "#6366f1",
    button_color:  "#6366f1",
    position:      "bottom-right",
    tone:          "friendly",
    avatar_visible: true,
  };

  // sync_status: "idle" | "syncing" | "done" | "error"
  var syncInfo = { is_ready: true, sync_status: "done", product_count: 0 };

  // -------------------------------------------------------------------------
  // Data fetches
  // -------------------------------------------------------------------------
  function fetchConfig(cb) {
    var xhr = new XMLHttpRequest();
    xhr.open("GET", API_URL + "/widget/config?siteKey=" + encodeURIComponent(SITE_KEY), true);
    xhr.onload = function () {
      if (xhr.status === 200) {
        try { Object.assign(config, JSON.parse(xhr.responseText)); } catch (e) {}
      }
      cb();
    };
    xhr.onerror = function () { cb(); };
    xhr.send();
  }

  function fetchSyncStatus(cb) {
    var xhr = new XMLHttpRequest();
    xhr.open("GET", API_URL + "/widget/sync-status?siteKey=" + encodeURIComponent(SITE_KEY), true);
    xhr.onload = function () {
      try { Object.assign(syncInfo, JSON.parse(xhr.responseText)); } catch (e) {}
      cb();
    };
    xhr.onerror = function () { cb(); };
    xhr.send();
  }

  // -------------------------------------------------------------------------
  // DOM injection
  // -------------------------------------------------------------------------
  function injectWidget() {
    var ready = syncInfo.is_ready;
    var pos   = config.position || "bottom-right";
    var side  = pos.indexOf("right") !== -1 ? "right" : "left";

    // Global CSS
    var styleEl = document.createElement("style");
    styleEl.textContent = [
      "@keyframes qb-fadein{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}",
      "@keyframes qb-pulse{0%,100%{transform:scale(1)}50%{transform:scale(1.07)}}",
      "@keyframes qb-glow{0%,100%{box-shadow:0 4px 16px rgba(99,102,241,.35)}",
        "50%{box-shadow:0 4px 24px rgba(99,102,241,.7)}}",
      "@keyframes qb-spin{to{transform:rotate(360deg)}}",
      "#qb-launcher{transition:background .3s,transform .2s;}",
      // pulsing glow when in setup/syncing state
      "#qb-launcher.qb-not-ready{animation:qb-pulse 2s ease-in-out infinite,qb-glow 2s ease-in-out infinite;}",
      // badge above button
      "#qb-badge{position:fixed;bottom:88px;" + side + ":14px;",
        "background:white;border:1px solid #e5e7eb;border-radius:20px;",
        "padding:6px 14px 6px 10px;font-size:12px;font-family:system-ui,sans-serif;",
        "color:#374151;box-shadow:0 2px 12px rgba(0,0,0,.12);",
        "white-space:nowrap;z-index:2147483644;",
        "display:flex;align-items:center;gap:7px;",
        "animation:qb-fadein .4s ease;}",
      "#qb-badge .qb-dot{width:8px;height:8px;border-radius:50%;flex-shrink:0;",
        "animation:qb-pulse 1.4s infinite;}",
    ].join("");
    document.head.appendChild(styleEl);

    // ---- Button ----
    var btn = document.createElement("div");
    btn.id  = "qb-launcher";
    btn.setAttribute("role", "button");
    btn.setAttribute("tabindex", "0");
    btn.setAttribute("aria-label", "Open Quiribot chat");
    btn.style.cssText = [
      "position:fixed", "bottom:20px", side + ":20px",
      "width:56px", "height:56px", "border-radius:50%",
      "background:" + config.button_color,
      "cursor:pointer", "z-index:2147483646",
      "display:flex", "align-items:center", "justify-content:center",
    ].join(";");

    var _chatSVG  = '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>';
    var _setupSVG = '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>';
    var _spinHTML = '<div style="width:24px;height:24px;border:2.5px solid rgba(255,255,255,.35);border-top-color:white;border-radius:50%;animation:qb-spin .75s linear infinite;"></div>';

    function renderButtonIcon() {
      if (ready) return _chatSVG;
      if (syncInfo.sync_status === "syncing") return _spinHTML;
      return _setupSVG;
    }

    btn.innerHTML = renderButtonIcon();
    if (!ready) btn.classList.add("qb-not-ready");

    // notification dot (proactive)
    var dot = document.createElement("span");
    dot.id  = "qb-dot";
    dot.style.cssText = "position:absolute;top:2px;" + side + ":2px;width:12px;height:12px;border-radius:50%;background:#ef4444;border:2px solid white;display:none;";
    btn.appendChild(dot);

    // ---- Setup badge (visible when not ready) ----
    var badge = null;
    if (!ready) {
      badge = document.createElement("div");
      badge.id = "qb-badge";
      var badgeDot  = document.createElement("span");
      badgeDot.className = "qb-dot";
      badgeDot.style.background = syncInfo.sync_status === "syncing" ? "#3b82f6" : "#f59e0b";
      var badgeText = document.createElement("span");
      badgeText.id  = "qb-badge-text";
      badgeText.textContent = syncInfo.sync_status === "syncing"
        ? "Syncing your store\u2026"
        : "Setting up your store\u2026";
      badge.appendChild(badgeDot);
      badge.appendChild(badgeText);
      document.body.appendChild(badge);
    }

    // ---- Panel + iframe ----
    var panel = document.createElement("div");
    panel.id  = "qb-panel";
    panel.style.cssText = [
      "position:fixed", "bottom:88px", side + ":20px",
      "width:460px", "height:600px", "max-height:calc(100vh - 120px)",
      "border-radius:16px", "box-shadow:0 8px 40px rgba(0,0,0,.18)",
      "overflow:hidden", "z-index:2147483645", "display:none",
      "transition:opacity .2s,transform .2s",
      "transform:translateY(8px)", "opacity:0",
    ].join(";");

    var shellSrc = SHELL_URL
      + "?siteKey="  + encodeURIComponent(SITE_KEY)
      + "&api="      + encodeURIComponent(API_URL)
      + "&tenantId=" + encodeURIComponent(config.tenant_id || "")
      + "&color="    + encodeURIComponent(config.primary_color)
      + "&botName="  + encodeURIComponent(config.bot_name)
      + "&greeting=" + encodeURIComponent(config.greeting)
      + "&tone="     + encodeURIComponent(config.tone)
      + "&ready="    + (ready ? "1" : "0");

    var iframe = document.createElement("iframe");
    iframe.src   = shellSrc;
    iframe.title = config.bot_name + " chat";
    iframe.style.cssText = "width:100%;height:100%;border:none;";
    iframe.setAttribute("allow", "clipboard-write");
    panel.appendChild(iframe);

    document.body.appendChild(btn);
    document.body.appendChild(panel);

    // ---- Open/close ----
    var open = false;
    function togglePanel() {
      open = !open;
      if (open) {
        panel.style.display = "block";
        requestAnimationFrame(function () {
          panel.style.transform = "translateY(0)";
          panel.style.opacity   = "1";
        });
        btn.style.transform = "rotate(90deg)";
        dot.style.display   = "none";
        if (badge) badge.style.display = "none";
        iframe.contentWindow && iframe.contentWindow.postMessage({ type: "QB_FOCUS" }, "*");
      } else {
        panel.style.transform = "translateY(8px)";
        panel.style.opacity   = "0";
        btn.style.transform   = "";
        if (badge && !ready) badge.style.display = "flex";
        setTimeout(function () { panel.style.display = "none"; }, 200);
      }
    }
    btn.addEventListener("click", togglePanel);
    btn.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") togglePanel();
    });

    // ---- postMessage bridge ----
    window.addEventListener("message", function (e) {
      if (e.source !== iframe.contentWindow) return;
      var msg = e.data || {};
      if (msg.type === "QB_CLOSE")  togglePanel();
      if (msg.type === "QB_RESIZE" && msg.height) {
        panel.style.height = Math.min(msg.height, window.innerHeight - 120) + "px";
      }
      // Chat.js tells us sync completed â€” update button to ready state
      if (msg.type === "QB_READY")  transitionToReady();
    });

    // Called when chat.js reports sync is done
    function transitionToReady() {
      ready = true;
      syncInfo.is_ready = true;
      btn.classList.remove("qb-not-ready");
      btn.style.background = config.button_color;
      // swap icon (preserve dot child)
      btn.innerHTML = _chatSVG;
      btn.appendChild(dot);
      if (badge) {
        badge.style.transition = "opacity .5s";
        badge.style.opacity    = "0";
        setTimeout(function () { if (badge.parentNode) badge.parentNode.removeChild(badge); }, 500);
      }
      // start proactive timer now that we're ready
      scheduleProactive();
    }

    // ---- Proactive engagement ----
    function scheduleProactive() {
      var proactiveTimer = setTimeout(checkProactive, 30000);
      document.addEventListener("visibilitychange", function () {
        if (document.hidden) clearTimeout(proactiveTimer);
      });
    }

    function checkProactive() {
      var xhr = new XMLHttpRequest();
      xhr.open("GET", API_URL + "/widget/proactive?siteKey=" + encodeURIComponent(SITE_KEY)
             + "&url=" + encodeURIComponent(window.location.href), true);
      xhr.onload = function () {
        try {
          var data = JSON.parse(xhr.responseText);
          if (data.triggered && data.message && !open) {
            dot.style.display = "block";
            showProactiveBubble(data.message);
          }
        } catch (e) {}
      };
      xhr.send();
    }

    function showProactiveBubble(message) {
      var bubble = document.createElement("div");
      bubble.id  = "qb-bubble";
      bubble.style.cssText = [
        "position:fixed", "bottom:88px", side + ":20px",
        "max-width:260px", "background:white",
        "border-radius:12px 12px 0 12px",
        "box-shadow:0 4px 20px rgba(0,0,0,.15)",
        "padding:12px 16px", "font-family:system-ui,sans-serif",
        "font-size:14px", "line-height:1.4", "color:#111",
        "z-index:2147483644", "cursor:pointer",
        "animation:qb-fadein .3s ease",
      ].join(";");
      bubble.textContent = message;
      var closeX = document.createElement("span");
      closeX.textContent = " \xd7";
      closeX.style.cssText = "cursor:pointer;color:#888;font-size:16px;margin-left:4px;";
      closeX.onclick = function (e) { e.stopPropagation(); bubble.parentNode && bubble.parentNode.removeChild(bubble); };
      bubble.appendChild(closeX);
      bubble.addEventListener("click", function () {
        bubble.parentNode && bubble.parentNode.removeChild(bubble);
        togglePanel();
        setTimeout(function () {
          iframe.contentWindow && iframe.contentWindow.postMessage(
            { type: "QB_PROACTIVE", message: message }, "*"
          );
        }, 400);
      });
      document.body.appendChild(bubble);
      setTimeout(function () {
        var b = document.getElementById("qb-bubble");
        if (b) b.parentNode && b.parentNode.removeChild(b);
      }, 12000);
    }

    if (ready) scheduleProactive();
  }

  // -------------------------------------------------------------------------
  // Boot
  // -------------------------------------------------------------------------
  function boot() {
    fetchConfig(function () {
      fetchSyncStatus(function () {
        if (document.readyState === "loading") {
          document.addEventListener("DOMContentLoaded", injectWidget);
        } else {
          injectWidget();
        }
      });
    });
  }

  boot();
})();
