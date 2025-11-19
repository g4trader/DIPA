import React from "react";

type InsightsBlockProps = {
  title: string;
  items: string[];
  icon: React.ReactNode;
  color?: "blue" | "green" | "red" | "yellow" | "orange" | "purple";
  id?: string;
};

/**
 * InsightsBlock - Bloco de insights estruturado
 * 
 * Exibe seções como "Principais Achados", "Implicações Comerciais", "Plano de Ação"
 * com ícone, título e lista de bullets
 */
export function InsightsBlock({
  title,
  items,
  icon,
  color = "blue",
  id,
}: InsightsBlockProps) {
  const colorClasses = {
    blue: "text-blue-400 border-blue-400/20 bg-blue-400/10",
    green: "text-emerald-400 border-emerald-400/20 bg-emerald-400/10",
    red: "text-red-400 border-red-400/20 bg-red-400/10",
    yellow: "text-yellow-400 border-yellow-400/20 bg-yellow-400/10",
    orange: "text-orange-400 border-orange-400/20 bg-orange-400/10",
    purple: "text-purple-400 border-purple-400/20 bg-purple-400/10",
  };

  if (!items || items.length === 0) {
    return null;
  }

  return (
    <div id={id} className="flex flex-col justify-start">
      <ul className="space-y-3 flex-1">
        {items.map((item, idx) => (
          <li key={idx} className="text-white/80 leading-relaxed flex items-start gap-2">
            <span className="text-blue-400 mt-1 flex-shrink-0">•</span>
            <span className="flex-1 text-sm opacity-90">{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

