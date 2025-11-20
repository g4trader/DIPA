"""
Módulo para carregar DataFrames no banco de dados.

Este módulo contém funções para inserir dados processados nas tabelas
do data warehouse usando SQLAlchemy com inserts em batch.
"""

import pandas as pd
import logging
from typing import Optional, Dict, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from src.config import config
from src.dw import connection as dw_connection
from src.dw.connection import init_db, get_db_engine, get_db_session
from src.dw.models import (
    Cliente, Vendedor, Supervisor, Venda, MetaVendedor, MetaDepartamento,
    DimTempo
)
from datetime import datetime

logger = logging.getLogger(__name__)


def get_or_create_supervisor(
    session: Session,
    nome: str,
    pasta: Optional[str] = None,
    gerente: Optional[str] = None
) -> Supervisor:
    """
    Obtém ou cria um supervisor.
    
    Args:
        session: Sessão SQLAlchemy
        nome: Nome do supervisor
        pasta: Pasta do supervisor
        gerente: Gerente relacionado
        
    Returns:
        Supervisor: Supervisor encontrado ou criado
    """
    # Gera código baseado no nome
    codigo = nome.upper().replace(' ', '_')[:50]
    
    # Busca supervisor existente
    supervisor = session.query(Supervisor).filter(
        Supervisor.codigo == codigo
    ).first()
    
    if not supervisor:
        # Cria novo supervisor
        supervisor = Supervisor(
            codigo=codigo,
            nome=nome,
            pasta=pasta,
            gerente=gerente,
            ativo=True
        )
        session.add(supervisor)
        session.flush()  # Para obter o ID
        logger.debug(f"Supervisor criado: {nome}")
    
    return supervisor


def get_or_create_vendedor(
    session: Session,
    nome: str,
    codigo: str,  # ✅ CORREÇÃO: codigo agora é obrigatório (deve ser rota_rca)
    supervisor_id: Optional[int] = None,
    # ✅ CORREÇÃO: nome_rca e rota_rca removidos (não são mais campos do modelo)
) -> Vendedor:
    """
    Obtém ou cria um vendedor.
    
    Args:
        session: Sessão SQLAlchemy
        nome: Nome do vendedor (pode ser None)
        codigo: Código do vendedor (obrigatório, deve ser rota_rca para JOIN funcionar)
        supervisor_id: ID do supervisor
        
    Returns:
        Vendedor: Vendedor encontrado ou criado
    """
    # ✅ CORREÇÃO: codigo agora é obrigatório e deve ser a rota_rca
    if not codigo:
        raise ValueError("codigo é obrigatório (deve ser rota_rca para JOIN funcionar)")
    
    codigo_final = str(codigo).strip()
    
    # Busca vendedor existente pelo código
    vendedor = session.query(Vendedor).filter(
        Vendedor.codigo == codigo_final
    ).first()
    
    if not vendedor:
        # Cria novo vendedor
        # ✅ CORREÇÃO: codigo deve ser rota_rca para JOIN funcionar
        # ✅ CORREÇÃO: nome_rca e rota_rca foram removidos do modelo, apenas codigo e nome
        vendedor = Vendedor(
            codigo=codigo_final,  # Usa rota_rca como código (chave de JOIN)
            nome=nome if nome else None,  # Nome pode ser None se criado apenas pela rota
            supervisor_id=supervisor_id,
            ativo=True
        )
        session.add(vendedor)
        session.flush()
        logger.debug(f"Vendedor criado: codigo={codigo_final}, nome={nome}")
    else:
        # Atualiza vendedor existente se houver informações novas
        if nome and not vendedor.nome:
            vendedor.nome = nome
        if supervisor_id and not vendedor.supervisor_id:
            vendedor.supervisor_id = supervisor_id
        # ✅ CORREÇÃO: nome_rca e rota_rca foram removidos do modelo
        session.flush()
    
    return vendedor


