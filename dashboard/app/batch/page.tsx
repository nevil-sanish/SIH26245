"use client";
// H1 view: occupancy curve, check-in markers (matched = filled ●, unmatched = hollow ○), door entry/exit ticks,
// timetable bands (theory / practical / break). Trainer subtraction is noted.
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { CartesianGrid, ComposedChart, Line, ReferenceArea, ResponsiveContainer, Scatter, Tooltip, XAxis, YAxis } from "recharts";
import { Card, EvidenceBadge, LabelTag, State, useFetch } from "@/components/ui";
import { api, fmtTime, type Label } from "@/lib/api";
import { useT } from "@/lib/i18n";

interface Rec {
  batch_id: string; date: string; label: Label; status: string; score: number | null; evidence_level: "FULL" | "REDUCED" | "INSUFFICIENT";
  checkins: number; coverage: number; matched: [number, number][]; unmatched: number[]; entries: number[]; exits: number[];
  occupancy_curve: [number, number][]; timetable: [number, number, string][]; trainers: number;
  signals: Record<string, { value: number; flag: boolean; severity: number; detail: string }>;
  claimed_trainee_hours?: number; observed_trainee_hours?: number; unverified_trainee_hours?: number; reason?: string;
  source_data: { label: Label; enrolled: number; job_role: string };
}

const BAND = { theory: "#56B4E933", practical: "#009E7333", break: "#99999933" } as Record<string, string>;

function Batch() {
  const q = useSearchParams();
  const { t } = useT();
  const { data, error } = useFetch(() => api<Rec>(`/v1/batches/${q.get("id")}/reconciliation?date=${q.get("date")}`), [q.toString()]);
  if (!data) return <State error={error} loading />;
  const occ = data.occupancy_curve.map(([x, y]) => ({ x, occ: y }));
  const top = Math.max(data.checkins, ...occ.map((o) => o.occ), 5) + 3;
  const matched = data.matched.map(([c]) => ({ x: c, y: top - 1 }));
  const unmatched = data.unmatched.map((c) => ({ x: c, y: top - 1 }));
  const ent = data.entries.map((x) => ({ x, y: 0.6 }));
  const ex = data.exits.map((x) => ({ x, y: 0.2 }));
  const xs = [...occ.map((o) => o.x), ...data.entries, ...data.unmatched, ...data.matched.map((m) => m[0])];
  return (
    <>
      <Card>
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-xl font-bold">{t("batch.title")} — {data.batch_id} · {data.date}</h1>
          <LabelTag label={data.label} /><span className="text-sm">check-ins <LabelTag label={data.source_data.label} /></span>
          <EvidenceBadge level={data.evidence_level} />
          <span className="ml-auto text-lg font-bold">{t("batch.score")}: {data.score ?? "—"}</span>
        </div>
        <p className="mt-1 text-sm text-slate-600">{data.source_data.job_role} · enrolled {data.source_data.enrolled} · {data.checkins} check-ins ·
          coverage {(data.coverage * 100).toFixed(0)} % · {t("batch.trainers")}: {data.trainers} · status <b>{data.status.replace("_", " ")}</b>{data.reason ? ` — ${data.reason}` : ""}</p>
      </Card>
      <Card title={t("batch.curve")}>
        <ResponsiveContainer width="100%" height={340}>
          <ComposedChart margin={{ top: 10, right: 10, bottom: 10, left: 0 }}>
            <CartesianGrid stroke="#eee" />
            <XAxis type="number" dataKey="x" domain={[Math.min(...xs), Math.max(...xs)]} tickFormatter={fmtTime} fontSize={10} />
            <YAxis type="number" domain={[0, top]} fontSize={10} />
            <Tooltip labelFormatter={(v) => fmtTime(Number(v))} />
            {data.timetable.map(([s, e, k], i) => <ReferenceArea key={i} x1={s} x2={e} fill={BAND[k] ?? "#eee"} label={{ value: k, position: "insideTop", fontSize: 10 }} />)}
            <Line data={occ} dataKey="occ" name="occupancy" stroke="#0072B2" dot={false} strokeWidth={2} isAnimationActive={false} />
            <Scatter data={matched} name={t("batch.matched")} fill="#009E73" shape="circle" />
            <Scatter data={unmatched} name={t("batch.unmatched")} shape={(p: { cx?: number; cy?: number }) =>
              <circle cx={p.cx} cy={p.cy} r={5} fill="white" stroke="#D55E00" strokeWidth={2} />} />
            <Scatter data={ent} name={t("batch.entry")} fill="#56B4E9" shape="triangle" />
            <Scatter data={ex} name={t("batch.exit")} fill="#CC79A7" shape="diamond" />
          </ComposedChart>
        </ResponsiveContainer>
        <ul className="mt-2 flex flex-wrap gap-4 text-sm">
          <li><span className="text-[#009E73]">●</span> {t("batch.matched")}</li><li><span className="text-[#D55E00]">○</span> {t("batch.unmatched")}</li>
          <li><span className="text-[#56B4E9]">▲</span> {t("batch.entry")}</li><li><span className="text-[#CC79A7]">◆</span> {t("batch.exit")}</li>
          <li><span className="text-[#0072B2]">—</span> occupancy (minus nothing; trainers shown separately)</li></ul>
      </Card>
      <Card title={t("batch.signals")}>
        <table><thead><tr><th>Signal</th><th>Value</th><th>Flag</th><th>Detail</th></tr></thead>
          <tbody>{Object.entries(data.signals ?? {}).map(([k, s]) => <tr key={k}><td className="font-mono text-sm">{k}</td><td>{s.value}</td>
            <td>{s.flag ? <span className="font-semibold text-[#D55E00]">▲ yes</span> : "no"}</td><td className="text-sm">{s.detail}</td></tr>)}</tbody></table>
        {data.claimed_trainee_hours !== undefined && <p className="mt-2 text-sm">claimed {data.claimed_trainee_hours} trainee-h ·
          observed {data.observed_trainee_hours} · unverified <b>{data.unverified_trainee_hours}</b></p>}
      </Card>
    </>
  );
}

export default function Page() { return <Suspense><Batch /></Suspense>; }
