# Modo Mock - Dados Reais da Base Dipam

Este diretório contém os dados mock para o modo de demonstração do DIPAM Copilot™.

## 📋 Visão Geral

O modo MOCK permite executar o DIPAM Copilot 100% na Vercel, sem depender de Cloud Run ou banco externo. Os dados são "congelados" em JSONs estáticos gerados a partir da base real.

**Importante:** O modo MOCK não é para testes técnicos, é para **DEMO executiva**. Os dados devem ser consistentes com a Q1 real.

## 🗂️ Estrutura de Arquivos

```
mock/
├── data/
│   ├── q1_clientes_sem_compra.json    # Lista de clientes (tabela principal)
│   └── q1_estatisticas.json           # Estatísticas (Big Number, faixas)
├── source_csv/                        # CSVs originais (opcional, para fallback)
└── README_MOCK_DATA.md                # Este arquivo
```

## 🚀 Gerando Snapshot Mock

### Opção A: Usando a Query Real do DW (Recomendado)

Use o script que chama diretamente a função `get_clientes_sem_compra_ha_dias`:

```bash
python scripts/generate_mock_snapshot_q1.py \
  --output-dir ./mock/data \
  --dias 60 \
  --data-referencia 2025-10-31
```

**Requisitos:**
- Base local já alimentada pelo ETL
- Banco SQLite ou PostgreSQL acessível
- Módulos do projeto instalados (`pip install -r requirements.txt`)

**Vantagens:**
- ✅ Usa exatamente a mesma lógica da Q1 real
- ✅ Garante consistência total
- ✅ Validações automáticas

### Opção B: Usando CSVs (Fallback)

Se a base não estiver disponível, use o script que processa CSVs:

```bash
# 1. Copie os CSVs para mock/source_csv/
cp "Clientes ativos.xls - Clientes ativos.csv" mock/source_csv/
cp "Detalhes de vendas - Set-out 2025.xlsx - Sheet1.csv" mock/source_csv/
cp "Supervisor pasta 1.xlsx - Sheet1.csv" mock/source_csv/

# 2. Execute o script
python scripts/export_mock_from_csv.py \
  --input-dir ./mock/source_csv \
  --output-dir ./mock/data \
  --dias-minimo 60
```

**Requisitos:**
- CSVs reais fornecidos pela Dipam
- Python com pandas instalado

**Limitações:**
- Pode ter pequenas diferenças em relação à query real (devido a diferenças de processamento)

## ✅ Validando Consistência

Após gerar os JSONs, valide que estão consistentes com a Q1 real:

```bash
python scripts/test_mock_q1_consistencia.py \
  --dias 60 \
  --data-referencia 2025-10-31 \
  --mock-data-dir ./mock/data \
  --tolerancia 0
```

**Validações realizadas:**
- ✅ Total de clientes mock == total Q1 real
- ✅ `total_clientes` no JSON stats == `len(clientes)` no JSON clientes
- ✅ Sem duplicatas no JSON mock
- ✅ Todos os clientes têm >= 61 dias sem compra
- ✅ Soma das faixas == total_clientes
- ✅ IDs de clientes idênticos entre real e mock (se tolerância = 0)

**Saída esperada:**
```
✅ VALIDAÇÃO PASSOU: Q1 mock está consistente com Q1 real!
```

## 📊 Estrutura dos JSONs

### `q1_clientes_sem_compra.json`

Lista de clientes (array de objetos):

```json
[
  {
    "cliente_id": 39,
    "nome": "Nome do Cliente",
    "segmento": "Segmento A",
    "rota_id": "ROTA 301",
    "vendedor_nome": "Vendedor Nome",
    "vendedor_codigo": "V001",
    "supervisor_nome": "Supervisor Nome",
    "supervisor_codigo": "S001",
    "data_ultima_compra": "2024-01-01",
    "dias_sem_compra": 90
  }
]
```

**Campos obrigatórios:**
- `cliente_id`: int (não string)
- `dias_sem_compra`: int (não string, >= 61)
- `nome`: string
- `vendedor_nome`: string (pode ser rota_id se vendedor não disponível)
- `supervisor_nome`: string

