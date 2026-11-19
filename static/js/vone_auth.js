/* Vishakha One sign-in pages: show/hide password, password strength, "working..." state on submit. */
(function () {
  "use strict";
  document.querySelectorAll("[data-toggle-password]").forEach(function (button) {
    button.addEventListener("click", function () {
      var input = document.getElementById(button.getAttribute("data-toggle-password"));
      if (!input) return;
      var show = input.type === "password";
      input.type = show ? "text" : "password";
      button.classList.toggle("on", show);
      button.setAttribute("aria-label", show ? "Hide password" : "Show password");
    });
  });

  function score(value) {
    if (!value) return 0;
    var s = 0;
    if (value.length >= 8) s++;
    if (value.length >= 12) s++;
    if (/[a-z]/.test(value) && /[A-Z]/.test(value)) s++;
    if (/\d/.test(value) && /[^A-Za-z0-9]/.test(value)) s++;
    return Math.max(1, s);
  }
  var labels = ["", "Too weak", "Weak", "Good", "Strong"];
  document.querySelectorAll("[data-strength-for]").forEach(function (meter) {
    var input = document.getElementById(meter.getAttribute("data-strength-for"));
    var label = meter.nextElementSibling;
    if (!input) return;
    input.addEventListener("input", function () {
      var s = input.value ? score(input.value) : 0;
      meter.setAttribute("data-s", String(s));
      if (label) label.textContent = labels[s];
    });
  });

  document.querySelectorAll("form[data-busy]").forEach(function (form) {
    form.addEventListener("submit", function () {
      var button = form.querySelector("button[type=submit]");
      if (button && form.checkValidity()) {
        setTimeout(function () { button.classList.add("is-loading"); button.disabled = true; }, 0);
      }
    });
  });
  window.addEventListener("pageshow", function () {  // coming back with the Back button
    document.querySelectorAll(".vbtn.is-loading").forEach(function (b) { b.classList.remove("is-loading"); b.disabled = false; });
  });
})();
