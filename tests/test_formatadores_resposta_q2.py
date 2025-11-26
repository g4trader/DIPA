"""
Testes para formatador de resposta executiva Q2.

Testa a função formatar_resposta_q2_exec com dados de exemplo
inspirados em RESUMO_ATUALIZACAO_Q2.md.
"""

import pytest
from src.agent.formatadores_resposta import (
    formatar_resposta_q2_exec,
    formatar_resposta_q2_completa,
    formatar_valor_br,
    formatar_percentual,
    formatar_periodo_descricao,
    calcular_metricas_q2
)


class TestFormatadoresAuxiliares:
    """Testes para funções auxiliares de formatação."""
    
    def test_formatar_valor_br(self):
        """Testa formatação de valores monetários."""
        assert formatar_valor_br(843012.12) == "R$ 843.012,12"
        assert formatar_valor_br(95.5) == "R$ 95,50"
        assert formatar_valor_br(0) == "R$ 0,00"
    
    def test_formatar_percentual(self):
        """Testa formatação de percentuais."""
        assert formatar_percentual(71.48) == "71,48%"
        assert formatar_percentual(22.9) == "22,90%"
        assert formatar_percentual(100.0) == "100,00%"
    
    def test_formatar_periodo_descricao(self):
        """Testa formatação de período."""
        resultado = formatar_periodo_descricao(
            "2025-09-01",
            "2025-09-30",
            "2025-10-01",
            "2025-10-31"
        )
        assert resultado == "set/25 x out/25"
    
    def test_calcular_metricas_q2(self):
        """Testa cálculo de métricas agregadas."""
        dados = [
            {"queda_absoluta": 100.0, "queda_percentual": 10.0},
            {"queda_absoluta": 200.0, "queda_percentual": 20.0},
            {"queda_absoluta": 300.0, "queda_percentual": 30.0}
        ]
        
        metrics = calcular_metricas_q2(dados)
        
        assert metrics["total_clientes"] == 3
        assert metrics["queda_media_absoluta"] == 200.0
        assert metrics["queda_media_percentual"] == 20.0
        assert metrics["queda_maxima_absoluta"] == 300.0
        assert metrics["queda_maxima_percentual"] == 30.0
        assert metrics["queda_total_absoluta"] == 600.0


