#!/usr/bin/env python3
"""
Script de testes para validar o endpoint /ask em produção.

Testa perguntas reais e valida se as respostas estão "inteligentes" (sem fallback genérico).

Uso:
    DIPAM_API_BASE_URL="https://dipam-ai-backend-xxxxx-uc.a.run.app" \
      python -m scripts.test_prod_agent
    
    # Ou com URL customizada:
    python -m scripts.test_prod_agent --url https://outra-url.com
"""

import sys
import os
import argparse
import time
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path

# Adiciona o diretório raiz ao path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

try:
    import requests
except ImportError:
    print("❌ Erro: biblioteca 'requests' não encontrada.")
    print("   Instale com: pip install requests")
    sys.exit(1)


# Frases típicas de fallback genérico (case-insensitive)
FALLBACK_PHRASES = [
    "não tenho informações suficientes",
    "não encontrei dados",
    "não foi possível processar",
    "erro ao consultar",
    "não consegui processar",
    "não há dados disponíveis",
    "não foi possível obter",
    "erro ao buscar",
    "não pude encontrar",
    "desculpe, não consegui",
    "não tenho acesso",
    "não foi possível acessar",
]


class TestResult:
    """Resultado de um teste individual."""
    
    def __init__(
        self,
        pergunta: str,
        papel: str,
        status_code: Optional[int] = None,
        tempo_resposta_ms: Optional[float] = None,
        resposta_texto: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        erro: Optional[str] = None,
        tem_fallback: bool = False,
    ):
        self.pergunta = pergunta
        self.papel = papel
        self.status_code = status_code
        self.tempo_resposta_ms = tempo_resposta_ms
        self.resposta_texto = resposta_texto
        self.payload = payload
        self.erro = erro
        self.tem_fallback = tem_fallback
    
    @property
    def sucesso(self) -> bool:
        """Retorna True se o teste passou."""
        if self.erro:
            return False
        if self.status_code != 200:
            return False
        if self.tem_fallback:
            return False
        if not self.resposta_texto and not self.payload:
            return False
        return True
    
    @property
    def status_label(self) -> str:
        """Retorna label do status (OK / POSSÍVEL PROBLEMA / ERRO)."""
        if self.erro:
            return "ERRO"
        if not self.sucesso:
            return "POSSÍVEL PROBLEMA"
        return "OK"
    
    def get_resumo(self, max_lines: int = 3) -> str:
        """Retorna resumo da resposta (primeiras linhas)."""
        if self.resposta_texto:
            linhas = self.resposta_texto.strip().split("\n")
            return "\n".join(linhas[:max_lines])
        
        if self.payload:
            # Tenta resumo_executivo primeiro
            structured = self.payload.get("structured", {})
            if isinstance(structured, dict):
                resumo = structured.get("resumo_executivo") or structured.get("resumoExecutivo")
                if resumo:
                    linhas = resumo.strip().split("\n")
                    return "\n".join(linhas[:max_lines])
            
            # Fallback para resumoExecutivo do payload
            resumo = self.payload.get("resumoExecutivo") or self.payload.get("resumo_executivo")
            if resumo:
                linhas = resumo.strip().split("\n")
                return "\n".join(linhas[:max_lines])
            
            # Último fallback: resposta do payload
            resposta = self.payload.get("resposta") or self.payload.get("question", "")
            if resposta:
                linhas = resposta.strip().split("\n")
                return "\n".join(linhas[:max_lines])
        
        return "(sem resumo disponível)"


def detectar_fallback(texto: str) -> bool:
    """
    Detecta se a resposta contém frases típicas de fallback genérico.
    
    Args:
        texto: Texto da resposta
        
    Returns:
        True se detectar fallback, False caso contrário
    """
    if not texto:
        return False
    
    texto_lower = texto.lower()
    for frase in FALLBACK_PHRASES:
        if frase.lower() in texto_lower:
            return True
    
    return False


