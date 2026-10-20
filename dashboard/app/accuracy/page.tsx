"use client";
import { useState } from "react";
import { Card, LabelTag, State, Stat, useFetch } from "@/components/ui";
import { api, API, type Label } from "@/lib/api";
import { useT } from "@/lib/i18n";

interface Conf { kind: "fraud" | "honest"; name: string; n: number; TP?: number; FN?: number; TN?: number; FP?: number; label: Label; fired?: string[]; false_flags?: string[] }
interface Acc {
  generated: string; overall: { fraud_fn_rate: number; honest_fp_rate: number }; confusion: Record<string, Conf>;
  door?: { any_direction: { precision: number; recall: number } }; count_door_clip?: { mae: number };
  robustness?: { variant: string; fps_measured: number; door_any: { precision: number; recall: number }; count: { mae: number } }[];
  bandwidth?: Record<string, { whisper_KB_per_hour: number | null; observed_KB_per_hour: number }>;
}

export default function Accuracy() {
  const { t } = useT();
  const { data, error, reload } = useFetch(() => api<Acc>("/v1/accuracy"));
  const [running, setRunning] = useState(false);
  const run = async () => { setRunning(true); try { await api("/v1/redteam/run?seeds=10", { method: "POST" }); } finally { setRunning(false); reload(); } };
  return (
    <>
      <Card title={t("acc.title")} right={<button onClick={run} disabled={running} className="rounded border px-3 py-1 text-sm">{running ? "…" : t("acc.run")}</button>}>
        <State error={error} loading={!data && !error} />
        {data && <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <Stat label={t("acc.fn")} value={`${(data.overall.fraud_fn_rate * 100).toFixed(1)} %`} />
          <Stat label={t("acc.fp")} value={`${(data.overall.honest_fp_rate * 100).toFixed(1)} %`} />
          {data.door && <Stat label="Door P / R" value={`${data.door.any_direction.precision} / ${data.door.any_direction.recall}`} tag={<LabelTag label="measured" />} />}
          {data.count_door_clip && <Stat label="Count MAE" value={data.count_door_clip.mae} tag={<LabelTag label="measured" />} />}
        </div>}
        <p className="mt-2 text-sm"><a className="text-[#0072B2] underline" href="https://github.com/nevil-sanish/SIH26245/blob/main/docs/ACCURACY_REPORT.md">docs/ACCURACY_REPORT.md</a> · generated {data?.generated}</p>
      </Card>
      {data && <Card title="Confusion matrices">
        <table><thead><tr><th>Scenario</th><th>Label</th><th>n</th><th>TP</th><th>FN</th><th>TN</th><th>FP</th><th>Flags</th></tr></thead>
          <tbody>{Object.entries(data.confusion).map(([k, v]) => <tr key={k}><td><b>{k}</b> {v.name}</td><td><LabelTag label={v.label} /></td><td>{v.n}</td>
            <td>{v.TP ?? "–"}</td><td className={v.FN ? "font-semibold text-[#D55E00]" : ""}>{v.FN ?? "–"}</td><td>{v.TN ?? "–"}</td>
            <td className={v.FP ? "font-semibold text-[#D55E00]" : ""}>{v.FP ?? "–"}</td><td className="text-xs">{(v.fired ?? v.false_flags ?? []).join(", ")}</td></tr>)}</tbody></table>
      </Card>}
      {data?.robustness && <Card title="Robustness (measured)">
        <table><thead><tr><th>Variant</th><th>fps</th><th>Door P</th><th>Door R</th><th>Count MAE</th></tr></thead>
          <tbody>{data.robustness.map((r) => <tr key={r.variant}><td>{r.variant}</td><td>{r.fps_measured}</td><td>{r.door_any.precision}</td><td>{r.door_any.recall}</td><td>{r.count.mae}</td></tr>)}</tbody></table>
      </Card>}
      {data?.bandwidth && <Card title="Bandwidth (measured)">
        <table><thead><tr><th>Camera</th><th>Whisper KB/h</th><th>Observed KB/h</th></tr></thead>
          <tbody>{Object.entries(data.bandwidth).map(([c, b]) => <tr key={c}><td>{c}</td><td>{b.whisper_KB_per_hour ?? "—"}</td><td>{b.observed_KB_per_hour}</td></tr>)}</tbody></table>
      </Card>}
      <p className="text-xs text-slate-500">API: {API}</p>
    </>
  );
}
