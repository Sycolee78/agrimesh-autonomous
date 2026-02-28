"use client";

import { useEffect, useState, useRef } from "react";
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  useMapEvents,
  useMap,
  Polygon,
  FeatureGroup,
} from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "leaflet-draw/dist/leaflet.draw.css";
import { useFarmStore } from "@/store/farmStore";
import type { Coordinates, FarmZone } from "@/types/farm";
import { lookupAEZZone } from "@/lib/api";

// ============================================================================
// Custom Icons
// ============================================================================

const customIcon = new L.Icon({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

const farmIcon = new L.Icon({
  iconUrl:
    "data:image/svg+xml," +
    encodeURIComponent(`
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#16a34a" width="36" height="36">
      <path d="M12 3L2 12h3v9h14v-9h3L12 3zm0 2.5L18 11v8H6v-8l6-5.5z"/>
      <path d="M10 14h4v6h-4z" fill="#15803d"/>
    </svg>
  `),
  iconSize: [36, 36],
  iconAnchor: [18, 36],
  popupAnchor: [0, -36],
});

// ============================================================================
// Drawing Controls Component
// ============================================================================

interface DrawingControlsProps {
  onZoneCreated: (zone: FarmZone) => void;
  drawingMode: string | null;
}

function DrawingControls({ onZoneCreated, drawingMode }: DrawingControlsProps) {
  const map = useMap();
  const featureGroupRef = useRef<L.FeatureGroup | null>(null);
  const drawControlRef = useRef<L.Control.Draw | null>(null);

  useEffect(() => {
    // Dynamic import for leaflet-draw (client-side only)
    import("leaflet-draw").then(() => {
      if (!featureGroupRef.current) {
        featureGroupRef.current = new L.FeatureGroup();
        map.addLayer(featureGroupRef.current);
      }

      // Remove existing draw control
      if (drawControlRef.current) {
        map.removeControl(drawControlRef.current);
      }

      // Create draw control
      const drawControl = new L.Control.Draw({
        position: "topright",
        draw: {
          polyline: false,
          rectangle: {
            shapeOptions: {
              color: getZoneColor(drawingMode),
              fillOpacity: 0.3,
            },
          },
          polygon: {
            allowIntersection: false,
            shapeOptions: {
              color: getZoneColor(drawingMode),
              fillOpacity: 0.3,
            },
          },
          circle: false,
          circlemarker: false,
          marker: false,
        },
        edit: {
          featureGroup: featureGroupRef.current,
          remove: true,
        },
      });

      map.addControl(drawControl);
      drawControlRef.current = drawControl;

      // Handle draw events
      map.on(L.Draw.Event.CREATED, (e: any) => {
        const layer = e.layer;
        const coords = layer.getLatLngs()[0].map((ll: L.LatLng) => ({
          lat: ll.lat,
          lng: ll.lng,
        }));

        const zone: FarmZone = {
          id: `zone-${Date.now()}`,
          type: (drawingMode as FarmZone["type"]) || "crops",
          polygon: coords,
          label: `${drawingMode || "Zone"} ${Date.now()}`.slice(-4),
        };

        onZoneCreated(zone);
        featureGroupRef.current?.addLayer(layer);
      });
    });

    return () => {
      if (drawControlRef.current) {
        map.removeControl(drawControlRef.current);
      }
    };
  }, [map, drawingMode, onZoneCreated]);

  return null;
}

function getZoneColor(zoneType: string | null): string {
  const colors: Record<string, string> = {
    crops: "#22c55e",
    pasture: "#eab308",
    buildings: "#64748b",
    water: "#3b82f6",
  };
  return colors[zoneType || "crops"] || "#22c55e";
}

// ============================================================================
// Map Event Handler
// ============================================================================

function MapEventHandler() {
  const { mapMode, selectLocation, initializeFarm, farmConfig } = useFarmStore();

  useMapEvents({
    click: (e) => {
      if (mapMode === "view" || mapMode === "select") {
        const coords: Coordinates = { lat: e.latlng.lat, lng: e.latlng.lng };

        if (!farmConfig) {
          initializeFarm(coords, 5);
        } else {
          selectLocation(coords);
        }
      }
    },
  });

  return null;
}

// ============================================================================
// Map Position Sync
// ============================================================================

function MapPositionSync() {
  const map = useMap();
  const { mapCenter, mapZoom, setMapCenter, setMapZoom } = useFarmStore();

  useEffect(() => {
    map.setView([mapCenter.lat, mapCenter.lng], mapZoom);
  }, [map, mapCenter, mapZoom]);

  useMapEvents({
    moveend: () => {
      const center = map.getCenter();
      setMapCenter({ lat: center.lat, lng: center.lng });
    },
    zoomend: () => {
      setMapZoom(map.getZoom());
    },
  });

  return null;
}

// ============================================================================
// Farm Zones Renderer
// ============================================================================

interface ZoneRendererProps {
  zones: FarmZone[];
  onZoneClick?: (zone: FarmZone) => void;
}

function ZoneRenderer({ zones, onZoneClick }: ZoneRendererProps) {
  const zoneColors: Record<string, string> = {
    crops: "#22c55e",
    pasture: "#eab308",
    buildings: "#64748b",
    water: "#3b82f6",
  };

  const zoneIcons: Record<string, string> = {
    crops: "🌾",
    pasture: "🐄",
    buildings: "🏠",
    water: "💧",
  };

  return (
    <>
      {zones.map((zone) => (
        <Polygon
          key={zone.id}
          positions={zone.polygon.map((p) => [p.lat, p.lng] as [number, number])}
          pathOptions={{
            color: zoneColors[zone.type] || "#888",
            fillColor: zoneColors[zone.type] || "#888",
            fillOpacity: 0.3,
            weight: 2,
          }}
          eventHandlers={{
            click: () => onZoneClick?.(zone),
          }}
        >
          <Popup>
            <div className="p-2 min-w-[150px]">
              <h3 className="font-semibold capitalize flex items-center gap-2">
                <span>{zoneIcons[zone.type] || "📍"}</span>
                {zone.type} Zone
              </h3>
              {zone.label && <p className="text-sm text-gray-600 mt-1">{zone.label}</p>}
              {zone.cropType && (
                <p className="text-sm mt-1">
                  <strong>Crop:</strong> {zone.cropType}
                </p>
              )}
              <p className="text-xs text-gray-400 mt-2">
                {zone.polygon.length} vertices
              </p>
            </div>
          </Popup>
        </Polygon>
      ))}
    </>
  );
}

// ============================================================================
// Location Info Popup
// ============================================================================

interface LocationPopupProps {
  location: Coordinates;
}

function LocationPopup({ location }: LocationPopupProps) {
  const aez = lookupAEZZone(location.lat, location.lng);
  const { initializeFarm, farmConfig } = useFarmStore();
  const [area, setArea] = useState(5);

  const handleCreateFarm = () => {
    initializeFarm(location, area);
  };

  if (farmConfig) {
    return (
      <div className="p-3 min-w-[200px]">
        <h3 className="font-semibold text-lg text-green-700">🌾 {farmConfig.name}</h3>
        <div className="mt-2 space-y-1 text-sm">
          <p>
            <strong>Area:</strong> {farmConfig.areaHa} hectares
          </p>
          <p>
            <strong>AEZ Zone:</strong> {aez.id} - {aez.name}
          </p>
          <p>
            <strong>Rainfall:</strong> {aez.rainfallRange}
          </p>
          <p>
            <strong>Zones:</strong> {farmConfig.zones.length} defined
          </p>
        </div>
        <div className="mt-3 pt-2 border-t">
          <p className="text-xs text-gray-500">
            Lat: {location.lat.toFixed(4)}, Lng: {location.lng.toFixed(4)}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-3 min-w-[250px]">
      <h3 className="font-semibold text-lg">📍 New Farm Location</h3>

      <div className="mt-2 space-y-1 text-sm">
        <p>
          <strong>AEZ Zone:</strong> {aez.id} - {aez.name}
        </p>
        <p>
          <strong>Expected Rainfall:</strong> {aez.rainfallRange}
        </p>
        <p className="text-gray-600">{aez.description}</p>
      </div>

      <div className="mt-3">
        <label className="block text-sm font-medium text-gray-700">
          Farm Size (hectares)
        </label>
        <input
          type="number"
          min={0.5}
          max={100}
          step={0.5}
          value={area}
          onChange={(e) => setArea(Number(e.target.value))}
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-green-500 focus:ring-green-500 text-sm p-2 border"
        />
      </div>

      <button
        onClick={handleCreateFarm}
        className="mt-3 w-full bg-green-600 text-white py-2 px-4 rounded-md hover:bg-green-700 transition-colors font-medium"
      >
        Create Farm Here
      </button>

      <p className="mt-2 text-xs text-gray-500">
        Coordinates: {location.lat.toFixed(4)}, {location.lng.toFixed(4)}
      </p>
    </div>
  );
}

// ============================================================================
// Drawing Mode Panel
// ============================================================================

interface DrawingModePanelProps {
  activeMode: string | null;
  onModeChange: (mode: string | null) => void;
}

function DrawingModePanel({ activeMode, onModeChange }: DrawingModePanelProps) {
  const modes = [
    { id: "crops", label: "Crop Zone", icon: "🌾", color: "bg-green-500" },
    { id: "pasture", label: "Pasture", icon: "🐄", color: "bg-yellow-500" },
    { id: "buildings", label: "Buildings", icon: "🏠", color: "bg-gray-500" },
    { id: "water", label: "Water", icon: "💧", color: "bg-blue-500" },
  ];

  return (
    <div className="absolute top-4 left-4 z-[1000] bg-white rounded-lg shadow-lg p-2">
      <p className="text-xs font-medium text-gray-500 mb-2 px-2">Draw Zone</p>
      <div className="flex flex-col gap-1">
        {modes.map((mode) => (
          <button
            key={mode.id}
            onClick={() => onModeChange(activeMode === mode.id ? null : mode.id)}
            className={`flex items-center gap-2 px-3 py-2 rounded-md text-sm transition-colors ${
              activeMode === mode.id
                ? `${mode.color} text-white`
                : "hover:bg-gray-100"
            }`}
          >
            <span>{mode.icon}</span>
            <span>{mode.label}</span>
          </button>
        ))}
      </div>
      {activeMode && (
        <p className="text-xs text-gray-500 mt-2 px-2">
          Click map corners to draw
        </p>
      )}
    </div>
  );
}

// ============================================================================
// Main Map Component
// ============================================================================

export default function FarmMap() {
  const {
    mapCenter,
    mapZoom,
    selectedLocation,
    farmConfig,
    addZone,
    mapMode,
  } = useFarmStore();
  const [mounted, setMounted] = useState(false);
  const [drawingMode, setDrawingMode] = useState<string | null>(null);

  useEffect(() => {
    setMounted(true);
  }, []);

  const handleZoneCreated = (zone: FarmZone) => {
    addZone(zone);
    setDrawingMode(null);
  };

  if (!mounted) {
    return (
      <div className="w-full h-full bg-gray-100 flex items-center justify-center">
        <div className="flex flex-col items-center gap-2">
          <div className="animate-spin rounded-full h-8 w-8 border-2 border-green-500 border-t-transparent" />
          <span className="text-gray-500">Loading map...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="relative w-full h-full">
      <MapContainer
        center={[mapCenter.lat, mapCenter.lng]}
        zoom={mapZoom}
        className="w-full h-full"
        zoomControl={false}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        <MapEventHandler />
        <MapPositionSync />

        {/* Drawing controls when farm exists */}
        {farmConfig && drawingMode && (
          <DrawingControls
            onZoneCreated={handleZoneCreated}
            drawingMode={drawingMode}
          />
        )}

        {/* Farm location marker */}
        {farmConfig && (
          <Marker
            position={[farmConfig.location.lat, farmConfig.location.lng]}
            icon={farmIcon}
          >
            <Popup>
              <LocationPopup location={farmConfig.location} />
            </Popup>
          </Marker>
        )}

        {/* Selected location marker (before farm is created) */}
        {selectedLocation && !farmConfig && (
          <Marker
            position={[selectedLocation.lat, selectedLocation.lng]}
            icon={customIcon}
          >
            <Popup>
              <LocationPopup location={selectedLocation} />
            </Popup>
          </Marker>
        )}

        {/* Farm zones */}
        {farmConfig && farmConfig.zones.length > 0 && (
          <ZoneRenderer zones={farmConfig.zones} />
        )}
      </MapContainer>

      {/* Drawing mode panel */}
      {farmConfig && (
        <DrawingModePanel
          activeMode={drawingMode}
          onModeChange={setDrawingMode}
        />
      )}

      {/* Zone count badge */}
      {farmConfig && farmConfig.zones.length > 0 && (
        <div className="absolute bottom-4 left-4 z-[1000] bg-white rounded-lg shadow-lg px-3 py-2">
          <span className="text-sm font-medium">
            {farmConfig.zones.length} zone{farmConfig.zones.length !== 1 ? "s" : ""} defined
          </span>
        </div>
      )}
    </div>
  );
}
