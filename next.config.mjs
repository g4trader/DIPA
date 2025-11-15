import path from 'path';
import { fileURLToPath } from 'url';

// Em módulos ESM, __dirname não existe, então criamos ele
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  
  // Configuração explícita de path aliases para garantir compatibilidade com Vercel
  webpack: (config, { buildId, dev, isServer, defaultLoaders, webpack }) => {
    // Adiciona alias para @ apontando para a raiz do projeto
    // Usamos path.resolve para garantir caminho absoluto
    config.resolve.alias = {
      ...config.resolve.alias,
      '@': path.resolve(__dirname),
    };
    
    // Garante que os módulos sejam resolvidos corretamente
    config.resolve.modules = [
      ...(config.resolve.modules || []),
      path.resolve(__dirname),
    ];
    
    return config;
  },
};

export default nextConfig;
