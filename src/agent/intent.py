"""
Detecção de Intenções do Agente.

Este módulo identifica a intenção do usuário a partir de perguntas
em linguagem natural, direcionando para o handler apropriado.
"""

import re
import logging
from typing import Dict, Any, Optional, Tuple
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class IntentType(Enum):
    """
    Tipos de intenções suportadas pelo agente.
    """
    CONSULTA_META = "consulta_meta"  # Consulta geral de meta (vendedor, supervisor, departamento, período)
    META_VENDEDOR = "meta_vendedor"  # Pergunta sobre meta de vendedor (legado)
    META_DEPARTAMENTO = "meta_departamento"  # Pergunta sobre meta de departamento (legado)
    MOTIVO_NAO_BATEU_META = "motivo_nao_bateu_meta"  # Por que não bateu meta
    PREVISAO_BATER_META = "previsao_bater_meta"  # Previsão de bater meta
    CHURN_CLIENTES = "churn_clientes"  # Pergunta sobre risco de churn
    CLIENTES_RISCO_CHURN = "clientes_risco_churn"  # Lista clientes em risco de churn
    RESUMO_SUPERVISOR = "resumo_supervisor"  # Resumo de supervisor/departamento
    VENDAS_ANALISE = "vendas_analise"  # Análise de vendas (histórica)
    VENDAS_PREVISAO = "vendas_previsao"  # Previsão/projeção de vendas futuras
    PRODUTOS_BAIXA_VENDA = "produtos_baixa_venda"  # Produtos com baixa venda/pior desempenho
    CLIENTES_CHURN_PRODUTO = "clientes_churn_produto"  # Clientes que abandonaram um produto específico
    CLIENTES_OPORTUNIDADES = "clientes_oportunidades"  # Oportunidades de crescimento com clientes
    DESEMPENHO_SUPERVISORES = "desempenho_supervisores"  # Comparação de desempenho de supervisores
    OPORTUNIDADES_DIRETORIA = "oportunidades_diretoria"  # Resumo executivo de oportunidades (diretor)
    CONSULTA_VENDEDORES_PERFORMANCE = "consulta_vendedores_performance"  # Análise de performance de vendedores (piores, impacto negativo, etc.)
    RANKING = "ranking"  # Rankings e comparações
    EXPLICACAO = "explicacao"  # Explicação de resultados
    OUTROS = "outros"  # Outras perguntas (fallback)
    DESCONHECIDA = "desconhecida"  # Intenção não reconhecida


# Mapeamento de meses em português para números
MESES_PT = {
    "janeiro": 1, "jan": 1,
    "fevereiro": 2, "fev": 2,
    "março": 3, "marco": 3, "mar": 3,
    "abril": 4, "abr": 4,
    "maio": 5, "mai": 5,
    "junho": 6, "jun": 6,
    "julho": 7, "jul": 7,
    "agosto": 8, "ago": 8,
    "setembro": 9, "set": 9,
    "outubro": 10, "out": 10,
    "novembro": 11, "nov": 11,
    "dezembro": 12, "dez": 12,
}

# Mapeamento reverso para conversão de número para string (para compatibilidade)
MESES_PT_STR = {
    "janeiro": "01", "jan": "01",
    "fevereiro": "02", "fev": "02",
    "março": "03", "marco": "03", "mar": "03",
    "abril": "04", "abr": "04",
    "maio": "05", "mai": "05",
    "junho": "06", "jun": "06",
    "julho": "07", "jul": "07",
    "agosto": "08", "ago": "08",
    "setembro": "09", "set": "09",
    "outubro": "10", "out": "10",
    "novembro": "11", "nov": "11",
    "dezembro": "12", "dez": "12",
}

# Padrões de pastas conhecidas
PASTAS_CONHECIDAS = [
    "verde", "amarela", "azul", "vermelha", "roxa", "laranja",
    "verde claro", "verde escuro", "amarelo", "amarelo claro"
]


def parse_mes_ano_from_text(text: str) -> Tuple[Optional[str], Optional[int]]:
    """
    Tenta extrair um mes_ano (YYYY-MM) e/ou um número de meses de janela (ex.: "últimos 6 meses")
    a partir de um texto em português.

    Retorna:
        - mes_ano (YYYY-MM) se encontrar algo explícito, senão None
        - janela_meses (int) se encontrar algo tipo "últimos 6 meses", senão None
    """
    text_low = text.lower()

    # 1) Padrões explícitos tipo 2025-10 / 2025/10
    m = re.search(r"(20\d{2})[/-](\d{1,2})", text_low)
    if m:
        ano = int(m.group(1))
        mes = int(m.group(2))
        if 1 <= mes <= 12:
            return f"{ano}-{mes:02d}", None

    # 2) "outubro de 2025" / "outubro 2025"
    for nome_mes, num_mes in MESES_PT.items():
        if nome_mes in text_low:
            m2 = re.search(r"20\d{2}", text_low)
            if m2:
                ano = int(m2.group(0))
                return f"{ano}-{num_mes:02d}", None

    # 3) "mês 10 de 2025" / "mes 10 2025"
    m = re.search(r"mes\s+(\d{1,2}).*?(20\d{2})", text_low)
    if m:
        mes = int(m.group(1))
        ano = int(m.group(2))
        if 1 <= mes <= 12:
            return f"{ano}-{mes:02d}", None

    # 4) "últimos X meses"
    m = re.search(r"últimos\s+(\d{1,2})\s+meses", text_low)
    if not m:
        m = re.search(r"ultimos\s+(\d{1,2})\s+meses", text_low)
    if m:
        janela = int(m.group(1))
        return None, janela

    return None, None


