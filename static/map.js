
const OXFORD = { lat: 51.7520, lng: -1.2577 };

let map;
let selectedPlace = null;
let markers = [];
let Place;
let AdvancedMarkerElement;

const sheet = document.getElementById("bottom-sheet");
const handle = document.getElementById("drag-handle");
const searchInput = document.getElementById("search");

let sheetOffset = 340;
let startY = 0;
let startOffset = 340;
let dragging = false;

// INITIALISE GOOGLE MAPS
window.initMap = async function () {
    try {
        const mapsLib = await google.maps.importLibrary("maps");
        const placesLib = await google.maps.importLibrary("places");
        const markerLib = await google.maps.importLibrary("marker");

        Place = placesLib.Place;
        AdvancedMarkerElement = markerLib.AdvancedMarkerElement;

        map = new mapsLib.Map(document.getElementById("map"), {
            center: OXFORD,
            zoom: 15,
            mapId: "DEMO_MAP_ID",
            disableDefaultUI: true,
            gestureHandling: "greedy",
            clickableIcons: false
        });

        await loadCafes();

    } catch (error) {
        console.error(error);
        document.getElementById("nearby-count").textContent =
            "Could not load Google Maps. Check API settings.";
    }
};

// LOAD REAL CAFES
async function loadCafes(query = "") {
    try {
        let response;

        if (query.trim()) {
            response = await Place.searchByText({
                textQuery: query + " in Oxford UK",
                fields: [
                    "id",
                    "displayName",
                    "location",
                    "formattedAddress"
                ],
                locationBias: {
                    center: OXFORD,
                    radius: 3000
                },
                maxResultCount: 20
            });
        } else {
            response = await Place.searchNearby({
                fields: [
                    "id",
                    "displayName",
                    "location",
                    "formattedAddress"
                ],
                locationRestriction: {
                    center: OXFORD,
                    radius: 2500
                },
                includedPrimaryTypes: ["cafe"],
                maxResultCount: 20
            });
        }

        clearMarkers();

        const places = response.places || [];

        document.getElementById("nearby-count").textContent =
            places.length + " places · Tap a pin";

        places.forEach((place, index) => {
            if (!place.location) return;

            const pin = document.createElement("div");
            pin.className = "cafe-pin";
            pin.style.cssText = `
                width: 25px;
                height: 25px;
                border-radius: 50% 50% 50% 0;
                background: #002147;
                border: 3px solid white;
                transform: rotate(-45deg);
                box-shadow: 0 3px 8px #0004;
                cursor: pointer;
            `;

            const marker = new AdvancedMarkerElement({
                map: map,
                position: place.location,
                title: place.displayName,
                content: pin
            });

            marker.addListener("click", () => {
                showPlace(place, index);
            });

            markers.push(marker);
        });

    } catch (error) {
        console.error("Places error:", error);
        document.getElementById("nearby-count").textContent =
            "Unable to load cafés. Check Places API access.";
    }
}

function clearMarkers() {
    markers.forEach(marker => marker.map = null);
    markers = [];
}

// SCREEN 2: SELECTED PLACE
function showPlace(place, index) {
    selectedPlace = place;

    document.getElementById("nearby-view")
        .classList.add("hidden");

    document.getElementById("place-view")
        .classList.remove("hidden");

    document.getElementById("place-name").textContent =
        place.displayName || "Oxford Café";

    document.getElementById("place-description").textContent =
        "Café · " + (place.formattedAddress || "Oxford");

    // SAMPLE QUEUE DATA - REPLACE WITH BACKEND LATER
    const queue = 5 + (index * 3) % 15;
    const wait = Math.round(queue * 1.15);

    document.getElementById("queue-now").textContent =
        queue + " people";

    document.getElementById("queue-later").textContent =
        "~" + wait + " min";

    document.getElementById("queue-status").textContent =
        queue > 10 ? "▮▮▮ Long" : "▮▮ Short";

    document.getElementById("prediction-text").textContent =
        queue > 10
            ? "Verdict: Skip it. The queue is currently long."
            : "Verdict: Good option. The queue is relatively short.";

    map.panTo(place.location);
    expandSheet();
}

// SHEET ANIMATIONS
function expandSheet() {
    sheetOffset = 0;
    sheet.style.transform = "translateY(0px)";
}

function collapseSheet() {
    sheetOffset = 340;
    sheet.style.transform = "translateY(340px)";
}

handle.addEventListener("pointerdown", event => {
    dragging = true;
    startY = event.clientY;
    startOffset = sheetOffset;

    sheet.style.transition = "none";
    handle.setPointerCapture(event.pointerId);
});

handle.addEventListener("pointermove", event => {
    if (!dragging) return;

    const delta = event.clientY - startY;
    sheetOffset = Math.max(0, Math.min(340, startOffset + delta));

    sheet.style.transform =
        `translateY(${sheetOffset}px)`;
});

handle.addEventListener("pointerup", () => {
    if (!dragging) return;

    dragging = false;
    sheet.style.transition =
        "transform .45s cubic-bezier(.22,1,.36,1)";

    if (sheetOffset < 170) {
        expandSheet();
    } else {
        collapseSheet();
    }
});

handle.addEventListener("pointercancel", () => {
    dragging = false;
    sheet.style.transition =
        "transform .45s cubic-bezier(.22,1,.36,1)";
    if (sheetOffset < 170) expandSheet();
    else collapseSheet();
});

// SEARCH
let searchTimer;

searchInput.addEventListener("input", () => {
    clearTimeout(searchTimer);

    searchTimer = setTimeout(() => {
        loadCafes(searchInput.value);
    }, 650);
});

// BUTTONS
document.getElementById("find-another")
    .addEventListener("click", () => {
        document.getElementById("place-view")
            .classList.add("hidden");

        document.getElementById("nearby-view")
            .classList.remove("hidden");

        selectedPlace = null;
        collapseSheet();
    });

document.getElementById("directions")
    .addEventListener("click", () => {
        if (!selectedPlace) return;

        const loc = selectedPlace.location;

        const url =
            "https://www.google.com/maps/dir/?api=1" +
            "&destination=" +
            encodeURIComponent(loc.lat() + "," + loc.lng()) +
            "&travelmode=walking";

        window.open(url, "_blank", "noopener,noreferrer");
    });
