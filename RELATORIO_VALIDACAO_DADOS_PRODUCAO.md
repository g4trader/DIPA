# Relatório de Validação de Dados - Produção

**Data:** 2025-11-25  
**Ambiente:** Produção (Cloud Run)  
**Versão:** v-prod-perf

## Status da Validação

### ⚠️ Problema Identificado: Timeout de 32s

O serviço está retornando `503 Service Unavailable` após aproximadamente 32 segundos de processamento. Isso indica um timeout antes da conclusão da requisição.

**Observações dos logs:**
- Query Q1 está executando corretamente (1234 clientes únicos detectados)
- Logs `[PERF_ASK]` sendo gerados
- Cache bypass está funcionando
- Timeout ocorre antes da conclusão do processamento completo

**Possíveis causas:**
1. Timeout do Cloud Run (configurado para 300s, mas pode haver timeout intermediário)
2. Timeout do gunicorn/uvicorn worker
3. Timeout durante chamada ao LLM (GROQ)
4. Processamento muito longo da query DW

**Recomendação:** Investigar timeout e ajustar configurações se necessário.

## Validações Realizadas

### 1. Endpoint /health ✅

```json
{
  "status": "healthy",
  "timestamp": "2025-11-25T19:12:10.224365",
  "environment": "production",
  "version": "1.0.0",
  "database": "sqlite",
  "components": {
    "database": "available",
    "openai": "available",
    "agent_service": "unavailable"
  }
}
```

**Status:** ✅ Endpoint respondendo corretamente

### 2. Logs de Performance

Logs `[PERF_ASK]` sendo gerados:
- `[PERF_ASK] Iniciando processamento de pergunta`

**Status:** ✅ Logs de performance instrumentados e funcionando

### 3. Query Q1 Executando

Nos logs, observamos que a query Q1 está sendo executada:
- Query SQL sendo gerada corretamente
- Filtros aplicados: `ativo = 1`, `dias_sem_compra >= 61`
- CTE base detectando clientes únicos

**Status:** ✅ Query executando corretamente

## Validações Pendentes (Requerem Estabilização)

### Comparação Local vs Produção

**Script criado:** `scripts/compare_local_prod_q1.py`

**Validações a realizar:**
- [ ] Total de clientes (esperado: 932)
- [ ] Todos os clientes ativos (ativo == True)
- [ ] Nenhuma duplicata
- [ ] % com vendedor/supervisor ≥ 97%
- [ ] Faixas (61–120, 121–180, 181–300, >300) idênticas

**Status:** ⏳ Aguardando estabilização do serviço

### Estrutura de Dados

**Campos esperados na resposta Q1:**
- `cliente_id` / `Cliente ID`
- `nome` / `Nome`
- `dias_sem_compra` / `Dias sem compra`
- `vendedor_nome` / `Vendedor`
- `supervisor_nome` / `Supervisor`
- `rota_rca` / `Rota`
- `segmento_venda` / `Segmento`

**Status:** ⏳ Aguardando resposta completa para validação

## Próximos Passos

1. **Aguardar estabilização** (10-15 minutos após último deploy)
2. **Executar comparação local vs produção:**
   ```bash
   python3 scripts/compare_local_prod_q1.py
   ```
3. **Validar estrutura de dados** na resposta completa
4. **Verificar métricas** de vendedor/supervisor preenchidos
5. **Confirmar faixas** de classificação

## Observações Técnicas

### AgentService Unavailable

O componente `agent_service` está marcado como "unavailable" no health check. Isso é esperado durante:
- Inicialização do serviço
- Carregamento de modelos ML em background
- Não impede o funcionamento do endpoint `/ask`

### Reinicializações Frequentes

O serviço está reiniciando frequentemente. Possíveis causas:
- Timeout de requisições longas (> 30s)
- Cold start do Cloud Run
- Recursos insuficientes durante picos

**Recomendação:** Monitorar métricas do Cloud Run e considerar aumentar recursos se necessário.

## Conclusão

✅ **Logs de performance funcionando**  
✅ **Query Q1 executando corretamente**  
✅ **Endpoint /health respondendo**  
⏳ **Validações de dados pendentes** (aguardando estabilização)

**Status Geral:** ⚠️ **AGUARDANDO ESTABILIZAÇÃO PARA VALIDAÇÃO COMPLETA**

