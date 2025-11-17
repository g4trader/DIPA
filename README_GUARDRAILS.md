# DIPAM COPILOT™ – README_GUARDRAILS.md  
### Guardrails oficiais de arquitetura, dados, inteligência, regras e boas práticas  
### (Documento obrigatório para Cursor + Codex + colaboradores)

Este documento define as regras **imutáveis** do projeto DIPAM COPILOT™.  
Ele deve ser seguido rigorosamente por:

- Cursor (IA responsável por escrever código)  
- Codex (IA responsável por auditar o repositório e PRs)  
- Desenvolvedores humanos  
- Sistemas automáticos de CI/CD  

Qualquer alteração nessas regras deve ser aprovada pelo Diretor.

---

# 📌 1. PRINCÍPIOS FUNDAMENTAIS DO DIPAM COPILOT™

1. O DIPAM COPILOT™ é um **Agente de Inteligência Comercial** da DIPAM Gaúcha.  
2. O sistema deve responder perguntas **baseadas exclusivamente em dados reais do DW**.  
3. O agente **não pode inventar números, metas, percentuais** ou “dados plausíveis”.  
4. Toda resposta deve seguir o fluxo padrão:  

Pergunta → IntentSpec → Orquestrador → DW → Dados Reais → LLM → Resposta Executiva

5. O sistema deve **aprender regras de feedback do Diretor**, que se tornam permanentes até ordem contrária.  
6. Todo o aprendizado deve ser registrado em:  
   - agent/feedback_rules.py  
   - data/rules.json (ou DW futuro)  
7. O DIPAM COPILOT™ deve manter respostas:  
   - **confiáveis**  
   - **explicáveis**  
   - **reprodutíveis**  
   - **auditáveis**

---

# 📌 2. ARQUITETURA OFICIAL

## 2.1. Módulos e responsabilidades

### ✔ /agent
- Interpretação de IntentSpec  
- Orquestração do fluxo  
- Aplicação de regras de feedback  
- Conversão dos dados em linguagem executiva (pós-processamento)  

### ✔ /dw
- Único local permitido para consultas SQL  
- Agregações  
- Cálculos de metas, vendas, tickets, mix  
- Nenhum outro módulo pode acessar o banco diretamente  

### ✔ /orchestrator
- Coordena DW + regras + IA  
- Valida Input  
- Garante que NENHUMA informação é inventada  

### ✔ /api
- Endpoints REST  
- Sanitização de inputs  
- Chamadas ao orquestrador  

### ✔ /frontend
- UI + UX  
- Nenhuma lógica de negócio  

---

# 📌 3. PROIBIÇÕES ABSOLUTAS

Essas regras são **imutáveis**:

### ❌ 3.1. Inventar dados  
Nenhum número, meta, item, produto pode ser criado manualmente.

### ❌ 3.2. Acessar o banco fora de /dw/*  
Proibido usar sqlite3 / psycopg2 diretamente em agent, orchestrator, api ou frontend.

### ❌ 3.3. SQL escrito fora da camada DW  
Todo SQL deve estar em /dw/queries/ ou funções do módulo dw.

### ❌ 3.4. Hardcode de metas  
Nada de “meta de R$ 2M” escrita no código.

### ❌ 3.5. Bypass de IntentSpec  
Nenhum módulo pode decidir a consulta sem antes interpretar a Intent.

### ❌ 3.6. Uso de BigQuery  
Não implementado. Referências só podem existir no roadmap.

---

# 📌 4. FLUXO OFICIAL DE CONSULTA (MANDATÓRIO)

Pergunta → IntentSpec → Orquestrador → DW → Dados Reais → LLM → Resposta Executiva

---

# 📌 5. INTENTSPEC (CONTRATO OBRIGATÓRIO)

Cada pergunta deve ser transformada em JSON estruturado contendo tipo, período, filtros, métricas e forma de agregação.

O Codex deve verificar se:
- Todos parâmetros obrigatórios existem  
- Nenhuma consulta é executada sem IntentSpec válido  
- Filters estão consistentes com a DW  

---

# 📌 6. CAMADA DE REGRAS (APRENDIZADO)

Toda vez que o Diretor fornecer um feedback do tipo:

“Para análises financeiras, ignore a pasta verde.”

Isso deve ser registrado em agent/feedback_rules.py e persistido em rules.json.

Exemplo:

{
  "analises_financeiras": {
    "excluir_carteiras": ["pasta_verde"]
  }
}

O orquestrador deve aplicar essas regras **antes de consultar o DW**.

---

# 📌 7. DW – REGRAS DE DADOS

- Fonte única: data/dipam_dw.db (SQLite no POC)  
- PostgreSQL no futuro  
- BigQuery não existe tecnicamente  
- Sem informações sintéticas  
- Consultas auditáveis e consistentes com IntentSpec  

---

# 📌 8. PÓS-PROCESSAMENTO OBRIGATÓRIO

O agente deve transformar dados brutos em insights executivos, respeitando:

- percentuais derivados do próprio DW  
- comparativos reais  
- anomalias reais  
- recomendações baseadas em dados  

Proibido gerar previsões ou tendências inventadas.

---

# 📌 9. LLM – REGRAS DE RESPOSTA

A IA deve:
- Usar apenas dados reais  
- Explicar raciocínio em linguagem executiva  
- Não assumir fatos não presentes  
- Sempre mencionar período, equipe, filtros e regras aplicadas  

---

# 📌 10. BOAS PRÁTICAS DE ENGENHARIA

- Tipagem obrigatória  
- Docstrings  
- Funções pequenas  
- Sem duplicação  
- Rotas enxutas  
- Logs claros  

---

# 📌 11. COMO O CODEX DEVE AUDITAR

O Codex deve verificar:

1. Respeitou arquitetura?  
2. IntentSpec foi seguido?  
3. Regras de aprendizado aplicadas?  
4. Nenhum SQL fora do DW?  
5. Nenhum dado inventado?  
6. Nenhuma referência indevida a BigQuery?  
7. Pós-processamento correto?  
8. PR adicionou testes?  
9. Código limpo?  

---

# 📌 12. COMO O CURSOR DEVE CODIFICAR

O Cursor deve:
1. Ler este arquivo antes de escrever código  
2. Seguir arquitetura  
3. Criar módulos corretos  
4. Nunca escrever SQL fora da camada DW  
5. Respeitar IntentSpec  
6. Aplicar regras de feedback  
7. Nunca gerar dados fictícios  
8. Criar commits limpos e claros  

---

# 📌 13. ROADMAP

Curto prazo: refinamento da IntentSpec, DW, regras persistentes  
Médio prazo: migração para PostgreSQL, dashboard autônomo  
Longo prazo: BigQuery, Forecast ML, simuladores  

---

# 📌 14. CONCLUSÃO

Este arquivo é a **Constituição Oficial do DIPAM COPILOT™**.  
Nenhum código pode violar estes guardrails.  
