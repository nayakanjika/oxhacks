/* ------------------------------------------------------------------
   Q-rious: the app screen (map, queue sheets, chat, settings).

   HOW THIS FILE IS ORGANISED (top to bottom)
     1. Settings and small helpers
     2. adaptPlace()  <- THE ONE PLACE that translates backend field names
     3. Loading places and asking Gemini (sample data now, real routes later)
     4. Voice: listen() and speak()  <- swap point for ElevenLabs
     5. The map (placeholder now; teammate's Google Map replaces it)
     6. The screens (home, place, alternatives, recommendation, compare, report)
     7. Chat, settings, and event handling

   TEAMMATE HOOKS (all on window.Qrious):
     Qrious.setPlaces(list)  give it places in the agreed shape
     Qrious.select(id)       open a place (call from a map marker click)
     Listen for the "qrious:places" event to draw markers on the real map.
   ------------------------------------------------------------------ */
(function () {
  "use strict";

  /* ============ 1. Settings and helpers ============ */
  var CFG = window.QRIOUS_CONFIG || { demo: true };
  var DEMO = window.QRIOUS_DEMO_PLACES || [];
  var $ = function (sel) { return document.querySelector(sel); };

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function num(v, fallback) { v = Number(v); return isFinite(v) ? v : (fallback || 0); }
  function store(kind, key, val) {           // safe storage: never crashes if blocked
    try {
      var s = kind === "session" ? window.sessionStorage : window.localStorage;
      if (val === undefined) return s.getItem(key);
      s.setItem(key, val);
    } catch (e) { return null; }
  }

  var ICON = {
    gear: '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h10M18 7h2M4 17h2M10 17h10"/><circle cx="16" cy="7" r="2"/><circle cx="8" cy="17" r="2"/></svg>',
    speak: '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><path d="M4 9v6h4l5 4V5L8 9z"/><path d="M16 9a4 4 0 0 1 0 6"/></svg>'
  };

  var S = {
    places: [], query: "", item: null,
    view: "home", cur: null, rec: null, stack: [], maxWalk: 10,
    saved: num(store("session", "qrious_saved"), 0),
    a11y: { large: false, dyslexia: false, contrast: false },
    notify: num(store("local", "qrious_notify"), 5) || 5,
    chatCtx: { item: null }, chatStarted: false, history: []
  };
  try { var savedA = JSON.parse(store("local", "qrious_a11y") || "null"); if (savedA) S.a11y = Object.assign(S.a11y, savedA); } catch (e) {}

  /* Queue length words. Always shown as a WORD plus bars, never colour alone. */
  function level(n) {
    if (n <= 4) return { key: "short", word: "Short", bars: 1 };
    if (n <= 9) return { key: "medium", word: "Medium", bars: 2 };
    return { key: "long", word: "Long", bars: 3 };
  }
  function barsHTML(k) {
    return '<span class="bars" aria-hidden="true">' + [6, 10, 14].map(function (h, i) {
      return '<i class="' + (i < k ? "" : "off") + '" style="height:' + h + 'px"></i>';
    }).join("") + "</span>";
  }
  function lvlHTML(n, extra) {
    var l = level(n);
    return '<span class="lvl">' + barsHTML(l.bars) + l.word + (extra ? " · " + extra : "") + "</span>";
  }
  function total(p) { return p.walk + p.wait; }
  function plural(n, one, many) { return n + " " + (n === 1 ? one : many); }
  function demoTag() {
    var sample = CFG.demo || S.places.some(function (p) { return p.source === "sample"; });
    return sample ? '<span class="demo-tag">Sample data</span>' : "";
  }

  function verdict(p) {
    if (p.trend === "dropping") return { title: "Worth waiting.", text: "The queue is clearing. About " + p.wait + " min." };
    if (p.trend === "rising" || level(p.queueArrive).key === "long") return { title: "Skip it.", text: "The queue is getting longer." };
    return p.wait <= 5 ? { title: "Go now.", text: "Only about " + p.wait + " min." }
                       : { title: "Your call.", text: "The queue is steady at about " + p.wait + " min." };
  }
  function isGood(p) { return verdict(p).title !== "Skip it."; }

  /* ============ 2. adaptPlace: backend shape -> screen shape ============
     If your teammate's data uses different names, change ONLY this function. */
  function adaptPlace(raw) {
    var wait = num(raw.wait_minutes);
    var name = raw.place || raw.name || "Unnamed place";
    return {
      id: raw.id || raw.place_id || name.toLowerCase().replace(/[^a-z0-9]+/g, "-"),
      name: name,
      category: raw.category || "Place",
      walk: num(raw.walk_minutes),
      queueNow: num(raw.queue_now),
      queueArrive: num(raw.queue_on_arrival, num(raw.queue_now)),
      wait: wait,
      low: raw.wait_low != null ? num(raw.wait_low) : Math.max(0, wait - 2),
      high: raw.wait_high != null ? num(raw.wait_high) : wait + 3,
      trend: raw.trend || "steady",
      sells: raw.sells || [],
      note: raw.recommendation || raw.summary || "",
      source: raw.source || (CFG.demo ? "sample" : ""),
      lat: raw.lat, lng: raw.lng,
      x: raw.map_x != null ? raw.map_x : 50, y: raw.map_y != null ? raw.map_y : 30
    };
  }

  /* ============ 3. Loading places and asking Gemini ============ */
  function loadPlaces(query) {
    if (CFG.demo) return Promise.resolve(DEMO.map(adaptPlace));
    return fetch(CFG.placesUrl + "?q=" + encodeURIComponent(query || ""))
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (d) { return (d.places || d).map(adaptPlace); })
      .catch(function () {
        toast("Couldn't reach the server, so you're seeing sample data.");
        return DEMO.map(adaptPlace);
      });
  }

  function matchItem(q) {
    q = (q || "").toLowerCase();
    if (/coconut/.test(q)) return "coconut milk";
    if (/\boat\b/.test(q)) return "oat milk";
    if (/\btea\b/.test(q)) return "tea";
    if (/(coffee|latte|flat white|cappuccino|espresso)/.test(q)) return "coffee";
    return null; // DEMO ONLY. The real search is done by Gemini on the backend.
  }
  function hasItem(p, item) {
    return p.sells.some(function (s) { return String(s).toLowerCase().indexOf(item) >= 0; });
  }

  var ERR_WHY = {
    no_key: "Gemini key missing from .env", bad_key: "Gemini key rejected",
    busy: "Gemini is busy", network: "couldn't reach Gemini",
    no_model: "Gemini model not available", empty: "no answer from Gemini"
  };
  function offlineAnswer(text, why) {   // safety net so the chat never goes blank
    var r = demoAsk(text);
    r.text += " (Offline demo answer: " + why + ".)";
    return r;
  }
  function askGemini(text, hist) {
    if (!CFG.demo) {
      return fetch(CFG.askUrl, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, history: hist || [], context: { item: S.chatCtx.item, selected: S.cur } })
      }).then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
        .then(function (d) {
          if (d.error || !d.reply) return offlineAnswer(text, ERR_WHY[d.error] || "Gemini error");
          return { text: d.reply, placeId: d.place_id };
        })
        .catch(function () { return offlineAnswer(text, "server not reachable"); });
    }
    return new Promise(function (resolve) { setTimeout(function () { resolve(demoAsk(text)); }, 650); });
  }

  /* Pretend Gemini, for the sample-data demo only. */
  function demoAsk(text) {
    var t = text.toLowerCase();
    var walkM = t.match(/walk\w*[^\d]{0,16}(\d+)/) || t.match(/(\d+)\s*(?:min\w*)\s*(?:walk|away)/);
    var budgetM = !walkM && t.match(/(?:have|got|within|in|only)\s*(\d+)\s*(?:min|minute)/);
    var walkLimit = walkM ? Number(walkM[1]) : null;
    var budget = budgetM ? Number(budgetM[1]) : null;
    var item = matchItem(t) || S.chatCtx.item;
    S.chatCtx.item = item;
    var quiet = /quiet|shortest|least busy/.test(t);

    if (/errand/.test(t)) return { text: "Errand planning isn't in this version yet. For now, tell me one stop at a time and I'll find the quickest option." };

    var pool = S.places.filter(function (p) { return !item || hasItem(p, item); });
    var byTotal = pool.slice().sort(function (a, b) { return total(a) - total(b); });
    var range = pool.slice();
    if (walkLimit) range = range.filter(function (p) { return p.walk <= walkLimit; });
    if (budget) range = range.filter(function (p) { return total(p) <= budget; });
    range.sort(quiet ? function (a, b) { return a.queueNow - b.queueNow; } : function (a, b) { return total(a) - total(b); });

    if (!pool.length) return { text: "I couldn't find anywhere that sells that nearby." };
    if (!range.length) {
      var q0 = byTotal[0];
      return { text: "Nothing fits that. The quickest overall is " + q0.name + ": " + q0.walk + " min walk plus about " + q0.wait + " min in the queue, " + total(q0) + " min in all.", placeId: q0.id };
    }
    var best = range[0];
    var reply = best.name + " is your best bet. It's a " + best.walk + " min walk plus about " + best.wait + " min in the queue, around " + total(best) + " min in all.";
    if (budget) reply += " That leaves about " + (budget - total(best)) + " spare minutes.";
    if (quiet) reply = best.name + " has the shortest queue right now: " + plural(best.queueNow, "person", "people") + ". It's a " + best.walk + " min walk.";
    var better = byTotal[0];
    if (!quiet && better.id !== best.id && total(better) < total(best)) {
      reply += " " + better.name + " is " + better.walk + " min away, but it would be " + (total(best) - total(better)) + " min quicker overall.";
    }
    return { text: reply, placeId: best.id };
  }

  /* ============ 4. Voice: swap these two functions for ElevenLabs later ============
     listen(cb)   -> speaks into the mic, calls cb(text)
     speak(text)  -> reads text aloud
     They use the browser's built-in voice tools for now (no key needed). */
  function listen(onText, btn) {
    var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) { toast("Voice input isn't supported in this browser. Try Chrome."); return; }
    var r = new SR();
    r.lang = "en-GB"; r.interimResults = false; r.maxAlternatives = 1;
    if (btn) { btn.classList.add("listening"); btn.setAttribute("aria-label", "Listening…"); }
    function done() { if (btn) { btn.classList.remove("listening"); btn.setAttribute("aria-label", "Speak"); } }
    r.onresult = function (e) { onText(e.results[0][0].transcript); };
    r.onerror = function () { toast("Couldn't hear that. Please try again."); };
    r.onend = done;
    try { r.start(); } catch (e) { done(); }
  }
  function speak(text) {
    if (!("speechSynthesis" in window)) { toast("Reading aloud isn't supported in this browser."); return; }
    window.speechSynthesis.cancel();
    var u = new SpeechSynthesisUtterance(text);
    u.lang = "en-GB";
    window.speechSynthesis.speak(u);
  }

  /* ============ 5. The map ============ */
  function drawMap() {
    if (CFG.realMap) return; // the real Google Map fills #map instead
    $("#map").innerHTML =
      '<svg class="streets" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">' +
      '<rect width="100" height="100" fill="#dfe7f1"/>' +
      '<rect x="48" y="36" width="26" height="14" rx="2" fill="#cddbc9"/>' +
      '<g fill="none" stroke="#fff" stroke-linecap="round" vector-effect="non-scaling-stroke">' +
      '<path d="M0 30 L100 22" stroke-width="14" vector-effect="non-scaling-stroke"/>' +
      '<path d="M32 0 L42 100" stroke-width="12" vector-effect="non-scaling-stroke"/>' +
      '<path d="M0 62 L100 70" stroke-width="10" vector-effect="non-scaling-stroke"/>' +
      '<path d="M76 0 L68 100" stroke-width="9" vector-effect="non-scaling-stroke"/>' +
      '<path d="M0 46 L100 42" stroke="#f4f7fb" stroke-width="6" vector-effect="non-scaling-stroke"/>' +
      '</g></svg><div id="pins"></div>';
  }
  function drawPins() {
    var layer = $("#pins");
    if (!layer) return;
    layer.innerHTML = S.places.map(function (p) {
      var match = !S.item || hasItem(p, S.item);
      var cls = "pin" + (S.cur === p.id || S.rec === p.id ? " sel" : "") + (match ? "" : " dim");
      return '<button class="' + cls + '" style="left:' + p.x + "%;top:" + p.y + '%" data-act="select" data-id="' + esc(p.id) +
        '" aria-label="' + esc(p.name + ", queue " + level(p.queueNow).word) + '"><span class="dot"></span><span class="tag">' + level(p.queueNow).word + "</span></button>";
    }).join("");
  }

  /* ============ 6. The screens ============ */
  function byId(id) { return S.places.filter(function (p) { return p.id === id; })[0]; }
  function alternativesFor(origin) {
    return S.places.filter(function (p) {
      return p.id !== origin.id && (!S.item || hasItem(p, S.item)) && p.walk <= S.maxWalk;
    }).sort(function (a, b) { return total(a) - total(b); });
  }
  function directionsURL(p) {
    var dest = p.lat != null && p.lng != null ? p.lat + "," + p.lng : p.name + ", Oxford";
    return "https://www.google.com/maps/dir/?api=1&destination=" + encodeURIComponent(dest) + "&travelmode=walking";
  }
  function head(title) {
    return '<header class="hdr"><button class="hdr-btn" data-act="back" aria-label="Back">‹</button><span tabindex="-1">' + esc(title) + "</span></header>";
  }
  function itemLabel() { return S.item || "what you're after"; }

  var VIEWS = {
    home: function () {
      var n = S.places.filter(function (p) { return !S.item || hasItem(p, S.item); }).length;
      return '<div class="grab"></div><div class="sheet-top"><div><h2 tabindex="-1">Near you</h2>' +
        '<p class="meta">' + (S.item ? plural(n, "place sells", "places sell") + " " + esc(S.item) : plural(n, "place", "places") + " nearby") + " · tap a pin" + demoTag() + "</p></div>" +
        '<button class="small-btn" data-act="settings" aria-label="Settings">' + ICON.gear + "</button></div>" +
        '<p class="saved-line">Time saved this session: <b>' + S.saved + " min</b></p>";
    },

    place: function () {
      var p = byId(S.cur); if (!p) return VIEWS.home();
      var v = verdict(p), good = isGood(p);
      var trendWord = p.trend === "dropping" ? "clearing" : p.trend === "rising" ? "growing" : "steady";
      return '<div class="grab"></div><div class="sheet-top"><div><h2 tabindex="-1">' + esc(p.name) + "</h2>" +
        '<p class="meta">' + esc(p.category) + " · " + p.walk + " min walk" + (S.item && hasItem(p, S.item) ? " · Sells " + esc(S.item) : "") + "</p></div>" +
        '<button class="small-btn" data-act="back" aria-label="Close">✕</button></div>' +
        '<div class="tiles"><div class="tile"><small>Queue now</small><b>' + plural(p.queueNow, "person", "people") + "</b>" + lvlHTML(p.queueNow) + "</div>" +
        '<div class="tile"><small>When you arrive</small><b>~' + p.wait + " min</b>" + lvlHTML(p.queueArrive, trendWord) + "</div></div>" +
        '<div class="note"><em>Prediction · ' + p.low + " to " + p.high + " min" + demoTag() + "</em>Verdict: <b>" + esc(v.title) + "</b> " + esc(v.text) + "</div>" +
        '<div class="btn-row">' +
        (good
          ? '<button class="btn btn-primary" data-act="go" data-id="' + esc(p.id) + '">Take me there</button><button class="btn btn-outline" data-act="alts">Find other places</button>'
          : '<button class="btn btn-primary" data-act="alts">Too long? Find another</button><button class="btn btn-outline" data-act="go" data-id="' + esc(p.id) + '">Take me here anyway</button>') +
        "</div>" +
        '<button class="link-btn" data-act="report" data-id="' + esc(p.id) + '">Report the queue here</button>';
    },

    alternatives: function () {
      var origin = byId(S.cur); if (!origin) return VIEWS.home();
      var list = alternativesFor(origin);
      var chips = [5, 10, 15].map(function (m) {
        return '<button class="chip" data-act="walk" data-min="' + m + '" aria-pressed="' + (S.maxWalk === m) + '">' + m + " min</button>";
      }).join("");
      var cards = list.map(function (p, i) {
        return '<button class="card' + (i === 0 ? " best" : "") + '" data-act="pick" data-id="' + esc(p.id) + '"><div>' +
          (i === 0 ? '<span class="badge">Best option</span>' : "") +
          "<h3>" + esc(p.name) + "</h3><p>" + p.walk + " min walk" + (S.item ? " · " + esc(S.item) + " ✓" : "") + "</p>" +
          "<p>" + lvlHTML(p.queueArrive, plural(p.queueArrive, "person", "people") + " on arrival") + '</p></div><div class="tot"><b>' + total(p) + " min</b><small>total</small></div></button>";
      }).join("");
      var empty = '<div class="empty"><b>Nothing else within ' + S.maxWalk + " min.</b>Try a longer walk" + (S.item ? " to find another place that sells " + esc(S.item) : "") + ".</div>";
      return head("Other options") + '<div class="body"><label class="lbl">How far will you walk?</label><div class="chips" role="group" aria-label="Walking distance">' + chips + "</div>" +
        (list.length ? cards : empty) +
        (list.length ? '<div class="btn-row"><button class="btn btn-outline" data-act="compare">Compare with ' + esc(origin.name) + "</button></div>" : "") +
        '<p class="meta" style="text-align:center;margin-top:.8rem">Total time = walk + predicted queue' + demoTag() + "</p></div>";
    },

    recommend: function () {
      var alt = byId(S.rec), origin = byId(S.cur); if (!alt || !origin) return VIEWS.home();
      var saved = total(origin) - total(alt);
      var trendTxt = alt.trend === "dropping" ? "drop" : alt.trend === "rising" ? "grow" : "stay";
      var text = alt.note || (alt.name + (S.item ? " sells " + S.item + " and" : "") + " is " + alt.walk + " minutes away. The queue should " + trendTxt +
        " to about " + plural(alt.queueArrive, "person", "people") + " by the time you arrive, so " +
        (saved > 0 ? "you'll be served sooner than at " + origin.name + "." : "it's about the same as " + origin.name + "."));
      return head("Your best option") + '<div class="body"><h2 tabindex="-1" style="margin:0;font-size:1.35rem">' + esc(alt.name) + "</h2>" +
        '<p class="meta">' + esc(alt.category) + " · " + alt.walk + " min walk" + (S.item ? " · " + esc(S.item) + " ✓" : "") + "</p>" +
        '<div class="note"><div class="row"><div><em>✦ Gemini' + demoTag() + "</em>" + esc(text) + '</div><button class="speak-btn" data-act="speak" data-text="' + esc(text) + '" aria-label="Read this aloud">' + ICON.speak + "</button></div></div>" +
        '<div class="tiles"><div class="tile"><small>Walk</small><b>' + alt.walk + ' min</b></div><div class="tile"><small>Queue on arrival</small><b>' + plural(alt.queueArrive, "person", "people") + "</b>" + lvlHTML(alt.queueArrive) + "</div></div>" +
        '<div class="saved-big"><small>Compared with ' + esc(origin.name) + "</small><b>" + (saved > 0 ? "You save " + saved + " min" : "About the same time") + "</b></div>" +
        '<div class="btn-row"><button class="btn btn-primary" data-act="go" data-id="' + esc(alt.id) + '" data-saved="' + Math.max(0, saved) + '">Take me there</button>' +
        '<button class="btn btn-outline" data-act="another">Show me another</button></div></div>';
    },

    compare: function () {
      var a = byId(S.cur), b = byId(S.rec); if (!a || !b) return VIEWS.home();
      function cell(val, win) { return '<div class="cell' + (win ? " win" : "") + '">' + val + "</div>"; }
      var rows = [
        ["Walk", a.walk + " min", b.walk + " min", b.walk < a.walk, a.walk < b.walk],
        ["Queue on arrival", "<b>" + plural(a.queueArrive, "person", "people") + "</b>" + lvlHTML(a.queueArrive), "<b>" + plural(b.queueArrive, "person", "people") + "</b>" + lvlHTML(b.queueArrive), b.queueArrive < a.queueArrive, a.queueArrive < b.queueArrive],
        ["Wait", "<b>~" + a.wait + " min</b>", "<b>~" + b.wait + " min</b>", b.wait < a.wait, a.wait < b.wait],
        ["Total", "<b>" + total(a) + " min</b>", "<b>" + total(b) + " min</b>", total(b) < total(a), total(a) < total(b)]
      ];
      return head("Compare") + '<div class="body"><div class="cmp"><div></div><div class="h">' + esc(a.name) + '</div><div class="h">' + esc(b.name) + "</div>" +
        rows.map(function (r) { return '<div class="lab">' + r[0] + "</div>" + cell(r[1], r[4]) + cell(r[2], r[3]); }).join("") + "</div>" +
        '<p class="meta" style="margin-top:.8rem">The highlighted box is quicker.' + demoTag() + "</p>" +
        '<div class="btn-row"><button class="btn btn-primary" data-act="go" data-id="' + esc(b.id) + '" data-saved="' + Math.max(0, total(a) - total(b)) + '">Take me to ' + esc(b.name) + '</button><button class="btn btn-outline" data-act="back">Back</button></div></div>';
    },

    report: function () {
      var opts = S.places.map(function (p) {
        return '<option value="' + esc(p.id) + '"' + (p.id === S.reportId ? " selected" : "") + ">" + esc(p.name) + "</option>";
      }).join("");
      function lv(key, word, hint, k) {
        return '<button class="level-btn" data-act="level" data-level="' + key + '">' + barsHTML(k) + "<span>" + word + "<small>" + hint + "</small></span></button>";
      }
      return head("Report a queue") + '<div class="body"><label class="lbl" for="reportPlace">Which place?</label><select class="field" id="reportPlace">' + opts + "</select>" +
        '<p class="meta" style="margin-top:1rem">How long is the queue right now?</p><div class="level-btns">' +
        lv("short", "Short", "Up to 4 people", 1) + lv("medium", "Medium", "5 to 9 people", 2) + lv("long", "Long", "10 or more people", 3) +
        '</div><p class="meta">Two taps. We only keep the length, nothing about you.</p></div>';
    }
  };

  function render(focus) {
    drawPins();
    var sheet = $("#sheet");
    var full = ["alternatives", "recommend", "compare", "report"].indexOf(S.view) >= 0;
    sheet.className = "sheet" + (full ? " full" : "");
    sheet.innerHTML = VIEWS[S.view]();
    if (focus) {
      var f = sheet.querySelector("h2, .hdr span");
      if (f) f.focus({ preventScroll: true });
    }
  }
  function nav(view, extra) {
    S.stack.push({ view: S.view, cur: S.cur, rec: S.rec });
    S.view = view;
    if (extra) Object.keys(extra).forEach(function (k) { S[k] = extra[k]; });
    render(true);
  }
  function back() {
    var s = S.stack.pop();
    if (!s) { S.view = "home"; S.cur = null; S.rec = null; }
    else { S.view = s.view; S.cur = s.cur; S.rec = s.rec; }
    render(true);
  }
  function selectPlace(id) {
    if (!byId(id)) return;
    S.stack = [{ view: "home", cur: null, rec: null }];
    S.view = "place"; S.cur = id; S.rec = null;
    render(true);
    document.dispatchEvent(new CustomEvent("qrious:select", { detail: id }));
  }
  function go(id, savedMin) {
    var p = byId(id); if (!p) return;
    if (savedMin > 0) {
      S.saved += savedMin; store("session", "qrious_saved", String(S.saved));
      toast("Nice, that's " + savedMin + " min saved. Opening directions…");
    } else { toast("Opening directions…"); }
    window.open(directionsURL(p), "_blank", "noopener");
  }

  /* ============ 7. Chat, settings, events ============ */
  var toastTimer;
  function toast(msg) {
    var t = $("#toast"); if (!t) return;
    t.textContent = msg; t.classList.add("show");
    clearTimeout(toastTimer); toastTimer = setTimeout(function () { t.classList.remove("show"); }, 3200);
  }

  function addMsg(who, text, placeId) {
    var log = $("#chatLog");
    var el = document.createElement("div");
    el.className = "msg " + (who === "u" ? "u" : "a");
    var html = esc(text);
    if (who === "a") {
      var p = placeId && byId(placeId);
      html += '<div class="msg-actions">' + (p ? '<button class="chip" data-act="chat-show" data-id="' + esc(p.id) + '">Show ' + esc(p.name) + "</button>" : "") +
        '<button class="speak-btn" data-act="speak" data-text="' + esc(text) + '" aria-label="Read this aloud">' + ICON.speak + "</button></div>";
    }
    el.innerHTML = html;
    log.appendChild(el); log.scrollTop = log.scrollHeight;
    return el;
  }
  function openChat() {
    $("#chat").hidden = false;
    if (!S.chatStarted) {
      S.chatStarted = true;
      addMsg("a", "Hi! Tell me what you're after and how long you've got, and I'll find the quickest option.");
      $("#chatChips").innerHTML = ["Coconut milk latte near me", "Quietest place now", "I have 15 minutes"].map(function (t) {
        return '<button class="chip" data-act="ask" data-text="' + esc(t) + '">' + esc(t) + "</button>";
      }).join("");
    }
    $("#chatText").focus();
  }
  function ask(text) {
    text = (text || "").trim(); if (!text) return;
    addMsg("u", text); $("#chatText").value = "";
    var typing = addMsg("a", "Thinking…"); typing.classList.add("typing");
    typing.querySelector(".msg-actions").remove();
    var hist = S.history.slice(-8);
    S.history.push({ role: "user", text: text });
    askGemini(text, hist).then(function (r) {
      typing.remove(); addMsg("a", r.text, r.placeId);
      S.history.push({ role: "model", text: r.text });
    });
  }

  function settingsRows() {
    function row(key, title, desc) {
      var on = S.a11y[key];
      return '<div class="setting"><div><h3>' + title + "</h3><p>" + desc + '</p></div><button class="chip" data-act="toggle" data-key="' + key + '" aria-pressed="' + on + '">' + (on ? "On" : "Off") + "</button></div>";
    }
    $("#settingsBody").innerHTML = '<h2 style="margin:0 0 .8rem;font-size:1.2rem">Make it easier to read</h2>' +
      row("large", "Larger text", "Makes everything bigger") +
      row("dyslexia", "Dyslexia-friendly font", "Uses Atkinson Hyperlegible") +
      row("contrast", "High contrast", "Stronger borders and text") +
      '<h2 style="margin:1.2rem 0 .8rem;font-size:1.2rem">Alerts and sharing</h2>' +
      '<div class="setting"><div><h3>Notify me</h3><p>Alert me when a queue drops under this many people</p>' +
      '<div class="stepper"><button data-act="notify-dec" aria-label="Fewer people">−</button><output id="notifyVal" aria-live="polite">' + S.notify + '</output><button data-act="notify-inc" aria-label="More people">+</button></div></div>' +
      '<button class="chip" data-act="notify-set">Set</button></div>' +
      '<div class="setting"><div><h3>Report a queue</h3><p>Two taps to help others</p></div><button class="chip" data-act="report-open">Open</button></div>';
  }
  function applyA11y() {
    document.documentElement.classList.toggle("a11y-large", !!S.a11y.large);
    document.body.classList.toggle("a11y-dyslexia", !!S.a11y.dyslexia);
    document.body.classList.toggle("a11y-contrast", !!S.a11y.contrast);
  }

  function doSearch(text) {
    S.query = (text || "").trim();
    S.item = matchItem(S.query);
    loadPlaces(S.query).then(function (list) {
      S.places = list; S.stack = []; S.view = "home"; S.cur = null; S.rec = null;
      render(false);
      document.dispatchEvent(new CustomEvent("qrious:places", { detail: S.places }));
      if (S.query && !S.item) toast("Showing everything nearby. In this demo I only filter by coffee, tea, oat milk and coconut milk.");
    });
  }

  document.addEventListener("click", function (e) {
    var el = e.target.closest("[data-act]"); if (!el) return;
    var act = el.getAttribute("data-act"), id = el.getAttribute("data-id");
    switch (act) {
      case "select": selectPlace(id); break;
      case "back": back(); break;
      case "alts": nav("alternatives"); break;
      case "walk": S.maxWalk = Number(el.getAttribute("data-min")); render(false); break;
      case "pick": nav("recommend", { rec: id }); break;
      case "another": {
        var list = alternativesFor(byId(S.cur));
        var i = list.map(function (p) { return p.id; }).indexOf(S.rec);
        if (list.length < 2) { toast("That's the only other option in range. Try a longer walk."); break; }
        S.rec = list[(i + 1) % list.length].id; render(true); break;
      }
      case "compare": S.view = "compare"; S.stack.push({ view: "alternatives", cur: S.cur, rec: S.rec });
        S.rec = S.rec || alternativesFor(byId(S.cur))[0].id; render(true); break;
      case "go": go(id, Number(el.getAttribute("data-saved") || 0)); break;
      case "report": S.reportId = id || S.cur || (S.places[0] && S.places[0].id); nav("report"); break;
      case "report-open": $("#settings").hidden = true; S.reportId = S.cur || (S.places[0] && S.places[0].id); nav("report"); break;
      case "level": {
        var pid = ($("#reportPlace") || {}).value, p = byId(pid), lvKey = el.getAttribute("data-level");
        if (p) {
          var people = { short: 2, medium: 6, long: 12 }[lvKey], wt = { short: 2, medium: 5, long: 12 }[lvKey];
          p.queueNow = people; p.queueArrive = people; p.wait = wt; p.low = Math.max(0, wt - 2); p.high = wt + 3;
          if (!CFG.demo) { fetch(CFG.reportUrl, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ place_id: pid, level: lvKey }) }).catch(function () {}); }
          toast("Thanks! Queue reported for " + p.name + ".");
        }
        back(); break;
      }
      case "settings": settingsRows(); $("#settings").hidden = false; $("#settingsClose").focus(); break;
      case "toggle": {
        var k = el.getAttribute("data-key"); S.a11y[k] = !S.a11y[k];
        store("local", "qrious_a11y", JSON.stringify(S.a11y)); applyA11y(); settingsRows();
        var again = $('#settingsBody [data-key="' + k + '"]'); if (again) again.focus(); break;
      }
      case "notify-dec": S.notify = Math.max(1, S.notify - 1); $("#notifyVal").textContent = S.notify; break;
      case "notify-inc": S.notify = Math.min(30, S.notify + 1); $("#notifyVal").textContent = S.notify; break;
      case "notify-set": store("local", "qrious_notify", String(S.notify));
        toast("Got it. We'll tell you when a queue drops under " + plural(S.notify, "person", "people") + "."); break; // real alerts: needs the backend
      case "ask": ask(el.getAttribute("data-text")); break;
      case "chat-show": $("#chat").hidden = true; selectPlace(id); break;
      case "speak": speak(el.getAttribute("data-text")); break;
    }
  });

  $("#searchForm").addEventListener("submit", function (e) { e.preventDefault(); doSearch($("#q").value); $("#q").blur(); });
  $("#chatBtn").addEventListener("click", openChat);
  $("#chatClose").addEventListener("click", function () { $("#chat").hidden = true; $("#chatBtn").focus(); });
  $("#settingsClose").addEventListener("click", function () { $("#settings").hidden = true; });
  $("#chatForm").addEventListener("submit", function (e) { e.preventDefault(); ask($("#chatText").value); });
  $("#micBtn").addEventListener("click", function () { var b = this; listen(function (t) { $("#q").value = t; doSearch(t); }, b); });
  $("#chatMic").addEventListener("click", function () { var b = this; listen(function (t) { ask(t); }, b); });
  document.addEventListener("keydown", function (e) {
    if (e.key !== "Escape") return;
    if (!$("#chat").hidden) $("#chat").hidden = true;
    else if (!$("#settings").hidden) $("#settings").hidden = true;
    else if (S.view !== "home") back();
  });

  /* Public hooks for the teammate's real map */
  window.Qrious = {
    setPlaces: function (list) { S.places = list.map(adaptPlace); render(false); document.dispatchEvent(new CustomEvent("qrious:places", { detail: S.places })); },
    select: selectPlace,
    places: function () { return S.places; }
  };

  /* Start */
  applyA11y();
  drawMap();
  loadPlaces("").then(function (list) {
    S.places = list; render(false);
    document.dispatchEvent(new CustomEvent("qrious:places", { detail: S.places }));
  });
})();
