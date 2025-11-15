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
    // Resolve caminho absoluto da raiz do projeto
    const projectRoot = path.resolve(__dirname);
    
    // Adiciona alias para @ apontando para a raiz do projeto
    // Usa tanto o alias simples quanto aliases específicos para cada pasta
    config.resolve.alias = {
      ...config.resolve.alias,
      '@': projectRoot,
      '@/lib': path.join(projectRoot, 'lib'),
      '@/components': path.join(projectRoot, 'components'),
      '@/types': path.join(projectRoot, 'types'),
      '@/app': path.join(projectRoot, 'app'),
      '@/styles': path.join(projectRoot, 'styles'),
      '@/assets': path.join(projectRoot, 'assets'),
    };
    
    // Garante que os módulos sejam resolvidos corretamente
    config.resolve.modules = [
      ...(Array.isArray(config.resolve.modules) ? config.resolve.modules : []),
      projectRoot,
      'node_modules',
    ];
    
    // Garante extensões de arquivo sejam reconhecidas
    config.resolve.extensions = [
      '.js',
      '.jsx',
      '.ts',
      '.tsx',
      '.json',
      ...(config.resolve.extensions || []),
    ];
    
    return config;
  },
};

export default nextConfig;
