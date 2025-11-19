import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';

export type ExecutivePdfPayload = {
  pergunta: string;
  resumoExecutivo?: string;
  kpis?: { label: string; valor: string | number }[];
  principaisAchados?: string[];
  implicacoes?: string[];
  planoAcao?: string[];
  alvosPrioritariosLista?: string[];
  tabelaTop10?: { cliente: string; diasSemCompra: number; rota?: string | null }[];
  tabelaPrincipal?: {
    colunas: string[];
    linhas: (string | number | null)[][];
  } | null;
};

export function generateExecutivePdf(data: ExecutivePdfPayload) {
  const doc = new jsPDF({ unit: 'pt', format: 'a4' });
  const marginLeft = 40;
  let cursorY = 50;

  const addTitle = (text: string) => {
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(14);
    doc.text(text, marginLeft, cursorY);
    cursorY += 22;
  };

  const addParagraph = (text?: string) => {
    if (!text) return;
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(11);
    const lines = doc.splitTextToSize(text, 515);
    doc.text(lines, marginLeft, cursorY);
    cursorY += lines.length * 14 + 14;
  };

  const addList = (title: string, items?: string[]) => {
    if (!items || !items.length) return;
    addTitle(title);
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(11);
    items.forEach((item) => {
      const lines = doc.splitTextToSize(`• ${item}`, 515);
      doc.text(lines, marginLeft, cursorY);
      cursorY += lines.length * 14;
    });
    cursorY += 10;
  };

  // Logo/Cabeçalho
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(18);
  doc.setTextColor(14, 165, 233); // cyan-500
  doc.text('DIPAM COPILOT™', marginLeft, cursorY);
  doc.setTextColor(0, 0, 0); // reset to black
  cursorY += 30;

  // Título principal (pergunta)
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(16);
  const titulo = doc.splitTextToSize(data.pergunta, 515);
  doc.text(titulo, marginLeft, cursorY);
  cursorY += titulo.length * 18 + 20;

  // KPIs
  if (data.kpis && data.kpis.length) {
    addTitle('Indicadores Principais');
    data.kpis.forEach((kpi) => {
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(11);
      doc.text(`${kpi.label}:`, marginLeft, cursorY);
      doc.setFont('helvetica', 'normal');
      const valorStr = typeof kpi.valor === 'number' 
        ? kpi.valor.toLocaleString('pt-BR') 
        : String(kpi.valor);
      doc.text(valorStr, marginLeft + 180, cursorY);
      cursorY += 16;
    });
    cursorY += 10;
  }

  // Resumo Executivo
  if (data.resumoExecutivo) {
    addTitle('Resumo Executivo');
    addParagraph(data.resumoExecutivo);
  }

  // Blocos executivos
  addList('Principais Achados', data.principaisAchados);
  addList('Implicações Comerciais', data.implicacoes);
  addList('Plano de Ação Imediato', data.planoAcao);

  // Alvos Prioritários – lista
  addList('Alvos Prioritários (TOP 10)', data.alvosPrioritariosLista);

  // Alvos Prioritários – tabela
  if (data.tabelaTop10 && data.tabelaTop10.length) {
    // Verifica se há alguma rota válida
    const temRotas = data.tabelaTop10.some(a => a.rota && a.rota !== '—' && a.rota !== '-');
    
    const headers = temRotas 
      ? [['Cliente', 'Dias sem compra', 'Rota']]
      : [['Cliente', 'Dias sem compra']];
    
    const body = data.tabelaTop10.map((a) => {
      const row = [a.cliente, String(a.diasSemCompra)];
      if (temRotas) {
        row.push(a.rota || '-');
      }
      return row;
    });

    autoTable(doc, {
      startY: cursorY + 10,
      margin: { left: marginLeft, right: marginLeft },
      head: headers,
      body: body,
      styles: { fontSize: 9 },
      headStyles: { fillColor: [20, 30, 60] },
    });
    // @ts-ignore
    cursorY = (doc as any).lastAutoTable.finalY + 20;
  }

  // Tabela principal
  if (data.tabelaPrincipal && data.tabelaPrincipal.colunas && data.tabelaPrincipal.linhas) {
    autoTable(doc, {
      startY: cursorY,
      margin: { left: marginLeft, right: marginLeft },
      head: [data.tabelaPrincipal.colunas],
      body: data.tabelaPrincipal.linhas.map((linha) =>
        linha.map((c) => (c === null ? '-' : String(c)))
      ),
      styles: { fontSize: 8 },
      headStyles: { fillColor: [15, 23, 42] },
    });
  }

  // Rodapé
  const pageCount = doc.getNumberOfPages();
  for (let i = 1; i <= pageCount; i++) {
    doc.setPage(i);
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(8);
    doc.setTextColor(128, 128, 128);
    doc.text(
      `DIPAM COPILOT™ - Página ${i} de ${pageCount}`,
      marginLeft,
      doc.internal.pageSize.height - 20
    );
    doc.text(
      new Date().toLocaleDateString('pt-BR'),
      doc.internal.pageSize.width - marginLeft - 80,
      doc.internal.pageSize.height - 20
    );
    doc.setTextColor(0, 0, 0);
  }

  doc.save('DIPAM_COPILOT_Relatorio.pdf');
}

