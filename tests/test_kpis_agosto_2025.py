"""
Testes de regressão para KPIs de agosto/2025.

Garante que os valores calculados estão corretos e não duplicados.
"""

import pytest
import sys
from pathlib import Path

# Adiciona o diretório raiz ao path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from src.dw.connection import get_db_session
from src.agent.queries_analytics import get_metas_realizado_por_mes


class TestKPIsAgosto2025:
    """Testes para garantir que os KPIs de agosto/2025 estão corretos."""
    
    @pytest.fixture
    def session(self):
        """Cria uma sessão de banco de dados."""
        session_context = get_db_session()
        session = next(session_context)
        yield session
        session.close()
    
    def test_meta_total_agosto_2025(self, session):
        """Testa se meta_total para agosto/2025 está correto (~17.83M)."""
        mes_ano = "2025-08"
        kpis = get_metas_realizado_por_mes(session, mes_ano, excluir_totais=True)
        
        meta_total = kpis["meta_total"]
        
        # Valores esperados (com tolerância de 1%)
        meta_esperada_min = 17_500_000.0
        meta_esperada_max = 18_000_000.0
        
        assert meta_esperada_min <= meta_total <= meta_esperada_max, (
            f"Meta total para {mes_ano} está incorreta: R$ {meta_total:,.2f}. "
            f"Esperado entre R$ {meta_esperada_min:,.2f} e R$ {meta_esperada_max:,.2f}"
        )
        
        print(f"✅ Meta total para {mes_ano}: R$ {meta_total:,.2f}")
    
    def test_realizado_total_agosto_2025(self, session):
        """Testa se realizado_total para agosto/2025 está correto (~17.25M)."""
        mes_ano = "2025-08"
        kpis = get_metas_realizado_por_mes(session, mes_ano, excluir_totais=True)
        
        realizado_total = kpis["realizado_total"]
        
        # Valores esperados (com tolerância de 1%)
        realizado_esperado_min = 17_000_000.0
        realizado_esperado_max = 17_500_000.0
        
        assert realizado_esperado_min <= realizado_total <= realizado_esperado_max, (
            f"Realizado total para {mes_ano} está incorreto: R$ {realizado_total:,.2f}. "
            f"Esperado entre R$ {realizado_esperado_min:,.2f} e R$ {realizado_esperado_max:,.2f}"
        )
        
        print(f"✅ Realizado total para {mes_ano}: R$ {realizado_total:,.2f}")
    
    def test_atingimento_medio_agosto_2025(self, session):
        """Testa se atingimento_medio para agosto/2025 está correto (~96.75%)."""
        mes_ano = "2025-08"
        kpis = get_metas_realizado_por_mes(session, mes_ano, excluir_totais=True)
        
        atingimento_medio = kpis["atingimento_medio"]
        
        # Valores esperados (com tolerância de 1%)
        atingimento_esperado_min = 96.0
        atingimento_esperado_max = 97.5
        
        assert atingimento_esperado_min <= atingimento_medio <= atingimento_esperado_max, (
            f"Atingimento médio para {mes_ano} está incorreto: {atingimento_medio:.2f}%. "
            f"Esperado entre {atingimento_esperado_min:.2f}% e {atingimento_esperado_max:.2f}%"
        )
        
        print(f"✅ Atingimento médio para {mes_ano}: {atingimento_medio:.2f}%")
    
    def test_excluir_totais_previne_duplicacao(self, session):
        """Testa se excluir_totais=True previne duplicação de valores."""
        mes_ano = "2025-08"
        
        # Calcula com e sem exclusão de Totais
        kpis_com_totais = get_metas_realizado_por_mes(session, mes_ano, excluir_totais=False)
        kpis_sem_totais = get_metas_realizado_por_mes(session, mes_ano, excluir_totais=True)
        
        meta_com = kpis_com_totais["meta_total"]
        meta_sem = kpis_sem_totais["meta_total"]
        
        # Se houver linha de Totais, os valores devem ser diferentes
        # Se não houver, devem ser iguais
        # O importante é que excluir_totais=True não cause valores duplicados
        
        # Verifica que não há duplicação (valores não devem ser o dobro)
        # Se meta_sem for aproximadamente metade de meta_com, há duplicação
        if meta_com > 0:
            razao = meta_com / meta_sem if meta_sem > 0 else 0
            # Se a razão for próxima de 2, há duplicação
            assert razao < 1.5, (
                f"Possível duplicação detectada: meta_com_totais={meta_com:,.2f}, "
                f"meta_sem_totais={meta_sem:,.2f}, razão={razao:.2f}"
            )
        
        print(f"✅ Exclusão de Totais funcionando corretamente")
        print(f"   Meta com Totais: R$ {meta_com:,.2f}")
        print(f"   Meta sem Totais: R$ {meta_sem:,.2f}")
    
    def test_valores_consistentes_entre_chamadas(self, session):
        """Testa se múltiplas chamadas retornam os mesmos valores."""
        mes_ano = "2025-08"
        
        kpis1 = get_metas_realizado_por_mes(session, mes_ano, excluir_totais=True)
        kpis2 = get_metas_realizado_por_mes(session, mes_ano, excluir_totais=True)
        
        assert kpis1["meta_total"] == kpis2["meta_total"], "Meta total inconsistente entre chamadas"
        assert kpis1["realizado_total"] == kpis2["realizado_total"], "Realizado total inconsistente entre chamadas"
        assert kpis1["atingimento_medio"] == kpis2["atingimento_medio"], "Atingimento médio inconsistente entre chamadas"
        
        print("✅ Valores consistentes entre múltiplas chamadas")


if __name__ == "__main__":
    # Permite rodar os testes diretamente
    pytest.main([__file__, "-v", "-s"])

