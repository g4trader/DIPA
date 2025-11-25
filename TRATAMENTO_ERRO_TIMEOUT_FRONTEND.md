# Tratamento de Erro de Timeout DW no Frontend

**Data:** 2025-11-25  
**Arquivos modificados:**
- `lib/dipamApi.ts`
- `components/DipaPanel.tsx`

## Implementação

### 1. Classe `DipamApiError` Estendida

**Arquivo:** `lib/dipamApi.ts`

**Mudanças:**
- Adicionado campo `tipo?: "timeout_dw" | "erro_interno"` para identificar tipo de erro
- Adicionado campo `hint?: string` para dicas adicionais ao usuário

**Código:**
```typescript
export class DipamApiError extends Error {
  /** Tipo do erro: "timeout_dw", "erro_interno", ou undefined para erros genéricos */
  tipo?: "timeout_dw" | "erro_interno";
  /** Hint adicional para o usuário (especialmente útil para timeout_dw) */
  hint?: string;
  
  constructor(
    message: string,
    public statusCode?: number,
    public response?: any
  ) {
    super(message);
    this.name = "DipamApiError";
    Object.setPrototypeOf(this, DipamApiError.prototype);
  }
}
```

### 2. Tratamento de Erro na Função `askDipamAgent`

**Arquivo:** `lib/dipamApi.ts`

**Mudanças:**
- Detecta erro de timeout DW (`erro_dw.error_type === "DW_TIMEOUT"`)
- Cria erro customizado com `tipo: "timeout_dw"` e mensagem amigável
- Detecta outros erros internos (`status === "erro_interno"`)
- Cria erro customizado com `tipo: "erro_interno"` e mensagem amigável

**Código:**
```typescript
// ✅ TRATAMENTO ESPECÍFICO: Erro de timeout de DW
if (body?.erro_dw?.error_type === "DW_TIMEOUT") {
  errorMessage = 
    "Sua pergunta exige uma consulta muito pesada no data warehouse e passou do tempo máximo de 20 segundos. " +
    "Tente reduzir o período ou deixar a pergunta mais específica (por exemplo, foque em um fornecedor, linha ou mês).";
  const timeoutError = new DipamApiError(errorMessage, response.status, errorData);
  timeoutError.tipo = "timeout_dw";
  timeoutError.hint = body.erro_dw?.hint || "Tente ajustar o período ou refazer a pergunta.";
  throw timeoutError;
}

// ✅ TRATAMENTO: Outros erros internos
if (body?.status === "erro_interno") {
  errorMessage = body?.mensagem || 
    "O Dipam AI encontrou um erro interno ao processar sua pergunta. Tente novamente em instantes.";
  const internalError = new DipamApiError(errorMessage, response.status, errorData);
  internalError.tipo = "erro_interno";
  throw internalError;
}
```

### 3. Tratamento de Erro no Componente `DipaPanel`

**Arquivo:** `components/DipaPanel.tsx`

**Mudanças:**
- Detecta tipo de erro (`timeout_dw`, `erro_interno`, ou genérico)
- Usa emoji diferente para timeout (⏱️) vs erro genérico (❌)
- Mensagem já vem amigável do backend (não precisa traduzir)

**Código:**
```typescript
if (error instanceof DipamApiError) {
  // ✅ TRATAMENTO ESPECÍFICO: Erro de timeout de DW
  if (error.tipo === "timeout_dw") {
    errorMessage = error.message; // Já contém mensagem amigável
    errorType = "timeout_dw";
  } 
  // ✅ TRATAMENTO: Outros erros internos
  else if (error.tipo === "erro_interno") {
    errorMessage = error.message; // Já contém mensagem amigável
    errorType = "erro_interno";
  }
  // Erro genérico da API
  else {
    errorMessage = error.message;
  }
}

// Para timeout_dw, usa emoji de relógio
const errorAgentMessage: ChatMessage = {
  id: crypto.randomUUID(),
  role: 'assistant',
  content: errorType === "timeout_dw" 
    ? `⏱️ ${errorMessage}` // Usa emoji de relógio para timeout
    : `❌ ${errorMessage}` // Usa emoji de erro para outros erros
};
```

