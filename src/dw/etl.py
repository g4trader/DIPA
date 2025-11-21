"""
ETL para Data Warehouse.

Este módulo contém funções para carregar dados processados no data warehouse.
"""

import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import Optional, Dict, List
import logging
from pathlib import Path

from src.config import config
from src.dw.connection import get_db_engine, init_db, get_db_session
from src.dw.models import (
    Cliente, Vendedor, Supervisor, Venda,
    MetaVendedor, MetaDepartamento
)

logger = logging.getLogger(__name__)


def load_data_to_dw(
    table_name: str,
    df: pd.DataFrame,
    if_exists: str = "replace",
    index: bool = False
):
    """
    Carrega dados de um DataFrame no data warehouse.
    
    Args:
        table_name: Nome da tabela de destino
        df: DataFrame com os dados
        if_exists: Comportamento se a tabela já existir ('replace', 'append', 'fail')
        index: Se True, inclui o index do DataFrame
    """
    try:
        engine = get_db_engine()
        
        logger.info(f"Carregando {len(df)} linhas na tabela {table_name}")
        
        df.to_sql(
            table_name,
            engine,
            if_exists=if_exists,
            index=index,
            method="multi",
            chunksize=1000
        )
        
        logger.info(f"Dados carregados com sucesso na tabela {table_name}")
    
    except Exception as e:
        logger.error(f"Erro ao carregar dados na tabela {table_name}: {str(e)}")
        raise


def load_clientes(df: pd.DataFrame):
    """
    Carrega dados de clientes no data warehouse.
    
    Args:
        df: DataFrame com dados de clientes
    """
    # Mapeia colunas do DataFrame para o modelo
    # Ajuste conforme necessário baseado na estrutura dos seus dados
    clientes_data = []
    
    for _, row in df.iterrows():
        cliente = {
            "codigo": str(row.get("codigo", row.get("id", ""))),
            "nome": str(row.get("nome", "")),
            "email": row.get("email"),
            "telefone": row.get("telefone"),
            "cidade": row.get("cidade"),
            "estado": row.get("estado"),
            "ativo": row.get("ativo", True),
            "data_cadastro": row.get("data_cadastro"),
        }
        clientes_data.append(cliente)
    
    df_clientes = pd.DataFrame(clientes_data)
    load_data_to_dw("clientes", df_clientes, if_exists="replace")


def load_vendedores(df: pd.DataFrame):
    """
    Carrega dados de vendedores no data warehouse.
    
    Args:
        df: DataFrame com dados de vendedores
    """
    vendedores_data = []
    
    for _, row in df.iterrows():
        vendedor = {
            "codigo": str(row.get("codigo", row.get("id", ""))),
            "nome": str(row.get("nome", "")),
            "email": row.get("email"),
            "supervisor_id": row.get("supervisor_id"),
            "ativo": row.get("ativo", True),
        }
        vendedores_data.append(vendedor)
    
    df_vendedores = pd.DataFrame(vendedores_data)
    load_data_to_dw("vendedores", df_vendedores, if_exists="replace")


def load_vendas(df: pd.DataFrame):
    """
    Carrega dados de vendas no data warehouse.
    
    Args:
        df: DataFrame com dados de vendas
    """
    vendas_data = []
    
    for _, row in df.iterrows():
        venda = {
            "cliente_id": row.get("cliente_id"),
            "vendedor_id": row.get("vendedor_id"),
            "data_venda": row.get("data_venda"),
            "valor": float(row.get("valor", 0)),
            "quantidade": row.get("quantidade"),
            "produto": row.get("produto"),
        }
        vendas_data.append(venda)
    
    df_vendas = pd.DataFrame(vendas_data)
    load_data_to_dw("vendas", df_vendas, if_exists="replace")


