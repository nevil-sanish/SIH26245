"use client";
import { Card, State, useFetch } from "@/components/ui";
import { api, fmtDate } from "@/lib/api";
import { useT } from "@/lib/i18n";

interface Fleet {
  cameras: { id: string; centre_id: string; cam: string; role: string; last_packet_t: number | null; online: boolean;
    unavailable_modules: string[]; packets: number; evidence: Record<string, number>; mean_bytes: number }[];
  models: Record<string, boolean>;
  edge_runs: { centre: string; camera: string; clip: string; frames: number; fps_measured: number; packets: number; mean_packet_bytes: number; unavailable: string[] }[];
  data_gaps: { id: number; centre_id: string; cam: string; start: number; end: number | null; reason: string }[];
}

export default function FleetPage() {
  const { t } = useT();
  const { data, error } = useFetch(() => api<Fleet>("/v1/health/fleet"));
  if (!data) return <State error={error} loading />;
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card title={t("fleet.cameras")}>
        <table><thead><tr><th>Camera</th><th>Status</th><th>Last packet</th><th>Evidence (last 60)</th><th>B/packet</th></tr></thead>
          <tbody>{data.cameras.map((c) => <tr key={c.id}><td>{c.id}<div className="text-xs text-slate-500">{c.role}</div></td>
            <td>{c.online ? <span className="text-[#009E73]">● {t("fleet.online")}</span> : <span className="text-slate-500">○ {t("fleet.offline")}</span>}
              {c.unavailable_modules.map((m) => <div key={m} className="text-xs text-[#D55E00]">▲ {m}: {t("fleet.unavailable")}</div>)}</td>
            <td className="text-xs">{c.last_packet_t ? fmtDate(c.last_packet_t) : "—"}</td>
            <td className="text-xs">OK {c.evidence.OK ?? 0} · INSUFF. {c.evidence.INSUFFICIENT ?? 0}</td><td>{c.mean_bytes}</td></tr>)}</tbody></table>
      </Card>
      <Card title={t("fleet.models")}>
        <ul className="text-sm">{Object.entries(data.models).map(([m, ok]) => <li key={m}>{ok ? <span className="text-[#009E73]">■ {t("fleet.available")}</span>
          : <span className="text-[#D55E00]">□ {t("fleet.unavailable")}</span>} — <span className="font-mono">{m}</span></li>)}</ul>
        <h3 className="mb-1 mt-4 text-sm font-semibold">{t("fleet.runs")}</h3>
        <table><thead><tr><th>Centre</th><th>Clip</th><th>fps</th><th>Packets</th><th>B</th></tr></thead>
          <tbody>{data.edge_runs.map((r, i) => <tr key={i}><td>{r.centre} · {r.camera}</td><td className="text-xs">{r.clip}</td><td>{r.fps_measured}</td>
            <td>{r.packets}</td><td>{r.mean_packet_bytes}</td></tr>)}</tbody></table>
      </Card>
      <Card title={t("fleet.gaps")}>
        <ul className="text-sm">{data.data_gaps.map((g) => <li key={g.id}>{g.centre_id}:{g.cam} · {g.reason} · {fmtDate(g.start)} → {g.end ? fmtDate(g.end) : "…"}</li>)}
          {!data.data_gaps.length && <li className="text-slate-500">{t("common.none")}</li>}</ul>
      </Card>
    </div>
  );
}
