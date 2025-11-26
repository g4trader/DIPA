"""
Integração específica para Q2: Queda de Faturamento (mês a mês).

Este módulo contém funções para:
1. Detectar perguntas sobre queda de faturamento (NLU baseado em regras)
2. Parsear períodos mencionados na pergunta
3. Gerar IntentSpec para Q2
4. Integrar com o orquestrador DW
"""

import logging
import re
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from calendar import monthrange

from src.agent.intent_spec import IntentSpec

logger = logging.getLogger(__name__)

# ============================================================================
# CONSTANTES E CONFIGURAÇÕES
# ============================================================================

# Palavras-chave que indicam queda de faturamento
PALAVRAS_QUEDA = [
    "queda de faturamento",
    "queda nas vendas",
    "queda no faturamento",
    "despencaram",
    "reduziram as compras",
    "caíram muito",
    "reduziram vendas",
    "diminuíram compras",
    "pararam de comprar",
    "reduziram muito",
    "queda",
    "redução",
    "diminuição",
    "decréscimo",
    "baixou",
    "caiu",
    "reduziu"
]

# Padrões de período
MESES_PT = {
    "janeiro": 1, "fevereiro": 2, "março": 3, "abril": 4,
    "maio": 5, "junho": 6, "julho": 7, "agosto": 8,
    "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12
}

MESES_PT_ABREV = {
    "jan": 1, "fev": 2, "mar": 3, "abr": 4,
    "mai": 5, "jun": 6, "jul": 7, "ago": 8,
    "set": 9, "out": 10, "nov": 11, "dez": 12
}


# ============================================================================
# DETECÇÃO DE INTENT Q2
# ============================================================================

def detectar_intent_q2(pergunta: str) -> bool:
    """
    Detecta se a pergunta é sobre queda de faturamento (Q2).
    
    Usa detecção baseada em palavras-chave e padrões simples.
    
    Args:
        pergunta: Pergunta do usuário em linguagem natural
        
    Returns:
        True se a pergunta parece ser sobre Q2, False caso contrário
    """
    pergunta_lower = pergunta.lower()
    
    # Verifica se contém palavras-chave de queda
    tem_palavra_queda = any(palavra in pergunta_lower for palavra in PALAVRAS_QUEDA)
    
    if not tem_palavra_queda:
        return False
    
    # Verifica se menciona período ou comparação temporal
    # Padrões: "de X para Y", "entre X e Y", "último mês", "mês passado", etc.
    padroes_periodo = [
        r"de\s+\w+\s+para\s+\w+",
        r"entre\s+\w+\s+e\s+\w+",
        r"último\s+mês",
        r"mês\s+passado",
        r"este\s+mês",
        r"mês\s+atual",
        r"trimestre",
        r"\d{4}",
        r"setembro|outubro|novembro|dezembro|janeiro|fevereiro|março|abril|maio|junho|julho|agosto"
    ]
    
    tem_periodo = any(re.search(padrao, pergunta_lower) for padrao in padroes_periodo)
    
    # Se tem palavra de queda E (menciona período OU menciona comparação/cliente)
    if tem_periodo or "cliente" in pergunta_lower or "clientes" in pergunta_lower:
        logger.info(f"[detectar_intent_q2] ✅ Detectado Q2 na pergunta: {pergunta[:100]}")
        return True
    
    return False


# ============================================================================
# PARSE DE PERÍODO
# ============================================================================

