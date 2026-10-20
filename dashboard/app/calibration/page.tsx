"use client";
// S7 calibration kit. The snapshot is opened locally and never uploaded; only coordinates are saved to the camera.
import { useEffect, useRef, useState } from "react";
import { Card } from "@/components/ui";
import { api } from "@/lib/api";
import { useT } from "@/lib/i18n";

type Mode = "door" | "room" | "asset" | "roi";
type Pt = [number, number];
const COLORS: Record<Mode, string> = { door: "#D55E00", room: "#0072B2", asset: "#009E73", roi: "#CC79A7" };

export default function Calibration() {
  const { t } = useT();
  const cv = useRef<HTMLCanvasElement>(null);
  const [img, setImg] = useState<HTMLImageElement | null>(null);
  const [mode, setMode] = useState<Mode>("door");
  const [door, setDoor] = useState<Pt[]>([]); const [room, setRoom] = useState<Pt[]>([]);
  const [assets, setAssets] = useState<{ asset_id: string; label: string; zone: Pt[] }[]>([]);
  const [cur, setCur] = useState<Pt[]>([]); const [roi, setRoi] = useState<Pt[]>([]);
  const [camera, setCamera] = useState("TC0421:CAM-DOOR"); const [msg, setMsg] = useState("");

  useEffect(() => {
    const c = cv.current; if (!c) return; const g = c.getContext("2d")!;
    c.width = img?.naturalWidth ?? 1280; c.height = img?.naturalHeight ?? 720;
    g.clearRect(0, 0, c.width, c.height); if (img) g.drawImage(img, 0, 0);
    const poly = (p: Pt[], col: string, close = true) => { if (!p.length) return; g.strokeStyle = col; g.lineWidth = 3; g.beginPath();
      p.forEach(([x, y], i) => (i ? g.lineTo(x, y) : g.moveTo(x, y))); if (close) g.closePath(); g.stroke();
      p.forEach(([x, y]) => { g.fillStyle = col; g.fillRect(x - 4, y - 4, 8, 8); }); };
    poly(door, COLORS.door, false); poly(room, COLORS.room); assets.forEach((a) => poly(a.zone, COLORS.asset)); poly(cur, COLORS.asset);
    if (roi.length === 2) { g.strokeStyle = COLORS.roi; g.strokeRect(roi[0][0], roi[0][1], roi[1][0] - roi[0][0], roi[1][1] - roi[0][1]); }
  }, [img, door, room, assets, cur, roi]);

  const click = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const c = cv.current!; const r = c.getBoundingClientRect();
    const p: Pt = [Math.round((e.clientX - r.left) * c.width / r.width), Math.round((e.clientY - r.top) * c.height / r.height)];
    if (mode === "door") setDoor(door.length >= 2 ? [p] : [...door, p]);
    if (mode === "room") setRoom([...room, p]);
    if (mode === "asset") setCur([...cur, p]);
    if (mode === "roi") setRoi(roi.length >= 2 ? [p] : [...roi, p]);
  };
  const closeAsset = () => { if (cur.length >= 3) { setAssets([...assets, { asset_id: `ASSET-${assets.length + 1}`, label: "", zone: cur }]); setCur([]); } };
  const save = async () => {
    const cfg = { door_line: door.length === 2 ? door : null, room_polygon: room.length >= 3 ? room : null, assets,
      timestamp_roi: roi.length === 2 ? [roi[0][0], roi[0][1], roi[1][0] - roi[0][0], roi[1][1] - roi[0][1]] : null };
    try { await api(`/v1/cameras/${encodeURIComponent(camera)}/config`, { method: "PUT", body: JSON.stringify(cfg) }); setMsg("saved"); }
    catch (e) { setMsg(String((e as Error).message)); }
  };
  return (
    <Card title={t("calib.title")}>
      <p className="mb-2 text-sm text-slate-600">{t("calib.help")}</p>
      <div className="mb-2 flex flex-wrap items-center gap-2 text-sm">
        <input type="file" accept="image/*" aria-label="snapshot" onChange={(e) => { const f = e.target.files?.[0]; if (!f) return;
          const i = new Image(); i.onload = () => setImg(i); i.src = URL.createObjectURL(f); }} />
        {(["door", "room", "asset", "roi"] as Mode[]).map((m) => <button key={m} onClick={() => setMode(m)} aria-pressed={mode === m}
          className={`rounded border px-2 py-1 ${mode === m ? "font-semibold" : ""}`} style={{ borderColor: COLORS[m] }}>{t("calib." + m)}</button>)}
        {mode === "asset" && <button onClick={closeAsset} className="rounded border px-2 py-1">✓ close zone</button>}
        <button onClick={() => { setDoor([]); setRoom([]); setAssets([]); setCur([]); setRoi([]); }} className="rounded border px-2 py-1">{t("calib.clear")}</button>
      </div>
      <canvas ref={cv} onClick={click} className="w-full cursor-crosshair rounded border bg-slate-100" />
      {assets.map((a, i) => <label key={i} className="mt-1 mr-2 inline-block text-sm">{a.asset_id}: <input className="rounded border px-1" placeholder="lathe machine"
        value={a.label} onChange={(e) => setAssets(assets.map((x, j) => j === i ? { ...x, label: e.target.value } : x))} /></label>)}
      <div className="mt-3 flex flex-wrap items-center gap-2 text-sm">
        <label>Camera <input className="rounded border px-1" value={camera} onChange={(e) => setCamera(e.target.value)} /></label>
        <button onClick={save} className="rounded bg-[#0072B2] px-3 py-1.5 text-white">{t("calib.save")}</button><span>{msg}</span>
      </div>
      <pre className="mt-3 overflow-auto rounded bg-slate-900 p-2 text-xs text-slate-100">{`door_line: ${JSON.stringify(door)}
room_polygon: ${JSON.stringify(room)}
assets: ${JSON.stringify(assets)}
timestamp_roi: ${JSON.stringify(roi)}`}</pre>
      <p className="mt-2 text-xs text-slate-500">Placement standard: docs/CAMERA_PLACEMENT.md</p>
    </Card>
  );
}
