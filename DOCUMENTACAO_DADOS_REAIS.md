# 📊 DOCUMENTAÇÃO DE DADOS REAIS - DIPAM COPILOT™

**Versão:** 1.0.0  
**Data:** Novembro 2025  
**Status:** Informações Estruturais e Exemplos

---

## ⚠️ NOTA IMPORTANTE

Este documento contém:
- **Estruturas reais** extraídas do código e banco de dados
- **Exemplos representativos** baseados na estrutura do sistema
- **Campos que devem ser preenchidos** com dados reais da DIPAM

**Para obter dados 100% reais**, é necessário:
1. Conectar ao banco de dados de produção
2. Executar queries SQL para extrair departamentos, marcas, SKUs, rotas, etc.
3. Validar com a equipe de negócios da DIPAM

---

## 1. LISTA DE DEPARTAMENTOS, MARCAS E CATEGORIAS DIPAM

### 1.1. Departamentos DIPAM

**Estrutura no Banco**: Campo `departamento` na tabela `vendas` e `metas_departamento`

**Exemplos de Departamentos** (estrutura esperada):
- Mercearia Doce
- Mercearia Salgada
- Higiene
- Limpeza
- Bomboniere
- Bebidas
- Pet Care
- Outros

**⚠️ AÇÃO NECESSÁRIA**: Executar query para obter lista completa:
```sql
SELECT DISTINCT departamento 
FROM vendas 
WHERE departamento IS NOT NULL 
ORDER BY departamento;
```

### 1.2. Marcas por Departamento

**Estrutura no Banco**: Campo `marca` na tabela `produtos` (se existir) ou extraído de `desc_produto`

**Exemplos de Marcas** (estrutura esperada):

**Mercearia Salgada**:
- Nissin
- Dipam
- Gomes da Costa
- Outras marcas do portfólio

**Bomboniere**:
- Haribo
- Riclan
- Arcor
- Outras marcas do portfólio

**Higiene**:
- Marcas de higiene pessoal
- Marcas de higiene bucal

**⚠️ AÇÃO NECESSÁRIA**: Executar query para obter lista completa:
```sql
SELECT DISTINCT marca, departamento 
FROM produtos 
WHERE marca IS NOT NULL 
ORDER BY departamento, marca;
```

### 1.3. Categorias por Produto

**Estrutura no Banco**: Campo `categoria` ou `secao` na tabela `produtos` ou `vendas`

**Exemplos de Categorias** (estrutura esperada):
- Biscoito
- Massa
- Doce
- Refrigerante
- Snacks
- Sopas
- Petiscos
- Balas
- Cerveja
- Outras categorias

**⚠️ AÇÃO NECESSÁRIA**: Executar query para obter lista completa:
```sql
SELECT DISTINCT categoria, departamento 
FROM produtos 
WHERE categoria IS NOT NULL 
ORDER BY departamento, categoria;
```

### 1.4. Lista Resumida (10 Principais)

**10 Principais Departamentos** (exemplos):
1. Mercearia Doce
2. Mercearia Salgada
3. Higiene
4. Limpeza
5. Bomboniere
6. Bebidas
7. Pet Care
8. [Outros departamentos reais]

**10 Principais Marcas** (exemplos):
1. Nissin
2. Dipam
3. Gomes da Costa
4. Haribo
5. Riclan
6. Arcor
7. [Outras marcas reais]

**10 Principais Categorias** (exemplos):
1. Biscoito
2. Massa
3. Doce
4. Refrigerante
5. Snacks
6. Sopas
7. Petiscos
8. Balas
9. Cerveja
10. [Outras categorias reais]

---

## 2. ESTRUTURA REAL DAS ROTAS RCA

### 2.1. Quantidade de Rotas

**Estrutura no Banco**: Tabela `vendedores` com campo `codigo` (ex.: "ROTA 77")

**Quantidade Aproximada**: ~63 rotas ativas (baseado em dados de agosto/2025)

**⚠️ AÇÃO NECESSÁRIA**: Executar query para obter quantidade exata:
```sql
SELECT COUNT(DISTINCT codigo) 
FROM vendedores 
WHERE ativo = 1;
```

### 2.2. Exemplo de Rota Real

