# 🔧 AJUSTES NO ETL: VENDEDOR E SUPERVISOR

## 📋 RESUMO

Este documento descreve as alterações realizadas no ETL para maximizar o preenchimento de **VENDEDOR** e **SUPERVISOR** na tabela "Dados Analíticos - Consulta Geral" para a pergunta "Quais clientes estão com cadastro ativo, mas sem nenhuma compra por mais de 60 dias?".

## ✅ ALTERAÇÕES REALIZADAS

### 1. Nova Função: `load_supervisores_e_vendedores_from_csv`

**Arquivo:** `src/dw/etl.py`

**Função:** Processa o CSV "Supervisor pasta 1.xlsx - Sheet1.csv" e constrói as dimensões de Supervisor e Vendedor.

**Lógica:**
- Lê o CSV e processa apenas linhas com "Código Vendedor" não nulo
- Cria/atualiza Supervisores a partir dos campos "Gerente", "Supervisor" e "Pastas"
- Cria/atualiza Vendedores usando:
  - `codigo` = campo "Vendedor" (ex.: "ROTA 301", "APP")
  - `nome` = campo "Vendedor"
  - `supervisor_id` = FK para Supervisor criado/atualizado
- Mantém preenchimento forward de Gerente/Supervisor/Pasta para linhas subsequentes

**Mapeamento:**
- `Supervisor.codigo` = nome do supervisor em maiúsculas com underscores
- `Supervisor.nome` = campo "Supervisor"
- `Supervisor.gerente` = campo "Gerente"
- `Supervisor.pasta` = campo "Pastas"
- `Vendedor.codigo` = campo "Vendedor" (rota, ex.: "ROTA 301")
- `Vendedor.nome` = campo "Vendedor"
- `Vendedor.supervisor_id` = FK para Supervisor

### 2. Nova Função: `enrich_clientes_from_csv`

**Arquivo:** `src/dw/etl.py`

**Função:** Enriquece clientes a partir do CSV "Clientes ativos.xls - Clientes ativos.csv".

**Lógica:**
- Para cada cliente, lê o campo "Vendedor 1" (código numérico)
- Busca Vendedor correspondente:
  - Primeiro tenta buscar por código numérico direto
  - Se não encontrar, tenta buscar pela rota (formato "ROTA XXX")
- Preenche no Cliente:
  - `Cliente.rota_rca` = `Vendedor.nome` (ex.: "ROTA 301")
  - `Cliente.supervisor_id` = `Vendedor.supervisor_id`
  - `Cliente.vendedor_id` = `Vendedor.id` (se o campo existir)
- Se vendedor não for encontrado, mantém campos como NULL (não quebra dados existentes)

**Mapeamento:**
- `Cliente.rota_rca` ← `Vendedor.nome` (quando Vendedor encontrado)
- `Cliente.supervisor_id` ← `Vendedor.supervisor_id` (quando Vendedor encontrado)
- `Cliente.vendedor_id` ← `Vendedor.id` (quando Vendedor encontrado e campo existir)

### 3. Nova Função: `process_supervisores_vendedores_clientes`

**Arquivo:** `src/dw/etl.py`

**Função:** Orquestra o processamento completo de supervisores, vendedores e enriquecimento de clientes.

**Fluxo:**
1. Processa CSV "Supervisor pasta 1.xlsx - Sheet1.csv" → cria/atualiza Supervisores e Vendedores
2. Processa CSV "Clientes ativos.xls - Clientes ativos.csv" → enriquece Clientes

### 4. Script de Execução: `run_etl_supervisores_vendedores.py`

**Arquivo:** `scripts/run_etl_supervisores_vendedores.py`

**Função:** Script para executar o ETL de supervisores, vendedores e clientes.

**Uso:**
```bash
python scripts/run_etl_supervisores_vendedores.py
```

### 5. Script de Validação: `diagnostico_pos_etl.py`

**Arquivo:** `scripts/diagnostico_pos_etl.py`

**Função:** Valida os resultados do ETL e mostra estatísticas de preenchimento.

