# 📋 DOCUMENTAÇÃO TÉCNICA DIPAM COPILOT™ - 12 ITENS ESSENCIAIS

**Versão:** 1.0.0  
**Data:** Novembro 2025  
**Status:** Em Produção

---

## 1. SYSTEM PROMPT COMPLETO DO DIPAM COPILOT

### 1.1. Prompt Base do Sistema

O agente recebe como instrução base o seguinte prompt (função `_get_system_prompt_dipam_copilot` em `src/llm_integration.py`):

```
Você é o DIPAM COPILOT™, um assistente de inteligência comercial avançado da DIPAM,
voltado para diretores, supervisores e vendedores.

PERSONA:
- Fala sempre em português brasileiro
- Tom consultivo, claro e direto
- Profissional mas acessível
- Focado em insights acionáveis

REGRAS FUNDAMENTAIS - ZERO INVENÇÃO DE DADOS:
1. Use APENAS os dados numéricos e análises fornecidas no contexto JSON.
2. NUNCA invente valores, períodos, produtos, quantidades, vendedores, supervisores ou clientes.
3. Se um dado não estiver presente no contexto, NÃO cite. Use apenas o que foi fornecido.
4. Se determinado mês/produto/supervisor não estiver no contexto, NÃO mencione.
5. Use formatação brasileira para números: R$ 1.000,00 (ponto para milhar, vírgula para decimal) e 85,5% (vírgula para decimal).
6. Seja preciso: use os números exatos do contexto, sem arredondar além do necessário.

ESTRUTURA OBRIGATÓRIA EM MARKDOWN (SEMPRE SEGUIR):

Responda SEMPRE usando esta estrutura exata em Markdown:

## Resumo executivo

[Um parágrafo curto (2-4 linhas) falando com o {tratamento}, explicando o que está acontecendo de forma geral baseado nos dados. Use os números do contexto para fundamentar.]

## Números-chave

[Use bullets (-) ou linhas curtas listando os principais números por mês/produto/supervisor/cliente, conforme o tipo de análise. CITE APENAS o que está no contexto.]

Exemplos de formato:
- Agosto 2025: Meta R$ 1.280.000,00 | Realizado R$ 1.050.000,00 | Atingimento 82,0%
- Supervisor João: Meta R$ 500.000,00 | Realizado R$ 420.000,00 | Atingimento 84,0%

## Insights relevantes

[3 a 5 bullets explicando o que os números mostram. Use verbos como: "houve melhora", "observa-se queda", "há concentração", "existe risco", etc.]

- [Insight baseado nos dados do contexto]
- [Insight baseado nos dados do contexto]
- [Insight baseado nos dados do contexto]

## Ações recomendadas

[3 bullets extremamente práticas e específicas. Seja concreto: cite nomes, rotas, departamentos, produtos que estão no contexto.]

- [Ação 1: específica e acionável, citando dados do contexto]
- [Ação 2: específica e acionável, citando dados do contexto]
- [Ação 3: específica e acionável, citando dados do contexto]

## Observações sobre os dados

[OPCIONAL - Inclua apenas se:
- Faltarem dados (período incompleto, poucos meses, etc.)
- O período solicitado for maior que o disponível
- Houver limitações nos dados fornecidos
Se os dados estiverem completos, OMITA esta seção.]

[Explicação clara das limitações, mencionando o que está disponível e o que não está.]

REGRAS IMPORTANTES:
- Se o contexto indicar "tem_dados_suficientes": false ou houver "mensagem_dados_insuficientes", seja explícito sobre a limitação na seção "Observações sobre os dados".
- Se a lista de meses/produtos/clientes for curta (ex.: só 2 meses), explique isso claramente.
- Nunca responda com "não tenho dados" se o contexto tiver números - use pelo menos o que tiver.
- Se houver truncamento de listas (indicado no contexto), mencione naturalmente nas observações.
- Mantenha cada seção concisa e objetiva.
- Use Markdown corretamente: ## para títulos, - para bullets.

FOCO PARA {TRATAMENTO}:
- {ENFOQUE}
- Priorize insights de alto nível e tendências (diretor) / comparações e gaps de gestão (supervisor) / oportunidades de vendas (vendedor)
- Sugira ações de gestão e acompanhamento (diretor) / acompanhamento de equipe (supervisor) / ações práticas de campo (vendedor)
```

### 1.2. Adaptação por Papel

O prompt é adaptado dinamicamente baseado no papel do usuário:

