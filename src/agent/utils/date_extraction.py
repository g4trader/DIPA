# src/agent/utils/date_extraction.py

import re
from typing import Optional

try:
    from unidecode import unidecode
except ImportError:
    def unidecode(s: str) -> str:
        return s  # fallback simples se não tiver lib


MESES_NOME = {
    "janeiro": 1,
    "fevereiro": 2,
    "marco": 3,
    "março": 3,
    "abril": 4,
    "maio": 5,
    "junho": 6,
    "julho": 7,
    "agosto": 8,
    "setembro": 9,
    "outubro": 10,
    "novembro": 11,
    "dezembro": 12,
}


def extrair_mes_ano_explicito(texto: str) -> Optional[str]:
    """
    Extrai um mes_ano explícito da pergunta (ex.: 'agosto 2025' -> '2025-08').
    
    Não faz nenhum ajuste para dados disponíveis – é 100% o que o usuário pediu.
    
    Args:
        texto: Texto da pergunta do usuário
        
    Returns:
        str | None: Data no formato YYYY-MM (ex.: "2025-08") ou None se não encontrar
    """
    t = unidecode(texto.lower())

    # Formatos numericos: 08/2025, 8/2025, 08-2025, 8-2025
    m = re.search(r"\b(0?[1-9]|1[0-2])[/\-](20\d{2})\b", t)
    if m:
        mes = int(m.group(1))
        ano = int(m.group(2))
        return f"{ano:04d}-{mes:02d}"

    # Formatos com nome do mes: "agosto 2025", "em agosto de 2025" etc.
    # IMPORTANTE: Procura meses completos primeiro (mais específicos) para evitar falsos positivos
    # Ex.: "ago" pode aparecer em "agosto" ou outras palavras, então priorizamos "agosto"
    meses_ordenados = sorted(MESES_NOME.items(), key=lambda x: -len(x[0]))  # Mais longos primeiro
    
    for nome, num in meses_ordenados:
        # Usa word boundary para evitar falsos positivos
        pattern = r"\b" + re.escape(nome) + r"\b"
        if re.search(pattern, t):
            m_ano = re.search(r"20\d{2}", t)
            if m_ano:
                ano = int(m_ano.group(0))
                return f"{ano:04d}-{num:02d}"

    return None

