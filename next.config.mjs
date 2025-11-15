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
    config.resolve.alias = {
      ...config.resolve.alias,
      '@': __dirname,
    };
    return config;
  },
};

export default nextConfig;
