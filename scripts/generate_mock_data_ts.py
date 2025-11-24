#!/usr/bin/env python3
"""
Script para gerar arquivo TypeScript com dados mock Q1 incluídos diretamente no código.
Isso garante que os dados estejam sempre disponíveis, mesmo na Vercel onde arquivos JSON
não são copiados para o build standalone.
"""

import json
import sys
from pathlib import Path

def generate_mock_data_ts():
    """Gera arquivo TypeScript com dados mock Q1."""
    project_root = Path(__file__).resolve().parent.parent
    
    # Carrega dados
    clientes_file = project_root / "mock" / "data" / "q1_clientes_sem_compra.json"
    stats_file = project_root / "mock" / "data" / "q1_estatisticas.json"
    
    if not clientes_file.exists():
        print(f"❌ Arquivo não encontrado: {clientes_file}")
        sys.exit(1)
    
    if not stats_file.exists():
        print(f"❌ Arquivo não encontrado: {stats_file}")
        sys.exit(1)
    
    with open(clientes_file, 'r', encoding='utf-8') as f:
        clientes = json.load(f)
    
    with open(stats_file, 'r', encoding='utf-8') as f:
        stats = json.load(f)
    
    # Gera código TypeScript
    output_file = project_root / "lib" / "mock" / "mockDataGenerated.ts"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("""/**
 * Dados mock Q1 gerados automaticamente
 * 
 * Este arquivo é gerado pelo script scripts/generate_mock_data_ts.py
 * a partir dos JSONs em mock/data/
 * 
 * ⚠️ NÃO EDITAR MANUALMENTE - será sobrescrito pelo script
 */

""")
        
        # Estatísticas
        f.write("export const q1EstatisticasMock = ")
        f.write(json.dumps(stats, indent=2, ensure_ascii=False))
        f.write(";\n\n")
        
        # Clientes
        f.write("export const q1ClientesMock: any[] = ")
        f.write(json.dumps(clientes, indent=2, ensure_ascii=False))
        f.write(";\n\n")
        
        f.write(f"// Total: {len(clientes)} clientes\n")
        f.write(f"// Gerado em: {Path(__file__).stat().st_mtime}\n")
    
    print(f"✅ Arquivo gerado: {output_file}")
    print(f"   - {len(clientes)} clientes")
    print(f"   - Estatísticas: {stats['total_clientes']} clientes totais")
    print(f"   - Tamanho: {output_file.stat().st_size / 1024:.1f} KB")

if __name__ == "__main__":
    generate_mock_data_ts()

