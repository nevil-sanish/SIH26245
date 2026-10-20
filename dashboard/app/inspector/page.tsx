"use client";
// Mobile-first inspector app. Today's visits are cached in localStorage so the page works offline in the field;
// on-site checks are kept locally and synced as flag notes when back online.
import { useEffect, useState } from "react";
import { Card, EvidenceBadge, RiskBadge } from "@/components/ui";
import { api, type CentreRow } from "@/lib/api";
import { useT } from "@/lib/i18n";

type Visit = CentreRow & { checklist: { flag_id: number; type: string; check: string; what: string }[] };

export default function Inspector() {
  const { t } = useT();
  const [visits, setVisits] = useState<Visit[] | null>(null);
  const [offline, setOffline] = useState(false);
  const [done, setDone] = useState<Record<number, boolean>>({});
  useEffect(() => {
    if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {});
    try { setDone(JSON.parse(localStorage.getItem("inspector.done") ?? "{}")); } catch {}
    api<Visit[]>("/v1/inspector/today").then((v) => { setVisits(v); try { localStorage.setItem("inspector.visits", JSON.stringify(v)); } catch {} })
      .catch(() => { try { setVisits(JSON.parse(localStorage.getItem("inspector.visits") ?? "[]")); setOffline(true); } catch { setVisits([]); } });
  }, []);
  const toggle = (id: number) => {
    const d = { ...done, [id]: !done[id] }; setDone(d);
    try { localStorage.setItem("inspector.done", JSON.stringify(d)); } catch {}
    if (d[id]) api(`/v1/flags/${id}/review`, { method: "POST", body: JSON.stringify({ action: "site_check", note: "checked on site" }) }).catch(() => {});
  };
  if (!visits) return <p>{t("common.loading")}</p>;
  return (
    <div className="mx-auto max-w-xl space-y-3">
      <h1 className="text-xl font-bold">{t("inspector.title")}</h1>
      {offline && <p className="rounded bg-[#E69F00]/20 p-2 text-sm">{t("inspector.offline")}</p>}
      {visits.map((v, i) => (
        <Card key={v.id} title={`${i + 1}. ${v.id} — ${v.name}`} right={<RiskBadge risk={v.risk} />}>
          <p className="text-sm text-slate-600">{v.district}, {v.state} · <EvidenceBadge level={v.evidence_level} /></p>
          <h3 className="mt-2 text-sm font-semibold">{t("inspector.checklist")}</h3>
          <ul className="mt-1 space-y-2">{v.checklist.map((c) => (
            <li key={c.flag_id}><label className="flex gap-2 text-sm">
              <input type="checkbox" className="mt-1 h-5 w-5" checked={!!done[c.flag_id]} onChange={() => toggle(c.flag_id)} />
              <span><b>{c.type}</b> — {c.check}<br /><span className="text-xs text-slate-500">{c.what}</span></span></label></li>))}</ul>
        </Card>))}
    </div>
  );
}