def testar_pergunta(
    base_url: str,
    pergunta: str,
    papel: str = "diretor",
    timeout: int = 30
) -> TestResult:
    """
    Testa uma pergunta no endpoint /ask.
    
    Args:
        base_url: URL base da API (sem /ask)
        pergunta: Pergunta a ser enviada
        papel: Papel do usuário (diretor, supervisor, rca)
        timeout: Timeout em segundos
        
    Returns:
        TestResult com resultado do teste
    """
    url = f"{base_url.rstrip('/')}/ask"
    
    payload = {
        "pergunta": pergunta,
        "papel": papel,
    }
    
    inicio = time.perf_counter()
    
    try:
        response = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=timeout
        )
        
        tempo_ms = (time.perf_counter() - inicio) * 1000
        
        # Tenta parsear JSON
        try:
            data = response.json()
        except Exception as e:
            return TestResult(
                pergunta=pergunta,
                papel=papel,
                status_code=response.status_code,
                tempo_resposta_ms=tempo_ms,
                erro=f"Erro ao parsear JSON: {str(e)}"
            )
        
        # Extrai resposta textual
        resposta_texto = None
        payload_estruturado = None
        
        # Tenta várias formas de extrair a resposta
        if isinstance(data, dict):
            payload_estruturado = data.get("payload") or data
            resposta_texto = (
                data.get("resposta") or
                data.get("resumoExecutivo") or
                data.get("resumo_executivo") or
                (data.get("payload", {}).get("resumoExecutivo") if isinstance(data.get("payload"), dict) else None) or
                (data.get("structured", {}).get("resumo_executivo") if isinstance(data.get("structured"), dict) else None)
            )
        
        # Detecta fallback
        tem_fallback = False
        if resposta_texto:
            tem_fallback = detectar_fallback(resposta_texto)
        
        return TestResult(
            pergunta=pergunta,
            papel=papel,
            status_code=response.status_code,
            tempo_resposta_ms=tempo_ms,
            resposta_texto=resposta_texto,
            payload=payload_estruturado,
            tem_fallback=tem_fallback,
            erro=None if response.status_code == 200 else f"HTTP {response.status_code}"
        )
    
    except requests.exceptions.Timeout:
        tempo_ms = (time.perf_counter() - inicio) * 1000
        return TestResult(
            pergunta=pergunta,
            papel=papel,
            tempo_resposta_ms=tempo_ms,
            erro=f"Timeout após {timeout}s"
        )
    
    except requests.exceptions.ConnectionError as e:
        tempo_ms = (time.perf_counter() - inicio) * 1000
        return TestResult(
            pergunta=pergunta,
            papel=papel,
            tempo_resposta_ms=tempo_ms,
            erro=f"Erro de conexão: {str(e)}"
        )
    
    except Exception as e:
        tempo_ms = (time.perf_counter() - inicio) * 1000
        return TestResult(
            pergunta=pergunta,
            papel=papel,
            tempo_resposta_ms=tempo_ms,
            erro=f"Erro inesperado: {str(e)}"
        )


