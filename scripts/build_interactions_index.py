#!/usr/bin/env python3
"""
Script CLI para construir índice de embeddings das interações.

Varre a tabela interacoes_agent e gera embeddings para todas as interações
que ainda não possuem embedding associado.
"""

import sys
from pathlib import Path

# Adiciona o diretório raiz ao path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

import os
import logging

# Força uso de SQLite se não especificado
os.environ.setdefault("DB_TYPE", "sqlite")

from src.dw.connection import init_db, get_db_session, create_tables
from src.dw.models import InteracaoAgent, InteracaoEmbedding
from src.agent.memory import indexar_interacao, gerar_embedding

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Função principal do script."""
    print("=" * 80)
    print("CONSTRUÇÃO DO ÍNDICE DE EMBEDDINGS DAS INTERAÇÕES")
    print("=" * 80)
    print()
    
    # Inicializa banco de dados
    try:
        init_db()
        create_tables()  # Garante que a tabela existe
        logger.info("Banco de dados inicializado")
    except Exception as e:
        logger.error(f"Erro ao inicializar banco: {str(e)}")
        sys.exit(1)
    
    # Cria sessão
    session_gen = get_db_session()
    session = next(session_gen)
    
    try:
        # Conta interações totais
        total_interacoes = session.query(InteracaoAgent).count()
        print(f"Total de interações no banco: {total_interacoes}")
        
        if total_interacoes == 0:
            print("❌ Nenhuma interação encontrada. Execute algumas perguntas primeiro.")
            return
        
        # Busca interações que já têm embedding
        interacoes_com_embedding_ids = [
            row[0] for row in session.query(InteracaoEmbedding.interacao_id).all()
        ]
        total_com_embedding = len(interacoes_com_embedding_ids)
        
        print(f"Interações já indexadas: {total_com_embedding}")
        print(f"Interações pendentes: {total_interacoes - total_com_embedding}")
        print()
        
        # Busca interações sem embedding
        if interacoes_com_embedding_ids:
            interacoes_sem_embedding = session.query(InteracaoAgent).filter(
                ~InteracaoAgent.id.in_(interacoes_com_embedding_ids)
            ).all()
        else:
            # Se não há embeddings, todas as interações precisam ser indexadas
            interacoes_sem_embedding = session.query(InteracaoAgent).all()
        
        if not interacoes_sem_embedding:
            print("✅ Todas as interações já possuem embeddings!")
            return
        
        print(f"Iniciando indexação de {len(interacoes_sem_embedding)} interações...")
        print()
        
        # Processa cada interação
        sucessos = 0
        erros = 0
        erros_lista = []
        
        for idx, interacao in enumerate(interacoes_sem_embedding, 1):
            try:
                print(f"[{idx}/{len(interacoes_sem_embedding)}] Processando interação {interacao.id}...", end=" ")
                
                # Gera e salva embedding
                indexar_interacao(
                    session=session,
                    interacao_id=interacao.id,
                    pergunta=interacao.pergunta
                )
                
                session.commit()
                sucessos += 1
                print("✅")
                
            except Exception as e:
                session.rollback()
                erros += 1
                erro_msg = f"Erro na interação {interacao.id}: {str(e)}"
                erros_lista.append(erro_msg)
                logger.error(erro_msg)
                print("❌")
        
        print()
        print("-" * 80)
        print("RESUMO DA INDEXAÇÃO")
        print("-" * 80)
        print(f"✅ Sucessos: {sucessos}")
        print(f"❌ Erros: {erros}")
        print(f"📊 Total processado: {sucessos + erros}")
        print(f"📈 Taxa de sucesso: {(sucessos / (sucessos + erros) * 100):.1f}%")
        
        if erros > 0:
            print()
            print("ERROS ENCONTRADOS:")
            for erro in erros_lista[:10]:  # Mostra apenas os 10 primeiros erros
                print(f"  - {erro}")
            if len(erros_lista) > 10:
                print(f"  ... e mais {len(erros_lista) - 10} erro(s)")
        
        print()
        print("✅ Indexação concluída!")
        
    except KeyboardInterrupt:
        print()
        print("\n⚠️  Interrompido pelo usuário. Fazendo rollback...")
        session.rollback()
        sys.exit(1)
    except Exception as e:
        logger.error(f"Erro inesperado: {str(e)}")
        import traceback
        traceback.print_exc()
        session.rollback()
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    main()