- **Diretor**: Tratamento "Diretor", enfoque em "visão estratégica e números consolidados"
- **Supervisor**: Tratamento "Supervisor", enfoque em "equipe e performance por vendedor/rota"
- **Vendedor**: Tratamento "Vendedor", enfoque em "resultados pessoais e clientes"

### 1.3. Modelo LLM Utilizado

- **Modelo padrão**: `gpt-4o-mini` (OpenAI)
- **Configuração**: `temperature=0.3` (respostas mais determinísticas)
- **Max tokens**: Limitado por contexto (otimização automática de listas grandes)

---

## 2. PROMPT DE ESTRUTURAÇÃO DA RESPOSTA

### 2.1. Formato de Resposta Estruturada

O backend retorna respostas no formato `CopilotStructuredResponse` (definido em `src/agent/schemas_structured.py`):

```typescript
interface CopilotStructuredResponse {
  resumo_executivo: string;           // Texto gerado pelo LLM seguindo estrutura Markdown
  secoes?: SecaoResposta[];           // Seções organizadas (vendedores, clientes, produtos, recomendações)
  tabelas?: DetalheTabela[];         // Tabelas de dados estruturados
  insights_preditivos?: InsightsPreditivos;  // Previsões ML (churn, meta_risk, oportunidades)
  contexto_debug?: any;               // Dados técnicos (apenas em modo debug)
}
```

### 2.2. Regras de Estruturação

1. **Resumo Executivo**: Sempre presente, 2-4 linhas, gerado pelo LLM
2. **Seções**: Organizadas por tipo (`lista_vendedores`, `lista_clientes`, `lista_produtos`, `texto`, `lista_recomendacoes`)
3. **Tabelas**: Formato padronizado com `titulo`, `tipo`, `colunas`, `linhas`
4. **Insights Preditivos**: Opcional, apenas se modelos ML estiverem disponíveis
5. **Contexto Debug**: Sempre presente, mas colapsado por padrão no frontend

### 2.3. Ordem dos Elementos na Resposta

1. **KPIs no topo** (extraídos das seções)
2. **Resumo Executivo** (texto principal)
3. **Insights Preditivos** (se disponíveis, com badge "IA Preditiva")
4. **Seções de dados** (vendedores, clientes, produtos)
5. **Tabelas detalhadas** (com collapse/expand)
6. **Contexto Debug** (colapsado)

### 2.4. Otimização de Contexto

O sistema trunca automaticamente listas grandes antes de enviar ao LLM:

- **Vendedores**: Máximo 20 itens
- **Produtos**: Máximo 50 itens
- **Clientes**: Máximo 30 itens
- **Departamentos**: Máximo 15 itens
- **Outras listas**: Máximo 25 itens

Isso reduz custos e melhora performance.

---

## 3. PERFIS REAIS (PERSONAS)

### 3.1. Diretor Comercial

**Cargo**: Diretor de Vendas / Diretor Comercial

**Comportamentos Esperados**:
- Faz perguntas estratégicas de alto nível
- Foca em números consolidados (meta total, realizado total, atingimento médio)
- Precisa de visão executiva rápida
- Quer entender "por que não batemos a meta" de forma agregada
- Interessa-se por tendências e comparações mês a mês

**Dores e Necessidades**:
- Falta de visibilidade rápida sobre performance geral
- Dificuldade em identificar principais responsáveis por gaps
- Necessidade de insights preditivos (quem vai não bater meta)
- Quer recomendações acionáveis de alto nível

**Exemplos de Perguntas**:
- "Por que não batemos a meta no mês de agosto de 2025?"
- "Quais são os 5 vendedores com maior risco de não bater a meta?"
- "Qual a situação geral das metas dos últimos 3 meses?"

### 3.2. Supervisor de Vendas

**Cargo**: Supervisor Regional / Gerente de Vendas

**Comportamentos Esperados**:
- Foca em performance de equipe (vendedores sob sua supervisão)
- Precisa de detalhamento por rota/vendedor
- Compara performance entre vendedores
- Identifica vendedores que precisam de apoio
- Analisa clientes críticos da sua região

**Dores e Necessidades**:
- Dificuldade em acompanhar múltiplos vendedores simultaneamente
- Necessidade de identificar vendedores em risco rapidamente
- Quer entender gaps por vendedor e suas causas
- Precisa de recomendações específicas por rota

**Exemplos de Perguntas**:
- "Quais vendedores da minha equipe estão abaixo da meta?"
- "Como está a performance da rota 22 em agosto?"
- "Quais clientes da pasta amarela estão em risco de churn?"

### 3.3. Vendedor (RCA)

