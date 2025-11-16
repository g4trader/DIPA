# Modelos de Dados - Dipam AI

Este documento descreve os modelos SQLAlchemy do data warehouse.

## 📊 Estrutura do Banco de Dados

### Tabelas Principais

#### 1. `dim_tempo` - Dimensão de Tempo

Tabela de dimensão temporal para facilitar análises e agregações.

**Campos**:
- `id` (PK): Identificador único
- `data` (Date, UNIQUE, INDEX): Data completa
- `ano` (Integer, INDEX): Ano
- `mes` (Integer, INDEX): Mês (1-12)
- `dia` (Integer): Dia do mês
- `trimestre` (Integer): Trimestre (1-4)
- `semestre` (Integer): Semestre (1-2)
- `dia_semana` (Integer): Dia da semana (1=Segunda, 7=Domingo)
- `nome_dia_semana` (String): Nome do dia da semana
- `nome_mes` (String): Nome do mês
- `mes_ano` (String, INDEX): "YYYY-MM" para facilitar queries
- `bimestre` (Integer): Bimestre (1-6)
- `created_at` (DateTime): Data de criação

#### 2. `supervisores` - Supervisores/Pastas

Representa os supervisores/pastas da empresa.

**Campos**:
- `id` (PK): Identificador único
- `codigo` (String(50), UNIQUE, INDEX): Código único do supervisor
- `nome` (String(255)): Nome do supervisor
- `pasta` (String(100), INDEX): Pasta associada
- `gerente` (String(255)): Gerente relacionado
- `ativo` (Boolean): Se está ativo
- `created_at`, `updated_at` (DateTime): Timestamps

**Relacionamentos**:
- `vendedores`: Vendedores sob este supervisor
- `metas_departamento`: Metas do departamento
- `clientes`: Clientes sob este supervisor

#### 3. `vendedores` - Vendedores

Representa os vendedores da empresa (ex.: "ROTA 77", "ROTA 02").

**Campos**:
- `id` (PK): Identificador único
- `codigo` (String(50), UNIQUE, INDEX): Código único (ex.: "ROTA 77")
- `nome` (String(255)): Nome do vendedor
- `nome_rca` (String(255)): Nome do RCA
- `rota_rca` (String(100)): Rota do RCA
- `supervisor_id` (FK → supervisores.id, INDEX): Supervisor relacionado
- `ativo` (Boolean): Se está ativo
- `created_at`, `updated_at` (DateTime): Timestamps

**Índices Compostos**:
- `idx_vendedor_supervisor`: (supervisor_id, ativo)

**Relacionamentos**:
- `vendas`: Vendas realizadas
- `metas_vendedor`: Metas do vendedor
- `meta_predictions`: Predições de meta
- `supervisor`: Supervisor relacionado

#### 4. `clientes` - Clientes

Representa os clientes da empresa. Baseado no CSV "Clientes ativos".

**Campos**:
- `id` (PK): Identificador único
- `cnpj_cpf` (String(18), INDEX): CNPJ/CPF do cliente
- `codigo` (String(50), UNIQUE, INDEX): Código único do cliente
- `fantasia` (String(255)): Nome fantasia
- `nome` (String(255)): Nome completo (campo "Cliente")
- `estado` (String(2), INDEX): Estado (UF)
- `municipio` (String(100), INDEX): Município/Cidade
- `regiao_administrativa` (String(100)): Região administrativa
- `local_venda` (String(100)): Local de venda
- `segmento_venda` (String(100)): Segmento de venda
- `grupo_economico` (String(100)): Grupo econômico
- `supervisor_id` (FK → supervisores.id, INDEX): Supervisor responsável
- `supervisor_responsavel` (String(255)): Nome do supervisor (histórico)
- `nome_rca` (String(255)): Nome do RCA
- `rota_rca` (String(100)): Rota do RCA
- `pasta` (String(100)): Pasta
- `consumidor_final` (Boolean): Se é consumidor final
- `bloqueado` (Boolean): Se está bloqueado
- `motivo_bloqueio` (Text): Motivo do bloqueio
- `observacoes` (Text): Observações adicionais
- `ativo` (Boolean, INDEX): Se está ativo
- `created_at`, `updated_at` (DateTime): Timestamps

