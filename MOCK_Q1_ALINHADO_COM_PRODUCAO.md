# Mock Q1 Alinhado com Produção

## Resumo

Este documento descreve como o modo mock da Q1 foi alinhado com a produção real, garantindo que ambos os ambientes usem exatamente os mesmos dados e estrutura executiva.

## O que foi feito

### 1. Snapshot Real do DW

Criado script `scripts/generate_mock_snapshot_q1_from_dw.py` que:

- **Usa a mesma função do DW real**: `get_clientes_sem_compra_ha_dias()` (mesma função usada em produção)
- **Aplica os mesmos filtros**: clientes ativos, >= 61 dias sem compra, sem duplicatas
- **Gera JSONs com estrutura idêntica**: `q1_clientes_sem_compra.json` e `q1_estatisticas.json`
- **Valida consistência**: garante que todos os `dias_sem_compra >= 61` e não há duplicatas

### 2. Mock Engine Ajustado

O `lib/mock/dipamMockEngine.ts` foi ajustado para:

- **Retornar estrutura igual ao orquestrador**: `dados_dw` com `classificacao_faixas`
- **Usar dados reais do snapshot**: carrega de `mockDataGenerated.ts` (dados incluídos no código)
- **Gerar markdown executivo localmente**: usa a mesma lógica do LLM, mas sem chamar o LLM (já que está no frontend)
- **Tabela com colunas corretas**: "Dados Analíticos - Consulta Geral" com 5 colunas (Cliente ID, Nome, Dias sem Compra, Vendedor, Supervisor)
- **Big Number correto**: `big_number = total_clientes_q1` (COUNT(DISTINCT cliente_id))

### 3. Frontend Ajustado

O `components/ResponseDashboard.tsx` foi ajustado para:

- **Buscar tabela em múltiplos formatos**: `jsonTecnico.tabela_principal`, `structured.detalhe_tabela`, `structured.secoes`
- **Renderizar título dinâmico**: usa título da tabela se disponível, senão usa "Dados Analíticos - Consulta Geral"
- **Processar markdown executivo**: extrai blocos (Resumo Executivo, Impactos Comerciais, Plano Prioritário)

### 4. Remoção de Mocks Antigos

- **Fallback mantido apenas para emergência**: `DADOS_MOCK_FALLBACK` só é usado se os dados reais não estiverem disponíveis
- **Logs de debug limitados**: apenas em desenvolvimento (`NODE_ENV === "development"`)

## Onde estão os snapshots

### Arquivos de Dados

- **`mock/data/q1_clientes_sem_compra.json`**: Lista completa de clientes (1029 registros)
- **`mock/data/q1_estatisticas.json`**: Estatísticas agregadas (total, faixas, percentuais)

### Arquivos Incluídos no Código

- **`lib/mock/mockDataGenerated.ts`**: Dados reais incluídos diretamente no código TypeScript (303KB)
  - Gerado por `scripts/generate_mock_data_ts.py`
  - Garante disponibilidade na Vercel (não depende de arquivos externos)

### Scripts

- **`scripts/generate_mock_snapshot_q1_from_dw.py`**: Gera snapshot usando função real do DW
- **`scripts/generate_mock_snapshot_q1.py`**: Gera snapshot a partir de CSVs (alternativa)
- **`scripts/test_mock_q1_consistencia.py`**: Valida consistência entre mock e produção
- **`scripts/generate_mock_data_ts.py`**: Gera `mockDataGenerated.ts` a partir dos JSONs

## Como regenerar e validar

### 1. Regenerar Snapshot do DW

⚠️ **IMPORTANTE**: O snapshot atual foi gerado a partir de CSVs e **não tem supervisor preenchido**. Para ter supervisor preenchido (como na produção), use o script que usa o DW real:

```bash
# Usa a função real do DW (recomendado - preenche supervisor corretamente)
python3 scripts/generate_mock_snapshot_q1_from_dw.py \
  --output-dir ./mock/data \
  --dias 60 \
  --data-referencia 2025-11-24
```

Este script:
- ✅ Usa `get_clientes_sem_compra_ha_dias()` real (mesma função da produção)
- ✅ Preenche `supervisor_nome` e `supervisor_codigo` corretamente (via JOINs)
- ✅ Ordena por `dias_sem_compra` crescente (mesma ordem da produção)
- ✅ Garante que todos os campos numéricos são int/float

### 2. Regenerar Dados TypeScript

Após regenerar os JSONs, gere o arquivo TypeScript:

```bash
python3 scripts/generate_mock_data_ts.py
```

Isso atualiza `lib/mock/mockDataGenerated.ts` com os novos dados.

### 3. Validar Consistência

```bash
# Valida que mock == produção real
python3 scripts/test_mock_q1_consistencia.py
```

O script valida:
- `total_mock == total_real`
- `set(cliente_id_mock) == set(cliente_id_real)`
- Todos os `dias_sem_compra >= 61`
- Soma das faixas == total_clientes

### 4. Commit dos Dados

```bash
git add mock/data/*.json lib/mock/mockDataGenerated.ts
git commit -m "feat: atualiza snapshot Q1 mock com dados reais do DW"
```

## Como rodar o modo mock e comparar com produção