**Cargo**: Representante Comercial Autônomo (RCA)

**Comportamentos Esperados**:
- Foca em seus próprios resultados
- Quer saber sua meta vs realizado
- Interessa-se por clientes em risco de churn
- Busca oportunidades de crescimento com clientes existentes
- Precisa de recomendações práticas de campo

**Dores e Necessidades**:
- Falta de visibilidade sobre sua própria performance
- Dificuldade em identificar clientes que precisam de atenção
- Necessidade de entender oportunidades de upsell/cross-sell
- Quer saber quais produtos focar

**Exemplos de Perguntas**:
- "Qual minha meta e realizado do mês?"
- "Quais meus clientes estão em risco de churn?"
- "Quais clientes têm potencial de crescimento?"

### 3.4. Analista de Dados (Interno)

**Cargo**: Analista de BI / Dados

**Comportamentos Esperados**:
- Usa o sistema para validar análises
- Precisa de dados técnicos detalhados
- Acessa contexto_debug para entender cálculos
- Faz perguntas complexas com múltiplos filtros

**Dores e Necessidades**:
- Necessidade de transparência nos cálculos
- Quer entender origem dos dados
- Precisa validar consistência dos números

---

## 4. REGRAS DE NEGÓCIO DA DIPAM

### 4.1. Definição de Cliente Crítico

**Regra**: Cliente é considerado "crítico" quando:

1. **Churn Score >= 70** (alto risco de churn)
   - Calculado por modelo ML ou heurística RFM
   - Baseado em: recency, frequency, monetary dos últimos 12 meses

2. **Dias desde última compra > 60 dias** (para clientes que compravam regularmente)

3. **Queda de faturamento > 30%** nos últimos 3 meses vs média histórica

4. **Cliente positivado sem compra** de produto específico (quando aplicável)

**Implementação**: `src/ml/scoring.py` - função `calcular_churn_score()`

### 4.2. Definição de Churn

**Regra**: Cliente é considerado "churnado" quando:

1. **Churn Flag = True** na tabela `analytics_cliente_mes`
   - Calculado por modelo ML (probabilidade >= 0.7) OU
   - Heurística: não comprou nos últimos 2-3 meses (dependendo do padrão histórico)

2. **Label de treinamento ML**: Cliente que não comprou nos próximos N meses após o mês de referência

**Implementação**: 
- `src/ml/training_pipeline.py` - função `preparar_dataset_churn()`
- `src/ml/scoring.py` - função `classificar_churn_flag()`

### 4.3. Definição de Vendedor em Risco

**Regra**: Vendedor está "em risco" quando:

1. **Atingimento < 95%** (meta não atingida ou muito próxima de não atingir)

2. **Meta Risk Score >= 80** (alto risco calculado por ML)
   - Probabilidade de não bater meta >= 0.7

3. **Gap negativo significativo** (meta - realizado > 5% da meta)

4. **Tendência negativa**: Atingimento caindo nos últimos 3 meses

**Implementação**: 
- `src/agent/queries_analytics.py` - função `get_piores_vendedores_por_gap()`
- `src/ml/predictor.py` - função `prever_risco_meta_vendedores()`

### 4.4. Definição de Meta Atingida ou Não

**Regra**: Meta é considerada "atingida" quando:

1. **Atingimento >= 100%** (realizado >= meta)

2. **Cálculo**: `atingimento = (realizado / meta) * 100`

3. **Classificação por faixas**:
   - **Verde**: >= 100% (meta atingida)
   - **Amarelo**: 95% - 99,9% (próximo de atingir, atenção)
   - **Vermelho**: < 95% (não atingida, risco)

**Implementação**: `src/agent/queries_analytics.py` - função `get_metas_realizado_por_mes()`

**⚠️ IMPORTANTE**: Sempre excluir linhas de totalizador ("Totais") das queries de agregação.

### 4.5. Como São Definidas as Rotas

**Estrutura**:
- **Rota = Código do Vendedor** (ex.: "ROTA 77", "ROTA 02")
- Cada vendedor tem um `codigo` único na tabela `vendedores`
- Campo `rota_rca` armazena a rota do RCA (pode ser igual ao código)

**Hierarquia**:
```
Supervisor (Pasta)
  └── Vendedores (Rotas)
       └── Clientes
```

**Implementação**: `src/dw/models.py` - classe `Vendedor`

### 4.6. Regras de Supervisão

**Estrutura**:
- **Supervisor** gerencia múltiplos **Vendedores**
- Cada vendedor pertence a um supervisor (`supervisor_id`)
- Supervisores são organizados por **Pasta** (ex.: "Pasta Verde", "Pasta Amarela")

