/**
 * Quiribot Widget Shell — chat.js  v2
 * Runs inside the sandboxed iframe (chat.html).
 *
 * URL params (set by loader.js):
 *   siteKey, api, color, botName, greeting, tone, ready (1|0)
 */
(function () {
  "use strict";

  // -------------------------------------------------------------------------
  // Config from URL params
  // -------------------------------------------------------------------------
  var params   = new URLSearchParams(window.location.search);
  var SITE_KEY = params.get("siteKey")  || "default";
  var API_URL  = (params.get("api")     || "http://localhost:8080").replace(/\/$/, "");
  var BOT_NAME = params.get("botName")  || "Quiribot";
  var GREETING = params.get("greeting") || "Hi! How can I help you find the perfect product today?";
  var COLOR    = params.get("color")    || "#6366f1";
  var IS_READY  = params.get("ready")    !== "0";    // default: ready
  var TENANT_ID = params.get("tenantId") || SITE_KEY; // real business UUID for queries

  // Apply colors
  document.documentElement.style.setProperty("--primary",      COLOR);
  document.documentElement.style.setProperty("--primary-dark", shadeColor(COLOR, -15));
  document.getElementById("header-name").textContent = BOT_NAME;

  // -------------------------------------------------------------------------
  // State
  // -------------------------------------------------------------------------
  var sessionId   = generateId();
  var chatHistory = [];
  var setupDone   = IS_READY;
  var _pollTimer  = null;

  // -------------------------------------------------------------------------
  // DOM refs
  // -------------------------------------------------------------------------
  var messagesEl  = document.getElementById("messages");
  var inputEl     = document.getElementById("user-input");
  var sendBtn     = document.getElementById("send-btn");
  var closeBtn    = document.getElementById("close-btn");
  var newChatBtn  = document.getElementById("new-chat-btn");
  var setupScreen = document.getElementById("qb-setup-screen");

  // -------------------------------------------------------------------------
  // Boot
  // -------------------------------------------------------------------------
  if (IS_READY) {
    appendBotMessage(GREETING);
  } else {
    showSetupScreen();
  }

  // -------------------------------------------------------------------------
  // Event listeners
  // -------------------------------------------------------------------------
  sendBtn.addEventListener("click", handleSend);
  inputEl.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  });
  inputEl.addEventListener("input", autoResize);

  closeBtn.addEventListener("click", function () {
    parent.postMessage({ type: "QB_CLOSE" }, "*");
  });

  newChatBtn.addEventListener("click", function () {
    if (!setupDone) return;
    sessionId   = generateId();
    chatHistory = [];
    messagesEl.innerHTML = "";
    appendBotMessage(GREETING);
    inputEl.focus();
  });

  window.addEventListener("message", function (e) {
    var msg = e.data || {};
    if (msg.type === "QB_FOCUS")    { inputEl.focus(); }
    if (msg.type === "QB_PROACTIVE" && msg.message) { appendBotMessage(msg.message); }
  });

  // -------------------------------------------------------------------------
  // First-time setup screen
  // -------------------------------------------------------------------------
  var CHECK_SVG = '<svg class="qb-done-icon" width="18" height="18" viewBox="0 0 18 18" fill="none">'
    + '<circle cx="9" cy="9" r="9" fill="#22c55e"/>'
    + '<path d="M5 9l3 3 5-6" stroke="white" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>'
    + '</svg>';
  var SPIN_HTML = '<div class="qb-spin-ring"></div>';

  function showSetupScreen() {
    disableInput("Setting up\u2026");
    setupScreen.style.display = "flex";

    // Step 0 done instantly (visual progress feels good)
    setTimeout(function () { setStep(0, "done"); setBar(18); }, 800);
    // Step 1 goes active
    setTimeout(function () { setStep(1, "active"); }, 1600);
    // Start polling
    _pollTimer = setTimeout(pollReady, 5000);
  }

  function setStep(index, state) {
    var stepEl = document.getElementById("step-" + index);
    var iconEl = document.getElementById("step-icon-" + index);
    if (!stepEl || !iconEl) return;
    stepEl.className = "qb-step " + state;
    if (state === "done")        { iconEl.innerHTML  = CHECK_SVG; }
    else if (state === "active") { iconEl.innerHTML  = SPIN_HTML; }
    else                         { iconEl.textContent = "\u25cb"; }
  }

  function setBar(pct) {
    var bar = document.getElementById("qb-bar");
    if (bar) bar.style.width = Math.min(pct, 100) + "%";
  }

  function pollReady() {
    var xhr = new XMLHttpRequest();
    xhr.open("GET", API_URL + "/widget/sync-status?siteKey=" + encodeURIComponent(SITE_KEY), true);
    xhr.timeout = 8000;

    xhr.onload = function () {
      try {
        var data = JSON.parse(xhr.responseText);
        if (data.is_ready) {
          completeSetup(data.product_count || 0);
        } else if (data.sync_status === "error") {
          showSetupError(data.message || "Sync failed. Retry from your dashboard.");
        } else {
          // Still syncing — nudge progress bar, keep polling
          var bar = document.getElementById("qb-bar");
          var cur = bar ? parseFloat(bar.style.width) || 20 : 20;
          setBar(Math.min(cur + 8 + Math.random() * 10, 85));
          _pollTimer = setTimeout(pollReady, 5000);
        }
      } catch (e) {
        _pollTimer = setTimeout(pollReady, 5000);
      }
    };
    xhr.onerror = xhr.ontimeout = function () {
      _pollTimer = setTimeout(pollReady, 8000);
    };
    xhr.send();
  }

  function completeSetup(productCount) {
    clearTimeout(_pollTimer);
    setupDone = true;

    setStep(1, "done");  setBar(80);
    setTimeout(function () { setStep(2, "active"); setBar(95); }, 400);
    setTimeout(function () { setStep(2, "done");   setBar(100); }, 1100);

    setTimeout(function () {
      var emoji   = document.getElementById("setup-emoji");
      var title   = document.getElementById("setup-title");
      var sub     = document.getElementById("setup-sub");
      var hint    = document.getElementById("setup-hint");
      var stepsEl = document.getElementById("qb-steps");
      var barEl   = document.querySelector(".qb-bar-track");

      if (emoji)   emoji.textContent = "\u2705";
      if (title)   title.textContent = "Your store is ready!";
      if (sub)     sub.textContent   = (productCount > 0 ? productCount + " products" : "Products") + " indexed and searchable";
      if (hint)    hint.textContent  = "Starting chat\u2026";
      if (stepsEl) stepsEl.style.display = "none";
      if (barEl)   barEl.style.display   = "none";

      // Tell parent loader — it updates the button to ready state
      parent.postMessage({ type: "QB_READY" }, "*");
    }, 1700);

    // Fade out setup → show chat
    setTimeout(function () {
      setupScreen.style.opacity = "0";
      setTimeout(function () {
        setupScreen.style.display  = "none";
        setupScreen.style.opacity  = "1";
        appendBotMessage(GREETING);
        enableInput();
        inputEl.focus();
      }, 420);
    }, 2800);
  }

  function showSetupError(msg) {
    clearTimeout(_pollTimer);
    var emoji  = document.getElementById("setup-emoji");
    var title  = document.getElementById("setup-title");
    var sub    = document.getElementById("setup-sub");
    var hint   = document.getElementById("setup-hint");
    var stepsEl = document.getElementById("qb-steps");
    var barEl  = document.querySelector(".qb-bar-track");

    if (emoji)   emoji.textContent = "\u26a0\ufe0f";
    if (title)   { title.textContent = "Setup failed"; title.style.color = "#b91c1c"; }
    if (sub)     sub.textContent  = msg;
    if (hint)    hint.innerHTML   = 'Retry sync from your <a href="/business/dashboard" target="_blank" style="color:var(--primary);">dashboard</a>.';
    if (stepsEl) stepsEl.style.display = "none";
    if (barEl)   barEl.style.display   = "none";
    disableInput("Unavailable");
  }

  function enableInput() {
    inputEl.disabled    = false;
    sendBtn.disabled    = false;
    inputEl.placeholder = "Ask me anything\u2026";
  }

  function disableInput(placeholder) {
    inputEl.disabled    = true;
    sendBtn.disabled    = true;
    inputEl.placeholder = placeholder || "Setting up\u2026";
  }

  // -------------------------------------------------------------------------
  // Core send logic
  // -------------------------------------------------------------------------
  function handleSend() {
    var text = inputEl.value.trim();
    if (!text || sendBtn.disabled) return;

    appendUserMessage(text);
    chatHistory.push({ role: "user", content: text });
    inputEl.value = "";
    autoResize();

    sendBtn.disabled = true;
    var typingId = appendTyping();

    callAPI(text, function (response) {
      removeTyping(typingId);
      sendBtn.disabled = false;

      if (!response || response.error) {
        var errMsg = (response && response.error) || "Something went wrong. Please try again.";
        appendBotMessage(errMsg);
        return;
      }

      var reply = response.conversational_reply || "";
      if (reply) {
        appendBotMessage(reply);
        chatHistory.push({ role: "assistant", content: reply });
      }

      var products = response.ranked_products || [];
      if (products.length) {
        appendProducts(products.slice(0, 3));
      }

      if (response.comparison && response.comparison.comparison_table) {
        appendComparisonTable(response.comparison);
      }

      if (!reply && !products.length) {
        appendBotMessage("I couldn't find anything matching that. Could you rephrase or try a different search?");
      }

      inputEl.focus();
    });
  }

  // -------------------------------------------------------------------------
  // API call
  // -------------------------------------------------------------------------
  function callAPI(queryText, cb) {
    var payload = JSON.stringify({
      query_text:   queryText,
      session_id:   sessionId,
      tenant_id:    TENANT_ID,
      chat_history: chatHistory.slice(-10),
    });

    var xhr = new XMLHttpRequest();
    xhr.open("POST", API_URL + "/query", true);
    xhr.setRequestHeader("Content-Type", "application/json");
    xhr.timeout = 360000;   // 6 min — phi3 on CPU can be slow

    xhr.onload = function () {
      try {
        cb(JSON.parse(xhr.responseText));
      } catch (e) {
        cb({ error: "Invalid response from server." });
      }
    };
    xhr.onerror   = function () { cb({ error: "Network error. Is the API running?" }); };
    xhr.ontimeout = function () { cb({ error: "Request timed out. Please try again." }); };
    xhr.send(payload);
  }

  // -------------------------------------------------------------------------
  // Render helpers
  // -------------------------------------------------------------------------
  function appendUserMessage(text) {
    var div = document.createElement("div");
    div.className = "msg user";
    var bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.textContent = text;
    div.appendChild(bubble);
    messagesEl.appendChild(div);
    scrollBottom();
  }

  function appendBotMessage(text) {
    var div = document.createElement("div");
    div.className = "msg bot";
    var bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.textContent = text;
    div.appendChild(bubble);
    messagesEl.appendChild(div);
    scrollBottom();
  }

  function appendTyping() {
    var id  = "typing-" + Date.now();
    var div = document.createElement("div");
    div.className = "msg bot";
    div.id = id;
    div.innerHTML = '<div class="bubble"><div class="typing-dots"><span></span><span></span><span></span></div></div>';
    messagesEl.appendChild(div);
    scrollBottom();
    return id;
  }

  function removeTyping(id) {
    var el = document.getElementById(id);
    if (el) el.parentNode.removeChild(el);
  }

  function appendProducts(products) {
    var container = document.createElement("div");
    container.className = "msg bot";
    var inner = document.createElement("div");
    inner.style.cssText = "display:flex;flex-direction:column;gap:8px;width:100%;max-width:320px;";

    products.forEach(function (p) {
      var meta  = p.metadata || {};
      var card  = document.createElement("div");
      card.className = "product-card";

      var img = document.createElement("img");
      img.src = meta.image || "";
      img.alt = meta.name || "Product";
      img.onerror = function () { this.style.display = "none"; };

      var info = document.createElement("div");
      info.className = "product-info";

      var name = document.createElement("div");
      name.className = "product-name";
      name.textContent = meta.name || p.product_id;

      var metaLine = document.createElement("div");
      metaLine.className = "product-meta";
      var rating = meta.rating ? "⭐ " + meta.rating + "/5  · " : "";
      metaLine.textContent = rating + (meta.category || "");

      var price = document.createElement("div");
      price.className = "product-price";
      price.textContent = meta.price != null ? "Rs. " + Number(meta.price).toLocaleString() : "";

      // View product link (shown only when a URL is available)
      var viewLink = null;
      var productUrl = (meta.url || "").trim();
      if (productUrl && productUrl !== "undefined") {
        viewLink = document.createElement("a");
        viewLink.className = "product-view-link";
        viewLink.textContent = "View Product →";
        viewLink.href = productUrl;
        viewLink.target = "_blank";
        viewLink.rel = "noopener noreferrer";
        viewLink.addEventListener("click", function (e) { e.stopPropagation(); });
      }

      info.appendChild(name);
      info.appendChild(metaLine);
      info.appendChild(price);
      if (viewLink) info.appendChild(viewLink);
      card.appendChild(img);
      card.appendChild(info);

      // Click the card body → open the product page in a new tab (if URL is available),
      // otherwise fall back to asking the bot for more details
      card.style.cursor = "pointer";
      card.addEventListener("click", function () {
        if (productUrl && productUrl !== "undefined") {
          window.open(productUrl, "_blank", "noopener,noreferrer");
        } else {
          inputEl.value = "Tell me more about " + (meta.name || "this product");
          handleSend();
        }
      });

      inner.appendChild(card);
    });

    container.appendChild(inner);
    messagesEl.appendChild(container);
    scrollBottom();
  }

  function appendComparisonTable(comparison) {
    var table = comparison.comparison_table;
    var narrative = comparison.narrative_summary || "";
    if (!table || !table.headers || !table.rows || !table.rows.length) {
      appendBotMessage("\uD83D\uDCCA Could not render comparison table.");
      return;
    }

    // headers: ["Product", attr1, attr2, ...]
    // rows: [{"Product": "Name", attr1: val, attr2: val}, ...]
    var attrs = table.headers.slice(1); // skip "Product" header
    var products = table.rows;

    // Find best value per numeric attribute for highlighting
    function bestIndex(attr) {
      var vals = products.map(function (r) { return parseFloat(r[attr]); });
      if (vals.some(isNaN)) return -1;
      // price → lowest is best; everything else → highest is best
      if (attr === "price") {
        var mn = Math.min.apply(null, vals);
        return vals.indexOf(mn);
      }
      var mx = Math.max.apply(null, vals);
      return vals.indexOf(mx);
    }

    var outer = document.createElement("div");
    outer.className = "msg bot";

    var wrap = document.createElement("div");
    wrap.className = "comparison-wrap";

    var tbl = document.createElement("table");
    tbl.className = "comparison-table";

    // Header row: first cell blank (attr label column), then one column per product
    var thead = document.createElement("thead");
    var hrow  = document.createElement("tr");
    var thBlank = document.createElement("th");
    thBlank.textContent = "";
    hrow.appendChild(thBlank);
    products.forEach(function (p) {
      var th = document.createElement("th");
      th.textContent = p["Product"] || "Product";
      hrow.appendChild(th);
    });
    thead.appendChild(hrow);
    tbl.appendChild(thead);

    // Body rows: one row per attribute
    var tbody = document.createElement("tbody");
    attrs.forEach(function (attr) {
      var tr = document.createElement("tr");
      var tdLabel = document.createElement("td");
      tdLabel.textContent = attr.replace(/_/g, " ");
      tr.appendChild(tdLabel);

      var best = bestIndex(attr);
      products.forEach(function (p, i) {
        var td = document.createElement("td");
        var val = p[attr];
        td.textContent = (val !== undefined && val !== null && val !== "N/A") ? val : "—";
        if (i === best) td.className = "comparison-winner";
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
    tbl.appendChild(tbody);

    wrap.appendChild(tbl);
    outer.appendChild(wrap);

    // Narrative summary below the table
    if (narrative) {
      var narDiv = document.createElement("div");
      narDiv.className = "comparison-narrative";
      narDiv.textContent = narrative;
      outer.appendChild(narDiv);
    }

    messagesEl.appendChild(outer);
    scrollBottom();
  }

  // -------------------------------------------------------------------------
  // Utilities
  // -------------------------------------------------------------------------
  function scrollBottom() {
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function autoResize() {
    inputEl.style.height = "auto";
    inputEl.style.height = Math.min(inputEl.scrollHeight, 96) + "px";
    parent.postMessage({ type: "QB_RESIZE", height: document.body.scrollHeight }, "*");
  }

  function generateId() {
    return "qb-" + Math.random().toString(36).slice(2, 11);
  }

  function shadeColor(hex, pct) {
    var num = parseInt(hex.slice(1), 16);
    var r   = Math.min(255, Math.max(0, (num >> 16) + pct));
    var g   = Math.min(255, Math.max(0, ((num >> 8) & 0xff) + pct));
    var b   = Math.min(255, Math.max(0, (num & 0xff) + pct));
    return "#" + ((r << 16) | (g << 8) | b).toString(16).padStart(6, "0");
  }

})();
