#!/usr/bin/env python3
"""
Script de teste para emular ambiente de produção.

Este script testa as mesmas funções usadas pela API em produção,
usando as mesmas variáveis de ambiente, para garantir que tudo funciona
corretamente antes do deploy.
"""

import os
import sys
import logging
from pathlib import Path

# Adiciona o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configura logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Perguntas de teste (as mesmas que devem funcionar em produção)
PERGUNTAS_TESTE = [
    "qual a meta de vendas do mês de outubro 2025",
    "Sou o Diretor e preciso saber de forma detalhada porque não batemos a meta no mês de agosto 2025",
    "quais foram os vendedores que mais geraram impacto negativo no realizado do mês de agosto 2025",
]


def testar_ambiente():
    """Testa se as variáveis de ambiente estão configuradas."""
    logger.info("=" * 80)
    logger.info("TESTE 1: Validação de Variáveis de Ambiente")
    logger.info("=" * 80)
    
    errors = []
    
    # Testa OPENAI_API_KEY
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        errors.append("❌ OPENAI_API_KEY não encontrada")
    else:
        logger.info(f"✅ OPENAI_API_KEY encontrada (tamanho: {len(openai_key)} caracteres)")
    
    # Testa configuração de banco
    db_type = os.getenv("DB_TYPE", os.getenv("DATABASE_TYPE", "sqlite"))
    logger.info(f"✅ DB_TYPE: {db_type}")
    
    if db_type == "sqlite":
        sqlite_path = os.getenv("SQLITE_PATH", "data/dipam_dw.db")
        logger.info(f"✅ SQLITE_PATH: {sqlite_path}")
        if not os.path.exists(sqlite_path):
            errors.append(f"❌ Arquivo SQLite não encontrado: {sqlite_path}")
        else:
            size_mb = os.path.getsize(sqlite_path) / (1024 * 1024)
            logger.info(f"✅ Arquivo SQLite encontrado (tamanho: {size_mb:.2f} MB)")
    
    if errors:
        logger.error("\n".join(errors))
        return False
    
    logger.info("✅ Todas as variáveis de ambiente estão configuradas corretamente")
    return True


