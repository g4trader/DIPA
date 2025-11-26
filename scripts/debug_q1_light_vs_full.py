#!/usr/bin/env python3
"""
Script de debug para comparar Q1 full vs light.

Uso:
    python scripts/debug_q1_light_vs_full.py
"""

import sys
import os
from pathlib import Path

# Adiciona o diretório raiz ao path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from src.dw.database import SessionLocal
from src.dw.queries import get_clientes_sem_compra_ha_dias, get_clientes_sem_compra_ha_dias_light

def main():
    print("=" * 80)
    print("DEBUG: Comparando Q1 FULL vs LIGHT")
    print("=" * 80)
    print()
    
    session = SessionLocal()
    dias = 60
    
    try:
        print(f"🔍 Executando Q1 FULL (dias={dias})...")
        full = get_clientes_sem_compra_ha_dias(session, dias=dias)
        print(f"✅ FULL: {len(full)} registros")
        
        print()
        print(f"🔍 Executando Q1 LIGHT (dias={dias}, limit=100)...")
        light = get_clientes_sem_compra_ha_dias_light(session, dias=dias, limit=100)
        print(f"✅ LIGHT: {len(light)} registros")
        
        print()
        print("=" * 80)
        print("COMPARAÇÃO")
        print("=" * 80)
        
        if len(full) > 0 and len(light) > 0:
            # Mostrar alguns IDs para comparar
            full_ids = {r.get("cliente_id") for r in full[:20]}
            light_ids = {r.get("cliente_id") for r in light[:20]}
            
            print(f"FULL (primeiros 20 IDs): {sorted(list(full_ids))[:10]}...")
            print(f"LIGHT (primeiros 20 IDs): {sorted(list(light_ids))[:10]}...")
            print(f"Interseção (primeiros 20): {len(full_ids & light_ids)} IDs em comum")
            
            # Verificar se light é subconjunto de full
            all_full_ids = {r.get("cliente_id") for r in full}
            all_light_ids = {r.get("cliente_id") for r in light}
            is_subset = all_light_ids.issubset(all_full_ids)
            print(f"LIGHT é subconjunto de FULL: {is_subset}")
            
            if not is_subset:
                diff = all_light_ids - all_full_ids
                print(f"⚠️  IDs em LIGHT mas não em FULL: {len(diff)} IDs")
                if len(diff) > 0:
                    print(f"   Exemplos: {list(diff)[:5]}")
        else:
            print("⚠️  Não é possível comparar: uma das queries retornou zero registros")
            if len(full) == 0:
                print("   ❌ FULL retornou 0 registros")
            if len(light) == 0:
                print("   ❌ LIGHT retornou 0 registros")
        
        print()
        print("=" * 80)
        print("CRITÉRIOS DE ACEITAÇÃO")
        print("=" * 80)
        print(f"✅ FULL ≈ 932: {'✅' if 900 <= len(full) <= 1000 else '❌'} ({len(full)} registros)")
        print(f"✅ LIGHT > 0: {'✅' if len(light) > 0 else '❌'} ({len(light)} registros)")
        print(f"✅ LIGHT ≤ 100: {'✅' if len(light) <= 100 else '❌'} ({len(light)} registros)")
        
        if len(full) > 0 and len(light) > 0:
            all_full_ids = {r.get("cliente_id") for r in full}
            all_light_ids = {r.get("cliente_id") for r in light}
            is_subset = all_light_ids.issubset(all_full_ids)
            print(f"✅ LIGHT é subconjunto de FULL: {'✅' if is_subset else '❌'}")
        
    except Exception as e:
        print(f"❌ Erro ao executar queries: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    main()