**Índices Compostos**:
- `idx_cliente_estado_municipio`: (estado, municipio)
- `idx_cliente_supervisor_ativo`: (supervisor_id, ativo)

**Relacionamentos**:
- `vendas`: Vendas realizadas
- `churn_risk`: Risco de churn (1:1)
- `supervisor`: Supervisor responsável

#### 5. `vendas` - Vendas

Representa as vendas realizadas. Baseado no CSV "Detalhes de vendas" (bimestral).

**Campos**:
- `id` (PK): Identificador único
- `data_venda` (Date, INDEX): Data da venda
- `tempo_id` (FK → dim_tempo.id, INDEX): Referência à dimensão temporal
- `gerente` (String(255)): Gerente
- `supervisor_id` (FK → supervisores.id, INDEX): Supervisor
- `supervisor_nome` (String(255)): Nome do supervisor (histórico)
- `vendedor_id` (FK → vendedores.id, INDEX): Vendedor
- `vendedor_nome` (String(255)): Nome do vendedor (histórico)
- `numero_nf` (String(50), INDEX): Número da nota fiscal
- `cliente_id` (FK → clientes.id, INDEX): Cliente
- `codigo_cliente` (String(50), INDEX): Código do cliente (histórico)
- `nome_cliente` (String(255)): Nome do cliente
- `cgc_cpf_cliente` (String(18)): CNPJ/CPF do cliente
- `ramo_atividade` (String(255)): Ramo de atividade
- `cidade_cliente` (String(100)): Cidade do cliente
- `codigo_produto` (String(50), INDEX): Código do produto
- `desc_produto` (String(255)): Descrição do produto
- `departamento` (String(100), INDEX): Departamento
- `secao` (String(100)): Seção
- `valor_total_liquido` (Float): Valor total líquido
- `valor_desconto` (Float): Valor de desconto
- `qtd_caixas` (Integer): Quantidade de caixas
- `qtd_unidades` (Integer): Quantidade de unidades
- `qtd_unidades_bonificacao` (Integer): Quantidade de unidades bonificação
- `qtd_un_venda_liquida` (Integer): Quantidade unidades venda líquida
- `created_at`, `updated_at` (DateTime): Timestamps

**Índices Compostos**:
- `idx_venda_data_cliente`: (data_venda, cliente_id)
- `idx_venda_data_vendedor`: (data_venda, vendedor_id)
- `idx_venda_mes_ano_vendedor`: (data_venda, vendedor_id)
- `idx_venda_departamento_data`: (departamento, data_venda)

**Relacionamentos**:
- `cliente`: Cliente relacionado
- `vendedor`: Vendedor relacionado
- `supervisor`: Supervisor relacionado
- `tempo`: Referência temporal

#### 6. `metas_vendedor` - Metas por Vendedor

Representa as metas de vendas por vendedor e mês. Baseado no CSV "Metas X Realizado Vendedor" (mensal).

**Campos**:
- `id` (PK): Identificador único
- `vendedor_id` (FK → vendedores.id, INDEX): Vendedor
- `vendedor_nome` (String(255)): Nome do vendedor (histórico)
- `ano` (Integer, INDEX): Ano
- `mes` (Integer, INDEX): Mês
- `mes_ano` (String(7), INDEX): "YYYY-MM" para facilitar queries
- `valor_meta` (Float): Valor da meta
- `valor_faturado` (Float): Valor faturado
- `valor_parado` (Float): Valor parado
- `valor_total` (Float): Valor total (faturado + parado)
- `percentual_atingido_valor` (Float): Percentual atingido (% Ating)
- `qtd_meta` (Integer): Quantidade meta
- `qtd_cx_faturado` (Integer): Quantidade caixas faturado
- `qtd_cx_paradas` (Integer): Quantidade caixas paradas
- `total_caixas` (Integer): Total de caixas
- `percentual_atingido_volume` (Float): Percentual atingido volume (% Vol Ating)
- `meta_pos` (Integer): Meta posição
- `clientes_pos` (Integer): Clientes posição
- `percentual_atingido_pos` (Float): Percentual atingido posição (% Ating.1)
- `created_at`, `updated_at` (DateTime): Timestamps

