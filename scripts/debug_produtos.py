#!/usr/bin/env python3
"""
Script para debug de produtos - verificar dados no banco.
"""

import sys
from pathlib import Path

root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

import os
os.environ.setdefault("DB_TYPE", "sqlite")

from src.dw.connection import get_db_session, init_db
from src.dw.models import Venda
from sqlalchemy import func

def main():
    init_db()
    session_gen = get_db_session()
    session = next(session_gen)
    
    try:
        # Verifica data máxima
        data_max = session.query(func.max(Venda.data_venda)).scalar()
        print(f"Data máxima de venda: {data_max}")
        
        # Conta total de vendas
        total_vendas = session.query(func.count(Venda.id)).scalar()
        print(f"Total de vendas no banco: {total_vendas}")
        
        # Conta vendas com produtos válidos
        vendas_com_produto = session.query(func.count(Venda.id)).filter(
            Venda.codigo_produto.isnot(None),
            Venda.desc_produto.isnot(None)
        ).scalar()
        print(f"Vendas com código e descrição de produto: {vendas_com_produto}")
        
        # Mostra algumas datas de exemplo
        vendas_sample = session.query(Venda.data_venda).distinct().order_by(Venda.data_venda.desc()).limit(10).all()
        print(f"\nÚltimas 10 datas distintas de venda:")
        for v in vendas_sample:
            print(f"  - {v[0]}")
        
        # Se houver data máxima, verifica quantas vendas nos últimos 90 dias
        if data_max:
            from datetime import timedelta
            data_inicio = data_max - timedelta(days=90)
            vendas_90d = session.query(func.count(Venda.id)).filter(
                Venda.data_venda.between(data_inicio, data_max)
            ).scalar()
            print(f"\nVendas nos últimos 90 dias (de {data_inicio} a {data_max}): {vendas_90d}")
            
            # Vendas com produtos válidos nos últimos 90 dias
            vendas_90d_com_produto = session.query(func.count(Venda.id)).filter(
                Venda.data_venda.between(data_inicio, data_max),
                Venda.codigo_produto.isnot(None),
                Venda.desc_produto.isnot(None)
            ).scalar()
            print(f"Vendas com produtos válidos nos últimos 90 dias: {vendas_90d_com_produto}")
            
            # Mostra alguns produtos únicos no período
            produtos_sample = session.query(
                Venda.codigo_produto,
                Venda.desc_produto,
                func.count(Venda.id).label('qtd_vendas')
            ).filter(
                Venda.data_venda.between(data_inicio, data_max),
                Venda.codigo_produto.isnot(None),
                Venda.desc_produto.isnot(None)
            ).group_by(Venda.codigo_produto, Venda.desc_produto).limit(5).all()
            
            if produtos_sample:
                print(f"\nPrimeiros 5 produtos únicos no período:")
                for cod, desc, qtd in produtos_sample:
                    print(f"  - {cod} | {desc[:40]} | {qtd} vendas")
        
    except Exception as e:
        print(f"Erro: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    main()





