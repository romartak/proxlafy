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

  // theme: cycle system → dark → light → system
  function setThemeIcon() { var c = document.documentElement.getAttribute("data-theme"); $id("theme-btn").textContent = c === "light" ? "☀" : (c === "dark" ? "☾" : "◐"); }
  (function () { var t; try { t = localStorage.getItem("proxlafy_theme"); } catch (e) {} if (t === "dark" || t === "light") document.documentElement.setAttribute("data-theme", t); setThemeIcon(); })();
  $id("theme-btn").onclick = function () {
    var c = document.documentElement.getAttribute("data-theme");
    var n = c === "dark" ? "light" : (c === "light" ? null : "dark");
    if (n) document.documentElement.setAttribute("data-theme", n); else document.documentElement.removeAttribute("data-theme");
    try { if (n) localStorage.setItem("proxlafy_theme", n); else localStorage.removeItem("proxlafy_theme"); } catch (e) {}
    setThemeIcon();
  };

  // expert / beginner mode
  (function () {
    var e; try { e = localStorage.getItem("proxlafy_expert") === "1"; } catch (x) {}
    document.body.classList.toggle("expert", !!e);
    var cb = $id("expert-toggle");
    if (cb) { cb.checked = !!e; cb.onchange = function () { document.body.classList.toggle("expert", cb.checked); try { localStorage.setItem("proxlafy_expert", cb.checked ? "1" : "0"); } catch (x) {} }; }
  })();

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

  // Run an async action FROM a button with honest feedback: spinner while it runs,
  // then a ✓ (green) or ✗ (red) pop that settles back to the original label. Nothing stays "stuck".
  function runBtn(btn, busyLabel, promise) {
    if (!btn) return promise;
    var orig = btn.innerHTML, w = btn.getBoundingClientRect().width;
    btn.disabled = true; btn.classList.add("busy"); btn.style.minWidth = Math.round(w) + "px";
    btn.innerHTML = '<span class="btn-spin" aria-hidden="true"></span><span>' + esc(busyLabel) + "</span>";
    function settle(cls, label) {
      btn.classList.remove("busy"); btn.classList.add(cls); btn.innerHTML = label;
      setTimeout(function () { btn.classList.remove("done", "failed"); btn.disabled = false; btn.style.minWidth = ""; btn.innerHTML = orig; }, 1500);
    }
    return promise.then(function (r) { settle((!r || r.ok !== false) ? "done" : "failed", (!r || r.ok !== false) ? "✓" : "✗"); return r; },
                        function (e) { settle("failed", "✗"); throw e; });
  }

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
    ["read", "scan", "emit", "library", "system"].forEach(function (v) { $id("view-" + v).hidden = v !== name; });
    if (name === "library") refreshCards();
    if (name === "emit") { refreshCards().then(renderEmit); loadWipe(); }
    if (name === "scan") SESSION.render();
    if (name === "system") { loadStandalone(); loadDevice(); }
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
      if (state.view === "emit") renderEmit();
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
  function wiegandHTML(card) {
    var w = card.wiegand;
    if (!w || !w.binary) return "";
    return '<div class="wieg"><div class="feas-title">Wiegand ' + w.bits + "-bit</div>" +
      '<div class="wb"><span class="par">' + w.even_parity + '</span><span class="fac">' + esc(w.facility_bits) + '</span><span class="crd">' + esc(w.card_bits) + '</span><span class="par">' + w.odd_parity + "</span></div>" +
      '<div class="wlegend"><span><b class="par">■</b> ' + T("w_parity") + '</span><span><b class="fac">■</b> ' + T("w_facility") + " " + w.fc + '</span><span><b class="crd">■</b> ' + T("w_card") + " " + w.cn + "</span></div></div>";
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
      '<div class="caps">' + capsHTML(card) + "</div>" + dataHTML(card) + wiegandHTML(card) + noteHTML(card) +
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
      renderScan(j.card); SESSION.add(j.card);
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
      h += '<div class="sheet-field"><label>' + T("tags") + '</label><input id="sf-tags" type="text" maxlength="200" placeholder="' + esc(T("tags_ph")) + '" value="' + esc((card.tags || []).join(", ")) + '"></div>';
      h += '<div class="btn-row"><button class="btn" data-a="savemeta">' + T("save") + '</button><button class="btn btn-ghost" data-a="del">🗑 ' + T("del") + "</button></div>";
    }
    if (card.raw_output) h += '<details class="console grow adv" style="padding:0;margin-top:10px;border:0"><summary class="small muted">' + T("raw") + '</summary><div class="sheet-raw">' + esc(card.raw_output.trim()) + "</div></details>";
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
      var url = card.id ? "/api/cards/" + card.id + "/decode" : "/api/decode";
      var opt = card.id ? { method: "POST" } : { method: "POST", body: { card: card } };
      runBtn(btn, T("decoding"), api(url, opt)).then(function (j) {
        if (j.ok) { toast(T("decode") + " ✓", "ok"); if (j.card) { card = j.card; if (typeof SESSION !== "undefined") SESSION.update(card); if (ctx === "sheet") openSheet(card); else if (ctx === "scan") renderScan(card); else renderRead(card); } refreshCards(); }
        else { toast((j.result && j.result.error) || j.error || T("err_generic"), "err"); }
      });
    } else if (a === "write") {
      if (!confirm(T("write_confirm"))) return;
      var wurl = card.id ? "/api/cards/" + card.id + "/write" : null;
      if (!wurl) { toast(T("save_first"), "err"); return; }
      runBtn(btn, T("cloning"), api(wurl, { method: "POST" })).then(function (j) {
        var vr = j.result && j.result.verified;
        var msg = !j.ok ? (j.error || T("err_generic")) : (vr === true ? T("verified_ok") : (vr === false ? T("verified_fail") : "OK ✓"));
        toast(msg, (j.ok && vr !== false) ? "ok" : "err");
      });
    } else if (a === "savemeta") {
      var tagsVal = ($id("sf-tags") ? $id("sf-tags").value : "").split(",").map(function (t) { return t.trim(); }).filter(Boolean);
      api("/api/cards/" + card.id, { method: "PATCH", body: { name: $id("sf-name").value, notes: $id("sf-notes").value, tags: tagsVal } })
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
      if (state.query) {
        var d = c.data || {};
        var hay = [c.name, c.type, c.label, d.uid, d.id, d.fc, d.cn, d.csn, (c.tags || []).join(" ")].join(" ");
        if (hay.toLowerCase().indexOf(state.query) < 0) return false;
      }
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
    var tagsHtml = (c.tags && c.tags.length)
      ? '<span class="tag-chips">' + c.tags.slice(0, 4).map(function (t) { return '<span class="tchip">' + esc(t) + "</span>"; }).join("") + "</span>"
      : "";
    b.innerHTML =
      '<span class="badge ' + c.band + '">' + c.band.toUpperCase() + "</span>" +
      '<span class="tag-title"><span class="tag-name">' + esc(c.name || c.type) + "</span>" +
      '<span class="tag-sub">' + esc(c.type + " · " + (c.label || "")) + "</span>" + tagsHtml + "</span>" +
      '<span class="tag-flags">' + flags + "</span>";
    b.onclick = function () { if (CMP.on) CMP.pick(c, b); else openSheet(c); };
    if (CMP.on && CMP.has(c.id)) b.classList.add("sel");
    if (!reduce) b.addEventListener("animationend", function () { b.classList.remove("fresh"); }, { once: true });
    return b;
  }
  function markSimming() {
    var id = (state.sim && state.sim.id) || (state.pending && state.pending.id);
    document.querySelectorAll("#library .tag").forEach(function (n) { n.classList.toggle("simming", n.getAttribute("data-id") === id); });
  }

  // ------------------------------------------------ compare two cards
  var CMP = (function () {
    var on = false, sel = [];
    var btn = $id("lib-compare"), hint = $id("cmp-hint"), dlg = $id("cmpsheet");
    function setOn(v) {
      on = v; sel = [];
      if (btn) btn.setAttribute("aria-pressed", v ? "true" : "false");
      if (btn) btn.classList.toggle("on", v);
      if (hint) hint.hidden = !v;
      document.body.classList.toggle("comparing", v);
      renderLibrary();
    }
    if (btn) btn.onclick = function () { setOn(!on); };
    function has(id) { return sel.indexOf(id) >= 0; }
    function pick(card, node) {
      var i = sel.indexOf(card.id);
      if (i >= 0) { sel.splice(i, 1); node.classList.remove("sel"); }
      else { sel.push(card.id); node.classList.add("sel"); if (sel.length > 2) { var drop = sel.shift(); var dn = document.querySelector('#library .tag[data-id="' + drop + '"]'); if (dn) dn.classList.remove("sel"); } }
      if (sel.length === 2) open();
    }
    function row(k, a, b, diff) {
      return '<tr' + (diff ? ' class="cmp-diff"' : "") + '><th>' + esc(k) + "</th><td>" + esc(a == null ? "—" : a) + "</td><td>" + esc(b == null ? "—" : b) + "</td></tr>";
    }
    function open() {
      var a = state.cards.filter(function (c) { return c.id === sel[0]; })[0];
      var b = state.cards.filter(function (c) { return c.id === sel[1]; })[0];
      if (!a || !b) return;
      var da = a.data || {}, db = b.data || {}, fa = a.feasibility || {}, fb = b.feasibility || {};
      var keys = [["Tipo · Type", a.type, b.type], ["Banda · Band", (a.band || "").toUpperCase(), (b.band || "").toUpperCase()],
        ["UID / ID", da.uid || da.id || da.csn, db.uid || db.id || db.csn], ["FC", da.fc, db.fc], ["CN", da.cn, db.cn],
        ["Emular · Emulate", ((fa.emulate || {}).score != null ? (fa.emulate.score + "%") : ((a.caps || {}).emulable ? "✓" : "—")), ((fb.emulate || {}).score != null ? (fb.emulate.score + "%") : ((b.caps || {}).emulable ? "✓" : "—"))],
        ["Clonar · Clone", ((fa.clone || {}).score != null ? (fa.clone.score + "%") : ((a.caps || {}).clonable ? "✓" : "—")), ((fb.clone || {}).score != null ? (fb.clone.score + "%") : ((b.caps || {}).clonable ? "✓" : "—"))],
        ["Etiquetas · Tags", (a.tags || []).join(", "), (b.tags || []).join(", ")]];
      var rows = keys.map(function (r) { return row(r[0], r[1], r[2], String(r[1] == null ? "" : r[1]) !== String(r[2] == null ? "" : r[2])); }).join("");
      $id("cmp-body").innerHTML = '<div class="sheet-head"><span class="sheet-title">' + T("compare") + "</span></div>" +
        '<table class="cmp-table"><thead><tr><th></th><td>' + esc(a.name || a.type) + "</td><td>" + esc(b.name || b.type) + "</td></tr></thead><tbody>" + rows + "</tbody></table>" +
        '<p class="muted small" style="margin-top:8px">' + T("compare_diff") + "</p>";
      if (typeof dlg.showModal === "function") { if (!dlg.open) dlg.showModal(); } else dlg.setAttribute("open", "");
    }
    if (dlg) dlg.addEventListener("click", function (e) { if (e.target === dlg) { try { dlg.close(); } catch (x) { dlg.removeAttribute("open"); } } });
    return { get on() { return on; }, has: has, pick: pick };
  })();

  // ------------------------------------------------ export / import / wipe
  (function () {
    var exp = $id("lib-export"), imp = $id("lib-import"), impFile = $id("lib-import-file");
    if (exp) exp.onclick = function () {
      api("/api/library/export").then(function (j) {
        if (!j.ok) { toast(T("err_generic"), "err"); return; }
        try {
          var blob = new Blob([JSON.stringify(j, null, 2)], { type: "application/json" });
          var url = URL.createObjectURL(blob), a = document.createElement("a");
          a.href = url; a.download = "proxlafy-biblioteca-" + new Date().toISOString().slice(0, 10) + ".json";
          document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
          toast(T("exported_ok") + " (" + (j.count || 0) + ")", "ok");
        } catch (e) { toast(T("err_generic"), "err"); }
      });
    };
    if (imp) imp.onclick = function () { impFile.click(); };
    if (impFile) impFile.onchange = function (e) {
      var f = e.target.files && e.target.files[0]; if (!f) return;
      var r = new FileReader();
      r.onload = function () {
        var cards;
        try { var data = JSON.parse(r.result); cards = Array.isArray(data) ? data : data.cards; } catch (x) { toast(T("import_bad"), "err"); return; }
        if (!Array.isArray(cards)) { toast(T("import_bad"), "err"); return; }
        api("/api/library/import", { method: "POST", body: { cards: cards } }).then(function (j) {
          if (j.ok) { toast(T("imported_ok") + ": " + j.imported, "ok"); refreshCards(); }
          else toast(j.error || T("err_generic"), "err");
        });
      };
      r.readAsText(f); e.target.value = "";
    };
  })();
  function loadWipe() {
    var box = $id("wipe-btns"); if (!box || box.dataset.loaded) return;
    api("/api/wipe").then(function (j) {
      var kinds = (j && j.kinds) || [];
      box.dataset.loaded = "1";
      box.innerHTML = kinds.map(function (k) { return '<button class="btn" data-wipe="' + esc(k.kind) + '">🧹 ' + esc(k.label) + "</button>"; }).join("");
      box.querySelectorAll("[data-wipe]").forEach(function (b) {
        b.onclick = function () {
          if (!confirm(T("wipe_confirm"))) return;
          runBtn(b, T("wiping"), api("/api/wipe", { method: "POST", body: { kind: b.getAttribute("data-wipe") } })).then(function (r) {
            toast(r.ok ? T("wipe_ok") : ((r.result && (r.result.output || "").slice(-120)) || r.error || T("err_generic")), r.ok ? "ok" : "err");
          });
        };
      });
    });
  }

  // ------------------------------------------------ bottom sheet
  var sheet = $id("sheet");
  function openSheet(card) {
    var body = $id("sheet-body");
    body.innerHTML =
      '<div class="sheet-head"><span class="badge ' + card.band + '">' + card.band.toUpperCase() + "</span>" +
        '<span class="sheet-title">' + esc(card.name || card.type) + "</span></div>" +
      '<div class="tag-sub" style="margin:2px 0 6px">' + esc(card.type + " · " + (card.label || "")) + "</div>" +
      '<div class="caps">' + capsHTML(card) + "</div>" + dataHTML(card) + wiegandHTML(card) + noteHTML(card) +
      feasHTML(card) + actionsHTML(card, "sheet") + modulesHTML(card);
    wireActions(body, card, "sheet");
    if (typeof sheet.showModal === "function") { if (!sheet.open) sheet.showModal(); } else { sheet.setAttribute("open", ""); }
  }
  function closeSheet() { if (sheet.open) { try { sheet.close(); } catch (e) { sheet.removeAttribute("open"); } } }
  sheet.addEventListener("click", function (e) { if (e.target === sheet) closeSheet(); });

  // ------------------------------------------------ help glossary
  var HELP = [
    { es: "Leer vs Emitir", en: "Read vs Emit", de: "<b>Leer</b> es escuchar una tarjeta y copiar sus datos al panel. <b>Emitir</b> (emular) es que el Proxmark se haga pasar por esa tarjeta ante un lector. Leer es de entrada; emitir es de salida.",
      den: "<b>Read</b> listens to a card and copies its data into the panel. <b>Emit</b> (emulate) makes the Proxmark pretend to be that card to a reader. Read is input; emit is output." },
    { es: "Volcar (dump)", en: "Dump", badge: "key", de: "Copiar <b>toda la memoria</b> de la tarjeta (todos los sectores con sus datos), no solo su número. Es la «fotocopia completa»: lo que luego se emula o se escribe en un clon. Sin el volcado, un clon solo tendría el UID y muchos lectores lo rechazarían.",
      den: "Copy <b>all the card's memory</b> (every sector with its data), not just its number. It's the full photocopy: what you then emulate or write to a clone. Without it a clone has only the UID, and many readers reject that." },
    { es: "Recuperar claves", en: "Recover keys", badge: "key", de: "Las tarjetas cifradas (MIFARE, iCLASS) cierran sus datos con <b>claves</b>, como un candado. Hay que encontrarlas (el Proxmark lo hace con <code>autopwn</code>) antes de poder volcar y clonar. Sin las claves, no se pueden leer los datos.",
      den: "Encrypted cards (MIFARE, iCLASS) lock their data behind <b>keys</b>, like a padlock. You must find them (the Proxmark does it with <code>autopwn</code>) before you can dump and clone. Without the keys the data can't be read." },
    { es: "Emular", en: "Emulate", de: "El Proxmark <b>se comporta como la tarjeta</b> por radio, sin tocar ningún plástico. Útil para probar un lector al momento. Se detiene desde el panel.",
      den: "The Proxmark <b>acts as the card</b> over radio, with no physical card involved. Good for testing a reader on the spot. Stop it from the panel." },
    { es: "Clonar (escribir)", en: "Clone (write)", de: "Copiar los datos de la tarjeta a <b>otra tarjeta física en blanco</b> (una T5577 para LF, una «magic» para HF). El resultado es una tarjeta real que puedes llevar.",
      den: "Copy the card's data onto <b>another blank physical card</b> (a T5577 for LF, a magic card for HF). The result is a real card you can carry." },
    { es: "Blanco / Candidata", en: "Blank / Candidate", de: "Un <b>blanco</b> es una tarjeta regrabable y vacía (T5577, EM4305, «magic»). En Escanear, una tarjeta así se marca como <b>candidata</b>: sirve para recibir un clon. El panel te dice qué credenciales acepta.",
      den: "A <b>blank</b> is an empty, rewritable card (T5577, EM4305, magic). In Scan, such a card is marked a <b>candidate</b>: it can receive a clone. The panel tells you which credentials it accepts." },
    { es: "Módulos", en: "Modules", de: "Los <b>pasos ordenados</b> del trabajo con una tarjeta: Identificar → Volcar → Recuperar claves → Emular/Clonar → Verificar. En tarjetas simples casi todos salen ya hechos (✓); en las cifradas verás los que faltan.",
      den: "The <b>ordered steps</b> for a card: Identify → Dump → Recover keys → Emulate/Clone → Verify. On simple cards most are already done (✓); on encrypted ones you'll see the ones still pending." },
    { es: "Viabilidad", en: "Feasibility", de: "La <b>probabilidad de que funcione</b> contra un lector real, por separado para emular y clonar, con sus requisitos y riesgos. No es una garantía: es una estimación honesta.",
      den: "The <b>chance it will work</b> against a real reader, separately for emulate and clone, with requirements and risks. Not a guarantee — an honest estimate." },
    { es: "LF vs HF", en: "LF vs HF", de: "<b>LF (125 kHz)</b>: tarjetas simples de proximidad (HID Prox, EM410x) — se leen y emiten fácil. <b>HF (13.56 MHz)</b>: tarjetas con chip y, a veces, cifrado (MIFARE, iCLASS). Son radios distintas: una HID Prox no se clona en una MIFARE.",
      den: "<b>LF (125 kHz)</b>: simple proximity cards (HID Prox, EM410x) — easy to read and emit. <b>HF (13.56 MHz)</b>: chip cards, sometimes encrypted (MIFARE, iCLASS). Different radios: an HID Prox can't be cloned onto a MIFARE." },
    { es: "Standalone", en: "Standalone", de: "Programar el Proxmark para funcionar <b>solo, sin la Pi ni el panel</b> — con cualquier fuente de energía y su botón. Se graba un «modo» en su firmware (p. ej. LF_SAMYRUN: leer y reemitir una HID con el botón).",
      den: "Program the Proxmark to run <b>on its own, no Pi or panel</b> — from any power source and its button. You flash a 'mode' into its firmware (e.g. LF_SAMYRUN: read and replay an HID with the button)." },
  ];
  var help = $id("help");
  function openHelp() {
    $id("help-list").innerHTML = HELP.map(function (h) {
      var badge = h.badge ? ' <span class="ht-badge ' + h.badge + '">' + (lang === "es" ? "clave" : "key") + "</span>" : "";
      return '<div class="help-term"><h4>' + esc(lang === "es" ? h.es : h.en) + badge + "</h4><p>" + (lang === "es" ? h.de : h.den) + "</p></div>";
    }).join("");
    if (typeof help.showModal === "function") { if (!help.open) help.showModal(); } else help.setAttribute("open", "");
  }
  $id("help-btn").onclick = openHelp;
  help.addEventListener("click", function (e) { if (e.target === help) { try { help.close(); } catch (x) { help.removeAttribute("open"); } } });

  // ------------------------------------------------ secret lab switch (Proxlafy ⇄ SDR-Kit)
  var labsheet = $id("labsheet");
  function canSwitch() { return state.role === "admin" || state.authOpen; }
  function openLabSheet() {
    var body = $id("labsheet-body");
    body.innerHTML = '<div class="sheet-head"><span class="sheet-title">' + esc(T("switch_title")) + "</span></div>" +
      '<p class="muted small">' + esc(T("switch_loading")) + "</p>";
    if (typeof labsheet.showModal === "function") { if (!labsheet.open) labsheet.showModal(); } else labsheet.setAttribute("open", "");
    api("/api/switch").then(function (j) { renderLabSheet((j && j.switch) || { enabled: false }); })
      .catch(function () { renderLabSheet({ enabled: false }); });
  }
  function renderLabSheet(s) {
    var body = $id("labsheet-body");
    var h = '<div class="sheet-head"><span class="sheet-title">' + esc(T("switch_title")) + "</span></div>";
    if (!s.enabled) { body.innerHTML = h + '<p class="muted">' + esc(T("switch_na")) + "</p>"; return; }
    var other = esc(s.other_label || "SDR-Kit");
    var curLabel = esc(s.current_label || "Proxlafy");
    h += '<p class="muted small">' + esc(T("switch_active")) + ": <b>" + curLabel + "</b></p>";
    if (s.other_installed) {
      h += "<p>" + T("switch_to").replace("%s", "<b>" + other + "</b>") + "</p>";
      h += '<div class="warn-box">' + T("switch_warn").replace("%ssid", "<b>" + esc(s.other_ssid || "") + "</b>")
             .replace("%ip", "<b>http://" + esc(s.other_ip || "192.168.4.1") + "</b>") + "</div>";
      h += '<button class="btn btn-primary btn-big" id="lab-go">' + T("switch_btn").replace("%s", other) + "</button>";
    } else {
      h += '<p class="muted">' + T("switch_notinst").replace("%s", "<b>" + other + "</b>") + "</p>";
      h += '<div class="warn-box">' + esc(T("switch_neednet")) + "</div>";
      h += '<button class="btn btn-primary btn-big" id="lab-install">' + T("switch_installbtn").replace("%s", other) + "</button>";
    }
    h += '<button class="btn btn-ghost btn-big" id="lab-cancel" style="margin-top:8px">' + esc(T("cancel")) + "</button>";
    body.innerHTML = h;
    var go = $id("lab-go"), inst = $id("lab-install"), cancel = $id("lab-cancel");
    if (go) go.onclick = function () { doSwitch(false, s); };
    if (inst) inst.onclick = function () { doSwitch(true, s); };
    if (cancel) cancel.onclick = closeLab;
  }
  function closeLab() { if (labsheet.open) { try { labsheet.close(); } catch (e) { labsheet.removeAttribute("open"); } } }
  labsheet.addEventListener("click", function (e) { if (e.target === labsheet) closeLab(); });
  function doSwitch(install, s) {
    closeLab();
    var other = esc(s.other_label || "SDR-Kit"), ssid = s.other_ssid || "", ip = s.other_ip || "192.168.4.1";
    var ov = $id("switching");
    $id("switching-msg").innerHTML = install
      ? T("switch_installing").replace("%s", other)
      : T("switch_reconnect").replace("%ssid", "<b>" + esc(ssid) + "</b>").replace("%ip", "<b>http://" + esc(ip) + "</b>");
    ov.hidden = false;
    api("/api/switch", { method: "POST", body: { target: "other", install: !!install } }).then(function (j) {
      if (!j.ok) { ov.hidden = true; toast(j.error || T("err_generic"), "err"); }
    }).catch(function () { /* expected: our own panel goes down as the other starts */ });
  }
  (function () {
    var brand = $(".brand"); if (!brand) return;
    brand.style.webkitUserSelect = "none"; brand.style.userSelect = "none";
    var timer = null, taps = 0, tapT = null;
    function arm() { timer = setTimeout(function () { timer = null; if (canSwitch()) openLabSheet(); }, 1000); }
    function disarm() { if (timer) { clearTimeout(timer); timer = null; } }
    brand.addEventListener("pointerdown", arm);
    ["pointerup", "pointerleave", "pointercancel"].forEach(function (ev) { brand.addEventListener(ev, disarm); });
    brand.addEventListener("click", function () {
      taps++; clearTimeout(tapT); tapT = setTimeout(function () { taps = 0; }, 600);
      if (taps >= 3) { taps = 0; if (canSwitch()) openLabSheet(); }
    });
  })();

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

  // ------------------------------------------------ EMIT hub
  var STD_FOR = { hid_prox: "LF_SAMYRUN", em410x: "LF_EM4100RWC", mifare_classic: "HF_MFCSIM", mifare_ultralight: "HF_AVEFUL", iclass: "HF_ICECLASS", iso15693: "HF_TMUDFORD" };
  document.querySelectorAll("#emit-dur-seg .seg-btn").forEach(function (b) {
    b.onclick = function () { document.querySelectorAll("#emit-dur-seg .seg-btn").forEach(function (x) { x.classList.remove("active"); }); b.classList.add("active"); state.emitSec = +b.getAttribute("data-sec"); };
  });
  function emitCard(c) {
    api("/api/emulate", { method: "POST", body: { id: c.id, seconds: state.emitSec || 0 } }).then(function (j) {
      if (j.ok) { toast(T("emulate_started") + ": " + (c.name || c.label), "ok"); refreshStatus().then(renderEmit); }
      else toast(j.error || T("err_generic"), "err");
    });
  }
  function emitTag(c) {
    var b = document.createElement("button"); b.className = "tag"; b.setAttribute("data-id", c.id);
    if (state.sim && state.sim.id === c.id) b.classList.add("simming");
    b.innerHTML = '<span class="badge ' + c.band + '">' + c.band.toUpperCase() + '</span><span class="tag-title"><span class="tag-name">' + esc(c.name || c.type) + '</span><span class="tag-sub">' + esc(c.type + " · " + (c.label || "")) + '</span></span><span class="tag-flags">▶</span>';
    b.onclick = function () { emitCard(c); };
    return b;
  }
  function renderEmitStd(active) {
    var box = $id("emit-standalone");
    var full = state.cards.filter(function (x) { return x.id === active.id; })[0] || active;
    var sf = full.standalone_for;
    var mode = (sf && sf.mode) || STD_FOR[active.key];
    if (!mode) { box.hidden = true; return; }
    var note = sf ? (lang === "es" ? sf.note_es : sf.note_en) :
      (lang === "es" ? ("Graba " + mode + " para que el Proxmark siga emitiendo esto con su propia energía, sin la Pi.")
                     : ("Flash " + mode + " so the Proxmark keeps emitting this on its own power, with no Pi."));
    box.hidden = false;
    box.innerHTML = "<h4>⚡ " + T("std_fallback_title") + "</h4><p>" + esc(note) + "</p>" +
      '<button class="btn" id="emit-std-prep">' + T("std_prepare") + ' <span class="mode-chip">' + esc(mode) + "</span></button>";
    $id("emit-std-prep").onclick = function () {
      if (!confirm(T("std_confirm"))) return;
      api("/api/standalone/flash", { method: "POST", body: { mode: mode } }).then(function (r) { if (r.ok) toast(T("std_flashing"), "ok"); });
    };
  }
  function renderEmit() {
    var hero = $id("emit-active"), live = state.sim, pend = state.pending, c = live || pend;
    if (c) {
      hero.className = "card emit-hero " + (live ? "live" : "pending");
      hero.innerHTML = '<div class="eh-kicker">' + (live ? T("emulating") : T("resuming")) + "</div>" +
        '<div class="eh-name">' + esc(c.name || c.label || c.type) + "</div>" +
        '<div class="eh-sub">' + esc((c.type || "") + (c.label ? " · " + c.label : "")) + "</div>" +
        (live ? '<div class="eh-wave"><i></i><i></i><i></i><i></i><i></i></div>' : "") +
        '<button class="btn btn-stop" id="emit-stop">' + T("stop") + "</button>";
      $id("emit-stop").onclick = function () { api("/api/emulate/stop", { method: "POST" }).then(function () { state.sim = null; state.pending = null; refreshStatus().then(renderEmit); toast(T("emulate_stopped")); }); };
      renderEmitStd(c);
    } else {
      hero.className = "card emit-hero";
      hero.innerHTML = '<div class="eh-empty"><span class="big">📡</span>' + esc(T("emit_none")) + '<br><span class="small">' + esc(T("emit_pick")) + "</span></div>";
      $id("emit-standalone").hidden = true;
    }
    var wrap = $id("emit-quick"); wrap.querySelectorAll(".tag").forEach(function (n) { n.remove(); });
    var emulables = state.cards.filter(function (x) { return (x.caps || {}).emulable; });
    $id("emit-empty").style.display = emulables.length ? "none" : "";
    var frag = document.createDocumentFragment();
    emulables.forEach(function (x) { frag.appendChild(emitTag(x)); });
    wrap.appendChild(frag);
  }

  // ------------------------------------------------ history
  // ------------------------------------------------ scan session (end-of-day review)
  var SESSION = (function () {
    var KEY = "proxlafy_session", list = [];
    try { list = JSON.parse(localStorage.getItem(KEY) || "[]") || []; } catch (e) { list = []; }
    function persist() { try { localStorage.setItem(KEY, JSON.stringify(list.slice(0, 300))); } catch (e) {} }
    function sig(c) { return (c.key || c.type || "") + "|" + (c.label || "") + "|" + ((c.data || {}).uid || (c.data || {}).id || ""); }
    function add(card) {
      if (!card) return;
      var s = sig(card), i = list.findIndex(function (x) { return x._sig === s; });
      if (i >= 0) { var ex = list.splice(i, 1)[0]; card._sid = ex._sid; card.saved = ex.saved; }   // move dup to top
      card = JSON.parse(JSON.stringify(card));
      card._sig = s; card._sid = card._sid || ("s" + Date.now().toString(36) + Math.random().toString(36).slice(2, 6));
      card._t = card._t || Date.now();
      list.unshift(card); persist(); render(true);
    }
    function update(card) { var i = list.findIndex(function (x) { return x._sid === card._sid || x._sig === sig(card); }); if (i >= 0) { card._sig = list[i]._sig; card._sid = list[i]._sid; card._t = list[i]._t; card.saved = list[i].saved; list[i] = JSON.parse(JSON.stringify(card)); persist(); render(); } }
    function remove(sid) { list = list.filter(function (x) { return x._sid !== sid; }); persist(); render(); }
    function clear() { list = []; persist(); render(); }
    function get(sid) { return list.filter(function (x) { return x._sid === sid; })[0]; }
    function render(bump) {
      var box = $id("session-list"), wrap = $id("scan-session"), cnt = $id("session-count");
      if (!box) return;
      wrap.hidden = !list.length;
      if (cnt) { cnt.textContent = list.length; if (bump && !reduce) { cnt.classList.remove("bump"); void cnt.offsetWidth; cnt.classList.add("bump"); } }
      box.innerHTML = list.map(function (c) {
        var saved = c.saved ? '<span class="sv-badge" title="guardada">✓</span>' : "";
        return '<div class="session-row' + (reduce ? "" : " fresh") + '" data-sid="' + c._sid + '">' +
          '<span class="badge ' + c.band + '">' + c.band.toUpperCase() + "</span>" +
          '<button class="sr-main" data-s="view"><span class="sr-name">' + esc(c.name || c.type) + saved + "</span>" +
          '<span class="sr-sub">' + esc((c.label || "") + " · " + new Date(c._t).toLocaleTimeString()) + "</span></button>" +
          '<span class="sr-acts">' +
            (c.saved ? "" : '<button class="chip chip-icon" data-s="save" title="' + esc(T("save")) + '">💾</button>') +
            ((c.caps || {}).decode && !c.decoded ? '<button class="chip chip-icon" data-s="decode" title="' + esc(T("decode")) + '">🔑</button>' : "") +
            '<button class="chip chip-icon" data-s="del" title="' + esc(T("del")) + '">🗑</button>' +
          "</span></div>";
      }).join("");
      box.querySelectorAll(".session-row").forEach(function (row) {
        var sid = row.getAttribute("data-sid");
        row.querySelectorAll("[data-s]").forEach(function (b) {
          b.onclick = function (e) { e.stopPropagation(); act(b.getAttribute("data-s"), sid, b); };
        });
      });
    }
    function act(a, sid, btn) {
      var c = get(sid); if (!c) return;
      if (a === "view") { renderScan(c); $id("scan-result").scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" }); }
      else if (a === "del") { remove(sid); }
      else if (a === "save") {
        runBtn(btn, "…", api("/api/cards", { method: "POST", body: { name: c.name || (c.type + " · " + (c.label || "")), card: c } })).then(function (j) {
          if (j.ok) { c.saved = true; persist(); render(); toast(T("save") + " ✓", "ok"); refreshCards(); } else toast(j.error || T("err_generic"), "err");
        });
      } else if (a === "decode") {
        runBtn(btn, "…", api("/api/decode", { method: "POST", body: { card: c } })).then(function (j) {
          if (j.ok && j.card) { update(j.card); toast(T("decode") + " ✓", "ok"); } else toast((j.result && j.result.error) || j.error || T("err_generic"), "err");
        });
      }
    }
    function saveAll() {
      var pend = list.filter(function (c) { return !c.saved; });
      if (!pend.length) { toast(T("session_none"), ""); return; }
      var n = 0;
      (function next(i) {
        if (i >= pend.length) { render(); toast(T("saved_n").replace("%n", n), "ok"); refreshCards(); return; }
        api("/api/cards", { method: "POST", body: { name: pend[i].name || (pend[i].type + " · " + (pend[i].label || "")), card: pend[i] } })
          .then(function (j) { if (j.ok) { pend[i].saved = true; n++; } persist(); next(i + 1); }).catch(function () { next(i + 1); });
      })(0);
    }
    function exportJson() {
      try {
        var blob = new Blob([JSON.stringify({ app: "proxlafy", kind: "scan-session", exported: Date.now() / 1000, count: list.length, cards: list }, null, 2)], { type: "application/json" });
        var url = URL.createObjectURL(blob), a = document.createElement("a");
        a.href = url; a.download = "proxlafy-sesion-" + new Date().toISOString().slice(0, 10) + ".json";
        document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
        toast(T("exported_ok") + " (" + list.length + ")", "ok");
      } catch (e) { toast(T("err_generic"), "err"); }
    }
    if ($id("session-saveall")) $id("session-saveall").onclick = saveAll;
    if ($id("session-export")) $id("session-export").onclick = exportJson;
    if ($id("session-clear")) $id("session-clear").onclick = function () { if (confirm(T("clear_confirm"))) clear(); };
    return { add: add, update: update, render: render };
  })();

  // ------------------------------------------------ device status
  function loadDevice() {
    return api("/api/device").then(function (j) {
      if (!j.ok) return; var d = j.device || {};
      var fmt = function (v, ok) { return v != null ? v.toFixed(1) + " V " + (ok ? "✓" : "⚠") : "–"; };
      var le = $id("sys-antlf"), he = $id("sys-anthf");
      if (le) le.textContent = fmt(d.lf_v, d.lf_ok);
      if (he) he.textContent = fmt(d.hf_v, d.hf_ok);
    }).catch(function () {});
  }

  // ------------------------------------------------ continuous scan
  var scanTimer = null;
  $id("scan-continuous").onchange = function () {
    if (this.checked) { scanTimer = setInterval(function () { if (state.view === "scan" && !state.sim && !$id("scan-btn").disabled) $id("scan-btn").click(); }, 1700); }
    else { clearInterval(scanTimer); scanTimer = null; }
  };

  function renderAll() { renderRead(state.lastRead); if (state.lastScan) renderScan(state.lastScan); renderLibrary(); if (state.standalone) renderStandalone(); if (state.view === "emit") renderEmit(); }

  // ------------------------------------------------ boot
  function boot() { refreshStatus().then(refreshCards).then(refreshLog); }
  applyI18n(); boot();
  setInterval(refreshStatus, 2500);
  setInterval(refreshLog, 1500);

  // ------------------------------------------------ self-update from the panel
  (function () {
    var checkBtn = $id("btn-update-check"), applyBtn = $id("btn-update-apply");
    if (!checkBtn) return;
    var statusEl = $id("update-status"), logEl = $id("update-log");
    checkBtn.onclick = function () {
      statusEl.textContent = T("update_checking"); checkBtn.disabled = true; applyBtn.hidden = true;
      api("/api/update").then(function (j) {
        checkBtn.disabled = false;
        var u = (j && j.update) || {};
        if (u.demo) { statusEl.textContent = T("update_demo"); return; }
        if (u.ok === false) { statusEl.textContent = T("err_generic") + " " + (u.error || ""); return; }
        if (!u.behind) { statusEl.textContent = T("update_uptodate") + " (" + esc(u.current || state.version) + ")"; return; }
        var changes = (u.changes || []).slice(0, 8).map(function (c) { return "• " + esc(c); }).join("<br>");
        statusEl.innerHTML = T("update_available").replace("%from", esc(u.current || "")).replace("%to", esc(u.latest || "?")).replace("%n", u.behind) +
          (changes ? '<div class="muted small" style="margin-top:6px">' + changes + "</div>" : "");
        applyBtn.hidden = false;
      }).catch(function () { checkBtn.disabled = false; statusEl.textContent = T("err_generic"); });
    };
    applyBtn.onclick = function () {
      applyBtn.disabled = true; checkBtn.disabled = true;
      statusEl.textContent = T("update_running"); logEl.hidden = false; logEl.textContent = "";
      api("/api/update", { method: "POST", body: {} }).then(function (j) {
        if (j && j.ok === false) { statusEl.textContent = j.error || T("err_generic"); applyBtn.disabled = false; checkBtn.disabled = false; return; }
        pollUpdate();
      }).catch(pollUpdate);
    };
    function pollUpdate() {
      var wentDown = false, tries = 0;
      var iv = setInterval(function () {
        tries++;
        if (tries > 100) { clearInterval(iv); statusEl.textContent = T("update_timeout"); return; }
        fetch("/api/update/log", { cache: "no-store" }).then(function (r) { return r.json(); })
          .then(function (j) { if (j && j.log) { logEl.textContent = j.log; logEl.scrollTop = logEl.scrollHeight; } }).catch(function () {});
        fetch("/api/status", { cache: "no-store" }).then(function (r) { return r.ok; })
          .then(function (ok) {
            if (!ok) { wentDown = true; return; }
            if (wentDown) { clearInterval(iv); statusEl.textContent = T("update_done"); setTimeout(function () { location.reload(); }, 2500); }
          }).catch(function () { wentDown = true; });
      }, 3000);
    }
  })();
})();
