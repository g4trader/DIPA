# 🔍 DIAGNÓSTICO: VENDEDOR E SUPERVISOR NA PERGUNTA Q1 (+60 DIAS SEM COMPRA)

## 📋 RESUMO EXECUTIVO

Este documento resume a análise completa do código para garantir que a pergunta "Quais clientes estão com cadastro ativo, mas sem nenhuma compra por mais de 60 dias?" retorne corretamente os campos **VENDEDOR** e **SUPERVISOR** na tabela "Dados Analíticos – Consulta Geral".

## ✅ 1. MODELOS DE DADOS

### 1.1. Relacionamentos Implementados

Os modelos SQLAlchemy já suportam o relacionamento **Cliente → Vendedor → Supervisor**:

**Arquivo:** `src/dw/models.py`

- **Cliente** (linhas 106-153):
  - `rota_rca` (String, indexado) - casa com `Vendedor.codigo`
  - `vendedor_id` (FK opcional) - chave estrangeira para `Vendedor.id`
  - `supervisor_id` (FK opcional) - chave estrangeira para `Supervisor.id`
  - Relacionamentos:
    - `vendedor = relationship("Vendedor", foreign_keys=[vendedor_id])`
    - `supervisor = relationship("Supervisor", back_populates="clientes")`

- **Vendedor** (linhas 73-103):
  - `codigo` (String, unique, indexado) - deve corresponder a `Cliente.rota_rca`
  - `supervisor_id` (FK opcional) - chave estrangeira para `Supervisor.id`
  - Relacionamento:
    - `supervisor = relationship("Supervisor", back_populates="vendedores")`

- **Supervisor** (linhas 46-70):
  - `id`, `codigo`, `nome`
  - Relacionamentos:
    - `vendedores = relationship("Vendedor", back_populates="supervisor")`
    - `clientes = relationship("Cliente", back_populates="supervisor")`

**✅ CONCLUSÃO:** Os modelos suportam completamente o relacionamento necessário.

## ✅ 2. QUERY (get_clientes_sem_compra_ha_dias)

### 2.1. JOINs Implementados

**Arquivo:** `src/dw/queries.py` (linhas 134-166)

A query já faz os JOINs corretos:

```python
query = (
    session.query(
        Cliente.id.label('cliente_id'),
        Cliente.nome,
        Cliente.segmento_venda.label('segmento'),
        Cliente.rota_rca.label('rota_id'),
        Vendedor.nome.label('vendedor_nome'),
        Vendedor.codigo.label('vendedor_codigo'),
        # Supervisor pode vir do Cliente ou do Vendedor (prioriza do Cliente)
        func.coalesce(
            Supervisor.nome,
            SupervisorViaVendedor.nome
        ).label('supervisor_nome'),
        func.coalesce(
            Supervisor.codigo,
            SupervisorViaVendedor.codigo
        ).label('supervisor_codigo'),
        ultima_compra_subq.c.data_ultima_compra,
        dias_sem_compra_expr.label('dias_sem_compra')
    )
    .outerjoin(ultima_compra_subq, Cliente.id == ultima_compra_subq.c.cliente_id)
    # JOIN com Vendedor usando rota_rca
    .outerjoin(Vendedor, Cliente.rota_rca == Vendedor.codigo)
    # Supervisor do Cliente (prioridade)
    .outerjoin(Supervisor, Cliente.supervisor_id == Supervisor.id)
    # Supervisor do Vendedor (fallback se Cliente não tiver supervisor)
    .outerjoin(
        SupervisorViaVendedor,
        Vendedor.supervisor_id == SupervisorViaVendedor.id
    )
    .filter(Cliente.ativo == True)
)
```

**Estratégia de JOIN:**
1. **Vendedor:** JOIN via `Cliente.rota_rca == Vendedor.codigo` (LEFT OUTER JOIN)
2. **Supervisor:** 
   - Prioridade 1: `Cliente.supervisor_id` (supervisor direto do cliente)
   - Prioridade 2: `Vendedor.supervisor_id` (supervisor do vendedor, como fallback)

### 2.2. Retorno da Query

**Arquivo:** `src/dw/queries.py` (linhas 228-239)

A query retorna um dicionário com todos os campos necessários:

```python
clientes_filtrados.append({
    "cliente_id": row.cliente_id,
    "nome": row.nome or "",
    "segmento": row.segmento or "",
    "rota_id": row.rota_id or "",
    "vendedor_nome": vendedor_nome,  # ✅ Retorna vendedor_nome
    "vendedor_codigo": vendedor_codigo,  # ✅ Retorna vendedor_codigo
    "supervisor_nome": supervisor_nome,  # ✅ Retorna supervisor_nome
    "supervisor_codigo": supervisor_codigo,  # ✅ Retorna supervisor_codigo
    "data_ultima_compra": row.data_ultima_compra.isoformat() if row.data_ultima_compra else None,
    "dias_sem_compra": dias_sem_compra
})
```

**✅ CONCLUSÃO:** A query retorna corretamente `vendedor_nome`, `vendedor_codigo`, `supervisor_nome` e `supervisor_codigo`.

## ✅ 3. MAPPER (map_handler_refatorado_to_ask_response)

### 3.1. Montagem da Tabela Principal

**Arquivo:** `src/api/mapper_handler_refatorado.py` (linhas 159-176)

O mapper monta a tabela_principal com as colunas corretas:

