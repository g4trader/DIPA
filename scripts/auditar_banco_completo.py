#!/usr/bin/env python3
"""
Script de auditoria completa do banco de dados.

Verifica:
- Tabelas e colunas
- Totalizadores (Totais, Total, SOMA, etc.)
- Valores numéricos absurdos
- IDs nulos ou duplicados
- Registros suspeitos
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from collections import defaultdict

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import SQLAlchemyError


# Configurações
TOTALIZADOR_KEYWORDS = [
    'total', 'totais', 'soma', 'sum', 'subtotal', 'total geral',
    'consolidado', 'geral', 'agregado', 'resumo'
]

COLUNAS_NOME_ENTIDADE = [
    'vendedor', 'vendedor_nome', 'vendedor_id',
    'cliente', 'cliente_nome', 'cliente_id',
    'rota', 'rota_nome', 'rota_id',
    'supervisor', 'supervisor_nome', 'supervisor_id',
    'departamento', 'departamento_nome'
]

COLUNAS_NUMERICAS_SUSPEITAS = {
    'valor_meta': {'max': 10_000_000, 'desc': 'Meta > R$ 10M por vendedor'},
    'valor_faturado': {'max': 10_000_000, 'desc': 'Realizado > R$ 10M por vendedor'},
    'meta_total': {'max': 10_000_000, 'desc': 'Meta total > R$ 10M por registro'},
    'realizado_total': {'max': 10_000_000, 'desc': 'Realizado total > R$ 10M por registro'},
    'faturamento': {'max': 10_000_000, 'desc': 'Faturamento > R$ 10M por registro'},
    'valor': {'max': 10_000_000, 'desc': 'Valor > R$ 10M por registro'},
}


def conectar_banco():
    """Conecta ao banco SQLite."""
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
    return engine


def listar_tabelas(engine) -> List[str]:
    """Lista todas as tabelas do banco."""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT name 
            FROM sqlite_master 
            WHERE type='table' 
            AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """))
        return [row[0] for row in result.fetchall()]


def listar_colunas(engine, tabela: str) -> List[Dict[str, Any]]:
    """Lista todas as colunas de uma tabela."""
    inspector = inspect(engine)
    columns = inspector.get_columns(tabela)
    return columns


def detectar_colunas_entidade(colunas: List[Dict[str, Any]]) -> List[str]:
    """Detecta colunas que parecem nomes de vendedor/cliente/rota."""
    colunas_entidade = []
    for col in colunas:
        nome_col = col['name'].lower()
        for keyword in COLUNAS_NOME_ENTIDADE:
            if keyword.lower() in nome_col:
                colunas_entidade.append(col['name'])
                break
    return colunas_entidade


def buscar_totalizadores(engine, tabela: str, colunas_entidade: List[str]) -> List[Dict[str, Any]]:
    """Busca registros que parecem totalizadores."""
    if not colunas_entidade:
        return []
    
    totalizadores = []
    
    with engine.connect() as conn:
        for coluna in colunas_entidade:
            # Busca por palavras-chave de totalizador
            for keyword in TOTALIZADOR_KEYWORDS:
                try:
                    query = text(f"""
                        SELECT * 
                        FROM {tabela}
                        WHERE LOWER({coluna}) LIKE :pattern
                        LIMIT 100
                    """)
                    result = conn.execute(query, {'pattern': f'%{keyword}%'})
                    rows = result.fetchall()
                    
                    if rows:
                        # Pega nomes das colunas
                        try:
                            col_names = [desc[0] for desc in result.cursor.description] if result.cursor.description else []
                        except:
                            # Fallback: usa nomes das colunas da query
                            col_names = [col['name'] for col in listar_colunas(engine, tabela)]
                        
                        if not col_names:
                            continue
                        
                        for row in rows:
                            registro = dict(zip(col_names, row))
                            totalizadores.append({
                                'tabela': tabela,
                                'coluna': coluna,
                                'keyword': keyword,
                                'registro': registro
                            })
                except SQLAlchemyError as e:
                    # Ignora erros de query (pode ser tipo de coluna incompatível)
                    pass
    
    return totalizadores


