"use client";
// Shared UI. Colour-blind-safe (Okabe–Ito) and never colour-only: every risk/evidence state also has an icon + text.
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import { logout, session, type Evidence, type Label } from "@/lib/api";
import { useT } from "@/lib/i18n";

export const RISK = {
  high: { color: "#D55E00", icon: "▲", min: 60 },
  medium: { color: "#E69F00", icon: "◆", min: 30 },
  low: { color: "#0072B2", icon: "●", min: 0 },
} as const;

export function riskLevel(r: number) { return r >= RISK.high.min ? "high" : r >= RISK.medium.min ? "medium" : "low"; }

export function RiskBadge({ risk }: { risk: number }) {
  const { t } = useT();
  const lv = riskLevel(risk);
  return (
    <span className="inline-flex items-center gap-1 rounded px-2 py-0.5 text-sm font-semibold text-white"
      style={{ background: RISK[lv].color }} aria-label={`${t("queue.risk")} ${risk} ${t("risk." + lv)}`}>
      <span aria-hidden>{RISK[lv].icon}</span>{Math.round(risk)} · {t("risk." + lv)}
    </span>
  );
}

const EV = { FULL: { icon: "■", cls: "border-[#009E73] text-[#00785a]" },
             REDUCED: { icon: "◧", cls: "border-[#E69F00] text-[#9a6a00]" },
             INSUFFICIENT: { icon: "□", cls: "border-slate-500 text-slate-600" } };

export function EvidenceBadge({ level }: { level: Evidence | null | undefined }) {
  const { t } = useT();
  if (!level) return <span className="text-slate-400">—</span>;
  return <span className={`inline-flex items-center gap-1 rounded border px-1.5 text-xs font-medium ${EV[level].cls}`}>
    <span aria-hidden>{EV[level].icon}</span>{t("ev." + level)}</span>;
}

const LB = { measured: "bg-[#009E73]/15 text-[#00684f]", simulated: "bg-[#CC79A7]/20 text-[#8a3f6b]", mock: "bg-slate-200 text-slate-700" };
export function LabelTag({ label }: { label: Label }) {
  const { t } = useT();
  return <span title={t("label.help")} className={`rounded px-1.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide ${LB[label]}`}>
    {t("label." + label)}</span>;
}

export function Card({ title, children, right }: { title?: string; children: ReactNode; right?: ReactNode }) {
  return <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
    {title && <div className="mb-3 flex items-center justify-between gap-2"><h2 className="font-semibold text-slate-800">{title}</h2>{right}</div>}
    {children}
  </section>;
}

export function useFetch<T>(fn: () => Promise<T>, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const reload = () => fn().then(setData).catch((e) => setError(String(e.message ?? e)));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { reload(); }, deps);
  return { data, error, reload };
}

export function State({ error, loading }: { error?: string | null; loading?: boolean }) {
  const { t } = useT();
  if (error) return <p role="alert" className="text-[#D55E00]">{t("common.error")}: {error}</p>;
  if (loading) return <p className="text-slate-500">{t("common.loading")}</p>;
  return null;
}

const NAV = [["/", "nav.overview"], ["/queue/", "nav.queue"], ["/inspector/", "nav.inspector"], ["/fleet/", "nav.fleet"],
             ["/calibration/", "nav.calibration"], ["/accuracy/", "nav.accuracy"], ["/privacy/", "nav.privacy"]] as const;

export function Shell({ children }: { children: ReactNode }) {
  const { t, lang, setLang } = useT();
  const path = usePathname();
  const [s, setS] = useState<ReturnType<typeof session>>(null);
  useEffect(() => {
    const cur = session();
    setS(cur);
    if (!cur && !path.startsWith("/login")) location.href = "/login/";
  }, [path]);
  if (path.startsWith("/login")) return <>{children}</>;
  return (
    <div className="min-h-screen bg-slate-50">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:bg-white focus:p-2">Skip to content</a>
      <header className="border-b bg-white">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-4 gap-y-2 px-4 py-2">
          <Link href="/" className="text-lg font-bold text-[#0072B2]">{t("app")}</Link>
          <nav aria-label="main" className="flex flex-wrap gap-1 text-sm">
            {NAV.filter(([h]) => s?.role !== "centre_operator" || ["/", "/calibration/", "/privacy/"].includes(h)).map(([h, k]) => (
              <Link key={h} href={h} aria-current={path === h ? "page" : undefined}
                className={`rounded px-2 py-1 hover:bg-slate-100 focus-visible:outline focus-visible:outline-2 ${path === h ? "bg-slate-100 font-semibold" : ""}`}>{t(k)}</Link>))}
          </nav>
          <div className="ml-auto flex items-center gap-2 text-sm">
            <span className="text-slate-500">{s?.user} · {s?.role}</span>
            <button onClick={() => setLang(lang === "en" ? "hi" : "en")} className="rounded border px-2 py-1" aria-label="language">
              {lang === "en" ? "हिन्दी" : "English"}</button>
            <button onClick={logout} className="rounded border px-2 py-1">{t("nav.logout")}</button>
          </div>
        </div>
      </header>
      <main id="main" className="mx-auto max-w-7xl space-y-4 px-4 py-4">{children}</main>
      <footer className="mx-auto max-w-7xl px-4 pb-6 text-xs text-slate-500">{t("label.help")}</footer>
    </div>
  );
}

export function Stat({ label, value, tag }: { label: string; value: ReactNode; tag?: ReactNode }) {
  return <div className="rounded-lg border bg-white p-4"><div className="text-sm text-slate-500">{label}</div>
    <div className="mt-1 flex items-center gap-2 text-2xl font-bold text-slate-800">{value}{tag}</div></div>;
}
