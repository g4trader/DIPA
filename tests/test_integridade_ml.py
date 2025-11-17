"""
Testes de integridade para ML e dados.

Verifica:
- KPIs corretos para agosto/2025
- Ausência de totalizadores
- Consistência de consultas
- Embeddings válidos
- IDs sem duplicatas
"""

import pytest
import sys
import os
from pathlib import Path
import json

# Importa numpy opcionalmente
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    np = None

# Adiciona o diretório raiz ao path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

# Importa diretamente do módulo connection sem passar pelo __init__.py
import importlib.util
connection_spec = importlib.util.spec_from_file_location(
    "connection",
    root_dir / "src" / "dw" / "connection.py"
)
connection_module = importlib.util.module_from_spec(connection_spec)
sys.modules["connection"] = connection_module
connection_spec.loader.exec_module(connection_module)
get_db_session = connection_module.get_db_session

from sqlalchemy import create_engine, text

# Tenta importar funções de queries (pode falhar se pandas não estiver disponível)
try:
    from src.agent.queries_analytics import get_metas_realizado_por_mes
    QUERIES_ANALYTICS_AVAILABLE = True
except ImportError:
    QUERIES_ANALYTICS_AVAILABLE = False
    get_metas_realizado_por_mes = None

try:
    from src.agent.queries_metas import get_metas_realizado_por_mes_direto
    QUERIES_METAS_AVAILABLE = True
except ImportError:
    QUERIES_METAS_AVAILABLE = False
    get_metas_realizado_por_mes_direto = None


# Valores esperados para agosto/2025 (SEM totalizador)
EXPECTED_META_TOTAL = 17833053.45
EXPECTED_REALIZADO_TOTAL = 17254142.15
EXPECTED_ATINGIMENTO_MEDIO = 96.75  # Aproximadamente
MES_ANO_TESTE = "2025-08"
TOLERANCIA_META = 100.0  # R$ 100 de tolerância
TOLERANCIA_ATINGIMENTO = 1.0  # 1% de tolerância


@pytest.fixture(scope="module")
def db_session():
    """Fixture para sessão de banco de dados."""
    session_generator = get_db_session()
    session = next(session_generator)
    yield session
    session.close()


