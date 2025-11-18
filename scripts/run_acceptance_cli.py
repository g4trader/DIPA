#!/usr/bin/env python3
"""
Script CLI para executar manualmente as 13 perguntas essenciais do cliente.

Permite que o PO (Fabiano) e o Diretor da Dipam rodem isso localmente
e vejam rapidamente a "cara" da IA, sem precisar abrir o frontend.

Uso:
    python scripts/run_acceptance_cli.py

Ou com URL customizada:
    DIPAM_BACKEND_URL=http://localhost:8000 python scripts/run_acceptance_cli.py
"""

import os
import sys
import requests
import time
from typing import Dict, Any, Optional

# Adiciona src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

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


def chamar_backend(pergunta: str, papel: str = "diretor") -> Optional[Dict[str, Any]]:
    """
    Chama o endpoint /ask do backend.
    
    Args:
        pergunta: Pergunta do usuário
        papel: Papel do usuário (diretor, supervisor, vendedor)
        
    Returns:
        Resposta JSON do backend ou None em caso de erro
    """
    url = f"{BACKEND_URL}/ask"
    payload = {
        "pergunta": pergunta,
        "papel": papel
    }
    
    try:
        print(f"  Chamando backend: {url}")
        response = requests.post(url, json=payload, timeout=120)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"  ERRO ao chamar backend: {e}")
        return None


def extrair_trecho(texto: str, marcador: str, linhas_apos: int = 15) -> str:
    """
    Extrai um trecho do texto após um marcador.
    
    Args:
        texto: Texto completo
        marcador: Marcador a procurar (ex.: "Resumo Executivo")
        linhas_apos: Número de linhas a extrair após o marcador
        
    Returns:
        Trecho extraído
    """
    texto_lower = texto.lower()
    marcador_lower = marcador.lower()
    
    # Procura o marcador no texto
    idx = texto_lower.find(marcador_lower)
    if idx == -1:
        return f"[{marcador} não encontrado no texto]"
    
    # Extrai a partir do marcador
    trecho = texto[idx:]
    linhas = trecho.split('\n')[:linhas_apos]
    
    return '\n'.join(linhas)


def extrair_texto_resposta(resposta: Dict[str, Any]) -> str:
    """
    Extrai o texto completo da resposta.
    
    Args:
        resposta: Resposta JSON do backend
        
    Returns:
        Texto completo da resposta
    """
    # Tenta respostaMarkdown direto
    if "respostaMarkdown" in resposta:
        return resposta.get("resumoExecutivo", "") + "\n\n" + resposta.get("respostaMarkdown", "")
    
    # Tenta structured.respostaMarkdown
    structured = resposta.get("structured", {})
    if isinstance(structured, dict) and "respostaMarkdown" in structured:
        return structured["respostaMarkdown"]
    
    # Fallback: usa resumoExecutivo
    return resposta.get("resumoExecutivo", "")


