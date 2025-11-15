"""
Teste de integração completo do pipeline end-to-end.

Este teste valida todo o pipeline de dados:
1. Ingestão de CSVs
2. Construção de features
3. Treinamento de modelos

Valida que:
- Tabelas do banco estão preenchidas
- Modelos foram gerados
- Features não estão vazias
- Pipeline roda sem erros

Este teste é crítico para CI/CD.
"""

import pytest
import sys
import pandas as pd
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
from sqlalchemy import inspect, create_engine
from sqlalchemy.orm import Session

# Adiciona diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import config
from src.dw.connection import init_db, get_db_engine, create_tables, get_db_session
from src.dw.models import (
    Base, Cliente, Vendedor, Supervisor, Venda, MetaVendedor, MetaDepartamento
)


@pytest.fixture
def temp_data_raw_dir():
    """Fixture que cria diretório temporário para data_raw/."""
    temp_dir = tempfile.mkdtemp()
    data_raw_dir = Path(temp_dir) / "data_raw"
    data_raw_dir.mkdir(parents=True)
    
    yield data_raw_dir
    
    # Limpa após teste
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def temp_models_dir():
    """Fixture que cria diretório temporário para models/."""
    temp_dir = tempfile.mkdtemp()
    models_dir = Path(temp_dir) / "artefacts"
    models_dir.mkdir(parents=True)
    
    yield models_dir
    
    # Limpa após teste
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def temp_data_processed_dir():
    """Fixture que cria diretório temporário para data_processed/."""
    temp_dir = tempfile.mkdtemp()
    data_processed_dir = Path(temp_dir)
    data_processed_dir.mkdir(parents=True)
    
    yield data_processed_dir
    
    # Limpa após teste
    shutil.rmtree(temp_dir, ignore_errors=True)


def create_minimal_clientes_csv(filepath: Path):
    """Cria CSV minimalista de clientes."""
    df = pd.DataFrame({
        'CNPJ/CPF': ['12.345.678/0001-90', '98.765.432/0001-10'],
        'Código': ['C001', 'C002'],
        'Fantasia': ['Fantasia A', 'Fantasia B'],
        'Cliente': ['Cliente A', 'Cliente B'],
        'Estado': ['SP', 'RJ'],
        'Município': ['São Paulo', 'Rio de Janeiro'],
        'Região Administrativa': ['Região 1', 'Região 2'],
        'Nome RCA': ['ROTA 77', 'ROTA 78'],
        'Rota RCA': ['ROTA 77', 'ROTA 78'],
        'Consumidor Final': ['Sim', 'Não'],
        'Bloqueio?': ['Não', 'Não']
    })
    df.to_csv(filepath, index=False, encoding='utf-8')


def create_minimal_vendas_csv(filepath: Path, periodo: str = "2024-12"):
    """Cria CSV minimalista de vendas."""
    df = pd.DataFrame({
        'Data': ['01/12/2024', '02/12/2024', '03/12/2024', '04/12/2024'],
        'Gerente': ['Gerente A', 'Gerente A', 'Gerente B', 'Gerente B'],
        'Supervisor': ['Supervisor A', 'Supervisor A', 'Supervisor B', 'Supervisor B'],
        'Vendedor': ['ROTA 77', 'ROTA 77', 'ROTA 78', 'ROTA 78'],
        'Número NF': ['NF001', 'NF002', 'NF003', 'NF004'],
        'Código Cliente': ['C001', 'C001', 'C002', 'C002'],
        'Nome Cliente': ['Cliente A', 'Cliente A', 'Cliente B', 'Cliente B'],
        'CGC/CPF': ['12.345.678/0001-90', '12.345.678/0001-90', '98.765.432/0001-10', '98.765.432/0001-10'],
        'Código Produto': ['P001', 'P002', 'P001', 'P003'],
        'Desc Produto': ['Produto 1', 'Produto 2', 'Produto 1', 'Produto 3'],
        'Departamento': ['Depto A', 'Depto A', 'Depto B', 'Depto B'],
        'Valor Total Líquido': ['R$ 1.000,00', 'R$ 1.500,00', 'R$ 2.000,00', 'R$ 2.500,00'],
        'Vlr.Desconto': ['R$ 100,00', 'R$ 150,00', 'R$ 200,00', 'R$ 250,00'],
        'Qtd Caixas': [10, 15, 20, 25],
        'Qtd Unidades': [100, 150, 200, 250]
    })
    df.to_csv(filepath, index=False, encoding='utf-8')