def detectar_valores_absurdos(engine, tabela: str, colunas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Detecta valores numéricos absurdos."""
    valores_absurdos = []
    
    # Identifica colunas numéricas suspeitas
    colunas_suspeitas = []
    for col in colunas:
        nome_col = col['name'].lower()
        for col_suspeita, config in COLUNAS_NUMERICAS_SUSPEITAS.items():
            if col_suspeita.lower() in nome_col:
                colunas_suspeitas.append({
                    'nome': col['name'],
                    'max': config['max'],
                    'desc': config['desc']
                })
                break
    
    if not colunas_suspeitas:
        return []
    
    with engine.connect() as conn:
        for col_config in colunas_suspeitas:
            try:
                query = text(f"""
                    SELECT * 
                    FROM {tabela}
                    WHERE {col_config['nome']} > :max_valor
                    LIMIT 100
                """)
                result = conn.execute(query, {'max_valor': col_config['max']})
                rows = result.fetchall()
                
                if rows:
                    try:
                        col_names = [desc[0] for desc in result.cursor.description] if result.cursor.description else []
                    except:
                        col_names = [col['name'] for col in listar_colunas(engine, tabela)]
                    
                    if not col_names:
                        continue
                    
                    for row in rows:
                        registro = dict(zip(col_names, row))
                        valores_absurdos.append({
                            'tabela': tabela,
                            'coluna': col_config['nome'],
                            'valor': registro.get(col_config['nome']),
                            'max_esperado': col_config['max'],
                            'descricao': col_config['desc'],
                            'registro': registro
                        })
            except SQLAlchemyError as e:
                pass
    
    return valores_absurdos


def detectar_ids_nulos_duplicados(engine, tabela: str, colunas: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Detecta IDs nulos ou duplicados."""
    problemas = {
        'ids_nulos': [],
        'ids_duplicados': []
    }
    
    # Procura coluna 'id' ou colunas que terminam com '_id'
    colunas_id = []
    for col in colunas:
        nome_col = col['name'].lower()
        if nome_col == 'id' or nome_col.endswith('_id'):
            colunas_id.append(col['name'])
    
    if not colunas_id:
        return problemas
    
    with engine.connect() as conn:
        for col_id in colunas_id:
            # Verifica IDs nulos
            try:
                query = text(f"""
                    SELECT COUNT(*) as count
                    FROM {tabela}
                    WHERE {col_id} IS NULL
                """)
                result = conn.execute(query)
                count_nulos = result.fetchone()[0]
                
                if count_nulos > 0:
                    problemas['ids_nulos'].append({
                        'coluna': col_id,
                        'quantidade': count_nulos
                    })
            except SQLAlchemyError:
                pass
            
            # Verifica IDs duplicados
            try:
                query = text(f"""
                    SELECT {col_id}, COUNT(*) as count
                    FROM {tabela}
                    WHERE {col_id} IS NOT NULL
                    GROUP BY {col_id}
                    HAVING COUNT(*) > 1
                    LIMIT 100
                """)
                result = conn.execute(query)
                duplicados = result.fetchall()
                
                if duplicados:
                    problemas['ids_duplicados'].append({
                        'coluna': col_id,
                        'quantidade': len(duplicados),
                        'exemplos': [{'id': row[0], 'count': row[1]} for row in duplicados[:10]]
                    })
            except SQLAlchemyError:
                pass
    
    return problemas


def auditar_tabela(engine, tabela: str) -> Dict[str, Any]:
    """Audita uma tabela completa."""
    print(f"  📊 Auditando tabela: {tabela}")
    
    resultado = {
        'tabela': tabela,
        'colunas': [],
        'colunas_entidade': [],
        'totalizadores': [],
        'valores_absurdos': [],
        'problemas_ids': {},
        'total_registros': 0
    }
    
    try:
        # Lista colunas
        colunas = listar_colunas(engine, tabela)
        resultado['colunas'] = [{'nome': col['name'], 'tipo': str(col['type'])} for col in colunas]
        
        # Detecta colunas de entidade
        colunas_entidade = detectar_colunas_entidade(colunas)
        resultado['colunas_entidade'] = colunas_entidade
        
        # Conta registros
        with engine.connect() as conn:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {tabela}"))
            resultado['total_registros'] = result.fetchone()[0]
        
        # Busca totalizadores
        if colunas_entidade:
            totalizadores = buscar_totalizadores(engine, tabela, colunas_entidade)
            resultado['totalizadores'] = totalizadores
        
        # Detecta valores absurdos
        valores_absurdos = detectar_valores_absurdos(engine, tabela, colunas)
        resultado['valores_absurdos'] = valores_absurdos
        
        # Detecta problemas com IDs
        problemas_ids = detectar_ids_nulos_duplicados(engine, tabela, colunas)
        resultado['problemas_ids'] = problemas_ids
        
    except Exception as e:
        resultado['erro'] = str(e)
        print(f"    ⚠️  Erro ao auditar {tabela}: {str(e)}")
    
    return resultado


def gerar_relatorio(resultados: List[Dict[str, Any]], output_dir: Path):
    """Gera relatórios JSON e TXT."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Resumo estatístico
    resumo = {
        'timestamp': timestamp,
        'total_tabelas': len(resultados),
        'tabelas_com_problemas': 0,
        'total_totalizadores': 0,
        'total_valores_absurdos': 0,
        'total_ids_nulos': 0,
        'total_ids_duplicados': 0,
        'tabelas_problematicas': []
    }
    
    for resultado in resultados:
        tem_problema = False
        
        if resultado.get('totalizadores'):
            resumo['total_totalizadores'] += len(resultado['totalizadores'])
            tem_problema = True
        
        if resultado.get('valores_absurdos'):
            resumo['total_valores_absurdos'] += len(resultado['valores_absurdos'])
            tem_problema = True
        
        if resultado.get('problemas_ids', {}).get('ids_nulos'):
            total_nulos = sum(p['quantidade'] for p in resultado['problemas_ids']['ids_nulos'])
            resumo['total_ids_nulos'] += total_nulos
            tem_problema = True
        
        if resultado.get('problemas_ids', {}).get('ids_duplicados'):
            total_duplicados = sum(p['quantidade'] for p in resultado['problemas_ids']['ids_duplicados'])
            resumo['total_ids_duplicados'] += total_duplicados
            tem_problema = True
        
        if tem_problema:
            resumo['tabelas_com_problemas'] += 1
            resumo['tabelas_problematicas'].append(resultado['tabela'])
    
    # Relatório completo
    relatorio = {
        'resumo': resumo,
        'resultados': resultados
    }
    
    # Salva JSON
    json_path = output_dir / "auditoria_banco.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(relatorio, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n✅ Relatório JSON salvo: {json_path}")
    
    # Gera relatório TXT
    txt_path = output_dir / "auditoria_banco.txt"
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("AUDITORIA COMPLETA DO BANCO DE DADOS\n")
        f.write("=" * 80 + "\n")
        f.write(f"Data/Hora: {timestamp}\n")
        f.write("\n")
        
        # Resumo
        f.write("RESUMO EXECUTIVO\n")
        f.write("-" * 80 + "\n")
        f.write(f"Total de tabelas auditadas: {resumo['total_tabelas']}\n")
        f.write(f"Tabelas com problemas: {resumo['tabelas_com_problemas']}\n")
        f.write(f"Totalizadores encontrados: {resumo['total_totalizadores']}\n")
        f.write(f"Valores absurdos encontrados: {resumo['total_valores_absurdos']}\n")
        f.write(f"IDs nulos encontrados: {resumo['total_ids_nulos']}\n")
        f.write(f"IDs duplicados encontrados: {resumo['total_ids_duplicados']}\n")
        f.write("\n")
        
        # Detalhes por tabela
        f.write("DETALHES POR TABELA\n")
        f.write("=" * 80 + "\n")
        
        for resultado in resultados:
            f.write(f"\nTabela: {resultado['tabela']}\n")
            f.write(f"Total de registros: {resultado.get('total_registros', 0):,}\n")
            f.write(f"Colunas: {len(resultado.get('colunas', []))}\n")
            
            if resultado.get('colunas_entidade'):
                f.write(f"Colunas de entidade: {', '.join(resultado['colunas_entidade'])}\n")
            
            # Totalizadores
            if resultado.get('totalizadores'):
                f.write(f"\n⚠️  TOTALIZADORES ENCONTRADOS: {len(resultado['totalizadores'])}\n")
                for tot in resultado['totalizadores'][:5]:  # Mostra apenas os 5 primeiros
                    f.write(f"  - Coluna '{tot['coluna']}' contém '{tot['keyword']}'\n")
                    # Mostra alguns campos do registro
                    registro = tot['registro']
                    campos_relevantes = {k: v for k, v in registro.items() 
                                       if k in ['id', 'vendedor_nome', 'cliente_nome', 'valor_meta', 'valor_faturado'] 
                                       and v is not None}
                    if campos_relevantes:
                        f.write(f"    Registro: {campos_relevantes}\n")
            
            # Valores absurdos
            if resultado.get('valores_absurdos'):
                f.write(f"\n⚠️  VALORES ABSURDOS: {len(resultado['valores_absurdos'])}\n")
                for val in resultado['valores_absurdos'][:5]:
                    f.write(f"  - {val['descricao']}\n")
                    f.write(f"    Coluna: {val['coluna']}, Valor: {val['valor']:,.2f}\n")
            
            # Problemas com IDs
            if resultado.get('problemas_ids', {}).get('ids_nulos'):
                f.write(f"\n⚠️  IDs NULOS:\n")
                for prob in resultado['problemas_ids']['ids_nulos']:
                    f.write(f"  - Coluna '{prob['coluna']}': {prob['quantidade']} registros nulos\n")
            
            if resultado.get('problemas_ids', {}).get('ids_duplicados'):
                f.write(f"\n⚠️  IDs DUPLICADOS:\n")
                for prob in resultado['problemas_ids']['ids_duplicados']:
                    f.write(f"  - Coluna '{prob['coluna']}': {prob['quantidade']} IDs duplicados\n")
                    if prob.get('exemplos'):
                        f.write(f"    Exemplos: {prob['exemplos'][:3]}\n")
        
        # Recomendações
        f.write("\n" + "=" * 80 + "\n")
        f.write("RECOMENDAÇÕES\n")
        f.write("=" * 80 + "\n")
        
        if resumo['total_totalizadores'] > 0:
            f.write(f"\n1. REMOVER TOTALIZADORES:\n")
            f.write(f"   - {resumo['total_totalizadores']} registros de totalizador encontrados\n")
            f.write(f"   - Recomendação: Excluir linhas onde vendedor_nome/cliente_nome contém 'Total', 'Totais', etc.\n")
            f.write(f"   - Usar filtros: WHERE LOWER(vendedor_nome) NOT LIKE '%total%'\n")
        
        if resumo['total_valores_absurdos'] > 0:
            f.write(f"\n2. INVESTIGAR VALORES ABSURDOS:\n")
            f.write(f"   - {resumo['total_valores_absurdos']} valores suspeitos encontrados\n")
            f.write(f"   - Verificar se são erros de importação ou dados legítimos\n")
        
        if resumo['total_ids_nulos'] > 0:
            f.write(f"\n3. CORRIGIR IDs NULOS:\n")
            f.write(f"   - {resumo['total_ids_nulos']} registros com ID nulo\n")
            f.write(f"   - Verificar integridade referencial\n")
        
        if resumo['total_ids_duplicados'] > 0:
            f.write(f"\n4. CORRIGIR IDs DUPLICADOS:\n")
            f.write(f"   - {resumo['total_ids_duplicados']} IDs duplicados encontrados\n")
            f.write(f"   - Verificar constraints de unicidade\n")
        
        if resumo['total_totalizadores'] == 0 and resumo['total_valores_absurdos'] == 0:
            f.write("\n✅ Nenhum problema crítico encontrado!\n")
    
    print(f"✅ Relatório TXT salvo: {txt_path}")
    
    return resumo


def imprimir_resumo(resumo: Dict[str, Any]):
    """Imprime resumo destacado na tela."""
    print("\n" + "=" * 80)
    print("📋 RESUMO DA AUDITORIA")
    print("=" * 80)
    print(f"\n📊 Estatísticas Gerais:")
    print(f"   - Total de tabelas: {resumo['total_tabelas']}")
    print(f"   - Tabelas com problemas: {resumo['tabelas_com_problemas']}")
    
    if resumo['tabelas_problematicas']:
        print(f"\n⚠️  Tabelas com problemas:")
        for tabela in resumo['tabelas_problematicas']:
            print(f"   - {tabela}")
    
    print(f"\n🔍 Problemas Encontrados:")
    print(f"   - Totalizadores: {resumo['total_totalizadores']}")
    print(f"   - Valores absurdos: {resumo['total_valores_absurdos']}")
    print(f"   - IDs nulos: {resumo['total_ids_nulos']}")
    print(f"   - IDs duplicados: {resumo['total_ids_duplicados']}")
    
    print(f"\n💡 Recomendações:")
    if resumo['total_totalizadores'] > 0:
        print(f"   ⚠️  REMOVER {resumo['total_totalizadores']} registros de totalizador")
        print(f"      Use: WHERE LOWER(vendedor_nome) NOT LIKE '%total%'")
    
    if resumo['total_valores_absurdos'] > 0:
        print(f"   ⚠️  INVESTIGAR {resumo['total_valores_absurdos']} valores suspeitos")
    
    if resumo['total_ids_nulos'] > 0:
        print(f"   ⚠️  CORRIGIR {resumo['total_ids_nulos']} IDs nulos")
    
    if resumo['total_ids_duplicados'] > 0:
        print(f"   ⚠️  CORRIGIR {resumo['total_ids_duplicados']} IDs duplicados")
    
    if (resumo['total_totalizadores'] == 0 and 
        resumo['total_valores_absurdos'] == 0 and 
        resumo['total_ids_nulos'] == 0 and 
        resumo['total_ids_duplicados'] == 0):
        print(f"   ✅ Nenhum problema crítico encontrado!")
    
    print("\n" + "=" * 80)


def main():
    """Função principal."""
    print("🔍 Iniciando auditoria completa do banco de dados...")
    print("=" * 80)
    
    try:
        # Conecta ao banco
        engine = conectar_banco()
        print("✅ Conectado ao banco de dados")
        
        # Lista tabelas
        tabelas = listar_tabelas(engine)
        print(f"✅ Encontradas {len(tabelas)} tabelas para auditar")
        print(f"   Tabelas: {', '.join(tabelas[:10])}{'...' if len(tabelas) > 10 else ''}")
        
        # Audita cada tabela
        resultados = []
        for tabela in tabelas:
            resultado = auditar_tabela(engine, tabela)
            resultados.append(resultado)
        
        # Gera relatórios
        output_dir = Path(__file__).parent.parent
        resumo = gerar_relatorio(resultados, output_dir)
        
        # Imprime resumo
        imprimir_resumo(resumo)
        
        print("\n✅ Auditoria concluída com sucesso!")
        
    except Exception as e:
        print(f"\n❌ Erro durante auditoria: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

