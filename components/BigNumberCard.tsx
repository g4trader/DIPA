import React from "react";

type BigNumberCardProps = {
  label: string;
  value: string | number;
  icon: React.ReactNode;
  trend?: "up" | "down" | "neutral";
  color?: "blue" | "green" | "red" | "yellow" | "orange";
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
    <div className="bg-[#0D111A] border border-white/10 rounded-xl p-6 flex items-center gap-4 hover:border-white/20 transition-all duration-200 shadow-lg hover:shadow-xl">
      <div className={`${colorClasses[color]} ${bgColorClasses[color]} rounded-xl p-3 text-3xl border`}>
        {icon}
      </div>
      <div className="flex-1">
        <p className="text-sm text-white/60 uppercase tracking-wide mb-1">{label}</p>
        <p className={`text-3xl font-bold text-white ${trend === "up" ? "text-emerald-400" : trend === "down" ? "text-red-400" : ""}`}>
          {typeof value === "number" ? value.toLocaleString("pt-BR") : value}
        </p>
      </div>
    </div>
  );
}

