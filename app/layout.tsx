
import "./../styles/globals.css";
import React from "react";
export const metadata = { title: "DIPAM COPILOT™ — Inteligência comercial em tempo real" };
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body className="min-h-screen bg-slate-50">{children}</body>
    </html>
  );
}
