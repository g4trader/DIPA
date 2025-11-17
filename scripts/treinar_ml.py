#!/usr/bin/env python3
"""
Script de treinamento de ML: gera embeddings e índices vetoriais.

Carrega dados limpos, gera embeddings de vendedores, clientes e produtos,
e cria índices vetoriais (FAISS) para busca semântica.
"""

import os
import sys
import json
import hashlib
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import numpy as np

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Tenta importar bibliotecas de ML
try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    print("⚠️  FAISS não disponível. Instale com: pip install faiss-cpu")

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("⚠️  OpenAI não disponível. Instale com: pip install openai")


# Configurações
ML_CACHE_DIR = Path(__file__).parent.parent / "ml_cache"
EMBEDDING_MODEL = "text-embedding-3-small"  # OpenAI embedding model
EMBEDDING_DIM = 1536  # Dimensão do embedding do text-embedding-3-small


def criar_diretorio_cache():
    """Cria diretório ml_cache se não existir."""
    ML_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    print(f"✅ Diretório de cache: {ML_CACHE_DIR}")


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


def calcular_hash_dados(engine, tabelas: List[str]) -> str:
    """Calcula hash fingerprint dos dados para detectar mudanças."""
    hasher = hashlib.sha256()
    
    with engine.connect() as conn:
        for tabela in tabelas:
            try:
                # Conta registros e pega alguns campos para hash
                result = conn.execute(text(f"""
                    SELECT COUNT(*) as count, 
                           MAX(id) as max_id,
                           MIN(id) as min_id
                    FROM {tabela}
                """))
                row = result.fetchone()
                if row:
                    hasher.update(f"{tabela}:{row[0]}:{row[1]}:{row[2]}".encode())
            except SQLAlchemyError:
                pass
    
    return hasher.hexdigest()[:16]  # Primeiros 16 caracteres


def carregar_dados_limpos(engine) -> Dict[str, Any]:
    """Carrega dados limpos das tabelas principais."""
    print("\n📊 Carregando dados limpos...")
    
    dados = {}
    
    with engine.connect() as conn:
        # Vendedores (exclui totalizadores)
        print("  - Carregando vendedores...")
        try:
            result = conn.execute(text("""
                SELECT id, nome, codigo, rota_rca, supervisor_id
                FROM vendedores
                WHERE LOWER(nome) NOT LIKE '%total%'
                AND nome != 'Totais'
                AND id IS NOT NULL
            """))
            dados['vendedores'] = [
                {
                    'id': row[0],
                    'nome': row[1] or '',
                    'codigo': row[2] or '',
                    'rota_rca': row[3] or '',
                    'supervisor_id': row[4]
                }
                for row in result.fetchall()
            ]
            print(f"    ✅ {len(dados['vendedores'])} vendedores carregados")
        except SQLAlchemyError as e:
            print(f"    ⚠️  Erro ao carregar vendedores: {e}")
            dados['vendedores'] = []
        
        # Clientes (exclui totalizadores)
        print("  - Carregando clientes...")
        try:
            result = conn.execute(text("""
                SELECT id, nome, fantasia, cidade_cliente, segmento_venda, rota_rca
                FROM clientes
                WHERE LOWER(nome) NOT LIKE '%total%'
                AND LOWER(nome) NOT LIKE '%soma%'
                AND LOWER(nome) NOT LIKE '%sum%'
                AND nome != 'Totais'
                AND id IS NOT NULL
                LIMIT 10000
            """))
            dados['clientes'] = [
                {
                    'id': row[0],
                    'nome': row[1] or '',
                    'fantasia': row[2] or '',
                    'cidade': row[3] or '',
                    'segmento': row[4] or '',
                    'rota_rca': row[5] or ''
                }
                for row in result.fetchall()
            ]
            print(f"    ✅ {len(dados['clientes'])} clientes carregados")
        except SQLAlchemyError as e:
            print(f"    ⚠️  Erro ao carregar clientes: {e}")
            dados['clientes'] = []
        
        # Produtos (da tabela vendas)
        print("  - Carregando produtos...")
        try:
            result = conn.execute(text("""
                SELECT DISTINCT codigo_produto, desc_produto, departamento, secao
                FROM vendas
                WHERE codigo_produto IS NOT NULL
                AND desc_produto IS NOT NULL
                LIMIT 5000
            """))
            produtos_dict = {}
            for row in result.fetchall():
                codigo = row[0]
                if codigo and codigo not in produtos_dict:
                    produtos_dict[codigo] = {
                        'codigo': codigo,
                        'descricao': row[1] or '',
                        'departamento': row[2] or '',
                        'secao': row[3] or ''
                    }
            dados['produtos'] = list(produtos_dict.values())
            print(f"    ✅ {len(dados['produtos'])} produtos únicos carregados")
        except SQLAlchemyError as e:
            print(f"    ⚠️  Erro ao carregar produtos: {e}")
            dados['produtos'] = []
        
        # Metas (para contexto)
        print("  - Carregando metas...")
        try:
            result = conn.execute(text("""
                SELECT COUNT(*) as count
                FROM metas_vendedor
                WHERE LOWER(vendedor_nome) NOT LIKE '%total%'
                AND vendedor_nome != 'Totais'
            """))
            dados['metas_count'] = result.fetchone()[0]
            print(f"    ✅ {dados['metas_count']} registros de metas (contagem)")
        except SQLAlchemyError as e:
            dados['metas_count'] = 0
        
        # Vendas (contagem)
        print("  - Carregando vendas...")
        try:
            result = conn.execute(text("""
                SELECT COUNT(*) as count
                FROM vendas
                WHERE LOWER(nome_cliente) NOT LIKE '%soma%'
                AND LOWER(nome_cliente) NOT LIKE '%sum%'
            """))
            dados['vendas_count'] = result.fetchone()[0]
            print(f"    ✅ {dados['vendas_count']} registros de vendas (contagem)")
        except SQLAlchemyError as e:
            dados['vendas_count'] = 0
    
    return dados