### Modo Mock (Vercel)

1. Configure variável de ambiente:
   ```
   NEXT_PUBLIC_DIPAM_ENV=mock
   ```

2. Acesse: https://dipam.vercel.app

3. Faça a pergunta: "Quais clientes estão com cadastro ativo, mas sem nenhuma compra por mais de 60 dias?"

4. Valide:
   - Big Number mostra total correto (ex.: 1029 clientes)
   - Tabela "Dados Analíticos - Consulta Geral" com 5 colunas corretas
   - Resumo Executivo, Impactos Comerciais e Plano Prioritário presentes
   - Dados reais (não "Cliente Exemplo" ou "Vendedor Exemplo")

### Produção Real

1. Acesse: https://dipam.smartiasolutions.com.br

2. Faça a mesma pergunta

3. Compare:
   - Big Number deve ser igual (ou muito próximo, se snapshot foi gerado em data diferente)
   - Tabela deve ter mesma estrutura e colunas
   - Blocos executivos devem ter mesmo formato e tom

### Comparação Local

Para comparar localmente:

```bash
# Modo mock
NEXT_PUBLIC_DIPAM_ENV=mock npm run dev

# Modo produção (requer backend rodando)
NEXT_PUBLIC_DIPAM_ENV=prod npm run dev
```

## Estrutura de Dados

### dados_dw (retornado pelo mock engine)

```typescript
{
  status: "ok",
  mensagem: "Dados consultados com sucesso. 1029 registro(s) encontrado(s).",
  dados: [
    {
      cliente_id: 35245,
      nome: "REDE MAXXI ECONOMICA",
      segmento: "",
      rota_id: "1301",
      vendedor_nome: "1301",
      vendedor_codigo: "",
      supervisor_nome: "",
      supervisor_codigo: "",
      data_ultima_compra: "2025-06-09T00:00:00",
      dias_sem_compra: 168
    },
    // ... mais clientes
  ],
  classificacao_faixas: {
    total: 1029,
    faixa_61_120: 585,
    faixa_121_180: 179,
    faixa_181_300: 229,
    faixa_mais_300: 36,
    percentual_61_120: 56.9,
    percentual_121_180: 17.4,
    percentual_181_300: 22.3,
    percentual_mais_300: 3.5
  }
}
```

### tabela_principal (formato esperado pelo frontend)

```typescript
{
  titulo: "Dados Analíticos - Consulta Geral",
  colunas: ["Cliente ID", "Nome", "Dias sem Compra", "Vendedor", "Supervisor"],
  linhas: [
    [35245, "REDE MAXXI ECONOMICA", 168, "1301", "—"],
    // ... mais linhas
  ]
}
```

## Critérios de Aceitação

✅ **Consistência de dados**
- `scripts/test_mock_q1_consistencia.py` passa 100%
- `total_clientes_q1` no mock == total real da Q1
- Não há duplicatas de cliente na tabela

✅ **UI mock vs produção**
- Big Number mostra mesmo total de clientes
- Tabela "Dados Analíticos - Consulta Geral" com mesmas colunas
- Primeiros registros batem com dados reais

✅ **Modelo executivo**
- Resumo Executivo usa linguagem formal
- Faz referência às faixas corretas (61-120, 121-180, 181-300, >300)
- Foco de curto prazo em 61-120 dias
- Não traz números diferentes da Q1 real

✅ **Código limpo**
- Não restam JSONs ou mocks antigos com dados fictícios para Q1
- `lib/mock/dipamMockEngine.ts` documentado indicando que Q1 usa snapshot real
- Logs de debug limitados ao ambiente de desenvolvimento

## Troubleshooting

### Mock mostra dados de fallback (5 clientes)

**Causa**: Dados reais não estão sendo carregados.

**Solução**:
1. Verifique se `lib/mock/mockDataGenerated.ts` existe e tem dados
2. Regenerar: `python3 scripts/generate_mock_data_ts.py`
3. Verificar logs: `[Q1 MOCK] total_clientes_q1` deve mostrar número real (ex.: 1029)

### Tabela mostra colunas erradas

**Causa**: Frontend não está lendo `jsonTecnico.tabela_principal` corretamente.

**Solução**:
1. Verificar `components/ResponseDashboard.tsx` linha 283-298
2. Verificar se `tabelaPrincipalQ1` está sendo montado corretamente
3. Verificar logs do console para ver estrutura retornada

### Big Number diferente entre mock e produção

**Causa**: Snapshot foi gerado em data diferente ou com filtros diferentes.

**Solução**:
1. Regenerar snapshot com mesma data de referência da produção
2. Validar com `scripts/test_mock_q1_consistencia.py`
3. Verificar se filtros de comportamento estão aplicados igualmente

## Notas Técnicas

- O mock engine **não chama o LLM** (está no frontend), mas gera markdown executivo usando a mesma lógica
- Os dados são incluídos diretamente no código TypeScript para garantir disponibilidade na Vercel
- O fallback (`DADOS_MOCK_FALLBACK`) é usado apenas se os dados reais não estiverem disponíveis
- A estrutura `dados_dw` retornada pelo mock é idêntica à estrutura retornada pelo orquestrador

