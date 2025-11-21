# 🔧 CORREÇÃO DO ETL: VENDEDOR E SUPERVISOR (REGRAS DO PM)

## 📋 RESUMO

Correção completa do ETL conforme regras definidas pelo PM para maximizar o preenchimento de **VENDEDOR** e **SUPERVISOR** na tela "Dados Analíticos — Consulta Geral".

## ✅ ALTERAÇÕES REALIZADAS

### 1. TABELA SUPERVISOR

**Arquivo:** `src/dw/etl.py` - Função `load_supervisores_e_vendedores_from_csv()`

**Regras implementadas:**
- `supervisor.nome` = coluna "Supervisor"
- `supervisor.gerente` = coluna "Gerente"
- Cada linha com Supervisor não vazio gera um supervisor
- Supervisor é criado/atualizado antes de criar vendedores (se necessário)

**Lógica:**
- Forward fill: Gerente/Supervisor/Pasta são mantidos até aparecerem novos valores
- Busca supervisor existente por nome antes de criar
- Atualiza supervisor existente se Gerente ou Pasta mudarem

### 2. TABELA VENDEDOR

**Arquivo:** `src/dw/etl.py` - Função `load_supervisores_e_vendedores_from_csv()`

**Regras implementadas:**
- `vendedor.codigo` = coluna "Código Vendedor" (int convertido para string, pois modelo usa String)
- `vendedor.nome` = coluna "Vendedor" (rota, ex.: "ROTA 301")
- `vendedor.supervisor_id` = FK para Supervisor onde Supervisor.nome == "Supervisor"
- Não gera vendedores sem "Código Vendedor"

**Lógica:**
- Processa apenas linhas com "Código Vendedor" não nulo
- Busca vendedor existente por código numérico (string)
- Cria/atualiza vendedor com supervisor_id correto

### 3. TABELA CLIENTE (ENRIQUECIMENTO)

**Arquivo:** `src/dw/etl.py` - Função `enrich_clientes_from_csv()`

**Regras implementadas:**
- `cliente.vendedor_codigo` = valor numérico "Vendedor 1" (inferido, não há campo direto)
- Busca vendedor onde `vendedor.codigo == cliente.vendedor_codigo`
- Se encontrar:
  - `cliente.rota_rca` = `vendedor.nome` (rota, ex.: "ROTA 301")
  - `cliente.supervisor_id` = `vendedor.supervisor_id`
- Se não encontrar:
  - `cliente.rota_rca` = NULL
  - `cliente.supervisor_id` = NULL

**Regra crítica implementada:**
- A coluna "Nome RCA" **NÃO** é usada como identificador
- O identificador oficial é "Vendedor 1" (código numérico)

### 4. REPROCESSAMENTO COMPLETO

**Arquivo:** `scripts/reprocessar_dimensoes.py` (NOVO)

**Funcionalidades:**
1. Limpa dados inconsistentes (clientes com rota_rca que não corresponde a vendedor)
2. Recria Supervisores a partir do CSV "Supervisor pasta 1"
3. Recria Vendedores a partir do mesmo CSV
4. Reprocessa Clientes com enriquecimento completo

**Uso:**
```bash
python scripts/reprocessar_dimensoes.py
```

### 5. VALIDAÇÃO AUTOMÁTICA

**Arquivo:** `scripts/diagnostico_pos_etl.py` (ATUALIZADO)

**Métricas exibidas:**
- Total de clientes ativos
- Quantos têm vendedor_codigo (inferido por rota_rca)
- Quantos têm rota_rca
- Quantos têm supervisor_id
- Na query "+60 dias sem compra":
  - Total
  - Com vendedor
  - Com supervisor

**Avaliação:**
- ✅ SUCESSO: ≥85% (objetivo atingido)
- ✅ BOM: ≥80% (próximo do objetivo)
- ⚠️ PARCIAL: 50-80% (melhorias necessárias)
- ⚠️ ATENÇÃO: <50% (revisar ETL)

