# ENGINEERING_QUERIES.md
DIPAM COPILOT™ – Engine de Consultas para Perguntas Essenciais V1  
Versão: 2025-11-17

---

## 1. Objetivo deste documento

Este documento define, de forma **canônica**, como o backend do DIPAM COPILOT™ deve responder às primeiras perguntas estratégicas da diretoria, usando **apenas dados reais** armazenados no Data Warehouse (DW).

Ele serve como:

- Especificação funcional das consultas
- Especificação técnica (SQL canônico)
- Guia de implementação para `src/dw/queries.py`
- Referência para o Intent Router e Behavior Memory

O desenvolvedor principal é o **Cursor**.  
O auditor de qualidade é o **Codex** (via painel ChatGPT).

---

## 2. Recapitulação do modelo de dados relevante

Tabelas do DW utilizadas aqui (nomes sugeridos; o Cursor deve alinhar com o schema real):

### 2.1 Tabelas base

- `dim_cliente`  
  - `cliente_id` (PK)  
  - `codigo_cliente` (opcional)  
  - `nome`  
  - `segmento` (ex.: 'conveniencia', 'varejo', etc.)  
  - `rota_id`  
  - `ativo` (boolean)  

- `dim_vendedor`  
  - `vendedor_id` (PK)  
  - `nome`  
  - `rota_id`  
  - `equipe` (ex.: 'conveniencia', 'autosservico', etc.)  
  - `supervisor_id`  

- `dim_supervisor`  
  - `supervisor_id` (PK)  
  - `nome`  
  - `pasta` (ex.: 'verde', 'amarela', 'vermelha')  

- `dim_produto`  
  - `produto_id` (PK)  
  - `sku` (código interno)  
  - `descricao`  
  - `industria` (ex.: 'Mars', 'Nissin', 'Red Bull', 'AB Brasil')  

- `fato_vendas_detalhado`  
  - `venda_id` (PK)  
  - `data` (DATE)  
  - `ano`  
  - `mes`  
  - `cliente_id` (FK)  
  - `vendedor_id` (FK)  
  - `produto_id` (FK)  
  - `quantidade` (em unidades ou caixas; definir na ingestão)  
  - `valor_total`  

- `fato_metas_vendedor_mensal`  
  - `ano`  
  - `mes`  
  - `vendedor_id`  
  - `industria` (opcional; quando meta é por indústria)  
  - `meta_valor`  
  - `realizado_valor`  
  - `atingimento_pct`  

---

## 3. Convenções gerais de implementação

- Todas as consultas devem ser escritas em SQL compatível com **SQLite e PostgreSQL** (evitar funções específicas).
- Datas podem ser tratadas com:
  - `DATE(data)` em SQLite
  - `CAST(data AS DATE)` em PostgreSQL  
  O Cursor deve encapsular essa diferença em helpers se necessário.
- Todas as funções em `src/dw/queries.py` devem:
  - receber parâmetros simples (anos, meses, datas, filtros)
  - retornar **lista de dicts** pronta para o pós-processador.
- Behavior Memory (ex.: excluir pasta verde) deve ser aplicada **antes** de executar o SQL, acrescentando filtros adicionais, como:
  - `AND ds.pasta NOT IN ('verde')`
  - ou  
    `AND dc.segmento NOT IN (... )`, conforme regra armazenada.

---

## 4. Perguntas essenciais e consultas canônicas

A seguir, cada pergunta da diretoria, com:

- Identificador
- Descrição
- Assinatura da função em `queries.py`
- IntentSpec sugerido
- SQL canônico (lógico)

### 4.1 Q1 — Clientes ativos sem compras por mais de 60 dias

**Pergunta:**  
> Quais clientes estão com cadastro ativo, mas sem nenhuma compra por mais de 60 dias?

**Função em `queries.py`:**

```python
def get_clientes_sem_compra_ha_dias(conn, dias: int) -> list[dict]:
    ...
```

**Lógica:**  
- Cliente com `dim_cliente.ativo = 1`  
- Última venda em `fato_vendas_detalhado` anterior à data de referência - dias  
- Ou nunca comprou

**SQL (versão lógica):**

