/* Q-rious: the real Google Map (built from Anjika's map.js).
   It fills <div id="map">, draws one pin per place, and talks to the app screens:
     - tap a pin          -> Qrious.select(id)  (opens that place's screen)
     - app selects a place -> the "qrious:select" event: this file pans to it
     - places change       -> the "qrious:places" event: this file redraws pins
   If there is no key, or Google refuses it, the sample map is used instead. */
(function () {
  var KEY = window.QRIOUS_MAPS_KEY;
  if (!KEY) return;                       // no key: the sample map stays

  var OXFORD = { lat: 51.7520, lng: -1.2577 };
  var map, MarkerClass, markers = {}, places = [], ready = false, done = false;

  function fallback(why) {
    if (done) return;
    done = true;
    console.warn("Q-rious: using the sample map (" + why + ")");
    if (window.Qrious && window.Qrious.useSampleMap) window.Qrious.useSampleMap();
  }
  window.gm_authFailure = function () { fallback("Google rejected the key"); };

  function levelWord(n) { return n <= 4 ? "Short" : n <= 9 ? "Medium" : "Long"; }

  function pinEl(p, selected) {
    var el = document.createElement("div");
    el.className = "gm-pin" + (selected ? " sel" : "");
    el.textContent = levelWord(p.queueNow) + " · " + p.wait + " min";
    return el;
  }

  function draw() {
    if (!ready) return;
    Object.keys(markers).forEach(function (id) { markers[id].map = null; });
    markers = {};
    var bounds = new google.maps.LatLngBounds(), n = 0;
    places.forEach(function (p) {
      if (typeof p.lat !== "number" || typeof p.lng !== "number") return;
      var m = new MarkerClass({
        map: map, position: { lat: p.lat, lng: p.lng },
        title: p.name + ", " + levelWord(p.queueNow) + " queue", content: pinEl(p, false)
      });
      m.addListener("click", function () { window.Qrious.select(p.id); });
      markers[p.id] = m; bounds.extend(m.position); n++;
    });
    if (n > 1) map.fitBounds(bounds, { top: 90, bottom: 300, left: 40, right: 40 });
    else if (n === 1) { map.setCenter(bounds.getCenter()); map.setZoom(16); }
  }

  function highlight(id) {
    places.forEach(function (p) {
      var m = markers[p.id]; if (!m) return;
      m.content = pinEl(p, p.id === id);
      m.zIndex = p.id === id ? 10 : 1;
    });
    var m2 = markers[id];
    if (m2) map.panTo(m2.position);
  }

  document.addEventListener("qrious:places", function (e) { places = e.detail || []; draw(); });
  document.addEventListener("qrious:select", function (e) { highlight(e.detail); });

  window.qriousInitMap = async function () {
    try {
      var mapsLib = await google.maps.importLibrary("maps");
      var markerLib = await google.maps.importLibrary("marker");
      MarkerClass = markerLib.AdvancedMarkerElement;
      map = new mapsLib.Map(document.getElementById("map"), {
        center: OXFORD, zoom: 15, mapId: "DEMO_MAP_ID",
        disableDefaultUI: true, gestureHandling: "greedy", clickableIcons: false
      });
      ready = true;
      places = (window.Qrious && window.Qrious.places()) || [];
      draw();
    } catch (err) {
      console.error(err);
      fallback("map failed to start");
    }
  };

  var s = document.createElement("script");
  s.async = true;
  s.src = "https://maps.googleapis.com/maps/api/js?key=" + encodeURIComponent(KEY) +
          "&loading=async&callback=qriousInitMap&v=weekly";
  s.onerror = function () { fallback("could not load Google Maps"); };
  document.head.appendChild(s);
  setTimeout(function () { if (!ready) fallback("timed out"); }, 10000);
})();
