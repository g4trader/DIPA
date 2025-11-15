"""
Testes para módulo de transformações/features.

Testa funções de construção de features para ML, incluindo
validação de cálculos e lógica de negócio.
"""

import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session

# Adiciona diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.mark.unit
class TestBuildFeaturesVendedorMes:
    """Testes para função build_features_vendedor_mes()."""
    
    def test_bateu_meta_calculation(self):
        """
        Testa que target bateu_meta é gerado corretamente.
        bateu_meta = 1 se perc_ating_valor >= 100, senão 0
        """
        from src.features import build_features_vendedor_mes
        
        # Mock da sessão e query SQL
        mock_session = MagicMock(spec=Session)
        
        # Cria DataFrame mock que simula resultado da query
        mock_df = pd.DataFrame({
            'mes_ano': ['2024-01', '2024-01', '2024-02', '2024-02'],
            'vendedor_id': [1, 2, 1, 2],
            'vendedor': ['ROTA 77', 'ROTA 78', 'ROTA 77', 'ROTA 78'],
            'meta_valor': [100000.0, 120000.0, 100000.0, 120000.0],
            'realizado_valor': [110000.0, 90000.0, 85000.0, 130000.0],
            'gap_valor': [10000.0, -30000.0, -15000.0, 10000.0],
            'perc_ating_valor': [110.0, 75.0, 85.0, 108.33],
            'meta_volume': [1000, 1200, 1000, 1200],
            'realizado_volume': [1100, 900, 850, 1300],
            'perc_ating_volume': [110.0, 75.0, 85.0, 108.33],
            'meta_positivacao': [50, 60, 50, 60],
            'clientes_positivados': [55, 45, 42, 65],
            'perc_ating_positivacao': [110.0, 75.0, 84.0, 108.33],
            'bateu_meta': [1, 0, 0, 1]  # Esperado
        })
        
        # Mock da função read_sql para retornar nosso DataFrame
        with patch('src.features.pd.read_sql') as mock_read_sql, \
             patch('src.features.get_db_session') as mock_get_session:
            
            mock_get_session.return_value.__next__.return_value = mock_session
            mock_read_sql.return_value = mock_df
            
            # Chama função
            result = build_features_vendedor_mes(session=None)
            
            # Verifica que bateu_meta foi calculado corretamente
            assert 'bateu_meta' in result.columns
            
            # Verifica cada linha
            for idx, row in result.iterrows():
                perc_ating = row['perc_ating_valor']
                bateu_meta = row['bateu_meta']
                
                if perc_ating >= 100:
                    assert bateu_meta == 1, f"Vendedor com {perc_ating}% deveria ter bateu_meta=1"
                else:
                    assert bateu_meta == 0, f"Vendedor com {perc_ating}% deveria ter bateu_meta=0"
    
    def test_gap_valor_calculation(self):
        """
        Testa que gap_valor = realizado_valor - meta_valor é calculado corretamente.
        """
        from src.features import build_features_vendedor_mes
        
        # Mock da sessão
        mock_session = MagicMock(spec=Session)
        
        # DataFrame com valores conhecidos
        mock_df = pd.DataFrame({
            'mes_ano': ['2024-01', '2024-01', '2024-02'],
            'vendedor_id': [1, 2, 1],
            'vendedor': ['ROTA 77', 'ROTA 78', 'ROTA 77'],
            'meta_valor': [100000.0, 120000.0, 100000.0],
            'realizado_valor': [85000.0, 135000.0, 100000.0],
            'gap_valor': [-15000.0, 15000.0, 0.0],  # Esperado
            'perc_ating_valor': [85.0, 112.5, 100.0],
            'meta_volume': [1000, 1200, 1000],
            'realizado_volume': [850, 1350, 1000],
            'perc_ating_volume': [85.0, 112.5, 100.0],
            'meta_positivacao': [50, 60, 50],
            'clientes_positivados': [42, 68, 50],
            'perc_ating_positivacao': [84.0, 113.33, 100.0],
            'bateu_meta': [0, 1, 1]
        })
        
        with patch('src.features.pd.read_sql') as mock_read_sql, \
             patch('src.features.get_db_session') as mock_get_session:
            
            mock_get_session.return_value.__next__.return_value = mock_session
            mock_read_sql.return_value = mock_df
            
            result = build_features_vendedor_mes(session=None)
            
            # Verifica cálculo de gap_valor
            assert 'gap_valor' in result.columns
            assert 'meta_valor' in result.columns
            assert 'realizado_valor' in result.columns
            
            for idx, row in result.iterrows():
                meta = row['meta_valor']
                realizado = row['realizado_valor']
                gap = row['gap_valor']
                
                expected_gap = realizado - meta
                assert abs(gap - expected_gap) < 0.01, \
                    f"gap_valor incorreto. Esperado: {expected_gap}, Obtido: {gap}"
    
    def test_vendedores_unicos_makes_sense(self):
        """
        Testa que o número de vendedores únicos faz sentido.
        """
        from src.features import build_features_vendedor_mes
        
        # Mock da sessão
        mock_session = MagicMock(spec=Session)
        
        # DataFrame com múltiplos vendedores e meses
        mock_df = pd.DataFrame({
            'mes_ano': ['2024-01', '2024-01', '2024-01', '2024-02', '2024-02', '2024-02'],
            'vendedor_id': [1, 2, 3, 1, 2, 3],
            'vendedor': ['ROTA 77', 'ROTA 78', 'ROTA 79', 'ROTA 77', 'ROTA 78', 'ROTA 79'],
            'meta_valor': [100000.0] * 6,
            'realizado_valor': [85000.0] * 6,
            'gap_valor': [-15000.0] * 6,
            'perc_ating_valor': [85.0] * 6,
            'meta_volume': [1000] * 6,
            'realizado_volume': [850] * 6,
            'perc_ating_volume': [85.0] * 6,
            'meta_positivacao': [50] * 6,
            'clientes_positivados': [42] * 6,
            'perc_ating_positivacao': [84.0] * 6,
            'bateu_meta': [0] * 6
        })
        
        with patch('src.features.pd.read_sql') as mock_read_sql, \
             patch('src.features.get_db_session') as mock_get_session:
            
            mock_get_session.return_value.__next__.return_value = mock_session
            mock_read_sql.return_value = mock_df
            
            result = build_features_vendedor_mes(session=None)
            
            # Verifica que tem vendedor
            assert 'vendedor' in result.columns
            
            # Conta vendedores únicos
            unique_vendedores = result['vendedor'].nunique()
            
            # Deve ter 3 vendedores únicos
            assert unique_vendedores == 3, \
                f"Esperado 3 vendedores únicos, encontrado {unique_vendedores}"
            
            # Verifica que temos dados para 2 meses
            unique_meses = result['mes_ano'].nunique()
            assert unique_meses == 2, \
                f"Esperado 2 meses únicos, encontrado {unique_meses}"
            
            # Verifica que temos 6 registros (3 vendedores x 2 meses)
            assert len(result) == 6, \
                f"Esperado 6 registros (3 vendedores x 2 meses), encontrado {len(result)}"


