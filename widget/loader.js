/**
 * Quiribot Widget Loader
 * =====================
 * Merchants paste this single script tag into their site.
 *
 * Usage:
 *   <script src="https://widget.quiribot.com/load.js"
 *           data-site-key="YOUR_SITE_KEY"
 *           data-api="https://api.quiribot.com"></script>
 *
 * For local development:
 *   <script src="http://localhost:7000/widget/loader.js"
 *           data-site-key="YOUR_SITE_KEY"
 *           data-api="http://localhost:8080"
 *           data-shell="http://localhost:7000/widget/shell"></script>
 */
(function () {
  "use strict";

  var script    = document.currentScript;
  var SITE_KEY  = script.getAttribute("data-site-key") || "";
  var API_URL   = (script.getAttribute("data-api")   || "http://localhost:8080").replace(/\/$/, "");
  var SHELL_URL = (script.getAttribute("data-shell") || "http://localhost:7000/widget/shell");

  if (!SITE_KEY) {
    console.warn("[Quiribot] No data-site-key attribute provided — widget disabled.");
    return;
  }

  // -------------------------------------------------------------------------
  // Fetch widget config (colors, bot name, greeting, position)
  // -------------------------------------------------------------------------
  var config = {
    bot_name:      "Quiribot",
    greeting:      "Hi! How can I help you find the perfect product?",
    primary_color: "#6366f1",
    button_color:  "#6366f1",
    position:      "bottom-right",
    tone:          "friendly",
    avatar_visible: true,
    tenant_id:     SITE_KEY,
  };

  function fetchConfig(cb) {
    var xhr = new XMLHttpRequest();
    xhr.open("GET", API_URL + "/widget/config?siteKey=" + encodeURIComponent(SITE_KEY), true);
    xhr.onload = function () {
      if (xhr.status === 200) {
        try {
          var data = JSON.parse(xhr.responseText);
          Object.assign(config, data);
        } catch (e) {}
      }
      cb();
    };
    xhr.onerror = function () { cb(); };
    xhr.send();
  }

  // -------------------------------------------------------------------------
  // DOM injection
  // -------------------------------------------------------------------------
  function injectWidget() {
    var pos = config.position || "bottom-right";
    var side   = pos.indexOf("right") !== -1 ? "right" : "left";
    var bottom = "20px";
    var sideVal= "20px";

    // Floating button
    var btn = document.createElement("div");
    btn.id  = "qb-launcher";
    btn.setAttribute("aria-label", "Open Quiribot chat");
    btn.setAttribute("role", "button");
    btn.setAttribute("tabindex", "0");
    btn.style.cssText = [
      "position:fixed", "bottom:" + bottom, side + ":" + sideVal,
      "width:56px", "height:56px", "border-radius:50%",
      "background:" + config.button_color,
      "box-shadow:0 4px 16px rgba(0,0,0,.25)",
      "cursor:pointer", "z-index:2147483646",
      "display:flex", "align-items:center", "justify-content:center",
      "transition:transform .2s",
    ].join(";");
    btn.innerHTML = '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>';

    // Notification dot (for proactive messages)
    var dot = document.createElement("span");
    dot.id  = "qb-dot";
    dot.style.cssText = "position:absolute;top:2px;" + side + ":2px;width:12px;height:12px;border-radius:50%;background:#ef4444;border:2px solid white;display:none;";
    btn.appendChild(dot);

    // iframe panel
    var panel = document.createElement("div");
    panel.id  = "qb-panel";
    panel.style.cssText = [
      "position:fixed", "bottom:88px", side + ":" + sideVal,
      "width:380px", "height:600px",
      "max-height:calc(100vh - 120px)",
      "border-radius:16px",
      "box-shadow:0 8px 40px rgba(0,0,0,.18)",
      "overflow:hidden", "z-index:2147483645",
      "display:none", "transition:opacity .2s,transform .2s",
      "transform:translateY(8px)", "opacity:0",
    ].join(";");

    // Build iframe src with all needed params
    var shellSrc = SHELL_URL
      + "?siteKey="  + encodeURIComponent(SITE_KEY)
      + "&api="      + encodeURIComponent(API_URL)
      + "&color="    + encodeURIComponent(config.primary_color)
      + "&botName="  + encodeURIComponent(config.bot_name)
      + "&greeting=" + encodeURIComponent(config.greeting)
      + "&tone="     + encodeURIComponent(config.tone);

    var iframe = document.createElement("iframe");
    iframe.src         = shellSrc;
    iframe.title       = config.bot_name + " chat";
    iframe.style.cssText = "width:100%;height:100%;border:none;";
    iframe.setAttribute("allow", "clipboard-write");
    panel.appendChild(iframe);

    document.body.appendChild(btn);
    document.body.appendChild(panel);

    // -----------------------------------------------------------------------
    // Toggle open / close
    // -----------------------------------------------------------------------
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
        iframe.contentWindow && iframe.contentWindow.postMessage({ type: "QB_FOCUS" }, "*");
      } else {
        panel.style.transform = "translateY(8px)";
        panel.style.opacity   = "0";
        btn.style.transform   = "";
        setTimeout(function () { panel.style.display = "none"; }, 200);
      }
    }
    btn.addEventListener("click", togglePanel);
    btn.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") togglePanel();
    });

    // -----------------------------------------------------------------------
    // postMessage bridge: iframe → parent page
    // -----------------------------------------------------------------------
    window.addEventListener("message", function (e) {
      if (e.source !== iframe.contentWindow) return;
      var msg = e.data || {};
      if (msg.type === "QB_CLOSE")  togglePanel();
      if (msg.type === "QB_RESIZE") {
        if (msg.height) panel.style.height = Math.min(msg.height, window.innerHeight - 120) + "px";
      }
    });

    // -----------------------------------------------------------------------
    // Proactive engagement: check if current page is a known product
    // -----------------------------------------------------------------------
    function checkProactive() {
      var xhr = new XMLHttpRequest();
      var url = API_URL + "/widget/proactive?siteKey=" + encodeURIComponent(SITE_KEY)
              + "&url=" + encodeURIComponent(window.location.href);
      xhr.open("GET", url, true);
      xhr.onload = function () {
        if (xhr.status !== 200) return;
        try {
          var data = JSON.parse(xhr.responseText);
          if (data.triggered && data.message) {
            showProactiveBubble(data.message);
          }
        } catch (e) {}
      };
      xhr.send();
    }

    function showProactiveBubble(message) {
      if (open) return;               // already open
      dot.style.display = "block";   // red notification dot
      var bubble = document.createElement("div");
      bubble.id  = "qb-bubble";
      bubble.style.cssText = [
        "position:fixed", "bottom:88px", side + ":" + sideVal,
        "max-width:260px", "background:white",
        "border-radius:12px 12px 0 12px",
        "box-shadow:0 4px 20px rgba(0,0,0,.15)",
        "padding:12px 16px", "font-family:system-ui,sans-serif",
        "font-size:14px", "line-height:1.4", "color:#111",
        "z-index:2147483644", "cursor:pointer",
        "animation:qb-fadein .3s ease",
      ].join(";");
      bubble.textContent = message;

      var closeBtn = document.createElement("span");
      closeBtn.textContent = " ×";
      closeBtn.style.cssText = "cursor:pointer;color:#888;font-size:16px;margin-left:4px;";
      closeBtn.onclick = function (e) {
        e.stopPropagation();
        document.body.removeChild(bubble);
      };
      bubble.appendChild(closeBtn);
      bubble.addEventListener("click", function () {
        document.body.removeChild(bubble);
        togglePanel();
        // Tell the widget shell to pre-fill with the proactive query
        setTimeout(function () {
          iframe.contentWindow && iframe.contentWindow.postMessage(
            { type: "QB_PROACTIVE", message: message }, "*"
          );
        }, 400);
      });

      document.body.appendChild(bubble);
      setTimeout(function () {
        if (document.getElementById("qb-bubble")) {
          document.body.removeChild(bubble);
        }
      }, 12000);
    }

    // Inject proactive CSS animation
    var styleEl = document.createElement("style");
    styleEl.textContent = "@keyframes qb-fadein{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}";
    document.head.appendChild(styleEl);

    // Trigger proactive check after 30s idle on page
    var proactiveTimer = setTimeout(checkProactive, 30000);
    document.addEventListener("visibilitychange", function () {
      if (document.hidden) clearTimeout(proactiveTimer);
    });
  }

  // -------------------------------------------------------------------------
  // Boot
  // -------------------------------------------------------------------------
  function boot() {
    fetchConfig(function () {
      if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", injectWidget);
      } else {
        injectWidget();
      }
    });
  }

  boot();
})();