def gerar_texto_embedding(entidade: Dict[str, Any], tipo: str) -> str:
    """Gera texto para embedding baseado no tipo de entidade."""
    if tipo == 'vendedor':
        partes = [
            entidade.get('nome', ''),
            entidade.get('codigo', ''),
            entidade.get('rota_rca', '')
        ]
        return ' '.join(filter(None, partes)).strip()
    
    elif tipo == 'cliente':
        partes = [
            entidade.get('nome', ''),
            entidade.get('fantasia', ''),
            entidade.get('cidade', ''),
            entidade.get('segmento', ''),
            entidade.get('rota_rca', '')
        ]
        return ' '.join(filter(None, partes)).strip()
    
    elif tipo == 'produto':
        partes = [
            entidade.get('descricao', ''),
            entidade.get('codigo', ''),
            entidade.get('departamento', ''),
            entidade.get('secao', '')
        ]
        return ' '.join(filter(None, partes)).strip()
    
    return ''


def gerar_embeddings_openai(textos: List[str], batch_size: int = 100) -> np.ndarray:
    """Gera embeddings usando OpenAI API."""
    if not OPENAI_AVAILABLE:
        raise ImportError("OpenAI não está disponível")
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY não está definida")
    
    client = OpenAI(api_key=api_key)
    embeddings = []
    
    print(f"    📡 Gerando embeddings via OpenAI ({len(textos)} textos)...")
    
    # Processa em batches
    for i in range(0, len(textos), batch_size):
        batch = textos[i:i + batch_size]
        try:
            response = client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=batch
            )
            batch_embeddings = [item.embedding for item in response.data]
            embeddings.extend(batch_embeddings)
            
            if (i + batch_size) % 500 == 0:
                print(f"      Processados {min(i + batch_size, len(textos))}/{len(textos)} textos")
        
        except Exception as e:
            print(f"      ⚠️  Erro no batch {i//batch_size + 1}: {e}")
            # Preenche com zeros em caso de erro
            embeddings.extend([[0.0] * EMBEDDING_DIM] * len(batch))
    
    return np.array(embeddings, dtype=np.float32)


