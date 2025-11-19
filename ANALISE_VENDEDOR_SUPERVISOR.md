# Análise: Por que Vendedor e Supervisor não aparecem na tabela

## Problema Identificado

As colunas "VENDEDOR" e "SUPERVISOR" estão aparecendo vazias (mostrando apenas "-") na tabela "Dados Analíticos - Consulta Geral".

## Estrutura dos Modelos

### Cliente
- `rota_rca` (String) - Campo que deveria conectar com Vendedor
- `supervisor_id` (Integer, ForeignKey) - Campo que conecta com Supervisor

### Vendedor
- `codigo` (String, unique) - Campo que deveria corresponder ao `rota_rca` do Cliente
- `nome` (String) - Nome do vendedor
- `supervisor_id` (Integer, ForeignKey) - Conecta com Supervisor

### Supervisor
- `id` (Integer, primary_key) - Chave primária
- `codigo` (String, unique) - Código único do supervisor
- `nome` (String) - Nome do supervisor

## Query Atual

A query em `src/dw/queries.py` (linha 143-144) faz:

```python
.outerjoin(Vendedor, Cliente.rota_rca == Vendedor.codigo)
.outerjoin(Supervisor, Cliente.supervisor_id == Supervisor.id)
```

## Possíveis Causas

### 1. Dados não carregados nas tabelas
- A tabela `vendedores` pode estar vazia
- A tabela `supervisores` pode estar vazia
- O processo ETL pode não estar carregando esses dados

### 2. Incompatibilidade de valores no JOIN
- `Cliente.rota_rca` pode ter valores diferentes de `Vendedor.codigo`
- Diferenças de espaços, maiúsculas/minúsculas, ou formatação
- Exemplo: "ROTA 77" vs "ROTA77" vs "rota 77"

### 3. Valores NULL ou vazios
- `Cliente.rota_rca` pode estar NULL ou vazio para muitos clientes
- `Cliente.supervisor_id` pode estar NULL para muitos clientes

### 4. Problema no processo ETL
- Os dados de vendedores podem não estar sendo extraídos dos CSVs
- Os dados de supervisores podem não estar sendo extraídos dos CSVs
- O relacionamento pode não estar sendo estabelecido corretamente

## Como Diagnosticar

### 1. Verificar se há dados nas tabelas

```sql
-- Verificar quantos vendedores existem
SELECT COUNT(*) FROM vendedores;

-- Verificar quantos supervisores existem
SELECT COUNT(*) FROM supervisores;

-- Verificar quantos clientes têm rota_rca preenchido
SELECT COUNT(*) FROM clientes WHERE rota_rca IS NOT NULL AND rota_rca != '';

-- Verificar quantos clientes têm supervisor_id preenchido
SELECT COUNT(*) FROM clientes WHERE supervisor_id IS NOT NULL;
```

### 2. Verificar correspondência entre valores

```sql
-- Verificar se há correspondência entre Cliente.rota_rca e Vendedor.codigo
SELECT DISTINCT c.rota_rca, v.codigo
FROM clientes c
LEFT JOIN vendedores v ON c.rota_rca = v.codigo
WHERE c.rota_rca IS NOT NULL
LIMIT 20;

-- Verificar exemplos de valores que não fazem match
SELECT c.rota_rca, v.codigo
FROM clientes c
LEFT JOIN vendedores v ON c.rota_rca = v.codigo
WHERE c.rota_rca IS NOT NULL AND v.codigo IS NULL
LIMIT 20;
```

### 3. Verificar o processo ETL

Verificar em `src/dw/etl.py`:
- Se os dados de vendedores estão sendo carregados
- Se os dados de supervisores estão sendo carregados
- Como o relacionamento está sendo estabelecido

## Soluções Possíveis

### Solução 1: Normalizar valores no JOIN

Se houver diferenças de formatação, podemos normalizar:

```python
# Normalizar espaços e case
.outerjoin(Vendedor, func.trim(func.upper(Cliente.rota_rca)) == func.trim(func.upper(Vendedor.codigo)))
```

### Solução 2: Usar fallback mais robusto

A query já tem fallback (linha 201-204), mas podemos melhorar:

```python
"vendedor_nome": row.vendedor_nome or row.vendedor_codigo or row.rota_id or "Não informado",
"supervisor_nome": row.supervisor_nome or row.supervisor_codigo or "Não informado",
```

### Solução 3: Carregar dados faltantes no ETL

Se os dados não estão sendo carregados, precisamos:
1. Verificar quais CSVs contêm dados de vendedores
2. Verificar quais CSVs contêm dados de supervisores
3. Ajustar o processo ETL para carregar esses dados
4. Estabelecer os relacionamentos corretamente

### Solução 4: Usar dados históricos das vendas

Se não houver tabela de vendedores, podemos usar dados históricos:

```python
# Buscar vendedor da última venda do cliente
ultima_venda_subq = (
    session.query(
        Venda.cliente_id,
        Venda.vendedor_nome,
        Venda.supervisor_nome,
        func.row_number().over(
            partition_by=Venda.cliente_id,
            order_by=Venda.data_venda.desc()
        ).label('rn')
    )
    .subquery()
)

query = query.outerjoin(
    ultima_venda_subq,
    and_(
        Cliente.id == ultima_venda_subq.c.cliente_id,
        ultima_venda_subq.c.rn == 1
    )
)
```

## Próximos Passos

1. **Verificar dados no banco**: Executar queries SQL para verificar se há dados
2. **Verificar ETL**: Verificar se o processo está carregando os dados corretamente
3. **Ajustar JOIN**: Se necessário, normalizar valores ou usar abordagem alternativa
4. **Testar**: Verificar se após os ajustes os dados aparecem corretamente

