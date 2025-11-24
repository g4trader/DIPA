#!/usr/bin/env python3
"""
Script para exportar dados Q1 da base local para JSON (modo mock).

Este script:
1. Conecta na base local (SQLite ou PostgreSQL)
2. Executa get_clientes_sem_compra_ha_dias(dias=60)
3. Exporta para mock/data/q1_dados_dw.json
4. Calcula e exporta estatísticas para mock/data/q1_estatisticas.json

Uso:
    python scripts/export_mock_q1_from_local_db.py
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime

# Adiciona o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.dw.connection import SessionLocal, init_db
from src.dw.queries import get_clientes_sem_compra_ha_dias


def classificar_por_faixas(dados):
    """Classifica clientes por faixas de dias sem compra."""
    faixas = {
        "faixa_61_120": 0,
        "faixa_121_180": 0,
        "faixa_181_300": 0,
        "faixa_maior_300": 0,
    }
    
    for cliente in dados:
        dias = cliente.get("dias_sem_compra", 0) or 0
        
        if 61 <= dias <= 120:
            faixas["faixa_61_120"] += 1
        elif 121 <= dias <= 180:
            faixas["faixa_121_180"] += 1
        elif 181 <= dias <= 300:
            faixas["faixa_181_300"] += 1
        elif dias > 300:
            faixas["faixa_maior_300"] += 1
    
    return faixas


def exportar_q1_para_json():
    """Exporta dados Q1 para arquivos JSON."""
    # Inicializa banco
    if SessionLocal is None:
        init_db()
    
    session = SessionLocal()
    
    try:
        print("🔄 Executando Q1 (get_clientes_sem_compra_ha_dias)...")
        resultados = get_clientes_sem_compra_ha_dias(session, dias=60)
        
        print(f"✅ Encontrados {len(resultados)} clientes sem compra há mais de 60 dias")
        
        # Cria diretório mock/data se não existir
        mock_data_dir = Path(__file__).parent.parent / "mock" / "data"
        mock_data_dir.mkdir(parents=True, exist_ok=True)
        
        # Calcula estatísticas
        faixas = classificar_por_faixas(resultados)
        total_clientes = len(resultados)
        
        # Prepara dados para exportação
        # Converte objetos RowProxy/dict para dict simples (serializável)
        dados_serializaveis = []
        for cliente in resultados:
            dados_serializaveis.append({
                "cliente_id": cliente.get("cliente_id"),
                "nome": cliente.get("nome", ""),
                "segmento": cliente.get("segmento", ""),
                "rota_id": cliente.get("rota_id", ""),
                "vendedor_nome": cliente.get("vendedor_nome", ""),
                "vendedor_codigo": cliente.get("vendedor_codigo", ""),
                "supervisor_nome": cliente.get("supervisor_nome", ""),
                "supervisor_codigo": cliente.get("supervisor_codigo", ""),
                "data_ultima_compra": cliente.get("data_ultima_compra"),
                "dias_sem_compra": cliente.get("dias_sem_compra", 0) or 0,
            })
        
        # Exporta dados principais
        q1_dados_path = mock_data_dir / "q1_dados_dw.json"
        with open(q1_dados_path, "w", encoding="utf-8") as f:
            json.dump(dados_serializaveis, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Dados exportados para {q1_dados_path}")
        print(f"   Total de registros: {len(dados_serializaveis)}")
        
        # Exporta estatísticas
        estatisticas = {
            "total_clientes": total_clientes,
            "faixas": faixas,
            "data_exportacao": datetime.now().isoformat(),
            "dias_filtro": 60,
        }
        
        q1_estatisticas_path = mock_data_dir / "q1_estatisticas.json"
        with open(q1_estatisticas_path, "w", encoding="utf-8") as f:
            json.dump(estatisticas, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Estatísticas exportadas para {q1_estatisticas_path}")
        print(f"   Faixas: 61-120: {faixas['faixa_61_120']}, "
              f"121-180: {faixas['faixa_121_180']}, "
              f"181-300: {faixas['faixa_181_300']}, "
              f">300: {faixas['faixa_maior_300']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao exportar Q1: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        session.close()


if __name__ == "__main__":
    print("🚀 Exportando dados Q1 para modo mock...")
    print("=" * 60)
    
    sucesso = exportar_q1_para_json()
    
    print("=" * 60)
    if sucesso:
        print("✅ Exportação concluída com sucesso!")
        sys.exit(0)
    else:
        print("❌ Exportação falhou!")
        sys.exit(1)