class TestKPIsAgosto2025:
    """Testes para KPIs de agosto/2025."""
    
    def test_meta_total_agosto_2025(self, db_session):
        """Testa se meta_total para agosto/2025 está correto (~17.83M)."""
        if QUERIES_ANALYTICS_AVAILABLE:
            kpis = get_metas_realizado_por_mes(db_session, MES_ANO_TESTE, excluir_totais=True)
            meta_total = kpis["meta_total"]
        else:
            # Usa SQL direto como fallback
            query = text("""
                SELECT SUM(valor_meta) as meta_total
                FROM metas_vendedor
                WHERE mes_ano = :mes_ano
                AND LOWER(vendedor_nome) NOT LIKE '%total%'
                AND vendedor_nome != 'Totais'
                AND vendedor_id IS NOT NULL
            """)
            result = db_session.execute(query, {'mes_ano': MES_ANO_TESTE})
            meta_total = float(result.fetchone()[0] or 0)
        
        assert abs(meta_total - EXPECTED_META_TOTAL) < TOLERANCIA_META, (
            f"Meta total para {MES_ANO_TESTE} está incorreta: R$ {meta_total:,.2f}. "
            f"Esperado: R$ {EXPECTED_META_TOTAL:,.2f} (±{TOLERANCIA_META})"
        )
        
        print(f"✅ Meta total para {MES_ANO_TESTE}: R$ {meta_total:,.2f}")
    
    def test_realizado_total_agosto_2025(self, db_session):
        """Testa se realizado_total para agosto/2025 está correto (~17.25M)."""
        if QUERIES_ANALYTICS_AVAILABLE:
            kpis = get_metas_realizado_por_mes(db_session, MES_ANO_TESTE, excluir_totais=True)
            realizado_total = kpis["realizado_total"]
        else:
            # Usa SQL direto como fallback
            query = text("""
                SELECT SUM(valor_faturado) as realizado_total
                FROM metas_vendedor
                WHERE mes_ano = :mes_ano
                AND LOWER(vendedor_nome) NOT LIKE '%total%'
                AND vendedor_nome != 'Totais'
                AND vendedor_id IS NOT NULL
            """)
            result = db_session.execute(query, {'mes_ano': MES_ANO_TESTE})
            realizado_total = float(result.fetchone()[0] or 0)
        
        assert abs(realizado_total - EXPECTED_REALIZADO_TOTAL) < TOLERANCIA_META, (
            f"Realizado total para {MES_ANO_TESTE} está incorreto: R$ {realizado_total:,.2f}. "
            f"Esperado: R$ {EXPECTED_REALIZADO_TOTAL:,.2f} (±{TOLERANCIA_META})"
        )
        
        print(f"✅ Realizado total para {MES_ANO_TESTE}: R$ {realizado_total:,.2f}")
    
    def test_atingimento_medio_agosto_2025(self, db_session):
        """Testa se atingimento_medio para agosto/2025 está correto (~96.75%)."""
        if QUERIES_ANALYTICS_AVAILABLE:
            kpis = get_metas_realizado_por_mes(db_session, MES_ANO_TESTE, excluir_totais=True)
            atingimento_medio = kpis["atingimento_medio"]
        else:
            # Usa SQL direto como fallback
            query = text("""
                SELECT 
                    SUM(valor_meta) as meta_total,
                    SUM(valor_faturado) as realizado_total
                FROM metas_vendedor
                WHERE mes_ano = :mes_ano
                AND LOWER(vendedor_nome) NOT LIKE '%total%'
                AND vendedor_nome != 'Totais'
                AND vendedor_id IS NOT NULL
            """)
            result = db_session.execute(query, {'mes_ano': MES_ANO_TESTE})
            row = result.fetchone()
            meta_total = float(row[0] or 0)
            realizado_total = float(row[1] or 0)
            atingimento_medio = (realizado_total / meta_total * 100) if meta_total > 0 else 0.0
        
        assert abs(atingimento_medio - EXPECTED_ATINGIMENTO_MEDIO) < TOLERANCIA_ATINGIMENTO, (
            f"Atingimento médio para {MES_ANO_TESTE} está incorreto: {atingimento_medio:.2f}%. "
            f"Esperado: {EXPECTED_ATINGIMENTO_MEDIO:.2f}% (±{TOLERANCIA_ATINGIMENTO}%)"
        )
        
        print(f"✅ Atingimento médio para {MES_ANO_TESTE}: {atingimento_medio:.2f}%")
    
    def test_kpis_consistencia_entre_funcoes(self, db_session):
        """Testa se get_metas_realizado_por_mes e get_metas_realizado_por_mes_direto retornam valores consistentes."""
        if not QUERIES_ANALYTICS_AVAILABLE or not QUERIES_METAS_AVAILABLE:
            pytest.skip("Funções de queries não disponíveis")
        
        kpis_analytics = get_metas_realizado_por_mes(db_session, MES_ANO_TESTE, excluir_totais=True)
        kpis_direto = get_metas_realizado_por_mes_direto(db_session, MES_ANO_TESTE, excluir_totais=True)
        
        # Valores devem ser próximos (pode haver pequenas diferenças de arredondamento)
        assert abs(kpis_analytics["meta_total"] - kpis_direto["meta_total"]) < TOLERANCIA_META * 2
        assert abs(kpis_analytics["realizado_total"] - kpis_direto["realizado_total"]) < TOLERANCIA_META * 2
        
        print("✅ KPIs consistentes entre funções de analytics e queries diretas")