def gerar_embeddings_entidades(dados: Dict[str, Any], tipo: str) -> tuple:
    """Gera embeddings para um tipo de entidade."""
    print(f"\n🔮 Gerando embeddings de {tipo}...")
    
    entidades = dados.get(tipo, [])
    if not entidades:
        print(f"    ⚠️  Nenhum {tipo} encontrado")
        return np.array([]), []
    
    # Gera textos para embedding
    textos = [gerar_texto_embedding(ent, tipo) for ent in entidades]
    textos = [t for t in textos if t]  # Remove vazios
    
    if not textos:
        print(f"    ⚠️  Nenhum texto válido para {tipo}")
        return np.array([]), []
    
    # Gera embeddings
    if OPENAI_AVAILABLE:
        embeddings = gerar_embeddings_openai(textos)
    else:
        # Fallback: embeddings aleatórios (para teste)
        print(f"    ⚠️  OpenAI não disponível, usando embeddings aleatórios")
        embeddings = np.random.randn(len(textos), EMBEDDING_DIM).astype(np.float32)
        embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
    
    # IDs correspondentes
    ids = [ent.get('id') or ent.get('codigo') for ent in entidades if gerar_texto_embedding(ent, tipo)]
    
    print(f"    ✅ {len(embeddings)} embeddings gerados")
    
    return embeddings, ids


def criar_indice_faiss(embeddings: np.ndarray) -> Optional[Any]:
    """Cria índice FAISS para busca vetorial."""
    if not FAISS_AVAILABLE:
        print("    ⚠️  FAISS não disponível, pulando criação de índice")
        return None
    
    if len(embeddings) == 0:
        print("    ⚠️  Nenhum embedding para criar índice")
        return None
    
    print(f"    🔍 Criando índice FAISS ({len(embeddings)} vetores, dim={embeddings.shape[1]})...")
    
    # Normaliza embeddings
    faiss.normalize_L2(embeddings)
    
    # Cria índice L2 (Euclidean distance)
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    
    # Adiciona vetores
    index.add(embeddings)
    
    print(f"    ✅ Índice criado: {index.ntotal} vetores")
    
    return index


def salvar_embeddings(embeddings: np.ndarray, ids: List[Any], tipo: str):
    """Salva embeddings em arquivo numpy."""
    arquivo = ML_CACHE_DIR / f"embeddings_{tipo}.npy"
    arquivo_ids = ML_CACHE_DIR / f"ids_{tipo}.json"
    
    np.save(arquivo, embeddings)
    print(f"    💾 Embeddings salvos: {arquivo}")
    
    with open(arquivo_ids, 'w', encoding='utf-8') as f:
        json.dump(ids, f, ensure_ascii=False)
    print(f"    💾 IDs salvos: {arquivo_ids}")


def salvar_indice_faiss(index: Any, tipo: str):
    """Salva índice FAISS."""
    if index is None:
        return
    
    arquivo = ML_CACHE_DIR / f"index_{tipo}.faiss"
    faiss.write_index(index, str(arquivo))
    print(f"    💾 Índice FAISS salvo: {arquivo}")


def criar_manifest(dados: Dict[str, Any], hash_dados: str, tempos: Dict[str, float]) -> Dict[str, Any]:
    """Cria manifest.json com metadados."""
    manifest = {
        'timestamp': datetime.now().isoformat(),
        'schema_version': '1.0.0',
        'embedding_model': EMBEDDING_MODEL,
        'embedding_dim': EMBEDDING_DIM,
        'data_fingerprint': hash_dados,
        'registros': {
            'vendedores': len(dados.get('vendedores', [])),
            'clientes': len(dados.get('clientes', [])),
            'produtos': len(dados.get('produtos', [])),
            'metas': dados.get('metas_count', 0),
            'vendas': dados.get('vendas_count', 0)
        },
        'embeddings_gerados': {
            'vendedores': len(dados.get('vendedores', [])),
            'clientes': len(dados.get('clientes', [])),
            'produtos': len(dados.get('produtos', []))
        },
        'tempos': tempos,
        'faiss_disponivel': FAISS_AVAILABLE,
        'openai_disponivel': OPENAI_AVAILABLE
    }
    
    return manifest


def calcular_tamanho_indice(tipo: str) -> int:
    """Calcula tamanho do índice em bytes."""
    arquivo = ML_CACHE_DIR / f"index_{tipo}.faiss"
    if arquivo.exists():
        return arquivo.stat().st_size
    return 0


