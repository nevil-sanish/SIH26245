"use client";
// Evidence viewer + review workflow. Every flag: what, why, evidence level, confidence, next step. A human decides.
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { Card, EvidenceBadge, LabelTag, State, useFetch } from "@/components/ui";
import { api, fmtDate, session, type FlagRow } from "@/lib/api";
import { useT } from "@/lib/i18n";

interface Evidence extends FlagRow {
  packets: { count: number; signature_ok: number; chain_ok: number; chain_unknown: number; chain_broken: number;
    sample: { cam: string; seq: number; t: number; hash: string; prev: string; sig: string; bytes: number }[] };
  thumbnails: { t: number; cam: string; jpeg_b64: string; flags: string[] }[];
  clock: { ts: number; drift: number }[];
  case: { id: number; status: string; assigned_to: string | null; actions: { actor: string; role: string; action: string; note: string | null; ts: string }[] } | null;
}

function Flag() {
  const id = useSearchParams().get("id");
  const { t } = useT();
  const { data, error, reload } = useFetch(() => api<Evidence>(`/v1/flags/${id}`), [id]);
  const [note, setNote] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const role = session()?.role;
  const act = async (action: string) => {
    try {
      if (role === "centre_operator" && data?.case) await api(`/v1/cases/${data.case.id}/response`, { method: "POST", body: JSON.stringify({ note, action }) });
      else await api(`/v1/flags/${id}/review`, { method: "POST", body: JSON.stringify({ action, note }) });
      setNote(""); setMsg(null); reload();
    } catch (e) { setMsg(String((e as Error).message)); }
  };
  if (!data) return <State error={error} loading />;
  const m = data.links?.matches as { other_centre: string; other_t: number; hamming: number }[] | undefined;
  return (
    <>
      <Card>
        <div className="flex flex-wrap items-center gap-2">
          <h1 className="text-xl font-bold">{data.type}</h1><LabelTag label={data.label} /><EvidenceBadge level={data.evidence_level} />
          <span className="text-sm">· <Link className="text-[#0072B2] underline" href={`/centre/?id=${data.centre_id}`}>{data.centre_id}</Link> · {data.date}</span>
          <span className="ml-auto rounded bg-slate-100 px-2 py-0.5 text-sm">{t("status." + data.status)}</span>
        </div>
        <dl className="mt-3 grid gap-2 text-sm md:grid-cols-[10rem_1fr]">
          <dt className="font-semibold">{t("flag.what")}</dt><dd>{data.type.replace(/_/g, " ")} (severity {data.severity})</dd>
          <dt className="font-semibold">{t("flag.why")}</dt><dd>{data.explanation}</dd>
          <dt className="font-semibold">{t("queue.evidence")}</dt><dd><EvidenceBadge level={data.evidence_level} /></dd>
          <dt className="font-semibold">{t("flag.confidence")}</dt><dd>{data.confidence}</dd>
          <dt className="font-semibold">{t("flag.next")}</dt><dd>{data.next_step}</dd>
        </dl>
        {typeof data.links?.reconciliation === "string" && data.batch_id &&
          <Link className="mt-2 inline-block text-sm text-[#0072B2] underline" href={`/batch/?id=${data.batch_id}&date=${data.date}`}>→ {t("batch.title")}</Link>}
      </Card>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title={t("flag.evidence")}>
          <p className="text-sm"><b>{t("flag.signatures")}:</b> {data.packets.signature_ok}/{data.packets.count} Ed25519 OK ·{" "}
            <b>{t("flag.chain")}:</b> {data.packets.chain_ok} linked, {data.packets.chain_broken} broken, {data.packets.chain_unknown} awaiting neighbour</p>
          <table className="mt-2"><thead><tr><th>cam</th><th>seq</th><th>hash</th><th>prev</th><th>sig</th><th>B</th></tr></thead>
            <tbody>{data.packets.sample.map((p) => <tr key={p.cam + p.seq} className="font-mono text-xs"><td>{p.cam}</td><td>{p.seq}</td>
              <td>{p.hash}</td><td>{p.prev}</td><td>{p.sig}</td><td>{p.bytes}</td></tr>)}</tbody></table>
          {m && <ul className="mt-3 text-sm">{m.slice(0, 5).map((x, i) => <li key={i}>frame matches centre <b>{x.other_centre}</b> on {fmtDate(x.other_t)} (Hamming {x.hamming}/64)</li>)}</ul>}
          {data.clock.length > 0 && <p className="mt-3 text-sm">DVR clock drift readings: {data.clock.slice(0, 6).map((c) => `${c.drift > 0 ? "+" : ""}${Math.round(c.drift)} s`).join(", ")}</p>}
        </Card>
        <Card title={t("flag.thumbs")}>
          <div className="flex flex-wrap gap-2">{data.thumbnails.map((th, i) => <figure key={i} className="text-center text-[10px]">
            <img src={`data:image/jpeg;base64,${th.jpeg_b64}`} width={192} height={108} alt={`face-blurred frame ${th.cam} ${fmtDate(th.t)}`} style={{ imageRendering: "pixelated" }} />
            <figcaption>{th.cam} · {fmtDate(th.t)}<br />{th.flags?.join(", ")}</figcaption></figure>)}
            {!data.thumbnails.length && <p className="text-slate-500">{t("common.none")}</p>}</div>
        </Card>
        <Card title={role === "centre_operator" ? t("flag.respond") : t("flag.review")}>
          <p className="mb-2 text-sm text-slate-600">{t("flag.noauto")}</p>
          <label className="block text-sm">{t("flag.note")}<textarea className="mt-1 w-full rounded border p-2" rows={2} value={note} onChange={(e) => setNote(e.target.value)} /></label>
          <div className="mt-2 flex flex-wrap gap-2">
            {role === "centre_operator" ? <>
              <button onClick={() => act("centre_response")} className="rounded bg-[#0072B2] px-3 py-1.5 text-white" disabled={!data.case}>{t("flag.respond")}</button>
              <button onClick={() => act("appeal")} className="rounded border px-3 py-1.5" disabled={!data.case}>{t("flag.appeal")}</button></> : <>
              <button onClick={() => act("confirm")} className="rounded bg-[#D55E00] px-3 py-1.5 text-white">{t("flag.confirm")}</button>
              <button onClick={() => act("false_alarm")} className="rounded border px-3 py-1.5">{t("flag.false_alarm")}</button>
              <button onClick={() => act("request_response")} className="rounded border px-3 py-1.5">{t("flag.request")}</button></>}
          </div>
          {msg && <p role="alert" className="mt-2 text-sm text-[#D55E00]">{msg}</p>}
        </Card>
        <Card title={t("flag.history")}>
          <ol className="space-y-1 text-sm">{data.case?.actions.map((a, i) => <li key={i}><span className="font-mono text-xs">{a.ts.slice(0, 16)}</span> · <b>{a.actor}</b> ({a.role}) · {a.action}{a.note ? ` — “${a.note}”` : ""}</li>)}
            {!data.case?.actions.length && <li className="text-slate-500">{t("common.none")}</li>}</ol>
        </Card>
      </div>
    </>
  );
}

export default function Page() { return <Suspense><Flag /></Suspense>; }
