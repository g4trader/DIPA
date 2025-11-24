# Dados Brutos (data_raw/)

Este diretório contém os dados brutos (CSVs) que serão processados pelo pipeline ETL.

## Estrutura Esperada

### Arquivos CSV Esperados

1. **clientes.csv**: Dados de clientes
   - Colunas esperadas: `codigo`, `nome`, `email`, `telefone`, `cidade`, `estado`, `ativo`, `data_cadastro`

2. **vendedores.csv**: Dados de vendedores
   - Colunas esperadas: `codigo`, `nome`, `email`, `supervisor_id`, `ativo`

3. **supervisores.csv**: Dados de supervisores/pastas
   - Colunas esperadas: `codigo`, `nome`, `pasta`, `ativo`

4. **vendas.csv**: Dados de vendas
   - Colunas esperadas: `cliente_id`, `vendedor_id`, `data_venda`, `valor`, `quantidade`, `produto`

5. **metas_vendedor.csv**: Dados de metas por vendedor
   - Colunas esperadas: `vendedor_id`, `ano`, `mes`, `meta_valor`, `realizado_valor`

6. **metas_departamento.csv**: Dados de metas por departamento
   - Colunas esperadas: `supervisor_id`, `ano`, `mes`, `meta_valor`, `realizado_valor`

## Formatos Esperados

### Datas
- Formato brasileiro: `DD/MM/YYYY` ou `DD-MM-YYYY`
- Formato ISO: `YYYY-MM-DD`

### Valores Monetários
- Formato brasileiro: `R$ 1.234,56`
- Separador decimal: vírgula (`,`)
- Separador de milhares: ponto (`.`)

### Números
- Separador decimal: vírgula (`,`)
- Separador de milhares: ponto (`.`)

## Uso

1. Coloque os arquivos CSV neste diretório
2. Execute o pipeline ETL: `python scripts/run_etl.py`
3. Os dados serão processados e carregados no data warehouse

## Notas

- Os arquivos CSV devem estar em formato UTF-8 ou Latin-1
- O pipeline ETL tentará inferir o encoding automaticamente
- Valores faltantes serão tratados durante o processamento
- Duplicatas serão removidas durante o processamento