def parse_periodo_queda_faturamento(texto_usuario: str) -> Dict[str, Any]:
    """
    Extrai parâmetros de período da pergunta do usuário.
    
    Suporta formatos como:
    - "de setembro para outubro"
    - "de set/25 para out/25"
    - "último mês"
    - "no trimestre atual"
    - "setembro 2025 x outubro 2025"
    
    Args:
        texto_usuario: Texto da pergunta do usuário
        
    Returns:
        Dict com:
        - data_ini_mes_anterior: "YYYY-MM-DD" ou None
        - data_fim_mes_anterior: "YYYY-MM-DD" ou None
        - data_ini_mes_atual: "YYYY-MM-DD" ou None
        - data_fim_mes_atual: "YYYY-MM-DD" ou None
        - ano: int (ano de referência)
    """
    texto_lower = texto_usuario.lower()
    hoje = datetime.now()
    ano_atual = hoje.year
    
    resultado = {
        "data_ini_mes_anterior": None,
        "data_fim_mes_anterior": None,
        "data_ini_mes_atual": None,
        "data_fim_mes_atual": None,
        "ano": ano_atual
    }
    
    # Padrão 1: "de [mês] para [mês]" ou "de [mês] x [mês]"
    padrao_de_para = re.search(
        r"de\s+(\w+)\s+(?:para|x|e)\s+(\w+)",
        texto_lower
    )
    if padrao_de_para:
        mes1_str = padrao_de_para.group(1)
        mes2_str = padrao_de_para.group(2)
        
        # Extrai ano se mencionado
        ano_match = re.search(r"(\d{4})", texto_usuario)
        ano = int(ano_match.group(1)) if ano_match else ano_atual
        
        mes1 = _parse_mes(mes1_str, ano)
        mes2 = _parse_mes(mes2_str, ano)
        
        if mes1 and mes2:
            # mes1 é o anterior, mes2 é o atual
            resultado["data_ini_mes_anterior"] = f"{ano}-{mes1:02d}-01"
            resultado["data_fim_mes_anterior"] = f"{ano}-{mes1:02d}-{monthrange(ano, mes1)[1]}"
            resultado["data_ini_mes_atual"] = f"{ano}-{mes2:02d}-01"
            resultado["data_fim_mes_atual"] = f"{ano}-{mes2:02d}-{monthrange(ano, mes2)[1]}"
            resultado["ano"] = ano
            logger.info(f"[parse_periodo_queda_faturamento] Padrão 'de X para Y': {mes1}/{ano} → {mes2}/{ano}")
            return resultado
    
    # Padrão 2: "último mês" ou "mês passado"
    if re.search(r"último\s+mês|mês\s+passado", texto_lower):
        # Mês anterior ao atual
        mes_anterior = hoje.replace(day=1) - timedelta(days=1)
        mes_atual = hoje.replace(day=1)
        
        ano_anterior = mes_anterior.year
        mes_num_anterior = mes_anterior.month
        ano_atual = mes_atual.year
        mes_num_atual = mes_atual.month
        
        resultado["data_ini_mes_anterior"] = f"{ano_anterior}-{mes_num_anterior:02d}-01"
        resultado["data_fim_mes_anterior"] = f"{ano_anterior}-{mes_num_anterior:02d}-{monthrange(ano_anterior, mes_num_anterior)[1]}"
        resultado["data_ini_mes_atual"] = f"{ano_atual}-{mes_num_atual:02d}-01"
        resultado["data_fim_mes_atual"] = f"{ano_atual}-{mes_num_atual:02d}-{monthrange(ano_atual, mes_num_atual)[1]}"
        resultado["ano"] = ano_atual
        logger.info(f"[parse_periodo_queda_faturamento] Padrão 'último mês': {mes_num_anterior}/{ano_anterior} → {mes_num_atual}/{ano_atual}")
        return resultado
    
    # Padrão 3: "no trimestre atual" ou "este trimestre"
    if re.search(r"trimestre\s+atual|este\s+trimestre", texto_lower):
        # Assume comparação entre dois meses do trimestre atual
        # Por exemplo: se estamos em outubro (Q4), compara setembro (mês 1) com outubro (mês 2)
        mes_atual = hoje.month
        trimestre = (mes_atual - 1) // 3 + 1
        primeiro_mes_trimestre = (trimestre - 1) * 3 + 1
        segundo_mes_trimestre = primeiro_mes_trimestre + 1
        
        if segundo_mes_trimestre <= 12:
            resultado["data_ini_mes_anterior"] = f"{ano_atual}-{primeiro_mes_trimestre:02d}-01"
            resultado["data_fim_mes_anterior"] = f"{ano_atual}-{primeiro_mes_trimestre:02d}-{monthrange(ano_atual, primeiro_mes_trimestre)[1]}"
            resultado["data_ini_mes_atual"] = f"{ano_atual}-{segundo_mes_trimestre:02d}-01"
            resultado["data_fim_mes_atual"] = f"{ano_atual}-{segundo_mes_trimestre:02d}-{monthrange(ano_atual, segundo_mes_trimestre)[1]}"
            resultado["ano"] = ano_atual
            logger.info(f"[parse_periodo_queda_faturamento] Padrão 'trimestre atual': {primeiro_mes_trimestre}/{ano_atual} → {segundo_mes_trimestre}/{ano_atual}")
            return resultado
    
    # Padrão 4: Menciona meses específicos (ex: "setembro" e "outubro")
    meses_encontrados = []
    for mes_nome, mes_num in MESES_PT.items():
        if mes_nome in texto_lower:
            meses_encontrados.append((mes_num, mes_nome))
    
    if len(meses_encontrados) >= 2:
        # Ordena por ordem de aparição no texto
        meses_encontrados.sort(key=lambda x: texto_lower.find(x[1]))
        mes1_num, mes1_nome = meses_encontrados[0]
        mes2_num, mes2_nome = meses_encontrados[1]
        
        # Extrai ano se mencionado
        ano_match = re.search(r"(\d{4})", texto_usuario)
        ano = int(ano_match.group(1)) if ano_match else ano_atual
        
        resultado["data_ini_mes_anterior"] = f"{ano}-{mes1_num:02d}-01"
        resultado["data_fim_mes_anterior"] = f"{ano}-{mes1_num:02d}-{monthrange(ano, mes1_num)[1]}"
        resultado["data_ini_mes_atual"] = f"{ano}-{mes2_num:02d}-01"
        resultado["data_fim_mes_atual"] = f"{ano}-{mes2_num:02d}-{monthrange(ano, mes2_num)[1]}"
        resultado["ano"] = ano
        logger.info(f"[parse_periodo_queda_faturamento] Padrão 'meses específicos': {mes1_nome}/{ano} → {mes2_nome}/{ano}")
        return resultado
    
    # Padrão 5: Formato "set/25" ou "09/25"
    padrao_mes_ano = re.findall(r"(\w+)/(\d{2,4})|(\d{1,2})/(\d{2,4})", texto_usuario)
    if len(padrao_mes_ano) >= 2:
        # Processa primeiro par
        par1 = padrao_mes_ano[0]
        par2 = padrao_mes_ano[1]
        
        mes1 = _parse_mes_ano(par1)
        mes2 = _parse_mes_ano(par2)
        
        if mes1 and mes2:
            ano = mes1["ano"] if mes1["ano"] >= 2000 else 2000 + mes1["ano"]
            resultado["data_ini_mes_anterior"] = f"{ano}-{mes1['mes']:02d}-01"
            resultado["data_fim_mes_anterior"] = f"{ano}-{mes1['mes']:02d}-{monthrange(ano, mes1['mes'])[1]}"
            resultado["data_ini_mes_atual"] = f"{ano}-{mes2['mes']:02d}-01"
            resultado["data_fim_mes_atual"] = f"{ano}-{mes2['mes']:02d}-{monthrange(ano, mes2['mes'])[1]}"
            resultado["ano"] = ano
            logger.info(f"[parse_periodo_queda_faturamento] Padrão 'mes/ano': {mes1['mes']}/{ano} → {mes2['mes']}/{ano}")
            return resultado
    
    # Padrão padrão: se não encontrou nada específico, usa set/25 e out/25 (demo)
    logger.warning(f"[parse_periodo_queda_faturamento] Não foi possível extrair período, usando padrão set/25 → out/25")
    resultado["data_ini_mes_anterior"] = "2025-09-01"
    resultado["data_fim_mes_anterior"] = "2025-09-30"
    resultado["data_ini_mes_atual"] = "2025-10-01"
    resultado["data_fim_mes_atual"] = "2025-10-31"
    resultado["ano"] = 2025
    
    return resultado