class TestFormatarRespostaQ2Exec:
    """Testes para formatação de resposta executiva Q2."""
    
    def test_formata_resposta_com_dados_completos(self):
        """Testa formatação com dados completos (top 5 clientes)."""
        # Dados baseados em RESUMO_ATUALIZACAO_Q2.md
        dados_q2 = {
            "dados_dw": {
                "dados": [
                    {
                        "cliente_id": 3318,
                        "cliente_nome": "ATACADAO DISTR COM IND LTDA LJ2",
                        "faturamento_mes_anterior": 3681404.58,
                        "faturamento_mes_atual": 2838392.46,
                        "queda_absoluta": 843012.12,
                        "queda_percentual": 22.90,
                        "rota": "ROTA 113",
                        "vendedor_nome": "ROTA 113",
                        "supervisor_nome": "Supervisor A"
                    },
                    {
                        "cliente_id": 2366,
                        "cliente_nome": "VIEZZER & CIA LTDA",
                        "faturamento_mes_anterior": 722858.49,
                        "faturamento_mes_atual": 194257.20,
                        "queda_absoluta": 528601.29,
                        "queda_percentual": 73.13,
                        "rota": "ROTA 21",
                        "vendedor_nome": "ROTA 21",
                        "supervisor_nome": "Supervisor B"
                    },
                    {
                        "cliente_id": 462,
                        "cliente_nome": "SDB COMERCIO DE ALIMENTOS LTDA",
                        "faturamento_mes_anterior": 504020.31,
                        "faturamento_mes_atual": 62583.90,
                        "queda_absoluta": 441436.41,
                        "queda_percentual": 87.58,
                        "rota": "ROTA 113",
                        "vendedor_nome": "ROTA 113",
                        "supervisor_nome": "Supervisor A"
                    },
                    {
                        "cliente_id": 3378,
                        "cliente_nome": "PEDRALLI & PEDRALLI SUPERMERCADO LTDA",
                        "faturamento_mes_anterior": 573815.91,
                        "faturamento_mes_atual": 230853.96,
                        "queda_absoluta": 342961.95,
                        "queda_percentual": 59.77,
                        "rota": "ROTA 04",
                        "vendedor_nome": "ROTA 04",
                        "supervisor_nome": "Supervisor C"
                    },
                    {
                        "cliente_id": 1476,
                        "cliente_nome": "NW DISTRIBUIDORA DE BEBIDAS LTDA EPP",
                        "faturamento_mes_anterior": 340144.74,
                        "faturamento_mes_atual": 0.0,
                        "queda_absoluta": 340144.74,
                        "queda_percentual": 100.00,
                        "rota": "ROTA 06",
                        "vendedor_nome": "ROTA 06",
                        "supervisor_nome": "Supervisor D"
                    }
                ],
                "metrics": {
                    "total_clientes_queda": 2326,
                    "queda_media_absoluta": 95374.42,
                    "queda_media_percentual": 71.48,
                    "queda_maxima_absoluta": 843012.12,
                    "queda_maxima_percentual": 184.32
                },
                "total_com_faturamento_mes_anterior": 4061
            },
            "periodo": {
                "data_ini_mes_anterior": "2025-09-01",
                "data_fim_mes_anterior": "2025-09-30",
                "data_ini_mes_atual": "2025-10-01",
                "data_fim_mes_atual": "2025-10-31"
            }
        }
        
        texto = formatar_resposta_q2_exec(dados_q2)
        
        # Verifica que menciona os números principais
        # O total de clientes deve vir das métricas (2326), não da lista (5)
        assert "2326" in texto or "2.326" in texto
        assert "R$ 843.012,12" in texto or "843.012" in texto
        assert "71,48%" in texto or "71.48%" in texto
        # Percentual de clientes com queda: 2326 / 4061 = 57,3%
        assert "57,3%" in texto or "57.3%" in texto or "57%" in texto
        
        # Verifica que menciona os 5 clientes
        assert "ATACADAO DISTR COM IND LTDA LJ2" in texto
        assert "VIEZZER & CIA LTDA" in texto
        assert "SDB COMERCIO DE ALIMENTOS LTDA" in texto
        assert "PEDRALLI & PEDRALLI SUPERMERCADO LTDA" in texto
        assert "NW DISTRIBUIDORA DE BEBIDAS LTDA EPP" in texto
        
        # Verifica que contém recomendação
        assert "Recomenda" in texto or "recomenda" in texto
        assert "ação" in texto or "contato" in texto
        
        # Verifica que menciona rotas
        assert "ROTA" in texto or "rota" in texto
    
    def test_formata_resposta_com_menos_de_5_clientes(self):
        """Testa que funciona mesmo com menos de 5 clientes."""
        dados_q2 = {
            "dados_dw": {
                "dados": [
                    {
                        "cliente_id": 3318,
                        "cliente_nome": "ATACADAO DISTR COM IND LTDA LJ2",
                        "faturamento_mes_anterior": 3681404.58,
                        "faturamento_mes_atual": 2838392.46,
                        "queda_absoluta": 843012.12,
                        "queda_percentual": 22.90,
                        "rota": "ROTA 113"
                    }
                ],
                "metrics": {
                    "total_clientes_queda": 1,
                    "queda_media_absoluta": 843012.12,
                    "queda_media_percentual": 22.90,
                    "queda_maxima_absoluta": 843012.12,
                    "queda_maxima_percentual": 22.90
                }
            },
            "periodo": {
                "data_ini_mes_anterior": "2025-09-01",
                "data_fim_mes_anterior": "2025-09-30",
                "data_ini_mes_atual": "2025-10-01",
                "data_fim_mes_atual": "2025-10-31"
            }
        }
        
        texto = formatar_resposta_q2_exec(dados_q2)
        
        # Não deve quebrar
        assert len(texto) > 0
        assert "ATACADAO" in texto
        assert "Recomenda" in texto or "recomenda" in texto
    
    def test_formata_resposta_sem_dados(self):
        """Testa que funciona mesmo sem dados."""
        dados_q2 = {
            "dados_dw": {
                "dados": [],
                "metrics": {
                    "total_clientes_queda": 0,
                    "queda_media_absoluta": 0.0,
                    "queda_media_percentual": 0.0,
                    "queda_maxima_absoluta": 0.0,
                    "queda_maxima_percentual": 0.0
                }
            },
            "periodo": {
                "data_ini_mes_anterior": "2025-09-01",
                "data_fim_mes_anterior": "2025-09-30",
                "data_ini_mes_atual": "2025-10-01",
                "data_fim_mes_atual": "2025-10-31"
            }
        }
        
        texto = formatar_resposta_q2_exec(dados_q2)
        
        # Deve retornar texto mesmo sem dados
        assert len(texto) > 0
        assert "não foram identificados" in texto.lower() or "0" in texto
    
    def test_texto_nao_contem_jargoes_tecnicos(self):
        """Testa que o texto não contém jargões técnicos."""
        dados_q2 = {
            "dados_dw": {
                "dados": [
                    {
                        "cliente_id": 3318,
                        "cliente_nome": "ATACADAO DISTR COM IND LTDA LJ2",
                        "queda_absoluta": 843012.12,
                        "queda_percentual": 22.90,
                        "rota": "ROTA 113"
                    }
                ],
                "metrics": {
                    "total_clientes_queda": 1,
                    "queda_media_absoluta": 843012.12,
                    "queda_media_percentual": 22.90,
                    "queda_maxima_absoluta": 843012.12,
                    "queda_maxima_percentual": 22.90
                }
            },
            "periodo": {
                "data_ini_mes_anterior": "2025-09-01",
                "data_fim_mes_anterior": "2025-09-30",
                "data_ini_mes_atual": "2025-10-01",
                "data_fim_mes_atual": "2025-10-31"
            }
        }
        
        texto = formatar_resposta_q2_exec(dados_q2).lower()
        
        # Não deve conter jargões técnicos
        assert "query" not in texto
        assert "dw" not in texto
        assert "data warehouse" not in texto
        assert "sql" not in texto
        assert "database" not in texto


