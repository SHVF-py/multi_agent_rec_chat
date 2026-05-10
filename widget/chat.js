/**
 * Quiribot Widget Shell — chat.js
 * Runs inside the sandboxed iframe.
 * Talks to the Quiribot API (port 8080) and the parent page via postMessage.
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

  // Apply primary color from config
  document.documentElement.style.setProperty("--primary", COLOR);
  document.documentElement.style.setProperty("--primary-dark", shadeColor(COLOR, -15));
  document.getElementById("header-name").textContent = BOT_NAME;

  // -------------------------------------------------------------------------
  // State
  // -------------------------------------------------------------------------
  var sessionId   = generateId();
  var chatHistory = [];   // [{role, content}] for the API
  var pendingText = "";   // pre-filled from proactive message

  // -------------------------------------------------------------------------
  // DOM refs
  // -------------------------------------------------------------------------
  var messagesEl = document.getElementById("messages");
  var inputEl    = document.getElementById("user-input");
  var sendBtn    = document.getElementById("send-btn");
  var closeBtn   = document.getElementById("close-btn");
  var newChatBtn = document.getElementById("new-chat-btn");

  // -------------------------------------------------------------------------
  // Boot: show greeting
  // -------------------------------------------------------------------------
  appendBotMessage(GREETING);

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
    sessionId   = generateId();
    chatHistory = [];
    messagesEl.innerHTML = "";
    appendBotMessage(GREETING);
    inputEl.focus();
  });

  // Listen for messages from loader.js (parent)
  window.addEventListener("message", function (e) {
    var msg = e.data || {};
    if (msg.type === "QB_FOCUS") { inputEl.focus(); }
    if (msg.type === "QB_PROACTIVE" && msg.message) {
      // Pre-fill input with product context
      inputEl.value = "Tell me more about this product";
      autoResize();
      appendBotMessage(msg.message);
      inputEl.focus();
    }
  });

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
        appendComparisonNote();
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
      tenant_id:    SITE_KEY,
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
      price.textContent = meta.price != null ? "$" + meta.price : "";

      info.appendChild(name);
      info.appendChild(metaLine);
      info.appendChild(price);
      card.appendChild(img);
      card.appendChild(info);

      // Click a product card → ask for more details
      card.addEventListener("click", function () {
        inputEl.value = "Tell me more about " + (meta.name || "this product");
        handleSend();
      });

      inner.appendChild(card);
    });

    container.appendChild(inner);
    messagesEl.appendChild(container);
    scrollBottom();
  }

  function appendComparisonNote() {
    appendBotMessage("📊 A comparison table is shown in the full app view.");
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
