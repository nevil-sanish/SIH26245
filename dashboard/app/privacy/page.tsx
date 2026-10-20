"use client";
import { Card, LabelTag, State, useFetch } from "@/components/ui";
import { api, session, type Label } from "@/lib/api";
import { useT } from "@/lib/i18n";

interface Priv { stored: { data: string; where: string; retention: string; label: Label }[]; never: string[]; thumbnails_held: number }
interface Audit { ts: string; user: string; role: string; action: string; target: string }

export default function Privacy() {
  const { t } = useT();
  const p = useFetch(() => api<Priv>("/v1/privacy"));
  const canAudit = ["admin", "state_monitor"].includes(session()?.role ?? "");
  const a = useFetch(() => (canAudit ? api<Audit[]>("/v1/audit-log") : Promise.resolve([] as Audit[])));
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card title={t("priv.title")}>
        <State error={p.error} loading={!p.data && !p.error} />
        {p.data && <><table><thead><tr><th>Data</th><th>Where</th><th>Retention</th></tr></thead>
          <tbody>{p.data.stored.map((s) => <tr key={s.data}><td>{s.data} <LabelTag label={s.label} /></td><td>{s.where}</td><td>{s.retention}</td></tr>)}</tbody></table>
          <p className="mt-2 text-sm">Face-blurred thumbnails currently held: <b>{p.data.thumbnails_held}</b></p>
          <h3 className="mt-3 font-semibold">{t("priv.never")}</h3>
          <ul className="list-disc pl-5 text-sm">{p.data.never.map((n) => <li key={n}>{n}</li>)}</ul>
          <p className="mt-2 text-xs"><a className="text-[#0072B2] underline" href="https://github.com/nevil-sanish/SIH26245/blob/main/docs/PRIVACY_DESIGN.md">docs/PRIVACY_DESIGN.md</a></p></>}
      </Card>
      {canAudit && <Card title={t("priv.audit")}>
        <table><thead><tr><th>Time</th><th>User</th><th>Action</th><th>Target</th></tr></thead>
          <tbody>{a.data?.map((r, i) => <tr key={i} className="text-xs"><td>{r.ts.slice(0, 19)}</td><td>{r.user} ({r.role})</td><td>{r.action}</td><td>{r.target}</td></tr>)}</tbody></table>
      </Card>}
    </div>
  );
}