def get_tempo_id(session: Session, data: datetime) -> Optional[int]:
    """
    Obtém ID da dimensão temporal para uma data.
    
    Args:
        session: Sessão SQLAlchemy
        data: Data
        
    Returns:
        int ou None: ID da dimensão temporal
    """
    if pd.isna(data):
        return None
    
    tempo = session.query(DimTempo).filter(
        DimTempo.data == data.date()
    ).first()
    
    return tempo.id if tempo else None


def load_clientes_to_db(df: pd.DataFrame, batch_size: int = 1000) -> int:
    """
    Carrega clientes do DataFrame para o banco de dados.
    
    Args:
        df: DataFrame com dados de clientes
        batch_size: Tamanho do batch para inserção
        
    Returns:
        int: Número de registros inseridos/atualizados
    """
    logger.info(f"Carregando {len(df)} clientes no banco de dados...")
    
    # Garante que o banco está inicializado
    if dw_connection.SessionLocal is None:
        init_db()
    
    session = dw_connection.SessionLocal()
    inserted = 0
    updated = 0
    
    try:
        # Mapeia colunas do DataFrame para o modelo
        for idx, row in df.iterrows():
            try:
                # ✅ CORREÇÃO: Mapeia 'Código' do CSV (com maiúscula) para codigo
                codigo = str(row.get('Código', row.get('codigo', row.get('id_cliente', ''))))
                if not codigo or codigo == 'nan' or codigo == 'None':
                    logger.warning(f"Cliente sem código na linha {idx}, pulando...")
                    continue
                
                # Busca cliente existente
                cliente = session.query(Cliente).filter(
                    Cliente.codigo == codigo
                ).first()
                
                # Prepara dados
                cliente_data = {
                    'codigo': codigo,
                    # ✅ CORREÇÃO: Mapeia 'CNPJ/CPF' do CSV
                    'cnpj_cpf': str(row.get('CNPJ/CPF', row.get('cnpj_cpf', ''))) if pd.notna(row.get('CNPJ/CPF', row.get('cnpj_cpf'))) else None,
                    # ✅ CORREÇÃO: Mapeia 'Fantasia' do CSV
                    'fantasia': str(row.get('Fantasia', row.get('fantasia', ''))) if pd.notna(row.get('Fantasia', row.get('fantasia'))) else None,
                    # ✅ CORREÇÃO: Mapeia 'Cliente' do CSV para nome
                    'nome': str(row.get('Cliente', row.get('cliente', row.get('nome', '')))),
                    # ✅ CORREÇÃO: Mapeia 'Estado' do CSV
                    'estado': str(row.get('Estado', row.get('estado', '')))[:2] if pd.notna(row.get('Estado', row.get('estado'))) else None,
                    # ✅ CORREÇÃO: Mapeia 'Município' do CSV
                    'municipio': str(row.get('Município', row.get('municipio', row.get('cidade', '')))) if pd.notna(row.get('Município', row.get('municipio', row.get('cidade')))) else None,
                    'regiao_administrativa': str(row.get('regiao_administrativa', '')) if pd.notna(row.get('regiao_administrativa')) else None,
                    'local_venda': str(row.get('local_venda', '')) if pd.notna(row.get('local_venda')) else None,
                    'segmento_venda': str(row.get('segmento_venda', '')) if pd.notna(row.get('segmento_venda')) else None,
                    'grupo_economico': str(row.get('grupo_economico', '')) if pd.notna(row.get('grupo_economico')) else None,
                    'supervisor_responsavel': str(row.get('supervisor_responsavel', '')) if pd.notna(row.get('supervisor_responsavel')) else None,
                    # ✅ CORREÇÃO: Mapeia 'Nome RCA' do CSV para 'rota_rca' do modelo
                    # O CSV tem 'Nome RCA' que contém valores como "ROTA 304", "ROTA 74 VD", etc.
                    'nome_rca': str(row.get('Nome RCA', row.get('nome_rca', ''))) if pd.notna(row.get('Nome RCA', row.get('nome_rca'))) else None,
                    'rota_rca': str(row.get('Nome RCA', row.get('rota_rca', ''))) if pd.notna(row.get('Nome RCA', row.get('rota_rca'))) else None,
                    'pasta': str(row.get('pasta', '')) if pd.notna(row.get('pasta')) else None,
                    'consumidor_final': bool(row.get('consumidor_final', False)),
                    'bloqueado': bool(row.get('bloqueio', row.get('bloqueado', False))),
                    'motivo_bloqueio': str(row.get('motivo_bloqueio', '')) if pd.notna(row.get('motivo_bloqueio')) else None,
                    'observacoes': str(row.get('observacoes_adicionais', row.get('observacoes', ''))) if pd.notna(row.get('observacoes_adicionais', row.get('observacoes'))) else None,
                    'ativo': True,
                }
                
                # Data de cadastro
                data_cadastro_cols = [col for col in df.columns if 'data' in col.lower() and 'cadastro' in col.lower()]
                if data_cadastro_cols and pd.notna(row.get(data_cadastro_cols[0])):
                    cliente_data['data_cadastro'] = row.get(data_cadastro_cols[0])
                
                # Supervisor ID (busca ou cria)
                supervisor_id = None
                if cliente_data['supervisor_responsavel']:
                    supervisor = get_or_create_supervisor(
                        session,
                        cliente_data['supervisor_responsavel'],
                        pasta=cliente_data.get('pasta')
                    )
                    cliente_data['supervisor_id'] = supervisor.id
                    supervisor_id = supervisor.id
                
                # Vendedor ID (cria vendedor a partir da rota_rca se existir)
                vendedor_id = None
                if cliente_data.get('rota_rca'):
                    rota_rca = str(cliente_data['rota_rca']).strip()
                    if rota_rca:
                        # Cria ou busca vendedor usando rota_rca como código
                        vendedor = get_or_create_vendedor(
                            session,
                            nome=cliente_data.get('nome_rca') or rota_rca,  # Usa nome_rca se disponível, senão usa rota
                            codigo=rota_rca,  # ✅ CORREÇÃO: usa rota_rca como código (chave de JOIN)
                            supervisor_id=supervisor_id
                        )
                        cliente_data['vendedor_id'] = vendedor.id
                        vendedor_id = vendedor.id
                
                if cliente:
                    # Atualiza cliente existente
                    for key, value in cliente_data.items():
                        setattr(cliente, key, value)
                    updated += 1
                else:
                    # Cria novo cliente
                    cliente = Cliente(**cliente_data)
                    session.add(cliente)
                    inserted += 1
                
                # Commit em batches
                if (inserted + updated) % batch_size == 0:
                    session.commit()
                    logger.debug(f"Commit batch: {inserted + updated} registros processados")
            
            except Exception as e:
                logger.error(f"Erro ao processar cliente na linha {idx}: {str(e)}")
                session.rollback()
                continue
        
        # Commit final
        session.commit()
        logger.info(f"Clientes carregados: {inserted} inseridos, {updated} atualizados")
        
        return inserted + updated
    
    except Exception as e:
        session.rollback()
        logger.error(f"Erro ao carregar clientes: {str(e)}")
        raise
    finally:
        session.close()


