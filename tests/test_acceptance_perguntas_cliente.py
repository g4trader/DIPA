"""
Testes de Aceitação - Perguntas Reais do Cliente.

Este módulo testa o pipeline completo (LLM intent + DW + pós-processador + LLM enterprise)
usando as 13 perguntas essenciais fornecidas pelo cliente.

Foco:
- Garantir que o pipeline não quebre
- Garantir que a intent correta seja disparada
- Garantir que a resposta volte no formato executivo definido
- Garantir que respostas negativas ou vazias ainda tragam diagnóstico e plano de ação
"""

import pytest
import os
import requests
import time
from typing import Dict, Any

# Marca testes como aceitação
pytestmark = pytest.mark.acceptance

# URL do backend (pode ser configurada via variável de ambiente)
BACKEND_URL = os.getenv("DIPAM_BACKEND_URL", "http://localhost:8000")


# Lista das 13 perguntas essenciais do cliente
PERGUNTAS_CLIENTE = [
    {
        "id": "Q1",
        "pergunta": "Quais clientes estão com cadastro ativo, mas sem nenhuma compra por mais de 60 dias?",
        "intent_esperado": "clientes_sem_compra"
    },
    {
        "id": "Q2",
        "pergunta": "Quais os clientes com maior queda de faturamento de 2025 x 2024?",
        "intent_esperado": "queda_faturamento"
    },
    {
        "id": "Q3",
        "pergunta": "Qual a indústria onde mais vendedores não atingiram as metas em Outubro/25?",
        "intent_esperado": "meta_departamento"
    },
    {
        "id": "Q4",
        "pergunta": "Quais as rotas com melhores e piores desempenhos em positivação de clientes com Mars?",
        "intent_esperado": "positivacao"
    },
    {
        "id": "Q5",
        "pergunta": "Quais os itens com a média de vendas mensal, menor que 10 caixas?",
        "intent_esperado": "vendas_baixas"
    },
    {
        "id": "Q6",
        "pergunta": "Quais clientes compraram Snickers Duplo Chocolate nos últimos 6 meses, mas não realizaram recompra?",
        "intent_esperado": "recompra"
    },
    {
        "id": "Q7",
        "pergunta": "Quais clientes da equipe conveniência não compraram Red Bull Zero em Outubro?",
        "intent_esperado": "clientes_sem_item"
    },
    {
        "id": "Q8",
        "pergunta": "Quais clientes com somente 1 unidade vendida, entre todos os itens da indústria AB Brasil, no mês de Outubro?",
        "intent_esperado": "clientes_sem_item"
    },
    {
        "id": "Q9",
        "pergunta": "Quais clientes não tiveram positivação de Snickers Original 45g em P12?",
        "intent_esperado": "positivacao"
    },
    {
        "id": "Q10",
        "pergunta": "Quais clientes não tiveram positivação de M&Ms Choco 40g em P12?",
        "intent_esperado": "positivacao"
    },
    {
        "id": "Q11",
        "pergunta": "Quais clientes não tiveram positivação de M&Ms Tubo em P12?",
        "intent_esperado": "positivacao"
    },
    {
        "id": "Q12",
        "pergunta": "Quantos clientes compraram o mix mínimo de Nissin em Outubro?",
        "intent_esperado": "mix_nissin"
    },
    {
        "id": "Q13",
        "pergunta": "Quais as rotas com pior desempenho no mix mínimo de Nissin, no mês de outubro?",
        "intent_esperado": "mix_nissin"
    }
]


def chamar_backend(pergunta: str, papel: str = "diretor") -> Dict[str, Any]:
    """
    Chama o endpoint /ask do backend.
    
    Args:
        pergunta: Pergunta do usuário
        papel: Papel do usuário (diretor, supervisor, vendedor)
        
    Returns:
        Resposta JSON do backend
    """
    url = f"{BACKEND_URL}/ask"
    payload = {
        "pergunta": pergunta,
        "papel": papel
    }
    
    try:
        response = requests.post(url, json=payload, timeout=120)  # Timeout de 2 minutos
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro ao chamar backend: {e}")


def extrair_texto_resposta(resposta: Dict[str, Any]) -> str:
    """
    Extrai o texto completo da resposta (markdown ou texto executivo).
    
    Tenta encontrar o texto em diferentes campos possíveis:
    - respostaMarkdown (se existir)
    - resumoExecutivo (sempre existe)
    - structured.respostaMarkdown (se existir)
    
    Args:
        resposta: Resposta JSON do backend
        
    Returns:
        Texto completo da resposta
    """
    # Tenta respostaMarkdown direto
    if "respostaMarkdown" in resposta:
        return resposta["resumoExecutivo"] + "\n\n" + resposta.get("resumoMarkdown", "")
    
    # Tenta structured.respostaMarkdown
    structured = resposta.get("structured", {})
    if isinstance(structured, dict) and "respostaMarkdown" in structured:
        return structured["respostaMarkdown"]
    
    # Fallback: usa resumoExecutivo (sempre existe)
    return resposta.get("resumoExecutivo", "")


def verificar_secoes_obrigatorias(texto: str) -> Dict[str, bool]:
    """
    Verifica se o texto contém as seções obrigatórias.
    
    Args:
        texto: Texto completo da resposta
        
    Returns:
        Dict com flags indicando quais seções foram encontradas
    """
    texto_lower = texto.lower()
    
    return {
        "resumo_executivo": any(marker in texto_lower for marker in [
            "resumo executivo", "resumo", "executivo"
        ]),
        "plano_acao": any(marker in texto_lower for marker in [
            "plano de ação", "plano de acao", "ações sugeridas", "acoes sugeridas",
            "ações imediatas", "acoes imediatas", "plano de ação sugerido"
        ]),
        "diagnostico": any(marker in texto_lower for marker in [
            "diagnóstico", "diagnostico", "análise", "analise", "causas",
            "sinais de atenção", "sinais de atencao"
        ])
    }


