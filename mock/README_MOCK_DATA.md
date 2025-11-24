# Dados Mock - Guia de Uso

Este documento explica como gerar e atualizar os dados mock usados pelo modo MOCK do DIPAM Copilot.

## 📋 Visão Geral

O modo MOCK usa dados estáticos em JSON gerados a partir dos CSVs reais do cliente. Isso permite:

- ✅ Rodar 100% na Vercel sem Cloud Run/DB
- ✅ Usar dados reais dos CSVs (mesmos números de produção)
- ✅ Atualizar dados facilmente quando novos CSVs chegarem

## 📁 Estrutura de Arquivos

```
mock/
├── source_csv/          # CSVs reais (não commitados, .gitignore)
│   ├── Clientes ativos.xls - Clientes ativos.csv
│   ├── Detalhes de vendas - Set-out 2025.xlsx - Sheet1.csv
│   └── Supervisor pasta 1.xlsx - Sheet1.csv
└── data/                # JSONs gerados (commitados)
    ├── q1_clientes_sem_compra.json
    └── q1_estatisticas.json
```

## 🚀 Como Gerar os Dados Mock

### 1. Preparar os CSVs

Copie os CSVs reais para `mock/source_csv/`:

```bash
# Exemplo: copiar CSVs do data_raw para mock/source_csv
cp "data_raw/Clientes ativos.xls - Clientes ativos.csv" mock/source_csv/
cp "data_raw/Detalhes de vendas - Set-out 2025.xlsx - Sheet1.csv" mock/source_csv/
cp "data_raw/Supervisor pasta 1.xlsx - Sheet1.csv" mock/source_csv/
```

**Arquivos necessários:**
- `Clientes ativos.xls - Clientes ativos.csv` (ou nome similar com "clientes" e "ativos")
- `Detalhes de vendas - Set-out 2025.xlsx - Sheet1.csv` (ou nome similar com "vendas" ou "detalhes")
- `Supervisor pasta 1.xlsx - Sheet1.csv` (ou nome similar com "supervisor")

### 2. Executar o Script de Exportação

```bash
python scripts/export_mock_from_csv.py \
  --input-dir ./mock/source_csv \
  --output-dir ./mock/data
```

**Parâmetros:**
- `--input-dir`: Diretório com os CSVs (padrão: `./mock/source_csv`)
- `--output-dir`: Diretório de saída para JSONs (padrão: `./mock/data`)
- `--dias-minimo`: Número mínimo de dias sem compra (padrão: 60)

**Exemplo com dias mínimo diferente:**
```bash
python scripts/export_mock_from_csv.py \
  --input-dir ./mock/source_csv \
  --output-dir ./mock/data \
  --dias-minimo 90
```

### 3. Verificar os JSONs Gerados

O script gera dois arquivos:

**`mock/data/q1_clientes_sem_compra.json`**
- Lista completa de clientes sem compra há mais de 60 dias
- Estrutura: array de objetos com `cliente_id`, `nome`, `dias_sem_compra`, `vendedor_nome`, `supervisor_nome`, etc.

**`mock/data/q1_estatisticas.json`**
- Estatísticas agregadas
- Total de clientes
- Distribuição por faixas (61-120, 121-180, 181-300, >300)

### 4. Commitar os JSONs

```bash
git add mock/data/*.json
git commit -m "chore: atualiza dados mock Q1 a partir dos CSVs reais"
git push
```

**Importante:** Os CSVs em `mock/source_csv/` NÃO devem ser commitados (estão no .gitignore). Apenas os JSONs gerados.

## 🔄 Fluxo de Atualização

Quando novos CSVs chegarem:

1. **Copiar CSVs para `mock/source_csv/`**
2. **Executar script de exportação**
3. **Verificar JSONs gerados**
4. **Commitar e fazer push dos JSONs**
5. **Vercel fará redeploy automático**

## 🧪 Testar Modo Mock Localmente

```bash
# Configurar variável de ambiente
export NEXT_PUBLIC_DIPAM_ENV=mock

# Iniciar servidor
npm run dev
```

**Validar:**
1. Fazer pergunta Q1: "Quais clientes estão com cadastro ativo, mas sem nenhuma compra por mais de 60 dias?"
2. Verificar:
   - ✅ Big Number mostra total do JSON
   - ✅ Tabela lista clientes do JSON
   - ✅ Faixas estão corretas
   - ✅ Nenhuma chamada ao backend real (verificar Network tab)

## 📊 Estrutura dos JSONs

### q1_clientes_sem_compra.json

```json
[
  {
    "cliente_id": 39,
    "nome": "MERCADO PIOVESANI DORNELLES",
    "segmento": "",
    "rota_id": "ROTA 51",
    "vendedor_nome": "ROTA 51",
    "vendedor_codigo": "",
    "supervisor_nome": "SUPERVISÃO GPOA",
    "supervisor_codigo": "",
    "data_ultima_compra": "2024-09-01T00:00:00",
    "dias_sem_compra": 61
  }
]
```

### q1_estatisticas.json

```json
{
  "total_clientes": 932,
  "faixas": {
    "61_120": 497,
    "121_180": 178,
    "181_300": 221,
    "acima_300": 36
  },
  "data_exportacao": "2025-01-01T12:00:00",
  "dias_filtro": 60
}
```

## 🔍 Lógica Aplicada

O script replica a mesma lógica da Q1 do DW:

1. **Filtra clientes ativos:**
   - Remove clientes com "Bloquear Cliente por Inatividade" = "Sim(S)"

2. **Calcula última compra:**
   - Agrupa vendas por cliente
   - Pega data máxima de compra

3. **Calcula dias sem compra:**
   - `dias_sem_compra = data_referencia - data_ultima_compra`
   - Se nunca comprou, considera 999 dias

4. **Filtra por dias:**
   - Apenas clientes com `dias_sem_compra >= 61` (mais de 60 dias)

5. **Associa vendedor/supervisor:**
   - Busca rota no CSV de clientes
   - Busca supervisor no CSV de supervisores pela rota

6. **Remove duplicatas:**
   - Garante 1 linha por cliente

## ⚠️ Troubleshooting

### Erro: "Arquivo de clientes não encontrado"

**Solução:** Verifique se os CSVs estão em `mock/source_csv/` com nomes que contenham:
- "clientes" e "ativos" (para clientes)
- "vendas" ou "detalhes" (para vendas)
- "supervisor" (para supervisores)

### Erro: "Coluna de data não encontrada"

**Solução:** O script procura colunas com "data" no nome. Verifique se o CSV de vendas tem uma coluna de data.

### Dados não aparecem no modo mock

**Solução:**
1. Verifique se os JSONs foram gerados corretamente
2. Verifique se os JSONs estão commitados
3. Verifique logs do servidor (Vercel) para ver se os arquivos foram carregados
4. O mock engine tem fallback hardcoded se os arquivos não forem encontrados

### Números diferentes de produção

**Solução:**
1. Verifique se está usando os CSVs mais recentes
2. Verifique se a data de referência está correta (script usa data atual por padrão)
3. Compare com o resultado do DW de produção para validar

## 📝 Notas

- Os CSVs em `mock/source_csv/` estão no `.gitignore` (não são commitados)
- Apenas os JSONs gerados em `mock/data/` são commitados
- O script é idempotente: pode ser executado múltiplas vezes
- A data de referência padrão é a data atual (pode ser ajustada no código se necessário)

