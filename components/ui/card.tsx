
import * as React from "react";
import { clsx } from "clsx";
import { ds } from "@/styles/ui";

export function Card({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={clsx(ds.card, className)} {...props} />;
}

export function CardContent({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={clsx("p-6", className)} {...props} />;
}