```sql
-- Q1: Clientes ativos sem compras há N dias
WITH ultima_compra AS (
    SELECT
        v.cliente_id,
        MAX(v.data) AS data_ultima_compra
    FROM fato_vendas_detalhado v
    GROUP BY v.cliente_id
),
referencia AS (
    SELECT DATE('now') AS hoje -- para SQLite em ambiente de teste;
                               -- em produção, usar parâmetro vindo da aplicação
)
SELECT
    c.cliente_id,
    c.nome,
    c.segmento,
    c.rota_id,
    u.data_ultima_compra,
    CAST((JULIANDAY(r.hoje) - JULIANDAY(u.data_ultima_compra)) AS INT) AS dias_sem_compra
FROM dim_cliente c
LEFT JOIN ultima_compra u ON u.cliente_id = c.cliente_id
CROSS JOIN referencia r
WHERE
    c.ativo = 1
    AND (
        u.data_ultima_compra IS NULL
        OR (JULIANDAY(r.hoje) - JULIANDAY(u.data_ultima_compra)) > :dias
    )
ORDER BY dias_sem_compra DESC NULLS LAST;
```

> Observação: no backend real, a data de referência deve vir como parâmetro (ex.: data de hoje no servidor) e a função deve adaptar para Postgres (`CURRENT_DATE` + `AGE`/`DATE_PART`).

---

### 4.2 Q2 — Clientes com maior queda de faturamento 2025 vs 2024

**Pergunta:**  
> Quais os clientes com maior queda de faturamento de 2025 x 2024?

**Função em `queries.py`:**

```python
def get_clientes_queda_faturamento_ano_contra_ano(conn, ano_base: int, ano_comparado: int, top_n: int = 50) -> list[dict]:
    ...
```

**Lógica:**  
- Somar faturamento por cliente em ano_base (ex.: 2024)  
- Somar faturamento por cliente em ano_comparado (ex.: 2025)  
- Calcular queda absoluta e percentual  
- Ordenar pela maior queda absoluta (valor positivo de queda)  

**SQL:**

```sql
WITH faturamento_base AS (
    SELECT
        v.cliente_id,
        SUM(v.valor_total) AS faturamento_base
    FROM fato_vendas_detalhado v
    WHERE v.ano = :ano_base
    GROUP BY v.cliente_id
),
faturamento_comp AS (
    SELECT
        v.cliente_id,
        SUM(v.valor_total) AS faturamento_comp
    FROM fato_vendas_detalhado v
    WHERE v.ano = :ano_comp
    GROUP BY v.cliente_id
),
uniao AS (
    SELECT
        COALESCE(b.cliente_id, c.cliente_id) AS cliente_id,
        COALESCE(b.faturamento_base, 0) AS faturamento_base,
        COALESCE(c.faturamento_comp, 0) AS faturamento_comp
    FROM faturamento_base b
    FULL OUTER JOIN faturamento_comp c
        ON b.cliente_id = c.cliente_id
)
SELECT
    u.cliente_id,
    c.nome,
    u.faturamento_base,
    u.faturamento_comp,
    (u.faturamento_comp - u.faturamento_base) AS delta_faturamento,
    CASE
        WHEN u.faturamento_base > 0 THEN
            (u.faturamento_comp - u.faturamento_base) * 100.0 / u.faturamento_base
        ELSE NULL
    END AS delta_percentual
FROM uniao u
JOIN dim_cliente c ON c.cliente_id = u.cliente_id
WHERE u.faturamento_comp < u.faturamento_base
ORDER BY delta_faturamento ASC
LIMIT :top_n;
```

> Para SQLite, `FULL OUTER JOIN` não existe; o Cursor deve implementar com `UNION` de LEFT/RIGHT JOIN ou criar uma view auxiliar usando essa estratégia.

---

### 4.3 Q3 — Indústria com mais vendedores fora da meta em Outubro/25

**Pergunta:**  
> Qual a indústria onde mais vendedores não atingiram as metas em Outubro/25?

**Função:**

```python
def get_industrias_com_mais_vendedores_fora_meta(conn, ano: int, mes: int, atingimento_limite: float = 100.0) -> list[dict]:
    ...
```

**SQL:**

```sql
SELECT
    fm.industria,
    COUNT(DISTINCT fm.vendedor_id) AS qtd_vendedores_fora_meta
FROM fato_metas_vendedor_mensal fm
WHERE
    fm.ano = :ano
    AND fm.mes = :mes
    AND fm.atingimento_pct < :atingimento_limite
GROUP BY fm.industria
ORDER BY qtd_vendedores_fora_meta DESC;
```

---

### 4.4 Q4 — Rotas com melhores e piores desempenhos em positivação de clientes Mars

**Pergunta:**  
> Quais as rotas com melhores e piores desempenhos em positivação de clientes com Mars?