**Regras**:
- Supervisor pode consultar dados apenas de seus vendedores
- Metas podem ser definidas por supervisor (tabela `metas_departamento`)
- Performance agregada por supervisor é calculada somando vendedores

**Implementação**: `src/dw/models.py` - classe `Supervisor`

### 4.7. Regras por Departamento

**Estrutura**:
- **Departamento** = Categoria de produto ou linha de negócio
- Vendas são categorizadas por `departamento` na tabela `vendas`
- Metas podem ser definidas por departamento

**Regras**:
- Análise de mix de produtos por departamento
- Comparação de performance entre departamentos
- Identificação de departamentos com baixa venda

**Implementação**: `src/dw/models.py` - campo `departamento` em `Venda`

---

## 5. DADOS INTERNOS REAIS QUE O COPILOT PRECISA CONHECER

### 5.1. Departamentos da DIPAM

**Estrutura**: Armazenada no campo `departamento` da tabela `vendas`

**Exemplos** (baseado na estrutura do banco):
- Departamentos de produtos alimentícios
- Categorias por linha de negócio

**Nota**: Lista completa deve ser extraída do banco de dados em produção.

### 5.2. Marcas

**Estrutura**: Armazenada no campo `marca` da tabela `produtos` (se existir)

**Exemplos**:
- Nissin (massa instantânea)
- Outras marcas do portfólio

**Nota**: Lista completa deve ser extraída do banco de dados.

### 5.3. Categorias

**Estrutura**: Armazenada no campo `categoria` ou `departamento` da tabela `produtos`

**Exemplos**:
- Massa instantânea
- Snacks
- Bebidas
- Outras categorias

### 5.4. SKUs

**Estrutura**: 
- Tabela `produtos` com campos:
  - `codigo` (SKU único)
  - `nome` / `descricao`
  - `categoria`
  - `departamento`
  - `marca` (se disponível)

**Exemplo de 30 SKUs Nissin** (estrutura esperada):
```
- Código: NIS001, Nome: "Miojo Nissin Galinha", Categoria: "Massa Instantânea", Marca: "Nissin"
- Código: NIS002, Nome: "Miojo Nissin Carne", Categoria: "Massa Instantânea", Marca: "Nissin"
... (28 SKUs adicionais)
```

**Nota**: SKUs reais devem ser extraídos da tabela `produtos` do banco.

### 5.5. Rotas

**Estrutura**:
- Tabela `vendedores` com campo `codigo` (ex.: "ROTA 77")
- Campo `rota_rca` para rota do RCA
- Relacionamento com `supervisor_id`

**Exemplos**:
- ROTA 01, ROTA 02, ROTA 22, ROTA 77, ROTA 94, etc.

**Total**: ~63 rotas ativas (baseado em dados de agosto/2025)

### 5.6. Relação Supervisor × RCA

**Estrutura**:
```
Supervisor (id, nome, pasta)
  └── Vendedor (id, codigo, rota_rca, supervisor_id)
       └── Cliente (id, nome, vendedor_id, supervisor_id)
```

**Campos relevantes**:
- `vendedores.supervisor_id` → FK para `supervisores.id`
- `clientes.supervisor_id` → FK para `supervisores.id`
- `clientes.vendedor_id` → FK para `vendedores.id` (via relacionamento)

**Implementação**: `src/dw/models.py` - relacionamentos SQLAlchemy

### 5.7. KPIs Oficiais da Empresa

**KPIs Principais**:

1. **Meta Total** (R$)
   - Soma de todas as metas de vendedores no mês
   - Exclui totalizadores

2. **Realizado Total** (R$)
   - Soma de todas as vendas realizadas no mês
   - Calculado de `vendas.valor_total_liquido`

3. **Atingimento Médio** (%)
   - `(Realizado Total / Meta Total) * 100`
   - Média ponderada ou simples, dependendo do contexto

4. **Gap Total** (R$)
   - `Meta Total - Realizado Total`
   - Negativo quando não atingiu

5. **Total de Vendedores**
   - Contagem de vendedores únicos com meta no mês
   - Exclui totalizadores

6. **Vendedores que Bateram Meta**
   - Contagem de vendedores com atingimento >= 100%

7. **Vendedores em Risco**
   - Contagem de vendedores com atingimento < 95% OU meta_risk_score >= 80

8. **Clientes em Risco de Churn**
   - Contagem de clientes com churn_score >= 70 OU churn_flag = True