def load_metas_vendedor(df: pd.DataFrame):
    """
    Carrega dados de metas de vendedor no data warehouse.
    
    Args:
        df: DataFrame com dados de metas de vendedor
    """
    metas_data = []
    
    for _, row in df.iterrows():
        meta = {
            "vendedor_id": row.get("vendedor_id"),
            "ano": int(row.get("ano", 2024)),
            "mes": int(row.get("mes", 1)),
            "meta_valor": float(row.get("meta_valor", 0)),
            "realizado_valor": float(row.get("realizado_valor", 0)),
            "percentual_atingido": row.get("percentual_atingido"),
        }
        metas_data.append(meta)
    
    df_metas = pd.DataFrame(metas_data)
    load_data_to_dw("metas_vendedor", df_metas, if_exists="replace")


def update_percentual_atingido():
    """
    Atualiza o percentual de meta atingida para todos os registros.
    """
    try:
        engine = get_db_engine()
        
        # Atualiza metas de vendedor
        query = text("""
            UPDATE metas_vendedor
            SET percentual_atingido = 
                CASE 
                    WHEN meta_valor > 0 THEN (realizado_valor / meta_valor) * 100
                    ELSE 0
                END
        """)
        
        with engine.connect() as conn:
            conn.execute(query)
            conn.commit()
        
        logger.info("Percentual de meta atingida atualizado")
    
    except Exception as e:
        logger.error(f"Erro ao atualizar percentual de meta: {str(e)}")
        raise