def load_vendas_to_db(df: pd.DataFrame, batch_size: int = 1000) -> int:
    """
    Carrega vendas do DataFrame para o banco de dados.
    
    Args:
        df: DataFrame com dados de vendas
        batch_size: Tamanho do batch para inserção
        
    Returns:
        int: Número de registros inseridos
    """
    logger.info(f"Carregando {len(df)} vendas no banco de dados...")
    
    # Garante que o banco está inicializado
    if dw_connection.SessionLocal is None:
        init_db()
    
    session = dw_connection.SessionLocal()
    inserted = 0
    
    try:
        for idx, row in df.iterrows():
            try:
                # Busca cliente
                codigo_cliente = str(row.get('codigo_cliente', ''))
                if not codigo_cliente or codigo_cliente == 'nan':
                    logger.warning(f"Venda sem código de cliente na linha {idx}, pulando...")
                    continue
                
                cliente = session.query(Cliente).filter(
                    Cliente.codigo == codigo_cliente
                ).first()
                
                if not cliente:
                    logger.warning(f"Cliente não encontrado: {codigo_cliente}, pulando venda...")
                    continue
                
                # ✅ CORREÇÃO: Busca ou cria vendedor usando rota_rca do cliente como código
                # Prioriza rota_rca do cliente para garantir JOIN correto
                rota_rca_cliente = cliente.rota_rca if cliente.rota_rca else None
                vendedor_nome = str(row.get('vendedor', '')) if pd.notna(row.get('vendedor')) else None
                
                supervisor_nome = str(row.get('supervisor', '')) if pd.notna(row.get('supervisor')) else None
                supervisor_id = None
                
                if supervisor_nome:
                    supervisor = get_or_create_supervisor(session, supervisor_nome)
                    supervisor_id = supervisor.id
                
                # ✅ CORREÇÃO: Usa rota_rca como código (chave de JOIN), não o nome
                if rota_rca_cliente:
                    # Se cliente tem rota_rca, usa como código do vendedor
                    vendedor = get_or_create_vendedor(
                        session,
                        nome=vendedor_nome or rota_rca_cliente,  # Nome do vendedor ou rota como fallback
                        codigo=rota_rca_cliente,  # ✅ CORREÇÃO: usa rota_rca como código
                        supervisor_id=supervisor_id
                    )
                elif vendedor_nome:
                    # Fallback: se não houver rota_rca, cria com nome (mas não ideal)
                    logger.warning(f"Cliente {codigo_cliente} sem rota_rca, criando vendedor com nome: {vendedor_nome}")
                    vendedor = get_or_create_vendedor(
                        session,
                        nome=vendedor_nome,
                        codigo=vendedor_nome,  # Fallback menos ideal
                        supervisor_id=supervisor_id
                    )
                else:
                    logger.warning(f"Venda sem vendedor e cliente sem rota_rca na linha {idx}, pulando...")
                    continue
                
                # Data da venda
                data_venda = row.get('data_venda')
                if pd.isna(data_venda):
                    logger.warning(f"Venda sem data na linha {idx}, pulando...")
                    continue
                
                # Prepara dados da venda
                venda_data = {
                    'data_venda': data_venda.date() if isinstance(data_venda, datetime) else data_venda,
                    'cliente_id': cliente.id,
                    'vendedor_id': vendedor.id,
                    'gerente': str(row.get('gerente', '')) if pd.notna(row.get('gerente')) else None,
                    'supervisor_id': supervisor_id,
                    'supervisor_nome': supervisor_nome,
                    'vendedor_nome': vendedor_nome,
                    'numero_nf': str(row.get('numero_nf', '')) if pd.notna(row.get('numero_nf')) else None,
                    'codigo_cliente': codigo_cliente,
                    'nome_cliente': str(row.get('nome_cliente', '')),
                    'cgc_cpf_cliente': str(row.get('cgc_cpf', row.get('cnpj_cpf', ''))) if pd.notna(row.get('cgc_cpf', row.get('cnpj_cpf'))) else None,
                    'ramo_atividade': str(row.get('ramo_de_atividade', '')) if pd.notna(row.get('ramo_de_atividade')) else None,
                    'cidade_cliente': str(row.get('cidade', '')) if pd.notna(row.get('cidade')) else None,
                    'codigo_produto': str(row.get('codigo_produto', '')) if pd.notna(row.get('codigo_produto')) else None,
                    'desc_produto': str(row.get('desc_produto', '')) if pd.notna(row.get('desc_produto')) else None,
                    'departamento': str(row.get('departamento', '')) if pd.notna(row.get('departamento')) else None,
                    'secao': str(row.get('secao', '')) if pd.notna(row.get('secao')) else None,
                    'valor_total_liquido': float(row.get('valor_total_liquido', 0)),
                    'valor_desconto': float(row.get('valor_desconto', row.get('vlr_desconto', 0))),
                    'qtd_caixas': int(row.get('qtd_caixas', 0)) if pd.notna(row.get('qtd_caixas')) else None,
                    'qtd_unidades': int(row.get('qtd_unidades', 0)) if pd.notna(row.get('qtd_unidades')) else None,
                    'qtd_unidades_bonificacao': int(row.get('qtd_unidades_bonificacao', 0)) if pd.notna(row.get('qtd_unidades_bonificacao')) else None,
                    'qtd_un_venda_liquida': int(row.get('qtd_un_venda_liquida', 0)) if pd.notna(row.get('qtd_un_venda_liquida')) else None,
                }
                
                # Busca tempo_id
                if data_venda:
                    tempo_id = get_tempo_id(session, data_venda)
                    if tempo_id:
                        venda_data['tempo_id'] = tempo_id
                
                # Cria venda
                venda = Venda(**venda_data)
                session.add(venda)
                inserted += 1
                
                # Commit em batches
                if inserted % batch_size == 0:
                    session.commit()
                    logger.debug(f"Commit batch: {inserted} vendas processadas")
            
            except Exception as e:
                logger.error(f"Erro ao processar venda na linha {idx}: {str(e)}")
                session.rollback()
                continue
        
        # Commit final
        session.commit()
        logger.info(f"Vendas carregadas: {inserted} registros inseridos")
        
        return inserted
    
    except Exception as e:
        session.rollback()
        logger.error(f"Erro ao carregar vendas: {str(e)}")
        raise
    finally:
        session.close()