**Função:**

```python
def get_rotas_positivacao_industria(conn, industria: str, data_inicio: str, data_fim: str) -> list[dict]:
    ...
```

**Definições:**

- Cliente positivado = cliente com pelo menos 1 venda da indústria no período.
- Positivação por rota = nº clientes positivados / nº clientes ativos na rota.

**SQL:**

```sql
WITH clientes_ativos AS (
    SELECT
        c.cliente_id,
        c.rota_id
    FROM dim_cliente c
    WHERE c.ativo = 1
),
clientes_positivados AS (
    SELECT DISTINCT
        v.cliente_id
    FROM fato_vendas_detalhado v
    JOIN dim_produto p ON p.produto_id = v.produto_id
    WHERE
        v.data BETWEEN :data_inicio AND :data_fim
        AND p.industria = :industria
),
por_rota AS (
    SELECT
        ca.rota_id,
        COUNT(DISTINCT ca.cliente_id) AS total_clientes_ativos,
        COUNT(DISTINCT CASE WHEN cp.cliente_id IS NOT NULL THEN ca.cliente_id END) AS clientes_positivados
    FROM clientes_ativos ca
    LEFT JOIN clientes_positivados cp ON cp.cliente_id = ca.cliente_id
    GROUP BY ca.rota_id
)
SELECT
    r.rota_id,
    r.total_clientes_ativos,
    r.clientes_positivados,
    CASE
        WHEN r.total_clientes_ativos > 0 THEN
            r.clientes_positivados * 100.0 / r.total_clientes_ativos
        ELSE 0
    END AS positivacao_pct
FROM por_rota r
ORDER BY positivacao_pct DESC;
```

> O pós-processador pode gerar “melhores” (top 5) e “piores” (bottom 5) a partir desse resultado.

---

### 4.5 Q5 — Itens com média de vendas mensal menor que 10 caixas

**Pergunta:**  
> Quais os itens com a média de vendas mensal, menor que 10 caixas?

**Função:**

```python
def get_itens_baixa_media_mensal(conn, meses_janela: int = 12, limite_media: float = 10.0, data_referencia: str | None = None) -> list[dict]:
    ...
```

**Lógica:**  
- Considerar janela de N meses para trás a partir de uma data de referência.  
- Calcular total de quantidade no período / nº de meses com venda (ou todos os meses da janela, decisão documentada).  
- Filtrar média < 10.

**SQL (simplificado, assumindo janela fixa de 12 meses):**

```sql
WITH periodo AS (
    SELECT
        DATE(:data_referencia, '-12 months') AS data_inicio,
        DATE(:data_referencia) AS data_fim
),
vendas_periodo AS (
    SELECT
        v.produto_id,
        STRFTIME('%Y-%m', v.data) AS ano_mes,
        SUM(v.quantidade) AS qtd_mes
    FROM fato_vendas_detalhado v
    JOIN periodo p ON v.data BETWEEN p.data_inicio AND p.data_fim
    GROUP BY v.produto_id, ano_mes
),
agregado AS (
    SELECT
        vp.produto_id,
        COUNT(DISTINCT vp.ano_mes) AS meses_com_venda,
        SUM(vp.qtd_mes) AS qtd_total
    FROM vendas_periodo vp
    GROUP BY vp.produto_id
)
SELECT
    a.produto_id,
    p.descricao,
    p.sku,
    p.industria,
    a.qtd_total,
    a.meses_com_venda,
    CASE
        WHEN a.meses_com_venda > 0 THEN a.qtd_total * 1.0 / a.meses_com_venda
        ELSE 0
    END AS media_mensal
FROM agregado a
JOIN dim_produto p ON p.produto_id = a.produto_id
WHERE media_mensal < :limite_media
ORDER BY media_mensal ASC;
```

---

### 4.6 Q6 — Recompra Snickers Duplo Chocolate (últimos 6 meses)

**Pergunta:**  
> Quais clientes compraram Snickers Duplo Chocolate nos últimos 6 meses, mas não realizaram recompra?

**Função:**

```python
def get_clientes_sem_recompra_sku(conn, sku: str, meses_janela: int = 6, data_referencia: str | None = None) -> list[dict]:
    ...
```

**Lógica:**  
- Identificar clientes que fizeram pelo menos uma compra do SKU na janela.  
- Identificar clientes que só compraram uma vez (ou que não compraram novamente após a primeira venda).  
- Para a V1, podemos começar com “comprou 1 vez apenas no período”.

**SQL (modelo):**