**Uso:**
```bash
python scripts/diagnostico_pos_etl.py
```

## 🔄 COMPATIBILIDADE

### Modelos Não Alterados

Conforme solicitado, **nenhum modelo foi alterado**. O ETL trabalha com os campos existentes:
- `Supervisor.codigo`, `Supervisor.nome`, `Supervisor.gerente`, `Supervisor.pasta`
- `Vendedor.codigo` (String), `Vendedor.nome`, `Vendedor.supervisor_id`
- `Cliente.rota_rca`, `Cliente.supervisor_id`, `Cliente.vendedor_id`

### Frontend Não Alterado

Conforme solicitado, **nenhum código do frontend foi alterado**.

## 📊 FLUXO DE PROCESSAMENTO

```
1. CSV "Supervisor pasta 1.xlsx - Sheet1.csv"
   ↓
   load_supervisores_e_vendedores_from_csv()
   ↓
   Supervisores criados/atualizados
   Vendedores criados/atualizados (codigo = "Código Vendedor", nome = "Vendedor")

2. CSV "Clientes ativos.xls - Clientes ativos.csv"
   ↓
   enrich_clientes_from_csv()
   ↓
   Para cada cliente:
   - Lê "Vendedor 1" (código numérico)
   - Busca vendedor onde codigo == "Vendedor 1"
   - Se encontrar: preenche rota_rca e supervisor_id
   - Se não encontrar: limpa rota_rca e supervisor_id
```

## 🚀 COMO USAR

### 1. Executar reprocessamento completo

```bash
python scripts/reprocessar_dimensoes.py
```

Este comando:
- Limpa dados inconsistentes
- Recria Supervisores
- Recria Vendedores
- Enriquece Clientes

### 2. Validar resultados

```bash
python scripts/diagnostico_pos_etl.py
```

### 3. Verificar no frontend

Fazer a pergunta: "Quais clientes estão com cadastro ativo, mas sem nenhuma compra por mais de 60 dias?"

Verificar se as colunas **VENDEDOR** e **SUPERVISOR** estão preenchidas na tabela "Dados Analíticos — Consulta Geral".

## 📝 NOTAS TÉCNICAS

### Mapeamento Código Numérico

- CSV "Supervisor pasta 1": "Código Vendedor" (int) → `Vendedor.codigo` (string)
- CSV "Clientes ativos": "Vendedor 1" (int) → busca `Vendedor.codigo` (string)
- Conversão int → string é feita automaticamente

### Tratamento de Dados Faltantes

- Se "Vendedor 1" não existir → cliente não é atualizado
- Se vendedor não for encontrado → `rota_rca` e `supervisor_id` são limpos (NULL)
- Se supervisor não existir para vendedor → `supervisor_id` permanece NULL

### Limpeza de Dados Inconsistentes

O script `reprocessar_dimensoes.py` limpa:
- Clientes com `rota_rca` que não corresponde a nenhum vendedor ativo
- Isso garante integridade referencial

## ✅ ARQUIVOS MODIFICADOS

1. `src/dw/etl.py` - Funções `load_supervisores_e_vendedores_from_csv()` e `enrich_clientes_from_csv()` reescritas conforme regras do PM
2. `scripts/reprocessar_dimensoes.py` - Novo script de reprocessamento completo
3. `scripts/diagnostico_pos_etl.py` - Atualizado com métricas do PM

## ✅ ARQUIVOS NÃO MODIFICADOS

- `src/dw/models.py` - Modelos não alterados
- `src/dw/queries.py` - Queries não alteradas
- `src/api/mapper_handler_refatorado.py` - Mapper não alterado
- `components/ResponseDashboard.tsx` - Frontend não alterado

## 🎯 OBJETIVO FINAL

Após o ETL corrigido, a tela "Dados Analíticos — Consulta Geral" deve exibir **VENDEDOR** e **SUPERVISOR** preenchidos para **>85% dos clientes**.