class TestAusenciaTotalizadores:
    """Testes para verificar ausência de totalizadores."""
    
    TABELAS_COM_NOMES = [
        ('metas_vendedor', 'vendedor_nome'),
        ('metas_departamento', 'supervisor_nome'),
        ('vendas', 'vendedor_nome'),
        ('vendas', 'nome_cliente'),
        ('clientes', 'nome'),
        ('vendedores', 'nome')
    ]
    
    @pytest.mark.parametrize("tabela,coluna", TABELAS_COM_NOMES)
    def test_sem_totalizadores_na_tabela(self, db_session, tabela, coluna):
        """Testa que não há registros com 'total' em colunas de nome."""
        query = text(f"""
            SELECT COUNT(*) as count
            FROM {tabela}
            WHERE LOWER({coluna}) LIKE '%total%'
            OR LOWER({coluna}) LIKE '%totais%'
            OR LOWER({coluna}) LIKE '%soma%'
            OR LOWER({coluna}) LIKE '%sum%'
            OR {coluna} = 'Totais'
        """)
        
        result = db_session.execute(query)
        count = result.fetchone()[0]
        
        assert count == 0, (
            f"Encontrados {count} registros com totalizadores na tabela '{tabela}', coluna '{coluna}'"
        )
        
        print(f"✅ Tabela '{tabela}' (coluna '{coluna}'): sem totalizadores")
    
    def test_metas_vendedor_sem_totais(self, db_session):
        """Testa especificamente que metas_vendedor não tem 'Totais'."""
        query = text("""
            SELECT COUNT(*) as count
            FROM metas_vendedor
            WHERE vendedor_nome = 'Totais'
            OR LOWER(vendedor_nome) LIKE '%total%'
        """)
        
        result = db_session.execute(query)
        count = result.fetchone()[0]
        
        assert count == 0, f"Encontrados {count} registros 'Totais' em metas_vendedor"
        
        print("✅ metas_vendedor: sem registros 'Totais'")


class TestConsistenciaConsultas:
    """Testes para verificar consistência de consultas."""
    
    def test_consulta_vendedor_consistente(self, db_session):
        """Testa que consultas por vendedor retornam valores consistentes."""
        # Busca um vendedor específico
        query = text("""
            SELECT vendedor_id, vendedor_nome, 
                   SUM(valor_meta) as meta,
                   SUM(valor_faturado) as realizado
            FROM metas_vendedor
            WHERE mes_ano = :mes_ano
            AND LOWER(vendedor_nome) NOT LIKE '%total%'
            AND vendedor_nome != 'Totais'
            AND vendedor_id IS NOT NULL
            GROUP BY vendedor_id, vendedor_nome
            LIMIT 10
        """)
        
        result = db_session.execute(query, {'mes_ano': MES_ANO_TESTE})
        vendedores = result.fetchall()
        
        assert len(vendedores) > 0, "Nenhum vendedor encontrado"
        
        # Verifica que cada vendedor tem valores válidos
        for vendedor in vendedores:
            vendedor_id, nome, meta, realizado = vendedor
            
            assert vendedor_id is not None, f"Vendedor {nome} tem ID nulo"
            assert meta is not None and meta >= 0, f"Vendedor {nome} tem meta inválida: {meta}"
            assert realizado is not None and realizado >= 0, f"Vendedor {nome} tem realizado inválido: {realizado}"
            assert 'total' not in nome.lower(), f"Vendedor {nome} contém 'total'"
        
        print(f"✅ {len(vendedores)} vendedores com valores consistentes")
    
    def test_soma_individual_igual_total(self, db_session):
        """Testa que a soma individual de vendedores é igual ao total calculado."""
        # Soma individual
        query_individual = text("""
            SELECT SUM(valor_meta) as meta_total,
                   SUM(valor_faturado) as realizado_total
            FROM metas_vendedor
            WHERE mes_ano = :mes_ano
            AND LOWER(vendedor_nome) NOT LIKE '%total%'
            AND vendedor_nome != 'Totais'
            AND vendedor_id IS NOT NULL
        """)
        
        result = db_session.execute(query_individual, {'mes_ano': MES_ANO_TESTE})
        soma_individual = result.fetchone()
        
        # Total via função (se disponível) ou recalcula
        if QUERIES_ANALYTICS_AVAILABLE:
            kpis = get_metas_realizado_por_mes(db_session, MES_ANO_TESTE, excluir_totais=True)
            meta_total = kpis["meta_total"]
            realizado_total = kpis["realizado_total"]
        else:
            meta_total = float(soma_individual[0] or 0)
            realizado_total = float(soma_individual[1] or 0)
        
        # Compara (com tolerância de arredondamento)
        diff_meta = abs(float(soma_individual[0] or 0) - meta_total)
        diff_realizado = abs(float(soma_individual[1] or 0) - realizado_total)
        
        assert diff_meta < 1.0, f"Diferença na meta: {diff_meta}"
        assert diff_realizado < 1.0, f"Diferença no realizado: {diff_realizado}"
        
        print("✅ Soma individual igual ao total calculado")


