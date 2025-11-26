# Endpoint API Q2 - Documentação

## Resumo

Endpoint REST para expor a funcionalidade Q2 (queda de faturamento) via API, permitindo que o frontend consuma tanto o texto executivo quanto os dados estruturados.

## Endpoints Implementados

### 1. `/api/copilot/q2` (Específico para Q2)

**Método:** `POST`

**Request Body:**
```json
{
  "pergunta": "Quais clientes tiveram queda de faturamento de setembro para outubro?"
}
```

**Response (200 OK):**
```json
{
  "tipo": "Q2_QUEDA_FATURAMENTO",
  "periodo": {
    "descricao": "set/25 x out/25",
    "data_ini_mes_anterior": "2025-09-01",
    "data_fim_mes_anterior": "2025-09-30",
    "data_ini_mes_atual": "2025-10-01",
    "data_fim_mes_atual": "2025-10-31"
  },
  "texto_executivo": "Análise de Queda de Faturamento - set/25 x out/25\n\nForam identificados 2326 clientes...",
  "resumo": {
    "total_clientes_queda": 2326,
    "percentual_clientes_queda": 57.3,
    "queda_media_absoluta": 95374.42,
    "queda_media_percentual": 71.48,
    "queda_maxima_absoluta": 843012.12,
    "queda_maxima_percentual": 184.32
  },
  "top_clientes": [
    {
      "nome": "ATACADAO DISTR COM IND LTDA LJ2",
      "cliente_id": 3318,
      "queda_absoluta": 843012.12,
      "queda_percentual": 22.90,
      "faturamento_mes_anterior": 3681404.58,
      "faturamento_mes_atual": 2838392.46,
      "rota": "ROTA 113",
      "vendedor_nome": "ROTA 113",
      "supervisor_nome": "Supervisor A"
    },
    ...
  ],
  "rotas": [
    {
      "rota": "ROTA 113",
      "qtd_clientes_queda": 2,
      "queda_total": 1284448.53
    },
    ...
  ],
  "dados_brutos": { ... }
}
```

**Erros:**

- `400 Bad Request`: Pergunta não é sobre queda de faturamento
- `422 Unprocessable Entity`: Request body inválido (falta campo `pergunta`)
- `500 Internal Server Error`: Erro interno ao processar
- `503 Service Unavailable`: Endpoint Q2 não disponível

### 2. `/ask` (Integração com Q2)

O endpoint `/ask` foi modificado para detectar automaticamente perguntas sobre Q2 e redirecionar para o processamento Q2.

**Comportamento:**
- Se a pergunta for detectada como Q2, usa `executar_q2_via_orquestrador()`
- Se não for Q2, segue o fluxo padrão do LLM
- Retorna `AskResponse` convertido (compatibilidade com frontend existente)

## Arquivos Criados/Modificados

### 1. `src/api/q2_endpoint.py` (Novo)

**Funções principais:**
- `normalizar_resposta_q2()`: Normaliza resposta do orquestrador para formato frontend
- `processar_q2_endpoint()`: Processa pergunta Q2 e retorna resposta normalizada

**Modelos Pydantic:**
- `Q2Request`: Request body
- `Q2Response`: Response body
- `Q2Resumo`: Métricas agregadas
- `Q2TopCliente`: Cliente com queda
- `Q2Rota`: Agregação por rota
- `Q2Periodo`: Período analisado

### 2. `src/api/main.py` (Modificado)

**Mudanças:**
- Importa módulo Q2 endpoint
- Adiciona endpoint `/api/copilot/q2`
- Modifica `/ask` para detectar Q2 e redirecionar

### 3. `tests/test_api_q2.py` (Novo)

**Testes implementados:**
- Endpoint Q2 com pergunta válida
- Endpoint Q2 com pergunta inválida
- Endpoint Q2 sem campo pergunta
- Endpoint Q2 com período não reconhecido
- Integração Q2 com endpoint /ask
- Estrutura da resposta Q2

## Estrutura da Resposta Normalizada

### Campos Obrigatórios

- `tipo`: Sempre `"Q2_QUEDA_FATURAMENTO"`
- `periodo`: Objeto com descrição e datas
- `texto_executivo`: Texto formatado pronto para exibição
- `resumo`: Métricas agregadas
- `top_clientes`: Lista dos top 10 clientes (máximo)
- `rotas`: Lista das top 5 rotas (máximo)
- `dados_brutos`: Dados completos do DW (opcional)

### Resumo de Métricas

