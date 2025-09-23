const BACKEND = process.env.NEXT_PUBLIC_BACKEND_ORIGIN || "http://localhost:8000";

const nextConfig = {
  async rewrites() {
    return [
      // Proxy limpio a Django en /api
      { source: "/api/:path*", destination: `${BACKEND}/api/:path*` },
      // (opcional) media protegido si lo usas
      { source: "/secure-media/:path*", destination: `${BACKEND}/api/secure-media/:path*` },
    ];
  },
};

export default nextConfig;