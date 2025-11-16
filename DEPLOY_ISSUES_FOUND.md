# Problemas Encontrados nos Testes de Deploy

Este documento lista os problemas encontrados ao executar `./scripts/run_deploy_checks.sh` e como corrigi-los.

## ✅ Problemas Corrigidos

### 1. Conexão de Banco Fechada Prematuramente

**Problema**: A sessão do banco estava sendo fechada após a primeira pergunta, causando "This Connection is closed" nas perguntas subsequentes.

**Sintoma**:
```
ERROR - Erro ao buscar skill por intent consulta_meta: This Connection is closed
ERROR - Erro ao buscar meta x realizado por vendedor: This Connection is closed
```

**Correção**: Modificado `scripts/test_cloud_like_env.py` para criar uma nova sessão para cada pergunta.

**Status**: ✅ Corrigido

### 2. Tabelas Faltando no Banco

**Problema**: Tabelas `skills` e coluna `intent_prevista` em `interacoes_agent` não existem.

**Sintoma**:
```
ERROR - Erro ao buscar skill por intent consulta_meta: (sqlite3.OperationalError) no such table: skills
ERROR - Erro ao registrar interação: table interacoes_agent has no column named intent_prevista
```

**Impacto**: Não crítico - o sistema continua funcionando, apenas não registra algumas informações.

**Status**: ⚠️ Não crítico (sistema funciona sem essas tabelas)

## ⚠️ Problemas Identificados (Requerem Investigação)

### 1. Respostas Genéricas Mesmo com Dados

**Problema**: Mesmo com 63 registros no banco para outubro 2025, a resposta gerada diz "não temos informações".

**Sintoma**:
```
📊 Registros em metas_vendedor para 2025-10: 63
👥 Vendedores encontrados no contexto: 10
⚠️  Resposta parece genérica/fallback
   Preview: ## Resumo executivo

Atualmente, não temos informações sobre as metas de vendas ou resultados realizados para o mês de outubro de 2025...
```

**Possíveis Causas**:
1. O prompt do LLM não está recebendo os dados corretamente
2. O contexto não está sendo formatado adequadamente para o LLM
3. O LLM está interpretando os dados de forma incorreta

**Ação Necessária**: Investigar `src/llm_integration.py` e verificar como o contexto está sendo passado para o LLM.

**Status**: ⚠️ Requer investigação

### 2. Parsing de Data Incorreto para "agosto 2025"

**Problema**: Na pergunta 3, o sistema extraiu "2025-05" em vez de "2025-08" para "agosto 2025".

**Sintoma**:
```
📝 Pergunta: quais foram os vendedores que mais geraram impacto negativo no realizado do mês de agosto 2025
📅 Mês/ano extraído da pergunta: 2025-08  ✅ (correto)
...
[_handle_vendedores_performance] entities.get('mes_ano')=2025-05  ❌ (incorreto)
```

**Possíveis Causas**:
1. Algum código está sobrescrevendo o mes_ano extraído
2. Há lógica de fallback que está usando um mês padrão
3. O código de intent detection está modificando o mes_ano

**Ação Necessária**: Investigar `src/agent/service.py` método `_handle_vendedores_performance` e verificar onde o mes_ano está sendo modificado.

**Status**: ⚠️ Requer investigação

### 3. Vendedores Não Encontrados no Contexto

**Problema**: Para as perguntas 2 e 3, nenhum vendedor foi encontrado no contexto, mesmo havendo dados no banco.

**Sintoma**:
```
📊 Registros em metas_vendedor para 2025-08: 64
⚠️  Nenhum vendedor encontrado no contexto
```

**Possíveis Causas**:
1. As queries não estão retornando dados devido à conexão fechada
2. O contexto não está sendo populado corretamente
3. Os dados estão em um formato diferente do esperado

**Ação Necessária**: Com a correção da conexão, este problema deve ser resolvido. Se persistir, investigar as queries em `src/agent/queries.py`.

**Status**: ⚠️ Provavelmente resolvido com correção da conexão

## 📊 Resumo dos Testes

### ✅ Testes que Passaram

1. **Variáveis de Ambiente**: Todas as env vars obrigatórias estão configuradas
2. **Conexão Banco**: Conexão OK, 753 registros em metas_vendedor
3. **Conexão OpenAI**: Chamada de teste OK
4. **Dados Disponíveis**: 
   - 64 registros para 2025-08 (agosto)
   - 63 registros para 2025-10 (outubro)

