"use client";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card, EvidenceBadge, LabelTag, RiskBadge, State, useFetch } from "@/components/ui";
import { api, fmtDate, rupees, type FlagRow, type Label } from "@/lib/api";
import { useT } from "@/lib/i18n";

interface Summary {
  centre: { id: string; name: string; state: string; district: string; label: Label };
  risk: { risk: number; reasons: { flag_id: number; type: string; explanation: string }[]; rupees_at_risk: number; unverified_trainee_hours: number; evidence_level: "FULL" | "REDUCED" | "INSUFFICIENT" | null };
  score_trend: { date: string; score: number }[]; inspections: string[];
  batches: { batch_id: string; date: string; score: number | null; status: string; evidence_level: "FULL" | "REDUCED" | "INSUFFICIENT"; unverified_trainee_hours: number | null; label: Label }[];
  assets: { asset_id: string; oai: number | null; flag: boolean; detail: string; identity: [string, number][]; label: Label }[];
  inventory: { batch: string; item: string; sanctioned: number; observed: number; source_note: string; label: Label }[];
  integrity: { ts: number; cam: string; kind: string; label: Label }[];
  clock: { ts: number; drift: number }[];
  flags: FlagRow[];
}

function Centre() {
  const id = useSearchParams().get("id") ?? "";
  const { t } = useT();
  const { data, error } = useFetch(() => api<Summary>(`/v1/centres/${id}/summary`), [id]);
  if (!data) return <State error={error} loading />;
  const trend = data.score_trend.slice(-30);
  return (
    <>
      <Card>
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-xl font-bold">{data.centre.id} — {data.centre.name}</h1><LabelTag label={data.centre.label} />
          <span className="text-slate-500">{data.centre.district}, {data.centre.state}</span>
          <span className="ml-auto flex items-center gap-2"><RiskBadge risk={data.risk.risk} /><EvidenceBadge level={data.risk.evidence_level} />
            <span className="font-semibold">{rupees(data.risk.rupees_at_risk)}</span><LabelTag label="simulated" /></span>
        </div>
      </Card>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title={t("centre.trend")} right={<span className="text-xs text-slate-500">H3</span>}>
          {trend.length ? <ResponsiveContainer width="100%" height={220}>
            <LineChart data={trend}><CartesianGrid stroke="#eee" /><XAxis dataKey="date" fontSize={10} /><YAxis domain={[0, 100]} fontSize={10} />
              <Tooltip />{data.inspections.filter((d) => trend.some((p) => p.date === d)).map((d) =>
                <ReferenceLine key={d} x={d} stroke="#CC79A7" strokeDasharray="4 2" label={{ value: "▼ audit", fontSize: 10, fill: "#8a3f6b" }} />)}
              <Line dataKey="score" stroke="#0072B2" dot={{ r: 2 }} /></LineChart></ResponsiveContainer>
            : <p className="text-slate-500">{t("common.none")}</p>}
        </Card>
        <Card title={t("centre.flags")}>
          <table><thead><tr><th>{t("common.date")}</th><th>{t("common.type")}</th><th>{t("queue.evidence")}</th><th>{t("common.status")}</th></tr></thead>
            <tbody>{data.flags.slice(0, 12).map((f) => <tr key={f.id}>
              <td>{f.date}</td><td><Link className="text-[#0072B2] underline" href={`/flag/?id=${f.id}`}>{f.type}</Link> <LabelTag label={f.label} />
                <div className="text-xs text-slate-500">{f.explanation}</div></td>
              <td><EvidenceBadge level={f.evidence_level} /></td><td>{t("status." + f.status)}</td></tr>)}</tbody></table>
        </Card>
        <Card title={t("centre.batches")}>
          <table><thead><tr><th>Batch</th><th>{t("common.date")}</th><th>{t("common.score")}</th><th>{t("queue.evidence")}</th><th>{t("common.status")}</th></tr></thead>
            <tbody>{data.batches.slice(0, 14).map((b) => <tr key={b.batch_id + b.date}>
              <td><Link className="text-[#0072B2] underline" href={`/batch/?id=${b.batch_id}&date=${b.date}`}>{b.batch_id}</Link></td><td>{b.date}</td>
              <td>{b.score ?? "—"}</td><td><EvidenceBadge level={b.evidence_level} /></td>
              <td className="text-xs">{b.status.replace("_", " ")} <LabelTag label={b.label} /></td></tr>)}</tbody></table>
        </Card>
        <Card title={t("centre.assets")}>
          {data.assets.length ? <table><thead><tr><th>Asset</th><th>OAI</th><th>Identity (DINOv2 cos)</th></tr></thead>
            <tbody>{data.assets.map((a) => <tr key={a.asset_id}><td>{a.asset_id} <LabelTag label={a.label} /></td>
              <td>{a.oai ?? "—"} {a.flag && <span className="text-[#D55E00]">▲</span>}<div className="text-xs text-slate-500">{a.detail}</div></td>
              <td className="text-xs">{a.identity.slice(-5).map(([d, v]) => `${d.slice(5)}: ${v}`).join(" · ") || "—"}</td></tr>)}</tbody></table>
            : <p className="text-slate-500">{t("common.none")}</p>}
          <h3 className="mb-1 mt-4 text-sm font-semibold">{t("centre.inventory")} <LabelTag label="mock" /></h3>
          <table><tbody>{data.inventory.map((r, i) => <tr key={i}><td>{r.item}</td>
            <td className={r.observed < r.sanctioned ? "font-semibold text-[#D55E00]" : ""}>{r.observed} / {r.sanctioned}{r.observed < r.sanctioned ? " ▲" : ""}</td>
            <td className="text-xs text-slate-500">{r.source_note}</td></tr>)}</tbody></table>
        </Card>
        <Card title={t("centre.integrity")}>
          <ul className="max-h-56 space-y-1 overflow-auto text-sm">{data.integrity.slice(-40).reverse().map((e, i) =>
            <li key={i}><span className="font-mono text-xs">{fmtDate(e.ts)}</span> · {e.cam} · <b>{e.kind}</b> <LabelTag label={e.label} /></li>)}
            {!data.integrity.length && <li className="text-slate-500">{t("common.none")}</li>}</ul>
        </Card>
        <Card title={t("centre.clock")}>
          {data.clock.length ? <ResponsiveContainer width="100%" height={200}>
            <LineChart data={data.clock.map((c) => ({ ...c, time: fmtDate(c.ts) }))}><CartesianGrid stroke="#eee" />
              <XAxis dataKey="time" fontSize={9} /><YAxis fontSize={10} /><Tooltip />
              <ReferenceLine y={120} stroke="#D55E00" strokeDasharray="3 3" /><ReferenceLine y={-120} stroke="#D55E00" strokeDasharray="3 3" />
              <Line dataKey="drift" stroke="#0072B2" dot={false} /></LineChart></ResponsiveContainer>
            : <p className="text-slate-500">{t("common.none")}</p>}
        </Card>
      </div>
    </>
  );
}

export default function Page() { return <Suspense><Centre /></Suspense>; }