**Formato**: `ROTA [NÚMERO] – [CIDADE/REGIÃO]`

**Exemplos** (estrutura esperada):
- ROTA 01 – Porto Alegre
- ROTA 02 – Canoas
- ROTA 22 – Lajeado
- ROTA 77 – Caxias do Sul
- ROTA 94 – Novo Hamburgo
- ROTA 101 – Lajeado

**Estrutura no Banco**:
- `vendedores.codigo` → "ROTA 77"
- `vendedores.nome` → Nome do vendedor
- `vendedores.rota_rca` → Rota do RCA (pode ser igual ao código)

**⚠️ AÇÃO NECESSÁRIA**: Executar query para obter lista completa:
```sql
SELECT codigo, nome, rota_rca, supervisor_id 
FROM vendedores 
WHERE ativo = 1 
ORDER BY codigo;
```

### 2.3. Relação Supervisor → RCA

**Estrutura no Banco**: 
- `supervisores.id` → ID do supervisor
- `vendedores.supervisor_id` → FK para supervisor
- `supervisores.pasta` → Pasta do supervisor (ex.: "Pasta Verde", "Pasta Amarela")

**Exemplos** (estrutura esperada):

**Supervisor José** – 12 RCAs
- ROTA 01
- ROTA 02
- ROTA 22
- [9 RCAs adicionais]

**Supervisor Maria** – 9 RCAs
- ROTA 77
- ROTA 94
- [7 RCAs adicionais]

**Supervisor Leandro** – 10 RCAs
- ROTA 101
- [9 RCAs adicionais]

**⚠️ AÇÃO NECESSÁRIA**: Executar query para obter lista completa:
```sql
SELECT 
    s.nome AS supervisor,
    s.pasta,
    COUNT(v.id) AS total_rcas,
    GROUP_CONCAT(v.codigo, ', ') AS rotas
FROM supervisores s
LEFT JOIN vendedores v ON s.id = v.supervisor_id AND v.ativo = 1
GROUP BY s.id, s.nome, s.pasta
ORDER BY s.nome;
```

---

## 3. SKUs REAIS

### 3.1. Estrutura de SKU

**Estrutura no Banco**: Tabela `produtos` (se existir) ou extraído de `vendas.codigo_produto`

**Campos Esperados**:
- `codigo` (SKU)
- `nome` / `desc_produto`
- `marca`
- `categoria`
- `departamento`
- `peso` (se disponível)
- `unidade_venda` (se disponível)

### 3.2. Exemplos de SKUs por Marca

**Formato**: `SKU | Nome | Marca | Categoria | Peso | Unidade de venda`

#### 5 SKUs Nissin (exemplos):
| SKU | Nome | Marca | Categoria | Peso | Unidade de venda |
|-----|------|-------|-----------|------|------------------|
| NIS001 | Miojo Nissin Galinha | Nissin | Massa Instantânea | 85g | Unidade |
| NIS002 | Miojo Nissin Carne | Nissin | Massa Instantânea | 85g | Unidade |
| NIS003 | Miojo Nissin Camarão | Nissin | Massa Instantânea | 85g | Unidade |
| NIS004 | Miojo Nissin Bacon | Nissin | Massa Instantânea | 85g | Unidade |
| NIS005 | Miojo Nissin Picanha | Nissin | Massa Instantânea | 85g | Unidade |

#### 5 SKUs Dipam (exemplos):
| SKU | Nome | Marca | Categoria | Peso | Unidade de venda |
|-----|------|-------|-----------|------|------------------|
| DIP001 | [Produto Dipam 1] | Dipam | [Categoria] | [Peso] | [Unidade] |
| DIP002 | [Produto Dipam 2] | Dipam | [Categoria] | [Peso] | [Unidade] |
| DIP003 | [Produto Dipam 3] | Dipam | [Categoria] | [Peso] | [Unidade] |
| DIP004 | [Produto Dipam 4] | Dipam | [Categoria] | [Peso] | [Unidade] |
| DIP005 | [Produto Dipam 5] | Dipam | [Categoria] | [Peso] | [Unidade] |