def _parse_mes(mes_str: str, ano: int) -> Optional[int]:
    """
    Converte string de mês para número.
    
    Args:
        mes_str: String do mês (ex: "setembro", "set", "09")
        ano: Ano de referência
        
    Returns:
        Número do mês (1-12) ou None se não conseguir parsear
    """
    mes_str_lower = mes_str.lower().strip()
    
    # Tenta nome completo
    if mes_str_lower in MESES_PT:
        return MESES_PT[mes_str_lower]
    
    # Tenta abreviação
    if mes_str_lower in MESES_PT_ABREV:
        return MESES_PT_ABREV[mes_str_lower]
    
    # Tenta número
    try:
        mes_num = int(mes_str_lower)
        if 1 <= mes_num <= 12:
            return mes_num
    except ValueError:
        pass
    
    return None


def _parse_mes_ano(par: Tuple[str, ...]) -> Optional[Dict[str, int]]:
    """
    Parseia par (mes, ano) de formato "set/25" ou "09/25".
    
    Args:
        par: Tupla com (mes_str, ano_str) ou (mes_num, ano_str)
        
    Returns:
        Dict com {"mes": int, "ano": int} ou None
    """
    if len(par) < 2:
        return None
    
    mes_str = par[0] if par[0] else par[2]  # Pode estar em posição 0 ou 2
    ano_str = par[1] if par[1] else par[3]  # Pode estar em posição 1 ou 3
    
    if not mes_str or not ano_str:
        return None
    
    # Parseia mês
    mes = _parse_mes(mes_str, 2025)
    if not mes:
        return None
    
    # Parseia ano
    try:
        ano = int(ano_str)
        if ano < 100:
            ano = 2000 + ano
    except ValueError:
        return None
    
    return {"mes": mes, "ano": ano}