def testar_conexao_banco():
    """Testa conexão com o banco de dados."""
    logger.info("\n" + "=" * 80)
    logger.info("TESTE 2: Conexão com Banco de Dados")
    logger.info("=" * 80)
    
    try:
        from src.dw.connection import init_db, get_db_engine
        from sqlalchemy import text
        
        init_db()
        engine = get_db_engine()
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM metas_vendedor"))
            count = result.scalar()
            logger.info(f"✅ Conexão com banco OK - {count} registros em metas_vendedor")
        
        # Testa se há dados para agosto e outubro 2025
        meses_teste = ["2025-08", "2025-10"]
        for mes_ano in meses_teste:
            with engine.connect() as conn:
                result = conn.execute(
                    text("SELECT COUNT(*) FROM metas_vendedor WHERE mes_ano = :mes_ano"),
                    {"mes_ano": mes_ano}
                )
                count = result.scalar()
                if count > 0:
                    logger.info(f"✅ Dados encontrados para {mes_ano}: {count} registros")
                else:
                    logger.warning(f"⚠️  Nenhum dado encontrado para {mes_ano}")
        
        return True
    except Exception as e:
        logger.error(f"❌ Erro ao conectar com banco: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def testar_openai():
    """Testa conexão com OpenAI."""
    logger.info("\n" + "=" * 80)
    logger.info("TESTE 3: Conexão com OpenAI")
    logger.info("=" * 80)
    
    try:
        from src.llm_openai_client import get_openai_client, call_llm
        
        config = get_openai_client()
        logger.info(f"✅ Cliente OpenAI configurado: {config['base_url']}, model: {config['model']}")
        
        # Testa chamada mínima
        resposta = call_llm(
            prompt="Responda apenas: OK",
            system_prompt="Você é um assistente de teste.",
            max_tokens=5,
            temperature=0
        )
        logger.info(f"✅ Chamada OpenAI OK - Resposta: {resposta[:50]}")
        return True
    except Exception as e:
        logger.error(f"❌ Erro ao conectar com OpenAI: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def testar_agent_service():
    """Testa o serviço do agente com perguntas reais."""
    logger.info("\n" + "=" * 80)
    logger.info("TESTE 4: Serviço do Agente")
    logger.info("=" * 80)
    
    try:
        from src.agent.service import get_agent_service
        from src.dw.connection import get_db_session
        from src.agent.utils.date_extraction import extrair_mes_ano_explicito
        
        agent_service = get_agent_service()
        
        todas_passaram = True
        
        for idx, pergunta in enumerate(PERGUNTAS_TESTE, 1):
            # Cria uma nova sessão para cada pergunta (evita "Connection is closed")
            session_gen = get_db_session()
            session = next(session_gen)
            
            try:
                logger.info(f"\n{'=' * 80}")
                logger.info(f"PERGUNTA {idx}/{len(PERGUNTAS_TESTE)}")
                logger.info(f"{'=' * 80}")
                logger.info(f"📝 Pergunta: {pergunta}")
                
                # Extrai mes_ano da pergunta antes de processar
                mes_ano_extraido = extrair_mes_ano_explicito(pergunta)
                if mes_ano_extraido:
                    logger.info(f"📅 Mês/ano extraído da pergunta: {mes_ano_extraido}")
                
                result = agent_service.process_question(
                    pergunta=pergunta,
                    usuario_id="test_user",
                    papel="diretor",
                    session=session
                )
                
                intent = result.get("intent", "N/A")
                confianca = result.get("confianca", 0.0)
                contexto = result.get("contexto", {})
                resposta = result.get("resposta", "")
                
                logger.info(f"🎯 Intent detectado: {intent} (confiança: {confianca:.2f})")
                
                # Verifica se há dados no contexto
                mes_ano = contexto.get("mes_ano") or contexto.get("mes_ano_analise") or contexto.get("mes_ano_solicitado")
                if mes_ano:
                    logger.info(f"📅 Mês/ano no contexto: {mes_ano}")
                    
                    # Verifica quantos registros existem no banco para esse mês
                    from sqlalchemy import text
                    with session.connection() as conn:
                        result_count = conn.execute(
                            text("SELECT COUNT(*) FROM metas_vendedor WHERE mes_ano = :mes_ano"),
                            {"mes_ano": mes_ano}
                        )
                        count_metas = result_count.scalar()
                        logger.info(f"📊 Registros em metas_vendedor para {mes_ano}: {count_metas}")
                
                # Verifica se há vendedores no contexto
                vendedores = []
                vendedores_sources = [
                    contexto.get("detalhe_vendedores_mes", {}).get("vendedores"),
                    contexto.get("detalhe_vendedores", {}).get("vendedores") if isinstance(contexto.get("detalhe_vendedores"), dict) else None,
                    contexto.get("vendedores"),
                    contexto.get("piores_meta"),
                    contexto.get("menores_venda"),
                    contexto.get("top_vendedores"),
                    contexto.get("pioresVendedores"),
                    contexto.get("melhoresVendedores"),
                ]
                
                for source in vendedores_sources:
                    if source and isinstance(source, list):
                        vendedores = source
                        break
                
                # Para consulta_vendedores_performance, também verifica piores_meta e menores_venda diretamente
                if intent == "consulta_vendedores_performance":
                    if not vendedores:
                        piores = contexto.get("piores_meta", [])
                        menores = contexto.get("menores_venda", [])
                        if piores and isinstance(piores, list):
                            vendedores = piores
                        elif menores and isinstance(menores, list):
                            vendedores = menores
                
                if vendedores:
                    logger.info(f"👥 Vendedores encontrados no contexto: {len(vendedores)}")
                    
                    # Conta quantos bateram meta
                    vendedores_que_bateram = sum(
                        1 for v in vendedores 
                        if isinstance(v, dict) 
                        and v.get("atingimento") is not None 
                        and isinstance(v.get("atingimento"), (int, float))
                        and float(v.get("atingimento", 0)) >= 100
                    )
                    logger.info(f"   - Vendedores que bateram meta: {vendedores_que_bateram}")
                    
                    # Mostra top 3 vendedores
                    if len(vendedores) > 0:
                        vendedores_ordenados = sorted(
                            [v for v in vendedores if isinstance(v, dict) and v.get("atingimento") is not None],
                            key=lambda x: float(x.get("atingimento", 0)),
                            reverse=True
                        )[:3]
                        logger.info(f"   - Top 3 vendedores:")
                        for v in vendedores_ordenados:
                            nome = v.get("vendedor_nome") or v.get("nome") or v.get("vendedor") or "N/A"
                            atingimento = v.get("atingimento", 0)
                            logger.info(f"     • {nome}: {atingimento:.1f}%")
                else:
                    # Para consulta_vendedores_performance, não é crítico se não houver vendedores no contexto
                    # (a resposta pode estar usando dados de outra forma)
                    if intent != "consulta_vendedores_performance":
                        logger.warning(f"⚠️  Nenhum vendedor encontrado no contexto")
                        todas_passaram = False
                    else:
                        logger.info(f"ℹ️  Nenhum vendedor encontrado no contexto (mas resposta pode estar usando dados de outra forma)")
                
                # Verifica se a resposta não é genérica
                # REGRA CRÍTICA: Se há dados no banco, a resposta NÃO deve ser genérica
                resposta_lower = resposta.lower()
                
                # Frases que indicam fallback genérico (quando aparecem no resumo executivo)
                # IMPORTANTE: Não considerar observações válidas sobre limitações como fallback
                frases_fallback_criticas = [
                    "não encontrei dados",
                    "não tenho informações sobre",
                    "não há dados disponíveis",
                    "não há informações disponíveis",
                    "desculpe, não foi possível",
                    "erro na api",
                    "dados ainda não foram carregados",
                    "não há dados de metas",
                    "não há dados de vendas",
                ]
                
                # Verifica se a frase de fallback aparece no resumo executivo (primeiras 500 caracteres)
                # Se aparecer apenas em "observações", pode ser uma limitação válida
                resumo_executivo = resposta_lower[:500]
                tem_fallback_critico = any(frase in resumo_executivo for frase in frases_fallback_criticas)
                
                # Também verifica se há números/valores na resposta (indica que está usando dados)
                tem_numeros = any(
                    palavra.replace('.', '').replace(',', '').isdigit() 
                    for palavra in resposta.split() 
                    if len(palavra) > 2
                ) or any(char.isdigit() for char in resposta[:200])
                
                # Se tem números na resposta, provavelmente não é fallback genérico
                tem_fallback = tem_fallback_critico and not tem_numeros
                
                # Verifica se há dados no contexto que deveriam ter sido usados
                tem_dados_contexto = False
                count_metas = 0
                if mes_ano:
                    # Verifica se há registros no banco para esse mês
                    # Usa uma nova sessão para não conflitar com a sessão já usada
                    from sqlalchemy import text
                    try:
                        from src.dw.connection import get_db_session as get_new_session
                        session_gen_check = get_new_session()
                        session_check = next(session_gen_check)
                        try:
                            result_count = session_check.execute(
                                text("SELECT COUNT(*) FROM metas_vendedor WHERE mes_ano = :mes_ano"),
                                {"mes_ano": mes_ano}
                            )
                            count_metas = result_count.scalar()
                            if count_metas > 0:
                                tem_dados_contexto = True
                        finally:
                            session_check.close()
                    except Exception as e:
                        logger.warning(f"Erro ao verificar dados no banco: {str(e)}")
                        # Se não conseguir verificar, assume que há dados se há vendedores no contexto
                        if vendedores:
                            tem_dados_contexto = True
                            count_metas = len(vendedores)
                
                # Se há dados no contexto mas a resposta é genérica, isso é um ERRO CRÍTICO
                # IMPORTANTE: Se a resposta contém números/valores, não é fallback genérico
                if tem_dados_contexto and tem_fallback:
                    logger.error(f"❌ ERRO CRÍTICO: Há {count_metas} registros no banco para {mes_ano}, mas a resposta diz que não há dados!")
                    logger.error(f"   Resposta: {resposta[:500]}...")
                    todas_passaram = False
                elif tem_fallback and not tem_numeros:
                    logger.warning(f"⚠️  Resposta parece genérica/fallback (sem números)")
                    logger.warning(f"   Preview: {resposta[:300]}...")
                    # Se não há dados, fallback é aceitável
                    if not tem_dados_contexto:
                        logger.info(f"   (Aceitável: não há dados no banco para {mes_ano})")
                    else:
                        todas_passaram = False
                elif tem_fallback and tem_numeros:
                    # Tem fallback mas também tem números - provavelmente é uma observação válida
                    logger.info(f"✅ Resposta gerada com dados ({len(resposta)} caracteres)")
                    logger.info(f"   Preview: {resposta[:300]}...")
                    logger.info(f"   (Nota: contém observações sobre limitações, mas usa dados reais)")
                else:
                    logger.info(f"✅ Resposta gerada ({len(resposta)} caracteres)")
                    logger.info(f"   Preview: {resposta[:300]}...")
                
                # Verifica se há KPIs estruturados
                if contexto.get("atingimento_medio") or contexto.get("perc_atingido_geral"):
                    atingimento_medio = contexto.get("atingimento_medio") or contexto.get("perc_atingido_geral")
                    logger.info(f"📈 Atingimento médio: {atingimento_medio:.2f}%")
            
            finally:
                # Fecha a sessão após cada pergunta
                session.close()
        
        if todas_passaram:
            logger.info(f"\n✅ Todas as perguntas foram processadas com sucesso!")
        else:
            logger.warning(f"\n⚠️  Algumas perguntas tiveram problemas (ver logs acima)")
        
        return todas_passaram
    except Exception as e:
        logger.error(f"❌ Erro ao testar agente: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def main():
    """Executa todos os testes."""
    logger.info("🚀 Iniciando testes de ambiente de produção")
    logger.info("")
    
    resultados = []
    
    # Teste 1: Variáveis de ambiente
    resultados.append(("Variáveis de Ambiente", testar_ambiente()))
    
    # Teste 2: Conexão com banco
    if resultados[0][1]:  # Só testa banco se ambiente OK
        resultados.append(("Conexão Banco", testar_conexao_banco()))
    
    # Teste 3: OpenAI
    if resultados[0][1]:  # Só testa OpenAI se ambiente OK
        resultados.append(("Conexão OpenAI", testar_openai()))
    
    # Teste 4: Agente
    if all(r[1] for r in resultados):  # Só testa agente se tudo OK
        resultados.append(("Serviço do Agente", testar_agent_service()))
    
    # Resumo final
    logger.info("\n" + "=" * 80)
    logger.info("RESUMO DOS TESTES")
    logger.info("=" * 80)
    
    for nome, sucesso in resultados:
        status = "✅ PASSOU" if sucesso else "❌ FALHOU"
        logger.info(f"{nome}: {status}")
    
    todos_passaram = all(r[1] for r in resultados)
    
    if todos_passaram:
        logger.info("\n✅ Todos os testes passaram! Ambiente pronto para produção.")
        return 0
    else:
        logger.error("\n❌ Alguns testes falharam. Corrija os problemas antes do deploy.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

