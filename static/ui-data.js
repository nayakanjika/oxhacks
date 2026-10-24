/* ------------------------------------------------------------------
   Q-rious: settings and SAMPLE DATA for the app screen.

   1) QRIOUS_CONFIG says whether we use the sample data (demo: true) or the
      real backend (demo: false).
   2) QRIOUS_DEMO_PLACES is the sample data. Its field names are the
      "agreed shape" for the backend, so the real routes should return the
      same names:

        place, category, walk_minutes, queue_now, queue_on_arrival,
        wait_minutes, sells, trend ("rising" | "dropping" | "steady")

      Optional extras: id, lat, lng, wait_low, wait_high, recommendation,
      by_hour (a list of average waits per hour, for the best-time chart).

   If the backend uses different names, DON'T change the screens. Change
   adaptPlace() in ui.js: it is the one place that translates field names.
   ------------------------------------------------------------------ */

window.QRIOUS_CONFIG = {
  demo: true,                // true = sample data. false = call the routes below.
  realMap: false,            // set true once the real Google Map fills #map
  placesUrl: "/api/places",  // GET ?q=coconut milk latte  ->  list of places
  askUrl: "/api/ask",        // POST {message, context}    ->  {reply, place_id?}
  reportUrl: "/api/report"   // POST {place_id, level}     ->  {ok: true}
};

/* map_x and map_y only place the pins on the placeholder map (0 to 100). */
window.QRIOUS_DEMO_PLACES = [
  {
    id: "blue-door", place: "Blue Door Café", category: "Café",
    walk_minutes: 2, queue_now: 14, queue_on_arrival: 13, wait_minutes: 14,
    wait_low: 12, wait_high: 17, trend: "rising",
    sells: ["coffee", "coconut milk", "oat milk"],
    lat: 51.7520, lng: -1.2577, map_x: 44, map_y: 34
  },
  {
    id: "corner-roast", place: "Corner Roast", category: "Café",
    walk_minutes: 6, queue_now: 6, queue_on_arrival: 3, wait_minutes: 3,
    wait_low: 2, wait_high: 5, trend: "dropping",
    sells: ["coffee", "coconut milk", "oat milk"],
    lat: 51.7535, lng: -1.2540, map_x: 70, map_y: 22
  },
  {
    id: "oat-and-bean", place: "Oat & Bean", category: "Café",
    walk_minutes: 9, queue_now: 6, queue_on_arrival: 5, wait_minutes: 3,
    wait_low: 2, wait_high: 6, trend: "dropping",
    sells: ["coffee", "coconut milk", "oat milk"],
    lat: 51.7490, lng: -1.2610, map_x: 22, map_y: 36
  },
  {
    id: "quad-coffee", place: "Quad Coffee", category: "Café",
    walk_minutes: 10, queue_now: 4, queue_on_arrival: 7, wait_minutes: 5,
    wait_low: 4, wait_high: 8, trend: "rising",
    sells: ["coffee", "coconut milk"],
    lat: 51.7555, lng: -1.2500, map_x: 80, map_y: 38
  },
  {
    id: "tillys", place: "Tilly's Tea Room", category: "Tea room",
    walk_minutes: 3, queue_now: 2, queue_on_arrival: 2, wait_minutes: 2,
    wait_low: 1, wait_high: 3, trend: "steady",
    sells: ["tea", "cake"],
    lat: 51.7510, lng: -1.2560, map_x: 56, map_y: 28
  }
];
