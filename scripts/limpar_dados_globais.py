#!/usr/bin/env python3
"""
Script de limpeza global de dados do banco.

Remove totalizadores, normaliza campos de texto, converte valores monetários
e verifica datas inválidas.
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from decimal import Decimal

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text, inspect, Column, Integer, String, DateTime, Float
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

# Lista de tabelas principais (mapeadas pelo SQLAlchemy)
# Podemos listar diretamente do banco também
TABELAS_PRINCIPAIS = [
    'metas_vendedor',
    'metas_departamento',
    'vendas',
    'vendedores',
    'clientes',
    'supervisores',
    'interacoes_agent',
    'meta_predictions',
    'churn_risk',
    'dim_tempo'
]


# Configurações
TOTALIZADOR_KEYWORDS = ['total', 'totais', 'soma', 'sum', 'subtotal', 'total geral']
COLUNAS_NOME_ENTIDADE = ['vendedor_nome', 'cliente_nome', 'supervisor_nome', 'departamento', 'nome']
COLUNAS_MONETARIAS = ['valor_meta', 'valor_faturado', 'valor_parado', 'valor_total', 
                     'faturamento', 'valor', 'preco', 'preco_unitario', 'valor_total_item']
COLUNAS_DATA = ['data_venda', 'data', 'created_at', 'updated_at', 'mes_ano']


def criar_tabela_log(engine):
    """Cria tabela de log se não existir."""
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS data_clean_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tabela TEXT NOT NULL,
                id_removido INTEGER,
                motivo TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                detalhes TEXT
            )
        """))
        conn.commit()
    print("✅ Tabela de log criada/verificada")


