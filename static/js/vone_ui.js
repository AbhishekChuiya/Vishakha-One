/* Vishakha One employee portal: theme, sidebar, menus, live search, notifications, favourites, tabs. */
(function () {
  "use strict";
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var store = {
    get: function (k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set: function (k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
  };
  var root = document.documentElement;
  function csrf() { var m = document.cookie.match(/(?:^|; )(?:[a-z_]*csrftoken)=([^;]+)/i); return m ? decodeURIComponent(m[1]) : ""; }
  function toast(text) {
    var t = document.createElement("div"); t.className = "toast"; t.setAttribute("role", "status"); t.textContent = text;
    document.body.appendChild(t); setTimeout(function () { t.remove(); }, 2600);
  }
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]; }); }

  // ---- theme (same storage key the portal always used) ----
  $$("[data-theme-toggle]").forEach(function (b) {
    b.addEventListener("click", function () {
      var dark = root.getAttribute("data-theme") !== "dark";
      root.setAttribute("data-theme", dark ? "dark" : "light"); store.set("vishakha_one_theme", dark ? "dark" : "light");
    });
  });

  // ---- sidebar: mobile drawer + desktop collapse ----
  $$("[data-nav-toggle]").forEach(function (b) { b.addEventListener("click", function () { root.classList.toggle("nav-open"); }); });
  var scrim = $(".vx-scrim"); if (scrim) scrim.addEventListener("click", function () { root.classList.remove("nav-open"); });
  var collapse = $("[data-side-collapse]");
  if (collapse) collapse.addEventListener("click", function () {
    var mini = root.getAttribute("data-side") === "mini"; if (mini) root.removeAttribute("data-side"); else root.setAttribute("data-side", "mini");
    store.set("vone_side", mini ? "full" : "mini");
  });

  // ---- pop-up menus (profile, notifications) ----
  function closePops(except) { $$("[data-pop]").forEach(function (p) { if (p !== except) p.hidden = true; }); $$("[data-pop-toggle]").forEach(function (b) { b.setAttribute("aria-expanded", "false"); }); }
  $$("[data-pop-toggle]").forEach(function (btn) {
    btn.addEventListener("click", function (e) {
      e.stopPropagation(); var pop = document.getElementById(btn.getAttribute("data-pop-toggle")); if (!pop) return;
      var open = pop.hidden; closePops(pop); pop.hidden = !open; btn.setAttribute("aria-expanded", open ? "true" : "false");
      if (open && pop.id === "vx-bell") loadBell();
    });
  });
  document.addEventListener("click", function (e) { if (!e.target.closest("[data-pop]") ) closePops(); });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape") { closePops(); hideSuggest(); var ai = $("#vx-ai"); if (ai) ai.hidden = true; root.classList.remove("nav-open"); } });

  // ---- notifications bell ----
  function loadBell() {
    var list = $("#vx-bell-list"); if (!list) return;
    fetch("/notifications/feed/", {credentials: "same-origin", headers: {"X-Requested-With": "XMLHttpRequest"}})
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (!d.items || !d.items.length) { list.innerHTML = '<div class="empty">You are all caught up. No unread notices.</div>'; return; }
        list.innerHTML = d.items.map(function (n) {
          return '<a class="bi" href="/notifications/"><b>' + esc(n.title) + '</b><small>' + esc(n.event_at || n.published_at) + (n.location ? ' &middot; ' + esc(n.location) : '') + '</small></a>';
        }).join("");
      }).catch(function () { list.innerHTML = '<div class="empty">Could not load notifications.</div>'; });
  }

  // ---- search with live suggestions ----
  var q = $("#vx-q"), box = $("#vx-suggest"), timer = null, items = [], cursor = -1;
  function hideSuggest() { if (box) { box.hidden = true; items = []; cursor = -1; } }
  function render(data, term) {
    var html = "";
    (data.groups || []).forEach(function (g) {
      html += "<h6>" + esc(g.title) + "</h6>";
      g.items.forEach(function (it) {
        html += '<a href="' + esc(it.url) + '"><span class="ico"><svg class="vi sm" viewBox="0 0 24 24" aria-hidden="true">' + (it.icon || "") + '</svg></span><span><b>' + esc(it.title) + '</b><small>' + esc(it.sub || "") + "</small></span></a>";
      });
    });
    if (!html) html = '<div class="none">No quick matches for &ldquo;' + esc(term) + "&rdquo;. Press Enter to search everything.</div>";
    else html += '<a class="all" href="/search/?q=' + encodeURIComponent(term) + '">See all results for &ldquo;' + esc(term) + "&rdquo;</a>";
    box.innerHTML = html; box.hidden = false; items = $$("a", box); cursor = -1;
  }
  if (q && box) {
    q.addEventListener("input", function () {
      clearTimeout(timer); var term = q.value.trim(); if (term.length < 2) { hideSuggest(); return; }
      timer = setTimeout(function () {
        fetch("/search/suggest/?q=" + encodeURIComponent(term), {credentials: "same-origin"}).then(function (r) { return r.json(); })
          .then(function (d) { if (q.value.trim() === term) render(d, term); }).catch(hideSuggest);
      }, 140);
    });
    q.addEventListener("keydown", function (e) {
      if (!items.length) return;
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault(); cursor = (cursor + (e.key === "ArrowDown" ? 1 : -1) + items.length) % items.length;
        items.forEach(function (a, i) { a.classList.toggle("on", i === cursor); });
      } else if (e.key === "Enter" && cursor >= 0) { e.preventDefault(); window.location = items[cursor].href; }
    });
    document.addEventListener("click", function (e) { if (!e.target.closest(".vx-search")) hideSuggest(); });
    document.addEventListener("keydown", function (e) {
      var typing = /^(INPUT|TEXTAREA|SELECT)$/.test((document.activeElement || {}).tagName) || (document.activeElement || {}).isContentEditable;
      if (((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") || (e.key === "/" && !typing)) { e.preventDefault(); q.focus(); q.select(); }
    });
  }

  // ---- favourite applications + filter ----
  var FAV = "vone_fav_apps", favs = [];
  try { favs = JSON.parse(store.get(FAV) || "[]"); } catch (e) { favs = []; }
  function paintFavs() { $$("[data-fav]").forEach(function (b) { b.setAttribute("aria-pressed", favs.indexOf(b.getAttribute("data-fav")) > -1 ? "true" : "false"); }); }
  paintFavs();
  document.addEventListener("click", function (e) {
    var b = e.target.closest("[data-fav]"); if (!b) return;
    e.preventDefault(); e.stopPropagation();
    var name = b.getAttribute("data-fav"), i = favs.indexOf(name);
    if (i > -1) favs.splice(i, 1); else favs.push(name);
    store.set(FAV, JSON.stringify(favs)); paintFavs(); applyAppFilter();
    toast(i > -1 ? "Removed from favourites" : "Added to favourites");
  });
  function applyAppFilter() {
    var grid = $("#app-grid"); if (!grid) return;
    var term = (($("[data-app-filter]") || {}).value || "").trim().toLowerCase();
    var onlyFav = ($("[data-fav-filter]") || {}).getAttribute && $("[data-fav-filter]").getAttribute("aria-pressed") === "true";
    var shown = 0;
    $$(".tile", grid).forEach(function (t) {
      var hay = (t.getAttribute("data-name") || "") + " " + (t.getAttribute("data-category") || "");
      var ok = (!term || hay.indexOf(term) > -1) && (!onlyFav || favs.indexOf(t.querySelector("[data-fav]").getAttribute("data-fav")) > -1);
      t.hidden = !ok; if (ok) shown++;
    });
    var empty = $("#apps-empty"); if (empty) empty.hidden = shown > 0;
    var count = $("[data-app-count]"); if (count) count.textContent = shown + (shown === 1 ? " application" : " applications");
  }
  var af = $("[data-app-filter]"); if (af) af.addEventListener("input", applyAppFilter);
  var ff = $("[data-fav-filter]"); if (ff) ff.addEventListener("click", function () { ff.setAttribute("aria-pressed", ff.getAttribute("aria-pressed") === "true" ? "false" : "true"); applyAppFilter(); });
  // ---- phones: first 4 apps, "More apps" reveals the rest ----
  var moreBtn = $("[data-apps-more]");
  function setApps(open) {
    var g = $("#app-grid"); if (!g) return; g.classList.toggle("expanded", open);
    if (moreBtn) { moreBtn.setAttribute("aria-expanded", open ? "true" : "false"); moreBtn.textContent = open ? "Fewer apps" : "More apps (" + Math.max($$(".tile", g).length - 4, 0) + ")"; }
  }
  if (moreBtn) moreBtn.addEventListener("click", function () { var g = $("#app-grid"); setApps(!g.classList.contains("expanded")); });
  if (af) af.addEventListener("input", function () { if ((af.value || "").trim()) setApps(true); });
  // ---- carousels (Insider, Bank benefits, Videos) ----
  $$("[data-rail-prev],[data-rail-next]").forEach(function (b) {
    b.addEventListener("click", function () {
      var id = b.getAttribute("data-rail-prev") || b.getAttribute("data-rail-next"), r = document.getElementById(id); if (!r) return;
      r.scrollBy({ left: (b.hasAttribute("data-rail-prev") ? -1 : 1) * Math.max(r.clientWidth * 0.85, 240), behavior: "smooth" });
    });
  });
  applyAppFilter();

  // ---- tabs (resources on home, canteen days) ----
  $$("[data-tabs]").forEach(function (wrap) {
    var tabs = $$("[data-tab]", wrap), panels = $$("[data-panel]", wrap);
    function show(name) {
      tabs.forEach(function (t) { var on = t.getAttribute("data-tab") === name; t.classList.toggle("on", on); t.setAttribute("aria-selected", on ? "true" : "false"); t.setAttribute("aria-pressed", on ? "true" : "false"); });
      panels.forEach(function (p) { p.hidden = p.getAttribute("data-panel") !== name; });
    }
    tabs.forEach(function (t) { t.addEventListener("click", function () { show(t.getAttribute("data-tab")); }); });
    var today = wrap.querySelector("[data-tab][data-today]");
    var start = (today && today.getAttribute("data-tab")) || wrap.getAttribute("data-start") || (tabs[0] && tabs[0].getAttribute("data-tab")); if (start) show(start);
  });

  // ---- dismiss a company notice without leaving the page ----
  $$("form[data-dismiss]").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      fetch(form.action, {method: "POST", credentials: "same-origin", headers: {"X-Requested-With": "XMLHttpRequest", "X-CSRFToken": csrf()}, body: new FormData(form)})
        .then(function (r) { if (!r.ok) throw 0; var n = form.closest(".nrow,.notice"); var card = form.closest(".notice-card"); if (n) n.remove(); if (card && !card.querySelector(".nrow")) card.remove(); })
        .catch(function () { form.submit(); });
    });
  });

  // ---- photo lightbox ----
  $$("[data-full]").forEach(function (g) {
    g.addEventListener("click", function () {
      var box = document.createElement("div"); box.className = "lightbox"; box.setAttribute("role", "dialog"); box.setAttribute("aria-label", "Photo");
      box.innerHTML = '<button type="button" aria-label="Close">&times;</button><img alt="" src="' + esc(g.getAttribute("data-full")) + '">';
      box.addEventListener("click", function () { box.remove(); }); document.body.appendChild(box);
    });
  });

  // ---- assistant preview panel ----
  var fab = $("#vx-fab"), ai = $("#vx-ai");
  if (fab && ai) fab.addEventListener("click", function () { ai.hidden = !ai.hidden; });
  $$("[data-open-ai]").forEach(function (b) { b.addEventListener("click", function (e) { e.preventDefault(); if (ai) ai.hidden = false; }); });
  $$("[data-ai-close]").forEach(function (b) { b.addEventListener("click", function () { if (ai) ai.hidden = true; }); });
  // ---- quick find: jump-to-page list ----
  var qf = $("[data-qf-input]");
  if (qf) {
    var qItems = $$("[data-qf-item]"), qEmpty = $(".qf-empty");
    qf.addEventListener("input", function () {
      var t = qf.value.trim().toLowerCase(), n = 0;
      qItems.forEach(function (a) { var ok = !t || a.textContent.toLowerCase().indexOf(t) > -1; a.hidden = !ok; if (ok) n++; });
      if (qEmpty) qEmpty.hidden = n > 0;
    });
    qf.addEventListener("keydown", function (e) { if (e.key === "Enter") { var f = qItems.filter(function (a) { return !a.hidden; })[0]; if (f) window.location = f.href; } });
    var qBtn = $('[data-pop-toggle="vx-quick"]'); if (qBtn) qBtn.addEventListener("click", function () { setTimeout(function () { qf.focus(); }, 30); });
  }
  // ---- profile photo: choose a file and it uploads straight away ----
  $$("input[data-autosubmit]").forEach(function (f) { f.addEventListener("change", function () { if (f.files && f.files.length && f.form) f.form.submit(); }); });
  // ---- grid / list layout toggle (remembered per page type) ----
  $$(".viewtoggle").forEach(function (group) {
    var btns = $$("button[data-view]", group); if (!btns.length) return;
    var target = $(btns[0].getAttribute("data-view-target")), key = "vone_view_" + (btns[0].getAttribute("data-view-key") || "x");
    function apply(mode) {
      if (target) target.classList.toggle("list", mode === "list");
      btns.forEach(function (b) { b.setAttribute("aria-pressed", b.getAttribute("data-view") === mode ? "true" : "false"); });
    }
    apply(store.get(key) === "list" ? "list" : "grid");
    btns.forEach(function (b) { b.addEventListener("click", function () { var m = b.getAttribute("data-view"); apply(m); store.set(key, m); }); });
  });
  // ---- shorter search hints on phones so they never get cut off ----
  if (window.matchMedia && window.matchMedia("(max-width:600px)").matches) {
    $$('input[type="search"]').forEach(function (i) { if (i.id === "vx-q" || i.closest(".banner-form")) i.placeholder = "Search…"; });
  }
  // ---- bookmarks ----
  document.addEventListener("click", function (e) {
    var btn = e.target.closest("button[data-bookmark]"); if (!btn) return; e.preventDefault();
    fetch("/bookmarks/toggle/" + btn.getAttribute("data-bookmark") + "/", { method: "POST", credentials: "same-origin", headers: { "X-CSRFToken": csrf(), "X-Requested-With": "XMLHttpRequest" } })
      .then(function (r) { if (!r.ok) throw 0; return r.json(); })
      .then(function (d) {
        btn.setAttribute("aria-pressed", d.bookmarked ? "true" : "false"); toast(d.bookmarked ? "Bookmarked" : "Bookmark removed");
        var grid = document.getElementById("bm-grid");
        if (grid && !d.bookmarked) { var card = btn.closest(".mcard"); if (card) card.remove(); }
      }).catch(function () { toast("Could not update the bookmark. Please try again."); });
  });
  // ---- back to top ----
  var top = $("#vx-totop");
  if (top) {
    var onScroll = function () { top.hidden = (window.pageYOffset || document.documentElement.scrollTop) < 400; };
    window.addEventListener("scroll", onScroll, { passive: true }); onScroll();
    top.addEventListener("click", function () { window.scrollTo({ top: 0, behavior: "smooth" }); });
  }
  $$("[data-prompt]").forEach(function (b) { b.addEventListener("click", function () { toast("Vishakha AI is not connected yet. It is coming soon."); }); });
})();