```sql
WITH periodo AS (
    SELECT
        DATE(:data_referencia, :janela_expr) AS data_inicio, -- ex: '-6 months'
        DATE(:data_referencia) AS data_fim
),
vendas_sku AS (
    SELECT
        v.cliente_id,
        v.data
    FROM fato_vendas_detalhado v
    JOIN dim_produto p ON p.produto_id = v.produto_id
    JOIN periodo pe ON v.data BETWEEN pe.data_inicio AND pe.data_fim
    WHERE p.descricao = :sku
),
agregado AS (
    SELECT
        vs.cliente_id,
        COUNT(*) AS qtd_compras,
        MIN(vs.data) AS primeira_compra,
        MAX(vs.data) AS ultima_compra
    FROM vendas_sku vs
    GROUP BY vs.cliente_id
)
SELECT
    a.cliente_id,
    c.nome,
    c.segmento,
    c.rota_id,
    a.qtd_compras,
    a.primeira_compra,
    a.ultima_compra
FROM agregado a
JOIN dim_cliente c ON c.cliente_id = a.cliente_id
WHERE a.qtd_compras = 1
ORDER BY a.primeira_compra;
```

---

### 4.7 Q7 — Clientes conveniência sem Red Bull Zero em Outubro

**Pergunta:**  
> Quais clientes da equipe conveniência não compraram Red Bull Zero em Outubro?

**Função:**

```python
def get_clientes_segmento_sem_sku_no_periodo(conn, segmento: str, sku: str, data_inicio: str, data_fim: str) -> list[dict]:
    ...
```

**SQL:**

```sql
WITH clientes_segmento AS (
    SELECT
        c.cliente_id,
        c.nome,
        c.rota_id
    FROM dim_cliente c
    WHERE c.segmento = :segmento
),
clientes_com_sku AS (
    SELECT DISTINCT
        v.cliente_id
    FROM fato_vendas_detalhado v
    JOIN dim_produto p ON p.produto_id = v.produto_id
    WHERE
        v.data BETWEEN :data_inicio AND :data_fim
        AND p.descricao = :sku
)
SELECT
    cs.cliente_id,
    cs.nome,
    cs.rota_id
FROM clientes_segmento cs
LEFT JOIN clientes_com_sku csku ON csku.cliente_id = cs.cliente_id
WHERE csku.cliente_id IS NULL
ORDER BY cs.nome;
```

> Obs.: se a definição de “equipe conveniência” estiver em `dim_vendedor` em vez de `segmento` do cliente, o Cursor deve ajustar o join.

---

### 4.8 Q8 — Clientes com somente 1 unidade vendida AB Brasil em Outubro

**Pergunta:**  
> Quais clientes com somente 1 unidade vendida, entre todos os itens da indústria AB Brasil, no mês de Outubro?

**Função:**

```python
def get_clientes_uma_unidade_industria_mes(conn, industria: str, ano: int, mes: int) -> list[dict]:
    ...
```

**SQL:**

```sql
SELECT
    v.cliente_id,
    c.nome,
    c.segmento,
    c.rota_id,
    SUM(v.quantidade) AS qtd_total
FROM fato_vendas_detalhado v
JOIN dim_produto p ON p.produto_id = v.produto_id
JOIN dim_cliente c ON c.cliente_id = v.cliente_id
WHERE
    v.ano = :ano
    AND v.mes = :mes
    AND p.industria = :industria
GROUP BY v.cliente_id, c.nome, c.segmento, c.rota_id
HAVING qtd_total = 1
ORDER BY c.nome;
```

---

### 4.9 Q9, Q10, Q11 — Clientes sem positivação de SKUs Mars no P12

**Perguntas:**  
> Quais clientes não tiveram positivação de Snickers Original 45g em P12?  
> Quais clientes não tiveram positivação de M&Ms Choco 40g em P12?  
> Quais clientes não tiveram positivação de M&Ms Tubo em P12?

Período P12 Mars: **06/10/2025 a 28/11/2025**

**Função genérica:**

```python
def get_clientes_sem_sku_no_periodo(conn, sku: str, data_inicio: str, data_fim: str) -> list[dict]:
    ...
```

**SQL (genérico):**