def normalize_mes_ano(mes_str: Optional[str], ano_str: Optional[str]) -> Optional[str]:
    """
    Normaliza mês e ano para formato YYYY-MM.
    
    Args:
        mes_str: String do mês (número ou nome em português)
        ano_str: String do ano
        
    Returns:
        str: Data no formato YYYY-MM ou None
    """
    if not mes_str or not ano_str:
        return None
    
    # Converte mês texto para número se necessário
    mes_num = MESES_PT.get(mes_str.lower())
    if mes_num is not None:
        mes_normalizado = f"{mes_num:02d}"
    elif mes_str.isdigit():
        mes_normalizado = mes_str.zfill(2)
    else:
        mes_normalizado = mes_str
    
    # Garante que o ano tem 4 dígitos
    if ano_str.isdigit():
        # Se ano tem 2 dígitos, assume 20XX
        if len(ano_str) == 2:
            ano_str = f"20{ano_str}"
    
    try:
        # Valida se é uma data válida
        datetime.strptime(f"{ano_str}-{mes_normalizado}", "%Y-%m")
        return f"{ano_str}-{mes_normalizado}"
    except ValueError:
        logger.warning(f"Data inválida: {ano_str}-{mes_normalizado}")
        return None


def extract_entities(pergunta: str) -> Dict[str, Optional[str]]:
    """
    Extrai entidades da pergunta (vendedor, supervisor, mês, etc.).
    
    Melhorado para identificar:
    - mês/ano (ex: agosto de 2025, 2025-08)
    - vendedor ou RCA
    - supervisor
    - departamento
    - rota
    - pasta (verde, amarela, etc.)
    - tipo: "meta", "realizado", "meta vs realizado"
    
    Args:
        pergunta: Pergunta do usuário
        
    Returns:
        dict: Dicionário com entidades extraídas
    """
    pergunta_original = pergunta
    pergunta_lower = pergunta.lower()
    entities = {
        "vendedor": None,
        "supervisor": None,
        "departamento": None,
        "mes_ano": None,
        "mes": None,
        "ano": None,
        "rota": None,
        "rca": None,
        "pasta": None,
        "tipo": None,  # "meta", "realizado", "meta_vs_realizado"
        "n_meses": None,  # Número de meses para análise histórica (ex.: "últimos 6 meses")
        "janela_meses": None,  # Janela de meses para análise (ex.: "últimos 6 meses")
    }
    
    # ========== Extrai N_MESES (últimos N meses) ==========
    # Padrões: "últimos 6 meses", "últimos 3 meses", "nos últimos 12 meses"
    n_meses_patterns = [
        r"últimos\s+(\d+)\s+meses",
        r"nos\s+últimos\s+(\d+)\s+meses",
        r"últimos\s+(\d+)\s+mes",  # "últimos 6 mês"
        r"(\d+)\s+meses.*últimos",  # "6 meses últimos"
    ]
    for pattern in n_meses_patterns:
        match = re.search(pattern, pergunta_lower)
        if match:
            try:
                n_meses = int(match.group(1))
                entities["n_meses"] = n_meses
                break
            except ValueError:
                pass
    
    # Se não encontrou número explícito mas menciona "últimos meses", usa padrão 6
    if not entities.get("n_meses") and re.search(r"últimos.*meses|últimos.*mês", pergunta_lower):
        entities["n_meses"] = 6  # Padrão: últimos 6 meses
    
    # ========== Extrai TIPO ==========
    # Identifica se pergunta sobre meta, realizado ou comparação
    if re.search(r"meta.*vs.*realizado|realizado.*vs.*meta|meta.*versus.*realizado", pergunta_lower):
        entities["tipo"] = "meta_vs_realizado"
    elif re.search(r"\brealizado\b|faturado|vendas", pergunta_lower):
        entities["tipo"] = "realizado"
    elif re.search(r"\bmeta\b|metas", pergunta_lower):
        entities["tipo"] = "meta"
    
    # ========== Extrai ROTA ==========
    # Padrões: "rota 77", "ROTA 12", "rota77"
    rota_patterns = [
        r"rota\s*(\d+)",
        r"r\.?\s*(\d+)",  # R.77 ou R 77
    ]
    for pattern in rota_patterns:
        match = re.search(pattern, pergunta_lower)
        if match:
            rota_num = match.group(1)
            entities["rota"] = f"ROTA {rota_num}"
            entities["vendedor"] = entities["rota"]  # Rota é o vendedor
            break
    
    # ========== Extrai RCA ==========
    # Padrões: "RCA 123", "rca 456"
    rca_pattern = r"rca\s*(\d+)"
    match = re.search(rca_pattern, pergunta_lower)
    if match:
        entities["rca"] = f"RCA {match.group(1)}"
        if not entities.get("vendedor"):
            entities["vendedor"] = entities["rca"]
    
    # ========== Extrai MÊS/ANO usando função melhorada ==========
    # Reutiliza o parser de mês/ano já criado (parse_mes_ano_from_text)
    # Garante que para CONSULTA_VENDEDORES_PERFORMANCE (e outras intents),
    # mes_ano e janela_meses sejam preenchidos corretamente.
    mes_ano, janela_meses = parse_mes_ano_from_text(pergunta_original)
    
    # Preenche mes_ano se encontrado (ex.: "2025-08")
    if mes_ano:
        entities["mes_ano"] = mes_ano  # ex.: "2025-08"
        # Extrai ano e mês separados para compatibilidade
        ano, mes = mes_ano.split('-')
        entities["ano"] = ano
        entities["mes"] = mes
    
    # Preenche janela_meses se encontrado (ex.: "últimos 6 meses")
    if janela_meses:
        entities["janela_meses"] = janela_meses  # ex.: 6 para "últimos 6 meses"
        # Mantém compatibilidade com código antigo que usa n_meses
        entities["n_meses"] = janela_meses
    
    # Fallback: Se não encontrou com a função melhorada, tenta padrões antigos
    if not entities.get("mes_ano") and not entities.get("n_meses"):
        # Prioridade 1: Padrão "agosto de 2025" ou "agosto/2025"
        mes_ano_patterns = [
            r"(\w+)\s+de\s+(\d{4})",  # "agosto de 2025"
            r"(\w+)\s+/\s+(\d{4})",   # "agosto/2025"
            r"(\w+)\s+-\s+(\d{4})",   # "agosto-2025"
        ]
        
        for pattern in mes_ano_patterns:
            match = re.search(pattern, pergunta_lower)
            if match:
                mes_str = match.group(1)
                ano_str = match.group(2)
                
                # Verifica se é um mês válido
                if mes_str.lower() in MESES_PT:
                    mes_num = MESES_PT[mes_str.lower()]
                    entities["mes"] = f"{mes_num:02d}"
                    entities["ano"] = ano_str
                    entities["mes_ano"] = normalize_mes_ano(entities["mes"], entities["ano"])
                    break
        
        # Prioridade 2: Padrão "2025-08" ou "08/2025"
        if not entities.get("mes_ano"):
            date_patterns = [
                r"(\d{4})[-/](\d{1,2})",  # 2025-08 ou 2025/08
                r"(\d{1,2})[/-](\d{4})",  # 08/2025 ou 08-2025
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, pergunta_original)  # Usa original para manter dígitos
                if match:
                    if len(match.group(1)) == 4:  # Ano primeiro
                        entities["ano"] = match.group(1)
                        mes_num = int(match.group(2))
                        if 1 <= mes_num <= 12:
                            entities["mes"] = f"{mes_num:02d}"
                    else:  # Mês primeiro
                        mes_num = int(match.group(1))
                        if 1 <= mes_num <= 12:
                            entities["mes"] = f"{mes_num:02d}"
                            entities["ano"] = match.group(2)
                    if entities.get("mes") and entities.get("ano"):
                        entities["mes_ano"] = f"{entities['ano']}-{entities['mes']}"
                    break
        
        # Prioridade 3: Mês isolado + ano isolado
        if not entities.get("mes_ano"):
            # Extrai mês por nome
            for mes_nome, mes_num in MESES_PT.items():
                if mes_nome in pergunta_lower and len(mes_nome) >= 3:  # Evita falsos positivos
                    entities["mes"] = f"{mes_num:02d}"
                    
                    # Tenta extrair ano
                    ano_pattern = r"\b(\d{4})\b"
                    ano_match = re.search(ano_pattern, pergunta_original)
                    if ano_match:
                        entities["ano"] = ano_match.group(1)
                        entities["mes_ano"] = normalize_mes_ano(entities["mes"], entities["ano"])
                    else:
                        # Assume ano atual se não especificado
                        entities["ano"] = str(datetime.now().year)
                        entities["mes_ano"] = normalize_mes_ano(entities["mes"], entities["ano"])
                    break
    
    # ========== Extrai PASTA ==========
    # Padrões: "pasta verde", "pasta amarela", "supervisor da pasta verde"
    pasta_patterns = [
        r"pasta\s+(\w+)",  # "pasta verde"
        r"supervisor.*pasta\s+(\w+)",  # "supervisor da pasta verde"
    ]
    
    for pattern in pasta_patterns:
        match = re.search(pattern, pergunta_lower)
        if match:
            pasta = match.group(1).lower()
            # Verifica se é uma pasta conhecida
            if pasta in PASTAS_CONHECIDAS or any(pasta in p for p in PASTAS_CONHECIDAS):
                entities["pasta"] = pasta.title()
                break
    
    # ========== Extrai SUPERVISOR ==========
    # Padrões: "supervisor João", "supervisor da pasta verde"
    supervisor_patterns = [
        r"supervisor\s+da\s+pasta\s+(\w+)",  # "supervisor da pasta amarela"
        r"supervisor\s+([A-ZÁÉÍÓÚÀÈÌÒÙÂÊÎÔÛÃÕÇ][a-záéíóúàèìòùâêîôûãõç]+(?:\s+[A-ZÁÉÍÓÚÀÈÌÒÙÂÊÎÔÛÃÕÇ][a-záéíóúàèìòùâêîôûãõç]+)?)",  # Nome próprio
        r"supervisor\s+([A-Za-z]+)",  # Nome simples
    ]
    
    for pattern in supervisor_patterns:
        match = re.search(pattern, pergunta_original)  # Usa original para manter maiúsculas
        if match:
            supervisor_nome = match.group(1).strip()
            # Se extraiu pasta, não considera como nome de supervisor
            if not entities.get("pasta") or supervisor_nome.lower() not in PASTAS_CONHECIDAS:
                entities["supervisor"] = supervisor_nome.title()
            break
    
    # Se tem pasta mas não tem supervisor nome, pode buscar supervisor da pasta
    if entities.get("pasta") and not entities.get("supervisor"):
        # Deixa para o handler buscar o supervisor pela pasta
        pass
    
    # ========== Extrai DEPARTAMENTO ==========
    # Padrões: "departamento X", "depto Y"
    departamento_patterns = [
        r"departamento\s+([A-Za-z0-9]+)",
        r"depto\s+([A-Za-z0-9]+)",
    ]
    
    for pattern in departamento_patterns:
        match = re.search(pattern, pergunta_lower)
        if match:
            entities["departamento"] = match.group(1).strip()
            break
    
    # ========== Extrai VENDEDOR ==========
    # Padrões: "vendedor João", "vendedor ROTA 77"
    # Só extrai se não tiver encontrado via rota/RCA
    if not entities.get("vendedor"):
        vendedor_patterns = [
            r"vendedor\s+([A-ZÁÉÍÓÚÀÈÌÒÙÂÊÎÔÛÃÕÇ][a-záéíóúàèìòùâêîôûãõç]+(?:\s+[A-ZÁÉÍÓÚÀÈÌÒÙÂÊÎÔÛÃÕÇ][a-záéíóúàèìòùâêîôûãõç]+)?)",  # Nome próprio
            r"vendedor\s+([A-Za-z]+\s+[A-Za-z]+)",  # Nome completo
            r"vendedor\s+([A-Za-z]+)",  # Nome simples
            r"rca\s+([A-Za-z0-9]+)",  # RCA seguido de código/nome
        ]
        
        for pattern in vendedor_patterns:
            match = re.search(pattern, pergunta_original, re.IGNORECASE)
            if match:
                vendedor_nome = match.group(1).strip()
                # Ignora se for "ROTA" ou "RCA" seguido de número (já foi extraído)
                if not re.match(r"^(rota|rca)\s*\d+$", vendedor_nome.lower()):
                    entities["vendedor"] = vendedor_nome
                    break
    
    # ========== Fallback: tenta identificar vendedor por nome próprio isolado ==========
    # Se não encontrou vendedor mas tem um nome próprio no início ou meio da frase
    if not entities.get("vendedor") and not entities.get("rota") and not entities.get("rca"):
        # Padrão: nome próprio seguido de meta/vendas/etc
        nome_proprio_pattern = r"^([A-ZÁÉÍÓÚÀÈÌÒÙÂÊÎÔÛÃÕÇ][a-záéíóúàèìòùâêîôûãõç]+(?:\s+[A-ZÁÉÍÓÚÀÈÌÒÙÂÊÎÔÛÃÕÇ][a-záéíóúàèìòùâêîôûãõç]+)?)\s+(?:tem|tem|bateu|atingiu|a)\s+(?:meta|vendas)"
        match = re.search(nome_proprio_pattern, pergunta_original)
        if match:
                    entities["vendedor"] = match.group(1)
    
    # ========== Extrai PRODUTO ==========
    # Padrões: "produto Nissin", "produto X", "Nissin", "MARILAN"
    # Procura após palavras-chave: "produto", "positivados", "compravam", "abandonaram"
    produto_patterns = [
        r"produto\s+([A-ZÁÉÍÓÚÀÈÌÒÙÂÊÎÔÛÃÕÇ][A-Za-záéíóúàèìòùâêîôûãõç0-9\s]+)",
        r"positivados.*(?:no|em|com)\s+produto\s+([A-ZÁÉÍÓÚÀÈÌÒÙÂÊÎÔÛÃÕÇ][A-Za-záéíóúàèìòùâêîôûãõç0-9\s]+)",
        r"positivados\s+(?:no|em|com)\s+([A-ZÁÉÍÓÚÀÈÌÒÙÂÊÎÔÛÃÕÇ][A-Za-záéíóúàèìòùâêîôûãõç0-9\s]+)",
        r"compravam\s+([A-ZÁÉÍÓÚÀÈÌÒÙÂÊÎÔÛÃÕÇ][A-Za-záéíóúàèìòùâêîôûãõç0-9\s]+)",
        r"abandonaram\s+(?:o|a)\s+produto\s+([A-ZÁÉÍÓÚÀÈÌÒÙÂÊÎÔÛÃÕÇ][A-Za-záéíóúàèìòùâêîôûãõç0-9\s]+)",
        r"abandonaram\s+(?:o|a)\s+([A-ZÁÉÍÓÚÀÈÌÒÙÂÊÎÔÛÃÕÇ][A-Za-záéíóúàèìòùâêîôûãõç0-9\s]+)",
    ]
    
    for pattern in produto_patterns:
        match = re.search(pattern, pergunta_original, re.IGNORECASE)
        if match:
            produto = match.group(1).strip()
            # Remove palavras comuns que podem ter sido capturadas
            produto = re.sub(r'\b(?:o|a|no|em|com|de|do|da|produto)\b', '', produto, flags=re.IGNORECASE).strip()
            if produto and len(produto) > 2:  # Evita falsos positivos muito curtos
                entities["produto"] = produto
                break
    
    # Fallback: se não encontrou produto mas a pergunta menciona marcas conhecidas
    if not entities.get("produto"):
        marcas_conhecidas = ["nissin", "marilan", "ajinomoto", "red bull", "mars", "ype", "condor", "hemmer"]
        for marca in marcas_conhecidas:
            if marca in pergunta_lower:
                entities["produto"] = marca.upper()
                break
    
    # ========== Extrai DIAS_SEM_COMPRA ==========
    # Padrões: "60 dias", "30 dias", "90 dias", "há mais de 60 dias"
    dias_patterns = [
        r"(\d+)\s*dias",
        r"há\s+mais\s+de\s+(\d+)\s*dias",
        r"mais\s+de\s+(\d+)\s*dias",
        r"(\d+)\s*dias\s+sem",
    ]
    
    for pattern in dias_patterns:
        match = re.search(pattern, pergunta_lower)
        if match:
            dias = int(match.group(1))
            if 1 <= dias <= 1000:  # Validação razoável
                entities["dias_sem_compra"] = dias
                break
    
    # Se não encontrou dias_sem_compra, usa default de 60
    if not entities.get("dias_sem_compra"):
        entities["dias_sem_compra"] = 60  # Default
    
    return entities


