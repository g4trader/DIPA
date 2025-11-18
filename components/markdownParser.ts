/**
 * Helper para parsear markdown executivo e extrair seções estruturadas
 * 
 * Extrai:
 * - Resumo Executivo
 * - Principais Achados
 * - Implicações Comerciais
 * - Plano de Ação Imediato
 * - Alvos Prioritários (TOP 10)
 */

export type ParsedMarkdown = {
  resumoExecutivo: string;
  principaisAchados: string[];
  implicacoesComerciais: string[];
  planoAcao: string[];
  topAlvos: Array<Record<string, any>>;
  kpis: Array<{ label: string; value: string | number; icon?: string }>;
};

export function parseMarkdownExecutivo(markdown: string): ParsedMarkdown {
  const result: ParsedMarkdown = {
    resumoExecutivo: "",
    principaisAchados: [],
    implicacoesComerciais: [],
    planoAcao: [],
    topAlvos: [],
    kpis: [],
  };

  if (!markdown) return result;

  const lines = markdown.split("\n");
  let currentSection: keyof ParsedMarkdown | null = null;
  let resumoLines: string[] = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();

    // Detecta seção por título
    if (line.match(/^##?\s*Resumo\s+Executivo/i)) {
      currentSection = "resumoExecutivo";
      continue;
    } else if (line.match(/^##?\s*Principais\s+Achados/i)) {
      currentSection = "principaisAchados";
      continue;
    } else if (line.match(/^##?\s*Implicações\s+Comerciais/i)) {
      currentSection = "implicacoesComerciais";
      continue;
    } else if (line.match(/^##?\s*Plano\s+de\s+Ação\s+Imediato/i)) {
      currentSection = "planoAcao";
      continue;
    } else if (line.match(/^##?\s*Alvos\s+Prioritários/i)) {
      currentSection = "topAlvos";
      continue;
    }

    // Processa conteúdo da seção atual
    if (currentSection === "resumoExecutivo") {
      if (line && !line.match(/^##?/)) {
        resumoLines.push(line);
      }
    } else if (currentSection === "principaisAchados" || currentSection === "implicacoesComerciais" || currentSection === "planoAcao") {
      // Detecta bullets
      const bulletMatch = line.match(/^[-*•]\s+(.+)/);
      if (bulletMatch) {
        result[currentSection].push(bulletMatch[1]);
      }
    } else if (currentSection === "topAlvos") {
      // Detecta bullets de alvos (formato: "SKU: X | Descrição: Y | ...")
      const bulletMatch = line.match(/^[-*•]\s+(.+)/);
      if (bulletMatch) {
        const content = bulletMatch[1];
        // Tenta parsear formato "Chave: Valor | Chave2: Valor2"
        const parts = content.split("|").map(p => p.trim());
        const obj: Record<string, any> = {};
        for (const part of parts) {
          const colonIdx = part.indexOf(":");
          if (colonIdx > 0) {
            const key = part.substring(0, colonIdx).trim();
            const value = part.substring(colonIdx + 1).trim();
            obj[key] = value;
          } else {
            obj["item"] = part;
          }
        }
        if (Object.keys(obj).length > 0) {
          result.topAlvos.push(obj);
        }
      }
    }
  }

  // Junta resumo executivo
  result.resumoExecutivo = resumoLines.join(" ").trim();

  // Tenta extrair KPIs do resumo executivo (números grandes mencionados)
  const kpiPatterns = [
    { pattern: /(\d+(?:\.\d+)?)\s*clientes?/gi, label: "Clientes Impactados", icon: "👥" },
    { pattern: /(\d+(?:\.\d+)?)\s*dias?/gi, label: "Média de Dias", icon: "⏳" },
    { pattern: /R\$\s*([\d.,]+)/gi, label: "Valor Total", icon: "💰" },
    { pattern: /(\d+(?:\.\d+)?)\s*%/gi, label: "Percentual", icon: "📊" },
  ];

  for (const { pattern, label, icon } of kpiPatterns) {
    const matches = markdown.match(pattern);
    if (matches && matches.length > 0) {
      const value = matches[0].replace(/[^\d.,]/g, "");
      if (value) {
        result.kpis.push({ label, value, icon });
      }
    }
  }

  return result;
}

