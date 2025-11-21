# Problema em Produção: Vendedor e Supervisor Vazios

## 🔍 Diagnóstico Realizado

**Endpoint de diagnóstico:** `/admin/diagnostico/vendedor-supervisor`

### Resultados:
```json
{
  "clientes": {
    "total": 5743,
    "ativos": 5743,
    "com_rota_rca": 0,  // ❌ PROBLEMA!
    "com_vendedor_id": 0
  },
  "vendedores": {
    "total": 66,
    "ativos": 66
  },
  "rotas": {
    "distintas": 0,  // ❌ PROBLEMA!
    "exemplos": []
  },
  "query_teste": {
    "total_resultados": 932,
    "com_vendedor": 0,  // ❌ PROBLEMA!
    "com_supervisor": 0,
    "exemplo": {
      "cliente_id": 182,
      "nome": "THIAGO CORREA GUEDES",
      "rota_id": "",  // ❌ VAZIO!
      "vendedor_nome": "",  // ❌ VAZIO!
      "vendedor_codigo": "",  // ❌ VAZIO!
      "supervisor_nome": "",  // ❌ VAZIO!
      "supervisor_codigo": ""  // ❌ VAZIO!
    }
  }
}
```

## ❌ Problema Identificado

**Os clientes em produção NÃO têm `rota_rca` preenchido!**

- 0 clientes com `rota_rca` preenchido
- 0 rotas distintas encontradas
- Por isso o JOIN não encontra vendedores
- Por isso as colunas VENDEDOR e SUPERVISOR aparecem vazias

## ✅ Solução

Os dados precisam ser **recarregados** com o mapeamento corrigido que mapeia `Nome RCA` → `rota_rca`.

### Opções:

1. **Via Endpoint `/admin/reload/clientes`** (requer CSV acessível):
   ```bash
   curl -X POST https://dipam-ai-backend-642830139828.us-central1.run.app/admin/reload/clientes
   ```
   - Requer CSV no GCS ou caminho local configurado
   - Variáveis de ambiente: `CLIENTES_CSV_GCS_URI` ou `CLIENTES_CSV_PATH`

2. **Via Processo ETL Normal**:
   - Executar o processo ETL completo que recarrega todos os dados
   - O ETL agora tem o mapeamento corrigido

3. **Atualização Direta no Banco** (se possível):
   - Atualizar `rota_rca` diretamente no banco se os dados estiverem em outro campo

## 📝 Status Atual

- ✅ Código corrigido e em produção
- ✅ Query funcionando (sem erros)
- ✅ JOIN usando `rota_rca` (sem depender de `vendedor_id`)
- ❌ **Dados não têm `rota_rca` preenchido**

## 🎯 Próximo Passo

**Recarregar os dados dos clientes em produção** usando uma das opções acima.

Após recarregar:
1. Executar migração novamente: `/admin/migrate/vendedor-id`
2. Testar a query novamente
3. Verificar se VENDEDOR e SUPERVISOR aparecem preenchidos

---

**Data:** 2025-11-20  
**Versão:** v-query-simple-join  
**Revisão:** dipam-ai-backend-00115-v9h