def main():
    """Executa todas as perguntas sequencialmente."""
    print("=" * 80)
    print("DIPAM COPILOT™ - Testes de Aceitação CLI")
    print("=" * 80)
    print(f"Backend URL: {BACKEND_URL}")
    print(f"Total de perguntas: {len(PERGUNTAS_CLIENTE)}")
    print("=" * 80)
    print()
    
    resultados = []
    
    for i, pergunta_data in enumerate(PERGUNTAS_CLIENTE, start=1):
        pergunta_id = pergunta_data["id"]
        pergunta = pergunta_data["pergunta"]
        intent_esperado = pergunta_data["intent_esperado"]
        
        print(f"\n{'=' * 80}")
        print(f"{pergunta_id}: {pergunta}")
        print(f"{'=' * 80}")
        
        # Chama backend
        start_time = time.time()
        resposta = chamar_backend(pergunta)
        tempo_processamento = time.time() - start_time
        
        if resposta is None:
            print(f"  ❌ ERRO: Não foi possível obter resposta")
            resultados.append({
                "id": pergunta_id,
                "status": "erro",
                "tempo": tempo_processamento
            })
            continue
        
        # Extrai informações
        intent_detectada = resposta.get("intent", "N/A")
        confidence = resposta.get("confidence", 0.0)
        resumo_executivo = resposta.get("resumoExecutivo", "")
        texto_completo = extrair_texto_resposta(resposta)
        
        # Exibe informações
        print(f"\n  Intent detectada: {intent_detectada} (esperado: {intent_esperado})")
        print(f"  Confidence: {confidence:.2f}")
        print(f"  Tempo de processamento: {tempo_processamento:.2f}s")
        
        # Valida estrutura executiva
        headers_obrigatorios = [
            "Resumo Executivo",
            "Principais Achados",
            "Implicações Comerciais",
            "Plano de Ação Imediato"
        ]
        
        estrutura_ok = all(header in texto_completo for header in headers_obrigatorios)
        if not estrutura_ok:
            print(f"\n  ⚠️  [AVISO] Estrutura executiva não encontrada!")
            headers_encontrados = [h for h in headers_obrigatorios if h in texto_completo]
            headers_faltando = [h for h in headers_obrigatorios if h not in texto_completo]
            if headers_faltando:
                print(f"     Headers faltando: {', '.join(headers_faltando)}")
        
        # Extrai e exibe trechos dos novos headers
        print(f"\n  📊 Resumo Executivo:")
        print("  " + "-" * 76)
        trecho_resumo = extrair_trecho(texto_completo, "Resumo Executivo", 10)
        for linha in trecho_resumo.split('\n'):
            if linha.strip() and not linha.strip().startswith("Principais Achados"):
                print(f"  {linha}")
        
        print(f"\n  🔍 Principais Achados:")
        print("  " + "-" * 76)
        trecho_achados = extrair_trecho(texto_completo, "Principais Achados", 10)
        for linha in trecho_achados.split('\n'):
            if linha.strip() and not linha.strip().startswith("Implicações Comerciais"):
                print(f"  {linha}")
        
        print(f"\n  💼 Implicações Comerciais:")
        print("  " + "-" * 76)
        trecho_implicacoes = extrair_trecho(texto_completo, "Implicações Comerciais", 10)
        for linha in trecho_implicacoes.split('\n'):
            if linha.strip() and not linha.strip().startswith("Plano de Ação Imediato"):
                print(f"  {linha}")
        
        print(f"\n  📋 Plano de Ação Imediato:")
        print("  " + "-" * 76)
        trecho_plano = extrair_trecho(texto_completo, "Plano de Ação Imediato", 10)
        for linha in trecho_plano.split('\n'):
            if linha.strip():
                print(f"  {linha}")
        
        # Verifica se tem dados
        tem_dados = resposta.get("kpis") is not None or len(resposta.get("insights", [])) > 0
        status = "ok" if tem_dados else "sem_dados"
        
        resultados.append({
            "id": pergunta_id,
            "status": status,
            "intent": intent_detectada,
            "confidence": confidence,
            "tempo": tempo_processamento
        })
        
        # Pausa entre perguntas (opcional)
        if i < len(PERGUNTAS_CLIENTE):
            time.sleep(1)
    
    # Resumo final
    print(f"\n{'=' * 80}")
    print("RESUMO FINAL")
    print(f"{'=' * 80}")
    
    total = len(resultados)
    ok = sum(1 for r in resultados if r["status"] == "ok")
    sem_dados = sum(1 for r in resultados if r["status"] == "sem_dados")
    erros = sum(1 for r in resultados if r["status"] == "erro")
    
    print(f"Total de perguntas: {total}")
    print(f"✅ OK (com dados): {ok}")
    print(f"⚠️  Sem dados: {sem_dados}")
    print(f"❌ Erros: {erros}")
    
    tempo_total = sum(r["tempo"] for r in resultados)
    print(f"\nTempo total: {tempo_total:.2f}s")
    print(f"Tempo médio por pergunta: {tempo_total/total:.2f}s")
    
    print(f"\n{'=' * 80}")


if __name__ == "__main__":
    main()

