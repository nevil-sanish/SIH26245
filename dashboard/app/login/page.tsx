"use client";
import { useState } from "react";
import { login } from "@/lib/api";
import { useT } from "@/lib/i18n";

export default function Login() {
  const { t, lang, setLang } = useT();
  const [u, setU] = useState(""); const [p, setP] = useState(""); const [err, setErr] = useState(false);
  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    try { const d = await login(u, p); location.href = d.role === "inspector" ? "/inspector/" : d.role === "centre_operator" ? "/" : "/queue/"; }
    catch { setErr(true); }
  };
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 p-4">
      <form onSubmit={submit} className="w-full max-w-sm space-y-3 rounded-lg border bg-white p-6 shadow-sm">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-bold text-[#0072B2]">{t("app")} — {t("login.title")}</h1>
          <button type="button" onClick={() => setLang(lang === "en" ? "hi" : "en")} className="rounded border px-2 text-sm">{lang === "en" ? "हिन्दी" : "English"}</button>
        </div>
        <p className="text-sm text-slate-500">{t("tagline")}</p>
        <label className="block text-sm">{t("login.user")}<input className="mt-1 w-full rounded border px-2 py-1.5" value={u} onChange={(e) => setU(e.target.value)} autoComplete="username" required /></label>
        <label className="block text-sm">{t("login.password")}<input type="password" className="mt-1 w-full rounded border px-2 py-1.5" value={p} onChange={(e) => setP(e.target.value)} autoComplete="current-password" required /></label>
        {err && <p role="alert" className="text-sm text-[#D55E00]">{t("login.error")}</p>}
        <button className="w-full rounded bg-[#0072B2] py-2 font-semibold text-white">{t("login.submit")}</button>
      </form>
    </main>
  );
}
