// Proxlafy · panel logic · lógica del panel (vanilla JS, offline)
(function () {
  "use strict";

  var lang = window.pickLang();
  var T = function (k) { return (window.I18N[lang] && window.I18N[lang][k]) || k; };

  var state = {
    role: null, authOpen: false, demo: false, connected: false,
    simulating: null, band: "auto", lastRead: null, cards: [], logCursor: 0, version: "–",
  };

  // ---------------------------------------------------------------- DOM
  var $ = function (id) { return document.getElementById(id); };
  var el = {
    login: $("login"), loginPw: $("login-pw"), loginBtn: $("login-btn"), loginErr: $("login-err"),
    main: $("main"), logout: $("logout"), langToggle: $("lang-toggle"), version: $("version"),
    devDot: $("dev-dot"), devState: $("dev-state"), devFw: $("dev-fw"),
    readBtn: $("read-btn"), readResult: $("read-result"),
    library: $("library"), libCount: $("lib-count"), libEmpty: $("lib-empty"),
    simbar: $("simbar"), simbarText: $("simbar-text"), simbarStop: $("simbar-stop"),
    consoleLog: $("console-log"), toast: $("toast"),
    modal: $("modal"), modalName: $("modal-name"), modalNotes: $("modal-notes"),
    modalRaw: $("modal-raw"), modalSave: $("modal-save"), modalCancel: $("modal-cancel"), modalTitle: $("modal-title"),
  };
  var editingId = null;

  // ---------------------------------------------------------------- i18n
  function applyI18n() {
    document.documentElement.lang = lang;
    el.langToggle.textContent = lang === "es" ? "EN" : "ES";
    document.querySelectorAll("[data-i18n]").forEach(function (n) { n.textContent = T(n.getAttribute("data-i18n")); });
    document.querySelectorAll("[data-i18n-ph]").forEach(function (n) { n.placeholder = T(n.getAttribute("data-i18n-ph")); });
  }
  el.langToggle.onclick = function () {
    lang = lang === "es" ? "en" : "es";
    try { localStorage.setItem("proxlafy_lang", lang); } catch (e) {}
    applyI18n(); render();
  };

  // ---------------------------------------------------------------- API
  function api(path, opts) {
    opts = opts || {};
    opts.headers = opts.headers || {};
    if (opts.body && typeof opts.body !== "string") {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(opts.body);
    }
    return fetch(path, opts).then(function (r) {
      return r.json().catch(function () { return { ok: false, error: "bad response" }; })
        .then(function (j) { j._status = r.status; return j; });
    });
  }

  function toast(msg, kind) {
    el.toast.textContent = msg;
    el.toast.className = "toast " + (kind || "");
    clearTimeout(toast._t);
    toast._t = setTimeout(function () { el.toast.classList.add("hidden"); }, 2600);
  }

  // ---------------------------------------------------------------- auth
  el.loginBtn.onclick = function () {
    api("/api/login", { method: "POST", body: { password: el.loginPw.value } }).then(function (j) {
      if (j.ok) { el.loginErr.classList.add("hidden"); el.loginPw.value = ""; refreshStatus(); refreshCards(); }
      else { el.loginErr.textContent = j.error || T("err_generic"); el.loginErr.classList.remove("hidden"); }
    });
  };
  el.loginPw.addEventListener("keydown", function (e) { if (e.key === "Enter") el.loginBtn.click(); });
  el.logout.onclick = function () { api("/api/logout", { method: "POST" }).then(function () { showLogin(); }); };

  function showLogin() { el.login.classList.remove("hidden"); el.main.classList.add("hidden"); el.logout.classList.add("hidden"); }
  function showMain() { el.login.classList.add("hidden"); el.main.classList.remove("hidden"); }

  // ---------------------------------------------------------------- status
  function refreshStatus() {
    return api("/api/status").then(function (j) {
      if (!j.ok) return;
      var s = j.status;
      state.role = s.role; state.authOpen = s.auth_open; state.demo = s.demo;
      state.connected = s.connected; state.simulating = s.simulating;
      if (s.firmware && s.firmware !== "?") { el.version.title = s.firmware; }
      if (s.version && s.version !== state.version) { state.version = s.version; el.version.textContent = "v" + s.version; }
      if (s.role === null && !s.auth_open) { showLogin(); return; }
      showMain();
      el.logout.classList.toggle("hidden", s.auth_open);
      renderDevice(s); renderSimbar();
    }).catch(function () {});
  }

  function renderDevice(s) {
    var dot = el.devDot, txt = el.devState, fw = el.devFw;
    dot.className = "dot";
    if (s.demo) { dot.classList.add("demo"); txt.textContent = T("dev_demo"); fw.textContent = s.firmware || ""; }
    else if (s.connected) { dot.classList.add("ok"); txt.textContent = T("dev_connected"); fw.textContent = s.firmware || ""; }
    else { dot.classList.add("off"); txt.textContent = T("dev_disconnected"); fw.textContent = s.error || ""; }
  }

  function renderSimbar() {
    if (state.simulating) {
      var c = state.simulating;
      el.simbar.classList.remove("hidden");
      el.simbarText.textContent = T("emulating") + ": " + (c.name || c.label || c.type);
    } else {
      el.simbar.classList.add("hidden");
    }
    markSimming();
  }
  el.simbarStop.onclick = function () {
    api("/api/emulate/stop", { method: "POST" }).then(function () { state.simulating = null; renderSimbar(); toast(T("emulate_stopped")); });
  };

  // ---------------------------------------------------------------- read
  document.querySelectorAll(".seg-btn").forEach(function (b) {
    b.onclick = function () {
      document.querySelectorAll(".seg-btn").forEach(function (x) { x.classList.remove("active"); });
      b.classList.add("active"); state.band = b.getAttribute("data-band");
    };
  });
  el.readBtn.onclick = function () {
    if (state.simulating) { toast(T("emulating") + "…"); return; }
    el.readBtn.disabled = true; el.readBtn.textContent = T("reading");
    api("/api/read", { method: "POST", body: { band: state.band } }).then(function (j) {
      el.readBtn.disabled = false; el.readBtn.textContent = T("read");
      if (!j.ok) { toast(j.error || T("err_generic"), "err"); return; }
      state.lastRead = j.card; renderRead(j.card);
    }).catch(function () { el.readBtn.disabled = false; el.readBtn.textContent = T("read"); });
  };

  function renderRead(card) {
    var box = el.readResult;
    box.classList.remove("hidden");
    if (!card) { box.innerHTML = '<p class="muted">' + esc(T("no_card")) + "</p>"; return; }
    box.innerHTML =
      '<div class="tag-top">' +
        '<span class="badge ' + card.band + '">' + card.band.toUpperCase() + "</span>" +
        '<div class="tag-title"><span class="tag-name">' + esc(card.type) + "</span>" +
        '<span class="tag-sub">' + esc(card.label || "") + "</span></div></div>" +
      '<div class="btn-row" style="margin-top:12px">' +
        '<button class="btn btn-primary" id="save-read">' + esc(T("save_card")) + "</button></div>";
    $("save-read").onclick = function () {
      var name = prompt(T("name") + ":", card.type + " · " + (card.label || ""));
      if (name === null) return;
      api("/api/cards", { method: "POST", body: { name: name, card: card } }).then(function (j) {
        if (j.ok) { toast(T("saved"), "ok"); box.classList.add("hidden"); refreshCards(); }
        else { toast(j.error || T("err_generic"), "err"); }
      });
    };
  }

  // ---------------------------------------------------------------- library
  function refreshCards() {
    return api("/api/cards").then(function (j) {
      if (!j.ok) return;
      state.cards = j.cards || []; render();
    });
  }

  function render() {
    el.libCount.textContent = state.cards.length;
    var canEdit = state.authOpen || state.role === "admin";
    var frag = document.createDocumentFragment();
    el.library.querySelectorAll(".tag").forEach(function (n) { n.remove(); });
    el.libEmpty.style.display = state.cards.length ? "none" : "";
    state.cards.forEach(function (c) { frag.appendChild(cardNode(c, canEdit)); });
    el.library.appendChild(frag);
    markSimming();
  }

  function cardNode(c, canEdit) {
    var d = document.createElement("div");
    d.className = "tag"; d.setAttribute("data-id", c.id);
    var sub = c.label || c.type;
    var actions = canEdit
      ? '<div class="tag-actions">' +
          '<button class="btn btn-primary" data-act="emulate">' + esc(T("emulate")) + "</button>" +
          '<button class="btn" data-act="write">' + esc(T("write")) + "</button>" +
          '<button class="btn icon-btn" data-act="edit" title="' + esc(T("edit")) + '">✎</button>' +
          '<button class="btn icon-btn" data-act="del" title="' + esc(T("del")) + '">🗑</button>' +
        "</div>"
      : "";
    d.innerHTML =
      '<div class="tag-top">' +
        '<span class="badge ' + c.band + '">' + c.band.toUpperCase() + "</span>" +
        '<div class="tag-title"><span class="tag-name">' + esc(c.name || c.type) + "</span>" +
        '<span class="tag-sub">' + esc(sub) + "</span></div></div>" + actions;
    d.querySelectorAll("[data-act]").forEach(function (b) {
      b.onclick = function () { cardAction(b.getAttribute("data-act"), c); };
    });
    return d;
  }

  function cardAction(act, c) {
    if (act === "emulate") {
      api("/api/cards/" + c.id + "/emulate", { method: "POST" }).then(function (j) {
        if (j.ok) { state.simulating = c; renderSimbar(); toast(T("emulate_started") + ": " + (c.name || c.label)); }
        else { toast(j.error || T("err_generic"), "err"); }
      });
    } else if (act === "write") {
      if (!confirm(T("write_confirm"))) return;
      toast(T("write") + "…");
      api("/api/cards/" + c.id + "/write", { method: "POST" }).then(function (j) {
        toast(j.ok ? "OK ✓" : (j.error || T("err_generic")), j.ok ? "ok" : "err");
      });
    } else if (act === "del") {
      if (!confirm(T("confirm_del"))) return;
      api("/api/cards/" + c.id, { method: "DELETE" }).then(function () { refreshCards(); });
    } else if (act === "edit") {
      openModal(c);
    }
  }

  function markSimming() {
    var simId = state.simulating && state.simulating.id;
    el.library.querySelectorAll(".tag").forEach(function (n) {
      n.classList.toggle("simming", n.getAttribute("data-id") === simId);
    });
  }

  // ---------------------------------------------------------------- modal
  function openModal(c) {
    editingId = c.id;
    el.modalName.value = c.name || "";
    el.modalNotes.value = c.notes || "";
    el.modalRaw.textContent = (c.raw_output || "").trim();
    el.modal.classList.remove("hidden");
  }
  el.modalCancel.onclick = function () { el.modal.classList.add("hidden"); };
  el.modalSave.onclick = function () {
    if (!editingId) return;
    api("/api/cards/" + editingId, { method: "PATCH", body: { name: el.modalName.value, notes: el.modalNotes.value } })
      .then(function (j) { el.modal.classList.add("hidden"); if (j.ok) refreshCards(); });
  };
  el.modal.addEventListener("click", function (e) { if (e.target === el.modal) el.modal.classList.add("hidden"); });

  // ---------------------------------------------------------------- console log
  function refreshLog() {
    return api("/api/log?since=" + state.logCursor).then(function (j) {
      if (!j.ok) return;
      state.logCursor = j.cursor;
      (j.items || []).forEach(function (it) {
        var line = document.createElement("div");
        line.className = "console-line " + (it.level || "");
        var ts = new Date(it.t * 1000).toLocaleTimeString();
        line.innerHTML = '<span class="ts">' + esc(ts) + "</span>" + esc(it.text);
        el.consoleLog.appendChild(line);
      });
      if (j.items && j.items.length) el.consoleLog.scrollTop = el.consoleLog.scrollHeight;
    }).catch(function () {});
  }

  // ---------------------------------------------------------------- util
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (m) {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[m];
  }); }

  // ---------------------------------------------------------------- boot
  applyI18n();
  refreshStatus().then(refreshCards).then(refreshLog);
  setInterval(refreshStatus, 2500);
  setInterval(refreshLog, 1500);
})();