**Implementação**: `src/agent/queries_analytics.py` - função `get_metas_realizado_por_mes()`

**Valores Esperados (Agosto/2025)**:
- Meta total: R$ 17.833.053,45
- Realizado total: R$ 17.254.142,15
- Atingimento médio: 96,75%
- Total de vendedores: 63

---

## 6. FLUXO MENSAL DE INGESTÃO DE DADOS

### 6.1. Processo de Ingestão

**Fonte de Dados**: CSVs mensais fornecidos pela empresa

**Arquivos Esperados**:
1. `Vendas_[MES]_[ANO].csv` - Vendas do mês
2. `Metas_Vendedor_[MES]_[ANO].csv` - Metas por vendedor
3. `Metas_Departamento_[MES]_[ANO].csv` - Metas por departamento
4. `Clientes_Ativos.csv` - Cadastro de clientes (atualização mensal)

### 6.2. Pipeline ETL

**Script**: `src/dw/etl.py`

**Etapas**:

1. **Extração**:
   - Leitura de CSVs
   - Validação de formato
   - Detecção de encoding

2. **Transformação**:
   - Normalização de datas (formato brasileiro → ISO)
   - Conversão de valores monetários (R$ 1.000,00 → 1000.00)
   - Remoção de caracteres especiais
   - Padronização de nomes (uppercase, trim)

3. **Limpeza**:
   - Remoção de totalizadores ("Totais", "Total", etc.)
   - Validação de IDs únicos
   - Detecção de duplicatas
   - Tratamento de valores nulos

4. **Carga**:
   - Inserção/atualização no banco SQLite/PostgreSQL
   - Criação de índices
   - Validação de integridade referencial

### 6.3. Geração de Analytics

**Script**: `scripts/run_analytics_job.py`

**Processo** (após ingestão):

1. **Recalcular Analytics**:
   - `analytics_vendedor_mes` - Agregações por vendedor/mês
   - `analytics_cliente_mes` - Agregações por cliente/mês
   - `analytics_produto_mes` - Agregações por produto/mês

2. **Aplicar Scores**:
   - `churn_score` e `churn_flag` (clientes)
   - `meta_risk_score` e `meta_risk_flag` (vendedores)
   - `queda_score` (produtos)

3. **Gerar Alertas**:
   - `analytics_alertas` - Alertas automáticos (churn, meta, queda)

### 6.4. Agendamento

**Atual**: Manual (script executado após ingestão)

**Futuro**: Cloud Scheduler chamando endpoint `/admin/run_analytics_job` ou script automatizado

**Frequência**: Mensal (após fechamento do mês)

---

## 7. PIPELINE DE GERAÇÃO DO DASHBOARD

### 7.1. Fluxo Completo

```
Pergunta do Usuário
    ↓
AgentService.process_question()
    ↓
1. Detecção de Intenção (intent.py)
    ↓
2. Extração de Entidades (mes_ano, vendedor, cliente, etc.)
    ↓
3. Busca de Dados (queries_analytics.py, queries.py)
    ↓
4. Previsões ML (predictor.py) - se aplicável
    ↓
5. Construção de Resposta Estruturada (structured_response_builder.py)
    ↓
6. Geração de Texto pelo LLM (llm_integration.py)
    ↓
7. Montagem do Payload Final (CopilotStructuredResponse)
    ↓
8. Registro de Interação (interacoes_agent)
    ↓
Resposta JSON para Frontend
```

### 7.2. Componentes do Dashboard

**Backend gera**:
- `resumo_executivo`: Texto Markdown
- `secoes`: Lista de seções (vendedores, clientes, produtos)
- `tabelas`: Tabelas estruturadas
- `insights_preditivos`: Previsões ML

**Frontend renderiza**:
- **KPIs no topo**: Extraídos das seções
- **Resumo executivo**: Texto formatado
- **Insights preditivos**: Cards com badge "IA Preditiva"
- **Tabelas**: Rankings com progress bars, badges, collapse/expand

### 7.3. Ordem de Renderização

1. **KPIs** (4 cards principais)
2. **Resumo Executivo** (texto destacado)
3. **Insights Preditivos** (se disponíveis)
4. **Seções de Dados** (vendedores, clientes, produtos)
5. **Tabelas Detalhadas** (com collapse)
6. **Contexto Debug** (colapsado)

---

## 8. BUSCAS E FILTROS ESPECIAIS SUPORTADOS

### 8.1. Filtros por Período

