"""
Testes para garantir que queries de metas_vendedor excluem totalizadores.
"""
import sys
from pathlib import Path

# Adiciona o diretório raiz ao path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from src.dw.connection import get_db_session
from src.agent.queries_metas import get_metas_realizado_por_mes_direto

# Valores esperados para agosto de 2025 (SEM totalizador)
EXPECTED_META_TOTAL = 17833053.45
EXPECTED_REALIZADO_TOTAL = 17254142.15
MES_ANO_TESTE = "2025-08"


def test_get_metas_realizado_por_mes_direto_sem_totais():
    """Testa se a função exclui totalizadores corretamente."""
    session = next(get_db_session())
    
    try:
        kpis = get_metas_realizado_por_mes_direto(session, MES_ANO_TESTE, excluir_totais=True)
        
        assert kpis is not None
        assert abs(kpis["meta_total"] - EXPECTED_META_TOTAL) < 100.0  # Tolerância de R$ 100
        assert abs(kpis["realizado_total"] - EXPECTED_REALIZADO_TOTAL) < 100.0
        assert kpis["total_vendedores"] == 63  # 63 vendedores sem o totalizador
        
        # Verifica se a linha "Totais" não está nas linhas detalhadas
        for linha in kpis["linhas_detalhadas"]:
            assert linha["vendedor_nome"] != "Totais"
            assert "total" not in linha["vendedor_nome"].lower()
        
        print(f"✅ Meta total: R$ {kpis['meta_total']:,.2f}")
        print(f"✅ Realizado total: R$ {kpis['realizado_total']:,.2f}")
        print(f"✅ Atingimento médio: {kpis['atingimento_medio']:.2f}%")
        print(f"✅ Total de vendedores: {kpis['total_vendedores']}")
        print(f"✅ Nenhuma linha 'Totais' encontrada")
        
    finally:
        session.close()


if __name__ == "__main__":
    test_get_metas_realizado_por_mes_direto_sem_totais()

