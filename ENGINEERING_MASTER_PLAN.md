# 📘 ENGINEERING_MASTER_PLAN.md  
**Blueprint oficial do DIPAM COPILOT™ – Agente de Inteligência Comercial Enterprise**  
**Versão: 2025.11**

---

# 📑 ÍNDICE
1. Visão Geral do Projeto  
2. Arquitetura de Dados  
3. Data Warehouse Consolidado  
4. ETL Completo (Ingestão dos CSV reais)  
5. Engine de Consultas SQL  
6. IntentSpec + Orquestrador Inteligente  
7. Camada de Diagnóstico de Causas  
8. Behavior Learning (Memória do Diretor)  
9. Pós-Processamento Narrativo Executivo  
10. API e Backend  
11. Deploy Enterprise no Cloud Run  
12. Guardrails, Auditoria e Logging  
13. Prompts prontos para o Cursor  

---

# 1. VISÃO GERAL DO PROJETO

O DIPAM COPILOT™ é um **agente de inteligência comercial em tempo real** com três responsabilidades centrais:

### (1) **Responder perguntas da diretoria com profundidade real**
- metas do mês / período  
- causas do gap  
- vendedores críticos  
- rotas problemáticas  
- clientes e SKUs em queda  
- tendências  
- plano de ação  

### (2) **Aprender feedback humano (Behavior Learning)**
O diretor diz:
> “Para esse tipo de análise, ignore os dados da pasta verde.”

O agente:
- registra a regra  
- armazena no behavior memory  
- aplica automaticamente em todas as análises similares  
- só desfaz se o Diretor pedir explicitamente  

### (3) **Operar sobre dados reais e consolidados, nunca inventados**
Usando unicamente os CSV reais da DIPAM (nov/24 a out/25), transformados em DW corporativo.

---

# 2. ARQUITETURA DE DADOS

### Camadas

data_raw/          → CSVs reais do cliente
ETL                → Normalização + Harmonização + Dimensões/Fatos
DW (SQLite/PG)     → Modelo relacional corporativo
Queries Engine     → SQL de alto nível
Orquestrador       → IntentSpec → SQL → Causas → Pós-Processamento
Behavior Memory    → Aprendizado contínuo do Diretor
Resposta Executiva → JSON final + narrativa
API / Cloud Run    → Endpoint /ask
Frontend Vercel    → Interface do COPILOT

---

# 3. DATA WAREHOUSE CONSOLIDADO

## 3.1 Tabelas Dimensão

### **dim_cliente**
- cliente_id (PK)  
- nome  
- canal  
- cidade  
- uf  
- rota_id  
- ativo  

### **dim_vendedor**
- vendedor_id (PK)  
- nome  
- rota_id  
- supervisor_id  

### **dim_supervisor**
- supervisor_id (PK)  
- nome  
- pasta  

### **dim_produto**
- produto_id (PK)  
- sku  
- descricao  
- marca  
- categoria  

---

## 3.2 Tabelas Fato

### **fato_vendas_detalhado**
- venda_id (PK)  
- data  
- ano  
- mes  
- cliente_id  
- vendedor_id  
- supervisor_id  
- produto_id  
- quantidade  
- valor_total  

### **fato_metas_departamento_mensal**
- ano  
- mes  
- departamento  
- meta_valor  
- realizado_valor  
- atingimento_pct  

### **fato_metas_vendedor_mensal**
- ano  
- mes  
- vendedor_id  
- meta_valor  
- realizado_valor  
- atingimento_pct  

---

# 4. ETL COMPLETO (CSV → DW)

## 4.1 Regras Gerais

- Ler todos os arquivos da pasta data_raw/  
- Unificar períodos quebrados (Jan–Fev, Mar–Abr, Jul–Ago etc.)  
- Detectar colunas dinamicamente  
- Normalizar nomes (acentos, casos, espaços)  
- Preencher dimensões primeiro  
- Depois fatos  
- Criar logs por tabela inserida  

## 4.2 Arquivos técnicos

- src/etl/load_raw_to_dw.py  
- src/etl/utils.py  
- scripts/run_etl.sh

---

# 5. ENGINE DE CONSULTAS SQL

Criar funções em:

src/dw/queries.py

Principais funções:

- get_metas_realizado_mes(ano, mes)  
- get_metas_realizado_periodo(...)  
- get_vendas_clientes_periodo(...)  
- get_vendas_skus_periodo(...)  
- get_clientes_queda_mes(...)  
- get_skus_queda_mes(...)  
- get_metas_vendedor_mes(...)  
- get_metas_departamento_mes(...)  

Retornar sempre listas de dicts prontas para o pós-processador.

