"use client";

import React from "react";
import { clsx } from "clsx";
import { Sparkles, ArrowRight, Loader2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ChatHistory } from "./ChatHistory";
import { ds } from "@/styles/ui";
import type { PanelMessage } from "./types";

type PromptCardProps = {
  question: string;
  busy: boolean;
  charactersCount: number;
  examples: string[];
  onQuestionChange: (value: string) => void;
  onSubmit: () => void;
  onSelectExample: (example: string) => void;
  onRandomExample: () => void;
  history: PanelMessage[];
};

export function PromptCard({
  question,
  busy,
  charactersCount,
  examples,
  onQuestionChange,
  onSubmit,
  onSelectExample,
  onRandomExample,
  history
}: PromptCardProps) {
  return (
    <Card>
      <CardContent className="flex flex-col gap-6 p-6 md:p-8">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Laboratório de prompts</p>
            <p className="mt-2 text-sm text-slate-400">
              Consulte o DIPA COPILOT™ para investigar metas, produtos e oportunidades comerciais em tempo real.
            </p>
          </div>
          <Sparkles className="h-5 w-5 text-blue-400" />
        </div>

        <PromptSuggestions
          examples={examples}
          activeValue={question}
          onSelect={(value) => {
            onQuestionChange(value);
            onSelectExample(value);
          }}
        />

        <form
          onSubmit={(event) => {
            event.preventDefault();
            onSubmit();
          }}
          className="space-y-4"
        >
          <div className="space-y-2">
            <label htmlFor="prompt-input" className="text-xs font-semibold uppercase tracking-wide text-slate-400">
              Pergunta
            </label>
            <textarea
              id="prompt-input"
              value={question}
              onChange={(event) => onQuestionChange(event.target.value)}
              placeholder="Ex.: Quanto vendemos de Nissin Miojo Galinha Caipira neste mês?"
              className="min-h-[160px] w-full resize-y rounded-2xl border border-slate-700 bg-slate-900/80 px-4 py-3 text-sm leading-relaxed text-slate-100 shadow-inner shadow-blue-950/40 placeholder:text-slate-500 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/40"
            />
            <div className="flex justify-end text-xs text-slate-500">{charactersCount} caracteres</div>
          </div>

          <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
            <Button
              type="button"
              variant="secondary"
              className="w-full sm:w-auto"
              onClick={onRandomExample}
              disabled={busy}
            >
              <Sparkles className="mr-2 h-4 w-4 text-blue-300" />
              Sugestão
            </Button>
            <Button type="submit" className="w-full sm:w-auto shadow-md shadow-blue-900/50 transition" disabled={busy}>
              {busy ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Gerando insight…
                </>
              ) : (
                <>
                  <ArrowRight className="mr-2 h-4 w-4" />
                  Gerar insight
                </>
              )}
            </Button>
          </div>
        </form>

        <div className="hidden border-t border-slate-800 pt-6 lg:block">
          <div className="mb-3 flex items-center justify-between">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Histórico</p>
            <span className="text-xs text-slate-500">{history.length} mensagens</span>
          </div>
          <div className="max-h-72 space-y-3 overflow-y-auto pr-2 scrollbar-thin scrollbar-track-slate-900 scrollbar-thumb-slate-700/80">
            <ChatHistory messages={history} />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

type PromptSuggestionsProps = {
  examples: string[];
  activeValue: string;
  onSelect: (value: string) => void;
};

function PromptSuggestions({ examples, activeValue, onSelect }: PromptSuggestionsProps) {
  if (!examples.length) return null;

  return (
    <div className="flex flex-wrap gap-2">
      {examples.map((example) => (
        <button
          key={example}
          type="button"
          aria-pressed={example === activeValue}
          onClick={() => onSelect(example)}
          className={clsx(
            ds.chip.base,
            example === activeValue ? ds.chip.active : ds.chip.default,
            "active:scale-95 motion-safe:transition-transform"
          )}
        >
          {example}
        </button>
      ))}
    </div>
  );
}

