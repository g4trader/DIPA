# Resumo - Fase 1: Camada de Analytics

## Data: 2025-11-16

## Objetivo

Criar uma camada de analytics (tabelas agregadas) para acelerar consultas e preparar o terreno para os modelos de ML, reduzindo a necessidade de queries pesadas em tempo real.

## Arquivos Criados

### 1. Modelos SQLAlchemy (`src/dw/models_analytics.py`)

Criados 4 modelos de tabelas de analytics:

- **`AnalyticsVendedorMes`**: Métricas mensais por vendedor
  - Meta vs Realizado, atingimento, gap, ranking
  - Indicadores de clientes (positivados, churn)
  - Diversidade de produtos (SKUs)
  
- **`AnalyticsClienteMes`**: Métricas mensais por cliente
  - Faturamento, quantidade de compras
  - Dias desde última compra
  - Churn score (reservado para ML - Fase 2)
  - Tendência de faturamento (opcional)
  
- **`AnalyticsProdutoMes`**: Métricas mensais por produto
  - Faturamento, quantidade vendida
  - Clientes ativos
  - Participação no faturamento total
  
- **`AnalyticsAlerta`**: Alertas automáticos
  - Tipos: vendedor_meta_em_risco, cliente_queda_faturamento, produto_queda_forte
  - Níveis: alto, medio, baixo
  - Detalhes em JSON

### 2. ETL de Analytics (`scripts/build_analytics.py`)

Script completo com funções para popular as tabelas:

- **`build_analytics_vendedor_mes()`**: Agrega metas e vendas por vendedor
  - Calcula meta_total, realizado_total, atingimento_pct, gap_valor
  - Calcula ranking de atingimento
  - Identifica clientes positivados e churn
  - Conta SKUs únicos
  
- **`build_analytics_cliente_mes()`**: Agrega vendas por cliente
  - Calcula faturamento_total, qtd_compras
  - Calcula dias_desde_ultima_compra
  
- **`build_analytics_produto_mes()`**: Agrega vendas por produto
  - Calcula faturamento_total, qtd_vendida
  - Conta clientes_ativos
  - Calcula participacao_no_faturamento
  
- **`build_analytics_alertas()`**: Gera alertas automáticos
  - Vendedores com atingimento < 90% e gap relevante
  - Clientes com queda > 30% vs mês anterior
  - Produtos com queda > 40% vs média 3 meses
  
- **`run_all_analytics()`**: Executa todas as funções na ordem correta

**Uso CLI:**
```bash
DB_TYPE=sqlite SQLITE_PATH=data/dipam_dw.db python -m scripts.build_analytics --mes-ano 2025-08
```

### 3. Funções de Leitura (`src/agent/queries_analytics.py`)

Funções utilitárias para o AgentService ler das tabelas analytics:

- **`get_resumo_meta_por_vendedor()`**: Resumo completo por vendedor
- **`get_piores_vendedores_por_gap()`**: Top piores por gap negativo
- **`get_melhores_vendedores_por_atingimento()`**: Top melhores por atingimento
- **`get_clientes_criticos_churn()`**: Clientes críticos por dias sem comprar
- **`get_produtos_em_queda()`**: Produtos com queda de volume
- **`get_alertas_criticos()`**: Alertas ordenados por nível

### 4. Script de Teste (`scripts/test_analytics.py`)

Script para validar as tabelas de analytics:

- Executa `run_all_analytics()`
- Imprime contagens por tabela
- Mostra top 5 vendedores com pior atingimento
- Mostra top 5 clientes por dias desde última compra
- Mostra top 5 produtos com menor faturamento

**Uso:**
```bash
DB_TYPE=sqlite SQLITE_PATH=data/dipam_dw.db python -m scripts.test_analytics --mes-ano 2025-08
```

## Arquivos Modificados

### 1. `src/dw/connection.py`

Adicionado import de `models_analytics` em:
- `init_db()` (quando `create_tables_if_not_exists=True`)
- `create_tables()`
- `drop_tables()`

Garante que as tabelas analytics sejam criadas automaticamente.

### 2. `src/run_ingestion.py`

Integrado build de analytics ao pipeline de ingestão:
- Após processar vendas, metas_vendedor e metas_departamento
- Coleta `mes_ano` únicos dos arquivos processados
- Executa `run_all_analytics()` para cada `mes_ano` encontrado
- Tratamento de erros gracioso (não quebra o pipeline se analytics falhar)

### 3. `src/agent/service.py`

Adicionado import das funções de queries_analytics:
- Funções disponíveis para uso futuro no agent
- Não altera lógica principal ainda (conforme solicitado)

## Características Técnicas

### Compatibilidade com SQLite e PostgreSQL

- Detecta `config.database.db_type`
- Usa `strftime` para SQLite
- Usa `extract` para PostgreSQL
- Queries adaptadas para cada tipo de banco

### UPSERT (Insert ou Update)

- Todas as funções de build fazem UPSERT
- Evita duplicatas usando `UniqueConstraint`
- Atualiza registros existentes se necessário

### Tratamento de Erros

- Logs detalhados em cada etapa
- Tratamento gracioso de erros (não quebra pipeline)
- Rollback automático em caso de erro crítico

### Performance

- Queries otimizadas com índices compostos
- Agregações feitas no banco (não em Python)
- Ranking calculado após inserção (evita queries complexas)

## Próximos Passos (Fase 2 - ML)

1. Preencher `churn_score` em `analytics_cliente_mes` usando modelo de ML
2. Adicionar `tendencia_faturamento_3m` em `analytics_cliente_mes`
3. Usar tabelas analytics no AgentService para acelerar respostas
4. Criar índices adicionais se necessário para otimização

## Testes

Para testar a implementação:

```bash
# 1. Criar tabelas (se necessário)
python -c "from src.dw.connection import create_tables; create_tables()"

# 2. Executar build de analytics
DB_TYPE=sqlite SQLITE_PATH=data/dipam_dw.db python -m scripts.build_analytics --mes-ano 2025-08

# 3. Testar e validar
DB_TYPE=sqlite SQLITE_PATH=data/dipam_dw.db python -m scripts.test_analytics --mes-ano 2025-08
```

## Estrutura de Dados

### analytics_vendedor_mes
- **Chave única**: `(vendedor_id, mes_ano)`
- **Índices**: vendedor_id, mes_ano, rank_atingimento, supervisor_id

### analytics_cliente_mes
- **Chave única**: `(cliente_id, mes_ano)`
- **Índices**: cliente_id, mes_ano, vendedor_id, dias_desde_ultima_compra

### analytics_produto_mes
- **Chave única**: `(codigo_produto, mes_ano)`
- **Índices**: codigo_produto, mes_ano, faturamento_total

### analytics_alertas
- **Sem chave única** (permite múltiplos alertas por entidade)
- **Índices**: tipo_alerta, mes_ano, nivel, referencia_id

## Observações

- As tabelas analytics são populadas **após** a carga de dados brutos
- O ETL pode ser executado independentemente do pipeline de ingestão
- Funções de leitura estão prontas mas **não são usadas ainda** no AgentService (conforme solicitado)
- Churn score permanece NULL até Fase 2 (ML)
- Alertas são gerados automaticamente baseados em regras de negócio simples