def create_minimal_metas_vendedor_csv(filepath: Path, mes_ano: str = "2024-12"):
    """Cria CSV minimalista de metas de vendedor."""
    df = pd.DataFrame({
        'Vendedor': ['ROTA 77', 'ROTA 78'],
        'Valor Meta': ['R$ 100.000,00', 'R$ 120.000,00'],
        'Vl. Faturado': ['R$ 85.000,00', 'R$ 135.000,00'],
        'Vl. Parado': ['R$ 0,00', 'R$ 0,00'],
        '% Ating': ['85,0%', '112,5%'],
        'Qtd Meta': [1000, 1200],
        'Qtd Cx Faturado': [850, 1350],
        'Qtd Cx Paradas': [0, 0],
        '% Vol Ating': ['85,0%', '112,5%'],
        'Meta Pos': [50, 60],
        'Cl. Pos.': [42, 68],
        '% Ating.1': ['84,0%', '113,3%']
    })
    df.to_csv(filepath, index=False, encoding='utf-8')


def create_minimal_metas_departamento_csv(filepath: Path, mes_ano: str = "2024-12"):
    """Cria CSV minimalista de metas de departamento."""
    df = pd.DataFrame({
        'Departamento': ['Depto A', 'Depto B'],
        'Valor Meta': ['R$ 200.000,00', 'R$ 250.000,00'],
        'Vl. Faturado': ['R$ 180.000,00', 'R$ 280.000,00'],
        '% Ating': ['90,0%', '112,0%'],
        'Qtd Meta': [2000, 2500],
        'Qtd Cx Faturado': [1800, 2800],
        'Meta Pos': [100, 120],
        'Cl. Pos.': [90, 135]
    })
    df.to_csv(filepath, index=False, encoding='utf-8')


@pytest.fixture
def sample_csvs(temp_data_raw_dir):
    """Fixture que cria CSVs minimalistas."""
    # Clientes
    clientes_file = temp_data_raw_dir / "Clientes ativos.csv"
    create_minimal_clientes_csv(clientes_file)
    
    # Vendas
    vendas_file = temp_data_raw_dir / "Detalhes de vendas - Dez 2024.csv"
    create_minimal_vendas_csv(vendas_file, "2024-12")
    
    # Metas Vendedor
    metas_vendedor_file = temp_data_raw_dir / "Metas X Realizado Vendedor - Dezembro24.csv"
    create_minimal_metas_vendedor_csv(metas_vendedor_file, "2024-12")
    
    # Metas Departamento
    metas_dept_file = temp_data_raw_dir / "Metas X Realizado Departamento - dezembro24.csv"
    create_minimal_metas_departamento_csv(metas_dept_file, "2024-12")
    
    return temp_data_raw_dir


@pytest.fixture
def temp_database():
    """Fixture que cria banco de dados temporário."""
    # Cria banco SQLite em memória ou arquivo temporário
    db_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    db_path = db_file.name
    db_file.close()
    
    # Configura conexão temporária
    original_db_type = config.database.db_type
    original_sqlite_path = config.database.sqlite_path
    
    # Atualiza config para usar banco temporário
    config.database.db_type = "sqlite"
    config.database.sqlite_path = db_path
    
    try:
        # Inicializa banco
        init_db()
        create_tables()
        
        yield db_path
        
    finally:
        # Restaura config original
        config.database.db_type = original_db_type
        config.database.sqlite_path = original_sqlite_path
        
        # Remove banco temporário
        try:
            Path(db_path).unlink(missing_ok=True)
        except:
            pass


