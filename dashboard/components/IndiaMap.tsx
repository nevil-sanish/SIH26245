"use client";
// Offline SVG map. Outline: Natural Earth admin-0, India point-of-view edition (public domain), simplified to
// public/india.json = {path, lon:[min,max], lat:[min,max], w, h}. Markers carry shape + colour (never colour only).
import Link from "next/link";
import { useEffect, useState } from "react";
import type { CentreRow } from "@/lib/api";
import { RISK, riskLevel } from "@/components/ui";

type Geo = { path: string; lon: [number, number]; lat: [number, number]; w: number; h: number };

export default function IndiaMap({ centres }: { centres: CentreRow[] }) {
  const [g, setG] = useState<Geo | null>(null);
  useEffect(() => { fetch("/india.json").then((r) => r.json()).then(setG).catch(() => setG(null)); }, []);
  const geo = g ?? { path: "", lon: [67.5, 98] as [number, number], lat: [6, 37.5] as [number, number], w: 600, h: 640 };
  const x = (lon: number) => ((lon - geo.lon[0]) / (geo.lon[1] - geo.lon[0])) * geo.w;
  const y = (lat: number) => ((geo.lat[1] - lat) / (geo.lat[1] - geo.lat[0])) * geo.h;
  return (
    <svg viewBox={`0 0 ${geo.w} ${geo.h}`} className="h-auto w-full max-w-md" role="img" aria-label="Map of monitored centres by risk">
      <path d={geo.path} fill="#eef2f7" stroke="#94a3b8" strokeWidth={1} />
      {centres.map((c) => {
        const lv = riskLevel(c.risk); const cx = x(c.lon), cy = y(c.lat), r = 9;
        const shape = lv === "high" ? <polygon points={`${cx},${cy - r} ${cx + r},${cy + r * 0.8} ${cx - r},${cy + r * 0.8}`} />
          : lv === "medium" ? <rect x={cx - r * 0.75} y={cy - r * 0.75} width={r * 1.5} height={r * 1.5} transform={`rotate(45 ${cx} ${cy})`} />
          : <circle cx={cx} cy={cy} r={r * 0.75} />;
        return <Link key={c.id} href={`/centre/?id=${c.id}`}>
          <g fill={RISK[lv].color} stroke="white" strokeWidth={1.5}><title>{`${c.id} ${c.name} — risk ${c.risk}`}</title>{shape}</g>
        </Link>;
      })}
    </svg>
  );
}