# ============================================================================
# GERAÇÃO DE INTENTSPEC PARA Q2
# ============================================================================

def gerar_intent_spec_q2(pergunta: str) -> IntentSpec:
    """
    Gera IntentSpec para Q2 a partir da pergunta do usuário.
    
    Args:
        pergunta: Pergunta do usuário em linguagem natural
        
    Returns:
        IntentSpec configurado para Q2
    """
    # Parseia período
    periodo_params = parse_periodo_queda_faturamento(pergunta)
    
    # Monta filtros
    filtros = {
        "data_ini_mes_anterior": periodo_params["data_ini_mes_anterior"],
        "data_fim_mes_anterior": periodo_params["data_fim_mes_anterior"],
        "data_ini_mes_atual": periodo_params["data_ini_mes_atual"],
        "data_fim_mes_atual": periodo_params["data_fim_mes_atual"],
        "min_faturamento_mes_anterior": 500.0,
        "min_queda_percentual": 10.0,
        "limit": 100
    }
    
    # Detecta se menciona "top N"
    top_match = re.search(r"top\s+(\d+)|os\s+(\d+)\s+maiores", pergunta.lower())
    if top_match:
        top_n = int(top_match.group(1) or top_match.group(2))
        filtros["limit"] = top_n
    
    # Cria IntentSpec
    intent_spec = IntentSpec(
        tipo="queda_faturamento",
        periodo_inicio=periodo_params["data_ini_mes_anterior"],
        periodo_fim=periodo_params["data_fim_mes_atual"],
        dimensao_principal="cliente",
        filtros=filtros
    )
    
    logger.info(
        f"[gerar_intent_spec_q2] IntentSpec Q2 criado: "
        f"periodo={periodo_params['data_ini_mes_anterior']} → {periodo_params['data_fim_mes_atual']}, "
        f"limit={filtros['limit']}"
    )
    
    return intent_spec


