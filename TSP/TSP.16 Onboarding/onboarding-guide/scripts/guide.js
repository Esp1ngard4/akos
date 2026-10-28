(function () {
  "use strict";
  /* role paths: {role: [description, icon, [[title, body, actors, toKind, to, phrase, after], ...]]} */
  var ROLES = __PATHS__, names = Object.keys(ROLES);
  var role = names.indexOf("Developer") >= 0 ? "Developer" : names[0], step = 0;
  function ic(n) { return '<svg><use href="#i-' + n + '"/></svg>'; }
  function chip(kind, text) { var s = document.createElement("span"); s.className = "who " + kind; s.innerHTML = ic(kind === "agent" ? "spark" : "person"); s.appendChild(document.createTextNode(text)); return s; }
  var rolesEl = document.getElementById("roles"), stepsEl = document.getElementById("steps");
  function render() {
    if (!rolesEl || !role) return;
    Array.prototype.forEach.call(rolesEl.children, function (b) { b.setAttribute("aria-pressed", b.getAttribute("data-role") === role ? "true" : "false"); });
    var p = ROLES[role][2]; stepsEl.innerHTML = "";
    p.forEach(function (s, i) {
      var li = document.createElement("li"), b = document.createElement("button"); b.type = "button";
      b.innerHTML = '<span class="n">' + (i < step ? "✓" : i + 1) + "</span><span></span>"; b.lastChild.textContent = s[0];
      if (i === step) b.setAttribute("aria-current", "true"); if (i < step) b.className = "done";
      b.addEventListener("click", function () { step = i; render(); }); li.appendChild(b); stepsEl.appendChild(li);
    });
    var s = p[step], actors = document.getElementById("actors"), to = document.getElementById("sto");
    document.getElementById("progress").textContent = role + " · step " + (step + 1) + " of " + p.length;
    document.getElementById("pct").textContent = Math.round((step + 1) / p.length * 100) + "%";
    document.getElementById("bar").style.width = ((step + 1) / p.length * 100) + "%";
    actors.innerHTML = "";
    if (s[2] === "both") { actors.appendChild(chip("person", "You decide")); actors.appendChild(chip("agent", "Agent prepares")); }
    else if (s[2] === "agent") actors.appendChild(chip("agent", "Agent does it with you"));
    else actors.appendChild(chip("person", "You"));
    document.getElementById("stitle").textContent = s[0]; document.getElementById("sbody").textContent = s[1];
    to.innerHTML = ""; to.appendChild(chip(s[3], s[4])); to.appendChild(document.createTextNode(s[3] === "agent" ? " say this" : ""));
    document.getElementById("ssay").textContent = s[5]; document.getElementById("sask").textContent = s[6] || "";
    document.getElementById("prev").disabled = step === 0;
    document.getElementById("nextstep").textContent = step === p.length - 1 ? "Done" : "Next step";
  }
  if (rolesEl) {
    names.forEach(function (r) {
      var b = document.createElement("button"); b.type = "button"; b.setAttribute("data-role", r);
      b.innerHTML = '<div class="ico">' + ic(ROLES[r][1]) + "</div><div><b></b><span></span></div>";
      b.querySelector("b").textContent = r; b.querySelector("span").textContent = ROLES[r][0];
      b.addEventListener("click", function () { role = r; step = 0; render(); }); rolesEl.appendChild(b);
    });
    document.getElementById("prev").addEventListener("click", function () { if (step > 0) { step--; render(); } });
    document.getElementById("nextstep").addEventListener("click", function () { if (step < ROLES[role][2].length - 1) { step++; render(); } });
    render();
  }

  /* the map, and where you are */
  var map = document.getElementById("map");
  function parts() { return Array.prototype.slice.call(document.querySelectorAll("section.part")); }
  (function () { var last = null;
    parts().forEach(function (s) { var g = s.getAttribute("data-group");
      if (g && g !== last) { var gl = document.createElement("li"); gl.className = "group"; gl.textContent = g; map.appendChild(gl); } last = g;
      var li = document.createElement("li"), a = document.createElement("a"); a.href = "#" + s.id; a.textContent = s.getAttribute("data-title"); li.appendChild(a); map.appendChild(li); }); })();
  function track() { var cur = null, ps = parts(); ps.forEach(function (s) { if (s.getBoundingClientRect().top < 160) cur = s.id; }); if (!cur && ps.length) cur = ps[0].id;
    map.querySelectorAll("a").forEach(function (a) { a.setAttribute("aria-current", a.getAttribute("href") === "#" + cur ? "true" : "false"); }); }
  window.addEventListener("scroll", track, { passive: true }); track();

  /* search */
  var q = document.getElementById("q"), res = document.getElementById("results");
  q.addEventListener("input", function () { var t = q.value.trim().toLowerCase(); res.innerHTML = ""; if (t.length < 2) { res.hidden = true; return; } var hits = [];
    document.querySelectorAll("section.part [data-search]").forEach(function (c) {
      if ((c.getAttribute("data-search") + " " + c.textContent).toLowerCase().indexOf(t) >= 0) hits.push({ c: c, sec: c.closest("section.part") }); });
    hits.slice(0, 8).forEach(function (h) { var a = document.createElement("a"); a.href = "#" + h.sec.id; a.textContent = (h.c.querySelector("h3") || h.c).textContent.trim().slice(0, 70);
      var sm = document.createElement("small"); sm.textContent = h.sec.getAttribute("data-title"); a.appendChild(sm); a.addEventListener("click", function () { res.hidden = true; q.value = ""; }); res.appendChild(a); });
    if (!hits.length) { var n = document.createElement("a"); n.textContent = "Nothing found. Try sprint, board or agent."; res.appendChild(n); } res.hidden = false; });
  document.addEventListener("keydown", function (ev) { if (ev.key === "Escape") res.hidden = true; });
})();
