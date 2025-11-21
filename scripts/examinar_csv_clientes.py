#!/usr/bin/env python3
"""
Script para examinar o CSV de clientes e identificar campos relacionados a rota/vendedor.
"""

import pandas as pd
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

csv_path = os.path.join(os.path.dirname(__file__), '..', 'data_raw', 'Clientes ativos.xls - Clientes ativos.csv')

print("=" * 80)
print("EXAMINANDO CSV DE CLIENTES")
print("=" * 80)

# Lê apenas as primeiras linhas para análise
df = pd.read_csv(csv_path, nrows=20)

print(f"\nTotal de colunas: {len(df.columns)}")
print(f"\nTodas as colunas:")
for i, col in enumerate(df.columns, 1):
    print(f"  {i:2d}. {col}")

# Procura colunas relacionadas
print("\n" + "=" * 80)
print("COLUNAS RELACIONADAS A ROTA/VENDEDOR/SUPERVISOR:")
print("=" * 80)

cols_relacionadas = []
for col in df.columns:
    col_lower = col.lower()
    if any(termo in col_lower for termo in ['rota', 'rca', 'vendedor', 'supervisor']):
        cols_relacionadas.append(col)
        print(f"  - {col}")

if cols_relacionadas:
    print(f"\nValores de exemplo para essas colunas (primeiras 5 linhas):")
    print(df[cols_relacionadas].head(5).to_string())
    
    print(f"\nValores únicos em cada coluna relacionada:")
    for col in cols_relacionadas:
        valores_unicos = df[col].dropna().unique()
        print(f"\n  {col}:")
        print(f"    Total de valores não-nulos: {df[col].notna().sum()}")
        print(f"    Valores únicos (primeiros 10): {valores_unicos[:10].tolist()}")

# Verifica também o arquivo de vendas para ver se tem informações de rota
print("\n" + "=" * 80)
print("EXAMINANDO CSV DE VENDAS (primeiro arquivo):")
print("=" * 80)

vendas_files = [f for f in os.listdir(os.path.join(os.path.dirname(__file__), '..', 'data_raw')) 
              if 'Detalhes de vendas' in f and f.endswith('.csv')]

if vendas_files:
    vendas_path = os.path.join(os.path.dirname(__file__), '..', 'data_raw', vendas_files[0])
    print(f"Arquivo: {vendas_files[0]}")
    df_vendas = pd.read_csv(vendas_path, nrows=10)
    
    print(f"\nColunas do arquivo de vendas:")
    for i, col in enumerate(df_vendas.columns, 1):
        print(f"  {i:2d}. {col}")
    
    cols_vendas_relacionadas = [c for c in df_vendas.columns 
                                if any(termo in c.lower() for termo in ['rota', 'rca', 'vendedor', 'supervisor'])]
    if cols_vendas_relacionadas:
        print(f"\nColunas relacionadas a rota/vendedor/supervisor:")
        for col in cols_vendas_relacionadas:
            print(f"  - {col}")
        print(f"\nValores de exemplo:")
        print(df_vendas[cols_vendas_relacionadas].head(5).to_string())

print("\n" + "=" * 80)
print("ANÁLISE CONCLUÍDA")
print("=" * 80)