def load_supervisores_e_vendedores_from_csv(csv_path: str, session: Session):
    """
    Carrega supervisores e vendedores a partir do CSV "Supervisor pasta 1.xlsx - Sheet1.csv".
    
    REGRAS DO PM:
    1. TABELA SUPERVISOR:
       - supervisor.nome = coluna "Supervisor"
       - supervisor.gerente = coluna "Gerente"
       - Cada linha com Supervisor não vazio deve gerar um supervisor
    
    2. TABELA VENDEDOR:
       - vendedor.codigo = coluna "Código Vendedor" (int, convertido para string)
       - vendedor.nome = coluna "Vendedor" (rota, ex.: "ROTA 301")
       - vendedor.supervisor_id = FK para Supervisor onde Supervisor.nome == "Supervisor"
       - vendedor.pasta = coluna "Pastas" (opcional, armazenado em Cliente.pasta se necessário)
       - Não gerar vendedores sem "Código Vendedor"
    
    Args:
        csv_path: Caminho para o arquivo CSV
        session: Sessão SQLAlchemy
    """
    logger.info(f"Carregando supervisores e vendedores de {csv_path}")
    
    try:
        df = pd.read_csv(csv_path, encoding='utf-8')
        
        # Remove linhas completamente vazias
        df = df.dropna(how='all')
        
        # Dicionário para armazenar supervisores por nome (chave única)
        supervisores_map = {}
        vendedores_created = 0
        vendedores_updated = 0
        supervisores_created = 0
        
        # Variáveis para rastrear supervisor atual (preenchimento forward)
        current_gerente = None
        current_supervisor_nome = None
        current_pasta = None
        
        for idx, row in df.iterrows():
            # REGRA PM: Preenche supervisor atual se houver (forward fill)
            gerente = row.get('Gerente')
            supervisor_nome = row.get('Supervisor')
            pasta = row.get('Pastas')
            
            if pd.notna(gerente) and str(gerente).strip():
                current_gerente = str(gerente).strip()
            if pd.notna(supervisor_nome) and str(supervisor_nome).strip():
                current_supervisor_nome = str(supervisor_nome).strip()
            if pd.notna(pasta) and str(pasta).strip():
                current_pasta = str(pasta).strip()
            
            # REGRA PM: Cada linha com Supervisor não vazio deve gerar um supervisor
            if current_supervisor_nome and current_supervisor_nome not in supervisores_map:
                # Busca supervisor existente por nome
                supervisor = session.query(Supervisor).filter(
                    Supervisor.nome == current_supervisor_nome
                ).first()
                
                if not supervisor:
                    # Cria novo supervisor
                    supervisor = Supervisor(
                        codigo=current_supervisor_nome.upper().replace(' ', '_').replace('/', '_'),
                        nome=current_supervisor_nome,
                        gerente=current_gerente,
                        pasta=current_pasta,
                        ativo=True
                    )
                    session.add(supervisor)
                    session.flush()  # Para obter o ID
                    supervisores_created += 1
                    logger.debug(f"Supervisor criado: nome={supervisor.nome}, gerente={supervisor.gerente}")
                else:
                    # Atualiza supervisor existente
                    updated = False
                    if supervisor.gerente != current_gerente and current_gerente:
                        supervisor.gerente = current_gerente
                        updated = True
                    if supervisor.pasta != current_pasta and current_pasta:
                        supervisor.pasta = current_pasta
                        updated = True
                    if updated:
                        logger.debug(f"Supervisor atualizado: nome={supervisor.nome}")
                
                supervisores_map[current_supervisor_nome] = supervisor
            
            # REGRA PM: Não gerar vendedores sem "Código Vendedor"
            codigo_vendedor = row.get('Código Vendedor')
            if pd.isna(codigo_vendedor):
                continue
            
            try:
                codigo_vendedor_int = int(float(codigo_vendedor))
                codigo_vendedor_str = str(codigo_vendedor_int)  # Converte para string (modelo usa String)
            except (ValueError, TypeError):
                logger.warning(f"Linha {idx}: Código Vendedor inválido: {codigo_vendedor}")
                continue
            
            # REGRA PM: vendedor.nome = coluna "Vendedor" (rota)
            vendedor_rota = row.get('Vendedor')
            if pd.isna(vendedor_rota):
                vendedor_rota = f"ROTA {codigo_vendedor_int}"
            else:
                vendedor_rota = str(vendedor_rota).strip()
            
            # REGRA PM: vendedor.supervisor_id = FK para Supervisor onde Supervisor.nome == "Supervisor"
            supervisor_id = None
            if current_supervisor_nome and current_supervisor_nome in supervisores_map:
                supervisor_id = supervisores_map[current_supervisor_nome].id
            
            # REGRA PM: vendedor.codigo = coluna "Código Vendedor" (int, como string)
            # Busca vendedor por código numérico
            vendedor = session.query(Vendedor).filter(
                Vendedor.codigo == codigo_vendedor_str
            ).first()
            
            if not vendedor:
                # Cria novo vendedor
                vendedor = Vendedor(
                    codigo=codigo_vendedor_str,  # Código numérico como string
                    nome=vendedor_rota,  # Rota (ex.: "ROTA 301")
                    supervisor_id=supervisor_id,
                    ativo=True
                )
                session.add(vendedor)
                vendedores_created += 1
                logger.debug(f"Vendedor criado: codigo={codigo_vendedor_str}, nome={vendedor_rota}, supervisor_id={supervisor_id}")
            else:
                # Atualiza vendedor existente
                updated = False
                if vendedor.nome != vendedor_rota:
                    vendedor.nome = vendedor_rota
                    updated = True
                if vendedor.supervisor_id != supervisor_id:
                    vendedor.supervisor_id = supervisor_id
                    updated = True
                if updated:
                    vendedores_updated += 1
                    logger.debug(f"Vendedor atualizado: codigo={codigo_vendedor_str}")
        
        session.commit()
        logger.info(f"✅ Supervisores e vendedores processados: {supervisores_created} supervisores criados, "
                   f"{vendedores_created} vendedores criados, {vendedores_updated} vendedores atualizados")
        
    except Exception as e:
        session.rollback()
        logger.error(f"Erro ao processar supervisores e vendedores: {str(e)}")
        raise