def detect_intent(pergunta: str) -> Dict[str, Any]:
    """
    Detecta a intenção do usuário a partir de uma pergunta.
    
    Usa padrões de palavras-chave e expressões para identificar
    o tipo de consulta desejada. Prioriza CONSULTA_META para
    perguntas relacionadas a metas.
    
    Args:
        pergunta: Pergunta do usuário em linguagem natural
        
    Returns:
        dict: Dicionário com intenção detectada e parâmetros extraídos
            {
                "intent": IntentType,
                "entities": {
                    "vendedor": str | None,
                    "supervisor": str | None,
                    "mes_ano": str | None,
                    "rota": str | None,
                    "pasta": str | None,
                    "tipo": str | None,
                    ...
                }
            }
    """
    pergunta_lower = pergunta.lower()
    
    # Extrai entidades primeiro
    entities = extract_entities(pergunta)
    
    # Regra explícita: Vendedores + Performance Negativa = CONSULTA_VENDEDORES_PERFORMANCE
    palavras_vendedores = ["vendedor", "vendedores", "rota", "rca"]
    palavras_negativas = [
        "venderam menos", "vendeu menos", "venderam pouco", "vendeu pouco",
        "impacto negativo", "longe da meta", "abaixo da meta",
        "não bateram a meta", "nao bateram a meta", "não bateu a meta", "nao bateu a meta",
        "não atingiram a meta", "nao atingiram a meta", "não atingiu a meta", "nao atingiu a meta",
        "pior desempenho", "pior performance", "ruim desempenho", "ruim performance",
        "menor venda", "menor vendas", "menor faturamento", "menos venderam",
        "impacto negativo", "geraram impacto negativo"
    ]
    
    tem_palavra_vendedor = any(p in pergunta_lower for p in palavras_vendedores)
    tem_palavra_negativa = any(p in pergunta_lower for p in palavras_negativas)
    
    # Se tem ambas condições, prioriza CONSULTA_VENDEDORES_PERFORMANCE
    if tem_palavra_vendedor and tem_palavra_negativa:
        logger.info(f"Intent detectada por regra explícita: CONSULTA_VENDEDORES_PERFORMANCE (vendedores + performance negativa)")
        return {
            "intent": IntentType.CONSULTA_VENDEDORES_PERFORMANCE,
            "entities": entities
        }
    
    # Padrões para detecção de intenção (CONSULTA_META tem prioridade)
    intent_patterns = {
        IntentType.CONSULTA_META: [
            r"mostre.*meta",
            r"qual.*meta",
            r"meta.*(?:de|do|da)",
            r"bateu.*meta",
            r"quem.*bateu.*meta",
            r"metas.*(?:por|por departamento)",
            r"meta.*(?:vendedor|supervisor|departamento|pasta)",
            r"realizado.*meta|meta.*realizado",
            r"atingiu.*meta|meta.*atingiu",
            r"percentual.*atingido",
            r"meta.*últimos.*meses",  # "meta dos últimos meses"
            r"últimos.*meses.*meta",  # "últimos meses de meta"
            r"metas.*últimos",  # "metas dos últimos N meses"
            r"como.*estão.*meta.*últimos",  # "como estão as metas dos últimos meses"
            r"evolução.*meta",  # "evolução das metas"
            r"\bmeta\b",  # Palavra "meta" isolada
        ],
        IntentType.MOTIVO_NAO_BATEU_META: [
            r"por que.*não.*bateu.*meta",
            r"motivo.*não.*bateu",
            r"razão.*não.*atingiu",
            r"por que.*não.*atingiu.*meta",
            r"explicar.*não.*bateu",
            r"análise.*não.*bateu.*meta",
        ],
        IntentType.PREVISAO_BATER_META: [
            r"previsão.*bater.*meta",
            r"probabilidade.*bater",
            r"vai.*bater.*meta",
            r"chance.*bater.*meta",
            r"prever.*meta",
        ],
        IntentType.CLIENTES_RISCO_CHURN: [
            r"clientes.*risco.*churn",
            r"clientes.*churn",
            r"lista.*clientes.*risco",
            r"top.*clientes.*churn",
            r"clientes.*abandonar",
            r"clientes.*perder",
        ],
        IntentType.META_VENDEDOR: [
            r"meta.*vendedor",
            r"vendedor.*meta",
        ],
        IntentType.META_DEPARTAMENTO: [
            r"meta.*departamento",
            r"meta.*supervisor",
            r"supervisor.*meta",
            r"equipe.*meta",
        ],
        IntentType.RESUMO_SUPERVISOR: [
            r"resumo.*supervisor",
            r"resumo.*departamento",
            r"equipe.*supervisor",
            r"supervisor.*resumo",
        ],
        IntentType.CHURN_CLIENTES: [
            r"churn",
            r"risco.*churn",
            r"cliente.*risco",
            r"cliente.*abandonar",
            r"cliente.*sair",
        ],
        IntentType.VENDAS_PREVISAO: [
            r"previsão.*faturamento",
            r"projeção.*vendas",
            r"quanto.*faturar",
            r"quanto.*deve.*faturar",
            r"previsão.*vendas",
            r"projeção.*faturamento",
            r"estimativa.*vendas",
            r"forecast.*vendas",
        ],
        IntentType.VENDAS_ANALISE: [
            r"vendas",
            r"faturamento",
            r"vendas.*mês",
            r"análise.*vendas",
            r"queda.*vendas",
            r"aumento.*vendas",
        ],
        IntentType.PRODUTOS_BAIXA_VENDA: [
            r"produtos.*vendendo.*menos",
            r"produtos.*pior.*desempenho",
            r"produtos.*menos.*vendem",
            r"itens.*giro.*fraco",
            r"produtos.*queda.*vendas",
            r"produtos.*precisam.*impulso",
            r"produtos.*fracos",
            r"produtos.*venda.*baixa",
            r"produtos.*baixa.*venda",
            r"produtos.*menor.*venda",
            r"produtos.*menos.*vendas",
            r"produtos.*pior.*vendas",
            r"produtos.*fraco.*desempenho",
            r"quais.*produtos.*menos.*vendem",
            r"produtos.*ruim.*venda",
            r"produtos.*decrescimo",
            r"produtos.*diminuição",
            r"produtos.*redução.*vendas",
            r"produtos.*queda.*performance",
        ],
        IntentType.CLIENTES_CHURN_PRODUTO: [
            r"clientes.*positivados.*produto",
            r"clientes.*compravam.*pararam",
            r"clientes.*abandonaram.*produto",
            r"clientes.*não.*compram.*produto",
            r"clientes.*sem.*compra.*produto",
            r"lista.*clientes.*produto.*dias",
            r"clientes.*pararam.*comprar",
            r"clientes.*deixaram.*comprar",
            r"quais.*clientes.*positivados",
            r"clientes.*churn.*produto",
        ],
        IntentType.CLIENTES_OPORTUNIDADES: [
            r"clientes.*potencial.*crescimento",
            r"clientes.*oportunidade",
            r"onde.*posso.*crescer",
            r"potencial.*desperdiçado",
            r"gap.*share",
            r"clientes.*recuperar",
            r"oportunidades.*cliente",
            r"clientes.*crescer",
            r"potencial.*recuperação",
        ],
        IntentType.DESEMPENHO_SUPERVISORES: [
            r"desempenho.*supervisor",
            r"qual.*supervisor.*distante.*meta",
            r"quem.*puxando.*resultado.*baixo",
            r"comparar.*supervisores",
            r"supervisores.*performance",
            r"equipes.*desempenho",
            r"gaps.*gestão",
            r"supervisores.*problemas",
            r"supervisores.*abaixo",
        ],
        IntentType.OPORTUNIDADES_DIRETORIA: [
            r"oportunidades.*próximos.*meses",
            r"onde.*posso.*crescer",
            r"maiores.*oportunidades.*recuperação",
            r"resumo.*oportunidades",
            r"visão.*executiva",
            r"oportunidades.*diretor",
            r"o que.*fazer.*crescer",
            r"estratégias.*crescimento",
        ],
        IntentType.CONSULTA_VENDEDORES_PERFORMANCE: [
            r"vendedores.*impacto.*negativo",
            r"vendedores.*venderam.*menos",
            r"vendedores.*pior.*desempenho",
            r"vendedores.*ruim.*performance",
            r"quais.*vendedores.*impacto.*negativo",
            r"quais.*vendedores.*venderam.*menos",
            r"quais.*vendedores.*menos.*venderam",
            r"vendedores.*ficaram.*longe.*meta",
            r"vendedores.*abaixo.*meta",
            r"vendedores.*baixo.*desempenho",
            r"vendedores.*pior.*performance",
            r"vendedores.*menor.*vendas",
            r"vendedores.*menor.*faturamento",
            r"vendedores.*queda.*vendas",
            r"vendedores.*problemas.*performance",
            r"vendedores.*necessitam.*atenção",
            r"ranking.*piores.*vendedores",
            r"piores.*vendedores.*mês",
            r"vendedores.*precisam.*melhorar",
        ],
        IntentType.RANKING: [
            r"ranking",
            r"top.*vendedor",
            r"melhor.*vendedor",
            r"pior.*vendedor",
            r"maior.*vendas",
            r"menor.*vendas",
        ],
        IntentType.EXPLICACAO: [
            r"por que",
            r"motivo",
            r"razão",
            r"explicar",
            r"análise.*motivo",
        ],
    }
    
    # Detecta intenção baseado em padrões
    intent_scores = {}
    for intent, patterns in intent_patterns.items():
        score = 0
        for pattern in patterns:
            if re.search(pattern, pergunta_lower):
                score += 1
        intent_scores[intent] = score
    
    # Prioriza CONSULTA_META fortemente (peso extra +3)
    if intent_scores.get(IntentType.CONSULTA_META, 0) > 0:
        intent_scores[IntentType.CONSULTA_META] += 3
    
    # Prioriza outras intenções específicas
    if intent_scores.get(IntentType.MOTIVO_NAO_BATEU_META, 0) > 0:
        intent_scores[IntentType.MOTIVO_NAO_BATEU_META] += 2
    if intent_scores.get(IntentType.CLIENTES_RISCO_CHURN, 0) > 0:
        intent_scores[IntentType.CLIENTES_RISCO_CHURN] += 2
    if intent_scores.get(IntentType.VENDAS_PREVISAO, 0) > 0:
        intent_scores[IntentType.VENDAS_PREVISAO] += 2  # Prioriza previsão sobre análise
    if intent_scores.get(IntentType.PRODUTOS_BAIXA_VENDA, 0) > 0:
        intent_scores[IntentType.PRODUTOS_BAIXA_VENDA] += 1  # Prioridade média
    if intent_scores.get(IntentType.CLIENTES_CHURN_PRODUTO, 0) > 0:
        intent_scores[IntentType.CLIENTES_CHURN_PRODUTO] += 2  # Prioridade alta
    if intent_scores.get(IntentType.CONSULTA_VENDEDORES_PERFORMANCE, 0) > 0:
        intent_scores[IntentType.CONSULTA_VENDEDORES_PERFORMANCE] += 2  # Prioridade alta
    
    # Intenção com maior score
    detected_intent = max(intent_scores.items(), key=lambda x: x[1]) if intent_scores else (None, 0)
    
    if detected_intent[1] == 0:
        # Nenhum padrão encontrado, tenta inferir pelo contexto das entidades
        if entities.get("vendedor") or entities.get("rota") or entities.get("rca"):
            if "por que" in pergunta_lower or "motivo" in pergunta_lower:
                intent = IntentType.MOTIVO_NAO_BATEU_META
            elif entities.get("tipo") == "meta" or "meta" in pergunta_lower:
                intent = IntentType.CONSULTA_META
            else:
                intent = IntentType.META_VENDEDOR
        elif entities.get("supervisor") or entities.get("pasta"):
            if "meta" in pergunta_lower:
                intent = IntentType.CONSULTA_META
            else:
                intent = IntentType.RESUMO_SUPERVISOR
        elif entities.get("mes_ano") and "meta" in pergunta_lower:
            intent = IntentType.CONSULTA_META
        elif "cliente" in pergunta_lower and ("risco" in pergunta_lower or "churn" in pergunta_lower):
            intent = IntentType.CLIENTES_RISCO_CHURN
        elif "cliente" in pergunta_lower:
            intent = IntentType.CHURN_CLIENTES
        elif ("previsão" in pergunta_lower or "projeção" in pergunta_lower or 
              re.search(r"quanto.*faturar", pergunta_lower)) and entities.get("mes_ano"):
            intent = IntentType.VENDAS_PREVISAO
        elif entities.get("mes_ano") and ("vendas" in pergunta_lower or "faturamento" in pergunta_lower):
            # Verifica se é mês futuro para decidir entre análise e previsão
            try:
                target_date = datetime.strptime(entities["mes_ano"], "%Y-%m")
                now = datetime.now()
                if target_date > datetime(now.year, now.month, 1):
                    intent = IntentType.VENDAS_PREVISAO
                else:
                    intent = IntentType.VENDAS_ANALISE
            except:
                intent = IntentType.VENDAS_ANALISE
        elif ("produtos" in pergunta_lower or "itens" in pergunta_lower) and (
            "menos" in pergunta_lower or "pior" in pergunta_lower or 
            "fracos" in pergunta_lower or "baixa" in pergunta_lower or
            "queda" in pergunta_lower or "fraco" in pergunta_lower or
            re.search(r"precisam.*impulso", pergunta_lower) or "ruim" in pergunta_lower
        ):
            intent = IntentType.PRODUTOS_BAIXA_VENDA
        elif ("cliente" in pergunta_lower and "produto" in pergunta_lower) or \
             ("positivados" in pergunta_lower and entities.get("produto")) or \
             ("abandonaram" in pergunta_lower and entities.get("produto")):
            intent = IntentType.CLIENTES_CHURN_PRODUTO
        elif ("vendedores" in pergunta_lower or "vendedor" in pergunta_lower) and entities.get("mes_ano") and (
            re.search(r"impacto.*negativo", pergunta_lower) or re.search(r"venderam.*menos", pergunta_lower) or
            "pior" in pergunta_lower or re.search(r"menos.*venderam", pergunta_lower) or
            re.search(r"abaixo.*meta", pergunta_lower) or re.search(r"longe.*meta", pergunta_lower) or
            "menos" in pergunta_lower or "impacto" in pergunta_lower or "negativo" in pergunta_lower
        ):
            intent = IntentType.CONSULTA_VENDEDORES_PERFORMANCE
        else:
            intent = IntentType.OUTROS
    else:
        intent = detected_intent[0]
    
    # Se tem entidades relacionadas a meta mas intenção não é CONSULTA_META,
    # força CONSULTA_META se for mais apropriado
    if (entities.get("tipo") == "meta" or 
        entities.get("mes_ano") and "meta" in pergunta_lower or
        (entities.get("vendedor") or entities.get("supervisor") or entities.get("pasta")) and "meta" in pergunta_lower):
        if intent not in [IntentType.MOTIVO_NAO_BATEU_META, IntentType.PREVISAO_BATER_META]:
            intent = IntentType.CONSULTA_META
    
    logger.info(f"Intenção detectada: {intent.value}, entities: {entities}")
    
    return {
        "intent": intent,
        "entities": entities
    }
