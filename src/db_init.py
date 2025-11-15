#!/usr/bin/env python3
"""
Script para inicializar o banco de dados.

Este script:
1. Cria todas as tabelas definidas nos modelos SQLAlchemy
2. Cria índices adicionais se necessário
3. Popula a tabela dim_tempo se necessário
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import logging

# Adiciona o diretório raiz ao path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from src.config import config
from src.dw.connection import init_db, create_tables, get_db_engine, Base
from src.dw.models import DimTempo
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def populate_dim_tempo(start_year: int = 2020, end_year: int = 2030):
    """
    Popula a tabela dim_tempo com dados de um período.
    
    Args:
        start_year: Ano inicial
        end_year: Ano final
    """
    try:
        engine = get_db_engine()
        
        logger.info(f"Populando dim_tempo de {start_year} a {end_year}...")
        
        # Verifica se já existe dados
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM dim_tempo"))
            count = result.scalar()
            
            if count > 0:
                logger.info(f"dim_tempo já possui {count} registros. Pulando população.")
                return
        
        # Gera datas
        start_date = datetime(start_year, 1, 1)
        end_date = datetime(end_year, 12, 31)
        
        current_date = start_date
        records = []
        
        meses_nomes = [
            "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
            "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
        ]
        
        dias_semana_nomes = [
            "Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira",
            "Sexta-feira", "Sábado", "Domingo"
        ]
        
        while current_date <= end_date:
            ano = current_date.year
            mes = current_date.month
            dia = current_date.day
            trimestre = (mes - 1) // 3 + 1
            semestre = 1 if mes <= 6 else 2
            dia_semana = current_date.weekday() + 1  # 1=Segunda, 7=Domingo
            nome_dia_semana = dias_semana_nomes[current_date.weekday()]
            nome_mes = meses_nomes[mes - 1]
            mes_ano = f"{ano}-{mes:02d}"
            bimestre = (mes - 1) // 2 + 1
            
            records.append({
                "data": current_date.date(),
                "ano": ano,
                "mes": mes,
                "dia": dia,
                "trimestre": trimestre,
                "semestre": semestre,
                "dia_semana": dia_semana,
                "nome_dia_semana": nome_dia_semana,
                "nome_mes": nome_mes,
                "mes_ano": mes_ano,
                "bimestre": bimestre,
            })
            
            current_date += timedelta(days=1)
        
        # Insere registros em lote usando bulk_insert_mappings
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        
        try:
            # Insere em chunks de 1000
            chunk_size = 1000
            for i in range(0, len(records), chunk_size):
                chunk = records[i:i + chunk_size]
                session.bulk_insert_mappings(DimTempo, chunk)
                session.commit()
                logger.info(f"Inseridos {min(i + chunk_size, len(records))}/{len(records)} registros")
        finally:
            session.close()
        
        logger.info(f"dim_tempo populada com {len(records)} registros")
    
    except Exception as e:
        logger.error(f"Erro ao popular dim_tempo: {str(e)}")
        raise


def create_additional_indexes():
    """
    Cria índices adicionais que podem não estar nos modelos.
    """
    try:
        engine = get_db_engine()
        
        logger.info("Criando índices adicionais...")
        
        indexes = [
            # Índices adicionais para vendas
            "CREATE INDEX IF NOT EXISTS idx_venda_cliente_data ON vendas(cliente_id, data_venda DESC)",
            "CREATE INDEX IF NOT EXISTS idx_venda_produto_data ON vendas(codigo_produto, data_venda DESC)",
            
            # Índices adicionais para metas
            "CREATE INDEX IF NOT EXISTS idx_meta_vendedor_percentual_desc ON metas_vendedor(percentual_atingido_valor DESC, ano DESC, mes DESC)",
            "CREATE INDEX IF NOT EXISTS idx_meta_departamento_percentual_desc ON metas_departamento(percentual_atingido_valor DESC, ano DESC, mes DESC)",
            
            # Índices para clientes
            "CREATE INDEX IF NOT EXISTS idx_cliente_cnpj_cpf ON clientes(cnpj_cpf) WHERE cnpj_cpf IS NOT NULL",
        ]
        
        with engine.connect() as conn:
            for index_sql in indexes:
                try:
                    conn.execute(text(index_sql))
                    conn.commit()
                except Exception as e:
                    logger.warning(f"Erro ao criar índice (pode já existir): {str(e)}")
        
        logger.info("Índices adicionais criados")
    
    except Exception as e:
        logger.error(f"Erro ao criar índices adicionais: {str(e)}")
        # Não falha se houver erro nos índices


def main():
    """Função principal."""
    print("=" * 60)
    print("Inicializando banco de dados")
    print("=" * 60)
    print()
    print(f"Tipo de banco: {config.database.db_type}")
    print(f"String de conexão: {config.database.connection_string[:50]}...")
    print()
    
    try:
        # Inicializa banco de dados
        logger.info("Inicializando conexão com banco de dados...")
        init_db()
        
        # Cria tabelas
        logger.info("Criando tabelas...")
        create_tables()
        logger.info("Tabelas criadas com sucesso!")
        
        print()
        
        # Popula dim_tempo
        response = input("Deseja popular a tabela dim_tempo? (s/n): ")
        if response.lower() == "s":
            start_year = int(input("Ano inicial (padrão: 2020): ") or "2020")
            end_year = int(input("Ano final (padrão: 2030): ") or "2030")
            populate_dim_tempo(start_year, end_year)
            print()
        
        # Cria índices adicionais
        response = input("Deseja criar índices adicionais? (s/n): ")
        if response.lower() == "s":
            create_additional_indexes()
            print()
        
        print("=" * 60)
        print("Banco de dados inicializado com sucesso!")
        print("=" * 60)
        print()
        print("Tabelas criadas:")
        print("  - dim_tempo")
        print("  - supervisores")
        print("  - vendedores")
        print("  - clientes")
        print("  - vendas")
        print("  - metas_vendedor")
        print("  - metas_departamento")
        print("  - meta_predictions")
        print("  - churn_risk")
        print()
    
    except Exception as e:
        logger.error(f"Erro ao inicializar banco de dados: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

