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
  alvosPrioritarios: string[];
  topAlvos: Array<Record<string, any>>;
  kpis: Array<{ label: string; value: number | string; icon?: string }>;
};

export function parseMarkdownExecutivo(markdown: string): ParsedMarkdown {
  const result: ParsedMarkdown = {
    resumoExecutivo: "",
    principaisAchados: [],
    implicacoesComerciais: [],
    planoAcao: [],
    alvosPrioritarios: [],
    topAlvos: [],
    kpis: [],
  };

  if (!markdown) return result;

  const lines = markdown.split("\n");
  let currentSection: string | null = null;
  let resumoLines: string[] = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();

    // Detecta seção por título (com ou sem markdown headers)
    if (line.match(/^##?\s*Resumo\s+Executivo/i) || line.match(/^Resumo\s+Executivo$/i)) {
      currentSection = "resumoExecutivo";
      continue;
    } else if (line.match(/^##?\s*Principais\s+Achados/i) || line.match(/^Principais\s+Achados$/i)) {
      currentSection = "principaisAchados";
      continue;
    } else if (line.match(/^##?\s*Implicações\s+Comerciais/i) || line.match(/^Implicações\s+Comerciais$/i)) {
      currentSection = "implicacoesComerciais";
      continue;
    } else if (line.match(/^##?\s*Plano\s+de\s+Ação\s+Imediato/i) || line.match(/^Plano\s+de\s+Ação\s+Imediato$/i)) {
      currentSection = "planoAcao";
      continue;
    } else if (line.match(/^##?\s*Alvos\s+Prioritários/i) || line.match(/^Alvos\s+Prioritários/i)) {
      currentSection = "alvosPrioritarios";
      continue;
    }

    // Para seções vazias, pula linhas em branco
    if (!line && currentSection) {
      continue;
    }

    // Processa conteúdo da seção atual
    if (currentSection === "resumoExecutivo") {
      // Resumo executivo: pega texto até encontrar próxima seção ou linha vazia dupla
      if (line && !line.match(/^(##?|Principais|Implicações|Plano|Alvos)/i)) {
        resumoLines.push(line);
      } else if (line.match(/^(Principais|Implicações|Plano|Alvos)/i)) {
        // Próxima seção encontrada, para de coletar resumo
        currentSection = null;
      }
    } else if (currentSection === "principaisAchados") {
      // Detecta bullets
      const bulletMatch = line.match(/^[-*•]\s+(.+)/);
      if (bulletMatch) {
        result.principaisAchados.push(bulletMatch[1]);
      } else if (line && !line.match(/^(##?|Implicações|Plano|Alvos)/i)) {
        // Texto sem bullet também pode ser parte do achado
        result.principaisAchados.push(line);
      }
    } else if (currentSection === "implicacoesComerciais") {
      const bulletMatch = line.match(/^[-*•]\s+(.+)/);
      if (bulletMatch) {
        result.implicacoesComerciais.push(bulletMatch[1]);
      } else if (line && !line.match(/^(##?|Principais|Plano|Alvos)/i)) {
        result.implicacoesComerciais.push(line);
      }
    } else if (currentSection === "planoAcao") {
      const bulletMatch = line.match(/^[-*•]\s+(.+)/);
      if (bulletMatch) {
        result.planoAcao.push(bulletMatch[1]);
      } else if (line && !line.match(/^(##?|Principais|Implicações|Alvos)/i)) {
        result.planoAcao.push(line);
      }
    } else if (currentSection === "alvosPrioritarios") {
      // Alvos podem ser lista simples ou objetos estruturados
      const bulletMatch = line.match(/^[-*•]\s+(.+)/);
      if (bulletMatch) {
        const content = bulletMatch[1];
        // Adiciona como string
        result.alvosPrioritarios.push(content);
        
        // Tenta também parsear como objeto se tiver formato "Chave: Valor | Chave2: Valor2"
        // Nota: O parser preserva TODOS os campos que vêm do backend (incluindo "Rota" se presente).
        // Se a coluna "Rota" aparecer vazia na tabela, é porque o backend não está enviando esse campo.
        if (content.includes("|") || content.includes(":")) {
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
      } else if (line && !line.match(/^(##?|Principais|Implicações|Plano)/i)) {
        result.alvosPrioritarios.push(line);
      }
    }
  }

  // Junta resumo executivo
  result.resumoExecutivo = resumoLines.join(" ").trim();

  // Tenta extrair KPIs do texto completo (números grandes mencionados)
  const kpiPatterns = [
    { pattern: /(\d+(?:\.\d+)?)\s*clientes?/gi, label: "Clientes Impactados", icon: "👥" },
    { pattern: /(\d+(?:\.\d+)?)\s*dias?/gi, label: "Média de Dias", icon: "⏳" },
    { pattern: /R\$\s*([\d.,]+)/gi, label: "Valor Total", icon: "💰" },
    { pattern: /(\d+(?:\.\d+)?)\s*%/gi, label: "Percentual", icon: "📊" },
  ];

  for (const { pattern, label, icon } of kpiPatterns) {
    const matches = markdown.match(pattern);
    if (matches && matches.length > 0) {
      // Pega o primeiro match e extrai número
      const match = matches[0];
      const numStr = match.replace(/[^\d.,]/g, "").replace(",", ".");
      const numValue = parseFloat(numStr);
      if (!isNaN(numValue)) {
        result.kpis.push({ label, value: numValue, icon });
      }
    }
  }

  return result;
}