def load_metas_vendedor_to_db(df: pd.DataFrame, batch_size: int = 1000) -> int:
    """
    Carrega metas de vendedor do DataFrame para o banco de dados.
    
    Args:
        df: DataFrame com dados de metas de vendedor
        batch_size: Tamanho do batch para inserção
        
    Returns:
        int: Número de registros inseridos/atualizados
    """
    logger.info(f"Carregando {len(df)} metas de vendedor no banco de dados...")
    logger.debug(f"Shape do DataFrame recebido: {df.shape}")
    logger.debug(f"Colunas do DataFrame: {list(df.columns)}")
    
    # Garante que o banco está inicializado
    if dw_connection.SessionLocal is None:
        init_db()
    
    session = dw_connection.SessionLocal()
    inserted = 0
    updated = 0
    skipped = 0
    
    try:
        for idx, row in df.iterrows():
            try:
                # Busca vendedor
                vendedor_nome = str(row.get('vendedor_nome', row.get('vendedor', ''))).strip()
                if not vendedor_nome or vendedor_nome == 'nan' or vendedor_nome == '':
                    logger.warning(f"Meta sem vendedor na linha {idx}, pulando...")
                    skipped += 1
                    continue
                
                vendedor = get_or_create_vendedor(session, vendedor_nome, codigo=vendedor_nome)
                
                # Ano e mês
                ano = int(row.get('ano', 0))
                mes = int(row.get('mes', 0))
                mes_ano = str(row.get('mes_ano', f"{ano}-{mes:02d}"))
                
                if not ano or not mes:
                    logger.warning(f"Meta sem ano/mês na linha {idx} (ano={ano}, mes={mes}), pulando...")
                    skipped += 1
                    continue
                
                # Busca meta existente
                meta = session.query(MetaVendedor).filter(
                    MetaVendedor.vendedor_id == vendedor.id,
                    MetaVendedor.ano == ano,
                    MetaVendedor.mes == mes
                ).first()
                
                # Prepara dados
                meta_data = {
                    'vendedor_id': vendedor.id,
                    'vendedor_nome': vendedor_nome,
                    'ano': ano,
                    'mes': mes,
                    'mes_ano': mes_ano,
                    'valor_meta': float(row.get('meta_valor', 0)),
                    'valor_faturado': float(row.get('realizado_valor', 0)),
                    'valor_parado': float(row.get('valor_parado', 0)),
                    'valor_total': float(row.get('valor_total', row.get('realizado_valor', 0) + row.get('valor_parado', 0))),
                    'percentual_atingido_valor': float(row.get('perc_ating_valor', 0)),
                    'qtd_meta': int(row.get('meta_volume', 0)) if pd.notna(row.get('meta_volume')) else None,
                    'qtd_cx_faturado': int(row.get('realizado_volume', 0)) if pd.notna(row.get('realizado_volume')) else None,
                    'qtd_cx_paradas': int(row.get('qtd_cx_paradas', 0)) if pd.notna(row.get('qtd_cx_paradas')) else None,
                    'total_caixas': int(row.get('total_caixas', 0)) if pd.notna(row.get('total_caixas')) else None,
                    'percentual_atingido_volume': float(row.get('perc_ating_volume', 0)),
                    'meta_pos': int(row.get('meta_positivacao', 0)) if pd.notna(row.get('meta_positivacao')) else None,
                    'clientes_pos': int(row.get('clientes_positivados', 0)) if pd.notna(row.get('clientes_positivados')) else None,
                    'percentual_atingido_pos': float(row.get('perc_ating_positivacao', 0)),
                }
                
                if meta:
                    # Atualiza meta existente
                    for key, value in meta_data.items():
                        setattr(meta, key, value)
                    updated += 1
                else:
                    # Cria nova meta
                    meta = MetaVendedor(**meta_data)
                    session.add(meta)
                    inserted += 1
                
                # Commit em batches
                if (inserted + updated) % batch_size == 0:
                    session.commit()
                    logger.debug(f"Commit batch: {inserted + updated} metas processadas")
            
            except Exception as e:
                logger.error(f"Erro ao processar meta na linha {idx}: {str(e)}")
                import traceback
                logger.debug(traceback.format_exc())
                session.rollback()
                skipped += 1
                continue
        
        # Commit final
        session.commit()
        logger.info(f"Metas de vendedor carregadas: {inserted} inseridas, {updated} atualizadas, {skipped} puladas")
        logger.debug(f"Total de linhas processadas: {inserted + updated + skipped} de {len(df)}")
        
        return inserted + updated
    
    except Exception as e:
        session.rollback()
        logger.error(f"Erro ao carregar metas de vendedor: {str(e)}")
        raise
    finally:
        session.close()


