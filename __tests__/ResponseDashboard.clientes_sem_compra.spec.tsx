/**
 * Teste de componente para ResponseDashboard - Cenário: Clientes sem compra
 * 
 * Valida que o componente renderiza corretamente:
 * - Resumo Executivo
 * - Tabela com dados de clientes (IDs sem formatação de moeda)
 * - Seções executivas
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { ResponseDashboard } from '@/components/ResponseDashboard';
import { CopilotStructuredResponse } from '@/types/agent';

// Mock da resposta do backend para clientes_sem_compra
const respostaClientesSemCompra: CopilotStructuredResponse = {
  resumo_executivo: `Durante o período de 01/11/2025 a 30/11/2025, identificamos 3 clientes com cadastro ativo que não realizaram nenhuma compra há mais de 60 dias. Estes clientes representam uma oportunidade de reativação comercial.`,
  
  secoes: [
    {
      titulo: "Dados Analíticos - Consulta Geral",
      tipo: "tabela_detalhada",
      dados: [
        {
          "Cliente ID": 729,
          "Nome": "FIGUEIRA GRAVATAI COMERCIO E DERIVADOS DE COMBUSTIVEIS LTDA",
          "Dias sem Compra": 381
        },
        {
          "Cliente ID": 3031,
          "Nome": "NATALY BRAGA BORGES",
          "Dias sem Compra": 376
        },
        {
          "Cliente ID": 4453,
          "Nome": "EDUARDO VIEIRA QUADROS",
          "Dias sem Compra": 374
        }
      ]
    }
  ],
  
  detalhe_tabela: {
    titulo: "Dados Analíticos - Consulta Geral",
    colunas: ["Cliente ID", "Nome", "Dias sem Compra"],
    linhas: [
      [729, "FIGUEIRA GRAVATAI COMERCIO E DERIVADOS DE COMBUSTIVEIS LTDA", 381],
      [3031, "NATALY BRAGA BORGES", 376],
      [4453, "EDUARDO VIEIRA QUADROS", 374]
    ]
  }
};

describe('ResponseDashboard - Clientes sem Compra', () => {
  it('deve renderizar o Resumo Executivo', () => {
    render(<ResponseDashboard data={respostaClientesSemCompra} />);
    
    expect(screen.getByText(/Resumo Executivo/i)).toBeInTheDocument();
    expect(screen.getByText(/identificamos 3 clientes/i)).toBeInTheDocument();
  });

  it('deve renderizar a tabela com cabeçalhos corretos', () => {
    render(<ResponseDashboard data={respostaClientesSemCompra} />);
    
    // Verifica cabeçalhos da tabela
    expect(screen.getByText(/Cliente ID/i)).toBeInTheDocument();
    expect(screen.getByText(/Nome/i)).toBeInTheDocument();
    expect(screen.getByText(/Dias sem Compra/i)).toBeInTheDocument();
  });

  it('deve renderizar os dados dos clientes corretamente', () => {
    render(<ResponseDashboard data={respostaClientesSemCompra} />);
    
    // Cliente 729 - FIGUEIRA GRAVATAI
    expect(screen.getByText('729')).toBeInTheDocument();
    expect(screen.getByText(/FIGUEIRA GRAVATAI/i)).toBeInTheDocument();
    expect(screen.getByText('381')).toBeInTheDocument();
    
    // Cliente 3031 - NATALY BRAGA BORGES
    expect(screen.getByText('3031')).toBeInTheDocument();
    expect(screen.getByText(/NATALY BRAGA BORGES/i)).toBeInTheDocument();
    expect(screen.getByText('376')).toBeInTheDocument();
  });

  it('NÃO deve formatar IDs numéricos como moeda (R$)', () => {
    render(<ResponseDashboard data={respostaClientesSemCompra} />);
    
    // Verifica que os IDs aparecem como números simples
    const clienteId729 = screen.getByText('729');
    const clienteId3031 = screen.getByText('3031');
    
    expect(clienteId729).toBeInTheDocument();
    expect(clienteId3031).toBeInTheDocument();
    
    // Verifica que NÃO existe formatação de moeda para IDs
    const currencyPattern = /R\$\s*3\.031/;
    const pageText = document.body.textContent || '';
    
    // Não deve encontrar "R$ 3.031" ou "R$ 729" na página
    expect(pageText).not.toMatch(/R\$\s*3\.031/);
    expect(pageText).not.toMatch(/R\$\s*729/);
    expect(pageText).not.toMatch(/R\$\s*4\.453/);
  });

  it('deve renderizar a seção "Dados Analíticos"', () => {
    render(<ResponseDashboard data={respostaClientesSemCompra} />);
    
    expect(screen.getByText(/Dados Analíticos/i)).toBeInTheDocument();
  });

  it('deve renderizar a tabela detalhada quando expandida', () => {
    render(<ResponseDashboard data={respostaClientesSemCompra} />);
    
    // A tabela detalhada deve estar presente
    expect(screen.getByText(/Dados Analíticos - Consulta Geral/i)).toBeInTheDocument();
    
    // Verifica que os dados da tabela detalhada estão presentes
    const table = document.querySelector('table');
    expect(table).toBeInTheDocument();
    
    // Verifica que a tabela contém os dados esperados
    const tableText = table?.textContent || '';
    expect(tableText).toContain('729');
    expect(tableText).toContain('3031');
    expect(tableText).toContain('NATALY BRAGA BORGES');
  });
});