- `total_clientes_queda`: Total de clientes com queda
- `percentual_clientes_queda`: % de clientes com queda (se disponível)
- `queda_media_absoluta`: Queda média em R$
- `queda_media_percentual`: Queda média em %
- `queda_maxima_absoluta`: Queda máxima em R$
- `queda_maxima_percentual`: Queda máxima em %

### Top Clientes

Cada cliente contém:
- `nome`: Nome do cliente
- `cliente_id`: ID do cliente
- `queda_absoluta`: Queda absoluta em R$
- `queda_percentual`: Queda percentual
- `faturamento_mes_anterior`: Faturamento no mês anterior
- `faturamento_mes_atual`: Faturamento no mês atual
- `rota`: Código da rota
- `vendedor_nome`: Nome do vendedor
- `supervisor_nome`: Nome do supervisor

### Rotas

Cada rota contém:
- `rota`: Código da rota
- `qtd_clientes_queda`: Quantidade de clientes com queda
- `queda_total`: Queda total da rota em R$

## Exemplos de Uso

### Exemplo 1: Chamada direta ao endpoint Q2

```bash
curl -X POST "http://localhost:8000/api/copilot/q2" \
  -H "Content-Type: application/json" \
  -d '{
    "pergunta": "Quais clientes tiveram queda de faturamento de setembro para outubro?"
  }'
```

### Exemplo 2: Via endpoint /ask (detecção automática)

```bash
curl -X POST "http://localhost:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "pergunta": "Quais clientes tiveram queda de faturamento de setembro para outubro?",
    "papel": "diretor"
  }'
```

### Exemplo 3: Frontend (TypeScript)

```typescript
const response = await fetch('/api/copilot/q2', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    pergunta: 'Quais clientes tiveram queda de faturamento de setembro para outubro?'
  })
});

const data = await response.json();

// Usa texto executivo
console.log(data.texto_executivo);

// Usa métricas
console.log(`Total de clientes: ${data.resumo.total_clientes_queda}`);

// Usa top clientes
data.top_clientes.forEach(cliente => {
  console.log(`${cliente.nome}: ${cliente.queda_absoluta}`);
});
```

## Critérios de Aceite

✅ **Frontend consegue chamar `/api/copilot/q2` com uma pergunta em PT-BR e receber:**
- Texto executivo pronto para exibição
- Estrutura JSON com métricas, top clientes e rotas

✅ **Endpoint não quebra fluxos existentes:**
- `/ask` continua funcionando normalmente
- Detecção Q2 é opcional (fallback para LLM se falhar)

✅ **Testes passando:**
- Testes unitários criados
- Cobertura de casos de sucesso e erro

## Validação

### Testes Implementados

1. ✅ Endpoint Q2 com pergunta válida
2. ✅ Endpoint Q2 com pergunta inválida (retorna 400)
3. ✅ Endpoint Q2 sem campo pergunta (retorna 422)
4. ✅ Endpoint Q2 com período não reconhecido (usa padrão)
5. ✅ Integração Q2 com endpoint /ask
6. ✅ Estrutura da resposta Q2 (todos os campos obrigatórios)

### Validação Manual

```bash
# Teste local (requer servidor rodando)
python3 -c "
import requests
response = requests.post(
    'http://localhost:8000/api/copilot/q2',
    json={'pergunta': 'Quais clientes tiveram queda de faturamento de setembro para outubro?'}
)
print(f'Status: {response.status_code}')
print(f'Tipo: {response.json()[\"tipo\"]}')
print(f'Total clientes: {response.json()[\"resumo\"][\"total_clientes_queda\"]}')
"
```

## Próximos Passos (Opcional)

1. **Cache de respostas Q2:**
   - Implementar cache para perguntas Q2 idênticas
   - TTL baseado no período analisado

2. **Paginação:**
   - Adicionar paginação para `top_clientes` se houver muitos resultados

3. **Filtros adicionais:**
   - Permitir filtros por rota, vendedor, supervisor
   - Permitir ajuste de limites (min_faturamento, min_queda_percentual)

4. **Webhooks:**
   - Notificar frontend quando análise Q2 estiver pronta (para análises longas)

## Notas Técnicas

- **Detecção Q2**: Usa `detectar_intent_q2()` antes de processar
- **Normalização**: Função `normalizar_resposta_q2()` garante estrutura consistente
- **Compatibilidade**: Endpoint `/ask` mantém compatibilidade com frontend existente
- **Erros**: Todos os erros retornam JSON estruturado com CORS headers