# ============================================================================
# INTEGRAÇÃO COM ORQUESTRADOR
# ============================================================================

def executar_q2_via_orquestrador(
    pergunta: str,
    intent_spec: Optional[IntentSpec] = None,
    incluir_texto_executivo: bool = True
) -> Dict[str, Any]:
    """
    Executa Q2 via orquestrador DW e formata resposta executiva.
    
    Args:
        pergunta: Pergunta do usuário
        intent_spec: IntentSpec (se None, será gerado automaticamente)
        incluir_texto_executivo: Se True, gera texto executivo formatado
        
    Returns:
        Dict com:
        - tipo: "Q2_QUEDA_FATURAMENTO"
        - dados_dw: resultado do orquestrador
        - periodo: parâmetros de período
        - texto_executivo: texto formatado (se incluir_texto_executivo=True)
        - periodo_descricao: descrição do período (se incluir_texto_executivo=True)
        - intent_spec: IntentSpec usado
    """
    # Importa dentro da função para permitir mock nos testes
    from src.agent.orquestrador_dw import executar_intent_spec as _executar_intent_spec
    
    # Gera IntentSpec se não fornecido
    if intent_spec is None:
        intent_spec = gerar_intent_spec_q2(pergunta)
    
    # Executa via orquestrador
    try:
        resultado_dw = _executar_intent_spec(intent_spec)
        
        # Extrai parâmetros de período do IntentSpec
        periodo = {
            "data_ini_mes_anterior": intent_spec.filtros.get("data_ini_mes_anterior"),
            "data_fim_mes_anterior": intent_spec.filtros.get("data_fim_mes_anterior"),
            "data_ini_mes_atual": intent_spec.filtros.get("data_ini_mes_atual"),
            "data_fim_mes_atual": intent_spec.filtros.get("data_fim_mes_atual")
        }
        
        resultado = {
            "tipo": "Q2_QUEDA_FATURAMENTO",
            "dados_dw": resultado_dw,
            "periodo": periodo,
            "intent_spec": intent_spec
        }
        
        # Gera texto executivo se solicitado
        if incluir_texto_executivo:
            try:
                from src.agent.formatadores_resposta import formatar_resposta_q2_completa
                resultado_formatado = formatar_resposta_q2_completa(
                    resultado,
                    incluir_dados_estruturados=True
                )
                resultado["texto_executivo"] = resultado_formatado["texto_executivo"]
                resultado["periodo_descricao"] = resultado_formatado["periodo"]
            except Exception as e:
                logger.warning(f"[executar_q2_via_orquestrador] Erro ao gerar texto executivo: {e}")
                resultado["texto_executivo"] = "Não foi possível gerar o texto executivo."
        
        return resultado
        
    except Exception as e:
        logger.error(f"[executar_q2_via_orquestrador] Erro ao executar Q2: {e}")
        raise


# ============================================================================
# FUNÇÃO PRINCIPAL DE INTEGRAÇÃO
# ============================================================================

def processar_pergunta_q2(pergunta: str) -> Dict[str, Any]:
    """
    Função principal para processar perguntas sobre Q2.
    
    Detecta se é Q2, parseia período, gera IntentSpec e executa.
    
    Args:
        pergunta: Pergunta do usuário
        
    Returns:
        Dict com resultado completo da Q2
    """
    # Detecta se é Q2
    if not detectar_intent_q2(pergunta):
        raise ValueError("Pergunta não é sobre queda de faturamento (Q2)")
    
    # Gera IntentSpec
    intent_spec = gerar_intent_spec_q2(pergunta)
    
    # Executa via orquestrador
    resultado = executar_q2_via_orquestrador(pergunta, intent_spec)
    
    return resultado

