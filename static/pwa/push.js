/* Vishakha One - browser notifications. Asks politely, only after sign-in, and never repeats a refusal for a week. */
(function () {
  "use strict";
  if (!("serviceWorker" in navigator) || !("PushManager" in window) || !("Notification" in window)) { document.documentElement.setAttribute("data-push", "unsupported"); return; }
  var DISMISS = "vone_push_dismissed", DAY = 86400000;
  function csrf() { var m = document.cookie.match(/csrftoken=([^;]+)/); return m ? decodeURIComponent(m[1]) : ""; }
  function b64(s) { var p = "=".repeat((4 - s.length % 4) % 4), r = (s + p).replace(/-/g, "+").replace(/_/g, "/"), raw = atob(r), a = new Uint8Array(raw.length); for (var i = 0; i < raw.length; i++) a[i] = raw.charCodeAt(i); return a; }
  function post(url, body) { return fetch(url, { method: "POST", credentials: "same-origin", keepalive: true, headers: { "Content-Type": "application/json", "X-CSRFToken": csrf() }, body: JSON.stringify(body) }); }
  function getRegistration() { return navigator.serviceWorker.register("/service-worker.js", { scope: "/" }).then(function () { return navigator.serviceWorker.ready; }); }
  var cfg = null;
  function config() { if (cfg) return cfg; cfg = fetch("/push/key/", { credentials: "same-origin" }).then(function (r) { return r.json(); }).catch(function () { return { enabled: false }; }); return cfg; }

  function subscribe() {
    return config().then(function (c) {
      if (!c.enabled) throw new Error("disabled");
      return getRegistration().then(function (reg) {
        return reg.pushManager.getSubscription().then(function (existing) { return existing || reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: b64(c.publicKey) }); });
      });
    }).then(function (sub) { return post("/push/subscribe/", { subscription: sub.toJSON() }).then(function (r) { if (!r.ok) throw new Error("save"); return sub; }); });
  }
  function unsubscribe() {
    return getRegistration().then(function (reg) { return reg.pushManager.getSubscription(); }).then(function (sub) {
      if (!sub) return; var ep = sub.endpoint; return post("/push/unsubscribe/", { endpoint: ep }).then(function () { return sub.unsubscribe(); });
    });
  }
  function enable() {
    return Notification.requestPermission().then(function (p) { if (p !== "granted") throw new Error(p); return subscribe(); });
  }
  window.VonePush = { enable: enable, disable: unsubscribe, subscribe: subscribe };

  function toast(msg) { var t = document.createElement("div"); t.className = "toast"; t.textContent = msg; document.body.appendChild(t); setTimeout(function () { t.remove(); }, 3200); }

  // ---- the polite prompt ----
  function showPrompt() {
    var host = document.querySelector("main"); if (!host || document.querySelector(".push-prompt")) return;
    var box = document.createElement("div"); box.className = "push-prompt"; box.setAttribute("role", "region"); box.setAttribute("aria-label", "Notifications");
    box.innerHTML = '<span class="pp-ico" aria-hidden="true">&#128276;</span><div class="pp-text"><b>Get notified on this device</b><span>Allow notifications to hear about approvals, company notices and updates, even when this tab is closed.</span></div><div class="pp-acts"><button type="button" class="pp-yes">Turn on</button><button type="button" class="pp-no">Not now</button></div>';
    host.insertBefore(box, host.firstChild);
    box.querySelector(".pp-no").addEventListener("click", function () { try { localStorage.setItem(DISMISS, String(Date.now())); } catch (e) {} box.remove(); });
    box.querySelector(".pp-yes").addEventListener("click", function () {
      enable().then(function () { box.remove(); toast("Notifications are on."); refreshToggles(); })
        .catch(function (e) { box.remove(); if (String(e && e.message) === "denied") toast("Notifications are blocked in your browser settings."); refreshToggles(); });
    });
  }

  // ---- profile page toggle ----
  function refreshToggles() {
    document.querySelectorAll("[data-push-toggle]").forEach(function (btn) {
      var state = btn.parentNode.querySelector("[data-push-state]");
      config().then(function (c) {
        if (!c.enabled) { btn.hidden = true; if (state) state.textContent = "Notifications are not switched on for this site yet. Ask your administrator."; return; }
        if (Notification.permission === "denied") { btn.hidden = true; if (state) state.textContent = "Blocked in your browser settings. Allow notifications for this site in the address-bar lock menu, then reload."; return; }
        getRegistration().then(function (reg) { return reg.pushManager.getSubscription(); }).then(function (sub) {
          var on = !!sub && Notification.permission === "granted";
          btn.hidden = false; btn.textContent = on ? "Turn off notifications" : "Turn on notifications"; btn.setAttribute("data-on", on ? "1" : "0");
          if (state) state.textContent = on ? "Notifications are on for this device." : "Notifications are off for this device.";
        });
      });
    });
  }
  document.addEventListener("click", function (e) {
    var btn = e.target.closest("[data-push-toggle]"); if (!btn) return;
    var on = btn.getAttribute("data-on") === "1";
    (on ? unsubscribe() : enable()).then(function () { toast(on ? "Notifications turned off." : "Notifications are on."); refreshToggles(); })
      .catch(function () { toast("Could not change notifications. Check your browser settings."); refreshToggles(); });
  });

  // ---- sign-out: stop this browser receiving the previous person's notifications ----
  document.addEventListener("submit", function (e) {
    var f = e.target; if (!f || !f.action || f.action.indexOf("/logout/") < 0) return;
    try { navigator.serviceWorker.ready.then(function (reg) { return reg.pushManager.getSubscription(); }).then(function (sub) { if (sub) post("/push/unsubscribe/", { endpoint: sub.endpoint }); }); } catch (err) {}
  }, true);

  function start() {
    config().then(function (c) {
      refreshToggles();
      if (!c.enabled) return;
      if (Notification.permission === "granted") { subscribe().catch(function () {}); return; }          // keep the server copy fresh
      if (Notification.permission !== "default") return;
      var last = 0; try { last = parseInt(localStorage.getItem(DISMISS) || "0", 10); } catch (e) {}
      if (Date.now() - last > 7 * DAY) setTimeout(showPrompt, 2500);
    });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start); else start();
})();
