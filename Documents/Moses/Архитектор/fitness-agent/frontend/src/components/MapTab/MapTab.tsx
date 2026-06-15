import { useEffect, useMemo, useRef } from "react";
import { MapContainer, Marker, Popup, TileLayer } from "react-leaflet";
import L from "leaflet";
import { getToolsRegistry, ToolsRegistry } from "../../api";

// Иконки Leaflet по умолчанию ломаются в бандлерах — используем CDN-URL.
const icon = L.icon({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

export default function MapTab({ highlightRunId }: { highlightRunId: string | null }) {
  const [reg, setReg] = useStateTools();
  if (!reg) return <div style={{ color: "var(--text-muted)" }}>Загрузка карты…</div>;
  return (
    <div style={{ height: "100%", borderRadius: 8, overflow: "hidden", border: "1px solid var(--border)" }}>
      <MapContainer center={[55.7558, 37.6173]} zoom={12} style={{ height: "100%", width: "100%" }}>
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; OpenStreetMap'
        />
        {reg.places.map((p) => (
          <Marker key={p.id} position={[p.lat, p.lng]} icon={icon}>
            <Popup>
              <div style={{ minWidth: 200 }}>
                <div style={{ fontWeight: 600, marginBottom: 4 }}>{p.name}</div>
                <div style={{ fontSize: 12, color: "#555", marginBottom: 6 }}>{p.address}</div>
                <div style={{ fontSize: 12, marginBottom: 6 }}>{p.description}</div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                  {p.type.map((t) => (
                    <span
                      key={t}
                      style={{
                        fontSize: 10,
                        padding: "2px 6px",
                        background: "#dbeafe",
                        color: "#1d4ed8",
                        borderRadius: 4,
                      }}
                    >
                      {t}
                    </span>
                  ))}
                </div>
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
}

// Хук-помощник, чтобы не было дублирования useState внутри if-блока
import { useState } from "react";
function useStateTools(): [ToolsRegistry | null, (r: ToolsRegistry | null) => void] {
  const [reg, setReg] = useState<ToolsRegistry | null>(null);
  useEffect(() => {
    getToolsRegistry().then(setReg).catch(() => setReg(null));
  }, []);
  return [reg, setReg];
}