**Formatos suportados**:
- `"agosto 2025"` → `2025-08`
- `"agosto de 2025"` → `2025-08`
- `"2025-08"` → `2025-08`
- `"últimos 3 meses"` → Janela de 3 meses
- `"últimos 6 meses"` → Janela de 6 meses

**Implementação**: `src/agent/utils/date_extraction.py`

### 8.2. Filtros por Vendedor/Rota

**Formatos suportados**:
- `"rota 22"` → Filtra por vendedor com código "ROTA 22"
- `"vendedor João"` → Busca por nome
- `"RCA 77"` → Busca por rota_rca

**Implementação**: `src/agent/intent.py` - função `extract_entities()`

### 8.3. Filtros por Supervisor/Pasta

**Formatos suportados**:
- `"pasta amarela"` → Filtra por supervisor com pasta "amarela"
- `"supervisor João"` → Busca por nome de supervisor
- `"departamento X"` → Filtra por departamento

**Implementação**: `src/agent/queries.py` - função `query_supervisor_meta()`

### 8.4. Filtros por Cliente

**Formatos suportados**:
- `"cliente X"` → Busca por nome de cliente
- `"clientes em risco"` → Filtra por churn_flag = True
- `"clientes críticos"` → Filtra por churn_score >= 70

**Implementação**: `src/agent/queries.py` - função `query_clientes_churn()`

### 8.5. Filtros Especiais (D-120, etc.)

**Formatos suportados**:
- `"D-120"` → Clientes que não compram há 120 dias
- `"últimos 30 dias"` → Janela de 30 dias
- `"este mês"` → Mês atual
- `"mês passado"` → Mês anterior

**Implementação**: `src/agent/utils/date_extraction.py`

### 8.6. Filtros Combinados

**Exemplos**:
- `"vendas da rota 22 em agosto 2025"`
- `"clientes em risco da pasta amarela"`
- `"vendedores abaixo da meta em agosto"`

**Implementação**: `src/agent/service.py` - função `process_question()`

---

## 9. FLUXOS DE TELA DO FRONTEND

### 9.1. Como Funciona o Painel

**Componente Principal**: `components/DipaPanel.tsx`

**Estrutura**:
```
┌─────────────────────────────────────┐
│  Header (Título DIPAM COPILOT™)     │
├─────────────────────────────────────┤
│                                     │
│  Área de Mensagens (scrollável)     │
│  - Mensagens do usuário (direita)   │
│  - Respostas do COPILOT (esquerda)  │
│                                     │
├─────────────────────────────────────┤
│  Campo de Input (fixo no rodapé)    │
│  [Digite sua pergunta...] [Enviar]  │
└─────────────────────────────────────┘
```

### 9.2. Ordem dos KPIs

**Componente**: `components/ResponseDashboard.tsx`

**KPIs exibidos (ordem)**:

1. **Faturamento do Mês** (R$)
   - Ícone: DollarSign
   - Cor: Neutra (slate)

2. **Atingimento da Meta** (%)
   - Ícone: Percent
   - Cor: Verde (>=100%), Amarelo (95-99%), Vermelho (<95%)

3. **Vendedores em Risco** (número)
   - Ícone: AlertCircle
   - Cor: Vermelho (se >0), Verde (se =0)

4. **Clientes em Alto Risco de Churn** (número)
   - Ícone: AlertCircle
   - Cor: Laranja
   - Apenas se `insights_preditivos.churn` estiver disponível

### 9.3. Comportamento de Loading

**Estados**:
1. **Idle**: Campo de input disponível
2. **Loading**: Spinner no campo de input, mensagem "Processando..."
3. **Success**: Resposta renderizada, scroll automático para última mensagem
4. **Error**: Mensagem de erro, campo de input disponível novamente

**Implementação**: `components/DipaPanel.tsx` - estado `isLoading`

### 9.4. Interação do Chat

**Fluxo**:
1. Usuário digita pergunta
2. Clica em "Enviar" ou pressiona Enter
3. Campo de input é limpo
4. Mensagem do usuário aparece (bubble direita)
5. Loading aparece
6. Resposta do COPILOT aparece (card esquerda)
7. Scroll automático para última mensagem

**Histórico**:
- Todas as mensagens são mantidas em estado
- Usuário pode rolar para ver histórico
- Cada resposta mantém seu próprio estado de collapse/expand

**Implementação**: `components/DipaPanel.tsx` - estado `messages`

---

## 10. DETALHES DOS MODELOS ML USADOS

### 10.1. Modelo de Churn de Clientes

**Algoritmo**: LogisticRegression ou GradientBoostingClassifier

