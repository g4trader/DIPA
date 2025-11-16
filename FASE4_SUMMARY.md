# FASE 4: Aprendizado Contínuo e Recálculo Automático - Resumo

## ✅ Implementação Completa

A FASE 4 foi implementada com sucesso, adicionando capacidades de aprendizado contínuo e recálculo automático ao DIPAM COPILOT™.

## 📁 Arquivos Criados

1. **`src/agent/interaction_registry.py`**
   - Função `registrar_interacao_agent()` para registrar todas as interações
   - Extrai metadados completos (resumo_executivo, contexto_debug, fonte_dados, etc.)

2. **`scripts/run_analytics_job.py`**
   - Script orquestrador para recálculo automático de analytics e scores
   - Suporta `--mes_ano` e `--ultimos_n_meses`
   - Gera logs e estatísticas detalhadas

3. **`src/ml/training_pipeline.py`**
   - Hooks para preparação de datasets para treino futuro
   - Funções: `preparar_dataset_churn()`, `preparar_dataset_meta_risk()`, `preparar_dataset_qa_respostas()`
   - Preparado para FASE 5 (treinamento real de modelos)

4. **`scripts/validate_fase4.py`**
   - Script de validação dos critérios de aceitação
   - Verifica todos os componentes da FASE 4

## 📝 Arquivos Modificados

1. **`src/dw/models.py`**
   - Adicionados campos na tabela `InteracaoAgent`:
     - `resumo_executivo`: Resumo executivo extraído
     - `debug_payload`: Contexto de debug completo (JSON)
     - `fonte_dados_principal`: Fonte principal dos dados
     - `num_registros_usados`: Quantidade de registros consultados
     - `tempo_processamento_ms`: Latência da pergunta
     - `sucesso_resposta`: Flag de sucesso (alias para `sucesso`)
     - `feedback_qualidade`: Escala 1-5
     - `feedback_comentario`: Comentário do Diretor (alias para `comentario`)

2. **`src/api/main.py`**
   - Endpoint `/ask` atualizado para:
     - Medir tempo de processamento
     - Registrar interação com todos os metadados via `registrar_interacao_agent()`
   - Novo endpoint `POST /feedback` (FASE 4):
     - Aceita `interacao_id`, `feedback_qualidade` (1-5), `feedback_comentario`
     - Atualiza campos de feedback na tabela `interacoes_agent`
   - Mantido endpoint antigo `POST /feedback/{interacao_id}` para compatibilidade

3. **`README_DEPLOY.md`**
   - Nova seção "Jobs Agendados (Analytics + Aprendizado) - FASE 4"
   - Documentação de como agendar jobs via Cloud Scheduler
   - Exemplos de uso do `run_analytics_job.py`
   - Frequências recomendadas (diário, semanal, mensal)

## 🎯 Critérios de Aceitação

### ✅ 1. Toda chamada ao /ask gera registro em interacoes_agent

**Status**: ✅ IMPLEMENTADO

- Função `registrar_interacao_agent()` criada
- Integrada no endpoint `/ask`
- Registra: pergunta, intent, entidades, resumo_executivo, sucesso_resposta, fonte_dados_principal, num_registros_usados, tempo_processamento_ms, debug_payload
- Não bloqueia resposta se falhar (apenas loga warning)

### ✅ 2. Endpoint POST /feedback funcionando

**Status**: ✅ IMPLEMENTADO

- Endpoint `POST /feedback` criado
- Aceita `interacao_id`, `feedback_qualidade` (1-5), `feedback_comentario` (máx. 2000 caracteres)
- Validação de feedback_qualidade (1-5)
- Atualiza campos `feedback_qualidade` e `feedback_comentario` na tabela
- Retorna JSON com status e mensagem

### ✅ 3. scripts/run_analytics_job.py roda sem erro

**Status**: ✅ IMPLEMENTADO

- Script criado com suporte a `--mes_ano` e `--ultimos_n_meses`
- Chama `run_all_analytics()` para cada mês
- Processa: analytics_vendedor_mes, analytics_cliente_mes, analytics_produto_mes, scores, alertas
- Gera logs detalhados e estatísticas
- Exit code baseado em sucesso/falha

### ✅ 4. src/ml/training_pipeline.py consegue montar datasets

