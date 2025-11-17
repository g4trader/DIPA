# Plano de Implementação Completo - DIPAM COPILOT™

## Status Atual

### ✅ Já Implementado

1. **Modelos DW** (`src/dw/models.py`)
   - ✅ DimTempo, Supervisor, Vendedor, Cliente, Venda
   - ✅ MetaVendedor, MetaDepartamento
   - ✅ MetaPrediction, ChurnRisk, InteracaoAgent

2. **Connection** (`src/dw/connection.py`)
   - ✅ Suporte SQLite e PostgreSQL
   - ✅ Inicialização automática

3. **Config** (`src/config.py`)
   - ✅ DatabaseConfig com suporte a ambos os tipos
   - ✅ Variáveis de ambiente

4. **Behavior Memory** (`src/agent/behavior_memory.py`)
   - ✅ Armazenamento em JSON
   - ✅ Funções de carregar/salvar/aplicar

5. **Causas Detector** (`src/agent/causas_detector.py`)
   - ✅ Detecção de causas críticas
   - ✅ Integração com DW

6. **Post Processor** (`src/agent/post_processor.py`)
   - ✅ Templates negativo e positivo
   - ✅ Estruturação completa

7. **Deploy Guardrails** (`PROMPT_DEPLOY.md`)
   - ✅ Regras obrigatórias para projeto trivihair

### 🔄 A Implementar

#### ETAPA 1: ETL Completo ✅ (utils.py criado)

**Arquivo:** `src/etl/load_raw_to_dw.py`

**Funções principais:**
- `run_full_etl(raw_dir="data_raw", conn=dw_connection)`
- `load_clientes(csv_path)`
- `load_supervisores(csv_path)`
- `load_vendas(csv_paths_list)` - Unifica todos os CSVs de vendas
- `load_metas_vendedor(csv_paths_list)`
- `load_metas_departamento(csv_paths_list)`

**Status:** `src/etl/utils.py` criado com funções auxiliares.

#### ETAPA 2: Queries SQL de Alto Nível

**Arquivo:** `src/dw/queries.py`

**Funções:**
- `get_metas_realizado_mes(ano, mes)`
- `get_metas_realizado_periodo(ano_mes_inicio, ano_mes_fim)`
- `get_metas_vendedor_mes(ano, mes)`
- `get_metas_departamento_mes(ano, mes)`
- `get_vendas_clientes_periodo(ano_mes_inicio, ano_mes_fim, filtros)`
- `get_vendas_skus_periodo(ano_mes_inicio, ano_mes_fim, filtros)`
- `get_clientes_queda_mes(ano, mes, limite)`
- `get_skus_queda_mes(ano, mes, limite)`

**Status:** A criar.

#### ETAPA 3: Consolidar Integrações

**Arquivos a revisar:**
- `src/agent/orquestrador_dw.py` - Já integra causas_detector
- `src/agent/handler_dw_refatorado.py` - Já integra post_processor
- `src/dw/causas.py` - Já existe e funciona

**Status:** Maioria já integrada, revisar se necessário.

#### ETAPA 4: Revisar Deploy

**Arquivos a revisar:**
- `Dockerfile` - Verificar se copia data/dipam_dw.db
- `src/config.py` - Já suporta DATABASE_TYPE e DATABASE_URL
- `README_DEPLOY.md` - Atualizar com instruções completas

**Status:** A revisar.

## Próximos Passos

1. **Criar ETL completo** (`src/etl/load_raw_to_dw.py`)
   - Ler CSVs reais de data_raw/
   - Normalizar e popular DW
   - Testar com dados reais

2. **Criar queries.py** (`src/dw/queries.py`)
   - Funções de alto nível
   - Integrar com orquestrador

3. **Revisar deploy**
   - Dockerfile
   - README_DEPLOY.md
   - Testar no Cloud Run

4. **Documentar tudo**
   - README principal
   - Documentação de cada módulo

## Estrutura de CSVs Identificada

### Clientes ativos.xls
- Colunas: CNPJ/CPF, Código, Fantasia, Cliente, Estado, Município, Vendedor 1, Nome RCA, etc.

### Detalhes de vendas - <período>
- Colunas: Data, Gerente, Supervisor, Vendedor, Código Cliente, Nome Cliente, Produto, Valor Total Líquido, etc.

### Metas X Realizado Vendedor - <mês>
- Colunas: Vendedor, Valor Meta, Vl. Faturado, % Ating, Qtd Meta, etc.

### Metas X Realizado Departamento - <mês>
- Colunas: Similar a metas vendedor, mas por departamento/supervisor

### Supervisor pasta 1.xlsx
- Colunas: Gerente, Supervisor, Código Vendedor, Vendedor, Pastas, Departamentos

## Notas Importantes

1. **Compatibilidade**: Tudo deve funcionar com SQLite (POC) e PostgreSQL (produção)
2. **Normalização**: Usar funções de utils.py para normalizar nomes, datas, valores
3. **Logs**: Todas as operações devem ser logadas
4. **Testes**: Criar testes básicos para cada função
5. **Documentação**: Documentar cada função com docstrings

