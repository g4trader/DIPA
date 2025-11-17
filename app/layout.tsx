
import "./../styles/globals.css";
import React from "react";
export const metadata = { 
  title: "DIPAM COPILOT™ — Inteligência comercial em tempo real",
};
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <head>
        <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🤖</text></svg>" />
      </head>
      <body className="min-h-screen bg-slate-50">{children}</body>
    </html>
  );
}