def enrich_clientes_from_csv(csv_path: str, session: Session):
    """
    Enriquece clientes a partir do CSV "Clientes ativos.xls - Clientes ativos.csv".
    
    REGRAS DO PM:
    - cliente.vendedor_codigo = valor numérico "Vendedor 1"
    - procurar vendedor onde vendedor.codigo == cliente.vendedor_codigo
    - se encontrar:
        cliente.rota_rca = vendedor.nome (rota, ex.: "ROTA 301")
        cliente.supervisor_id = vendedor.supervisor_id
    - se não encontrar:
        cliente.rota_rca = NULL
        cliente.supervisor_id = NULL
    
    REGRA CRÍTICA: A coluna "Nome RCA" NÃO pode ser usada como único identificador de rota.
    
    Args:
        csv_path: Caminho para o arquivo CSV
        session: Sessão SQLAlchemy
    """
    logger.info(f"Enriquecendo clientes de {csv_path}")
    
    try:
        df = pd.read_csv(csv_path, encoding='utf-8', low_memory=False)
        
        # Remove linhas completamente vazias
        df = df.dropna(how='all')
        
        if 'Vendedor 1' not in df.columns:
            logger.warning("Coluna 'Vendedor 1' não encontrada no CSV")
            return
        
        if 'Código' not in df.columns:
            logger.warning("Coluna 'Código' não encontrada no CSV")
            return
        
        clientes_atualizados = 0
        clientes_sem_vendedor = 0
        
        # REGRA PM: Criar cache de vendedores por código numérico (vendedor.codigo == "Código Vendedor")
        vendedores_cache = {}
        vendedores_db = session.query(Vendedor).all()
        for v in vendedores_db:
            # vendedor.codigo é o código numérico (string)
            if v.codigo:
                vendedores_cache[v.codigo] = v
        
        for idx, row in df.iterrows():
            codigo_cliente = row.get('Código')
            if pd.isna(codigo_cliente):
                continue
            
            codigo_cliente_str = str(codigo_cliente).strip()
            
            # Verifica se coluna vendedor_id existe ANTES de buscar cliente
            from sqlalchemy import inspect as sqlalchemy_inspect
            inspector = sqlalchemy_inspect(session.bind)
            columns = [col['name'] for col in inspector.get_columns('clientes')]
            has_vendedor_id_col = 'vendedor_id' in columns
            
            # Busca cliente no banco
            if not has_vendedor_id_col:
                # Se coluna não existe, busca via SQL direto para evitar erro
                result = session.execute(
                    text("SELECT id, codigo, rota_rca, supervisor_id FROM clientes WHERE codigo = :codigo LIMIT 1"),
                    {"codigo": codigo_cliente_str}
                ).first()
                
                if not result:
                    logger.debug(f"Cliente não encontrado: {codigo_cliente_str}")
                    continue
                
                # Cria objeto simples com os dados
                cliente_data = {
                    "id": result[0],
                    "codigo": result[1],
                    "rota_rca": result[2],
                    "supervisor_id": result[3]
                }
                cliente = None  # Não usa objeto ORM
            else:
                # Coluna existe, usa ORM normalmente
                cliente = session.query(Cliente).filter(
                    Cliente.codigo == codigo_cliente_str
                ).first()
                
                if not cliente:
                    logger.debug(f"Cliente não encontrado: {codigo_cliente_str}")
                    continue
                cliente_data = None
            
            # Lê Vendedor 1
            vendedor_1 = row.get('Vendedor 1')
            if pd.isna(vendedor_1):
                continue
            
            try:
                vendedor_1_int = int(float(vendedor_1))
                vendedor_1_str = str(vendedor_1_int)
            except (ValueError, TypeError):
                logger.debug(f"Cliente {codigo_cliente_str}: Vendedor 1 inválido: {vendedor_1}")
                clientes_sem_vendedor += 1
                continue
            
            # REGRA PM: procurar vendedor onde vendedor.codigo == cliente.vendedor_codigo
            vendedor = vendedores_cache.get(vendedor_1_str)
            
            if vendedor:
                # REGRA PM: se encontrar, preenche rota_rca e supervisor_id
                try:
                    cliente_id = cliente.id if cliente else cliente_data["id"]
                    
                    # Sempre usa UPDATE direto via SQL para evitar problemas com colunas inexistentes
                    result = session.execute(
                        text("""
                            UPDATE clientes 
                            SET rota_rca = :rota_rca, supervisor_id = :supervisor_id 
                            WHERE id = :cliente_id
                              AND (rota_rca IS NULL OR rota_rca != :rota_rca OR supervisor_id IS NULL OR supervisor_id != :supervisor_id)
                        """),
                        {
                            "rota_rca": vendedor.nome,
                            "supervisor_id": vendedor.supervisor_id,
                            "cliente_id": cliente_id
                        }
                    )
                    
                    if result.rowcount > 0:
                        session.commit()
                        clientes_atualizados += 1
                        logger.debug(f"Cliente {codigo_cliente_str} atualizado: rota_rca={vendedor.nome}, "
                                   f"supervisor_id={vendedor.supervisor_id}")
                except Exception as e:
                    logger.error(f"Erro ao atualizar cliente {codigo_cliente_str}: {str(e)}")
                    session.rollback()
                    continue
            else:
                # REGRA PM: se não encontrar, rota_rca = NULL e supervisor_id = NULL
                # Usa UPDATE direto via SQL para evitar problemas com colunas inexistentes
                try:
                    cliente_id = cliente.id if cliente else cliente_data["id"]
                    
                    result = session.execute(
                        text("""
                            UPDATE clientes 
                            SET rota_rca = NULL, supervisor_id = NULL 
                            WHERE id = :cliente_id
                              AND (rota_rca IS NOT NULL OR supervisor_id IS NOT NULL)
                        """),
                        {"cliente_id": cliente_id}
                    )
                    
                    if result.rowcount > 0:
                        session.commit()
                        clientes_atualizados += 1
                
                    clientes_sem_vendedor += 1
                    logger.debug(f"Cliente {codigo_cliente_str}: Vendedor {vendedor_1_str} não encontrado - campos limpos")
                except Exception as e:
                    logger.error(f"Erro ao limpar campos do cliente {codigo_cliente_str}: {str(e)}")
                    session.rollback()
                    clientes_sem_vendedor += 1
                    continue
        
        session.commit()
        logger.info(f"✅ Clientes enriquecidos: {clientes_atualizados} atualizados, "
                   f"{clientes_sem_vendedor} sem vendedor correspondente")
        
    except Exception as e:
        session.rollback()
        logger.error(f"Erro ao enriquecer clientes: {str(e)}")
        raise