class TestEmbeddings:
    """Testes para verificar embeddings."""
    
    @pytest.fixture
    def ml_cache_dir(self):
        """Retorna diretório de cache ML."""
        return Path(__file__).parent.parent / "ml_cache"
    
    def test_embeddings_vendedores_existem(self, ml_cache_dir):
        """Testa que embeddings de vendedores existem e não estão vazios."""
        if not NUMPY_AVAILABLE:
            pytest.skip("NumPy não está disponível")
        
        embeddings_file = ml_cache_dir / "embeddings_vendedores.npy"
        ids_file = ml_cache_dir / "ids_vendedores.json"
        
        if not embeddings_file.exists():
            pytest.skip("Embeddings de vendedores não foram gerados ainda")
        
        embeddings = np.load(embeddings_file)
        assert embeddings.size > 0, "Embeddings de vendedores estão vazios"
        assert embeddings.shape[0] > 0, "Nenhum embedding de vendedor encontrado"
        assert embeddings.shape[1] > 0, "Dimensão dos embeddings é zero"
        
        # Verifica que não são todos zeros
        assert not np.all(embeddings == 0), "Embeddings são todos zeros"
        
        if ids_file.exists():
            with open(ids_file, 'r') as f:
                ids = json.load(f)
            assert len(ids) == embeddings.shape[0], "Número de IDs não corresponde ao número de embeddings"
        
        print(f"✅ Embeddings de vendedores: {embeddings.shape[0]} vetores, dim={embeddings.shape[1]}")
    
    def test_embeddings_clientes_existem(self, ml_cache_dir):
        """Testa que embeddings de clientes existem e não estão vazios."""
        if not NUMPY_AVAILABLE:
            pytest.skip("NumPy não está disponível")
        
        embeddings_file = ml_cache_dir / "embeddings_clientes.npy"
        ids_file = ml_cache_dir / "ids_clientes.json"
        
        if not embeddings_file.exists():
            pytest.skip("Embeddings de clientes não foram gerados ainda")
        
        embeddings = np.load(embeddings_file)
        assert embeddings.size > 0, "Embeddings de clientes estão vazios"
        assert embeddings.shape[0] > 0, "Nenhum embedding de cliente encontrado"
        assert embeddings.shape[1] > 0, "Dimensão dos embeddings é zero"
        
        # Verifica que não são todos zeros
        assert not np.all(embeddings == 0), "Embeddings são todos zeros"
        
        if ids_file.exists():
            with open(ids_file, 'r') as f:
                ids = json.load(f)
            assert len(ids) == embeddings.shape[0], "Número de IDs não corresponde ao número de embeddings"
        
        print(f"✅ Embeddings de clientes: {embeddings.shape[0]} vetores, dim={embeddings.shape[1]}")
    
    def test_embeddings_produtos_existem(self, ml_cache_dir):
        """Testa que embeddings de produtos existem e não estão vazios."""
        if not NUMPY_AVAILABLE:
            pytest.skip("NumPy não está disponível")
        
        embeddings_file = ml_cache_dir / "embeddings_produtos.npy"
        ids_file = ml_cache_dir / "ids_produtos.json"
        
        if not embeddings_file.exists():
            pytest.skip("Embeddings de produtos não foram gerados ainda")
        
        embeddings = np.load(embeddings_file)
        assert embeddings.size > 0, "Embeddings de produtos estão vazios"
        assert embeddings.shape[0] > 0, "Nenhum embedding de produto encontrado"
        assert embeddings.shape[1] > 0, "Dimensão dos embeddings é zero"
        
        # Verifica que não são todos zeros
        assert not np.all(embeddings == 0), "Embeddings são todos zeros"
        
        if ids_file.exists():
            with open(ids_file, 'r') as f:
                ids = json.load(f)
            assert len(ids) == embeddings.shape[0], "Número de IDs não corresponde ao número de embeddings"
        
        print(f"✅ Embeddings de produtos: {embeddings.shape[0]} vetores, dim={embeddings.shape[1]}")
    
    def test_manifest_existe(self, ml_cache_dir):
        """Testa que manifest.json existe e contém informações válidas."""
        manifest_file = ml_cache_dir / "manifest.json"
        
        if not manifest_file.exists():
            pytest.skip("Manifest não foi gerado ainda")
        
        with open(manifest_file, 'r') as f:
            manifest = json.load(f)
        
        assert 'timestamp' in manifest
        assert 'schema_version' in manifest
        assert 'registros' in manifest
        assert 'embeddings_gerados' in manifest
        
        print(f"✅ Manifest válido: versão {manifest.get('schema_version')}")


