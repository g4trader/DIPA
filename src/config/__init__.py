"""
Módulo de configuração.

Este módulo contém configurações e utilitários de configuração do sistema.
Este diretório (src/config/) contém arquivos de configuração específicos,
enquanto src/config.py contém a configuração principal do projeto.
"""

# Para compatibilidade com imports como "from src.config import config",
# importamos o módulo config.py do diretório pai usando importlib
import sys
import os
import importlib.util

# Caminho para config.py (está em src/config.py, não em src/config/config.py)
_parent_dir = os.path.dirname(os.path.dirname(__file__))
_config_py_path = os.path.join(_parent_dir, 'config.py')

if os.path.exists(_config_py_path):
    try:
        # Carrega o módulo config.py diretamente
        spec = importlib.util.spec_from_file_location("src.config_module", _config_py_path)
        config_module = importlib.util.module_from_spec(spec)
        sys.modules["src.config_module"] = config_module
        spec.loader.exec_module(config_module)
        
        # Acessa a instância 'config' do módulo config.py
        # (config.py tem: config = Config() na linha 167)
        config = config_module.config
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Erro ao importar config.py: {str(e)}")
        config = None
else:
    config = None
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(f"Arquivo config.py não encontrado em {_config_py_path}")