class TestFormatarRespostaQ2Completa:
    """Testes para formatação completa Q2."""
    
    def test_retorna_estrutura_completa(self):
        """Testa que retorna estrutura completa com texto e dados."""
        dados_q2 = {
            "dados_dw": {
                "dados": [
                    {
                        "cliente_id": 3318,
                        "cliente_nome": "ATACADAO DISTR COM IND LTDA LJ2",
                        "queda_absoluta": 843012.12,
                        "queda_percentual": 22.90,
                        "rota": "ROTA 113"
                    }
                ],
                "metrics": {
                    "total_clientes_queda": 1,
                    "queda_media_absoluta": 843012.12,
                    "queda_media_percentual": 22.90,
                    "queda_maxima_absoluta": 843012.12,
                    "queda_maxima_percentual": 22.90
                }
            },
            "periodo": {
                "data_ini_mes_anterior": "2025-09-01",
                "data_fim_mes_anterior": "2025-09-30",
                "data_ini_mes_atual": "2025-10-01",
                "data_fim_mes_atual": "2025-10-31"
            }
        }
        
        resultado = formatar_resposta_q2_completa(dados_q2, incluir_dados_estruturados=True)
        
        assert resultado["tipo"] == "Q2_QUEDA_FATURAMENTO"
        assert "texto_executivo" in resultado
        assert "periodo" in resultado
        assert "dados" in resultado
        assert len(resultado["texto_executivo"]) > 0

