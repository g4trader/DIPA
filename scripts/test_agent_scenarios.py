#!/usr/bin/env python3
"""
Script de testes end-to-end do DIPAM COPILOT™.

Simula perguntas reais de diretor/supervisor e mede:
- Intent detectada
- Tempo de resposta
- Qualidade da resposta (português natural)
- Conteúdo do contexto numérico (não vazio)

Uso:
    DB_TYPE=sqlite python -m scripts.test_agent_scenarios
"""

import os
import sys
import time
import traceback
from typing import Dict, Any, List

# Garante que o diretório raiz está no path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Define DB_TYPE=sqlite antes de importar módulos do banco
os.environ.setdefault('DB_TYPE', 'sqlite')

from src.agent.service import get_agent_service
from src.dw.connection import get_db_session


# ============================================================================
# CENÁRIOS DE TESTE
# ============================================================================

SCENARIOS: List[Dict[str, str]] = [
    {
        "nome": "Metas últimos 6 meses - visão diretor",
        "pergunta": "Sou diretor e preciso ver meta e realizado de vendas dos últimos 6 meses, mês a mês, com um resumo da tendência.",
        "papel": "diretor"
    },
    {
        "nome": "Clientes Nissin sem compra há 60 dias",
        "pergunta": "Preciso saber quais clientes positivados no produto Nissin que não compram há mais de 60 dias e quais são os mais importantes em faturamento.",
        "papel": "supervisor"
    },
    {
        "nome": "Oportunidades por produto - massas",
        "pergunta": "Quero oportunidades de crescimento na linha de massas, mostrando clientes que poderiam comprar mais com base no histórico e mix atual.",
        "papel": "diretor"
    },
    {
        "nome": "Desempenho dos supervisores",
        "pergunta": "Quais supervisores estão mais distantes de bater as metas nos últimos 3 meses e por quê?",
        "papel": "diretor"
    },
    {
        "nome": "Resumo executivo para diretoria",
        "pergunta": "Me faça um resumo executivo das 5 maiores oportunidades e 5 maiores riscos na carteira de clientes com base nas vendas e metas dos últimos meses.",
        "papel": "diretor"
    },
    {
        "nome": "Produtos com baixa venda",
        "pergunta": "Quais produtos estão vendendo menos nos últimos 90 dias?",
        "papel": "supervisor"
    },
    {
        "nome": "Quem bateu meta em agosto",
        "pergunta": "Quem bateu meta em agosto de 2025?",
        "papel": "diretor"
    },
    {
        "nome": "Clientes em risco de churn",
        "pergunta": "Quais clientes estão reduzindo o volume de compras nos últimos 3 meses? Mostre os principais em risco.",
        "papel": "supervisor"
    }
]


# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================

def print_header(text: str, char: str = "="):
    """Imprime um cabeçalho formatado."""
    print(f"\n{char * 80}")
    print(f"{text.center(80)}")
    print(f"{char * 80}\n")


def print_section(text: str, char: str = "-"):
    """Imprime uma seção formatada."""
    print(f"\n{char * 80}")
    print(f"{text}")
    print(f"{char * 80}")


def truncate_text(text: str, max_chars: int = 400) -> str:
    """Trunca texto para um número máximo de caracteres."""
    if not text:
        return "(vazio)"
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "... (truncado)"


