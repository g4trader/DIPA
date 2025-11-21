"use client";

import React from "react";
import { clsx } from "clsx";

type TitleProps = {
  children: React.ReactNode;
  level?: 1 | 2 | 3 | 4 | 5 | 6;
  className?: string;
};

/**
 * Title - Componente de título padronizado DIPAM
 */
export function Title({
  children,
  level = 1,
  className = "",
}: TitleProps) {
  const baseClasses = "font-semibold text-white";
  
  const levelClasses = {
    1: "text-3xl md:text-4xl",
    2: "text-2xl md:text-3xl",
    3: "text-xl md:text-2xl",
    4: "text-lg md:text-xl",
    5: "text-base md:text-lg",
    6: "text-sm md:text-base",
  };

  const Component = `h${level}` as keyof JSX.IntrinsicElements;

  return (
    <Component className={clsx(baseClasses, levelClasses[level], className)}>
      {children}
    </Component>
  );
}

