import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Docker volume mount'ta hot-reload için
  experimental: {
    // App Router - default zaten aktif
  },
  // Backend API proxy: /api isteklerini FastAPI'ye yönlendir
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
