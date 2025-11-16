"use client";

import React from "react";
import { clsx } from "clsx";
import { ds } from "@/styles/ui";
import type { PanelMessage } from "./types";

type ChatHistoryProps = {
  messages: PanelMessage[];
  emptyMessage?: string;
  className?: string;
};

export function ChatHistory({ messages, emptyMessage, className }: ChatHistoryProps) {
  if (!messages.length) {
    return (
      <p className={clsx("text-sm text-slate-500", className)}>
        {emptyMessage ?? "Nenhuma interação ainda. Gere um insight para iniciar."}
      </p>
    );
  }

  return (
    <div className={clsx("space-y-3", className)}>
      {messages.map((message, index) => (
        <ChatBubble key={`${message.role}-${index}`} role={message.role} text={message.text} />
      ))}
    </div>
  );
}

function ChatBubble({ role, text }: { role: "user" | "assistant"; text: string }) {
  const isUser = role === "user";
  const bubbleClass = isUser ? ds.chat.user : ds.chat.assistant;

  return (
    <div className={clsx("flex", isUser ? "justify-end" : "justify-start")}>
      <div className={clsx(bubbleClass, "flex flex-col gap-1 transition duration-200 ease-out")}>
        <span className="text-[10px] font-semibold uppercase tracking-wide text-slate-300 opacity-70">
          {isUser ? "Você" : "DIPA"}
        </span>
        <p className="text-sm leading-relaxed">{text}</p>
      </div>
    </div>
  );
}




