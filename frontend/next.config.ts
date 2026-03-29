import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Hot-reload for Docker volumes
  experimental: {
    // App Router is active by default in Next.js 15
  },
  // Backend API proxy
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