**Features** (7 features):
1. `recency_dias_sem_compra` - Dias desde última compra
2. `frequency_fat_12m` - Número de meses com compra nos últimos 12 meses
3. `monetary_fat_12m` - Faturamento acumulado nos últimos 12 meses
4. `ticket_medio_mes` - Ticket médio do mês atual
5. `qtd_itens_mes` - Quantidade de itens comprados no mês
6. `variacao_faturamento_3m` - Variação percentual vs média dos últimos 3 meses
7. `faturamento_media_3m` - Média de faturamento dos últimos 3 meses

**Threshold**:
- **Alto risco**: `prob_churn >= 0.7` → `churn_flag = True`
- **Médio risco**: `0.4 <= prob_churn < 0.7`
- **Baixo risco**: `prob_churn < 0.4`

**Implementação**: 
- Treinamento: `src/ml/training_pipeline.py` - `preparar_dataset_churn()`
- Previsão: `src/ml/predictor.py` - `prever_churn_clientes()`

### 10.2. Modelo de Risco de Meta (Vendedores)

**Algoritmo**: LogisticRegression ou RandomForestClassifier

**Features** (8 features):
1. `atingimento_meta_atual` - Atingimento percentual atual
2. `variacao_atingimento_3m` - Variação de atingimento nos últimos 3 meses
3. `faturamento_mes` - Faturamento do mês atual
4. `faturamento_12m` - Faturamento acumulado dos últimos 12 meses
5. `qtd_clientes_ativos_mes` - Quantidade de clientes ativos no mês
6. `media_faturamento_cliente` - Média de faturamento por cliente
7. `qtd_clientes_churn_3m` - Quantidade de clientes que deram churn nos últimos 3 meses
8. `mix_produtos` - Diversidade de produtos vendidos (qtd de SKUs)

**Threshold**:
- **Alto risco**: `prob_nao_bater_meta >= 0.7` → `meta_risk_flag = True`
- **Médio risco**: `0.4 <= prob_nao_bater_meta < 0.7`
- **Baixo risco**: `prob_nao_bater_meta < 0.4`

**Implementação**:
- Treinamento: `src/ml/training_pipeline.py` - `preparar_dataset_meta_risk()`
- Previsão: `src/ml/predictor.py` - `prever_risco_meta_vendedores()`

### 10.3. Modelo de Oportunidades

**Algoritmo**: RandomForestClassifier ou GradientBoostingClassifier

**Features** (6 features):
1. `faturamento_atual` - Faturamento atual do cliente
2. `faturamento_max_12m` - Maior faturamento nos últimos 12 meses
3. `percentual_atual_vs_max_12m` - Percentual atual vs máximo histórico
4. `ticket_medio` - Ticket médio do cliente
5. `qtd_categorias_compradas` - Quantidade de categorias compradas
6. `qtd_categorias_disponiveis` - Quantidade de categorias disponíveis (se disponível)

**Threshold**:
- **Alto potencial**: `score_oportunidade >= 0.7`
- **Médio potencial**: `0.4 <= score_oportunidade < 0.7`
- **Baixo potencial**: `score_oportunidade < 0.4`

**Implementação**:
- Treinamento: `src/ml/training_pipeline.py` - `preparar_dataset_oportunidades()`
- Previsão: `src/ml/predictor.py` - `sugerir_oportunidades()`

### 10.4. Como os Insights São Ativados

**Fluxo**:

1. **Detecção de Intent**:
   - Se intent for `consulta_meta` → Ativa previsão de `meta_risk`
   - Se intent for `clientes_churn` → Ativa previsão de `churn`
   - Se intent for `clientes_oportunidades` → Ativa previsão de `oportunidades`

2. **Verificação de Modelo**:
   - Verifica se modelo está treinado (`models/registry.json`)
   - Se não estiver, retorna lista vazia (sem insights preditivos)

3. **Chamada ao Predictor**:
   - `prever_churn_clientes()` → Lista de clientes em risco
   - `prever_risco_meta_vendedores()` → Lista de vendedores em risco
   - `sugerir_oportunidades()` → Lista de clientes com potencial

4. **Inclusão na Resposta**:
   - Adiciona `insights_preditivos` ao `CopilotStructuredResponse`
   - Frontend renderiza cards com badge "IA Preditiva"

**Implementação**: `src/agent/service.py` - função `_handle_meta_query_diretor_analytics()`

---

## 11. ROADMAP REAL DO PRODUTO

### 11.1. O Que Está Planejado (Próximos 30-90 dias)