**Métricas:**
- Total de clientes ativos
- Quantos têm `rota_rca` não nulo
- Quantos têm `supervisor_id` não nulo
- Na query "clientes sem compra há +60 dias":
  - Total de clientes
  - Quantos têm `vendedor_nome`
  - Quantos têm `supervisor_nome`

**Uso:**
```bash
python scripts/diagnostico_pos_etl.py
```

## 🔄 COMPATIBILIDADE

### Modelos Não Alterados

Os modelos `Cliente`, `Vendedor` e `Supervisor` **não foram alterados**. O ETL apenas preenche campos existentes:
- `Cliente.rota_rca` (já existia)
- `Cliente.supervisor_id` (já existia)
- `Cliente.vendedor_id` (já existia, opcional)
- `Vendedor.codigo` (já existia)
- `Vendedor.supervisor_id` (já existia)
- `Supervisor.codigo`, `Supervisor.nome`, `Supervisor.gerente`, `Supervisor.pasta` (já existiam)

### Queries Não Alteradas

As queries existentes **não foram alteradas**. O ETL apenas preenche dados que as queries já utilizam:
- `get_clientes_sem_compra_ha_dias` já faz JOIN com Vendedor e Supervisor
- O mapper já monta a tabela com colunas "Vendedor" e "Supervisor"
- O frontend já exibe essas colunas

## 📊 RESULTADOS ESPERADOS

Após executar o ETL:

1. **Supervisores:** Criados/atualizados a partir do CSV "Supervisor pasta 1"
2. **Vendedores:** Criados/atualizados com `codigo` = rota (ex.: "ROTA 301") e `supervisor_id` preenchido
3. **Clientes:** Enriquecidos com `rota_rca` e `supervisor_id` quando há correspondência com Vendedor

**Métricas de sucesso:**
- ≥ 80% dos clientes sem compra há +60 dias devem ter `vendedor_nome`
- ≥ 80% dos clientes sem compra há +60 dias devem ter `supervisor_nome`

## 🚀 COMO USAR

### 1. Executar o ETL

```bash
python scripts/run_etl_supervisores_vendedores.py
```

### 2. Validar resultados

```bash
python scripts/diagnostico_pos_etl.py
```

### 3. Verificar no frontend

Fazer a pergunta: "Quais clientes estão com cadastro ativo, mas sem nenhuma compra por mais de 60 dias?"

Verificar se as colunas **VENDEDOR** e **SUPERVISOR** estão preenchidas na tabela "Dados Analíticos - Consulta Geral".

## 📝 NOTAS TÉCNICAS

### Mapeamento Código Numérico → Rota

O CSV "Clientes ativos" usa "Vendedor 1" como código numérico (ex.: 1301), enquanto o CSV "Supervisor pasta 1" usa "Vendedor" como rota (ex.: "ROTA 301").

O ETL resolve isso:
1. No processamento de "Supervisor pasta 1", armazena mapeamento código numérico → rota
2. No enriquecimento de clientes, busca vendedor primeiro por código numérico, depois por rota

### Tratamento de Dados Faltantes

- Se "Vendedor 1" não existir no CSV de clientes → cliente não é atualizado
- Se vendedor não for encontrado para "Vendedor 1" → `rota_rca` e `supervisor_id` permanecem NULL
- Se supervisor não existir para um vendedor → `supervisor_id` permanece NULL

Isso garante que dados existentes não sejam corrompidos.

## ✅ ARQUIVOS MODIFICADOS

1. `src/dw/etl.py` - Adicionadas 3 novas funções
2. `scripts/run_etl_supervisores_vendedores.py` - Novo script de execução
3. `scripts/diagnostico_pos_etl.py` - Novo script de validação

## ✅ ARQUIVOS NÃO MODIFICADOS

- `src/dw/models.py` - Modelos não alterados
- `src/dw/queries.py` - Queries não alteradas
- `src/api/mapper_handler_refatorado.py` - Mapper não alterado
- `components/ResponseDashboard.tsx` - Frontend não alterado

