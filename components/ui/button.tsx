
import * as React from "react";
import { clsx } from "clsx";
import { ds } from "@/styles/ui";

type ButtonVariant = "primary" | "secondary" | "ghost";
type ButtonSize = "sm" | "md";

type Props = React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant; size?: ButtonSize };

export function Button({ className, variant = "primary", size = "md", ...props }: Props) {
  const base = `${ds.button.base} disabled:opacity-60 disabled:cursor-not-allowed`;
  const variantMap: Record<ButtonVariant, string> = {
    primary: ds.button.primary,
    secondary: ds.button.secondary,
    ghost:
      "bg-transparent text-slate-300 hover:bg-slate-800/70 hover:shadow-[0_0_12px_rgba(59,130,246,0.25)] focus-visible:ring-slate-600"
  };
  const sizeMap: Record<ButtonSize, string> = {
    sm: "px-4 py-2 text-sm",
    md: "px-5 py-2.5 text-sm"
  };

  return <button className={clsx(base, variantMap[variant], sizeMap[size], className)} {...props} />;
}
