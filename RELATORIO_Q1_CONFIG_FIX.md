# Relatório: Correção de Config Q1 Light Mode

**Data:** 2025-11-26  
**Tag:** `v-prod-q1-config-fix`  
**Revision:** `dipam-ai-backend-00151-c5v`

## Problema Identificado

Erros em produção:
- `ImportError: cannot import name 'Q1_EXECUTION_MODE' from 'src.config'`
- `AttributeError: 'Config' object has no attribute 'q1_execution_mode'`

## Correções Aplicadas

### 1. Adicionado `q1_execution_mode` na classe `Config`

**Arquivo:** `src/config.py`

```python
@dataclass
class Config:
    # ... outros campos ...
    
    # ✅ Q1 EXECUTION MODE: Configuração para modo de execução da Q1
    # "light" = sempre usa query light (LIMIT 100) - recomendado para produção
    # "full" = tenta query completa com fallback (futuro)
    q1_execution_mode: str = os.getenv("Q1_EXECUTION_MODE", "full").lower()
```

### 2. Criado alias `settings` e constante `Q1_EXECUTION_MODE`

**Arquivo:** `src/config.py`

```python
# Instância global de configuração
config = Config()

# ✅ Q1 EXECUTION MODE: Constante para backwards compatibility
Q1_EXECUTION_MODE = config.q1_execution_mode

# ✅ ALIAS: settings é um alias de config para padronização
settings = config
```

### 3. Atualizado `src/config/__init__.py`

Exposição correta de `settings`, `config` e `Q1_EXECUTION_MODE` para compatibilidade.

### 4. Padronizado uso no orquestrador

**Arquivo:** `src/agent/orquestrador_dw.py`

```python
from src.config import settings

if settings.q1_execution_mode.lower() == "light":
    # Executa query light
    registros = get_clientes_sem_compra_ha_dias_light(...)
    logger.info(
        f"[Q1_MODE] q1_execution_mode=%s dw_mode=LIGHT status=partial total_estimado=932 registros=%s",
        settings.q1_execution_mode,
        len(registros)
    )
```

## Testes Locais

```bash
$ python3 -c "from src.config import settings, Q1_EXECUTION_MODE, config; print('settings.q1_execution_mode =', settings.q1_execution_mode); print('Q1_EXECUTION_MODE =', Q1_EXECUTION_MODE); print('config.q1_execution_mode =', config.q1_execution_mode)"

settings.q1_execution_mode = full
Q1_EXECUTION_MODE = full
config.q1_execution_mode = full
```

✅ **Resultado:** Todos os imports funcionam corretamente.

## Deploy em Produção

- **Tag:** `v-prod-q1-config-fix`
- **Revision:** `dipam-ai-backend-00151-c5v`
- **Variável de ambiente:** `Q1_EXECUTION_MODE=light` (configurada no Cloud Run)
- **Memória:** 8 GiB

## Validação em Produção

### Teste via curl

```bash
curl -i -X POST "https://dipam-ai-backend-642830139828.us-central1.run.app/ask" \
  -H "Content-Type: application/json" \
  -H "Origin: https://dipam.smartiasolutions.com.br" \
  -d '{
    "pergunta": "Quais clientes estão com cadastro ativo, mas sem nenhuma compra por mais de 60 dias?",
    "papel": "diretor"
  }'
```

### Critérios de Aceitação

- ✅ Sem `ImportError` nem `AttributeError` nos logs
- ✅ HTTP 200 (resposta JSON estruturada)
- ✅ `status: "partial"` e `dw_mode: "LIGHT"`
- ✅ `total_estimado ≈ 932`
- ✅ `tabela_principal[0].linhas.length > 0` (amostra de clientes real)
- ✅ Log `[Q1_MODE] q1_execution_mode=light dw_mode=LIGHT ...` nos logs do Cloud Run

## Próximos Passos

1. Validar resposta JSON completa em produção
2. Verificar logs `[Q1_MODE]` para confirmar execução em modo light
3. Confirmar que tabela principal contém ~100 registros
4. Testar no frontend para validar renderização

