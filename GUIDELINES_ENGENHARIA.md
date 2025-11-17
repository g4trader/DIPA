# 🎯 GUIDELINES DE ENGENHARIA - DIPAM COPILOT™

**Versão:** 1.0.0  
**Data:** Novembro 2025  
**Status:** Diretrizes Obrigatórias

---

## 📋 CONTEXTO DO PRODUTO

O **DIPAM COPILOT™** é um agente de inteligência comercial em tempo real para a DIPAM Gaúcha que responde perguntas em português sobre:
- Metas, vendas, clientes, vendedores, supervisores
- Rotas, categorias, marcas e SKUs

---

## 🏗️ ARQUITETURA DE DADOS

### Estado Atual

**Data Warehouse (DW) - Abstração Lógica**:
- Acessado via módulos `src/dw/*`
- **Físico atual**: SQLite (`data/dipam_dw.db`) - POC
- **Físico planejado**: PostgreSQL - Migração futura
- **BigQuery**: ❌ **NÃO IMPLEMENTADO** - Apenas roadmap futuro

### Princípios Fundamentais

1. **DW é uma ABSTRAÇÃO**
   - Hoje: SQLite
   - Amanhã: PostgreSQL
   - **NUNCA** mude a camada de negócio ao trocar o banco físico

2. **NUNCA assuma BigQuery ou serviços externos**
   - BigQuery não existe no código atual
   - Se mencionado, é apenas roadmap
   - Documente claramente quando for roadmap

3. **SEMPRE use a camada DW existente**
   - Use `src/dw/connection.py` para conexões
   - Use `src/dw/queries_*.py` para consultas
   - Use repositórios/DAOs quando existirem
   - **NUNCA** faça queries diretas no SQLite fora da camada DW

---

## 🚫 REGRAS PROIBIDAS

### ❌ NÃO FAÇA

1. **Queries diretas no SQLite**
   ```python
   # ❌ ERRADO
   import sqlite3
   conn = sqlite3.connect('data/dipam_dw.db')
   cursor.execute("SELECT * FROM vendas...")
   ```

2. **Assumir BigQuery existe**
   ```python
   # ❌ ERRADO
   from google.cloud import bigquery
   client = bigquery.Client()
   ```

3. **Criar números na LLM**
   ```python
   # ❌ ERRADO
   resposta = f"Meta total: R$ {calcular_na_llm()}"  # NUNCA!
   ```

4. **Bypass da camada DW**
   ```python
   # ❌ ERRADO
   engine = create_engine("sqlite:///...")  # Fora de dw/connection.py
   ```

### ✅ FAÇA

1. **Use sempre a camada DW**
   ```python
   # ✅ CORRETO
   from src.dw.connection import get_db_session
   from src.agent.queries_analytics import get_metas_realizado_por_mes
   
   session = next(get_db_session())
   kpis = get_metas_realizado_por_mes(session, mes_ano="2025-08")
   ```

2. **Crie funções reutilizáveis**
   ```python
   # ✅ CORRETO
   def get_kpis_mensais(session: Session, mes_ano: str) -> Dict:
       """Função reutilizável independente do banco físico."""
       # Usa SQLAlchemy, não SQL direto
       # Funciona com SQLite E PostgreSQL
   ```

3. **Documente claramente**
   ```python
   # ✅ CORRETO
   # NOTA: BigQuery é apenas roadmap futuro.
   # Estado atual: SQLite (POC) → PostgreSQL (produção planejada)
   # Esta função funciona com ambos via SQLAlchemy.
   ```

---

## 🎯 OBJETIVO DO AGENT

O DIPAM COPILOT™ deve ser um **agent de verdade** que:

### 1. ENTENDE a intenção de negócio
- Detecta o que o usuário quer saber
- Identifica entidades (mês, vendedor, cliente, etc.)
- Mapeia para intents conhecidas

### 2. TRADUZ em especificação de consulta
- Período (mes_ano, janela de tempo)
- Filtros (vendedor, supervisor, rota, cliente)
- Agrupamento (por vendedor, por produto, etc.)
- Métricas (meta, realizado, atingimento, churn_score, etc.)

### 3. EXECUTA usando a camada DW
- Chama funções de `src/agent/queries_*.py`
- Usa `src/agent/queries_analytics.py` para KPIs
- **NUNCA** inventa números
- **SEMPRE** busca dados reais do DW

### 4. DEVOLVE resposta executiva
- Números corretos (do DW, não da LLM)
- Tabelas estruturadas
- Insights de negócio (baseados em dados reais)

---

## 🔧 PROCESSO DE TRABALHO

### Quando receber uma nova tarefa ou erro:

1. **ANALISE o código relevante**
   - Identifique qual módulo DW está envolvido
   - Verifique se há função de consulta existente
   - Entenda o fluxo atual do agent

2. **IDENTIFIQUE o que precisa de ajuste**
   - Qual parte da camada DW precisa melhorar?
   - Qual parte do agent precisa refatorar?
   - Há queries diretas que precisam ser movidas para a camada DW?

3. **PROPONHA um plano de refatoração**
   - Crie/refatore funções reutilizáveis
   - Garanta independência do banco físico
   - Documente claramente

4. **GERE o código com segurança**
   - Use sempre a camada DW existente
   - Teste com SQLite (atual)
   - Garanta compatibilidade com PostgreSQL (futuro)
   - Documente que BigQuery é apenas roadmap

---

## 📁 ESTRUTURA DE MÓDULOS DW

### Módulos Existentes

```
src/dw/
├── connection.py          # Conexão com banco (SQLite/PostgreSQL)
├── models.py              # Modelos SQLAlchemy (tabelas principais)
├── models_analytics.py    # Modelos SQLAlchemy (tabelas analytics)
└── etl.py                 # Pipeline ETL (carregamento de dados)

src/agent/
├── queries.py             # Queries básicas (vendedores, clientes, etc.)
├── queries_analytics.py   # Queries de analytics (KPIs agregados)
└── queries_metas.py       # Queries específicas de metas
```