---

# 6. INTENTSPEC + ORQUESTRADOR

### IntentSpec deve ter:

tipo: "meta" | "vendas" | "mix" | "queda_clientes" | ...
periodo_inicio
periodo_fim
dimensao_principal
dimensao_secundaria
filtros
metricas

### Orquestrador

Fluxo oficial:

IntentParser → Behavior Memory → SQL Engine → Causas → Pós-Processamento → JSON Final

---

# 7. CAMADA DE DIAGNÓSTICO DE CAUSAS

Arquivo:

src/agent/causas_detector.py

Responsável por identificar:

- rotas críticas  
- vendedores problemáticos  
- clientes com queda  
- SKUs com queda  
- eventos atípicos  
- explicação clara dos motivos do gap  

Se o desempenho está negativo, a resposta precisa ser extremamente detalhada — nunca genérica.

---

# 8. BEHAVIOR LEARNING

Arquivo:

src/agent/behavior_memory.py
data/behavior_rules.json

### Requisitos:

- armazenar feedback do diretor  
- aplicar automaticamente em análises futuras  
- regras aplicadas antes da consulta SQL  
- nunca sobrescrever sem permissão  
- logar comportamento aplicado

---

# 9. PÓS-PROCESSAMENTO NARRATIVO EXECUTIVO

Arquivo:

src/agent/post_processor.py

### Estrutura da Resposta (negativo)

Resumo Executivo
Diagnóstico de Causas
- Rotas Críticas
- Vendedores Críticos
- Clientes com Queda
- SKUs com Queda

Checklist de Problemas
Plano de Ação (7 dias)
Plano de Ação (30 dias)
Tendências e Riscos

Detalhes Técnicos (JSON)

### Estrutura da Resposta (positivo)

- O que deu certo  
- Quem puxou o resultado pra cima  
- Oportunidades de expansão  
- Riscos ocultos  
- Plano de continuidade  

---

# 10. API e BACKEND

### Endpoint principal:

POST /ask

Pipeline:

input → IntentSpec → Behavior Learning → Queries → Causas → Narrativa → resposta

Garantias:

- nunca inventar números  
- sempre retornar JSON estruturado  
- confiar apenas no DW consolidado  

---

# 11. DEPLOY ENTERPRISE NO CLOUD RUN

### Serviço:

dipam-ai-backend

### Projeto:

trivihair

### Região:

us-central1

### Comando canônico:

gcloud run deploy dipam-ai-backend   --project=trivihair   --region=us-central1   --platform=managed   --image=gcr.io/trivihair/dipam-ai-backend   --set-secrets=OPENAI_API_KEY=openai-api-key:latest   --set-env-vars=DATABASE_TYPE=sqlite,DW_PATH=/app/data/dipam_dw.db   --allow-unauthenticated

### Nunca usar outros projetos.  
### Nunca alterar o nome do serviço.  
### Nunca publicar sem secret válido.

---

# 12. GUARDA-REIAS E AUDITORIA

### Codex deve verificar:

- se Cursor alterou qualquer parâmetro proibido  
- se project ID errado apareceu  
- se novas dependências inseguras foram introduzidas  
- se números no texto estão sendo inventados pelo LLM  
- se regras de Behavior Learning foram aplicadas corretamente  
- se DW está sendo consultado corretamente  

---

# 13. PROMPTS PRONTOS PARA O CURSOR

## 13.1 Criar DW

Analise todos os CSV da pasta data_raw/ e gere um DW corporativo com as tabelas descritas em ENGINEERING_MASTER_PLAN.md seção 3. Crie schema.py, init_db.py e adapte connection.py. Não remova dados existentes. Garantir compatibilidade SQLite e Postgres.

## 13.2 Criar ETL

Gerar load_raw_to_dw.py para ler todos os CSVs, harmonizar, normalizar e popular as tabelas do DW. Criar utils.py e logs claros de inserção.

## 13.3 Queries SQL

Criar dw/queries.py com todas as funções descritas na seção 5, retornando listas de dicts. Conectar ao DW via connection.py.

## 13.4 Causas

Implementar detectar_causas_para_mes conforme seção 7. Integrar ao orquestrador.

## 13.5 Behavior Memory

Criar behavior_memory.py + JSON de regras. Implementar apply_behavior_to_intent. Integrar na etapa inicial do orquestrador.

## 13.6 Pós-Processador

Criar post_processor.py construindo a resposta executiva completa. Integrar na resposta final do endpoint /ask.

## 13.7 Deploy

Atualizar Dockerfile, requirements e README_DEPLOY.md seguindo exatamente a seção 11. Deploy somente no projeto trivihair e região us-central1.
