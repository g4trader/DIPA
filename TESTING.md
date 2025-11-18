# Testes Automatizados - DIPAM COPILOT™

Este documento descreve como executar os testes automatizados do frontend do DIPAM COPILOT™.

## 📋 Estrutura de Testes

### Testes de Componente (Unit/UI)
- **Localização**: `__tests__/`
- **Stack**: Jest + React Testing Library
- **Objetivo**: Validar que os componentes renderizam corretamente os dados do backend

### Testes E2E (End-to-End)
- **Localização**: `e2e/`
- **Stack**: Playwright
- **Objetivo**: Validar o fluxo completo da aplicação em produção

## 🚀 Comandos Rápidos

### Testes de Componente

```bash
# Rodar todos os testes de componente
npm test

# Rodar em modo watch (re-executa ao salvar arquivos)
npm run test:watch

# Rodar com cobertura de código
npm run test:coverage
```

### Testes E2E

```bash
# Rodar todos os testes E2E
npm run test:e2e

# Rodar com interface gráfica do Playwright
npm run test:e2e:ui

# Rodar com navegador visível (headed mode)
npm run test:e2e:headed

# Rodar contra URL específica
FRONTEND_BASE_URL=https://dipam.smartiasolutions.br npm run test:e2e
```

## 📝 Testes Implementados

### Teste de Componente: `ResponseDashboard.clientes_sem_compra.spec.tsx`

Valida que o componente `ResponseDashboard` renderiza corretamente:

- ✅ Resumo Executivo
- ✅ Tabela com cabeçalhos corretos ("Cliente ID", "Nome", "Dias sem Compra")
- ✅ Dados dos clientes (729, 3031, 4453)
- ✅ **IDs NÃO formatados como moeda** (não deve aparecer "R$ 3.031,00")
- ✅ Seção "Dados Analíticos"

### Teste E2E: `q1_clientes_sem_compra.spec.ts`

Valida o fluxo completo da pergunta Q1:

- ✅ Abre o DIPAM COPILOT™
- ✅ Digita a pergunta: "Quais clientes estão com cadastro ativo, mas sem nenhuma compra por mais de 60 dias?"
- ✅ Valida resposta com Resumo Executivo
- ✅ Valida tabela com "CLIENTE ID"
- ✅ Valida presença de clientes 3031 e NATALY BRAGA BORGES
- ✅ **Garante que NÃO existe "R$ 3.031,00" na página**

## 🔧 Configuração

### Variáveis de Ambiente

Para testes E2E, você pode configurar a URL base:

```bash
export FRONTEND_BASE_URL=https://dipam.smartiasolutions.br
```

Ou passar inline:

```bash
FRONTEND_BASE_URL=https://dipam.smartiasolutions.br npm run test:e2e
```

### Instalação de Dependências

Se você ainda não instalou as dependências de teste:

```bash
npm install --save-dev @playwright/test @testing-library/react @testing-library/jest-dom jest jest-environment-jsdom
```

E instalar os navegadores do Playwright:

```bash
npx playwright install --with-deps
```

## 🔄 CI/CD

Os testes rodam automaticamente no GitHub Actions em cada:

- Push para `main` ou `develop`
- Pull Request para `main` ou `develop`

O workflow está configurado em `.github/workflows/frontend-tests.yml` e inclui:

1. **Job `unit-ui`**: Roda testes de componente
2. **Job `e2e-q1`**: Roda testes E2E contra a URL configurada

## 📊 Cobertura

Para ver a cobertura de código:

```bash
npm run test:coverage
```

O relatório será gerado em `coverage/`.

## 🐛 Troubleshooting

### Erro: "Cannot find module '@testing-library/react'"

Execute:
```bash
npm install --save-dev @testing-library/react @testing-library/jest-dom
```

### Erro: "Playwright browsers not installed"

Execute:
```bash
npx playwright install --with-deps
```

### Testes E2E falhando por timeout

Aumente o timeout no arquivo de teste ou verifique se a URL está acessível:

```typescript
await page.waitForSelector('text=/Resumo Executivo/i', { timeout: 60000 });
```

## 📚 Recursos

- [Jest Documentation](https://jestjs.io/docs/getting-started)
- [React Testing Library](https://testing-library.com/react)
- [Playwright Documentation](https://playwright.dev/docs/intro)
