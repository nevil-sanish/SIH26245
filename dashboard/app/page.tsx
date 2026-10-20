"use client";
import Link from "next/link";
import IndiaMap from "@/components/IndiaMap";
import { Card, EvidenceBadge, LabelTag, RiskBadge, RISK, State, Stat, useFetch } from "@/components/ui";
import { api, rupees, type CentreRow } from "@/lib/api";
import { useT } from "@/lib/i18n";

export default function Overview() {
  const { t } = useT();
  const { data, error } = useFetch(() => api<CentreRow[]>("/v1/centres"));
  if (!data) return <State error={error} loading />;
  const sum = (k: keyof CentreRow) => data.reduce((a, c) => a + Number(c[k] || 0), 0);
  return (
    <>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label={t("overview.centres")} value={data.length} />
        <Stat label={t("overview.flags")} value={sum("open_flags")} />
        <Stat label={t("overview.rupees")} value={rupees(sum("rupees_at_risk"))} tag={<LabelTag label="simulated" />} />
        <Stat label={t("overview.gaps")} value={sum("data_gaps")} />
      </div>
      <div className="grid gap-4 md:grid-cols-[minmax(0,420px)_1fr]">
        <Card title={t("overview.map")}>
          <IndiaMap centres={data} />
          <ul className="mt-2 flex gap-3 text-sm" aria-label="legend">
            {(["high", "medium", "low"] as const).map((k) => <li key={k} className="flex items-center gap-1">
              <span style={{ color: RISK[k].color }} aria-hidden>{RISK[k].icon}</span>{t("risk." + k)}</li>)}
          </ul>
        </Card>
        <Card title={t("nav.queue")}>
          <table><thead><tr><th>{t("queue.centre")}</th><th>{t("queue.risk")}</th><th>{t("queue.evidence")}</th><th>{t("queue.reasons")}</th></tr></thead>
            <tbody>{[...data].sort((a, b) => b.risk - a.risk).slice(0, 8).map((c) => (
              <tr key={c.id}><td><Link className="font-medium text-[#0072B2] underline" href={`/centre/?id=${c.id}`}>{c.id}</Link>
                <div className="text-xs text-slate-500">{c.name} · {c.district}, {c.state}</div></td>
                <td><RiskBadge risk={c.risk} /></td><td><EvidenceBadge level={c.evidence_level} /></td>
                <td className="text-xs">{c.reasons[0]?.explanation ?? "—"}</td></tr>))}</tbody></table>
        </Card>
      </div>
    </>
  );
}
