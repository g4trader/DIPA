# CSVs Fonte para Modo Mock

Esta pasta deve conter os CSVs reais fornecidos pela Dipam.

## 📁 Arquivos Necessários

### 1. Clientes
- `Clientes ativos.xls - Clientes ativos.csv`

### 2. Vendas (todos os arquivos serão consolidados)
- `Detalhes de vendas - Jan-fev 2025.xlsx - Sheet1.csv`
- `Detalhes de vendas - Mar-Abr 2025.xlsx - Sheet1.csv`
- `Detalhes de vendas - Mai-Jun 2025.xlsx - Sheet1.csv`
- `Detalhes de vendas - Jul-ago 2025.xlsx - Sheet1.csv`
- `Detalhes de vendas - Set-out 2025.xlsx - Sheet1.csv`
- `Detalhes de vendas - Nov-dez 2024.xlsx - Sheet1.csv`

### 3. Supervisores
- `Supervisor pasta 1.xlsx - Sheet1.csv`

## 🚀 Como Adicionar os CSVs

1. **Extraia o arquivo zip fornecido pela Dipam**

2. **Copie os CSVs para esta pasta:**

```bash
# Exemplo
cp "Clientes ativos.xls - Clientes ativos.csv" mock/source_csv/
cp "Detalhes de vendas - *.csv" mock/source_csv/
cp "Supervisor pasta 1.xlsx - Sheet1.csv" mock/source_csv/
```

3. **Execute o script de geração:**

```bash
python scripts/generate_mock_snapshot_q1.py \
  --input-dir ./mock/source_csv \
  --output-dir ./mock/data
```

## ⚠️ Importante

- Esta pasta está no `.gitignore` (CSVs não são commitados)
- Apenas os JSONs gerados em `mock/data/` são commitados
- Os CSVs devem ter os nomes exatos ou similares para serem detectados automaticamente

