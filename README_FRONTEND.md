# DIPAM COPILOT™ - Frontend

## Estrutura Visual dos Cards de Resposta

O frontend do DIPAM COPILOT™ foi projetado para oferecer uma experiência visual "WOW" focada no Diretor Comercial, com diferenciação clara entre dados analíticos e preditivos.

### Layout Geral

Cada resposta do COPILOT é renderizada como um card completo com a seguinte estrutura:

```
┌─────────────────────────────────────────────────┐
│  Header: DIPAM COPILOT™ + Intent + Confiança   │
├─────────────────────────────────────────────────┤
│  KPIs Principais (4 cards horizontais)         │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐          │
│  │ KPI1 │ │ KPI2 │ │ KPI3 │ │ KPI4 │          │
│  └──────┘ └──────┘ └──────┘ └──────┘          │
├─────────────────────────────────────────────────┤
│  Resumo Executivo (destaque)                    │
├─────────────────────────────────────────────────┤
│  Insights Preditivos (se houver ML)             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│  │ Churn    │ │ Meta Risk│ │Oportunid.│        │
│  └──────────┘ └──────────┘ └──────────┘        │
├─────────────────────────────────────────────────┤
│  Seções de Dados (tabelas com collapse/expand) │
│  - Vendedores (com barras de progresso)         │
│  - Clientes (com badges de churn)                │
│  - Produtos                                      │
│  - Recomendações                                 │
├─────────────────────────────────────────────────┤
│  Tabela de Oportunidades (se houver ML)         │
├─────────────────────────────────────────────────┤
│  [Ver detalhamento completo] (collapse)          │
├─────────────────────────────────────────────────┤
│  [Ver contexto técnico (debug)] (collapse)      │
└─────────────────────────────────────────────────┘
```

### 1. KPIs no Topo

**Localização**: Primeira seção visível após o header

**Componente**: Grid de 3-4 cards horizontais

**KPIs Exibidos**:
- **Faturamento do Mês**: Valor total realizado (R$)
- **Atingimento da Meta**: Percentual médio (com cores: verde ≥100%, amarelo 95-99%, vermelho <95%)
- **Vendedores em Risco**: Número de vendedores com risco de não bater meta
- **Clientes em Alto Risco de Churn**: Número de clientes com prob_churn ≥ 70% (se insights preditivos disponíveis)

**Visual**:
- Cards com gradiente de fundo baseado na cor do indicador
- Ícones (DollarSign, Percent, AlertCircle)
- Indicadores de tendência (TrendingUp, TrendingDown, Minus)
- Cores dinâmicas baseadas no valor (verde/amarelo/vermelho)

### 2. Resumo Executivo

**Localização**: Logo após os KPIs

**Visual**:
- Card destacado com ícone de Target
- Texto com line-height maior para melhor legibilidade
- Parágrafos separados para clareza
- Sempre menciona insights preditivos quando disponíveis

### 3. Insights Preditivos (FASE 5)

**Localização**: Após o Resumo Executivo

**Diferenciação Visual**:
- **Borda roxa** (`border-purple-500/30`) para destacar como "IA Preditiva"
- **Badge "IA Preditiva"** no header da seção
- **Ícone Brain** para representar inteligência artificial
- **Cards internos** com cores específicas:
  - **Churn**: Laranja (orange-500)
  - **Meta Risk**: Vermelho (red-500)
  - **Oportunidades**: Verde (emerald-500)

**Conteúdo**:
- Total de clientes/vendedores em risco
- Descrição clara do que cada métrica representa

### 4. Tabelas Executivas

#### 4.1. Tabela de Vendedores

