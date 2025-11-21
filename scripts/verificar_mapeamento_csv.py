#!/usr/bin/env python3
"""
Script para verificar como as colunas do CSV devem ser mapeadas para o modelo Cliente.
"""

import pandas as pd
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

csv_path = os.path.join(os.path.dirname(__file__), '..', 'data_raw', 'Clientes ativos.xls - Clientes ativos.csv')

print("=" * 80)
print("VERIFICANDO MAPEAMENTO CSV -> MODELO CLIENTE")
print("=" * 80)

df = pd.read_csv(csv_path, nrows=10)

print("\nColunas no CSV:")
for col in df.columns:
    print(f"  - {col}")

print("\n" + "=" * 80)
print("MAPEAMENTO NECESSÁRIO:")
print("=" * 80)

# Mapeamento necessário baseado no que vimos
mapeamento = {
    'Código': 'codigo',
    'CNPJ/CPF': 'cnpj_cpf',
    'Fantasia': 'fantasia',
    'Cliente': 'nome',
    'Estado': 'estado',
    'Município': 'municipio',
    'Nome RCA': 'nome_rca',  # ✅ Esta coluna existe no CSV
    'Nome RCA': 'rota_rca',  # ⚠️ PROBLEMA: Nome RCA deveria ser rota_rca?
    # Mas vimos que "Nome RCA" tem valores como "ROTA 304", "ROTA 74 VD"
    # Então "Nome RCA" deveria mapear para rota_rca!
    'Vendedor 1': 'vendedor_codigo',  # Código numérico do vendedor
}

print("\nMapeamento sugerido:")
for csv_col, model_field in mapeamento.items():
    if csv_col in df.columns:
        valores_exemplo = df[csv_col].dropna().head(3).tolist()
        print(f"  CSV['{csv_col}'] -> Cliente.{model_field}")
        print(f"    Exemplos: {valores_exemplo}")
    else:
        print(f"  ⚠️  CSV['{csv_col}'] -> Cliente.{model_field} (COLUNA NÃO ENCONTRADA)")

print("\n" + "=" * 80)
print("PROBLEMA IDENTIFICADO:")
print("=" * 80)
print("""
O CSV tem a coluna 'Nome RCA' que contém valores como:
  - 'ROTA 304'
  - 'ROTA 74 VD'
  - 'ROTA 34 VD'
  
Mas o código em load_clientes_to_db está procurando por:
  - 'rota_rca' (minúsculas, sem espaço)
  - 'nome_rca' (minúsculas, sem espaço)

SOLUÇÃO: Precisamos mapear 'Nome RCA' -> 'rota_rca' no código de ETL.
""")

print("\n" + "=" * 80)
print("VERIFICANDO VALORES DE 'Nome RCA':")
print("=" * 80)
if 'Nome RCA' in df.columns:
    valores_rota = df['Nome RCA'].dropna().unique()
    print(f"Total de valores únicos não-nulos: {len(valores_rota)}")
    print(f"Valores únicos (primeiros 10): {valores_rota[:10].tolist()}")
    
    # Verifica se há correspondência com vendedores
    print("\nVerificando correspondência com 'Vendedor 1':")
    df_com_rota = df[df['Nome RCA'].notna()]
    if len(df_com_rota) > 0:
        print(df_com_rota[['Código', 'Fantasia', 'Vendedor 1', 'Nome RCA']].head(5).to_string())


