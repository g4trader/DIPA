import React from "react";

type BigNumberCardProps = {
  label: string;
  value: string | number;
  icon: React.ReactNode;
  trend?: "up" | "down" | "neutral";
  color?: "blue" | "green" | "red" | "yellow" | "orange";
  id?: string;
};

/**
 * BigNumberCard - Card de KPI com número grande e impacto visual
 * 
 * Usado para exibir métricas principais de forma destacada no topo do dashboard
 */
export default function BigNumberCard({
  label,
  value,
  icon,
  trend,
  color = "blue",
  id,
}: BigNumberCardProps) {
  const colorClasses = {
    blue: "text-blue-400 border-blue-400/20",
    green: "text-emerald-400 border-emerald-400/20",
    red: "text-red-400 border-red-400/20",
    yellow: "text-yellow-400 border-yellow-400/20",
    orange: "text-orange-400 border-orange-400/20",
  };

  const bgColorClasses = {
    blue: "bg-blue-400/10",
    green: "bg-emerald-400/10",
    red: "bg-red-400/10",
    yellow: "bg-yellow-400/10",
    orange: "bg-orange-400/10",
  };

  return (
    <div id={id} className="flex flex-col justify-between rounded-2xl bg-[#0F172A] border border-white/10 px-6 py-5 shadow-lg shadow-black/40 hover:border-white/20 transition-all duration-200">
      <div className="flex items-start gap-4 mb-3">
        <div className={`${colorClasses[color]} ${bgColorClasses[color]} rounded-xl p-3 text-xl border flex-shrink-0`}>
          {icon}
        </div>
        <p className="text-sm text-white/70 opacity-70 uppercase tracking-wide pt-1">{label}</p>
      </div>
          <div className="flex-1 flex items-end">
            <p className={`mt-2 text-3xl md:text-4xl font-bold tracking-tight text-white ${trend === "up" ? "text-emerald-400" : trend === "down" ? "text-red-400" : ""}`}>
              {typeof value === "number" ? value.toLocaleString("pt-BR") : value}
            </p>
          </div>
    </div>
  );
}

