import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useCivic } from "../../i18n/civic";
import type { IssueSummary } from "../../types/civic";
import { LEVEL_COLOR, btnSecondary } from "./ui";

/** Leaflet map of issues. Loaded only when the viewer asks (tiles come from a third party). */
export function HotspotMap({ issues }: { issues: IssueSummary[] }) {
  const { c } = useCivic();
  const [show, setShow] = useState(false);
  const [failed, setFailed] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (!show || !ref.current) return;
    let map: import("leaflet").Map | undefined;
    let cancelled = false;
    Promise.all([import("leaflet"), import("leaflet/dist/leaflet.css")])
      .then(([L]) => {
        if (cancelled || !ref.current) return;
        const pts = issues.filter((i) => i.lat !== null && i.lng !== null);
        map = L.map(ref.current, { scrollWheelZoom: false }).setView([21.5, 79], 5);
        L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
          maxZoom: 12,
          attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        }).addTo(map);
        for (const i of pts) {
          L.circleMarker([i.lat!, i.lng!], {
            radius: 6 + Math.min(18, Math.sqrt(i.report_count) * 1.5),
            color: LEVEL_COLOR[i.priority_level],
            fillColor: LEVEL_COLOR[i.priority_level],
            fillOpacity: 0.55,
            weight: i.hotspot ? 3 : 1,
          })
            .bindTooltip(`${i.category_label} · ${i.locality ?? ""} ${i.district} · ${i.priority_score ?? "–"}/100`)
            .on("click", () => navigate(`/dev/hotspots/${i.id}`))
            .addTo(map);
        }
        if (pts.length) map.fitBounds(L.latLngBounds(pts.map((i) => [i.lat!, i.lng!] as [number, number])).pad(0.3));
      })
      .catch(() => setFailed(true));
    return () => {
      cancelled = true;
      map?.remove();
    };
  }, [show, issues, navigate]);

  if (!show) {
    return (
      <div className="rounded-md bg-surface-low p-3 text-sm">
        <p>{c.mapNotice}</p>
        <button type="button" onClick={() => setShow(true)} className={`${btnSecondary} mt-2`}>{c.showMap}</button>
      </div>
    );
  }
  if (failed) return <p role="alert" className="text-sm text-red-700">{c.errorGeneric}</p>;
  return <div ref={ref} className="h-80 w-full rounded-md border border-line sm:h-96" role="region" aria-label={c.hotspots} />;
}
