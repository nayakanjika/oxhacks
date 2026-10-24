
/* =====================================
   1. CREATE OXFORD MAP
===================================== */

const map = L.map("map", {
    zoomControl: false
}).setView(
    [51.7520, -1.2577],
    15
);

/* =====================================
   2. ADD MAP TILES
===================================== */

L.tileLayer(
    "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    {
        maxZoom: 19,
        attribution: "&copy; OpenStreetMap contributors"
    }
).addTo(map);

map.attributionControl.setPosition("topright");

/* =====================================
   3. CREATE MARKER LAYER
===================================== */

const markers = L.layerGroup().addTo(map);

const searchInput = document.getElementById("search");
const results = document.getElementById("results");

let places = [];

/* =====================================
   4. CUSTOM MARKER DESIGN
===================================== */

const cafeIcon = L.divIcon({
    className: "",
    html: '<div class="custom-marker"></div>',
    iconSize: [18, 18],
    iconAnchor: [9, 9]
});

/* =====================================
   5. LOAD REAL OXFORD LOCATIONS
===================================== */

async function loadPlaces() {

    results.textContent = "Loading Oxford cafés...";

    // Oxford city centre bounding box
    const query = `
        [out:json][timeout:25];
        (
            nwr["amenity"="cafe"]
                (51.735,-1.280,51.770,-1.235);

            nwr["amenity"="restaurant"]
                (51.735,-1.280,51.770,-1.235);

            nwr["amenity"="fast_food"]
                (51.735,-1.280,51.770,-1.235);
        );
        out center;
    `;

    try {

        const response = await fetch(
            "https://overpass.kumi.systems/api/interpreter",
            {
                method: "POST",
                body: new URLSearchParams({
                    data: query
                })
            }
        );

        if (!response.ok) {
            throw new Error("Could not fetch places");
        }

        const data = await response.json();

        places = data.elements
            .map(item => ({
                name: item.tags?.name,
                type: item.tags?.amenity,
                cuisine: item.tags?.cuisine || "",
                lat: item.lat ?? item.center?.lat,
                lon: item.lon ?? item.center?.lon
            }))
            .filter(place =>
                place.name &&
                place.lat != null &&
                place.lon != null
            );

        displayPlaces(places);

    } catch (error) {

        console.error(error);

        results.textContent =
            "Unable to load locations. Please try again.";
    }
}

/* =====================================
   6. DISPLAY PLACES ON MAP
===================================== */

function displayPlaces(filteredPlaces) {

    // Remove previous markers
    markers.clearLayers();

    // Clear previous search results
    results.replaceChildren();

    filteredPlaces.slice(0, 100).forEach(place => {

        // Add marker
        const marker = L.marker(
            [place.lat, place.lon],
            {
                icon: cafeIcon
            }
        ).addTo(markers);

        // Safe popup content
        const popup = document.createElement("div");

        const popupTitle = document.createElement("strong");
        popupTitle.textContent = place.name;

        const popupType = document.createElement("p");
        popupType.textContent = place.cuisine || place.type;

        popup.append(popupTitle, popupType);

        marker.bindPopup(popup);

        // Create result card
        const item = document.createElement("div");

        item.className = "result";

        const name = document.createElement("strong");
        name.textContent = place.name;

        const description = document.createElement("small");

        description.textContent =
            place.type +
            (place.cuisine ? " · " + place.cuisine : "");

        item.append(name, description);

        // Clicking a result zooms to location
        item.addEventListener("click", () => {

            map.flyTo(
                [place.lat, place.lon],
                17,
                {
                    duration: 1.2
                }
            );

            marker.openPopup();
        });

        results.appendChild(item);
    });

    if (filteredPlaces.length === 0) {

        results.textContent =
            "No matching places found.";
    }
}

/* =====================================
   7. SEARCH FUNCTION
===================================== */

searchInput.addEventListener("input", () => {

    const searchTerm =
        searchInput.value.toLowerCase().trim();

    const filtered = places.filter(place => {

        const searchableText = `
            ${place.name}
            ${place.type}
            ${place.cuisine}
        `.toLowerCase();

        return searchableText.includes(searchTerm);
    });

    displayPlaces(filtered);
});

/* =====================================
   8. INITIALISE
===================================== */

loadPlaces();