**Curto Prazo (30 dias)**:
- ✅ Migração para PostgreSQL (Cloud SQL)
- ✅ Melhorias de performance (cache de respostas)
- ✅ Dashboard de analytics avançados
- ✅ Exportação de relatórios (PDF, Excel)

**Médio Prazo (90 dias)**:
- 🔄 Integração com BigQuery (dados históricos)
- 🔄 Modelos ML mais sofisticados (deep learning opcional)
- 🔄 Notificações por email
- 🔄 Versão mobile (PWA)

### 11.2. O Que Está Congelado

**Congelado (sem previsão)**:
- ❌ Integração com sistemas externos (ERP, CRM)
- ❌ Autenticação multi-tenant
- ❌ API pública para terceiros
- ❌ Versão white-label

### 11.3. O Que É Prioridade

**Prioridade Alta**:
1. **Migração PostgreSQL** - Necessário para escalar
2. **Cache de Respostas** - Reduzir custos de LLM
3. **Melhorias de ML** - Aumentar precisão das previsões
4. **Dashboard Interativo** - Melhorar UX

**Prioridade Média**:
1. **Integração BigQuery** - Acesso a dados históricos
2. **Notificações** - Alertas proativos
3. **Exportação de Relatórios** - Funcionalidade solicitada

**Prioridade Baixa**:
1. **Versão Mobile** - Nice to have
2. **Multi-idioma** - Futuro

---

## 12. OBJETIVO FINAL DA DOCUMENTAÇÃO

### 12.1. Apresentação para Diretoria

**Foco**: Visão estratégica e de negócio

**Conteúdo**:
- O que é o DIPAM COPILOT™
- Benefícios para a empresa
- ROI esperado
- Roadmap de funcionalidades

**Formato**: Apresentação executiva (PowerPoint/PDF)

### 12.2. Documentação Interna de Engenharia

**Foco**: Detalhes técnicos para desenvolvedores internos

**Conteúdo**:
- Arquitetura do sistema
- Estrutura de código
- Como contribuir
- Processo de deploy
- Troubleshooting

**Formato**: Markdown (este documento) + README.md

### 12.3. Entrega para Desenvolvedores Externos

**Foco**: Onboarding rápido e completo

**Conteúdo**:
- Setup do ambiente
- Estrutura do projeto
- APIs e endpoints
- Exemplos de uso
- Guias de contribuição

**Formato**: Documentação completa (Markdown) + Exemplos de código

### 12.4. Objetivo Desta Documentação Específica

**Este documento** (`DOCUMENTACAO_12_ITENS.md`) serve para:

1. **Completar a documentação técnica** solicitada pelo ChatGPT 5.1
2. **Fornecer informações essenciais** sobre prompts, regras de negócio e dados internos
3. **Facilitar retomada do trabalho** após perda de histórico de conversa
4. **Servir como referência rápida** para desenvolvedores e stakeholders

**Público-alvo**: Desenvolvedores, analistas, e assistentes de IA (ChatGPT, Claude, etc.)

---

## APÊNDICE: GLOSSÁRIO DE MÉTRICAS COMERCIAIS

### A. Métricas de Meta e Realizado

- **Meta**: Valor planejado de vendas para um período (R$)
- **Realizado**: Valor efetivamente vendido no período (R$)
- **Atingimento**: Percentual de realização da meta `(realizado / meta) * 100`
- **Gap**: Diferença entre meta e realizado `meta - realizado` (negativo = não atingiu)

### B. Métricas de Churn

- **Churn**: Perda de cliente (cliente que parou de comprar)
- **Churn Score**: Score de 0-100 indicando probabilidade de churn (ML)
- **Churn Flag**: Boolean indicando se cliente está em risco (True/False)
- **Dias sem Compra**: Quantidade de dias desde a última compra

### C. Métricas de Vendedor

- **Meta Risk Score**: Score de 0-100 indicando risco de não bater meta (ML)
- **Meta Risk Flag**: Boolean indicando se vendedor está em risco
- **Vendedores em Risco**: Vendedores com atingimento < 95% OU meta_risk_score >= 80

### D. Métricas de Cliente

- **Cliente Crítico**: Cliente com churn_score >= 70 OU dias_sem_compra > 60
- **Cliente Positivado**: Cliente que comprou pelo menos uma vez
- **Ticket Médio**: Valor médio por compra `faturamento_total / qtd_compras`

### E. Métricas de Produto

- **Mix de Produtos**: Distribuição de vendas por produto/categoria
- **Participação**: Percentual de um produto no total de vendas
- **Queda Score**: Score indicando queda de vendas de um produto

---

**Fim da Documentação**

