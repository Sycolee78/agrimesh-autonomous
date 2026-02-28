"use client";

import { useEffect, useState } from "react";
import { MapContainer, TileLayer, Marker, Popup, useMapEvents, useMap, Polygon } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { useFarmStore } from "@/store/farmStore";
import type { Coordinates, FarmZone } from "@/types/farm";
import { lookupAEZZone } from "@/lib/api";

// Fix Leaflet icon issue in Next.js
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
  iconUrl: "data:image/svg+xml," + encodeURIComponent(`
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
// Map Event Handler
// ============================================================================

function MapEventHandler() {
  const { mapMode, selectLocation, initializeFarm, farmConfig } = useFarmStore();

  useMapEvents({
    click: (e) => {
      if (mapMode === "view" || mapMode === "select") {
        const coords: Coordinates = { lat: e.latlng.lat, lng: e.latlng.lng };
        
        if (!farmConfig) {
          // First click initializes the farm
          initializeFarm(coords, 5); // Default 5 hectares
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
}

function ZoneRenderer({ zones }: ZoneRendererProps) {
  const zoneColors: Record<string, string> = {
    crops: "#22c55e",
    pasture: "#eab308",
    buildings: "#64748b",
    water: "#3b82f6",
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
        >
          <Popup>
            <div className="p-2">
              <h3 className="font-semibold capitalize">{zone.type} Zone</h3>
              {zone.label && <p className="text-sm text-gray-600">{zone.label}</p>}
              {zone.cropType && <p className="text-sm">Crop: {zone.cropType}</p>}
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
          <p><strong>Area:</strong> {farmConfig.areaHa} hectares</p>
          <p><strong>AEZ Zone:</strong> {aez.id} - {aez.name}</p>
          <p><strong>Rainfall:</strong> {aez.rainfallRange}</p>
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
        <p><strong>AEZ Zone:</strong> {aez.id} - {aez.name}</p>
        <p><strong>Expected Rainfall:</strong> {aez.rainfallRange}</p>
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
// Main Map Component
// ============================================================================

export default function FarmMap() {
  const { mapCenter, mapZoom, selectedLocation, farmConfig } = useFarmStore();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return (
      <div className="w-full h-full bg-gray-100 flex items-center justify-center">
        <div className="text-gray-500">Loading map...</div>
      </div>
    );
  }

  return (
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

      {/* Farm location marker */}
      {farmConfig && (
        <Marker position={[farmConfig.location.lat, farmConfig.location.lng]} icon={farmIcon}>
          <Popup>
            <LocationPopup location={farmConfig.location} />
          </Popup>
        </Marker>
      )}

      {/* Selected location marker (before farm is created) */}
      {selectedLocation && !farmConfig && (
        <Marker position={[selectedLocation.lat, selectedLocation.lng]} icon={customIcon}>
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
  );
}
