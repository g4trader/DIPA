# 🔧 COMMIT MESSAGE: Correção ETL Vendedor e Supervisor

## Título

```
fix(etl): Corrige ETL de vendedores e supervisores conforme regras do PM
```

## Descrição

Corrige o ETL para maximizar o preenchimento de VENDEDOR e SUPERVISOR na tela "Dados Analíticos — Consulta Geral" para a pergunta "Quais clientes estão com cadastro ativo, mas sem nenhuma compra por mais de 60 dias?".

### Alterações no ETL

#### 1. TABELA SUPERVISOR (`load_supervisores_e_vendedores_from_csv`)
- `supervisor.nome` = coluna "Supervisor"
- `supervisor.gerente` = coluna "Gerente"
- Cada linha com Supervisor não vazio gera um supervisor
- Forward fill de Gerente/Supervisor/Pasta

#### 2. TABELA VENDEDOR (`load_supervisores_e_vendedores_from_csv`)
- `vendedor.codigo` = coluna "Código Vendedor" (int → string)
- `vendedor.nome` = coluna "Vendedor" (rota, ex.: "ROTA 301")
- `vendedor.supervisor_id` = FK para Supervisor onde Supervisor.nome == "Supervisor"
- Não gera vendedores sem "Código Vendedor"

#### 3. TABELA CLIENTE (`enrich_clientes_from_csv`)
- `cliente.vendedor_codigo` = valor numérico "Vendedor 1"
- Busca vendedor onde `vendedor.codigo == cliente.vendedor_codigo`
- Se encontrar: `cliente.rota_rca = vendedor.nome`, `cliente.supervisor_id = vendedor.supervisor_id`
- Se não encontrar: limpa `rota_rca` e `supervisor_id` (NULL)
- **Regra crítica**: "Nome RCA" NÃO é usado como identificador

#### 4. REPROCESSAMENTO COMPLETO (`scripts/reprocessar_dimensoes.py`)
- Limpa dados inconsistentes (clientes com rota_rca sem vendedor correspondente)
- Recria Supervisores
- Recria Vendedores
- Reprocessa Clientes com enriquecimento completo

#### 5. VALIDAÇÃO AUTOMÁTICA (`scripts/diagnostico_pos_etl.py`)
- Exibe métricas: total clientes, com vendedor_codigo, com rota_rca, com supervisor_id
- Na query "+60 dias sem compra": total, com vendedor, com supervisor
- Avaliação: ≥85% (sucesso), ≥80% (bom), 50-80% (parcial), <50% (atenção)

### Arquivos Modificados

- `src/dw/etl.py`: Funções `load_supervisores_e_vendedores_from_csv()` e `enrich_clientes_from_csv()` reescritas conforme regras do PM
- `scripts/reprocessar_dimensoes.py`: Novo script de reprocessamento completo
- `scripts/diagnostico_pos_etl.py`: Atualizado com métricas do PM

### Arquivos NÃO Modificados

- `src/dw/models.py`: Modelos não alterados (conforme solicitado)
- `src/dw/queries.py`: Queries não alteradas
- `src/api/mapper_handler_refatorado.py`: Mapper não alterado
- `components/ResponseDashboard.tsx`: Frontend não alterado

### Como Usar

```bash
# 1. Executar reprocessamento completo
python scripts/reprocessar_dimensoes.py

# 2. Validar resultados
python scripts/diagnostico_pos_etl.py
```

### Objetivo

Após o ETL corrigido, a tela "Dados Analíticos — Consulta Geral" deve exibir VENDEDOR e SUPERVISOR preenchidos para >85% dos clientes.

### Breaking Changes

Nenhum. O ETL apenas preenche campos existentes sem alterar modelos ou frontend.

