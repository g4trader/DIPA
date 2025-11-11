
import "./../styles/globals.css";
import React from "react";
export const metadata = { title: "DIPA – Dipam Intelligence & Performance Assistant" };
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body className="min-h-screen bg-slate-50">{children}</body>
    </html>
  );
}
