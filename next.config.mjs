import path from 'path';
import { fileURLToPath } from 'url';

// Em módulos ESM, __dirname não existe, então criamos ele
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  
  // Habilita standalone output para Cloud Run
  // Isso cria um servidor Node.js otimizado que pode ser executado independentemente
  output: 'standalone',
  
  // Configura variáveis de ambiente públicas (acessíveis no navegador)
  env: {
    NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL || process.env.NEXT_PUBLIC_DIPAM_API_URL,
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
