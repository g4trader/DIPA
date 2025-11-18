import React from "react";

type ExecutiveSectionCardProps = {
  title: string;
  icon?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
};

/**
 * ExecutiveSectionCard - Container padronizado para seções executivas
 * 
 * Usado para criar hierarquia visual consistente em todo o dashboard
 */
export function ExecutiveSectionCard({
  title,
  icon,
  children,
  className = "",
}: ExecutiveSectionCardProps) {
  return (
    <div className={`bg-[#0F172A] border border-white/5 rounded-xl p-6 shadow-lg ${className}`}>
      {(title || icon) && (
        <div className="flex items-center gap-3 mb-4 pb-3 border-b border-white/5">
          {icon && (
            <div className="text-blue-400 text-xl">{icon}</div>
          )}
          {title && (
            <h3 className="text-xl font-semibold text-white">{title}</h3>
          )}
        </div>
      )}
      <div className="text-sm opacity-90 leading-relaxed text-slate-300">
        {children}
      </div>
    </div>
  );
}

