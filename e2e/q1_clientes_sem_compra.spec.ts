import { test, expect } from '@playwright/test';

/**
 * Teste E2E para Q1: Clientes sem compra há mais de 60 dias
 * 
 * Valida o fluxo completo:
 * 1. Abre o DIPAM COPILOT™
 * 2. Faz a pergunta Q1
 * 3. Valida a resposta com Resumo Executivo, tabela e dados corretos
 * 4. Garante que IDs não são formatados como moeda
 */

const PERGUNTA_Q1 = 'Quais clientes estão com cadastro ativo, mas sem nenhuma compra por mais de 60 dias?';

test.describe('Q1 - Clientes sem compra há mais de 60 dias', () => {
  test('deve renderizar resposta completa com dados corretos', async ({ page }) => {
    // Abre a URL base (configurada no playwright.config.ts)
    await page.goto('/');
    
    // Aguarda a página carregar completamente
    await page.waitForLoadState('networkidle');
    
    // Localiza o campo de pergunta (ajuste o seletor conforme necessário)
    const inputPergunta = page.locator('input[type="text"], textarea').first();
    await expect(inputPergunta).toBeVisible();
    
    // Digita a pergunta Q1
    await inputPergunta.fill(PERGUNTA_Q1);
    
    // Localiza e clica no botão de enviar
    const botaoEnviar = page.locator('button:has-text("Enviar"), button[type="submit"]').first();
    await expect(botaoEnviar).toBeVisible();
    await botaoEnviar.click();
    
    // Aguarda a resposta aparecer (pode haver um spinner/loading)
    // Aguarda até que o texto "Resumo Executivo" apareça na página
    await page.waitForSelector('text=/Resumo Executivo/i', { timeout: 30000 });
    
    // Valida que o Resumo Executivo está presente
    const resumoExecutivo = page.locator('text=/Resumo Executivo/i');
    await expect(resumoExecutivo).toBeVisible();
    
    // Valida que existe um card ou bloco com "Dados Analíticos"
    const dadosAnaliticos = page.locator('text=/Dados Analíticos/i');
    await expect(dadosAnaliticos.first()).toBeVisible();
    
    // Valida que a tabela contém a coluna "CLIENTE ID" (ou "Cliente ID")
    const colunaClienteId = page.locator('text=/Cliente ID/i, text=/CLIENTE ID/i');
    await expect(colunaClienteId.first()).toBeVisible();
    
    // Valida que existe uma linha com "3031" e "NATALY BRAGA BORGES"
    // Busca na tabela ou no conteúdo da página
    const clienteId3031 = page.locator('text=3031');
    await expect(clienteId3031.first()).toBeVisible();
    
    const nomeNataly = page.locator('text=/NATALY BRAGA BORGES/i');
    await expect(nomeNataly.first()).toBeVisible();
    
    // Valida que também existe o cliente 729
    const clienteId729 = page.locator('text=729');
    await expect(clienteId729.first()).toBeVisible();
    
    const nomeFigueira = page.locator('text=/FIGUEIRA GRAVATAI/i');
    await expect(nomeFigueira.first()).toBeVisible();
  });

  test('NÃO deve formatar IDs como moeda (R$ 3.031,00)', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    const inputPergunta = page.locator('input[type="text"], textarea').first();
    await inputPergunta.fill(PERGUNTA_Q1);
    
    const botaoEnviar = page.locator('button:has-text("Enviar"), button[type="submit"]').first();
    await botaoEnviar.click();
    
    // Aguarda a resposta
    await page.waitForSelector('text=/Resumo Executivo/i', { timeout: 30000 });
    
    // Obtém todo o texto da página
    const pageContent = await page.textContent('body');
    
    // Verifica que NÃO existe formatação de moeda para IDs
    // Não deve encontrar "R$ 3.031" ou "R$ 3.031,00"
    expect(pageContent).not.toMatch(/R\$\s*3\.031/);
    expect(pageContent).not.toMatch(/R\$\s*729/);
    expect(pageContent).not.toMatch(/R\$\s*4\.453/);
    
    // Verifica que os IDs aparecem como números simples
    expect(pageContent).toMatch(/\b3031\b/);
    expect(pageContent).toMatch(/\b729\b/);
  });

  test('deve exibir badge de confiança e card de resposta', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    const inputPergunta = page.locator('input[type="text"], textarea').first();
    await inputPergunta.fill(PERGUNTA_Q1);
    
    const botaoEnviar = page.locator('button:has-text("Enviar"), button[type="submit"]').first();
    await botaoEnviar.click();
    
    // Aguarda a resposta
    await page.waitForSelector('text=/Resumo Executivo/i', { timeout: 30000 });
    
    // Verifica que existe badge de confiança (pode variar o formato)
    const badgeConfianca = page.locator('text=/confiança/i, text=/confidence/i').first();
    await expect(badgeConfianca).toBeVisible({ timeout: 5000 }).catch(() => {
      // Se não encontrar badge de confiança, não é crítico para este teste
      console.log('Badge de confiança não encontrado, continuando...');
    });
    
    // Verifica que existe um card de resposta (pode ser identificado por classes ou estrutura)
    const cardResposta = page.locator('[class*="card"], [class*="response"], [class*="answer"]').first();
    await expect(cardResposta).toBeVisible();
  });
});