**Status**: ✅ IMPLEMENTADO

- Arquivo criado com funções:
  - `preparar_dataset_churn()`: Dataset de churn por cliente
  - `preparar_dataset_meta_risk()`: Dataset de risco de meta por vendedor
  - `preparar_dataset_qa_respostas()`: Dataset de qualidade de resposta
  - `preparar_dataset_produto_queda()`: Dataset de queda de produtos
  - `exportar_datasets_para_treino()`: Função orquestradora
- Retorna DataFrames/listas de dicts prontos para treino futuro
- Não treina modelos ainda (será na FASE 5)

### ✅ 5. README_DEPLOY.md documenta jobs agendados

**Status**: ✅ IMPLEMENTADO

- Seção completa adicionada
- Documenta 3 opções de agendamento:
  - Cloud Scheduler (recomendado)
  - Cloud Run Job
  - Pipeline externo (cron, Airflow, etc.)
- Exemplos de comandos
- Frequências recomendadas
- Monitoramento e validação

## 🧪 Como Validar

Execute o script de validação:

```bash
DB_TYPE=sqlite SQLITE_PATH=data/dipam_dw.db python -m scripts.validate_fase4
```

O script valida:
1. ✅ Interações sendo registradas
2. ✅ Endpoint /feedback existe
3. ✅ Script run_analytics_job.py existe
4. ✅ training_pipeline.py consegue montar datasets
5. ✅ Documentação completa

## 📊 Exemplo de Uso

### Registrar Interação (automático via /ask)

```bash
curl -X POST http://localhost:8080/ask \
  -H "Content-Type: application/json" \
  -d '{
    "pergunta": "Sou o Diretor e preciso saber porque não batemos a meta no mês de agosto 2025",
    "papel": "diretor"
  }'
```

A interação será registrada automaticamente com todos os metadados.

### Enviar Feedback

```bash
curl -X POST http://localhost:8080/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "interacao_id": 123,
    "feedback_qualidade": 4,
    "feedback_comentario": "Resposta boa, mas poderia detalhar mais os clientes em risco."
  }'
```

### Recálculo de Analytics

```bash
# Recalcular mês específico
DB_TYPE=sqlite SQLITE_PATH=data/dipam_dw.db \
  python -m scripts.run_analytics_job --mes_ano=2025-08

# Recalcular últimos 6 meses
DB_TYPE=sqlite SQLITE_PATH=data/dipam_dw.db \
  python -m scripts.run_analytics_job --ultimos_n_meses=6
```

### Preparar Datasets para Treino

```python
from src.dw.connection import get_db_session
from src.ml.training_pipeline import preparar_dataset_churn

session = next(get_db_session())
dataset = preparar_dataset_churn(session, "2025-08", "2025-08")
print(f"Dataset preparado: {len(dataset)} registros")
```

## 🔄 Próximos Passos (FASE 5)

1. **Treinamento Real de Modelos**
   - Usar datasets preparados para treinar modelos scikit-learn/lightweight
   - Comparar com scores baseline (heurísticas)
   - Avaliar performance

2. **Endpoint Admin**
   - Criar `/admin/run_analytics_job` para execução via HTTP
   - Autenticação/autorização
   - Dashboard de monitoramento

3. **Alertas de Jobs**
   - Notificações quando jobs falharem
   - Métricas de performance dos jobs

4. **Melhoria Contínua**
   - Usar feedback_qualidade para melhorar prompts
   - A/B testing de diferentes abordagens
   - Análise de padrões de perguntas

## 📈 Estatísticas Esperadas

Após algumas interações, você pode verificar:

```sql
-- Total de interações
SELECT COUNT(*) FROM interacoes_agent;

-- Intents mais frequentes
SELECT intent, COUNT(*) as total 
FROM interacoes_agent 
GROUP BY intent 
ORDER BY total DESC;

-- Interações com feedback
SELECT COUNT(*) 
FROM interacoes_agent 
WHERE feedback_qualidade IS NOT NULL;

-- Tempo médio de processamento
SELECT AVG(tempo_processamento_ms) as tempo_medio_ms
FROM interacoes_agent
WHERE tempo_processamento_ms IS NOT NULL;
```

---

**Data de Conclusão**: 2025-01-XX  
**Status**: ✅ FASE 4 COMPLETA

