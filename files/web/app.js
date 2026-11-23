// Proxlafy · panel logic · lógica del panel (vanilla JS, offline)
(function () {
  "use strict";
  var lang = window.pickLang();
  var T = function (k) { return (window.I18N[lang] && window.I18N[lang][k]) || k; };
  var reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;

  var state = {
    role: null, authOpen: false, demo: false, connected: false,
    sim: null, pending: null, band: "auto", filter: "all", query: "",
    lastRead: null, cards: [], logCursor: 0, version: "–", view: "read",
  };

  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $id = function (id) { return document.getElementById(id); };

  // ------------------------------------------------ i18n
  function applyI18n() {
    document.documentElement.lang = lang;
    $id("lang-toggle").textContent = lang === "es" ? "EN" : "ES";
    document.querySelectorAll("[data-i18n]").forEach(function (n) { n.textContent = T(n.getAttribute("data-i18n")); });
    document.querySelectorAll("[data-i18n-ph]").forEach(function (n) { n.placeholder = T(n.getAttribute("data-i18n-ph")); });
  }
  $id("lang-toggle").onclick = function () {
    lang = lang === "es" ? "en" : "es";
    try { localStorage.setItem("proxlafy_lang", lang); } catch (e) {}
    applyI18n(); renderAll();
  };

  // ------------------------------------------------ api / toast
  function api(path, opts) {
    opts = opts || {};
    opts.headers = opts.headers || {};
    if (opts.body && typeof opts.body !== "string") { opts.headers["Content-Type"] = "application/json"; opts.body = JSON.stringify(opts.body); }
    return fetch(path, opts).then(function (r) {
      return r.json().catch(function () { return { ok: false }; }).then(function (j) { j._status = r.status; return j; });
    });
  }
  var toastT;
  function toast(msg, kind) {
    var t = $id("toast"); t.textContent = msg; t.className = "toast " + (kind || ""); t.hidden = false;
    clearTimeout(toastT); toastT = setTimeout(function () { t.hidden = true; }, 2600);
  }
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (m) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[m]; }); }

  // ------------------------------------------------ auth
  $id("login-btn").onclick = function () {
    api("/api/login", { method: "POST", body: { password: $id("login-pw").value } }).then(function (j) {
      if (j.ok) { $id("login-err").hidden = true; $id("login-pw").value = ""; boot(); }
      else { $id("login-err").textContent = j.error || T("err_generic"); $id("login-err").hidden = false; }
    });
  };
  $id("login-pw").addEventListener("keydown", function (e) { if (e.key === "Enter") $id("login-btn").click(); });
  $id("logout").onclick = function () { api("/api/logout", { method: "POST" }).then(showLogin); };
  function showLogin() { $id("login").hidden = false; $id("main").hidden = true; $id("logout").hidden = true; }
  function showMain() { $id("login").hidden = true; $id("main").hidden = false; }

  // ------------------------------------------------ views (seg pill)
  document.querySelectorAll(".seg-item").forEach(function (b, i) {
    b.onclick = function () { setView(b.getAttribute("data-view"), i); };
  });
  function setView(name, idx) {
    state.view = name;
    var items = Array.prototype.slice.call(document.querySelectorAll(".seg-item"));
    items.forEach(function (x, i) { x.classList.toggle("active", x.getAttribute("data-view") === name); if (x.getAttribute("data-view") === name) idx = i; });
    $(".seg-nav").style.setProperty("--active", idx);
    ["read", "scan", "library", "system"].forEach(function (v) { $id("view-" + v).hidden = v !== name; });
    if (name === "library") refreshCards();
    if (name === "system") loadStandalone();
  }

  // ------------------------------------------------ status
  function refreshStatus() {
    return api("/api/status").then(function (j) {
      if (!j.ok) return;
      var s = j.status;
      state.role = s.role; state.authOpen = s.auth_open; state.demo = s.demo;
      state.connected = s.connected; state.sim = s.simulating; state.pending = s.pending_sim;
      if (s.firmware && s.firmware !== "?") $id("version").title = s.firmware;
      if (s.version) { state.version = s.version; $id("version").textContent = "v" + s.version; }
      if (s.role === null && !s.auth_open) { showLogin(); return; }
      showMain();
      $id("logout").hidden = s.auth_open;
      renderDevice(s); renderSimbar(); renderSystem(s);
    }).catch(function () {});
  }
  function renderDevice(s) {
    var dot = $id("dev-dot"), txt = $id("dev-state"), fw = $id("dev-fw"), pill = $id("dev-pill");
    dot.className = "dot";
    if (s.demo) { dot.classList.add("demo"); txt.textContent = T("dev_demo"); fw.textContent = s.firmware || ""; }
    else if (s.connected) { dot.classList.add("ok"); txt.textContent = T("dev_connected"); fw.textContent = s.firmware || ""; }
    else { dot.classList.add("off"); txt.textContent = T("dev_disconnected"); fw.textContent = s.error || ""; }
    pill.hidden = !s.demo; pill.textContent = "DEMO";
  }
  function renderSystem(s) {
    $id("sys-fw").textContent = s.firmware || "–";
    var conn = $id("sys-conn"); conn.textContent = s.connected ? T("conn_yes") : T("conn_no");
    conn.className = s.connected ? "ok" : "off";
    $id("sys-ver").textContent = "v" + (s.version || "–");
    if (s.count != null) $id("sys-count").textContent = s.count;
  }
  function renderSimbar() {
    var bar = $id("simbar"), live = state.sim, pend = state.pending;
    if (live) {
      bar.hidden = false; bar.className = "simbar live";
      $id("simbar-kicker").textContent = T("emulating");
      $id("simbar-text").textContent = live.name || live.label || live.type;
    } else if (pend) {
      bar.hidden = false; bar.className = "simbar pending";
      $id("simbar-kicker").textContent = T("resuming");
      $id("simbar-text").textContent = pend.name || pend.label || pend.type;
    } else { bar.hidden = true; }
    markSimming();
  }
  $id("simbar-stop").onclick = function () {
    api("/api/emulate/stop", { method: "POST" }).then(function () { state.sim = null; state.pending = null; renderSimbar(); toast(T("emulate_stopped")); });
  };

  // ------------------------------------------------ capabilities / data helpers
  function capsHTML(card) {
    var c = card.caps || {}; var h = "";
    h += '<span class="cap ' + (c.emulable ? "yes" : "no") + '">' + (c.emulable ? "▶ " + T("cap_emulable") : T("cap_not_emulable")) + "</span>";
    h += '<span class="cap ' + (c.clonable ? "yes" : "no") + '">' + (c.clonable ? "⎘ " + T("cap_clonable") : T("cap_not_clonable")) + "</span>";
    if (c.target) h += '<span class="cap target">→ ' + esc(c.target) + "</span>";
    if (c.secure) h += '<span class="cap secure">🔒 ' + T("cap_secure") + "</span>";
    if (card.decoded) h += '<span class="cap yes">✓ ' + T("cap_decoded") + "</span>";
    return h;
  }
  function dataHTML(card) {
    var d = card.data || {}; var rows = "";
    Object.keys(d).forEach(function (k) {
      if (k.charAt(0) === "_") return;
      var v = d[k]; if (v === true) v = "✓"; if (v === false) return;
      rows += "<dt>" + esc(k) + "</dt><dd>" + esc(v) + "</dd>";
    });
    return rows ? '<dl class="kv">' + rows + "</dl>" : "";
  }
  function noteHTML(card) {
    var c = card.caps || {}; var note = lang === "es" ? c.notes_es : c.notes_en;
    if (!note) return "";
    return '<div class="note' + (c.secure ? " secure" : "") + '">' + esc(note) + "</div>";
  }
  function verdictLabel(v) { return T("v_" + v); }
  function feasBlock(kind, fe) {
    if (!fe) return "";
    var icon = kind === "emulate" ? "▶" : "⎘", v = fe.verdict;
    var h = '<div class="feas-sub"><div class="feas-head"><span>' + icon + '</span><span class="fname">' + T("feas_" + kind) + '</span><span class="verdict ' + v + '">' + verdictLabel(v) + "</span></div>";
    if (v !== "no") {
      h += '<div class="meter"><span class="meter-fill ' + v + '" style="--p:' + (fe.score / 100) + '"></span></div>';
      h += '<div class="feas-score">' + fe.score + "% · " + T("chance") + "</div>";
    }
    var items = "";
    (fe.requirements || []).forEach(function (r) { items += '<li class="req ' + (r.level || "") + '"><span class="ic">◆</span>' + esc(lang === "es" ? r.es : r.en) + "</li>"; });
    (fe.risks || []).forEach(function (r) { items += '<li class="' + (r.level || "low") + '"><span class="ic">⚠</span>' + esc(lang === "es" ? r.es : r.en) + "</li>"; });
    if (items) h += '<ul class="feas-list">' + items + "</ul>";
    return h + "</div>";
  }
  function feasHTML(card) {
    if (!card.feasibility) return "";
    var f = card.feasibility;
    return '<div class="feas"><div class="feas-title">' + T("feas_title") + "</div>" + feasBlock("emulate", f.emulate) + feasBlock("clone", f.clone) + "</div>";
  }
  function modulesHTML(card) {
    if (!card.modules || !card.modules.length) return "";
    var hasRun = card.modules.some(function (m) { return m.action && m.status === "ready"; });
    var h = '<div class="mods"><div class="mods-head"><div class="feas-title">' + T("mods_title") + "</div>";
    if (hasRun) h += '<button class="btn runflow" data-a="runflow">▶ ' + T("run_flow") + "</button>";
    h += "</div>";
    card.modules.forEach(function (m) {
      var mark = m.status === "done" ? "✓" : (m.status === "blocked" ? "🔒" : (m.status === "ready" ? "›" : "·"));
      h += '<div class="mod ' + m.status + '"><div class="mod-dot">' + mark + '</div><div class="mod-body"><div class="mod-title">' + esc(lang === "es" ? m.title_es : m.title_en) + '</div><div class="mod-desc">' + esc(lang === "es" ? m.desc_es : m.desc_en) + "</div>";
      if (m.action && m.status === "ready") h += '<button class="btn mod-btn" data-a="' + m.action + '">' + T("mod_run") + "</button>";
      if (m.status === "blocked") h += '<div class="mod-hint">' + T("mod_blocked") + "</div>";
      h += "</div></div>";
    });
    return h + "</div>";
  }
  function candidateHTML(card) {
    if (!card.candidate || !card.candidate.blank) return "";
    return '<div class="candidate"><span class="ic">✓</span><div><b>' + esc(T("candidate_blank")) + '</b><div class="cnote">' + esc(lang === "es" ? card.candidate.note_es : card.candidate.note_en) + "</div></div></div>";
  }
  function headSubHTML(card) {
    return '<div class="sheet-head"><span class="badge ' + card.band + '">' + card.band.toUpperCase() + '</span><span class="sheet-title">' + esc(card.type) + '</span></div><div class="tag-sub" style="margin:2px 0 4px">' + esc(card.label || "") + "</div>";
  }

  // ------------------------------------------------ READ
  document.querySelectorAll("#view-read .seg-btn").forEach(function (b) {
    b.onclick = function () {
      document.querySelectorAll("#view-read .seg-btn").forEach(function (x) { x.classList.remove("active"); });
      b.classList.add("active"); state.band = b.getAttribute("data-band");
    };
  });
  $id("read-btn").onclick = function () {
    if (state.sim) { toast(T("emulating")); return; }
    setLoading($id("read-btn"), true);
    api("/api/read", { method: "POST", body: { band: state.band } }).then(function (j) {
      setLoading($id("read-btn"), false);
      if (!j.ok) { toast(j.error || T("err_generic"), "err"); return; }
      state.lastRead = j.card; renderRead(j.card);
    }).catch(function () { setLoading($id("read-btn"), false); });
  };
  function setLoading(btn, on) {
    btn.disabled = on;
    var lab = $(".btn-label", btn), dots = $(".loader-dots", btn);
    if (lab) lab.textContent = on ? T("reading") : T("read");
    if (dots) dots.hidden = !on;
  }
  function detailInnerHTML(card, ctx) {
    return headSubHTML(card) + (ctx === "scan" ? candidateHTML(card) : "") +
      '<div class="caps">' + capsHTML(card) + "</div>" + dataHTML(card) + noteHTML(card) +
      feasHTML(card) + actionsHTML(card, "read") + modulesHTML(card);
  }
  function renderRead(card) {
    var box = $id("read-result");
    if (!card) { box.innerHTML = '<div class="card detect"><p class="muted">' + esc(T("no_card")) + "</p></div>"; return; }
    box.innerHTML = '<div class="card detect card-detail">' + detailInnerHTML(card, "read") + "</div>";
    wireActions(box, card, "read");
  }

  // ------------------------------------------------ SCAN / IDENTIFY
  document.querySelectorAll("#scan-band .seg-btn").forEach(function (b) {
    b.onclick = function () {
      document.querySelectorAll("#scan-band .seg-btn").forEach(function (x) { x.classList.remove("active"); });
      b.classList.add("active"); state.scanBand = b.getAttribute("data-band");
    };
  });
  $id("scan-btn").onclick = function () {
    if (state.sim) { toast(T("emulating")); return; }
    setLoadingScan(true);
    api("/api/read", { method: "POST", body: { band: state.scanBand || "auto" } }).then(function (j) {
      setLoadingScan(false);
      if (!j.ok) { toast(j.error || T("err_generic"), "err"); return; }
      renderScan(j.card);
    }).catch(function () { setLoadingScan(false); });
  };
  function setLoadingScan(on) {
    var btn = $id("scan-btn"); btn.disabled = on;
    var lab = $(".btn-label", btn), dots = $(".loader-dots", btn);
    if (lab) lab.textContent = on ? T("reading") : T("scan_btn");
    if (dots) dots.hidden = !on;
  }
  function renderScan(card) {
    var box = $id("scan-result");
    if (!card) { box.innerHTML = '<div class="card detect"><p class="muted">' + esc(T("no_card")) + "</p></div>"; return; }
    state.lastScan = card;
    box.innerHTML = '<div class="card detect card-detail">' + detailInnerHTML(card, "scan") + "</div>";
    wireActions(box, card, "scan");
  }

  // ------------------------------------------------ action buttons (shared read + sheet)
  function actionsHTML(card, ctx) {
    var c = card.caps || {}; var h = '<div class="btn-row" style="margin-top:14px">';
    if (ctx === "read") h += '<button class="btn btn-primary" data-a="save">' + T("save_card") + "</button>";
    if (c.decode && !card.decoded) h += '<button class="btn" data-a="decode">' + (c.secure ? "🔑 " + T("decode_keys") : T("decode")) + "</button>";
    if (c.emulable) h += '<button class="btn ' + (ctx === "sheet" ? "btn-primary" : "") + '" data-a="emit">▶ ' + T("emit") + "</button>";
    if (c.clonable) h += '<button class="btn" data-a="write">⎘ ' + T("write_to") + " " + esc((c.target || "").split("/")[0].trim()) + "</button>";
    h += "</div>";
    if (ctx === "sheet") {
      h += '<div class="sheet-field"><label>' + T("name") + '</label><input id="sf-name" type="text" maxlength="80" value="' + esc(card.name || "") + '"></div>';
      h += '<div class="sheet-field"><label>' + T("notes") + '</label><textarea id="sf-notes" rows="2" maxlength="500">' + esc(card.notes || "") + "</textarea></div>";
      h += '<div class="btn-row"><button class="btn" data-a="savemeta">' + T("save") + '</button><button class="btn btn-ghost" data-a="del">🗑 ' + T("del") + "</button></div>";
    }
    if (card.raw_output) h += '<details class="console grow" style="padding:0;margin-top:10px;border:0"><summary class="small muted">' + T("raw") + '</summary><div class="sheet-raw">' + esc(card.raw_output.trim()) + "</div></details>";
    return h;
  }
  function wireActions(root, card, ctx) {
    root.querySelectorAll("[data-a]").forEach(function (b) {
      b.onclick = function () { doAction(b.getAttribute("data-a"), card, ctx, b); };
    });
  }
  function doAction(a, card, ctx, btn) {
    if (a === "save") {
      var name = prompt(T("name") + ":", card.type + " · " + (card.label || ""));
      if (name === null) return;
      api("/api/cards", { method: "POST", body: { name: name, card: card } }).then(function (j) {
        if (j.ok) { toast(T("save") + " ✓", "ok"); (ctx === "scan" ? $id("scan-result") : $id("read-result")).innerHTML = ""; refreshCards(); }
        else toast(j.error || T("err_generic"), "err");
      });
    } else if (a === "emit") {
      var body = card.id ? { id: card.id } : { card: card };
      api("/api/emulate", { method: "POST", body: body }).then(function (j) {
        if (j.ok) { toast(T("emulate_started") + ": " + (card.name || card.label), "ok"); closeSheet(); refreshStatus(); }
        else toast(j.error || T("err_generic"), "err");
      });
    } else if (a === "decode") {
      if (btn) { btn.disabled = true; btn.textContent = T("decoding"); }
      var url = card.id ? "/api/cards/" + card.id + "/decode" : "/api/decode";
      var opt = card.id ? { method: "POST" } : { method: "POST", body: { card: card } };
      api(url, opt).then(function (j) {
        if (j.ok) { toast(T("decode") + " ✓", "ok"); if (j.card) { card = j.card; if (ctx === "sheet") openSheet(card); else if (ctx === "scan") renderScan(card); else renderRead(card); } refreshCards(); }
        else { toast((j.result && j.result.error) || j.error || T("err_generic"), "err"); if (btn) { btn.disabled = false; } }
      });
    } else if (a === "write") {
      if (!confirm(T("write_confirm"))) return;
      if (btn) { btn.disabled = true; btn.textContent = T("cloning"); }
      var wurl = card.id ? "/api/cards/" + card.id + "/write" : null;
      if (!wurl) { toast(T("save_card") + " →", "err"); if (btn) btn.disabled = false; return; }
      api(wurl, { method: "POST" }).then(function (j) {
        toast(j.ok ? "OK ✓" : (j.error || T("err_generic")), j.ok ? "ok" : "err");
        if (btn) { btn.disabled = false; btn.textContent = "⎘ " + T("write_to"); }
      });
    } else if (a === "savemeta") {
      api("/api/cards/" + card.id, { method: "PATCH", body: { name: $id("sf-name").value, notes: $id("sf-notes").value } })
        .then(function (j) { if (j.ok) { toast(T("save") + " ✓", "ok"); closeSheet(); refreshCards(); } });
    } else if (a === "del") {
      if (!confirm(T("confirm_del"))) return;
      api("/api/cards/" + card.id, { method: "DELETE" }).then(function () { closeSheet(); refreshCards(); });
    } else if (a === "runflow") {
      var mods = card.modules || [];
      var needsDecode = mods.some(function (m) { return m.key === "decode" && m.status === "ready"; });
      var finish = function (c) { var em = (c.caps || {}).emulable; doAction(em ? "emit" : "write", c, ctx); };
      if (needsDecode) {
        toast(T("decoding"));
        var durl = card.id ? "/api/cards/" + card.id + "/decode" : "/api/decode";
        var dopt = card.id ? { method: "POST" } : { method: "POST", body: { card: card } };
        api(durl, dopt).then(function (j) { finish(j.ok && j.card ? j.card : card); });
      } else { finish(card); }
    }
  }

  // ------------------------------------------------ LIBRARY
  function refreshCards() { return api("/api/cards").then(function (j) { if (j.ok) { state.cards = j.cards || []; renderLibrary(); } }); }
  $id("lib-search").addEventListener("input", function (e) { state.query = e.target.value.toLowerCase(); renderLibrary(); });
  document.querySelectorAll("#view-library .filter .seg-btn").forEach(function (b) {
    b.onclick = function () {
      document.querySelectorAll("#view-library .filter .seg-btn").forEach(function (x) { x.classList.remove("active"); });
      b.classList.add("active"); state.filter = b.getAttribute("data-filter"); renderLibrary();
    };
  });
  function filtered() {
    return state.cards.filter(function (c) {
      if (state.filter !== "all" && c.band !== state.filter) return false;
      if (state.query) { var hay = (c.name || "") + " " + (c.type || "") + " " + (c.label || ""); if (hay.toLowerCase().indexOf(state.query) < 0) return false; }
      return true;
    });
  }
  function renderLibrary() {
    var wrap = $id("library"); wrap.querySelectorAll(".tag").forEach(function (n) { n.remove(); });
    var list = filtered();
    $id("lib-empty").style.display = list.length ? "none" : "";
    var frag = document.createDocumentFragment();
    list.forEach(function (c) { frag.appendChild(tagNode(c)); });
    wrap.appendChild(frag);
    markSimming();
  }
  function tagNode(c) {
    var b = document.createElement("button"); b.className = "tag"; if (!reduce) b.classList.add("fresh");
    b.setAttribute("data-id", c.id);
    var caps = c.caps || {};
    var flags = "";
    if (caps.emulable) flags += '<span title="emulable">▶</span>';
    if (caps.clonable) flags += '<span title="clonable">⎘</span>';
    if (caps.secure) flags += '<span class="on-sec" title="secure">🔒</span>';
    b.innerHTML =
      '<span class="badge ' + c.band + '">' + c.band.toUpperCase() + "</span>" +
      '<span class="tag-title"><span class="tag-name">' + esc(c.name || c.type) + "</span>" +
      '<span class="tag-sub">' + esc(c.type + " · " + (c.label || "")) + "</span></span>" +
      '<span class="tag-flags">' + flags + "</span>";
    b.onclick = function () { openSheet(c); };
    if (!reduce) b.addEventListener("animationend", function () { b.classList.remove("fresh"); }, { once: true });
    return b;
  }
  function markSimming() {
    var id = (state.sim && state.sim.id) || (state.pending && state.pending.id);
    document.querySelectorAll("#library .tag").forEach(function (n) { n.classList.toggle("simming", n.getAttribute("data-id") === id); });
  }

  // ------------------------------------------------ bottom sheet
  var sheet = $id("sheet");
  function openSheet(card) {
    var body = $id("sheet-body");
    body.innerHTML =
      '<div class="sheet-head"><span class="badge ' + card.band + '">' + card.band.toUpperCase() + "</span>" +
        '<span class="sheet-title">' + esc(card.name || card.type) + "</span></div>" +
      '<div class="tag-sub" style="margin:2px 0 6px">' + esc(card.type + " · " + (card.label || "")) + "</div>" +
      '<div class="caps">' + capsHTML(card) + "</div>" + dataHTML(card) + noteHTML(card) +
      feasHTML(card) + actionsHTML(card, "sheet") + modulesHTML(card);
    wireActions(body, card, "sheet");
    if (typeof sheet.showModal === "function") { if (!sheet.open) sheet.showModal(); } else { sheet.setAttribute("open", ""); }
  }
  function closeSheet() { if (sheet.open) { try { sheet.close(); } catch (e) { sheet.removeAttribute("open"); } } }
  sheet.addEventListener("click", function (e) { if (e.target === sheet) closeSheet(); });

  // ------------------------------------------------ console log
  function refreshLog() {
    return api("/api/log?since=" + state.logCursor).then(function (j) {
      if (!j.ok) return; state.logCursor = j.cursor;
      var box = $id("console-log");
      (j.items || []).forEach(function (it) {
        var line = document.createElement("div"); line.className = "console-line " + (it.level || "");
        line.innerHTML = '<span class="ts">' + esc(new Date(it.t * 1000).toLocaleTimeString()) + "</span>" + esc(it.text);
        box.appendChild(line);
      });
      if (j.items && j.items.length) box.scrollTop = box.scrollHeight;
    }).catch(function () {});
  }

  // ------------------------------------------------ standalone
  function loadStandalone() {
    return api("/api/standalone?lang=" + lang).then(function (j) {
      if (!j.ok) return;
      state.standalone = j; renderStandalone();
    }).catch(function () {});
  }
  function renderStandalone() {
    var j = state.standalone; if (!j) return;
    var cur = (j.status && j.status.current) || null;
    var flashing = j.status && j.status.flashing;
    $id("std-current").innerHTML = T("std_current") + ": " +
      (cur ? '<span class="chip-mode">' + esc(cur) + "</span>" : '<span class="chip-mode none">' + T("std_none") + "</span>");
    var modes = (j.catalog && j.catalog.modes) || [];
    $id("std-modes").innerHTML = modes.map(function (m) {
      var on = cur === m.id;
      var badges = '<span class="std-badge ' + m.band + '">' + m.band.toUpperCase() + "</span>";
      if (m.rec) badges += '<span class="std-badge rec">' + T("std_rec") + "</span>";
      if (m.flash) badges += '<span class="std-badge rdv4">' + T("std_rdv4") + "</span>";
      var btn = on ? "" : '<button class="btn' + (m.rec ? " btn-primary" : "") + '" data-flash="' + m.id + '"' + (flashing ? " disabled" : "") + ">" + (flashing ? T("std_flashing") : T("std_flash")) + "</button>";
      return '<div class="std-mode' + (on ? " on" : "") + '"><div class="std-mode-head"><span class="std-id">' + esc(m.id) + "</span>" + badges + '</div><div class="std-name">' + esc(m.name) + '</div><div class="std-desc">' + esc(m.desc) + "</div>" + btn + "</div>";
    }).join("");
    $id("std-modes").querySelectorAll("[data-flash]").forEach(function (b) {
      b.onclick = function () {
        if (!confirm(T("std_confirm"))) return;
        api("/api/standalone/flash", { method: "POST", body: { mode: b.getAttribute("data-flash") } })
          .then(function (r) { if (r.ok) { toast(T("std_flashing"), "ok"); setView("system"); setTimeout(loadStandalone, 800); } });
      };
    });
    var repos = (j.catalog && j.catalog.repos) || [];
    $id("std-repos").innerHTML = repos.map(function (r) {
      return '<div class="std-repo"><b>' + esc(r.name) + '</b> <span class="st">★' + r.stars + '</span><span class="rw">' + esc(r.what) + "</span></div>";
    }).join("");
  }

  function renderAll() { renderRead(state.lastRead); if (state.lastScan) renderScan(state.lastScan); renderLibrary(); if (state.standalone) renderStandalone(); }

  // ------------------------------------------------ boot
  function boot() { refreshStatus().then(refreshCards).then(refreshLog); }
  applyI18n(); boot();
  setInterval(refreshStatus, 2500);
  setInterval(refreshLog, 1500);
})();
