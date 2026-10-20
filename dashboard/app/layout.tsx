import "./globals.css";
import type { ReactNode } from "react";
import { I18nProvider } from "@/lib/i18n";
import { Shell } from "@/components/ui";

export const metadata = { title: "SAKSHI — compliance monitoring", manifest: "/manifest.json" };

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body><I18nProvider><Shell>{children}</Shell></I18nProvider></body>
    </html>
  );
}