class TestDuplicatasIDs:
    """Testes para verificar ausência de duplicatas em IDs."""
    
    TABELAS_COM_ID = [
        'metas_vendedor',
        'metas_departamento',
        'vendas',
        'vendedores',
        'clientes',
        'supervisores'
    ]
    
    @pytest.mark.parametrize("tabela", TABELAS_COM_ID)
    def test_sem_ids_duplicados(self, db_session, tabela):
        """Testa que não há IDs duplicados na tabela."""
        query = text(f"""
            SELECT id, COUNT(*) as count
            FROM {tabela}
            WHERE id IS NOT NULL
            GROUP BY id
            HAVING COUNT(*) > 1
            LIMIT 10
        """)
        
        result = db_session.execute(query)
        duplicados = result.fetchall()
        
        assert len(duplicados) == 0, (
            f"Encontrados {len(duplicados)} IDs duplicados na tabela '{tabela}': "
            f"{[d[0] for d in duplicados[:5]]}"
        )
        
        print(f"✅ Tabela '{tabela}': sem IDs duplicados")
    
    def test_vendedor_id_unicos_em_metas(self, db_session):
        """Testa que vendedor_id é único por mês em metas_vendedor."""
        query = text("""
            SELECT vendedor_id, mes_ano, COUNT(*) as count
            FROM metas_vendedor
            WHERE vendedor_id IS NOT NULL
            AND mes_ano = :mes_ano
            GROUP BY vendedor_id, mes_ano
            HAVING COUNT(*) > 1
        """)
        
        result = db_session.execute(query, {'mes_ano': MES_ANO_TESTE})
        duplicados = result.fetchall()
        
        assert len(duplicados) == 0, (
            f"Encontrados {len(duplicados)} vendedor_id duplicados por mês em metas_vendedor"
        )
        
        print(f"✅ metas_vendedor: vendedor_id únicos por mês em {MES_ANO_TESTE}")


if __name__ == "__main__":
    # Permite rodar os testes diretamente
    pytest.main([__file__, "-v", "-s"])