def registrar_log(engine, tabela: str, id_removido: Optional[int], motivo: str, detalhes: Optional[str] = None):
    """Registra uma entrada no log."""
    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO data_clean_log (tabela, id_removido, motivo, detalhes)
            VALUES (:tabela, :id_removido, :motivo, :detalhes)
        """), {
            'tabela': tabela,
            'id_removido': id_removido,
            'motivo': motivo,
            'detalhes': detalhes
        })
        conn.commit()


def listar_tabelas_mapeadas(engine) -> List[str]:
    """Lista todas as tabelas mapeadas pelo SQLAlchemy que existem no banco."""
    # Verifica quais tabelas realmente existem no banco
    inspector = inspect(engine)
    tabelas_existentes = set(inspector.get_table_names())
    
    # Filtra apenas tabelas principais (exclui tabelas de sistema e log)
    tabelas_sistema = {'sqlite_sequence', 'data_clean_log'}
    tabelas_validas = [
        t for t in TABELAS_PRINCIPAIS 
        if t in tabelas_existentes and t not in tabelas_sistema
    ]
    
    return sorted(tabelas_validas)


def detectar_colunas_nome(engine, tabela: str) -> List[str]:
    """Detecta colunas que parecem nomes de entidade."""
    inspector = inspect(engine)
    colunas = inspector.get_columns(tabela)
    
    colunas_nome = []
    for col in colunas:
        nome_col = col['name'].lower()
        for keyword in COLUNAS_NOME_ENTIDADE:
            if keyword.lower() in nome_col:
                colunas_nome.append(col['name'])
                break
    return colunas_nome


def detectar_colunas_monetarias(engine, tabela: str) -> List[str]:
    """Detecta colunas monetárias."""
    inspector = inspect(engine)
    colunas = inspector.get_columns(tabela)
    
    colunas_monetarias = []
    for col in colunas:
        nome_col = col['name'].lower()
        tipo_col = str(col['type']).lower()
        
        # Verifica por nome
        for keyword in COLUNAS_MONETARIAS:
            if keyword.lower() in nome_col:
                colunas_monetarias.append(col['name'])
                break
        
        # Verifica por tipo (Float, Numeric, Decimal)
        if 'float' in tipo_col or 'numeric' in tipo_col or 'decimal' in tipo_col:
            if col['name'] not in colunas_monetarias:
                colunas_monetarias.append(col['name'])
    
    return colunas_monetarias


def detectar_colunas_data(engine, tabela: str) -> List[str]:
    """Detecta colunas de data."""
    inspector = inspect(engine)
    colunas = inspector.get_columns(tabela)
    
    colunas_data = []
    for col in colunas:
        nome_col = col['name'].lower()
        tipo_col = str(col['type']).lower()
        
        # Verifica por nome
        for keyword in COLUNAS_DATA:
            if keyword.lower() in nome_col:
                colunas_data.append(col['name'])
                break
        
        # Verifica por tipo (Date, DateTime)
        if 'date' in tipo_col:
            if col['name'] not in colunas_data:
                colunas_data.append(col['name'])
    
    return colunas_data


def remover_totalizadores(engine, tabela: str, colunas_nome: List[str]) -> int:
    """Remove registros que contêm totalizadores."""
    if not colunas_nome:
        return 0
    
    total_removidos = 0
    
    with engine.connect() as conn:
        for coluna in colunas_nome:
            for keyword in TOTALIZADOR_KEYWORDS:
                try:
                    # Busca IDs a serem removidos
                    query = text(f"""
                        SELECT id, {coluna}
                        FROM {tabela}
                        WHERE LOWER({coluna}) LIKE :pattern
                    """)
                    result = conn.execute(query, {'pattern': f'%{keyword}%'})
                    rows = result.fetchall()
                    
                    if rows:
                        ids_remover = [row[0] for row in rows if row[0] is not None]
                        
                        if ids_remover:
                            # Remove registros
                            placeholders = ','.join([':id' + str(i) for i in range(len(ids_remover))])
                            params = {f'id{i}': id_val for i, id_val in enumerate(ids_remover)}
                            
                            delete_query = text(f"DELETE FROM {tabela} WHERE id IN ({placeholders})")
                            conn.execute(delete_query, params)
                            conn.commit()
                            
                            # Registra no log
                            for id_val, nome_val in rows:
                                if id_val:
                                    registrar_log(
                                        engine, tabela, id_val,
                                        f"Totalizador removido: '{keyword}' em coluna '{coluna}'",
                                        f"Valor: {nome_val}"
                                    )
                            
                            total_removidos += len(ids_remover)
                            print(f"    🗑️  Removidos {len(ids_remover)} registros com '{keyword}' em '{coluna}'")
                
                except SQLAlchemyError as e:
                    # Ignora erros (pode ser tipo de coluna incompatível)
                    pass
    
    return total_removidos


def normalizar_texto(engine, tabela: str, colunas_texto: List[str]) -> int:
    """Normaliza campos de texto (strip, remove whitespace duplo)."""
    if not colunas_texto:
        return 0
    
    total_corrigidos = 0
    
    with engine.connect() as conn:
        for coluna in colunas_texto:
            try:
                # Busca registros com problemas
                query = text(f"""
                    SELECT id, {coluna}
                    FROM {tabela}
                    WHERE {coluna} IS NOT NULL
                    AND (
                        {coluna} != TRIM({coluna})
                        OR {coluna} LIKE '%  %'
                    )
                """)
                result = conn.execute(query)
                rows = result.fetchall()
                
                if rows:
                    for row_id, valor_original in rows:
                        if valor_original:
                            # Normaliza: strip e remove espaços duplos
                            valor_normalizado = ' '.join(str(valor_original).strip().split())
                            
                            if valor_normalizado != valor_original:
                                # Atualiza
                                update_query = text(f"""
                                    UPDATE {tabela}
                                    SET {coluna} = :novo_valor
                                    WHERE id = :id
                                """)
                                conn.execute(update_query, {
                                    'novo_valor': valor_normalizado,
                                    'id': row_id
                                })
                                conn.commit()
                                
                                registrar_log(
                                    engine, tabela, row_id,
                                    f"Texto normalizado na coluna '{coluna}'",
                                    f"'{valor_original}' -> '{valor_normalizado}'"
                                )
                                total_corrigidos += 1
                
                if total_corrigidos > 0:
                    print(f"    ✏️  Normalizados {total_corrigidos} registros na coluna '{coluna}'")
            
            except SQLAlchemyError as e:
                pass
    
    return total_corrigidos


def converter_monetarios(engine, tabela: str, colunas_monetarias: List[str]) -> int:
    """Converte campos monetários para float."""
    if not colunas_monetarias:
        return 0
    
    total_corrigidos = 0
    
    with engine.connect() as conn:
        for coluna in colunas_monetarias:
            try:
                # Busca registros com valores que não são numéricos
                query = text(f"""
                    SELECT id, {coluna}
                    FROM {tabela}
                    WHERE {coluna} IS NOT NULL
                    AND typeof({coluna}) = 'text'
                """)
                result = conn.execute(query)
                rows = result.fetchall()
                
                if rows:
                    for row_id, valor_original in rows:
                        if valor_original:
                            try:
                                # Tenta converter para float
                                # Remove caracteres não numéricos (exceto ponto e vírgula)
                                valor_str = str(valor_original).replace(',', '.').replace('R$', '').replace(' ', '')
                                valor_float = float(valor_str)
                                
                                # Atualiza
                                update_query = text(f"""
                                    UPDATE {tabela}
                                    SET {coluna} = :novo_valor
                                    WHERE id = :id
                                """)
                                conn.execute(update_query, {
                                    'novo_valor': valor_float,
                                    'id': row_id
                                })
                                conn.commit()
                                
                                registrar_log(
                                    engine, tabela, row_id,
                                    f"Valor monetário convertido na coluna '{coluna}'",
                                    f"'{valor_original}' -> {valor_float}"
                                )
                                total_corrigidos += 1
                            
                            except (ValueError, TypeError):
                                # Não conseguiu converter, registra como problema
                                registrar_log(
                                    engine, tabela, row_id,
                                    f"Valor monetário inválido na coluna '{coluna}'",
                                    f"Valor: {valor_original}"
                                )
                
                if total_corrigidos > 0:
                    print(f"    💰 Convertidos {total_corrigidos} valores monetários na coluna '{coluna}'")
            
            except SQLAlchemyError as e:
                pass
    
    return total_corrigidos


def verificar_datas(engine, tabela: str, colunas_data: List[str]) -> int:
    """Verifica e corrige datas inválidas ou vazias."""
    if not colunas_data:
        return 0
    
    total_problemas = 0
    
    with engine.connect() as conn:
        for coluna in colunas_data:
            try:
                # Busca datas inválidas (NULL ou strings vazias)
                query = text(f"""
                    SELECT id, {coluna}
                    FROM {tabela}
                    WHERE {coluna} IS NULL
                    OR {coluna} = ''
                    OR {coluna} = '0000-00-00'
                    OR {coluna} = '1900-01-01'
                """)
                result = conn.execute(query)
                rows = result.fetchall()
                
                if rows:
                    for row_id, valor in rows:
                        registrar_log(
                            engine, tabela, row_id,
                            f"Data inválida ou vazia na coluna '{coluna}'",
                            f"Valor: {valor}"
                        )
                        total_problemas += 1
                
                if total_problemas > 0:
                    print(f"    📅 Encontrados {total_problemas} problemas de data na coluna '{coluna}'")
            
            except SQLAlchemyError as e:
                pass
    
    return total_problemas


def limpar_tabela(engine, tabela: str) -> Dict[str, int]:
    """Limpa uma tabela completa."""
    print(f"\n📊 Limpando tabela: {tabela}")
    
    resultado = {
        'totalizadores_removidos': 0,
        'textos_normalizados': 0,
        'monetarios_convertidos': 0,
        'datas_problemas': 0
    }
    
    try:
        # Detecta colunas
        colunas_nome = detectar_colunas_nome(engine, tabela)
        colunas_monetarias = detectar_colunas_monetarias(engine, tabela)
        colunas_data = detectar_colunas_data(engine, tabela)
        
        # Detecta todas as colunas de texto
        inspector = inspect(engine)
        todas_colunas = inspector.get_columns(tabela)
        colunas_texto = [
            col['name'] for col in todas_colunas
            if 'text' in str(col['type']).lower() or 'varchar' in str(col['type']).lower()
        ]
        
        # Remove totalizadores
        if colunas_nome:
            resultado['totalizadores_removidos'] = remover_totalizadores(engine, tabela, colunas_nome)
        
        # Normaliza texto
        if colunas_texto:
            resultado['textos_normalizados'] = normalizar_texto(engine, tabela, colunas_texto)
        
        # Converte monetários
        if colunas_monetarias:
            resultado['monetarios_convertidos'] = converter_monetarios(engine, tabela, colunas_monetarias)
        
        # Verifica datas
        if colunas_data:
            resultado['datas_problemas'] = verificar_datas(engine, tabela, colunas_data)
    
    except Exception as e:
        print(f"    ⚠️  Erro ao limpar {tabela}: {str(e)}")
        registrar_log(engine, tabela, None, f"Erro durante limpeza: {str(e)}", None)
    
    return resultado


def main():
    """Função principal."""
    print("🧹 Iniciando limpeza global de dados...")
    print("=" * 80)
    
    try:
        # Conecta ao banco
        db_type = os.getenv("DB_TYPE", "sqlite")
        sqlite_path = os.getenv("SQLITE_PATH", "data/dipam_dw.db")
        
        if db_type != "sqlite":
            raise ValueError(f"Este script suporta apenas SQLite. DB_TYPE={db_type}")
        
        # Resolve caminho absoluto se necessário
        if not os.path.isabs(sqlite_path):
            project_root = Path(__file__).parent.parent
            sqlite_path = project_root / sqlite_path
        
        if not os.path.exists(sqlite_path):
            raise FileNotFoundError(f"Banco de dados não encontrado: {sqlite_path}")
        
        engine = create_engine(f"sqlite:///{sqlite_path}")
        print(f"✅ Conectado ao banco: {sqlite_path}")
        
        # Cria tabela de log
        criar_tabela_log(engine)
        
        # Lista tabelas mapeadas
        tabelas = listar_tabelas_mapeadas(engine)
        print(f"✅ Encontradas {len(tabelas)} tabelas para limpar")
        print(f"   Tabelas: {', '.join(tabelas)}")
        
        # Limpa cada tabela
        resultados_gerais = {}
        for tabela in tabelas:
            resultado = limpar_tabela(engine, tabela)
            resultados_gerais[tabela] = resultado
        
        # Imprime resumo
        print("\n" + "=" * 80)
        print("📋 RESUMO DA LIMPEZA")
        print("=" * 80)
        
        total_removidos = 0
        total_normalizados = 0
        total_convertidos = 0
        total_datas = 0
        
        for tabela, resultado in resultados_gerais.items():
            removidos = resultado['totalizadores_removidos']
            normalizados = resultado['textos_normalizados']
            convertidos = resultado['monetarios_convertidos']
            datas = resultado['datas_problemas']
            
            if removidos > 0 or normalizados > 0 or convertidos > 0 or datas > 0:
                print(f"\n📊 {tabela}:")
                if removidos > 0:
                    print(f"   🗑️  Totalizadores removidos: {removidos}")
                if normalizados > 0:
                    print(f"   ✏️  Textos normalizados: {normalizados}")
                if convertidos > 0:
                    print(f"   💰 Valores monetários convertidos: {convertidos}")
                if datas > 0:
                    print(f"   📅 Problemas de data encontrados: {datas}")
            
            total_removidos += removidos
            total_normalizados += normalizados
            total_convertidos += convertidos
            total_datas += datas
        
        print("\n" + "=" * 80)
        print("📊 TOTAIS GERAIS")
        print("=" * 80)
        print(f"   🗑️  Totalizadores removidos: {total_removidos}")
        print(f"   ✏️  Textos normalizados: {total_normalizados}")
        print(f"   💰 Valores monetários convertidos: {total_convertidos}")
        print(f"   📅 Problemas de data encontrados: {total_datas}")
        print(f"\n✅ Limpeza concluída! Log salvo em data_clean_log")
        
    except Exception as e:
        print(f"\n❌ Erro durante limpeza: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