#### 5 SKUs Dr. Oetker (exemplos):
| SKU | Nome | Marca | Categoria | Peso | Unidade de venda |
|-----|------|-------|-----------|------|------------------|
| OET001 | [Produto Dr. Oetker 1] | Dr. Oetker | [Categoria] | [Peso] | [Unidade] |
| OET002 | [Produto Dr. Oetker 2] | Dr. Oetker | [Categoria] | [Peso] | [Unidade] |
| OET003 | [Produto Dr. Oetker 3] | Dr. Oetker | [Categoria] | [Peso] | [Unidade] |
| OET004 | [Produto Dr. Oetker 4] | Dr. Oetker | [Categoria] | [Peso] | [Unidade] |
| OET005 | [Produto Dr. Oetker 5] | Dr. Oetker | [Categoria] | [Peso] | [Unidade] |

#### 5 SKUs Gomes da Costa (exemplos):
| SKU | Nome | Marca | Categoria | Peso | Unidade de venda |
|-----|------|-------|-----------|------|------------------|
| GOM001 | [Produto Gomes da Costa 1] | Gomes da Costa | [Categoria] | [Peso] | [Unidade] |
| GOM002 | [Produto Gomes da Costa 2] | Gomes da Costa | [Categoria] | [Peso] | [Unidade] |
| GOM003 | [Produto Gomes da Costa 3] | Gomes da Costa | [Categoria] | [Peso] | [Unidade] |
| GOM004 | [Produto Gomes da Costa 4] | Gomes da Costa | [Categoria] | [Peso] | [Unidade] |
| GOM005 | [Produto Gomes da Costa 5] | Gomes da Costa | [Categoria] | [Peso] | [Unidade] |

**⚠️ AÇÃO NECESSÁRIA**: Executar query para obter SKUs reais:
```sql
SELECT DISTINCT 
    codigo_produto AS sku,
    desc_produto AS nome,
    departamento,
    secao AS categoria
FROM vendas
WHERE codigo_produto IS NOT NULL
ORDER BY departamento, desc_produto
LIMIT 100;
```

---

## 4. ESTRUTURA DAS METAS REAIS

### 4.1. Como a DIPAM Recebe Metas

**Estrutura no Banco**: 
- Tabela `metas_vendedor` → Metas por RCA (vendedor)
- Tabela `metas_departamento` → Metas por supervisor/departamento

**Níveis de Meta**:
1. **Por RCA (Vendedor)**: Meta individual de cada vendedor
2. **Por Supervisor**: Meta agregada do supervisor (soma dos RCAs)
3. **Por Departamento**: Meta por departamento/supervisor

**Fonte de Dados**: CSVs mensais:
- `Metas_X_Realizado_Vendedor_[MES]_[ANO].csv`
- `Metas_X_Realizado_Departamento_[MES]_[ANO].csv`

### 4.2. Exemplo Real de Meta Mensal

**Estrutura Esperada**:

**Supervisor Leandro**
- **Meta**: R$ 1.200.000,00
- **Realizado**: R$ 980.000,00
- **Gap**: R$ 220.000,00 (negativo = não atingiu)
- **Atingimento**: 81,67%
- **Período**: Agosto 2025

**Detalhamento por RCA** (exemplo):
- ROTA 101: Meta R$ 150.000 | Realizado R$ 120.000 | Atingimento 80%
- ROTA 102: Meta R$ 180.000 | Realizado R$ 140.000 | Atingimento 77,78%
- [Outros RCAs...]

**⚠️ AÇÃO NECESSÁRIA**: Executar query para obter exemplo real:
```sql
SELECT 
    s.nome AS supervisor,
    md.mes_ano,
    md.valor_meta,
    md.valor_faturado AS realizado,
    (md.valor_meta - md.valor_faturado) AS gap,
    md.percentual_atingido_valor AS atingimento
FROM metas_departamento md
JOIN supervisores s ON md.supervisor_id = s.id
WHERE md.mes_ano = '2025-08'
ORDER BY gap DESC
LIMIT 5;
```

---

## 5. REGRAS DE POSITIVAÇÃO REAL

### 5.1. Definição de Cliente Positivado

**Regra Implementada no Sistema**:
- Cliente é considerado "positivado" quando comprou **pelo menos uma vez** no período analisado
- Campo `clientes_pos` na tabela `metas_vendedor` indica quantidade de clientes positivados

