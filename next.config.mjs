import path from 'path';
import { fileURLToPath } from 'url';

// Em módulos ESM, __dirname não existe, então criamos ele
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// 🔒 GUARDRAIL: Bloqueia uso de mock em produção na Vercel
// Este check impede que alguém faça deploy do mock por engano na instância de produção
// IMPORTANTE: Só bloqueia se estiver rodando na Vercel (VERCEL=true) e for projeto de produção
if (process.env.NEXT_PUBLIC_DIPAM_ENV === "mock" && process.env.NODE_ENV === "production" && process.env.VERCEL === "1") {
  // Permite mock apenas se for explicitamente o projeto mock da Vercel
  // Verifica se é o projeto dipam-vercel (mock) ou dipam-smartiasolutions (prod)
  const vercelProjectName = process.env.VERCEL_PROJECT_NAME || "";
  const isMockProject = vercelProjectName === "dipam-vercel";
  
  if (!isMockProject) {
    throw new Error(
      "❌ Build abortado: mock não pode ser usado em produção.\n" +
      "O ambiente NEXT_PUBLIC_DIPAM_ENV=mock só é permitido no projeto dipam-vercel.\n" +
      "Para produção (dipam-smartiasolutions), configure NEXT_PUBLIC_DIPAM_ENV=prod"
    );
  }
  
  console.log("✅ [GUARDRAIL] Mock permitido no projeto dipam-vercel (ambiente de laboratório)");
}

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  
  // Habilita standalone output para Cloud Run
  // Isso cria um servidor Node.js otimizado que pode ser executado independentemente
  output: 'standalone',
  
  // Garante que arquivos JSON em mock/data sejam incluídos no build standalone
  // Isso é necessário para que os dados mock estejam disponíveis na Vercel
  experimental: {
    outputFileTracingIncludes: {
      '/api/mock/ask': ['./mock/data/**/*.json'],
      '/api/mock/data': ['./mock/data/**/*.json'],
      '*': ['./mock/data/**/*.json'], // Inclui para todas as rotas
    },
  },
  
  // Configura variáveis de ambiente públicas (acessíveis no navegador)
  env: {
    NEXT_PUBLIC_DIPAM_ENV: process.env.NEXT_PUBLIC_DIPAM_ENV || "prod",
    NEXT_PUBLIC_DIPAM_API_URL: process.env.NEXT_PUBLIC_DIPAM_API_URL,
    NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL || process.env.NEXT_PUBLIC_DIPAM_API_URL,
    NEXT_PUBLIC_BACKEND_URL: process.env.NEXT_PUBLIC_BACKEND_URL || process.env.NEXT_PUBLIC_DIPAM_API_URL,
    NEXT_PUBLIC_PROJECT_ENV: process.env.NEXT_PUBLIC_PROJECT_ENV || (process.env.NEXT_PUBLIC_DIPAM_ENV === "mock" ? "mock" : "production"),
  },
  
  // Configuração explícita de path aliases para garantir compatibilidade com Vercel
  webpack: (config, { buildId, dev, isServer, defaultLoaders, webpack }) => {
    // Resolve caminho absoluto da raiz do projeto
    const projectRoot = path.resolve(__dirname);
    
    // IMPORTANTE: Remove aliases antigos que possam conflitar
    const existingAlias = config.resolve.alias || {};
    
    // Adiciona alias para @ apontando para a raiz do projeto
    // Usa path.join para garantir compatibilidade cross-platform
    config.resolve.alias = {
      ...existingAlias,
      '@': projectRoot,
      '@/lib': path.resolve(projectRoot, 'lib'),
      '@/components': path.resolve(projectRoot, 'components'),
      '@/types': path.resolve(projectRoot, 'types'),
      '@/app': path.resolve(projectRoot, 'app'),
      '@/styles': path.resolve(projectRoot, 'styles'),
      '@/assets': path.resolve(projectRoot, 'assets'),
      '@/mock': path.resolve(projectRoot, 'mock'),
    };
    
    // Garante que os módulos sejam resolvidos corretamente
    // A ordem importa: primeiro o projeto, depois node_modules
    const existingModules = Array.isArray(config.resolve.modules) 
      ? config.resolve.modules 
      : config.resolve.modules 
        ? [config.resolve.modules] 
        : [];
    
    config.resolve.modules = [
      projectRoot,
      ...existingModules.filter(m => m !== projectRoot && m !== 'node_modules'),
      'node_modules',
    ];
    
    // Garante extensões de arquivo sejam reconhecidas
    const existingExts = Array.isArray(config.resolve.extensions)
      ? config.resolve.extensions
      : [];
    
    const requiredExts = ['.js', '.jsx', '.ts', '.tsx', '.json'];
    config.resolve.extensions = [
      ...requiredExts,
      ...existingExts.filter(ext => !requiredExts.includes(ext)),
    ];
    
    // Debug: log dos aliases (também em produção para debug no Vercel)
    if (process.env.NODE_ENV === 'development' || process.env.VERCEL) {
      console.log('[Next.js Webpack Config] Project root:', projectRoot);
      console.log('[Next.js Webpack Config] @ alias:', config.resolve.alias['@']);
      console.log('[Next.js Webpack Config] @/lib alias:', config.resolve.alias['@/lib']);
      console.log('[Next.js Webpack Config] Expected lib/dipamApi.ts at:', path.resolve(projectRoot, 'lib', 'dipamApi.ts'));
    }
    
    return config;
  },
};

export default nextConfig;
