#!/usr/bin/env python3
"""Verifica campos de produto nas vendas."""

import sys
from pathlib import Path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

import os
os.environ.setdefault("DB_TYPE", "sqlite")

from src.dw.connection import get_db_session, init_db
from src.dw.models import Venda
from sqlalchemy import func, distinct

def main():
    init_db()
    session_gen = get_db_session()
    session = next(session_gen)
    
    try:
        # Verifica estrutura de uma venda exemplo
        venda_exemplo = session.query(Venda).first()
        if venda_exemplo:
            print("Campos de uma venda exemplo:")
            print(f"  codigo_produto: {venda_exemplo.codigo_produto}")
            print(f"  desc_produto: {venda_exemplo.desc_produto}")
            print(f"  departamento: {venda_exemplo.departamento}")
            print(f"  secao: {venda_exemplo.secao}")
            print(f"  data_venda: {venda_exemplo.data_venda}")
            print(f"  valor_total_liquido: {venda_exemplo.valor_total_liquido}")
            print()
        
        # Conta vendas com produtos não nulos
        print("Análise de campos de produto:")
        total = session.query(func.count(Venda.id)).scalar()
        
        com_codigo = session.query(func.count(Venda.id)).filter(Venda.codigo_produto.isnot(None)).scalar()
        com_desc = session.query(func.count(Venda.id)).filter(Venda.desc_produto.isnot(None)).scalar()
        com_departamento = session.query(func.count(Venda.id)).filter(Venda.departamento.isnot(None)).scalar()
        
        print(f"  Total vendas: {total:,}")
        print(f"  Com codigo_produto não NULL: {com_codigo:,}")
        print(f"  Com desc_produto não NULL: {com_desc:,}")
        print(f"  Com departamento não NULL: {com_departamento:,}")
        
        # Se não tiver codigo/desc, talvez usemos departamento como alternativa
        if com_departamento > 0:
            print("\nUsando departamento como identificador de produto:")
            produtos_depto = session.query(
                Venda.departamento,
                func.sum(Venda.qtd_unidades).label('unidades'),
                func.sum(Venda.qtd_caixas).label('caixas'),
                func.sum(Venda.valor_total_liquido).label('faturamento')
            ).filter(
                Venda.departamento.isnot(None)
            ).group_by(Venda.departamento).order_by('faturamento').limit(20).all()
            
            if produtos_depto:
                print(f"{'Departamento':<40} {'Unidades':<12} {'Caixas':<10} {'Faturamento':<15}")
                print("-" * 80)
                for depto, unidades, caixas, fat in produtos_depto:
                    print(f"{str(depto)[:38]:<40} {int(unidades) if unidades else 0:<12} {float(caixas) if caixas else 0:.1f:<10} R$ {float(fat):,.2f}")
        
    except Exception as e:
        print(f"Erro: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    main()