def load_metas_departamento_to_db(df: pd.DataFrame, batch_size: int = 1000) -> int:
    """
    Carrega metas de departamento do DataFrame para o banco de dados.
    
    Args:
        df: DataFrame com dados de metas de departamento
        batch_size: Tamanho do batch para inserção
        
    Returns:
        int: Número de registros inseridos/atualizados
    """
    logger.info(f"Carregando {len(df)} metas de departamento no banco de dados...")
    logger.debug(f"Shape do DataFrame recebido: {df.shape}")
    logger.debug(f"Colunas do DataFrame: {list(df.columns)}")
    
    # Garante que o banco está inicializado
    if dw_connection.SessionLocal is None:
        init_db()
    
    session = dw_connection.SessionLocal()
    inserted = 0
    updated = 0
    skipped = 0
    
    try:
        for idx, row in df.iterrows():
            try:
                # Busca supervisor
                supervisor_nome = str(row.get('supervisor_nome', row.get('supervisor', row.get('departamento', '')))).strip()
                if not supervisor_nome or supervisor_nome == 'nan' or supervisor_nome == '':
                    logger.warning(f"Meta sem supervisor/departamento na linha {idx}, pulando...")
                    skipped += 1
                    continue
                
                supervisor = get_or_create_supervisor(session, supervisor_nome)
                
                # Ano e mês
                ano = int(row.get('ano', 0))
                mes = int(row.get('mes', 0))
                mes_ano = str(row.get('mes_ano', f"{ano}-{mes:02d}"))
                
                if not ano or not mes:
                    logger.warning(f"Meta sem ano/mês na linha {idx} (ano={ano}, mes={mes}), pulando...")
                    skipped += 1
                    continue
                
                # Busca meta existente
                meta = session.query(MetaDepartamento).filter(
                    MetaDepartamento.supervisor_id == supervisor.id,
                    MetaDepartamento.ano == ano,
                    MetaDepartamento.mes == mes
                ).first()
                
                # Prepara dados
                meta_data = {
                    'supervisor_id': supervisor.id,
                    'supervisor_nome': supervisor_nome,
                    'departamento': str(row.get('departamento', '')).strip() if pd.notna(row.get('departamento')) and str(row.get('departamento')).strip() != '' else None,
                    'ano': ano,
                    'mes': mes,
                    'mes_ano': mes_ano,
                    'valor_meta': float(row.get('meta_valor', 0)),
                    'valor_faturado': float(row.get('realizado_valor', 0)),
                    'valor_parado': float(row.get('valor_parado', 0)),
                    'valor_total': float(row.get('valor_total', row.get('realizado_valor', 0) + row.get('valor_parado', 0))),
                    'percentual_atingido_valor': float(row.get('perc_ating_valor', 0)),
                    'qtd_meta': int(row.get('meta_volume', 0)) if pd.notna(row.get('meta_volume')) else None,
                    'qtd_cx_faturado': int(row.get('realizado_volume', 0)) if pd.notna(row.get('realizado_volume')) else None,
                    'qtd_cx_paradas': int(row.get('qtd_cx_paradas', 0)) if pd.notna(row.get('qtd_cx_paradas')) else None,
                    'total_caixas': int(row.get('total_caixas', 0)) if pd.notna(row.get('total_caixas')) else None,
                    'percentual_atingido_volume': float(row.get('perc_ating_volume', 0)),
                    'meta_pos': int(row.get('meta_positivacao', 0)) if pd.notna(row.get('meta_positivacao')) else None,
                    'clientes_pos': int(row.get('clientes_positivados', 0)) if pd.notna(row.get('clientes_positivados')) else None,
                    'percentual_atingido_pos': float(row.get('perc_ating_positivacao', 0)),
                }
                
                if meta:
                    # Atualiza meta existente
                    for key, value in meta_data.items():
                        setattr(meta, key, value)
                    updated += 1
                else:
                    # Cria nova meta
                    meta = MetaDepartamento(**meta_data)
                    session.add(meta)
                    inserted += 1
                
                # Commit em batches
                if (inserted + updated) % batch_size == 0:
                    session.commit()
                    logger.debug(f"Commit batch: {inserted + updated} metas processadas")
            
            except Exception as e:
                logger.error(f"Erro ao processar meta na linha {idx}: {str(e)}")
                import traceback
                logger.debug(traceback.format_exc())
                session.rollback()
                skipped += 1
                continue
        
        # Commit final
        session.commit()
        logger.info(f"Metas de departamento carregadas: {inserted} inseridas, {updated} atualizadas, {skipped} puladas")
        logger.debug(f"Total de linhas processadas: {inserted + updated + skipped} de {len(df)}")
        
        return inserted + updated
    
    except Exception as e:
        session.rollback()
        logger.error(f"Erro ao carregar metas de departamento: {str(e)}")
        raise
    finally:
        session.close()