### 5.2. Quantos Dias Contam como "Positivado"?

**⚠️ NECESSÁRIO VALIDAR COM NEGÓCIOS**:
- **Hipótese 1**: Cliente que comprou no mês atual (independente de dias)
- **Hipótese 2**: Cliente que comprou nos últimos 30 dias
- **Hipótese 3**: Cliente que comprou nos últimos 60 dias

**Implementação Atual**: Cliente positivado = cliente com pelo menos 1 venda no mês

### 5.3. Limitador Oficial da DIPAM

**⚠️ NECESSÁRIO VALIDAR COM NEGÓCIOS**:
- Existe valor mínimo de compra?
- Existe quantidade mínima de SKUs?
- Existe ticket mínimo?

**Implementação Atual**: Apenas verifica se houve compra (sem limitadores)

### 5.4. O Que Acontece se o Cliente Compra Só 1 SKU?

**⚠️ NECESSÁRIO VALIDAR COM NEGÓCIOS**:
- Cliente é considerado positivado mesmo com 1 SKU?
- Existe regra de mix mínimo de produtos?

**Implementação Atual**: Cliente é positivado mesmo com 1 SKU

### 5.5. Regra de Ticket Mínimo

**⚠️ NECESSÁRIO VALIDAR COM NEGÓCIOS**:
- Existe ticket mínimo para considerar cliente positivado?
- Qual o valor mínimo?

**Implementação Atual**: Não há validação de ticket mínimo

### 5.6. Versão Resumida (Hipótese)

**Regra de Positivação** (hipótese baseada no código):
- Cliente é "positivado" quando comprou **pelo menos 1 vez no mês**
- Não há limitador de valor mínimo
- Não há limitador de quantidade de SKUs
- Não há regra de ticket mínimo

**⚠️ VALIDAR COM EQUIPE DE NEGÓCIOS DA DIPAM**

---

## 6. MAPEAMENTO DE PERGUNTAS ESPECIAIS

### 6.1. Exemplos Reais de Perguntas

#### Exemplo 1: Churn com Período
**Pergunta**: "Quero saber os clientes que deixaram de comprar a partir de julho"

**Mapeamento**:
- **Intenção**: `clientes_risco_churn` ou `clientes_churn_produto`
- **Recorte**: Período (a partir de julho 2025)
- **Entidade**: Cliente
- **Agregação**: Listagem com risco de churn
- **Filtros**: `mes_ano >= '2025-07'` + `churn_flag = True`

#### Exemplo 2: Meta por Supervisor
**Pergunta**: "Qual a meta do supervisor Leandro em agosto?"

**Mapeamento**:
- **Intenção**: `consulta_meta` ou `resumo_supervisor`
- **Recorte**: Mês (agosto 2025)
- **Entidade**: Supervisor (Leandro)
- **Agregação**: Meta, realizado, atingimento
- **Filtros**: `supervisor_nome = 'Leandro'` + `mes_ano = '2025-08'`

#### Exemplo 3: Vendedores em Risco
**Pergunta**: "Quais vendedores têm maior risco de não bater a meta em agosto?"

**Mapeamento**:
- **Intenção**: `consulta_vendedores_performance` ou `motivo_nao_bateu_meta`
- **Recorte**: Mês (agosto 2025)
- **Entidade**: Vendedor
- **Agregação**: Ranking por gap negativo ou meta_risk_score
- **Filtros**: `mes_ano = '2025-08'` + `atingimento < 95%` OU `meta_risk_score >= 80`

#### Exemplo 4: Clientes Críticos por Rota
**Pergunta**: "Quais clientes da rota 22 estão em risco de churn?"

**Mapeamento**:
- **Intenção**: `clientes_risco_churn`
- **Recorte**: Rota (22)
- **Entidade**: Cliente
- **Agregação**: Listagem com churn_score e dias sem compra
- **Filtros**: `vendedor.codigo = 'ROTA 22'` + `churn_score >= 70`

#### Exemplo 5: Performance de Produtos
**Pergunta**: "Quais produtos tiveram queda de vendas em agosto?"

**Mapeamento**:
- **Intenção**: `produtos_baixa_venda`
- **Recorte**: Mês (agosto 2025)
- **Entidade**: Produto
- **Agregação**: Ranking por queda_score ou variação negativa
- **Filtros**: `mes_ano = '2025-08'` + `queda_score > 0` OU `variacao_pct < 0`

