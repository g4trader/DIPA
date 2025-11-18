import { defineConfig, devices } from '@playwright/test';

/**
 * Configuração do Playwright para testes E2E
 * 
 * URL base pode ser configurada via variável de ambiente FRONTEND_BASE_URL
 * Exemplo: FRONTEND_BASE_URL=https://dipam.smartiasolutions.br npm run test:e2e
 */
export default defineConfig({
  testDir: './e2e',
  
  /* Roda testes em paralelo */
  fullyParallel: true,
  
  /* Falha o build se você deixou test.only no CI */
  forbidOnly: !!process.env.CI,
  
  /* Retry no CI se os testes falharem */
  retries: process.env.CI ? 2 : 0,
  
  /* Opt out of parallel tests on CI. */
  workers: process.env.CI ? 1 : undefined,
  
  /* Reporter para usar. Ver https://playwright.dev/docs/test-reporters */
  reporter: 'html',
  
  /* Opções compartilhadas para todos os projetos abaixo. Ver https://playwright.dev/docs/api/class-testoptions. */
  use: {
    /* URL base para usar em navegação como `await page.goto('/')`. */
    baseURL: process.env.FRONTEND_BASE_URL || 'http://localhost:3000',
    
    /* Coleta trace quando retry o teste falhado. Ver https://playwright.dev/docs/trace-viewer */
    trace: 'on-first-retry',
    
    /* Screenshot apenas quando falhar */
    screenshot: 'only-on-failure',
  },

  /* Configura projetos para múltiplos navegadores */
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },

    // Opcional: adicionar outros navegadores
    // {
    //   name: 'firefox',
    //   use: { ...devices['Desktop Firefox'] },
    // },
    // {
    //   name: 'webkit',
    //   use: { ...devices['Desktop Safari'] },
    // },
  ],

  /* Roda o servidor de desenvolvimento antes de iniciar os testes */
  // webServer: {
  //   command: 'npm run dev',
  //   url: 'http://localhost:3000',
  //   reuseExistingServer: !process.env.CI,
  // },
});