```sql
WITH clientes_ativos AS (
    SELECT
        c.cliente_id,
        c.nome,
        c.rota_id
    FROM dim_cliente c
    WHERE c.ativo = 1
),
clientes_com_sku AS (
    SELECT DISTINCT
        v.cliente_id
    FROM fato_vendas_detalhado v
    JOIN dim_produto p ON p.produto_id = v.produto_id
    WHERE
        v.data BETWEEN :data_inicio AND :data_fim
        AND p.descricao = :sku
)
SELECT
    ca.cliente_id,
    ca.nome,
    ca.rota_id
FROM clientes_ativos ca
LEFT JOIN clientes_com_sku cs ON cs.cliente_id = ca.cliente_id
WHERE cs.cliente_id IS NULL
ORDER BY ca.rota_id, ca.nome;
```

> Para Snickers Original 45g, M&Ms Choco 40g, M&Ms Tubo, basta chamar a função com o SKU correto.

---

### 4.10 Q12 — Clientes que atingiram o mix mínimo de Nissin em Outubro

**Pergunta:**  
> Quantos clientes compraram o mix mínimo de Nissin em Outubro?  
> Mix Mínimo de Nissin = itens 2257 / 2087 / 2086 + 1 item entre (2101 / 2102 / 2103)

Assumindo que:
- os códigos (2257, 2087, 2086, 2101, 2102, 2103) são `sku` em `dim_produto`.

**Função:**

```python
def get_clientes_mix_minimo_nissin_mes(conn, ano: int, mes: int) -> list[dict]:
    ...
```

**SQL:**

```sql
WITH vendas_nissin AS (
    SELECT
        v.cliente_id,
        p.sku,
        SUM(v.quantidade) AS qtd
    FROM fato_vendas_detalhado v
    JOIN dim_produto p ON p.produto_id = v.produto_id
    WHERE
        v.ano = :ano
        AND v.mes = :mes
        AND p.industria = 'Nissin'
        AND p.sku IN ('2257', '2087', '2086', '2101', '2102', '2103')
    GROUP BY v.cliente_id, p.sku
),
pivot AS (
    SELECT
        cliente_id,
        SUM(CASE WHEN sku = '2257' THEN 1 ELSE 0 END) AS tem_2257,
        SUM(CASE WHEN sku = '2087' THEN 1 ELSE 0 END) AS tem_2087,
        SUM(CASE WHEN sku = '2086' THEN 1 ELSE 0 END) AS tem_2086,
        SUM(CASE WHEN sku IN ('2101', '2102', '2103') THEN 1 ELSE 0 END) AS tem_complementar
    FROM vendas_nissin
    GROUP BY cliente_id
),
clientes_mix_ok AS (
    SELECT
        cliente_id
    FROM pivot
    WHERE
        tem_2257 > 0
        AND tem_2087 > 0
        AND tem_2086 > 0
        AND tem_complementar > 0
)
SELECT
    cmo.cliente_id,
    c.nome,
    c.rota_id
FROM clientes_mix_ok cmo
JOIN dim_cliente c ON c.cliente_id = cmo.cliente_id
ORDER BY c.rota_id, c.nome;
```

> O pós-processador pode contar quantos clientes retornaram e já responder a pergunta “Quantos clientes…?”.

---

### 4.11 Q13 — Rotas com pior desempenho no mix mínimo de Nissin (Outubro)

**Pergunta:**  
> Quais as rotas com pior desempenho no mix mínimo de Nissin, no mês de outubro?

**Função:**

```python
def get_rotas_desempenho_mix_minimo_nissin_mes(conn, ano: int, mes: int) -> list[dict]:
    ...
```

**SQL:**