### Como Usar

```python
# 1. Obter sessão do banco
from src.dw.connection import get_db_session
session = next(get_db_session())

# 2. Usar funções de consulta existentes
from src.agent.queries_analytics import get_metas_realizado_por_mes
kpis = get_metas_realizado_por_mes(session, mes_ano="2025-08", excluir_totais=True)

# 3. Usar modelos SQLAlchemy
from src.dw.models import Venda, MetaVendedor
vendas = session.query(Venda).filter(Venda.mes_ano == "2025-08").all()
```

---

## 📝 EXEMPLOS DE BOAS PRÁTICAS

### Exemplo 1: Função de Consulta Reutilizável

```python
# ✅ CORRETO: src/agent/queries_analytics.py
def get_metas_realizado_por_mes(
    session: Session,
    mes_ano: str,
    excluir_totais: bool = True
) -> Dict[str, Any]:
    """
    Calcula KPIs agregados de meta e realizado para um mês específico.
    
    Esta função é a FONTE ÚNICA DE VERDADE para cálculos de KPIs mensais.
    Funciona com SQLite (atual) e PostgreSQL (futuro) via SQLAlchemy.
    
    NOTA: BigQuery é apenas roadmap futuro. Esta função não usa BigQuery.
    """
    # Usa SQLAlchemy, não SQL direto
    query = session.query(AnalyticsVendedorMes).filter(
        AnalyticsVendedorMes.mes_ano == mes_ano
    )
    
    if excluir_totais:
        query = query.filter(
            ~func.lower(AnalyticsVendedorMes.vendedor_nome).like('%total%')
        )
    
    # Calcula agregados
    resultados = query.all()
    meta_total = sum(r.meta_total for r in resultados)
    realizado_total = sum(r.realizado_total for r in resultados)
    
    return {
        "meta_total": meta_total,
        "realizado_total": realizado_total,
        "atingimento_medio": (realizado_total / meta_total * 100) if meta_total > 0 else 0,
        "linhas_detalhadas": resultados
    }
```

### Exemplo 2: Agent Usando a Camada DW

```python
# ✅ CORRETO: src/agent/service.py
def _handle_meta_query_diretor_analytics(self, ...):
    """
    Handler para consultas de meta usando analytics.
    
    SEMPRE usa a camada DW, nunca inventa números.
    """
    # 1. Usa função única de agregação (FONTE ÚNICA DE VERDADE)
    from src.agent.queries_analytics import get_metas_realizado_por_mes
    
    kpis_mes = get_metas_realizado_por_mes(session, mes_ano, excluir_totais=True)
    
    # 2. Extrai valores dos KPIs (não inventa)
    meta_total = kpis_mes["meta_total"]
    realizado_total = kpis_mes["realizado_total"]
    atingimento_medio = kpis_mes["atingimento_medio"]
    
    # 3. Passa valores EXATOS para o LLM (não deixa calcular)
    contexto_llm = {
        "meta_total": meta_total,  # Valor do DW
        "realizado_total": realizado_total,  # Valor do DW
        "atingimento_medio": atingimento_medio,  # Valor do DW
    }
    
    # 4. LLM apenas explica, não calcula
    resposta = gerar_resposta_llm(contexto_llm, pergunta)
    
    return resposta
```

### Exemplo 3: Documentação Clara

```python
# ✅ CORRETO: Documentação no código
"""
Módulo de conexão com Data Warehouse.

ARQUITETURA:
- DW é uma abstração lógica acessada via este módulo
- Estado atual: SQLite (data/dipam_dw.db) - POC
- Estado futuro: PostgreSQL - Migração planejada
- BigQuery: NÃO implementado - Apenas roadmap futuro

USO:
- Sempre use get_db_session() para obter sessão
- Nunca crie conexões diretas fora deste módulo
- Funções de consulta devem usar SQLAlchemy (compatível com ambos)
"""
```

---

## ✅ CHECKLIST ANTES DE COMMITAR

- [ ] Usei apenas a camada DW existente?
- [ ] Não fiz queries diretas no SQLite?
- [ ] Não assumi que BigQuery existe?
- [ ] Criei funções reutilizáveis independentes do banco físico?
- [ ] Documentei claramente que BigQuery é apenas roadmap?
- [ ] O agent usa SEMPRE dados do DW, nunca inventa números?
- [ ] Testei com SQLite (atual)?
- [ ] Garanti compatibilidade com PostgreSQL (futuro)?

---

## 🚨 SINAIS DE ALERTA

Se você ver no código:

1. **`import sqlite3`** → ❌ Query direta, mover para camada DW
2. **`from google.cloud import bigquery`** → ❌ BigQuery não existe, remover
3. **`engine = create_engine("sqlite:///...")`** fora de `dw/connection.py` → ❌ Bypass da camada DW
4. **Números calculados na LLM** → ❌ Deve vir do DW
5. **SQL hardcoded** → ❌ Usar SQLAlchemy ou funções de consulta

---

## 📚 REFERÊNCIAS

- **Conexão DW**: `src/dw/connection.py`
- **Queries Analytics**: `src/agent/queries_analytics.py`
- **Queries Básicas**: `src/agent/queries.py`
- **Queries Metas**: `src/agent/queries_metas.py`
- **Modelos**: `src/dw/models.py`, `src/dw/models_analytics.py`

---

**Fim das Guidelines**

**⚠️ LEMBRE-SE**: DW é abstração. Hoje SQLite, amanhã PostgreSQL. BigQuery é roadmap, não realidade.

