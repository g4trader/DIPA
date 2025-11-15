/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  
  // Next.js 14+ usa automaticamente o tsconfig.json para path aliases
  // Mas podemos verificar se está configurado corretamente
  // O baseUrl e paths no tsconfig.json devem ser suficientes
};

export default nextConfig;