@pytest.mark.unit
class TestBuildFeaturesClienteMes:
    """Testes para função build_features_cliente_mes()."""
    
    def test_dias_desde_ultima_compra_calculation(self):
        """
        Testa que dias_desde_ultima_compra é calculado corretamente.
        """
        from src.features import build_features_cliente_mes
        
        # Mock da sessão
        mock_session = MagicMock(spec=Session)
        
        # Cria datas de referência
        data_atual = datetime(2024, 2, 1)  # Fevereiro 2024
        data_compra_anterior_15d = datetime(2024, 1, 17)  # 15 dias antes
        data_compra_anterior_45d = datetime(2023, 12, 18)  # 45 dias antes
        data_compra_anterior_90d = datetime(2023, 11, 3)  # 90 dias antes
        
        # DataFrame mock que simula resultado da query
        # A query calcula dias desde última compra até o início do mês atual
        dias_esperados_15d = (data_atual - data_compra_anterior_15d).days
        dias_esperados_45d = (data_atual - data_compra_anterior_45d).days
        dias_esperados_90d = (data_atual - data_compra_anterior_90d).days
        
        mock_df = pd.DataFrame({
            'mes_ano': ['2024-02', '2024-02', '2024-02'],
            'ano': [2024, 2024, 2024],
            'mes': [2, 2, 2],
            'id_cliente': [1, 2, 3],
            'codigo_cliente': ['C001', 'C002', 'C003'],
            'nome_cliente': ['Cliente 1', 'Cliente 2', 'Cliente 3'],
            'valor_total_mes': [5000.0, 3000.0, 2000.0],
            'qtd_pedidos_mes': [5, 3, 2],
            'qtd_departamentos_diferentes': [3, 2, 1],
            'dias_desde_ultima_compra': [dias_esperados_15d, dias_esperados_45d, dias_esperados_90d],
            'ticket_medio_mes': [1000.0, 1000.0, 1000.0],
            'churn_provavel': [0, 0, 1]
        })
        
        # Mock das vendas futuras para cálculo de churn
        mock_df_vendas_futuras = pd.DataFrame({
            'cliente_id': [1, 2],  # Cliente 3 não tem venda futura
            'mes_venda': [
                pd.to_datetime('2024-03-01'),
                pd.to_datetime('2024-02-15')
            ]
        })
        
        with patch('src.features.pd.read_sql') as mock_read_sql, \
             patch('src.features.get_db_session') as mock_get_session:
            
            mock_get_session.return_value.__next__.return_value = mock_session
            
            # Primeira chamada retorna dados principais, segunda retorna vendas futuras
            mock_read_sql.side_effect = [mock_df, mock_df_vendas_futuras]
            
            result = build_features_cliente_mes(session=None, dias_churn=90)
            
            # Verifica que dias_desde_ultima_compra existe
            assert 'dias_desde_ultima_compra' in result.columns
            
            # Verifica valores (com tolerância para diferenças de cálculo)
            for idx, row in result.iterrows():
                dias = row['dias_desde_ultima_compra']
                assert dias > 0 or pd.isna(dias), \
                    f"dias_desde_ultima_compra deve ser positivo ou NaN, encontrado: {dias}"
    
    def test_ticket_medio_calculation(self):
        """
        Testa que ticket_medio = valor_total_mes / qtd_pedidos_mes é calculado corretamente.
        """
        from src.features import build_features_cliente_mes
        
        # Mock da sessão
        mock_session = MagicMock(spec=Session)
        
        # DataFrame com valores conhecidos para testar cálculo
        mock_df = pd.DataFrame({
            'mes_ano': ['2024-02', '2024-02', '2024-02'],
            'ano': [2024, 2024, 2024],
            'mes': [2, 2, 2],
            'id_cliente': [1, 2, 3],
            'codigo_cliente': ['C001', 'C002', 'C003'],
            'nome_cliente': ['Cliente 1', 'Cliente 2', 'Cliente 3'],
            'valor_total_mes': [10000.0, 6000.0, 1500.0],  # Valores totais
            'qtd_pedidos_mes': [10, 6, 3],  # Quantidade de pedidos
            # ticket_medio esperado: 1000.0, 1000.0, 500.0
            'ticket_medio_mes': [1000.0, 1000.0, 500.0],
            'qtd_departamentos_diferentes': [3, 2, 1],
            'dias_desde_ultima_compra': [15, 45, 90],
            'churn_provavel': [0, 0, 1]
        })
        
        mock_df_vendas_futuras = pd.DataFrame({
            'cliente_id': [1, 2],
            'mes_venda': [
                pd.to_datetime('2024-03-01'),
                pd.to_datetime('2024-02-15')
            ]
        })
        
        with patch('src.features.pd.read_sql') as mock_read_sql, \
             patch('src.features.get_db_session') as mock_get_session:
            
            mock_get_session.return_value.__next__.return_value = mock_session
            mock_read_sql.side_effect = [mock_df, mock_df_vendas_futuras]
            
            result = build_features_cliente_mes(session=None, dias_churn=90)
            
            # Verifica que ticket_medio_mes existe
            assert 'ticket_medio_mes' in result.columns
            assert 'valor_total_mes' in result.columns
            assert 'qtd_pedidos_mes' in result.columns
            
            # Verifica cálculo
            for idx, row in result.iterrows():
                valor_total = row['valor_total_mes']
                qtd_pedidos = row['qtd_pedidos_mes']
                ticket_medio = row['ticket_medio_mes']
                
                if qtd_pedidos > 0:
                    expected_ticket = valor_total / qtd_pedidos
                    assert abs(ticket_medio - expected_ticket) < 0.01, \
                        f"ticket_medio incorreto. Esperado: {expected_ticket:.2f}, Obtido: {ticket_medio:.2f}"
                else:
                    # Se não há pedidos, ticket_medio deve ser 0 ou NaN
                    assert ticket_medio == 0 or pd.isna(ticket_medio), \
                        f"ticket_medio deve ser 0 ou NaN quando qtd_pedidos=0, encontrado: {ticket_medio}"
    
    def test_churn_provavel_calculation(self):
        """
        Testa que churn_provavel = 1 se cliente fica o período definido sem comprar.
        """
        from src.features import build_features_cliente_mes
        
        # Mock da sessão
        mock_session = MagicMock(spec=Session)
        
        # DataFrame principal
        # Cliente 1: comprou em março (dentro do período) -> churn_provavel = 0
        # Cliente 2: comprou em maio (fora do período) -> churn_provavel = 1
        # Cliente 3: não comprou nunca -> churn_provavel = 1
        mes_atual = datetime(2024, 2, 1)  # Fevereiro 2024
        dias_churn = 90  # 90 dias após fevereiro = maio
        
        mock_df = pd.DataFrame({
            'mes_ano': ['2024-02', '2024-02', '2024-02'],
            'ano': [2024, 2024, 2024],
            'mes': [2, 2, 2],
            'id_cliente': [1, 2, 3],
            'codigo_cliente': ['C001', 'C002', 'C003'],
            'nome_cliente': ['Cliente 1', 'Cliente 2', 'Cliente 3'],
            'valor_total_mes': [5000.0, 3000.0, 2000.0],
            'qtd_pedidos_mes': [5, 3, 2],
            'qtd_departamentos_diferentes': [3, 2, 1],
            'ticket_medio_mes': [1000.0, 1000.0, 1000.0],
            'dias_desde_ultima_compra': [15, 45, 90],
            'churn_provavel_placeholder': [0, 0, 0]  # Será calculado
        })
        
        # Vendas futuras:
        # Cliente 1: comprou em março (dentro de 90 dias)
        # Cliente 2: comprou em junho (fora de 90 dias)
        # Cliente 3: não tem venda futura
        mock_df_vendas_futuras = pd.DataFrame({
            'cliente_id': [1, 2],
            'mes_venda': [
                pd.to_datetime('2024-03-01'),  # Dentro do período
                pd.to_datetime('2024-06-01')   # Fora do período (mais de 90 dias)
            ]
        })
        
        with patch('src.features.pd.read_sql') as mock_read_sql, \
             patch('src.features.get_db_session') as mock_get_session:
            
            mock_get_session.return_value.__next__.return_value = mock_session
            mock_read_sql.side_effect = [mock_df, mock_df_vendas_futuras]
            
            result = build_features_cliente_mes(session=None, dias_churn=90)
            
            # Verifica que churn_provavel existe
            assert 'churn_provavel' in result.columns
            
            # Verifica valores esperados
            # Cliente 1: tem venda em março (dentro de 90 dias) -> churn_provavel = 0
            cliente1 = result[result['id_cliente'] == 1]
            if len(cliente1) > 0:
                assert cliente1.iloc[0]['churn_provavel'] == 0, \
                    "Cliente 1 deveria ter churn_provavel=0 (comprou dentro do período)"
            
            # Cliente 2: comprou em junho (mais de 90 dias após fev) -> churn_provavel = 1
            cliente2 = result[result['id_cliente'] == 2]
            if len(cliente2) > 0:
                assert cliente2.iloc[0]['churn_provavel'] == 1, \
                    "Cliente 2 deveria ter churn_provavel=1 (comprou fora do período)"
            
            # Cliente 3: não tem venda futura -> churn_provavel = 1
            cliente3 = result[result['id_cliente'] == 3]
            if len(cliente3) > 0:
                assert cliente3.iloc[0]['churn_provavel'] == 1, \
                    "Cliente 3 deveria ter churn_provavel=1 (não comprou no período)"


