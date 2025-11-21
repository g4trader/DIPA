#!/usr/bin/env python3
"""
Script para configurar o ambiente do projeto.

Este script:
1. Cria o ambiente virtual
2. Instala dependências
3. Cria diretórios necessários
4. Configura variáveis de ambiente
5. Inicializa o banco de dados (Postgres via Docker)
"""

import os
import subprocess
import sys
from pathlib import Path
import shutil

def run_command(command, check=True):
    """
    Executa um comando no shell.
    
    Args:
        command: Comando a ser executado
        check: Se True, falha se o comando retornar erro
    """
    print(f"Executando: {command}")
    result = subprocess.run(
        command,
        shell=True,
        check=check,
        capture_output=True,
        text=True
    )
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr)
    return result


def create_venv():
    """Cria o ambiente virtual."""
    venv_path = Path("venv")
    
    if venv_path.exists():
        print("Ambiente virtual já existe. Pulando criação...")
        return
    
    print("Criando ambiente virtual...")
    run_command(f"{sys.executable} -m venv venv")


def install_dependencies():
    """Instala dependências do projeto."""
    print("Instalando dependências...")
    
    # Determina o comando pip baseado no OS
    if os.name == "nt":  # Windows
        pip_cmd = "venv\\Scripts\\pip"
    else:  # Unix/Linux/Mac
        pip_cmd = "venv/bin/pip"
    
    run_command(f"{pip_cmd} install --upgrade pip")
    run_command(f"{pip_cmd} install -r requirements.txt")


def create_directories():
    """Cria diretórios necessários."""
    print("Criando diretórios...")
    
    directories = [
        "data_raw",
        "data_processed",
        "data_warehouse",
        "models",
        "notebooks",
        "logs",
        "features",
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"  Criado: {directory}/")


def create_env_file():
    """Cria arquivo .env se não existir."""
    env_file = Path(".env")
    
    if env_file.exists():
        print("Arquivo .env já existe. Pulando criação...")
        return
    
    print("Criando arquivo .env...")
    
    env_content = """# Configurações do ambiente
ENVIRONMENT=development
DEBUG=True
LOG_LEVEL=INFO

# Configurações de banco de dados
DB_TYPE=postgresql
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=dipam_user
POSTGRES_PASSWORD=dipam_password
POSTGRES_DB=dipam_dw

# Configurações de ML
ML_RANDOM_SEED=42
ML_TEST_SIZE=0.2
ML_CV_FOLDS=5
"""
    
    with open(env_file, "w") as f:
        f.write(env_content)
    
    print("Arquivo .env criado. Por favor, ajuste as configurações se necessário.")


def start_docker():
    """Inicia o Docker Compose."""
    print("Iniciando Docker Compose...")
    
    # Verifica se Docker está instalado
    try:
        run_command("docker --version", check=False)
    except:
        print("Docker não encontrado. Por favor, instale o Docker primeiro.")
        return
    
    # Verifica se Docker Compose está instalado
    try:
        run_command("docker compose version", check=False)
    except:
        print("Docker Compose não encontrado. Por favor, instale o Docker Compose primeiro.")
        return
    
    # Inicia Docker Compose
    print("Iniciando containers...")
    run_command("docker compose up -d")
    
    print("Aguardando banco de dados estar pronto...")
    import time
    time.sleep(5)
    
    print("Docker Compose iniciado com sucesso!")


def initialize_database():
    """Inicializa o banco de dados."""
    print("Inicializando banco de dados...")
    
    try:
        from src.dw.connection import init_db, create_tables
        
        init_db()
        create_tables()
        
        print("Banco de dados inicializado com sucesso!")
    except Exception as e:
        print(f"Erro ao inicializar banco de dados: {str(e)}")
        print("Você pode inicializar manualmente depois.")


def main():
    """Função principal."""
    print("=" * 60)
    print("Configurando ambiente do projeto Dipam AI")
    print("=" * 60)
    print()
    
    # Cria ambiente virtual
    create_venv()
    print()
    
    # Instala dependências
    install_dependencies()
    print()
    
    # Cria diretórios
    create_directories()
    print()
    
    # Cria arquivo .env
    create_env_file()
    print()
    
    # Inicia Docker (opcional)
    response = input("Deseja iniciar o Docker Compose agora? (s/n): ")
    if response.lower() == "s":
        start_docker()
        print()
        
        # Inicializa banco de dados
        response = input("Deseja inicializar o banco de dados agora? (s/n): ")
        if response.lower() == "s":
            initialize_database()
            print()
    
    print("=" * 60)
    print("Configuração concluída!")
    print("=" * 60)
    print()
    print("Próximos passos:")
    print("1. Ative o ambiente virtual:")
    print("   source venv/bin/activate  # Linux/Mac")
    print("   venv\\Scripts\\activate  # Windows")
    print()
    print("2. Configure o arquivo .env com suas credenciais")
    print()
    print("3. Se ainda não iniciou o Docker, execute:")
    print("   docker compose up -d")
    print()
    print("4. Inicialize o banco de dados:")
    print("   python scripts/init_db.py")
    print()
    print("5. Execute o pipeline ETL:")
    print("   python scripts/run_etl.py")
    print()
    print("6. Treine os modelos:")
    print("   python scripts/train_models.py")
    print()


if __name__ == "__main__":
    main()