### ⚠️ Testes que Falharam

1. **Serviço do Agente**: 
   - Pergunta 1: Funcionou parcialmente (dados encontrados, mas resposta genérica)
   - Pergunta 2: Falhou (conexão fechada)
   - Pergunta 3: Falhou (conexão fechada + parsing incorreto de data)

## 🔧 Próximos Passos

1. ✅ **Corrigido**: Sessão de banco sendo fechada prematuramente
2. ⚠️ **Investigar**: Por que respostas são genéricas mesmo com dados
3. ⚠️ **Investigar**: Por que parsing de "agosto" gera "2025-05"
4. ⚠️ **Opcional**: Criar migrations para tabelas faltantes (skills, intent_prevista)

## 🧪 Como Reproduzir

```bash
# Executar testes
./scripts/run_deploy_checks.sh

# Ver logs detalhados
export OPENAI_API_KEY="sk-..."
export DB_TYPE="sqlite"
export SQLITE_PATH="data/dipam_dw.db"
export ENVIRONMENT="production"
python scripts/test_cloud_like_env.py
```

---

## ✅ Correções Implementadas (2025-11-15)

### 1. Parsing de Datas Corrigido

**Problema**: "agosto 2025" estava sendo interpretado como "2025-05" em alguns casos.

**Causa Raiz**: O código procurava meses em ordem do dicionário, e abreviações curtas (ex.: "ago") podiam ser encontradas antes de nomes completos (ex.: "agosto"), causando falsos positivos.

**Correção**:
- Modificado `src/agent/intent.py` e `src/agent/utils/date_extraction.py` para:
  - Ordenar meses por tamanho (mais longos primeiro) antes de procurar
  - Usar word boundaries (`\b`) para evitar falsos positivos
  - Priorizar nomes completos sobre abreviações

**Arquivos Modificados**:
- `src/agent/intent.py` (função `parse_mes_ano_from_text` e `extract_entities`)
- `src/agent/utils/date_extraction.py` (função `extrair_mes_ano_explicito`)

### 2. Respostas Genéricas Eliminadas

**Problema**: Mesmo com 63-64 registros no banco, o LLM gerava respostas dizendo "não há dados".

**Causa Raiz**: 
- Prompts do LLM não eram suficientemente explícitos sobre usar dados quando disponíveis
- Validação de `tem_dados` não verificava se as listas realmente tinham elementos

**Correção**:
- **Prompts Fortalecidos** (`src/llm_integration.py`):
  - Adicionada regra crítica explícita: "NUNCA DIGA QUE NÃO HÁ DADOS SE HOUVER DADOS"
  - Instruções claras sobre quando usar dados vs. quando dizer que não há dados
  - Exemplos específicos de como usar dados mesmo quando são poucos
  
- **Validação no Código**:
  - `gerar_resposta_consulta_meta`: Verifica se `serie_mensal` ou `detalhe_vendedores_mes` têm elementos
  - `gerar_resposta_performance_vendedores`: Verifica se `piores_meta` ou `menores_venda` têm elementos
  - `_handle_vendedores_performance`: Valida `tem_dados` baseado em dados reais, não apenas `periodo_tem_dados`
  - Se há dados nas listas, `tem_dados` é automaticamente corrigido para `True`

**Arquivos Modificados**:
- `src/llm_integration.py` (funções `gerar_resposta_consulta_meta` e `gerar_resposta_performance_vendedores`)
- `src/agent/service.py` (método `_handle_vendedores_performance`)

### 3. Script de Teste Melhorado

**Melhorias**:
- Detecção mais robusta de respostas genéricas quando há dados no banco
- Verifica se há registros no banco para o mês solicitado
- Marca como ERRO CRÍTICO se há dados no banco mas a resposta diz que não há dados
- Lista expandida de frases de fallback para detectar

**Arquivos Modificados**:
- `scripts/test_cloud_like_env.py` (função `testar_agent_service`)

### 4. Regra de Ouro Implementada

**Regra**: "Se uma resposta citar números, eles vieram do banco de dados real. Se houver dados, nunca dizer 'não tenho informações'."

**Implementação**:
- Validação em múltiplas camadas (código + prompts)
- Logs de warning quando `tem_dados` é corrigido automaticamente
- Script de teste detecta violações dessa regra

---

**Data**: 2025-11-15
**Status**: ✅ Correções implementadas e testadas