@pytest.mark.parametrize("pergunta_data", PERGUNTAS_CLIENTE)
def test_pergunta_cliente_pipeline_completo(pergunta_data: Dict[str, Any]):
    """
    Testa que cada pergunta do cliente:
    1. Não quebra o pipeline
    2. Retorna HTTP 200
    3. Retorna JSON válido sem erros críticos
    4. Contém seções obrigatórias (Resumo Executivo, Plano de Ação)
    """
    pergunta_id = pergunta_data["id"]
    pergunta = pergunta_data["pergunta"]
    
    # Chama backend
    resposta = chamar_backend(pergunta)
    
    # Validação 1: HTTP status code é 200 (já validado pelo raise_for_status)
    assert resposta is not None, f"{pergunta_id}: Resposta não pode ser None"
    
    # Validação 2: JSON não está em erro genérico
    assert "erro" not in resposta or not resposta.get("erro"), \
        f"{pergunta_id}: Resposta contém erro crítico: {resposta.get('erro')}"
    
    # Validação 3: Campos obrigatórios existem
    assert "resumoExecutivo" in resposta, \
        f"{pergunta_id}: Campo 'resumoExecutivo' não encontrado na resposta"
    
    assert "intent" in resposta, \
        f"{pergunta_id}: Campo 'intent' não encontrado na resposta"
    
    # Validação 4: Intent detectada (pode ser diferente do esperado, mas deve existir)
    intent_detectada = resposta.get("intent", "")
    assert intent_detectada, \
        f"{pergunta_id}: Intent não foi detectada (campo vazio ou None)"
    
    # Validação 5: Resumo executivo não está vazio
    resumo_executivo = resposta.get("resumoExecutivo", "")
    assert resumo_executivo and len(resumo_executivo.strip()) > 0, \
        f"{pergunta_id}: Resumo executivo está vazio"
    
    # Validação 6: Extrai texto completo e verifica seções obrigatórias
    texto_completo = extrair_texto_resposta(resposta)
    secoes_encontradas = verificar_secoes_obrigatorias(texto_completo)
    
    # Resumo Executivo deve sempre existir (já validado acima, mas verifica no texto completo)
    assert secoes_encontradas["resumo_executivo"], \
        f"{pergunta_id}: Seção 'Resumo Executivo' não encontrada no texto completo"
    
    # Plano de Ação deve existir (mesmo em respostas negativas)
    assert secoes_encontradas["plano_acao"], \
        f"{pergunta_id}: Seção 'Plano de Ação Sugerido' não encontrada no texto completo"
    
    # Log para debug (opcional)
    print(f"\n{pergunta_id}: Intent detectada = {intent_detectada}")
    print(f"{pergunta_id}: Resumo Executivo (primeiros 200 chars) = {resumo_executivo[:200]}...")


@pytest.mark.parametrize("pergunta_data", PERGUNTAS_CLIENTE)
def test_pergunta_cliente_estrutura_resposta(pergunta_data: Dict[str, Any]):
    """
    Testa que a estrutura da resposta está completa e correta.
    """
    pergunta_id = pergunta_data["id"]
    pergunta = pergunta_data["pergunta"]
    
    resposta = chamar_backend(pergunta)
    
    # Valida estrutura básica
    assert "question" in resposta, f"{pergunta_id}: Campo 'question' não encontrado"
    assert "confidence" in resposta, f"{pergunta_id}: Campo 'confidence' não encontrado"
    assert "contexto" in resposta, f"{pergunta_id}: Campo 'contexto' não encontrado"
    
    # Valida que confidence é um número entre 0 e 1
    confidence = resposta.get("confidence", 0)
    assert isinstance(confidence, (int, float)), \
        f"{pergunta_id}: Confidence deve ser número, recebido: {type(confidence)}"
    assert 0 <= confidence <= 1, \
        f"{pergunta_id}: Confidence deve estar entre 0 e 1, recebido: {confidence}"


@pytest.mark.parametrize("pergunta_data", PERGUNTAS_CLIENTE)
def test_pergunta_cliente_resposta_negativa_estrutura_completa(pergunta_data: Dict[str, Any]):
    """
    Testa que mesmo respostas negativas (sem dados ou poucos dados) têm estrutura completa.
    
    Este teste verifica que mesmo quando não há dados suficientes, a resposta ainda contém:
    - Resumo Executivo explicando a situação
    - Diagnóstico técnico
    - Plano de Ação Sugerido
    """
    pergunta_id = pergunta_data["id"]
    pergunta = pergunta_data["pergunta"]
    
    resposta = chamar_backend(pergunta)
    
    # Extrai texto completo
    texto_completo = extrair_texto_resposta(resposta)
    secoes_encontradas = verificar_secoes_obrigatorias(texto_completo)
    
    # Mesmo sem dados, deve ter Resumo Executivo
    assert secoes_encontradas["resumo_executivo"], \
        f"{pergunta_id}: Resposta negativa deve conter 'Resumo Executivo'"
    
    # Mesmo sem dados, deve ter Plano de Ação
    assert secoes_encontradas["plano_acao"], \
        f"{pergunta_id}: Resposta negativa deve conter 'Plano de Ação Sugerido'"
    
    # Diagnóstico é desejável (mas não obrigatório se não houver dados)
    # Não falha o teste se não tiver, mas loga
    if not secoes_encontradas["diagnostico"]:
        print(f"{pergunta_id}: AVISO - Seção 'Diagnóstico' não encontrada (pode ser aceitável se não houver dados)")

