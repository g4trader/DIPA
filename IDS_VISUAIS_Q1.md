# 🎯 IDs Visuais - Resposta Q1 (Clientes sem Compra)

Todos os elementos visuais da resposta Q1 agora possuem IDs únicos para facilitar ajustes específicos.

## 📋 Lista Completa de IDs

### 🎴 Card Principal
- `dipam-card-resposta-principal` - Container principal do card de resposta

### 📑 Header do Card
- `dipam-card-header` - Container do header
- `dipam-card-header-icon` - Ícone ⚡ do DIPAM
- `dipam-card-header-brand` - Container da marca
- `dipam-card-header-brand-name` - Texto "DIPAM COPILOT™"
- `dipam-card-header-brand-tagline` - Texto "Inteligência comercial em tempo real"
- `dipam-card-header-badges` - Container dos badges
- `dipam-card-header-badge-intent` - Badge com o intent (ex: "Consulta Geral")
- `dipam-card-header-badge-confidence` - Badge com % de confiança

### ❓ Pergunta
- `dipam-card-question` - Título com a pergunta do usuário
- `dipam-card-content` - Container do conteúdo principal

### 📊 KPIs (Total de Clientes)
- `dipam-card-kpis-container` - Container dos KPIs
- `dipam-card-kpi-{idx}` - Container de cada KPI (0, 1, 2...)
- `dipam-card-kpi-card-{idx}` - Card individual do KPI

### 📝 Resumo Executivo
- `dipam-card-resumo-executivo` - Container do resumo executivo
- `dipam-card-resumo-executivo-titulo` - Título "Resumo Executivo"
- `dipam-card-resumo-executivo-conteudo` - Conteúdo do resumo

### 📋 Tabela Principal (Q1)
- `dipam-table-clientes-sem-compra` - Container da tabela
- `dipam-table-clientes-sem-compra-titulo` - Título "Clientes sem compra há mais de 60 dias"
- `dipam-table-clientes-sem-compra-data` - Tabela com os dados (DataTable)

### 📄 Paginação da Tabela
- `dipam-card-paginacao-clientes-sem-compra` - Container da paginação
- `dipam-card-btn-pagina-anterior-clientes` - Botão "Anterior"
- `dipam-card-info-paginacao-clientes` - Texto "Página X de Y (Z registros)"
- `dipam-card-btn-pagina-proxima-clientes` - Botão "Próxima"

### 👥 Tabela de Vendedores (Q1)
- `dipam-table-vendedores-clientes-inativos` - Container da tabela de vendedores
- `dipam-table-vendedores-clientes-inativos-data` - Tabela com dados de vendedores

### 💡 Insights Blocks
- `dipam-card-insights-container` - Container de todos os insights

#### Principais Achados / Síntese Analítica
- `dipam-card-principais-achados` - Container do card
- `dipam-card-principais-achados-titulo` - Título da seção
- `dipam-card-principais-achados-conteudo` - Conteúdo (lista de bullets)

#### Implicações Comerciais / Riscos Comerciais
- `dipam-card-implicacoes-comerciais` - Container do card
- `dipam-card-implicacoes-comerciais-titulo` - Título da seção
- `dipam-card-implicacoes-comerciais-conteudo` - Conteúdo (lista de bullets)

#### Plano de Ação Imediato
- `dipam-card-plano-acao` - Container do card
- `dipam-card-plano-acao-titulo` - Título da seção
- `dipam-card-plano-acao-conteudo` - Conteúdo (lista de bullets)

### 🎯 Alvos Prioritários (TOP 10)
- `dipam-card-alvos-prioritarios` - Container do card
- `dipam-card-alvos-prioritarios-titulo` - Título "Alvos Prioritários (TOP 10)"
- `dipam-card-alvos-prioritarios-lista` - Lista de alvos (ul)
- `dipam-card-alvo-prioritario-{idx}` - Cada item da lista (0, 1, 2...)
- `dipam-table-top-10-alvos` - Tabela com top 10 (se disponível)

## 🔍 Como Usar

Para ajustar um elemento específico, me informe o ID e o que precisa ser alterado. Exemplos:

- "Ajustar `dipam-card-resumo-executivo` - aumentar padding e mudar cor de fundo"
- "Modificar `dipam-table-clientes-sem-compra-titulo` - mudar tamanho da fonte"
- "Ajustar espaçamento em `dipam-card-insights-container`"

## 📝 Notas

- IDs seguem o padrão: `dipam-{tipo}-{nome}-{subelemento?}`
- `{idx}` indica índice numérico (0, 1, 2...)
- Todos os IDs são únicos e consistentes