### 6.2. Padrões de Interpretação

**Períodos**:
- "a partir de julho" → `mes_ano >= '2025-07'`
- "últimos 3 meses" → Janela de 3 meses
- "D-120" → Clientes sem compra há 120 dias

**Entidades**:
- "supervisor X" → Filtro por `supervisor_nome`
- "rota Y" → Filtro por `vendedor.codigo`
- "cliente Z" → Filtro por `cliente.nome`

**Agregações**:
- "listagem" → Tabela com detalhes
- "ranking" → Ordenação por métrica
- "resumo" → KPIs agregados

---

## 7. PADRÕES VISUAIS (CORES, GRADIENTES, ESPAÇAMENTOS)

### 7.1. Cor Primária do Sistema

**Cor Principal**: `slate` (tons de cinza/azul escuro)
- **Background principal**: `slate-900` a `slate-950`
- **Texto principal**: `slate-100` a `slate-300`
- **Bordas**: `slate-800`

**Código Tailwind**:
```css
bg-slate-900/95 to-slate-950/95  /* Background gradiente */
text-slate-100                   /* Texto principal */
border-slate-800                 /* Bordas */
```

### 7.2. Cores dos KPIs Principais

**KPIs por Status**:

1. **Faturamento do Mês** (neutro):
   - Cor: `slate-100`
   - Background: `slate-900/80 to-slate-950/80`
   - Borda: `slate-800`

2. **Atingimento da Meta**:
   - **Verde** (>= 100%): `emerald-400` / `emerald-500/20`
   - **Amarelo** (95-99%): `yellow-400` / `yellow-500/20`
   - **Vermelho** (< 95%): `red-400` / `red-500/20`

3. **Vendedores em Risco**:
   - **Vermelho** (se > 0): `red-400` / `red-500/20`
   - **Verde** (se = 0): `emerald-400` / `emerald-500/20`

4. **Clientes em Alto Risco de Churn**:
   - Cor: `orange-400` / `orange-500/20`

5. **Insights Preditivos** (IA):
   - Cor: `purple-400` / `purple-500/20`
   - Badge: `purple-500/20` com texto `purple-300`

**Código Tailwind**:
```css
/* Verde (sucesso) */
text-emerald-400
bg-emerald-500/20
border-emerald-500/30

/* Amarelo (atenção) */
text-yellow-400
bg-yellow-500/20
border-yellow-500/30

/* Vermelho (risco) */
text-red-400
bg-red-500/20
border-red-500/30

/* Laranja (churn) */
text-orange-400
bg-orange-500/20
border-orange-500/30

/* Roxo (IA) */
text-purple-400
bg-purple-500/20
border-purple-500/30
```

### 7.3. Fonte Usada

**Fonte Padrão**: Sistema (sans-serif)
- **Títulos**: `font-semibold` (600)
- **Texto**: `font-medium` (500) ou padrão (400)
- **KPIs**: `font-bold` (700)
- **Labels**: `font-medium` (500) + `uppercase` + `tracking-wide`

**Tamanhos**:
- **Títulos**: `text-lg` (18px)
- **KPIs**: `text-2xl` (24px)
- **Texto**: `text-sm` (14px) ou `text-xs` (12px)

### 7.4. Bordas (Radius)

**Border Radius**:
- **Cards principais**: `rounded-2xl` (16px)
- **Ícones/avatares**: `rounded-xl` (12px) ou `rounded-lg` (8px)
- **Badges**: `rounded-full` (100%)
- **Elementos pequenos**: `rounded-lg` (8px)

**Código Tailwind**:
```css
rounded-2xl    /* 16px - Cards principais */
rounded-xl     /* 12px - Ícones */
rounded-lg     /* 8px - Elementos pequenos */
rounded-full   /* 100% - Badges circulares */
```

### 7.5. Sombra

**Sombras Utilizadas**:
- **Cards principais**: `shadow-lg` + `hover:shadow-xl`
- **Cards de insights**: `shadow-xl`

**Código Tailwind**:
```css
shadow-lg        /* Sombra padrão */
hover:shadow-xl  /* Sombra no hover */
shadow-xl        /* Sombra mais intensa */
```

