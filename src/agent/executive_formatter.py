"""
Executive Formatter - DIPAM COPILOT™.

Este módulo é responsável por transformar qualquer resultado DW em uma
narrativa executiva de alto padrão, de maneira consistente e reutilizável.
"""

from typing import Dict, Any, List, Optional


def formatar_execucao(dados, intent_spec, filtros, regras_behavior):
    """
    Gera narrativa executiva de alto nível com 4 blocos:
    1. Resumo Executivo
    2. Principais Achados
    3. Implicações Comerciais
    4. Plano de Ação Imediato
    
    Args:
        dados: Lista de dados retornados do DW (pode ser None ou lista vazia)
        intent_spec: IntentSpec (pode ser dict ou objeto)
        filtros: Dict com filtros aplicados
        regras_behavior: Lista de regras comportamentais aplicadas
    
    Returns:
        Dict com estrutura:
        {
            "resumo": str,
            "achados": List[str],
            "implicacoes": List[str],
            "plano": List[str]
        }
    """
    # Extrai tipo do intent_spec (pode ser dict ou objeto)
    intent_tipo = None
    if hasattr(intent_spec, 'tipo'):
        intent_tipo = intent_spec.tipo
    elif isinstance(intent_spec, dict):
        intent_tipo = intent_spec.get("tipo", "outros")
    else:
        intent_tipo = "outros"
    
    # Se não houver dados → narrativa negativa
    if not dados or (isinstance(dados, list) and len(dados) == 0):
        return {
            "resumo": "Nenhum registro foi encontrado com base nos filtros aplicados.",
            "achados": [
                "A ausência de registros pode indicar baixa atuação comercial ou falta de reposição no período.",
                "SKU, rota ou equipe podem estar com baixa movimentação estrutural."
            ],
            "implicacoes": [
                "Existe risco de perda de espaço no PDV.",
                "Pode indicar necessidade de ação imediata da equipe comercial."
            ],
            "plano": [
                "Validar filtros e parâmetros utilizados.",
                "Iniciar follow-up com supervisores responsáveis.",
                "Criar rotina automática de monitoramento."
            ]
        }
    
    # Se houver dados → narrativa positiva
    num_registros = len(dados) if isinstance(dados, list) else 1
    
    # Formata filtros para exibição
    filtros_str = ", ".join([f"{k}={v}" for k, v in filtros.items() if v is not None]) if filtros else "nenhum filtro específico"
    
    return {
        "resumo": (
            f"Foram encontrados {num_registros} registros relevantes relacionados à intenção "
            f"'{intent_tipo}', considerando {filtros_str}."
        ),
        "achados": [
            "Os dados mostram padrões relevantes que exigem atenção da liderança.",
            "Identificou-se movimentação que pode representar oportunidades comerciais imediatas."
        ],
        "implicacoes": [
            "Possibilidade de recuperação ou aceleração das vendas.",
            "Ajustes táticos podem aumentar performance no curto prazo."
        ],
        "plano": [
            "Priorizar análises por rota/equipe conforme impacto.",
            "Acompanhar vendedores responsáveis pelos principais casos.",
            "Revisitar indicadores em 7 dias."
        ]
    }