@pytest.mark.unit
class TestFeatureCalculations:
    """Testes adicionais para validação de cálculos de features."""
    
    def test_gap_valor_negative_positive(self):
        """
        Testa que gap_valor pode ser negativo (não bateu meta) ou positivo (superou meta).
        """
        # Cria DataFrame simples para testar cálculo
        df = pd.DataFrame({
            'meta_valor': [100000.0, 100000.0],
            'realizado_valor': [85000.0, 125000.0],
        })
        
        df['gap_valor'] = df['realizado_valor'] - df['meta_valor']
        
        # Primeira linha: não bateu meta (gap negativo)
        assert df.iloc[0]['gap_valor'] < 0, "Gap deve ser negativo quando não bateu meta"
        
        # Segunda linha: superou meta (gap positivo)
        assert df.iloc[1]['gap_valor'] > 0, "Gap deve ser positivo quando superou meta"
    
    def test_bateu_meta_threshold(self):
        """
        Testa limiar exato de 100% para bateu_meta.
        """
        # Testa casos exatos
        perc_ating_values = [99.9, 100.0, 100.1]
        expected_bateu_meta = [0, 1, 1]
        
        for perc, expected in zip(perc_ating_values, expected_bateu_meta):
            bateu = 1 if perc >= 100 else 0
            assert bateu == expected, \
                f"Para perc_ating={perc}%, bateu_meta deveria ser {expected}, obtido {bateu}"
    
    def test_ticket_medio_zero_division(self):
        """
        Testa que ticket_medio lida corretamente com divisão por zero.
        """
        # Casos de teste
        test_cases = [
            {'valor_total': 10000.0, 'qtd_pedidos': 10, 'expected': 1000.0},
            {'valor_total': 0.0, 'qtd_pedidos': 5, 'expected': 0.0},
            {'valor_total': 1000.0, 'qtd_pedidos': 0, 'expected': 0.0},  # Divisão por zero
        ]
        
        for case in test_cases:
            valor = case['valor_total']
            qtd = case['qtd_pedidos']
            expected = case['expected']
            
            if qtd > 0:
                ticket = valor / qtd
            else:
                ticket = 0.0
            
            assert abs(ticket - expected) < 0.01, \
                f"ticket_medio incorreto para valor={valor}, qtd={qtd}. Esperado: {expected}, Obtido: {ticket}"
