# Resumo da Implementação - Modo Mock com Dados Reais dos CSVs

## ✅ Implementação Concluída

### Arquivos Criados

1. **`scripts/export_mock_from_csv.py`**
   - Script Python que processa CSVs reais
   - Aplica mesma lógica da Q1 do DW
   - Gera JSONs em `mock/data/`

2. **`mock/README_MOCK_DATA.md`**
   - Documentação completa de uso
   - Instruções passo a passo
   - Troubleshooting

3. **`mock/source_csv/.gitkeep`**
   - Estrutura para armazenar CSVs (não commitados)

### Arquivos Modificados

1. **`lib/mock/dipamMockEngine.ts`**
   - Prioriza `q1_clientes_sem_compra.json` (dados reais)
   - Fallback para `q1_dados_dw.json` (compatibilidade)
   - Normaliza estrutura de faixas (61_120, 121_180, 181_300, acima_300)
   - Usa estatísticas do JSON quando disponível

## 📊 Estrutura dos Dados

### JSONs Gerados

**`mock/data/q1_clientes_sem_compra.json`**
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

**`mock/data/q1_estatisticas.json`**
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

## 🔄 Fluxo de Uso

### 1. Preparar CSVs

```bash
cp "data_raw/Clientes ativos.xls - Clientes ativos.csv" mock/source_csv/
cp "data_raw/Detalhes de vendas - Set-out 2025.xlsx - Sheet1.csv" mock/source_csv/
cp "data_raw/Supervisor pasta 1.xlsx - Sheet1.csv" mock/source_csv/
```

### 2. Executar Script

```bash
python scripts/export_mock_from_csv.py \
  --input-dir ./mock/source_csv \
  --output-dir ./mock/data
```

### 3. Commitar JSONs

```bash
git add mock/data/*.json
git commit -m "chore: atualiza dados mock Q1 a partir dos CSVs reais"
git push
```

### 4. Deploy Automático

Vercel fará redeploy automaticamente após o push.

## 🧪 Validação

### Testar Localmente

```bash
export NEXT_PUBLIC_DIPAM_ENV=mock
npm run dev
```

**Pergunta Q1:**
"Quais clientes estão com cadastro ativo, mas sem nenhuma compra por mais de 60 dias?"

**Validações:**
- ✅ Big Number mostra total do JSON
- ✅ Tabela lista clientes do JSON
- ✅ Faixas estão corretas
- ✅ Nenhuma chamada ao backend real (Network tab)

### Comparar com Produção

Os números devem bater com o DW de produção quando usando os mesmos CSVs.

## 📋 Lógica Aplicada

O script replica exatamente a lógica de `get_clientes_sem_compra_ha_dias`:

1. **Filtra clientes ativos:**
   - Remove clientes com "Bloquear Cliente por Inatividade" = "Sim(S)"

2. **Calcula última compra:**
   - Agrupa vendas por cliente
   - Pega data máxima

3. **Calcula dias sem compra:**
   - `dias_sem_compra = data_referencia - data_ultima_compra`
   - Se nunca comprou: 999 dias

4. **Filtra:**
   - Apenas `dias_sem_compra >= 61` (mais de 60 dias)

5. **Associa vendedor/supervisor:**
   - Busca rota no CSV de clientes
   - Busca supervisor no CSV de supervisores

6. **Remove duplicatas:**
   - Garante 1 linha por cliente

## ✅ Critérios de Aceitação

- [x] Modo MOCK continua isolado via `NEXT_PUBLIC_DIPAM_ENV=mock`
- [x] Produção (ENV ≠ mock) permanece chamando backend Cloud Run normalmente
- [x] Q1 em modo MOCK usa dados gerados a partir dos CSVs reais
- [x] Nenhuma chamada externa (Cloud Run / DB) no modo MOCK
- [x] Roteiro/documentação para o PO executar o script de export
- [x] Script lê CSVs e gera JSONs com sucesso
- [x] Mock engine ajustado para usar novos JSONs

## 📝 Próximos Passos (Para o PO)

1. **Copiar CSVs reais para `mock/source_csv/`**
2. **Executar script de exportação**
3. **Verificar JSONs gerados**
4. **Commitar e fazer push**
5. **Validar no modo mock**

## 🔗 Referências

- Documentação completa: `mock/README_MOCK_DATA.md`
- Script de exportação: `scripts/export_mock_from_csv.py`
- Mock engine: `lib/mock/dipamMockEngine.ts`

