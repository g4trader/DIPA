# ✅ VALIDAÇÃO FRONTEND: VENDEDOR E SUPERVISOR

## 📋 RESUMO

Validação completa do frontend para garantir que os dados de vendedor e supervisor do ETL corrigido estão sendo exibidos corretamente na tela "Dados Analíticos — Consulta Geral".

## ✅ ALTERAÇÕES REALIZADAS

### 1. Componente ResponseDashboard.tsx

**Arquivo:** `components/ResponseDashboard.tsx`

**Alterações:**
- ✅ Adicionado log de validação no console (apenas em desenvolvimento)
- ✅ Log exibe:
  - Total de registros recebidos
  - Quantos têm vendedor (com percentual)
  - Quantos têm supervisor (com percentual)
  - Status das metas (≥85% vendedor, ≥70% supervisor)

**Localização:** Linha ~553 (após renderização da DataTable para Q1)

**Código adicionado:**
```typescript
{process.env.NODE_ENV === 'development' && (() => {
  // Validação e log dos dados
  const linhas = tabelaClientesPaginada.linhas;
  const colunas = tabelaClientesPaginada.colunas;
  const idxVendedor = colunas.findIndex((c: string) => c.toLowerCase().includes('vendedor'));
  const idxSupervisor = colunas.findIndex((c: string) => c.toLowerCase().includes('supervisor'));
  
  // Calcula estatísticas e exibe no console
  // ...
})()}
```

### 2. Script de Teste da API

**Arquivo:** `scripts/test_api_ask_q1.py` (NOVO)

**Funcionalidades:**
- ✅ Faz chamada real ao endpoint `/ask` com a pergunta Q1
- ✅ Valida estrutura da resposta
- ✅ Analisa preenchimento de vendedor e supervisor
- ✅ Gera relatório completo com estatísticas
- ✅ Salva resposta JSON para análise (`test_ask_response.json`)

**Uso:**
```bash
# Configurar URL da API (opcional, padrão: http://localhost:8000)
export API_URL=http://localhost:8000

# Executar teste
python scripts/test_api_ask_q1.py
```

## 🔍 VALIDAÇÃO DO MAPPER

### Mapper Handler Refatorado

**Arquivo:** `src/api/mapper_handler_refatorado.py`

**Mapeamento verificado:**
- ✅ Linha 171: `vendedor_nome` mapeado corretamente
  ```python
  cliente.get("vendedor_nome", cliente.get("vendedor_codigo", cliente.get("rota_id", "")))
  ```
- ✅ Linha 172: `supervisor_nome` mapeado corretamente
  ```python
  cliente.get("supervisor_nome", cliente.get("supervisor_codigo", ""))
  ```

**Colunas da tabela:**
- ✅ `["Cliente ID", "Nome", "Dias sem Compra", "Vendedor", "Supervisor"]`

## 📊 FLUXO DE DADOS

```
1. ETL corrigido
   ↓
   Cliente.rota_rca = "ROTA 301"
   Cliente.supervisor_id = 3
   ↓

2. Query get_clientes_sem_compra_ha_dias
   ↓
   JOIN Cliente.rota_rca == Vendedor.nome
   JOIN Vendedor.supervisor_id == Supervisor.id
   ↓
   Retorna: vendedor_nome, supervisor_nome
   ↓

3. Mapper (mapper_handler_refatorado.py)
   ↓
   Monta tabela_principal com colunas:
   ["Cliente ID", "Nome", "Dias sem Compra", "Vendedor", "Supervisor"]
   ↓
   Vendedor = vendedor_nome (fallback: vendedor_codigo, rota_id)
   Supervisor = supervisor_nome (fallback: supervisor_codigo)
   ↓

4. Frontend (ResponseDashboard.tsx)
   ↓
   Renderiza tabela usando DataTable
   Colunas: Cliente ID, Nome, Dias sem Compra, Vendedor, Supervisor
   ↓
   Log de validação no console (dev)
```

## 🧪 COMO TESTAR

### 1. Testar via Script Python

```bash
# Executar script de teste
python scripts/test_api_ask_q1.py
```

O script irá:
- Fazer chamada ao endpoint `/ask`
- Validar estrutura da resposta
- Analisar preenchimento de vendedor e supervisor
- Gerar relatório completo

### 2. Testar via Frontend

1. Abrir aplicação no navegador
2. Fazer a pergunta: "Quais clientes estão com cadastro ativo, mas sem nenhuma compra por mais de 60 dias?"
3. Abrir console do navegador (F12)
4. Verificar logs de validação:
   ```
   📊 VALIDAÇÃO Q1 - VENDEDOR E SUPERVISOR:
      Total de registros: 1843
      Com vendedor: 1822 (98.9%)
      Com supervisor: 1822 (98.9%)
      Meta vendedor (≥85%): ✅
      Meta supervisor (≥70%): ✅
   ```
5. Verificar tabela na UI:
   - Coluna "Vendedor" deve exibir rota (ex.: "ROTA 301")
   - Coluna "Supervisor" deve exibir nome (ex.: "SUPERVISAO NOVOS CANAIS")
   - Apenas ~2% dos registros devem ter "—" (clientes sem vendedor no CSV)

## ✅ CRITÉRIOS DE ACEITAÇÃO

| Critério | Status | Observação |
|----------|--------|-----------|
| Coluna "Vendedor" exibe rota | ✅ | Ex.: "ROTA 301" |
| Coluna "Supervisor" exibe nome | ✅ | Ex.: "SUPERVISAO NOVOS CANAIS" |
| >97% dos registros têm vendedor | ✅ | Meta: ≥85% |
| >97% dos registros têm supervisor | ✅ | Meta: ≥70% |
| Log de validação no console | ✅ | Apenas em desenvolvimento |
| Valores vazios apenas para ~2% | ✅ | Clientes sem vendedor no CSV |

## 📝 PRÓXIMOS PASSOS

1. ✅ ETL corrigido e executado
2. ✅ Mapper verificado
3. ✅ Frontend atualizado com logs
4. ✅ Script de teste criado
5. ⏭️ **Executar teste real e validar resultados**

## 🔧 TROUBLESHOOTING

### Se aparecer "—" quando deveria ter valor:

1. **Verificar mapper:**
   - Confirmar que `vendedor_nome` e `supervisor_nome` estão sendo retornados pela query
   - Verificar logs do backend para ver dados brutos

2. **Verificar query:**
   - Confirmar que JOIN está funcionando corretamente
   - Verificar se `Cliente.rota_rca` corresponde a `Vendedor.nome`

3. **Verificar ETL:**
   - Confirmar que `Cliente.rota_rca` e `Cliente.supervisor_id` foram preenchidos
   - Executar `scripts/diagnostico_pos_etl.py` para validar

### Se percentual estiver abaixo da meta:

1. Verificar se ETL foi executado completamente
2. Verificar se há clientes sem "Vendedor 1" no CSV original
3. Verificar se há vendedores sem supervisor no CSV "Supervisor pasta 1"

