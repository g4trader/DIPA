#!/usr/bin/env python3
"""
Script para testar perguntas localmente usando o novo fluxo refatorado.

Uso:
    python -m scripts.testar_pergunta_local "Liste as metas por mês de todo o período que você tem."
"""

import sys
import json
from pathlib import Path

# Adiciona o diretório raiz ao path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

# Importa diretamente para evitar importar src.dw.__init__.py que importa etl.py
import importlib.util
import os

# Importa connection diretamente
base_dir = os.path.dirname(os.path.dirname(__file__))
connection_path = os.path.join(base_dir, "src", "dw", "connection.py")
spec_connection = importlib.util.spec_from_file_location("connection", connection_path)
connection = importlib.util.module_from_spec(spec_connection)
spec_connection.loader.exec_module(connection)

get_db_session = connection.get_db_session
init_db = connection.init_db

from src.agent.handler_dw_refatorado import processar_pergunta_com_dw


def main():
    """Testa uma pergunta usando o novo fluxo refatorado."""
    # Pergunta padrão ou da linha de comando
    if len(sys.argv) > 1:
        pergunta = " ".join(sys.argv[1:])
    else:
        pergunta = "Liste as metas por mês de todo o período que você tem."
    
    print("=" * 80)
    print("TESTE LOCAL - DIPAM COPILOT™")
    print("=" * 80)
    print()
    print(f"📋 Pergunta: {pergunta}")
    print()
    print("🔄 Processando...")
    print()
    
    # Inicializa banco
    init_db(create_tables_if_not_exists=True)
    
    # Processa pergunta
    with get_db_session() as session:
        try:
            resposta = processar_pergunta_com_dw(
                pergunta=pergunta,
                session=session,
                papel="diretor"
            )
            
            # Exibe resultado
            print("=" * 80)
            print("✅ RESPOSTA GERADA")
            print("=" * 80)
            print()
            
            # IntentSpec
            intent_spec = resposta.get("intent_spec")
            if intent_spec:
                print("📋 IntentSpec:")
                print(f"   Tipo: {intent_spec.tipo}")
                print(f"   Dimensão Principal: {intent_spec.dimensao_principal}")
                print(f"   Período: {intent_spec.periodo_inicio} a {intent_spec.periodo_fim}")
                print()
            
            # Resumo Executivo
            resumo = resposta.get("resumo_executivo", "")
            if resumo:
                print("📝 Resumo Executivo:")
                print(f"   {resumo}")
                print()
            
            # Período Analisado
            periodo = resposta.get("periodo_analisado", {})
            if periodo:
                print("📅 Período Analisado:")
                print(f"   Início: {periodo.get('inicio', 'N/A')}")
                print(f"   Fim: {periodo.get('fim', 'N/A')}")
                print()
            
            # Tabela Principal
            tabela = resposta.get("tabela_principal", [])
            if tabela:
                print("📊 Tabela Principal:")
                for i, item in enumerate(tabela, 1):
                    if isinstance(item, dict):
                        colunas = item.get("colunas", [])
                        linhas = item.get("linhas", [])
                        print(f"   Tabela {i}:")
                        print(f"      Colunas: {', '.join(colunas)}")
                        print(f"      Linhas: {len(linhas)} registros")
                        if linhas:
                            print(f"      Primeiras 3 linhas:")
                            for linha in linhas[:3]:
                                print(f"         {linha}")
                print()
            
            # Insights
            insights = resposta.get("insights", [])
            if insights:
                print("💡 Insights:")
                for i, insight in enumerate(insights, 1):
                    print(f"   {i}. {insight}")
                print()
            
            # Regras Aplicadas
            regras_aplicadas = resposta.get("regras_aplicadas")
            if regras_aplicadas:
                print("🔧 Regras Aplicadas:")
                print(f"   {json.dumps(regras_aplicadas, indent=2, ensure_ascii=False)}")
                print()
            
            # Dados DW
            dados_dw = resposta.get("dados_dw", {})
            if dados_dw:
                tem_dados = dados_dw.get("tem_dados", False)
                print(f"📦 Dados DW: {'✅ Tem dados' if tem_dados else '❌ Sem dados'}")
                if tem_dados:
                    dados = dados_dw.get("dados", [])
                    print(f"   Total de registros: {len(dados)}")
                print()
            
            # JSON Completo (opcional)
            print("=" * 80)
            print("📄 JSON Completo (primeiros 500 caracteres):")
            print("=" * 80)
            resposta_json = json.dumps(resposta, indent=2, ensure_ascii=False, default=str)
            print(resposta_json[:500] + "..." if len(resposta_json) > 500 else resposta_json)
            print()
            
        except Exception as e:
            print("=" * 80)
            print("❌ ERRO AO PROCESSAR PERGUNTA")
            print("=" * 80)
            print(f"Erro: {str(e)}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    main()