### 7.6. Espaçamento Padrão

**Espaçamentos Utilizados**:

**Padding**:
- **Cards principais**: `p-5` (20px) ou `p-6` (24px)
- **Ícones**: `p-2` (8px) ou `p-3` (12px)
- **Badges**: `px-3 py-1` (12px horizontal, 4px vertical)

**Margin/Gap**:
- **Entre cards**: `gap-4` (16px)
- **Entre seções**: `space-y-6` (24px vertical)
- **Entre elementos**: `gap-2` (8px) ou `gap-3` (12px)
- **Margin bottom**: `mb-1` (4px), `mb-2` (8px), `mb-3` (12px), `mb-4` (16px)

**Código Tailwind**:
```css
p-5              /* 20px - Padding card */
p-6              /* 24px - Padding card maior */
gap-4            /* 16px - Gap entre elementos */
space-y-6        /* 24px - Espaçamento vertical entre seções */
mb-2             /* 8px - Margin bottom */
```

### 7.7. Resumo dos Padrões Visuais

| Elemento | Valor | Código Tailwind |
|----------|-------|-----------------|
| **Cor primária** | Slate (cinza/azul escuro) | `slate-900`, `slate-950` |
| **Cor KPI sucesso** | Verde | `emerald-400`, `emerald-500/20` |
| **Cor KPI atenção** | Amarelo | `yellow-400`, `yellow-500/20` |
| **Cor KPI risco** | Vermelho | `red-400`, `red-500/20` |
| **Cor KPI churn** | Laranja | `orange-400`, `orange-500/20` |
| **Cor IA** | Roxo | `purple-400`, `purple-500/20` |
| **Fonte títulos** | Semibold (600) | `font-semibold` |
| **Fonte KPIs** | Bold (700) | `font-bold` |
| **Border radius cards** | 16px | `rounded-2xl` |
| **Border radius ícones** | 12px | `rounded-xl` |
| **Sombra cards** | Large | `shadow-lg` |
| **Espaçamento padrão** | 16px-24px | `gap-4`, `space-y-6` |

---

## APÊNDICE: QUERIES SQL PARA EXTRAIR DADOS REAIS

### A.1. Departamentos
```sql
SELECT DISTINCT departamento 
FROM vendas 
WHERE departamento IS NOT NULL 
ORDER BY departamento;
```

### A.2. Marcas
```sql
SELECT DISTINCT marca, departamento 
FROM produtos 
WHERE marca IS NOT NULL 
ORDER BY departamento, marca;
```

### A.3. Categorias
```sql
SELECT DISTINCT categoria, departamento 
FROM produtos 
WHERE categoria IS NOT NULL 
ORDER BY departamento, categoria;
```

### A.4. Rotas e Supervisores
```sql
SELECT 
    s.nome AS supervisor,
    s.pasta,
    COUNT(v.id) AS total_rcas,
    GROUP_CONCAT(v.codigo, ', ') AS rotas
FROM supervisores s
LEFT JOIN vendedores v ON s.id = v.supervisor_id AND v.ativo = 1
GROUP BY s.id, s.nome, s.pasta
ORDER BY s.nome;
```

### A.5. SKUs
```sql
SELECT DISTINCT 
    codigo_produto AS sku,
    desc_produto AS nome,
    departamento,
    secao AS categoria
FROM vendas
WHERE codigo_produto IS NOT NULL
ORDER BY departamento, desc_produto;
```

### A.6. Metas
```sql
SELECT 
    s.nome AS supervisor,
    md.mes_ano,
    md.valor_meta,
    md.valor_faturado AS realizado,
    (md.valor_meta - md.valor_faturado) AS gap,
    md.percentual_atingido_valor AS atingimento
FROM metas_departamento md
JOIN supervisores s ON md.supervisor_id = s.id
WHERE md.mes_ano = '2025-08'
ORDER BY gap DESC;
```

---

**Fim da Documentação**

**⚠️ PRÓXIMOS PASSOS**:
1. Executar queries SQL acima no banco de produção
2. Validar dados com equipe de negócios da DIPAM
3. Atualizar este documento com dados reais
4. Incluir regras de positivação validadas