def main():
    """Função principal do script."""
    parser = argparse.ArgumentParser(
        description="Testa o endpoint /ask em produção com perguntas reais"
    )
    parser.add_argument(
        "--url",
        type=str,
        help="URL base da API (sobrescreve DIPAM_API_BASE_URL)"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Timeout em segundos para cada requisição (padrão: 30)"
    )
    
    args = parser.parse_args()
    
    # Lê URL base
    base_url = args.url or os.getenv("DIPAM_API_BASE_URL")
    
    if not base_url:
        print("❌ Erro: URL base da API não fornecida.")
        print("   Use --url ou defina DIPAM_API_BASE_URL")
        sys.exit(1)
    
    # Remove barra final se houver
    base_url = base_url.rstrip("/")
    
    print("=" * 80)
    print("🧪 TESTES DO ENDPOINT /ask - DIPAM COPILOT™")
    print("=" * 80)
    print(f"URL base: {base_url}")
    print(f"Timeout: {args.timeout}s")
    print("=" * 80)
    print()
    
    # Define perguntas de teste
    perguntas_teste: List[Tuple[str, str, str]] = [
        # (pergunta, papel, descricao)
        (
            "Sou o Diretor e preciso saber de forma detalhada porque não batemos a meta no mês de agosto 2025.",
            "diretor",
            "Diretor - Meta não batida (agosto 2025)"
        ),
        (
            "Quais são os vendedores com maior risco de não bater a meta em agosto 2025?",
            "diretor",
            "Diretor - Vendedores em risco (agosto 2025)"
        ),
        (
            "Quais clientes da minha carteira estão em maior risco de churn em agosto 2025?",
            "supervisor",
            "Supervisor - Clientes em risco de churn (agosto 2025)"
        ),
        (
            "Quais clientes positivados no produto Nissin não compram há mais de 60 dias?",
            "rca",
            "RCA - Clientes Nissin sem compra (60+ dias)"
        ),
        (
            "Quais foram os vendedores que mais impactaram negativamente o realizado de agosto 2025?",
            "diretor",
            "Geral - Vendedores com maior impacto negativo (agosto 2025)"
        ),
        (
            "Quais clientes têm maior potencial de crescimento na rota 22 em agosto 2025?",
            "diretor",
            "Geral - Oportunidades de crescimento (rota 22, agosto 2025)"
        ),
    ]
    
    resultados: List[TestResult] = []
    
    # Executa testes
    for idx, (pergunta, papel, descricao) in enumerate(perguntas_teste, 1):
        print(f"\n[{idx}/{len(perguntas_teste)}] {descricao}")
        print(f"Pergunta: {pergunta}")
        print(f"Papel: {papel}")
        print("Testando...", end=" ", flush=True)
        
        resultado = testar_pergunta(
            base_url=base_url,
            pergunta=pergunta,
            papel=papel,
            timeout=args.timeout
        )
        
        resultados.append(resultado)
        
        # Imprime resultado
        if resultado.sucesso:
            print("✅")
        else:
            print("❌")
        
        print(f"  Status: {resultado.status_label}")
        print(f"  Tempo: {resultado.tempo_resposta_ms:.0f}ms" if resultado.tempo_resposta_ms else "  Tempo: N/A")
        
        if resultado.erro:
            print(f"  Erro: {resultado.erro}")
        elif resultado.status_code:
            print(f"  HTTP: {resultado.status_code}")
        
        if resultado.tem_fallback:
            print("  ⚠️  ATENÇÃO: Resposta contém frases de fallback genérico")
        
        print(f"  Resumo:")
        resumo = resultado.get_resumo(max_lines=3)
        for linha in resumo.split("\n"):
            print(f"    {linha}")
        
        # Pequena pausa entre requisições
        if idx < len(perguntas_teste):
            time.sleep(0.5)
    
    # Resumo final
    print("\n" + "=" * 80)
    print("📊 RESUMO FINAL")
    print("=" * 80)
    
    sucessos = sum(1 for r in resultados if r.sucesso)
    falhas = len(resultados) - sucessos
    
    print(f"Total de testes: {len(resultados)}")
    print(f"✅ Sucessos: {sucessos}")
    print(f"❌ Falhas/Problemas: {falhas}")
    
    if resultados:
        tempos = [r.tempo_resposta_ms for r in resultados if r.tempo_resposta_ms]
        if tempos:
            tempo_medio = sum(tempos) / len(tempos)
            tempo_max = max(tempos)
            tempo_min = min(tempos)
            print(f"\nTempos de resposta:")
            print(f"  Média: {tempo_medio:.0f}ms")
            print(f"  Mínimo: {tempo_min:.0f}ms")
            print(f"  Máximo: {tempo_max:.0f}ms")
    
    print("\n" + "=" * 80)
    
    # Detalhes de falhas
    if falhas > 0:
        print("\n⚠️  DETALHES DAS FALHAS:")
        print("-" * 80)
        for idx, resultado in enumerate(resultados, 1):
            if not resultado.sucesso:
                print(f"\n[{idx}] {resultado.pergunta[:60]}...")
                print(f"    Papel: {resultado.papel}")
                print(f"    Status: {resultado.status_label}")
                if resultado.erro:
                    print(f"    Erro: {resultado.erro}")
                if resultado.tem_fallback:
                    print(f"    ⚠️  Contém fallback genérico")
                if resultado.status_code and resultado.status_code != 200:
                    print(f"    HTTP: {resultado.status_code}")
    
    print("\n" + "=" * 80)
    
    # Exit code
    if falhas == 0:
        print("✅ Todos os testes passaram!")
        sys.exit(0)
    else:
        print(f"❌ {falhas} teste(s) falharam ou apresentaram problemas.")
        sys.exit(1)


if __name__ == "__main__":
    main()