@pytest.mark.integration
@pytest.mark.slow
class TestFullPipeline:
    """Testes de integração completa do pipeline end-to-end."""
    
    def test_full_pipeline_end_to_end(
        self,
        sample_csvs,
        temp_database,
        temp_models_dir,
        temp_data_processed_dir
    ):
        """
        Testa pipeline completo end-to-end:
        1. Ingestão de CSVs
        2. Construção de features
        3. Treinamento de modelos
        """
        # 1. Configura paths temporários
        original_data_raw = config.paths.data_raw_dir
        original_models = config.ml.models_dir
        original_data_processed = config.paths.data_processed_dir
        
        config.paths.data_raw_dir = sample_csvs
        config.ml.models_dir = temp_models_dir.parent
        config.paths.data_processed_dir = temp_data_processed_dir
        
        try:
            # 2. Executa ingestão
            print("\n" + "="*60)
            print("ETAPA 1: Ingestão de Dados")
            print("="*60)
            
            from src.run_ingestion import run_ingestion_pipeline
            
            try:
                # Executa pipeline de ingestão e captura exit code
                import sys
                from io import StringIO
                
                # Redireciona stdout temporariamente para capturar output
                old_stdout = sys.stdout
                sys.stdout = StringIO()
                
                try:
                    exit_code = run_ingestion_pipeline()
                finally:
                    output = sys.stdout.getvalue()
                    sys.stdout = old_stdout
                    if output:
                        print(output)
                
                # Valida que ingestão foi bem-sucedida
                assert exit_code == 0, "Ingestão deveria terminar sem erros"
                
                # Valida que dados foram inseridos no banco
                session_context = get_db_session()
                session = next(session_context)
                
                try:
                    # Verifica clientes
                    count_clientes = session.query(Cliente).count()
                    assert count_clientes > 0, \
                        f"Deveria ter clientes no banco, encontrado: {count_clientes}"
                    print(f"✓ Clientes inseridos: {count_clientes}")
                    
                    # Verifica vendas
                    count_vendas = session.query(Venda).count()
                    assert count_vendas > 0, \
                        f"Deveria ter vendas no banco, encontrado: {count_vendas}"
                    print(f"✓ Vendas inseridas: {count_vendas}")
                    
                    # Verifica metas vendedor
                    count_metas_vendedor = session.query(MetaVendedor).count()
                    assert count_metas_vendedor > 0, \
                        f"Deveria ter metas de vendedor no banco, encontrado: {count_metas_vendedor}"
                    print(f"✓ Metas de vendedor inseridas: {count_metas_vendedor}")
                    
                    # Verifica metas departamento
                    count_metas_dept = session.query(MetaDepartamento).count()
                    assert count_metas_dept > 0, \
                        f"Deveria ter metas de departamento no banco, encontrado: {count_metas_dept}"
                    print(f"✓ Metas de departamento inseridas: {count_metas_dept}")
                
                finally:
                    session.close()
            
            except Exception as e:
                pytest.fail(f"Ingestão falhou: {str(e)}")
            
            # 3. Executa construção de features
            print("\n" + "="*60)
            print("ETAPA 2: Construção de Features")
            print("="*60)
            
            from src.run_build_features import run_build_features_pipeline
            
            try:
                df_vendedor, df_cliente = run_build_features_pipeline(
                    start_mes_ano=None,
                    end_mes_ano=None,
                    dias_churn=90,
                    save_files=True
                )
                
                # Valida que features foram construídas
                assert df_vendedor is not None, "Features de vendedor não deveriam ser None"
                assert df_cliente is not None, "Features de cliente não deveriam ser None"
                assert len(df_vendedor) > 0, \
                    f"Features de vendedor não deveriam estar vazias, encontrado: {len(df_vendedor)}"
                assert len(df_cliente) > 0, \
                    f"Features de cliente não deveriam estar vazias, encontrado: {len(df_cliente)}"
                
                print(f"✓ Features de vendedor: {len(df_vendedor)} registros")
                print(f"✓ Features de cliente: {len(df_cliente)} registros")
                
                # Verifica que arquivos foram salvos
                features_vendedor_file = temp_data_processed_dir / "features_vendedor.csv"
                features_cliente_file = temp_data_processed_dir / "features_cliente.csv"
                
                assert features_vendedor_file.exists(), \
                    f"Arquivo de features de vendedor deveria existir: {features_vendedor_file}"
                assert features_cliente_file.exists(), \
                    f"Arquivo de features de cliente deveria existir: {features_cliente_file}"
                
                # Valida estrutura dos DataFrames
                assert 'bateu_meta' in df_vendedor.columns, \
                    "Features de vendedor deveriam ter coluna 'bateu_meta'"
                assert 'churn_provavel' in df_cliente.columns, \
                    "Features de cliente deveriam ter coluna 'churn_provavel'"
                
                print(f"✓ Arquivos de features salvos corretamente")
            
            except Exception as e:
                pytest.fail(f"Construção de features falhou: {str(e)}")
            
            # 4. Executa treinamento de modelos
            print("\n" + "="*60)
            print("ETAPA 3: Treinamento de Modelos")
            print("="*60)
            
            from src.run_train_models import run_train_models_pipeline
            
            try:
                exit_code = run_train_models_pipeline(
                    meta_model_type='logistic_regression',  # Mais rápido para testes
                    churn_model_type='logistic_regression',  # Mais rápido para testes
                    test_size=0.3,
                    temporal_split=True,
                    dias_churn=90
                )
                
                # Valida que treinamento foi bem-sucedido
                assert exit_code == 0, "Treinamento deveria terminar sem erros"
                
                # Verifica que modelos foram salvos
                model_files = list(temp_models_dir.glob("*.joblib"))
                assert len(model_files) > 0, \
                    f"Deveria ter modelos salvos, encontrado: {len(model_files)} arquivos"
                
                print(f"✓ Modelos salvos: {len(model_files)} arquivos")
                
                # Verifica metadados
                metadata_files = list(temp_models_dir.glob("*.json"))
                assert len(metadata_files) > 0, \
                    f"Deveria ter metadados salvos, encontrado: {len(metadata_files)} arquivos"
                
                print(f"✓ Metadados salvos: {len(metadata_files)} arquivos")
                
                # Valida que modelos podem ser carregados
                from src.models_ml import MetaModel, ChurnModel
                
                meta_model_files = [f for f in model_files if "meta_model" in f.name]
                if meta_model_files:
                    model = MetaModel(model_type='logistic_regression')
                    model.load(str(meta_model_files[0]))
                    assert model.is_trained, "Modelo carregado deveria estar treinado"
                    print(f"✓ Modelo de meta carregado e válido")
                
                churn_model_files = [f for f in model_files if "churn_model" in f.name]
                if churn_model_files:
                    model = ChurnModel(model_type='logistic_regression')
                    model.load(str(churn_model_files[0]))
                    assert model.is_trained, "Modelo carregado deveria estar treinado"
                    print(f"✓ Modelo de churn carregado e válido")
            
            except Exception as e:
                pytest.fail(f"Treinamento de modelos falhou: {str(e)}")
            
            print("\n" + "="*60)
            print("PIPELINE COMPLETO: TODAS AS ETAPAS CONCLUÍDAS COM SUCESSO")
            print("="*60)
            
            # Validações finais
            self._validate_final_state(temp_database, temp_models_dir, temp_data_processed_dir)
        
        finally:
            # Restaura paths originais
            config.paths.data_raw_dir = original_data_raw
            config.ml.models_dir = original_models
            config.paths.data_processed_dir = original_data_processed
    
    def _validate_final_state(
        self,
        temp_database: str,
        temp_models_dir: Path,
        temp_data_processed_dir: Path
    ):
        """
        Valida estado final do pipeline.
        
        Verifica:
        - Tabelas do banco estão preenchidas
        - Modelos foram gerados
        - Features não estão vazias
        """
        print("\n" + "="*60)
        print("VALIDAÇÃO FINAL DO ESTADO")
        print("="*60)
        
        # 1. Valida banco de dados
        session_context = get_db_session()
        session = next(session_context)
        
        try:
            # Verifica que todas as tabelas principais têm dados
            tables_to_check = [
                (Cliente, "clientes"),
                (Venda, "vendas"),
                (MetaVendedor, "metas_vendedor"),
                (MetaDepartamento, "metas_departamento")
            ]
            
            for model, table_name in tables_to_check:
                count = session.query(model).count()
                assert count > 0, \
                    f"Tabela {table_name} deveria ter dados, encontrado: {count} registros"
                print(f"✓ Tabela {table_name}: {count} registros")
        
        finally:
            session.close()
        
        # 2. Valida arquivos de features
        features_vendedor_file = temp_data_processed_dir / "features_vendedor.csv"
        features_cliente_file = temp_data_processed_dir / "features_cliente.csv"
        
        if features_vendedor_file.exists():
            df_vendedor = pd.read_csv(features_vendedor_file)
            assert len(df_vendedor) > 0, "Features de vendedor não deveriam estar vazias"
            assert 'bateu_meta' in df_vendedor.columns
            print(f"✓ Features de vendedor: {len(df_vendedor)} registros no arquivo")
        
        if features_cliente_file.exists():
            df_cliente = pd.read_csv(features_cliente_file)
            assert len(df_cliente) > 0, "Features de cliente não deveriam estar vazias"
            assert 'churn_provavel' in df_cliente.columns
            print(f"✓ Features de cliente: {len(df_cliente)} registros no arquivo")
        
        # 3. Valida modelos
        model_files = list(temp_models_dir.glob("*.joblib"))
        assert len(model_files) >= 2, \
            f"Deveria ter pelo menos 2 modelos (meta e churn), encontrado: {len(model_files)}"
        
        # Verifica tamanho dos arquivos (não deveriam estar vazios)
        for model_file in model_files:
            assert model_file.stat().st_size > 0, \
                f"Arquivo de modelo não deveria estar vazio: {model_file}"
        
        print(f"✓ Modelos gerados: {len(model_files)} arquivos")
        
        # 4. Valida metadados
        metadata_files = list(temp_models_dir.glob("*.json"))
        if metadata_files:
            import json
            for metadata_file in metadata_files:
                with open(metadata_file) as f:
                    metadata = json.load(f)
                    assert 'metrics' in metadata
                    assert 'version' in metadata
                    assert 'model_type' in metadata
            
            print(f"✓ Metadados gerados: {len(metadata_files)} arquivos")
        
        print("\n" + "="*60)
        print("TODAS AS VALIDAÇÕES PASSARAM")
        print("="*60)


