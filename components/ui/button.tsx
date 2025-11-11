
import * as React from "react";
import { clsx } from "clsx";
type Props = React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "default"|"outline"|"ghost"|"secondary"; size?: "sm"|"md" };
export function Button({ className, variant="default", size="md", ...props }: Props) {
  const base = "inline-flex items-center justify-center rounded-xl font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-sky-300/60 disabled:opacity-50";
  const variants: Record<string,string> = {
    default: "bg-sky-600 text-white hover:bg-sky-700",
    outline: "border border-sky-200 bg-white text-sky-700 hover:bg-sky-50",
    ghost: "hover:bg-slate-100",
    secondary: "bg-slate-200 hover:bg-slate-300"
  };
  const sizes: Record<string,string> = { sm: "h-8 px-3 text-sm", md: "h-10 px-4 text-sm" };
  return <button className={clsx(base, variants[variant], sizes[size], className)} {...props} />;
}
