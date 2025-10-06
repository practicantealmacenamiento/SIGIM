const BACKEND = process.env.NEXT_PUBLIC_BACKEND_ORIGIN || "http://localhost:8000";
const PREFIX  = process.env.NEXT_PUBLIC_API_PREFIX || "/api/v1";

/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      // Proxy a Django con prefijo versionado
      { source: "/api/:path*", destination: `${BACKEND}${PREFIX}/:path*` },

      // (opcional) media protegido si lo usas
      { source: "/secure-media/:path*", destination: `${BACKEND}${PREFIX}/secure-media/:path*` },
    ];
  },
};

export default nextConfig;