## Fluxo de Erro

### Cenário 1: Timeout de DW

1. **Backend retorna:**
   ```json
   {
     "status": "erro_interno",
     "mensagem": "A consulta de dados demorou mais do que o tempo máximo configurado (20s).",
     "erro_dw": {
       "error_type": "DW_TIMEOUT",
       "hint": "Sugira no front ao usuário ajustar o período ou refazer a pergunta."
     }
   }
   ```

2. **Frontend detecta:**
   - `body.erro_dw.error_type === "DW_TIMEOUT"`

3. **Frontend cria erro:**
   - `DipamApiError` com `tipo: "timeout_dw"`
   - Mensagem amigável: "Sua pergunta exige uma consulta muito pesada..."

4. **UI exibe:**
   - ⏱️ Sua pergunta exige uma consulta muito pesada no data warehouse e passou do tempo máximo de 20 segundos. Tente reduzir o período ou deixar a pergunta mais específica (por exemplo, foque em um fornecedor, linha ou mês).

### Cenário 2: Outro Erro Interno

1. **Backend retorna:**
   ```json
   {
     "status": "erro_interno",
     "mensagem": "Erro na consulta de dados."
   }
   ```

2. **Frontend detecta:**
   - `body.status === "erro_interno"`

3. **Frontend cria erro:**
   - `DipamApiError` com `tipo: "erro_interno"`
   - Mensagem amigável do backend

4. **UI exibe:**
   - ❌ O Dipam AI encontrou um erro interno ao processar sua pergunta. Tente novamente em instantes.

### Cenário 3: Erro Genérico

1. **Backend retorna:**
   - Status HTTP != 200
   - Sem `erro_dw` ou `status: "erro_interno"`

2. **Frontend trata:**
   - Erro genérico com mensagem padrão ou do backend

3. **UI exibe:**
   - ❌ Mensagem de erro genérica

## Benefícios

1. **UX Melhorada:**
   - Diretor não vê "erro técnico"
   - Vê orientação clara: "reduza o período, deixe a pergunta mais específica"

2. **Diferenciação Visual:**
   - Timeout: ⏱️ (relógio)
   - Erro genérico: ❌ (erro)

3. **Mensagens Contextuais:**
   - Timeout: Sugestão de como resolver (reduzir período, ser mais específico)
   - Erro interno: Sugestão de tentar novamente

4. **Extensível:**
   - Fácil adicionar novos tipos de erro no futuro
   - Estrutura preparada para outros erros específicos

## Testes

### Teste 1: Timeout de DW

**Pergunta:** "Quais clientes estão com cadastro ativo, mas sem nenhuma compra por mais de 60 dias?" (com período muito longo)

**Esperado:**
- ⏱️ Mensagem amigável sobre timeout
- Sugestão de reduzir período ou ser mais específico

### Teste 2: Erro Interno

**Pergunta:** Qualquer pergunta que cause erro interno no backend

**Esperado:**
- ❌ Mensagem amigável sobre erro interno
- Sugestão de tentar novamente

### Teste 3: Erro Genérico

**Pergunta:** Qualquer pergunta que cause erro genérico (ex.: CORS, rede)

**Esperado:**
- ❌ Mensagem de erro genérica
- Informação sobre verificar conexão

## Conclusão

✅ **Tratamento de erro implementado:**
- Timeout DW: Mensagem amigável com sugestão de ação
- Erro interno: Mensagem amigável com sugestão de tentar novamente
- Erro genérico: Mensagem padrão

✅ **UX melhorada:**
- Diretor não vê erros técnicos
- Vê orientações claras sobre como resolver

✅ **Extensível:**
- Fácil adicionar novos tipos de erro
- Estrutura preparada para evolução