**Índices Compostos**:
- `idx_meta_vendedor_mes_ano`: (mes_ano, vendedor_id)
- `idx_meta_vendedor_ano_mes`: (ano, mes, vendedor_id)
- `idx_meta_vendedor_percentual`: (percentual_atingido_valor, ano, mes)

**Relacionamentos**:
- `vendedor`: Vendedor relacionado

#### 7. `metas_departamento` - Metas por Departamento

Representa as metas de vendas por departamento/supervisor e mês. Baseado no CSV "Metas X Realizado Departamento" (mensal).

**Campos**:
- Similar a `metas_vendedor`, mas com `supervisor_id` ao invés de `vendedor_id`
- `departamento` (String(100), INDEX): Departamento

**Índices Compostos**:
- Similar a `metas_vendedor`

**Relacionamentos**:
- `supervisor`: Supervisor relacionado

#### 8. `meta_predictions` - Predições de Meta

Armazena predições de probabilidade de bater meta por vendedor/mês (gerado por ML).

**Campos**:
- `id` (PK): Identificador único
- `vendedor_id` (FK → vendedores.id, INDEX): Vendedor
- `ano` (Integer, INDEX): Ano
- `mes` (Integer, INDEX): Mês
- `mes_ano` (String(7), INDEX): "YYYY-MM"
- `probabilidade_atingir` (Float): Probabilidade (0-1)
- `modelo_version` (String(50)): Versão do modelo
- `created_at` (DateTime): Data de criação

**Índices Compostos**:
- `idx_meta_prediction_mes_ano_vendedor`: (mes_ano, vendedor_id)

#### 9. `churn_risk` - Risco de Churn

Armazena predições de risco de churn por cliente (gerado por ML).

**Campos**:
- `id` (PK): Identificador único
- `cliente_id` (FK → clientes.id, UNIQUE, INDEX): Cliente
- `risco_churn` (Float): Probabilidade de churn (0-1)
- `score` (String(20)): Score ('baixo', 'medio', 'alto')
- `modelo_version` (String(50)): Versão do modelo
- `created_at`, `updated_at` (DateTime): Timestamps

## 🔗 Relacionamentos

```
supervisores
  ├── vendedores (1:N)
  ├── metas_departamento (1:N)
  └── clientes (1:N)

vendedores
  ├── vendas (1:N)
  ├── metas_vendedor (1:N)
  └── meta_predictions (1:N)

clientes
  ├── vendas (1:N)
  └── churn_risk (1:1)

dim_tempo
  └── vendas (1:N)
```

## 📝 Notas

1. **Histórico**: Muitas tabelas mantêm campos de nome (ex.: `vendedor_nome`, `supervisor_nome`) para preservar histórico, mesmo que os relacionamentos possam mudar.

2. **Índices**: Todos os campos de foreign key têm índices. Índices compostos foram criados para otimizar queries comuns.

3. **Timestamps**: Todas as tabelas principais têm `created_at` e `updated_at` para tracking.

4. **Mes_ano**: Campo `mes_ano` (formato "YYYY-MM") foi adicionado em várias tabelas para facilitar queries temporais sem precisar calcular no momento da query.

5. **Dimensão Temporal**: A tabela `dim_tempo` deve ser populada antes de usar análises temporais complexas.

## 🚀 Uso

### Inicializar Banco

```bash
python src/db_init.py
```

### Usar Alembic (Migrações)

```bash
# Criar migration
alembic revision --autogenerate -m "descrição"

# Aplicar migrations
alembic upgrade head

# Reverter migration
alembic downgrade -1
```

### Usar Modelos

```python
from src.dw.models import Cliente, Venda, MetaVendedor
from src.dw.connection import get_db_session

# Usar em queries
session = next(get_db_session())
clientes = session.query(Cliente).filter(Cliente.ativo == True).all()
```