def main():
    """Função principal."""
    print("🤖 Iniciando treinamento de ML (embeddings e índices vetoriais)...")
    print("=" * 80)
    
    inicio_total = time.time()
    tempos = {}
    
    try:
        # Cria diretório de cache
        criar_diretorio_cache()
        
        # Conecta ao banco
        engine = conectar_banco()
        print("✅ Conectado ao banco de dados")
        
        # Carrega dados limpos
        inicio_carregamento = time.time()
        dados = carregar_dados_limpos(engine)
        tempos['carregamento'] = time.time() - inicio_carregamento
        
        # Calcula hash dos dados
        tabelas = ['vendedores', 'clientes', 'vendas', 'metas_vendedor']
        hash_dados = calcular_hash_dados(engine, tabelas)
        print(f"\n🔐 Fingerprint dos dados: {hash_dados}")
        
        # Gera embeddings
        embeddings_total = 0
        
        # Vendedores
        inicio = time.time()
        emb_vendedores, ids_vendedores = gerar_embeddings_entidades(dados, 'vendedores')
        if len(emb_vendedores) > 0:
            salvar_embeddings(emb_vendedores, ids_vendedores, 'vendedores')
            index_vendedores = criar_indice_faiss(emb_vendedores)
            salvar_indice_faiss(index_vendedores, 'vendedores')
            embeddings_total += len(emb_vendedores)
        tempos['embeddings_vendedores'] = time.time() - inicio
        
        # Clientes
        inicio = time.time()
        emb_clientes, ids_clientes = gerar_embeddings_entidades(dados, 'clientes')
        if len(emb_clientes) > 0:
            salvar_embeddings(emb_clientes, ids_clientes, 'clientes')
            index_clientes = criar_indice_faiss(emb_clientes)
            salvar_indice_faiss(index_clientes, 'clientes')
            embeddings_total += len(emb_clientes)
        tempos['embeddings_clientes'] = time.time() - inicio
        
        # Produtos
        inicio = time.time()
        emb_produtos, ids_produtos = gerar_embeddings_entidades(dados, 'produtos')
        if len(emb_produtos) > 0:
            salvar_embeddings(emb_produtos, ids_produtos, 'produtos')
            index_produtos = criar_indice_faiss(emb_produtos)
            salvar_indice_faiss(index_produtos, 'produtos')
            embeddings_total += len(emb_produtos)
        tempos['embeddings_produtos'] = time.time() - inicio
        
        # Cria manifest
        tempos['total'] = time.time() - inicio_total
        manifest = criar_manifest(dados, hash_dados, tempos)
        
        # Salva manifest
        manifest_path = ML_CACHE_DIR / "manifest.json"
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        print(f"\n✅ Manifest salvo: {manifest_path}")
        
        # Relatório final
        print("\n" + "=" * 80)
        print("📋 RELATÓRIO FINAL")
        print("=" * 80)
        print(f"\n📊 Total de embeddings gerados: {embeddings_total}")
        print(f"   - Vendedores: {len(emb_vendedores)}")
        print(f"   - Clientes: {len(emb_clientes)}")
        print(f"   - Produtos: {len(emb_produtos)}")
        
        print(f"\n⏱️  Tempo total: {tempos['total']:.2f}s")
        print(f"   - Carregamento: {tempos['carregamento']:.2f}s")
        print(f"   - Embeddings vendedores: {tempos['embeddings_vendedores']:.2f}s")
        print(f"   - Embeddings clientes: {tempos['embeddings_clientes']:.2f}s")
        print(f"   - Embeddings produtos: {tempos['embeddings_produtos']:.2f}s")
        
        print(f"\n💾 Tamanho dos índices:")
        for tipo in ['vendedores', 'clientes', 'produtos']:
            tamanho = calcular_tamanho_indice(tipo)
            if tamanho > 0:
                tamanho_mb = tamanho / (1024 * 1024)
                print(f"   - {tipo}: {tamanho_mb:.2f} MB")
        
        print(f"\n🔐 Fingerprint: {hash_dados}")
        print(f"📁 Cache: {ML_CACHE_DIR}")
        print("\n✅ Treinamento concluído com sucesso!")
        
    except Exception as e:
        print(f"\n❌ Erro durante treinamento: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