**Recursos**:
- **Coluna de posição (#)**: Ranking visual
- **Barras de progresso**: Para atingimento (verde/amarelo/vermelho)
- **Badges de risco**: Se meta_risk_score disponível
- **Botão collapse/expand**: Para não poluir a interface

**Cores**:
- Atingimento ≥ 100%: Verde (emerald-400)
- Atingimento 80-99%: Amarelo (yellow-400)
- Atingimento < 80%: Vermelho (red-400)
- Linhas com meta_risk_flag: Fundo vermelho claro (bg-red-500/5)

#### 4.2. Tabela de Clientes (Churn)

**Recursos**:
- **Badges de risco de churn**: 
  - "Alto" (vermelho) para prob_churn ≥ 70%
  - "Médio" (amarelo) para prob_churn 40-69%
  - "Baixo" (verde) para prob_churn < 40%
- **Percentual de probabilidade**: Exibido abaixo do badge
- **Coluna "Última Compra"**: Dias desde última compra
- **Linhas destacadas**: Clientes com churn_flag ou prob_churn ≥ 70% têm fundo vermelho claro

#### 4.3. Tabela de Oportunidades

**Recursos**:
- **Score de oportunidade**: Badge verde com percentual
- **Barra comparativa**: Mostra fat_atual vs fat_max_12m
- **Visualização clara**: Percentual atual vs máximo histórico

### 5. Detalhamento Técnico

**Localização**: Rodapé do card

**Comportamento**:
- **Sempre colapsado por padrão**
- Botão "Ver detalhamento completo" para expandir tabela completa
- JSON técnico dentro de `<details>` aninhado (sempre colapsado)
- Foco do Diretor: Tabelas e cards, não JSON

### 6. Experiência de Chat

#### 6.1. Campo de Pergunta

**Localização**: Fixo no rodapé da tela (`sticky bottom-0`)

**Comportamento**:
- **Auto-resize**: Textarea cresce até 160px de altura
- **Limpeza automática**: Input é limpo imediatamente após envio
- **Enter para enviar**: Shift+Enter para nova linha
- **Foco automático**: Mantém foco após resposta

#### 6.2. Scroll Automático

**Implementação**: `messagesEndRef` com `scrollIntoView({ behavior: "smooth" })`

**Comportamento**:
- Scroll suave até a última mensagem ao receber resposta
- Não interfere com scroll manual do usuário

#### 6.3. Histórico de Mensagens

**Visual**:
- Pergunta do Diretor: Bubble alinhada à direita (cor diferente)
- Resposta do COPILOT: Card grande com estrutura de dashboard
- Layout similar a GenAI moderna (ChatGPT, Claude, etc.)

### 7. Cores e Estilo

**Paleta de Cores**:
- **Verde (emerald)**: Sucesso, atingimento ≥ 100%, baixo risco
- **Amarelo (yellow)**: Atenção, atingimento 80-99%, risco médio
- **Vermelho (red)**: Alerta, atingimento < 80%, alto risco
- **Laranja (orange)**: Churn (risco de perda de cliente)
- **Roxo (purple)**: IA Preditiva (insights de ML)
- **Azul (sky/blue)**: Ações, botões principais

**Tipografia**:
- Títulos: `text-lg font-semibold`
- KPIs: `text-2xl font-bold`
- Texto corpo: `text-sm leading-relaxed`
- Labels: `text-xs uppercase tracking-wide`

### 8. Responsividade

**Breakpoints**:
- Mobile: Grid de KPIs em 1 coluna
- Tablet: Grid de KPIs em 2 colunas
- Desktop: Grid de KPIs em 4 colunas

**Tabelas**:
- Scroll horizontal em telas pequenas
- Layout completo em telas grandes

---

## Arquivos Principais

- `components/ResponseDashboard.tsx`: Componente principal de renderização de respostas estruturadas
- `components/CopilotAnswerCard.tsx`: Wrapper do card de resposta
- `components/DipaPanel.tsx`: Componente principal do chat com input fixo
- `types/agent.ts`: Tipos TypeScript para respostas estruturadas
- `lib/dipamApi.ts`: Cliente HTTP para API do backend

## Estrutura de Dados

O backend retorna um objeto `CopilotStructuredResponse` com:

```typescript
{
  resumo_executivo: string;
  secoes: Array<{
    titulo: string;
    tipo: "lista_vendedores" | "lista_clientes" | "lista_produtos" | "lista_recomendacoes" | "texto";
    dados: any[];
  }>;
  detalhe_tabela?: {
    titulo?: string;
    colunas: string[];
    linhas: any[][];
  };
  insights_preditivos?: {
    churn?: { total_clientes_risco_alto: number; top_clientes: any[] };
    meta_risk?: { vendedores_risco_alto: number; detalhes: any[] };
    oportunidades?: { total_clientes_potencial: number; top_clientes: any[] };
  };
  contexto_debug?: any;
}
```

O frontend renderiza automaticamente cada seção conforme seu tipo, aplicando estilos e componentes apropriados.

