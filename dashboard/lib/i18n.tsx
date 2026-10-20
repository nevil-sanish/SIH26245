"use client";
// EN/HI strings from i18n/*.json. Language persists in localStorage. Flag-type names stay in English
// (they are stable identifiers shown alongside the translated explanation labels).
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import en from "@/i18n/en.json";
import hi from "@/i18n/hi.json";

type Lang = "en" | "hi";
const DICTS: Record<Lang, Record<string, string>> = { en, hi };
const Ctx = createContext<{ lang: Lang; setLang: (l: Lang) => void; t: (k: string) => string }>({
  lang: "en", setLang: () => {}, t: (k) => k,
});

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLang] = useState<Lang>("en");
  useEffect(() => {
    try { const l = localStorage.getItem("lang"); if (l === "hi" || l === "en") setLang(l); } catch {}
  }, []);
  useEffect(() => {
    document.documentElement.lang = lang;
    try { localStorage.setItem("lang", lang); } catch {}
  }, [lang]);
  const t = (k: string) => DICTS[lang][k] ?? DICTS.en[k] ?? k;
  return <Ctx.Provider value={{ lang, setLang, t }}>{children}</Ctx.Provider>;
}

export const useT = () => useContext(Ctx);