def format_time(seconds: float) -> str:
    """Formata tempo em segundos de forma legível."""
    if seconds < 1.0:
        return f"{seconds * 1000:.1f} ms"
    elif seconds < 60.0:
        return f"{seconds:.2f} s"
    else:
        mins = int(seconds // 60)
        secs = seconds % 60
        return f"{mins}m {secs:.2f}s"


def check_portuguese_natural(text: str) -> Dict[str, Any]:
    """
    Verifica se o texto parece estar em português natural.
    
    Heurísticas simples:
    - Não é apenas JSON
    - Não é apenas números
    - Contém palavras comuns em português
    - Tem estrutura de frases (pontos, vírgulas)
    """
    if not text or len(text.strip()) == 0:
        return {
            "is_natural": False,
            "reason": "Texto vazio"
        }
    
    text_lower = text.lower()
    
    # Palavras comuns em português
    portuguese_words = [
        "o", "a", "de", "que", "e", "do", "da", "em", "um", "para", "é", "com",
        "não", "uma", "os", "no", "se", "na", "por", "mais", "as", "dos",
        "como", "mas", "foi", "ao", "ele", "das", "tem", "à", "seu", "sua",
        "ou", "ser", "quando", "muito", "há", "nos", "já", "está", "eu",
        "também", "só", "pelo", "pela", "até", "isso", "ela", "entre", "era",
        "depois", "sem", "mesmo", "aos", "ter", "seus", "suas", "numa",
        "pelos", "pelas", "havia", "seja", "qual", "será", "nós", "tenho",
        "lhe", "deles", "essas", "esses", "pelas", "pelos"
    ]
    
    # Verifica se contém palavras em português
    word_count = sum(1 for word in portuguese_words if word in text_lower)
    has_portuguese = word_count > 5
    
    # Verifica se não é apenas JSON estruturado
    is_json_like = text.strip().startswith("{") and text.strip().endswith("}")
    
    # Verifica se tem estrutura de frase
    has_sentence_structure = any(char in text for char in [".", ",", "!", "?", "\n"])
    
    # Verifica se não é apenas números e símbolos
    has_words = any(c.isalpha() for c in text)
    
    is_natural = (
        has_portuguese and
        not is_json_like and
        has_sentence_structure and
        has_words
    )
    
    reasons = []
    if not has_portuguese:
        reasons.append("poucas palavras em português")
    if is_json_like:
        reasons.append("parece ser JSON estruturado")
    if not has_sentence_structure:
        reasons.append("falta estrutura de frase")
    if not has_words:
        reasons.append("sem palavras alfabéticas")
    
    return {
        "is_natural": is_natural,
        "reason": ", ".join(reasons) if reasons else "OK",
        "word_count": word_count
    }


def check_context_not_empty(contexto: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verifica se o contexto numérico não está vazio.
    
    Retorna informações sobre quais chaves existem e se há dados úteis.
    """
    if not contexto:
        return {
            "is_empty": True,
            "keys": [],
            "has_data": False,
            "message": "Contexto vazio ou None"
        }
    
    keys = list(contexto.keys())
    has_data = False
    
    # Verifica se há dados úteis (não apenas campos vazios, None ou listas vazias)
    for key, value in contexto.items():
        if value is None:
            continue
        if isinstance(value, (list, dict)):
            if len(value) > 0:
                has_data = True
                break
        elif isinstance(value, (str, int, float)):
            if value and value != "" and value != 0:
                has_data = True
                break
        else:
            has_data = True
            break
    
    return {
        "is_empty": not has_data,
        "keys": keys,
        "has_data": has_data,
        "key_count": len(keys),
        "message": f"Contexto tem {len(keys)} chave(s): {', '.join(keys[:10])}" + ("..." if len(keys) > 10 else "")
    }


# ============================================================================
# FUNÇÃO PRINCIPAL
# ============================================================================

def test_scenario(scenario: Dict[str, str], scenario_num: int, total: int) -> Dict[str, Any]:
    """
    Testa um cenário específico.
    
    Args:
        scenario: Dicionário com 'nome' e 'pergunta'
        scenario_num: Número do cenário (1-indexed)
        total: Total de cenários
        
    Returns:
        dict: Resultado do teste com métricas e informações
    """
    print_header(f"Cenário {scenario_num}/{total}: {scenario['nome']}")
    print(f"Pergunta: {scenario['pergunta']}")
    print(f"Papel: {scenario.get('papel', 'diretor')}")
    
    resultado = {
        "scenario": scenario["nome"],
        "pergunta": scenario["pergunta"],
        "sucesso": False,
        "intent": None,
        "confianca": None,
        "tempo_segundos": None,
        "resposta_preview": None,
        "resposta_completa": None,
        "contexto_keys": [],
        "contexto_has_data": False,
        "is_portuguese_natural": False,
        "erro": None
    }
    
    session = None
    try:
        # Abre sessão de banco de dados
        session_context = get_db_session()
        session = next(session_context)
        
        # Obtém instância do agente
        agent = get_agent_service()
        
        # Mede o tempo da chamada
        start = time.perf_counter()
        
        result = agent.process_question(
            pergunta=scenario["pergunta"],
            session=session,
            usuario_id="debug_teste_scenarios",
            papel=scenario.get("papel", "diretor"),
        )
        
        elapsed = time.perf_counter() - start
        
        # Extrai informações do resultado
        resultado["sucesso"] = True
        resultado["intent"] = result.get("intent", "N/A")
        resultado["confianca"] = result.get("confianca")
        resultado["tempo_segundos"] = elapsed
        resultado["resposta_completa"] = result.get("resposta", "")
        resultado["resposta_preview"] = truncate_text(resultado["resposta_completa"], max_chars=400)
        
        # Verifica contexto
        contexto = result.get("contexto", {})
        contexto_info = check_context_not_empty(contexto)
        resultado["contexto_keys"] = contexto_info["keys"]
        resultado["contexto_has_data"] = contexto_info["has_data"]
        
        # Verifica se a resposta está em português natural
        portuguese_check = check_portuguese_natural(resultado["resposta_completa"])
        resultado["is_portuguese_natural"] = portuguese_check["is_natural"]
        resultado["portuguese_reason"] = portuguese_check["reason"]
        
        # Imprime resultados
        print_section("📊 Resultados")
        print(f"✅ Sucesso: Sim")
        print(f"🎯 Intent detectada: {resultado['intent']}")
        if resultado["confianca"] is not None:
            print(f"📈 Confiança: {resultado['confianca']:.1%}")
        print(f"⏱️  Tempo de resposta: {format_time(elapsed)}")
        print(f"\n📝 Resposta (preview):\n{resultado['resposta_preview']}")
        print(f"\n📦 Contexto:")
        print(f"   - Chaves: {len(contexto_info['keys'])} chave(s)")
        if contexto_info['keys']:
            print(f"   - Lista: {', '.join(contexto_info['keys'][:10])}" + ("..." if len(contexto_info['keys']) > 10 else ""))
        print(f"   - Tem dados: {'✅ Sim' if contexto_info['has_data'] else '❌ Não'}")
        print(f"\n🇧🇷 Português natural: {'✅ Sim' if resultado['is_portuguese_natural'] else '❌ Não'}")
        if not resultado['is_portuguese_natural']:
            print(f"   - Razão: {portuguese_check['reason']}")
        
    except Exception as e:
        resultado["erro"] = str(e)
        resultado["traceback"] = traceback.format_exc()
        
        print_section("❌ ERRO")
        print(f"Erro ao processar cenário: {str(e)}")
        print(f"\nStack trace:")
        print(traceback.format_exc())
        
    finally:
        # Fecha sessão
        if session:
            try:
                session.close()
            except:
                pass
    
    return resultado


def main():
    """Função principal para executar todos os testes."""
    print_header("🧪 TESTES END-TO-END DO DIPAM COPILOT™", char="=")
    print(f"Total de cenários: {len(SCENARIOS)}")
    print(f"Data/Hora: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    resultados: List[Dict[str, Any]] = []
    
    # Executa cada cenário
    for i, scenario in enumerate(SCENARIOS, start=1):
        resultado = test_scenario(scenario, i, len(SCENARIOS))
        resultados.append(resultado)
        
        # Pequena pausa entre cenários
        time.sleep(0.5)
    
    # Resumo final
    print_header("📊 RESUMO FINAL", char="=")
    
    total = len(resultados)
    sucesso = sum(1 for r in resultados if r["sucesso"])
    falhas = total - sucesso
    
    print(f"Total de cenários: {total}")
    print(f"✅ Sucessos: {sucesso} ({sucesso/total*100:.1f}%)")
    print(f"❌ Falhas: {falhas} ({falhas/total*100:.1f}%)")
    
    if sucesso > 0:
        tempos = [r["tempo_segundos"] for r in resultados if r["tempo_segundos"] is not None]
        if tempos:
            tempo_medio = sum(tempos) / len(tempos)
            tempo_min = min(tempos)
            tempo_max = max(tempos)
            print(f"\n⏱️  Tempo de resposta:")
            print(f"   - Média: {format_time(tempo_medio)}")
            print(f"   - Mínimo: {format_time(tempo_min)}")
            print(f"   - Máximo: {format_time(tempo_max)}")
        
        portugues_natural = sum(1 for r in resultados if r.get("is_portuguese_natural", False))
        print(f"\n🇧🇷 Português natural: {portugues_natural}/{sucesso} ({portugues_natural/sucesso*100:.1f}%)")
        
        contexto_com_dados = sum(1 for r in resultados if r.get("contexto_has_data", False))
        print(f"📦 Contexto com dados: {contexto_com_dados}/{sucesso} ({contexto_com_dados/sucesso*100:.1f}%)")
    
    # Detalhes por cenário
    print_section("📋 Detalhes por Cenário")
    for i, resultado in enumerate(resultados, start=1):
        status = "✅" if resultado["sucesso"] else "❌"
        intent = resultado.get("intent", "N/A")
        tempo = format_time(resultado["tempo_segundos"]) if resultado["tempo_segundos"] else "N/A"
        portugues = "✅" if resultado.get("is_portuguese_natural") else "❌"
        contexto = "✅" if resultado.get("contexto_has_data") else "❌"
        
        print(f"{status} {i}. {resultado['scenario']}")
        print(f"   Intent: {intent} | Tempo: {tempo} | Português: {portugues} | Contexto: {contexto}")
        if resultado["erro"]:
            print(f"   Erro: {resultado['erro']}")
    
    # Retorna código de saída baseado em sucesso
    if falhas == 0:
        print_header("✅ TODOS OS TESTES PASSARAM!", char="=")
        exit_code = 0
    else:
        print_header(f"⚠️  {falhas} TESTE(S) FALHARAM", char="=")
        exit_code = 1
    
    return exit_code


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Teste interrompido pelo usuário")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ ERRO FATAL: {str(e)}")
        traceback.print_exc()
        sys.exit(1)