@pytest.mark.integration
@pytest.mark.slow
class TestPipelineComponents:
    """Testes de componentes individuais do pipeline."""
    
    def test_ingestion_only(self, sample_csvs, temp_database):
        """Testa apenas ingestão de dados."""
        original_data_raw = config.paths.data_raw_dir
        config.paths.data_raw_dir = sample_csvs
        
        try:
            from src.run_ingestion import run_ingestion_pipeline
            
            exit_code = run_ingestion_pipeline()
            
            assert exit_code == 0
            
            # Valida que dados foram inseridos
            session_context = get_db_session()
            session = next(session_context)
            
            try:
                assert session.query(Cliente).count() > 0
                assert session.query(Venda).count() > 0
            finally:
                session.close()
        
        finally:
            config.paths.data_raw_dir = original_data_raw
    
    def test_features_only(self, temp_database, temp_data_processed_dir):
        """Testa apenas construção de features (requer dados no banco)."""
        # Primeiro insere dados mínimos no banco
        session_context = get_db_session()
        session = next(session_context)
        
        try:
            # Cria supervisor
            from src.dw.models import Supervisor
            supervisor = Supervisor(
                codigo="SUP001",
                nome="Supervisor Teste",
                ativo=True
            )
            session.add(supervisor)
            session.flush()
            
            # Cria vendedor
            vendedor = Vendedor(
                codigo="ROTA 77",
                nome="Vendedor Teste",
                supervisor_id=supervisor.id,
                ativo=True
            )
            session.add(vendedor)
            session.flush()
            
            # Cria cliente
            cliente = Cliente(
                codigo="C001",
                cnpj_cpf="12.345.678/0001-90",
                nome="Cliente Teste",
                ativo=True
            )
            session.add(cliente)
            session.flush()
            
            # Cria meta
            meta = MetaVendedor(
                vendedor_id=vendedor.id,
                ano=2024,
                mes=12,
                mes_ano="2024-12",
                valor_meta=100000.0,
                valor_faturado=85000.0,
                percentual_atingido_valor=85.0,
                qtd_meta=1000,
                qtd_cx_faturado=850,
                percentual_atingido_volume=85.0
            )
            session.add(meta)
            session.commit()
        
        finally:
            session.close()
        
        # Testa construção de features
        original_data_processed = config.paths.data_processed_dir
        config.paths.data_processed_dir = temp_data_processed_dir
        
        try:
            from src.run_build_features import run_build_features_pipeline
            
            df_vendedor, df_cliente = run_build_features_pipeline(
                save_files=True
            )
            
            assert df_vendedor is not None
            assert len(df_vendedor) > 0
        
        finally:
            config.paths.data_processed_dir = original_data_processed


@pytest.mark.integration
@pytest.mark.slow
class TestPipelineErrorHandling:
    """Testes de tratamento de erros no pipeline."""
    
    def test_ingestion_with_invalid_csv(self, temp_data_raw_dir, temp_database):
        """Testa ingestão com CSV inválido."""
        # Cria CSV malformado
        invalid_file = temp_data_raw_dir / "invalid.csv"
        invalid_file.write_text("invalid,data\ncorrupt,file")
        
        original_data_raw = config.paths.data_raw_dir
        config.paths.data_raw_dir = temp_data_raw_dir
        
        try:
            from src.run_ingestion import run_ingestion_pipeline
            
            # Deveria continuar processando outros arquivos
            exit_code = run_ingestion_pipeline()
            
            # Pode ter erro ou não, mas não deveria crashar
            assert exit_code in [0, 1]
        
        finally:
            config.paths.data_raw_dir = original_data_raw