def process_supervisores_vendedores_clientes(
    supervisor_csv_path: Optional[str] = None,
    clientes_csv_path: Optional[str] = None
):
    """
    Processa supervisores, vendedores e enriquece clientes a partir dos CSVs.
    
    Args:
        supervisor_csv_path: Caminho para "Supervisor pasta 1.xlsx - Sheet1.csv"
        clientes_csv_path: Caminho para "Clientes ativos.xls - Clientes ativos.csv"
    """
    logger.info("=" * 80)
    logger.info("PROCESSANDO SUPERVISORES, VENDEDORES E CLIENTES")
    logger.info("=" * 80)
    
    # Usa caminhos padrão se não fornecidos
    if supervisor_csv_path is None:
        supervisor_csv_path = config.paths.root_dir / "data_raw" / "Supervisor pasta 1.xlsx - Sheet1.csv"
    if clientes_csv_path is None:
        clientes_csv_path = config.paths.root_dir / "data_raw" / "Clientes ativos.xls - Clientes ativos.csv"
    
    # Converte para Path se necessário
    supervisor_csv_path = Path(supervisor_csv_path)
    clientes_csv_path = Path(clientes_csv_path)
    
    # Inicializa banco
    init_db()
    
    # Usa get_db_session que é um generator
    session_gen = get_db_session()
    session = next(session_gen)
    
    try:
        # 1. Processa supervisores e vendedores
        if supervisor_csv_path.exists():
            load_supervisores_e_vendedores_from_csv(str(supervisor_csv_path), session)
        else:
            logger.warning(f"Arquivo não encontrado: {supervisor_csv_path}")
        
        # 2. Enriquece clientes
        if clientes_csv_path.exists():
            enrich_clientes_from_csv(str(clientes_csv_path), session)
        else:
            logger.warning(f"Arquivo não encontrado: {clientes_csv_path}")
        
        logger.info("=" * 80)
        logger.info("PROCESSAMENTO CONCLUÍDO")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"Erro durante processamento: {str(e)}")
        raise
    finally:
        try:
            session.close()
        except:
            pass
        try:
            next(session_gen, None)
        except:
            pass