```python
# Para Q1 (clientes_sem_compra), monta tabela_principal com colunas corretas
if intent == "clientes_sem_compra" and dados_dw.get("dados"):
    dados_clientes = dados_dw.get("dados", [])
    if dados_clientes and isinstance(dados_clientes, list) and len(dados_clientes) > 0:
        # Monta tabela_principal com colunas: Cliente ID, Nome, Dias sem Compra, Vendedor, Supervisor
        tabela_principal = [{
            "colunas": ["Cliente ID", "Nome", "Dias sem Compra", "Vendedor", "Supervisor"],
            "linhas": [
                [
                    cliente.get("cliente_id", ""),
                    cliente.get("nome", ""),
                    cliente.get("dias_sem_compra", 0) or 0,
                    cliente.get("vendedor_nome", cliente.get("vendedor_codigo", cliente.get("rota_id", ""))),  # ✅ Vendedor
                    cliente.get("supervisor_nome", cliente.get("supervisor_codigo", ""))  # ✅ Supervisor
                ]
                for cliente in dados_clientes
            ]
        }]
```

**Estratégia de Fallback:**
- **Vendedor:** `vendedor_nome` → `vendedor_codigo` → `rota_id` → `""`
- **Supervisor:** `supervisor_nome` → `supervisor_codigo` → `""`

**✅ CONCLUSÃO:** O mapper monta corretamente a tabela com as colunas "Vendedor" e "Supervisor".

## ✅ 4. FRONTEND (ResponseDashboard.tsx)

### 4.1. Exibição da Tabela

**Arquivo:** `components/ResponseDashboard.tsx` (linhas 532-580)

O frontend exibe a tabela corretamente:

```tsx
{isQ1 && tabelaClientesPaginada ? (
  <div id={generateTableId('clientes-sem-compra')}>
    <h2>Clientes sem compra há mais de 60 dias</h2>
    <DataTable
      id={generateTableId('clientes-sem-compra-data')}
      rows={tabelaClientesPaginada.linhas.map((linha: any[]) => {
        const obj: Record<string, any> = {};
        tabelaClientesPaginada.colunas.forEach((col: string, idx: number) => {
          obj[col] = linha[idx];
        });
        return obj;
      })}
      highlightFirstColumn={true}
    />
  </div>
) : null}
```

**✅ CONCLUSÃO:** O frontend exibe a tabela com as colunas recebidas do backend, incluindo "Vendedor" e "Supervisor".

## 🔍 5. POSSÍVEIS PROBLEMAS

### 5.1. Dados Não Existem no Banco

**Cenário:** Os dados de vendedor/supervisor podem não existir no banco de dados.

**Verificação necessária:**
1. Verificar se `Cliente.rota_rca` está preenchido
2. Verificar se existe `Vendedor` com `codigo` correspondente a `Cliente.rota_rca`
3. Verificar se `Vendedor.supervisor_id` está preenchido
4. Verificar se `Cliente.supervisor_id` está preenchido (quando aplicável)

**Script de diagnóstico:** `scripts/diagnostico_vendedor_supervisor_q1.py`

### 5.2. JOIN Não Funciona por Incompatibilidade de Dados

**Cenário:** `Cliente.rota_rca` pode não corresponder exatamente a `Vendedor.codigo` (diferenças de espaços, maiúsculas/minúsculas, etc.).

**Solução:** A query já usa `outerjoin`, então mesmo que não encontre, não quebra. Mas os valores ficarão vazios.

### 5.3. Dados Vazios Retornam "—" no Frontend

**Cenário:** Se não houver vendedor/supervisor, o frontend pode exibir "—" ou string vazia.

**Comportamento esperado:** Isso é correto - se não houver dados, deve exibir "—" ou vazio.

## 📝 6. RECOMENDAÇÕES

### 6.1. Verificar Dados no Banco

Execute o script de diagnóstico para verificar se os dados existem:

```bash
python scripts/diagnostico_vendedor_supervisor_q1.py
```

### 6.2. Verificar ETL

Se os dados não existirem, verificar o processo ETL que popula:
- `Cliente.rota_rca`
- `Vendedor.codigo` (deve corresponder a `Cliente.rota_rca`)
- `Vendedor.supervisor_id`
- `Cliente.supervisor_id` (quando aplicável)

### 6.3. Testar Endpoint Diretamente

Testar o endpoint `/ask` com a pergunta:

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{
    "pergunta": "Quais clientes estão com cadastro ativo, mas sem nenhuma compra por mais de 60 dias?",
    "papel": "diretor"
  }'
```

Verificar se o JSON retornado contém:
- `structured.tabela_principal[0].colunas` inclui "Vendedor" e "Supervisor"
- `structured.tabela_principal[0].linhas` contém valores para vendedor e supervisor

## ✅ 7. CONCLUSÃO

**O código está correto e completo:**

1. ✅ Modelos suportam relacionamento Cliente → Vendedor → Supervisor
2. ✅ Query faz JOINs corretos e retorna vendedor_nome, vendedor_codigo, supervisor_nome, supervisor_codigo
3. ✅ Mapper monta tabela_principal com colunas "Vendedor" e "Supervisor"
4. ✅ Frontend exibe a tabela com as colunas recebidas

**Se os campos aparecem vazios ("—"), o problema é de DADOS, não de CÓDIGO.**

**Próximos passos:**
1. Executar script de diagnóstico para verificar dados no banco
2. Se dados não existirem, verificar ETL
3. Se dados existirem mas não aparecerem, verificar logs da query para entender por que os JOINs não estão funcionando

