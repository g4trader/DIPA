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
    // Headings executivos para Q1: "Síntese Analítica", "Riscos Comerciais", "Carteiras Prioritárias"
    if (line.match(/^##?\s*Resumo\s+Executivo/i) || line.match(/^Resumo\s+Executivo$/i)) {
      currentSection = "resumoExecutivo";
      continue;
    } else if (line.match(/^##?\s*Principais\s+Achados/i) || line.match(/^Principais\s+Achados$/i) || 
               line.match(/^##?\s*Síntese\s+Analítica/i) || line.match(/^Síntese\s+Analítica$/i)) {
      currentSection = "principaisAchados";
      continue;
    } else if (line.match(/^##?\s*Implicações\s+Comerciais/i) || line.match(/^Implicações\s+Comerciais$/i) ||
               line.match(/^##?\s*Riscos\s+Comerciais/i) || line.match(/^Riscos\s+Comerciais$/i)) {
      currentSection = "implicacoesComerciais";
      continue;
    } else if (line.match(/^##?\s*Plano\s+de\s+Ação\s+Imediato/i) || line.match(/^Plano\s+de\s+Ação\s+Imediato$/i)) {
      currentSection = "planoAcao";
      continue;
    } else if (line.match(/^##?\s*Alvos\s+Prioritários/i) || line.match(/^Alvos\s+Prioritários/i) ||
               line.match(/^##?\s*Carteiras\s+Prioritárias/i) || line.match(/^Carteiras\s+Prioritárias/i)) {
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
        
        // Parse estruturado: "CLIENTE | X dias sem compra | Rota: Y"
        if (content.includes("|")) {
          const parts = content.split("|").map(p => p.trim());
          const cliente = parts[0] || '';
          const diasTexto = parts[1] || '';
          const rotaTexto = parts[2] || '';
          
          // Extrai dias do texto (ex: "381 dias sem compra" -> 381)
          const diasMatch = diasTexto.match(/(\d+)/);
          const dias = diasMatch ? Number(diasMatch[1]) : null;
          
          // Extrai rota (remove "Rota:" se presente)
          let rota = rotaTexto.replace(/^Rota:\s*/i, '').trim();
          if (!rota) rota = '—';
          
          // Cria objeto estruturado
          const obj: Record<string, any> = {
            Cliente: cliente,
            "Dias sem compra": dias !== null ? dias : '—',
            Rota: rota,
          };
          
          result.topAlvos.push(obj);
        } else if (content.includes(":")) {
          // Fallback: formato "Chave: Valor | Chave2: Valor2"
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

  // Extrai KPIs com regexes específicas (prioridade sobre padrões genéricos)
  const resumoTexto = result.resumoExecutivo || markdown;

  // 1) Clientes impactados - padrão específico
  const clientesMatch = resumoTexto.match(/foram identificados?\s+([\d\.]+)\s*clientes?/i);
  if (clientesMatch) {
    const clientes = Number(clientesMatch[1].replace(/\./g, ''));
    if (!isNaN(clientes)) {
      result.kpis.push({
        label: "Clientes Impactados",
        value: clientes,
        icon: "👥",
      });
    }
  }

  // 2) Média de dias - padrão específico (prioridade sobre "mais de X dias")
  let mediaDiasMatch =
    resumoTexto.match(/m[eé]dia de dias sem compra é de\s+([\d\.]+)\s*dias/i) ||
    resumoTexto.match(/m[eé]dia de\s+([\d\.]+)\s*dias/i);
  
  if (mediaDiasMatch) {
    const mediaDias = Number(mediaDiasMatch[1].replace(/\./g, ''));
    if (!isNaN(mediaDias)) {
      result.kpis.push({
        label: "Média de Dias",
        value: mediaDias,
        icon: "⏳",
      });
    }
  }

  // 3) Valor Total (R$)
  const valorMatch = resumoTexto.match(/R\$\s*([\d.,]+)/i);
  if (valorMatch) {
    const valorStr = valorMatch[1].replace(/\./g, '').replace(',', '.');
    const valor = parseFloat(valorStr);
    if (!isNaN(valor)) {
      result.kpis.push({
        label: "Valor Total",
        value: valor,
        icon: "💰",
      });
    }
  }

  // 4) Percentual
  const percentualMatch = resumoTexto.match(/(\d+(?:\.\d+)?)\s*%/i);
  if (percentualMatch) {
    const percentual = parseFloat(percentualMatch[1]);
    if (!isNaN(percentual)) {
      result.kpis.push({
        label: "Percentual",
        value: percentual,
        icon: "📊",
      });
    }
  }

  return result;
}

