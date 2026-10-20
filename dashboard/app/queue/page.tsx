"use client";
import Link from "next/link";
import { useState } from "react";
import { Card, EvidenceBadge, LabelTag, RiskBadge, State, useFetch } from "@/components/ui";
import { api, rupees, type CentreRow } from "@/lib/api";
import { useT } from "@/lib/i18n";

export default function Queue() {
  const { t } = useT();
  const { data, error } = useFetch(() => api<CentreRow[]>("/v1/risk-queue"));
  const [assigned, setAssigned] = useState<Record<string, string>>({});
  const [who, setWho] = useState<Record<string, string>>({});
  const assign = async (c: CentreRow) => {
    const name = who[c.id] || "inspector1";
    for (const r of c.reasons) await api(`/v1/flags/${r.flag_id}/review`, { method: "POST", body: JSON.stringify({ action: "assign", assignee: who }) });
    setAssigned({ ...assigned, [c.id]: name });
  };
  if (!data) return <State error={error} loading />;
  return (
    <Card title={t("queue.title")}>
      <div className="overflow-x-auto"><table>
        <thead><tr><th>#</th><th>{t("queue.centre")}</th><th>{t("queue.risk")}</th><th>{t("queue.evidence")}</th><th>{t("queue.rupees")}</th>
          <th>{t("queue.reasons")}</th><th>{t("queue.last")}</th><th></th></tr></thead>
        <tbody>{data.map((c, i) => (
          <tr key={c.id}>
            <td>{i + 1}</td>
            <td><Link className="font-medium text-[#0072B2] underline" href={`/centre/?id=${c.id}`}>{c.id}</Link>
              <div className="text-xs text-slate-500">{c.name}<br />{c.district}, {c.state}</div>
              <div className="mt-1 flex gap-1">{c.flag_labels.map((l) => <LabelTag key={l} label={l} />)}</div></td>
            <td><RiskBadge risk={c.risk} /><div className="text-xs text-slate-500">{c.open_flags} flags</div></td>
            <td><EvidenceBadge level={c.evidence_level} /></td>
            <td>{rupees(c.rupees_at_risk)}<div className="text-xs text-slate-500">{c.unverified_trainee_hours} unverified trainee-h</div></td>
            <td><ol className="list-decimal space-y-1 pl-4 text-xs">{c.reasons.map((r) => (
              <li key={r.flag_id}><Link className="text-[#0072B2] underline" href={`/flag/?id=${r.flag_id}`}>{r.type}</Link> — {r.explanation}{" "}
                <EvidenceBadge level={r.evidence_level} /></li>))}</ol></td>
            <td>{c.last_inspection ?? "—"}</td>
            <td>{assigned[c.id] ? <span className="text-sm">{t("queue.assigned")}: {assigned[c.id]}</span>
              : <div className="flex flex-col gap-1">
                  <input aria-label={t("queue.assign")} placeholder="inspector1" className="w-28 rounded border px-1 text-sm"
                    value={who[c.id] ?? ""} onChange={(e) => setWho({ ...who, [c.id]: e.target.value })} />
                  <button onClick={() => assign(c)} className="rounded border px-2 py-1 text-sm">{t("queue.assign")}</button></div>}</td>
          </tr>))}</tbody></table></div>
    </Card>
  );
}
