# Q1 Mock - Preservação de Estrutura Executiva e Dados

## Visão Geral

O modo mock da Q1 (clientes sem compra há mais de 60 dias) foi implementado para replicar **exatamente** a mesma estrutura executiva e dados da Q1 real, garantindo que a experiência do usuário seja idêntica em ambos os ambientes.

## Como o Snapshot é Gerado

### 1. Script de Geração

O snapshot é gerado pelo script `scripts/generate_mock_snapshot_q1.py`, que:

- Lê os CSVs reais da Dipam:
  - `Clientes ativos.xls - Clientes ativos.csv`
  - `Detalhes de vendas - *.csv` (múltiplos arquivos por período)
  - `Supervisor pasta 1.xlsx - Sheet1.csv`
- Aplica a mesma lógica da query real `get_clientes_sem_compra_ha_dias`:
  - Filtra clientes ativos
  - Calcula dias sem compra (referência: data atual)
  - Filtra clientes com > 60 dias sem compra
  - Remove duplicatas
  - Associa vendedor e supervisor
- Gera dois arquivos JSON:
  - `mock/data/q1_clientes_sem_compra.json`: Lista completa de clientes (1029 clientes)
  - `mock/data/q1_estatisticas.json`: Estatísticas agregadas (total, faixas, data de referência)

### 2. Validação de Consistência

O script `scripts/test_mock_q1_consistencia.py` valida que:

- Total de clientes mock = total Q1 real
- Distribuição por faixas idêntica
- Nenhuma duplicata extra
- Todos os `dias_sem_compra >= 61`

## Como o Mock Garante Mesma Estrutura e Dados da Q1 Real

### 1. Estrutura Executiva

O mock engine (`lib/mock/dipamMockEngine.ts`) gera um markdown executivo completo com **exatamente** os mesmos blocos da Q1 real:

1. **Resumo Executivo** (3-4 linhas)
   - Quantidade total de clientes
   - Distribuição por faixas com percentuais
   - Foco em clientes 61-120 dias como oportunidade principal

2. **Impactos Comerciais**
   - Perda de receita recorrente
   - Risco de migração de carteira
   - Concentração operacional (rotas/supervisões)
   - Oportunidade de recuperação (faixa 61-120 dias)

3. **Plano Prioritário de Ação (Próximos 7 dias)**
   - **Prioridade 1 (61-120 dias)**: Recontato imediato, campanhas de reativação
   - **Prioridade 2 (121-180 dias)**: Ações coordenadas com supervisão
   - **Prioridade 3 (181-300 dias)**: Avaliação caso a caso
   - **Não priorizar (>300 dias)**: Carteira fria, monitoramento passivo

### 2. Tabela de Clientes

A tabela mock usa **exatamente** a mesma estrutura da Q1 real:

- **Título**: "Dados Analíticos - Consulta Geral"
- **Colunas**: Cliente ID, Nome, Dias sem Compra, Vendedor, Supervisor
- **Paginação**: 20 registros por página
- **Dados**: Vêm do snapshot real (`q1_clientes_sem_compra.json`)
- **Formato**: Mesma lógica de fallback do mapper real (vendedor_nome → vendedor_codigo → rota_id)

### 3. Dados Reais

O mock engine carrega os dados do snapshot gerado a partir dos CSVs reais:

- **Fonte**: `lib/mock/mockDataGenerated.ts` (dados incluídos diretamente no código TypeScript)
- **Fallback**: Tenta carregar de `mock/data/q1_clientes_sem_compra.json` (desenvolvimento)
- **Total**: 1029 clientes reais (não dados fictícios)
- **Estatísticas**: Distribuição por faixas idêntica à Q1 real

## Como Alternar Entre Mock e Prod

### Frontend

Configure a variável de ambiente `NEXT_PUBLIC_DIPAM_ENV`:

- **Mock**: `NEXT_PUBLIC_DIPAM_ENV=mock`
- **Produção**: `NEXT_PUBLIC_DIPAM_ENV=prod` (ou não configurado)

### Backend (API Route)

O endpoint `/api/mock/ask` é ativado automaticamente quando `NEXT_PUBLIC_DIPAM_ENV=mock`.

### Vercel

Para usar o modo mock na Vercel:

1. Configure a variável de ambiente:
   ```
   NEXT_PUBLIC_DIPAM_ENV=mock
   ```

2. O frontend automaticamente:
   - Chama `/api/mock/ask` em vez do backend real
   - Usa dados do snapshot incluídos no bundle
   - Renderiza a mesma estrutura executiva da Q1 real

## Estrutura de Arquivos

```
lib/mock/
├── dipamMockEngine.ts          # Motor mock (gera estrutura executiva)
├── mockData.ts                  # Carregamento de dados (fallback)
└── mockDataGenerated.ts         # Dados reais incluídos no código (303KB)

mock/data/
├── q1_clientes_sem_compra.json # Snapshot de clientes (1029 registros)
└── q1_estatisticas.json         # Estatísticas agregadas

scripts/
├── generate_mock_snapshot_q1.py # Gera snapshot a partir de CSVs
└── test_mock_q1_consistencia.py # Valida consistência com Q1 real
```

## Comandos Úteis

### Gerar Snapshot

```bash
python3 scripts/generate_mock_snapshot_q1.py --output-dir ./mock/data
```

### Validar Consistência

```bash
python3 scripts/test_mock_q1_consistencia.py
```

### Regenerar Dados TypeScript

```bash
python3 scripts/generate_mock_data_ts.py
```

## Critérios de Aceitação

✅ **Conteúdo Executivo**
- Resumo Executivo presente (3-4 linhas)
- Impactos Comerciais presente
- Plano Prioritário de Ação presente
- Linguagem formal, executiva

✅ **Tabela de Clientes**
- Título: "Dados Analíticos - Consulta Geral"
- 5 colunas: Cliente ID, Nome, Dias sem Compra, Vendedor, Supervisor
- 20 registros por página
- Sem duplicatas
- Vendedor e Supervisor preenchidos para ≥95% dos clientes

✅ **Consistência com DW**
- Total de clientes mock = total Q1 real
- Distribuição por faixas idêntica
- Nenhuma duplicata extra

✅ **Sem Impacto em Produção**
- Com `env=prod`, comportamento idêntico ao atual
- Modo mock isolado e condicionado por variável de ambiente

## Notas Técnicas

- Os dados são incluídos diretamente no código TypeScript (`mockDataGenerated.ts`) para garantir disponibilidade na Vercel
- O mock engine replica a lógica de classificação por faixas do backend Python
- A estrutura executiva segue exatamente o template definido em `src/llm_integration_intent.py` para Q1
- O frontend processa o markdown executivo usando `parseMarkdownExecutivo` para extrair os blocos