### `q1_estatisticas.json`

Estatísticas para Big Number e Resumo Executivo:

```json
{
  "total_clientes": 932,
  "faixas": {
    "61_120": 497,
    "121_180": 178,
    "181_300": 221,
    "acima_300": 36
  },
  "data_referencia": "2025-10-31",
  "data_exportacao": "2025-01-15T10:30:00",
  "dias_filtro": 60,
  "fonte": "query_real_dw"
}
```

**Campos obrigatórios:**
- `total_clientes`: int (não string)
- `faixas`: objeto com chaves `"61_120"`, `"121_180"`, `"181_300"`, `"acima_300"` (valores int)
- `data_referencia`: string (YYYY-MM-DD)
- `data_exportacao`: string (ISO 8601)

## 🔧 Uso no Frontend

O mock engine (`lib/mock/dipamMockEngine.ts`) carrega automaticamente os JSONs:

1. Tenta carregar `mock/data/q1_clientes_sem_compra.json`
2. Tenta carregar `mock/data/q1_estatisticas.json`
3. Se não encontrar, usa dados fallback (5 clientes de exemplo)

**Modo Mock ativo:**
```bash
export NEXT_PUBLIC_DIPAM_ENV=mock
npm run dev
```

**Pergunta de teste:**
```
Quais clientes estão com cadastro ativo, mas sem nenhuma compra por mais de 60 dias?
```

## 🧪 Testes Manuais

### 1. Gerar Snapshot

```bash
python scripts/generate_mock_snapshot_q1.py --output-dir ./mock/data
```

### 2. Verificar JSONs

```bash
# Ver total de clientes
cat mock/data/q1_estatisticas.json | grep total_clientes

# Ver primeiros clientes
head -20 mock/data/q1_clientes_sem_compra.json
```

### 3. Validar Consistência

```bash
python scripts/test_mock_q1_consistencia.py
```

### 4. Testar Localmente

```bash
export NEXT_PUBLIC_DIPAM_ENV=mock
npm run dev
```

### 5. Validar UI

- ✅ Big Number mostra o total real (não "5 clientes")
- ✅ Resumo Executivo fala em números coerentes (centenas de clientes)
- ✅ Tabela lista clientes REAIS (nome, rota, supervisor)
- ✅ Faixas exibidas corretamente
- ✅ Nenhum erro no console

### 6. Build

```bash
npm run build
```

Deve passar sem erros.

## 📝 Commit dos JSONs

Os JSONs gerados devem ser commitados no repositório:

```bash
git add mock/data/q1_clientes_sem_compra.json
git add mock/data/q1_estatisticas.json
git commit -m "feat: atualiza dados mock Q1 com snapshot real da base"
```

**Importante:** Atualize os JSONs sempre que:
- A base for atualizada com novos dados
- A lógica da Q1 for alterada
- Houver necessidade de atualizar a demo

## 🚨 Troubleshooting

### Erro: "Não foi possível inicializar conexão com banco"

**Solução:** Execute o ETL primeiro:
```bash
python scripts/run_etl.py
```

### Erro: "Arquivo não encontrado"

**Solução:** Verifique se os JSONs existem:
```bash
ls -la mock/data/
```

### Erro: "Validação falhou"

**Solução:** 
1. Verifique se a base está atualizada
2. Execute o script de geração novamente
3. Verifique os logs para identificar a divergência

### Mock mostra "5 clientes" (dados fallback)

**Solução:** 
1. Verifique se os JSONs existem em `mock/data/`
2. Verifique os logs do mock engine no console do navegador
3. Verifique se o caminho está correto (Vercel pode ter estrutura diferente)

## 📚 Referências

- Query real: `src/dw/queries.py` → `get_clientes_sem_compra_ha_dias`
- Mock engine: `lib/mock/dipamMockEngine.ts`
- Script de geração: `scripts/generate_mock_snapshot_q1.py`
- Script de validação: `scripts/test_mock_q1_consistencia.py`
- Script CSV fallback: `scripts/export_mock_from_csv.py`
