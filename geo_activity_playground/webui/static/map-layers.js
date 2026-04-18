export function add_layers_to_map(map, config) {
    const {
        zoom,
        attribution,
        baseTileUrl,
        overlay = 'Colorful Cluster',
        squarePlanner = null,
        heatmapExtraArgs = null,
        historyEventIndex = null
    } = config;

    const mapId = map.getContainer().id;
    const storageKey = `map-layers-${mapId}`;

    let saved = {};
    try {
        saved = JSON.parse(localStorage.getItem(storageKey) || '{}');
    } catch (e) {
        console.warn('Failed to load saved map layers:', e);
    }

    const baseLayerName = "Map";
    const base_maps = {
        [baseLayerName]: L.tileLayer(baseTileUrl, {
            maxZoom: 19,
            updateWhenZooming: false,
            keepBuffer: 4,
            attribution
        }),
    };

    // Build heatmap URL with optional extra args
    let heatmap_url = "/heatmap/tile/{z}/{x}/{y}.png";
    if (heatmapExtraArgs) {
        heatmap_url += `?${heatmapExtraArgs}`;
    }

    const mapterhornPaneName = "mapterhorn-hillshade";
    if (!map.getPane(mapterhornPaneName)) {
        const pane = map.createPane(mapterhornPaneName);
        pane.style.zIndex = "380";
        pane.style.mixBlendMode = "multiply";
        pane.style.pointerEvents = "none";
    }

    if (!(L.gridLayer && L.gridLayer.relief)) {
        console.error("leaflet-relief is required for Mapterhorn hillshade but is not available.");
    }

    const historyParam = Number.isInteger(historyEventIndex)
        ? `&event_index=${historyEventIndex}`
        : '';

    const overlay_maps = {
        "Mapterhorn Hillshade": (L.gridLayer && L.gridLayer.relief)
            ? L.gridLayer.relief({
                mode: "hillshade",
                tileSize: 256,
                elevationUrl: L.GridLayer.Relief.elevationUrls.mapterhorn,
                elevationExtractor: L.GridLayer.Relief.elevationExtractors.mapterhorn,
                attribution: L.GridLayer.Relief.elevationAttributions.mapterhorn,
                hillshadeColorFunction: (intensity) => {
                    const gray = Math.round(255 * intensity);
                    return [gray, gray, gray];
                },
                opacity: 0.5,
                maxZoom: 17,
                pane: mapterhornPaneName
            })
            : L.layerGroup(),
        "Colorful Cluster": L.tileLayer(`/explorer/${zoom}/tile/{z}/{x}/{y}.png?color_strategy=colorful_cluster${historyParam}`, {
            maxZoom: 19,
            updateWhenZooming: false,
            keepBuffer: 4,
            attribution
        }),
        "Max Cluster": L.tileLayer(`/explorer/${zoom}/tile/{z}/{x}/{y}.png?color_strategy=max_cluster${historyParam}`, {
            maxZoom: 19,
            updateWhenZooming: false,
            keepBuffer: 4,
            attribution
        }),
        "First Visit": L.tileLayer(`/explorer/${zoom}/tile/{z}/{x}/{y}.png?color_strategy=first`, {
            maxZoom: 19,
            updateWhenZooming: false,
            keepBuffer: 4,
            attribution
        }),
        "Last Visit": L.tileLayer(`/explorer/${zoom}/tile/{z}/{x}/{y}.png?color_strategy=last`, {
            maxZoom: 19,
            updateWhenZooming: false,
            keepBuffer: 4,
            attribution
        }),
        "Number of Visits": L.tileLayer(`/explorer/${zoom}/tile/{z}/{x}/{y}.png?color_strategy=visits`, {
            maxZoom: 19,
            updateWhenZooming: false,
            keepBuffer: 4,
            attribution
        }),
        "Visited": L.tileLayer(`/explorer/${zoom}/tile/{z}/{x}/{y}.png?color_strategy=visited`, {
            maxZoom: 19,
            updateWhenZooming: false,
            keepBuffer: 4,
            attribution
        }),
        "Missing": L.tileLayer(`/explorer/${zoom}/tile/{z}/{x}/{y}.png?color_strategy=missing`, {
            maxZoom: 19,
            updateWhenZooming: false,
            keepBuffer: 4,
            attribution
        }),
        "Heatmap": L.tileLayer(heatmap_url, {
            maxZoom: 19,
            updateWhenZooming: false,
            keepBuffer: 4,
            attribution
        }),
    };

    // Determine which overlay to select by default
    let selectedOverlay = overlay;

    if (squarePlanner) {
        const { x, y, size } = squarePlanner;
        overlay_maps["Square Planner"] = L.tileLayer(
            `/explorer/${zoom}/tile/{z}/{x}/{y}.png?color_strategy=square_planner&x=${x}&y=${y}&size=${size}`,
            { maxZoom: 19, updateWhenZooming: false, keepBuffer: 4, attribution }
        );
        selectedOverlay = "Square Planner";
    }

    const selectedBase = baseLayerName;

    // In square planner mode the active overlay must be deterministic and tied to URL
    // parameters; saved overlays can otherwise hide the planner layer.
    let selectedOverlays;
    if (squarePlanner) {
        selectedOverlays = [selectedOverlay];
    } else if (saved.overlays && Array.isArray(saved.overlays)) {
        const savedOverlays = saved.overlays.filter(name => overlay_maps[name]);
        selectedOverlays = savedOverlays.length > 0 ? savedOverlays : [selectedOverlay];
    } else {
        // Fall back to default (single overlay as array)
        selectedOverlays = [selectedOverlay];
    }

    base_maps[selectedBase].addTo(map);
    selectedOverlays.forEach(name => overlay_maps[name].addTo(map));

    L.control.layers(base_maps, overlay_maps).addTo(map);

    // Save layer selections to localStorage
    map.on('baselayerchange', (e) => {
        try {
            const current = JSON.parse(localStorage.getItem(storageKey) || '{}');
            current.base = e.name;
            localStorage.setItem(storageKey, JSON.stringify(current));
        } catch (err) {
            console.warn('Failed to save base layer preference:', err);
        }
    });

    // Helper to save all currently active overlays
    function saveOverlays() {
        try {
            const current = JSON.parse(localStorage.getItem(storageKey) || '{}');
            current.overlays = Object.keys(overlay_maps).filter(name => map.hasLayer(overlay_maps[name]));
            localStorage.setItem(storageKey, JSON.stringify(current));
        } catch (err) {
            console.warn('Failed to save overlay preference:', err);
        }
    }

    map.on('overlayadd', saveOverlays);
    map.on('overlayremove', saveOverlays);
}
