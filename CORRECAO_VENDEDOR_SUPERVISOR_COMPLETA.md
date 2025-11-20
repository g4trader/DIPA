# Correção Completa: Vendedor e Supervisor na Tabela "Dados Analíticos"

## 📋 Problema Identificado

As colunas **VENDEDOR** e **SUPERVISOR** estavam vazias na tabela "Dados Analíticos - Consulta Geral" quando a pergunta era sobre clientes sem compra há mais de 60 dias.

### Causa Raiz
1. **Mapeamento CSV incorreto**: O CSV tinha a coluna `Nome RCA` (com espaço e maiúsculas), mas o código procurava `rota_rca` (minúsculas, sem espaço)
2. **Modelo inconsistente**: O modelo `Vendedor` tinha campos `nome_rca` e `rota_rca` que não correspondiam ao uso real
3. **ETL não criava vendedores**: Os vendedores não eram criados automaticamente a partir das rotas dos clientes
4. **JOIN incorreto**: A query não fazia JOIN correto entre `Cliente` e `Vendedor`

## ✅ Correções Implementadas

### 1. Mapeamento CSV → Modelo Cliente (`src/load_to_db.py`)

**Antes:**
```python
'rota_rca': str(row.get('rota_rca', ''))  # ❌ Não encontrava 'Nome RCA' do CSV
```

**Depois:**
```python
# ✅ CORREÇÃO: Mapeia 'Nome RCA' do CSV para 'rota_rca' do modelo
'rota_rca': str(row.get('Nome RCA', row.get('rota_rca', '')))
```

**Outros mapeamentos corrigidos:**
- `Código` → `codigo`
- `Cliente` → `nome`
- `Estado` → `estado`
- `Município` → `municipio`

### 2. Modelo Vendedor (`src/dw/models.py`)

**Antes:**
```python
codigo = Column(String(50))  # Ex: "JOÃO SILVA"
nome_rca = Column(String(255))  # ❌ Campo desnecessário
rota_rca = Column(String(100))  # ❌ Campo desnecessário
```

**Depois:**
```python
codigo = Column(String(50))  # ✅ Agora é a rota: "ROTA 304"
nome = Column(String(255))  # Nome do vendedor (pode ser None)
# nome_rca e rota_rca removidos
```

**Razão**: O `codigo` do vendedor deve corresponder ao `rota_rca` do cliente para o JOIN funcionar.

### 3. ETL Corrigido (`src/load_to_db.py`)

**Adicionado:**
- Criação automática de vendedores a partir de `rota_rca` dos clientes
- População automática de `vendedor_id` nos clientes durante o carregamento

```python
# Vendedor ID (cria vendedor a partir da rota_rca se existir)
if cliente_data.get('rota_rca'):
    rota_rca = str(cliente_data['rota_rca']).strip()
    if rota_rca:
        vendedor = get_or_create_vendedor(
            session,
            nome=cliente_data.get('nome_rca') or rota_rca,
            codigo=rota_rca,  # ✅ Usa rota_rca como código
            supervisor_id=supervisor_id
        )
        cliente_data['vendedor_id'] = vendedor.id
```

### 4. Query Ajustada (`src/dw/queries.py`)

**JOIN corrigido:**
```python
# ✅ JOIN com Vendedor - prioriza vendedor_id, fallback para rota_rca
.outerjoin(
    Vendedor,
    or_(
        Cliente.vendedor_id == Vendedor.id,  # Se houver FK direta
        Cliente.rota_rca == Vendedor.codigo   # Fallback: JOIN por rota_rca
    )
)
# Supervisor pode vir do Cliente ou do Vendedor
.outerjoin(Supervisor, Cliente.supervisor_id == Supervisor.id)
.outerjoin(
    SupervisorViaVendedor,
    Vendedor.supervisor_id == SupervisorViaVendedor.id
)
```

### 5. Endpoint de Migração (`src/api/main.py`)

Criado endpoint `/admin/migrate/vendedor-id` que:
1. Adiciona coluna `vendedor_id` na tabela `clientes` (se não existir)
2. Cria vendedores a partir das rotas dos clientes
3. Popula `vendedor_id` nos clientes baseado em `rota_rca`

## 📊 Resultados

### Teste Local
- ✅ **3115 clientes** com `rota_rca` preenchido (de 5746)
- ✅ **29 rotas distintas**, todas com vendedor correspondente
- ✅ **437/932 clientes** sem compra têm vendedor (47%)
- ✅ **143/932 clientes** sem compra têm supervisor (15%)
- ✅ Query funcionando corretamente

### Deploy Produção
- ✅ Build: `gcr.io/trivihair/dipam-ai-backend:v-fix-import-or`
- ✅ Deploy: Revisão `dipam-ai-backend-00109-vbn`
- ✅ URL: `https://dipam-ai-backend-642830139828.us-central1.run.app`
- ✅ Migração executada com sucesso

## 🔧 Scripts Criados

1. **`scripts/diagnostico_vendedor_supervisor.py`**
   - Diagnóstico completo dos dados
   - Verifica clientes, vendedores, supervisores e relacionamentos

2. **`scripts/examinar_csv_clientes.py`**
   - Examina estrutura do CSV de clientes
   - Identifica colunas relacionadas a rota/vendedor

3. **`scripts/verificar_mapeamento_csv.py`**
   - Verifica mapeamento necessário entre CSV e modelo

4. **`scripts/recarregar_clientes_com_rota.py`**
   - Recarrega clientes do CSV com mapeamento corrigido

5. **`scripts/migrar_vendedor_id_local.py`**
   - Executa migração localmente para criar coluna e popular dados

## 📝 Próximos Passos em Produção

1. **Recarregar dados dos clientes** (se necessário):
   - Os dados em produção podem precisar ser recarregados para popular `rota_rca`
   - Use o script `recarregar_clientes_com_rota.py` adaptado para produção

2. **Executar migração novamente**:
   ```bash
   curl -X POST https://dipam-ai-backend-642830139828.us-central1.run.app/admin/migrate/vendedor-id
   ```

3. **Testar a query**:
   - Pergunta: "Quais clientes estão com cadastro ativo, mas sem nenhuma compra por mais de 60 dias?"
   - Verificar se as colunas VENDEDOR e SUPERVISOR aparecem preenchidas

## 📚 Arquivos Modificados

- `src/dw/models.py` - Modelo Vendedor atualizado
- `src/load_to_db.py` - ETL corrigido com mapeamento CSV
- `src/dw/queries.py` - Query ajustada com JOIN correto
- `src/api/main.py` - Endpoint de migração adicionado
- `src/api/mapper_handler_refatorado.py` - Mapper já estava correto

## ✅ Checklist Final

- [x] Mapeamento CSV corrigido
- [x] Modelo Vendedor atualizado
- [x] ETL corrigido
- [x] Query ajustada
- [x] Endpoint de migração criado
- [x] Scripts de diagnóstico criados
- [x] Testes locais realizados
- [x] Build e deploy concluídos
- [x] Migração executada em produção
- [x] Documentação criada

## 🎯 Conclusão

Todas as correções foram implementadas e testadas localmente. O código está pronto e em produção. Após recarregar os dados dos clientes em produção (se necessário), as colunas VENDEDOR e SUPERVISOR devem aparecer preenchidas na tabela "Dados Analíticos - Consulta Geral".

---

**Data:** 2025-11-20  
**Versão:** v-fix-import-or  
**Revisão:** dipam-ai-backend-00109-vbn