```sql
WITH clientes_ativos AS (
    SELECT
        c.cliente_id,
        c.rota_id
    FROM dim_cliente c
    WHERE c.ativo = 1
),
clientes_mix_ok AS (
    -- reutiliza a CTE da consulta anterior (Q12), adaptada aqui
    WITH vendas_nissin AS (
        SELECT
            v.cliente_id,
            p.sku,
            SUM(v.quantidade) AS qtd
        FROM fato_vendas_detalhado v
        JOIN dim_produto p ON p.produto_id = v.produto_id
        WHERE
            v.ano = :ano
            AND v.mes = :mes
            AND p.industria = 'Nissin'
            AND p.sku IN ('2257', '2087', '2086', '2101', '2102', '2103')
        GROUP BY v.cliente_id, p.sku
    ),
    pivot AS (
        SELECT
            cliente_id,
            SUM(CASE WHEN sku = '2257' THEN 1 ELSE 0 END) AS tem_2257,
            SUM(CASE WHEN sku = '2087' THEN 1 ELSE 0 END) AS tem_2087,
            SUM(CASE WHEN sku = '2086' THEN 1 ELSE 0 END) AS tem_2086,
            SUM(CASE WHEN sku IN ('2101', '2102', '2103') THEN 1 ELSE 0 END) AS tem_complementar
        FROM vendas_nissin
        GROUP BY cliente_id
    )
    SELECT
        cliente_id
    FROM pivot
    WHERE
        tem_2257 > 0
        AND tem_2087 > 0
        AND tem_2086 > 0
        AND tem_complementar > 0
)
SELECT
    ca.rota_id,
    COUNT(DISTINCT ca.cliente_id) AS total_clientes_ativos,
    COUNT(DISTINCT CASE WHEN cmo.cliente_id IS NOT NULL THEN ca.cliente_id END) AS clientes_mix_ok,
    CASE
        WHEN COUNT(DISTINCT ca.cliente_id) > 0 THEN
            COUNT(DISTINCT CASE WHEN cmo.cliente_id IS NOT NULL THEN ca.cliente_id END) * 100.0
            / COUNT(DISTINCT ca.cliente_id)
        ELSE 0
    END AS pct_mix_ok
FROM clientes_ativos ca
LEFT JOIN clientes_mix_ok cmo ON cmo.cliente_id = ca.cliente_id
GROUP BY ca.rota_id
ORDER BY pct_mix_ok ASC;
```

---

## 5. Integração com Intent Router

O Intent Router deve mapear:

- Q1 → `tipo = "clientes_sem_compra"` → `get_clientes_sem_compra_ha_dias`  
- Q2 → `tipo = "queda_faturamento"` → `get_clientes_queda_faturamento_ano_contra_ano`  
- Q3 → `tipo = "meta_departamento"` → `get_industrias_com_mais_vendedores_fora_meta`  
- Q4 → `tipo = "positivacao"` → `get_rotas_positivacao_industria`  
- Q5 → `tipo = "mix"` → `get_itens_baixa_media_mensal`  
- Q6 → `tipo = "recompra"` → `get_clientes_sem_recompra_sku`  
- Q7 → `tipo = "clientes_sem_item"` (segmentado) → `get_clientes_segmento_sem_sku_no_periodo`  
- Q8 → `tipo = "vendas_baixas"` → `get_clientes_uma_unidade_industria_mes`  
- Q9/Q10/Q11 → `tipo = "clientes_sem_item"` → `get_clientes_sem_sku_no_periodo`  
- Q12 → `tipo = "mix_nissin"` (cliente) → `get_clientes_mix_minimo_nissin_mes`  
- Q13 → `tipo = "mix_nissin"` (rota) → `get_rotas_desempenho_mix_minimo_nissin_mes`

---

## 6. Behavior Memory (aplicação nas consultas)

Quando o Diretor registrar feedback como:

- “Excluir pasta verde”
- “Ignorar clientes da pasta amarela”
- “Focar apenas em conveniência”

O módulo `behavior_memory.apply_behavior_to_intent` deve:

- acrescentar filtros aos IntentSpec  
- que se traduzem em cláusulas adicionais nos SQL:

Exemplos:

- Excluir pasta verde (supervisor/cliente):

```sql
AND (ds.pasta IS NULL OR ds.pasta NOT IN ('verde'))
```

- Focar apenas em segmento conveniência:

```sql
AND c.segmento = 'conveniencia'
```

Esse comportamento deve ser transparente para `queries.py`:  
o orquestrador prepara os filtros e injeta parâmetros (ou pedaços de WHERE adicionais) de forma centralizada.

---

## 7. Testes automatizados

Para cada função de `queries.py`, o Cursor deve criar testes em:

- `tests/test_queries_essenciais.py`

Com cenários mínimos:

- DW de teste com poucos clientes, produtos, vendas, metas  
- Verificação de:
  - linhas retornadas  
  - colunas obrigatórias  
  - ausência de erro em filtros opcionais  
  - comportamento com Behavior Memory ativado (ex.: simular exclusão de pasta verde)

---

## 8. Instruções para o Cursor

1. Implementar todas as funções descritas neste documento em `src/dw/queries.py`.
2. Garantir compatibilidade com **SQLite** (dev) e **PostgreSQL** (produção futura).
3. Atualizar Intent Router e Orquestrador para usar essas funções.
4. Criar testes automatizados cobrindo cada consulta.
5. Não inventar dados; toda resposta deve vir do DW consolidado.
6. Integrar Behavior Memory antes da execução das consultas, respeitando regras do Diretor.

Fim do documento.
