import fs from "node:fs";
import path from "node:path";
import type { NextConfig } from "next";

function hydrateRootEnv() {
  const rootEnvPath = path.resolve(process.cwd(), "..", ".env");
  if (!fs.existsSync(rootEnvPath)) {
    return;
  }

  const raw = fs.readFileSync(rootEnvPath, "utf-8");
  for (const line of raw.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) {
      continue;
    }

    const separatorIndex = trimmed.indexOf("=");
    if (separatorIndex <= 0) {
      continue;
    }

    const key = trimmed.slice(0, separatorIndex).trim();
    if (!key || process.env[key] !== undefined) {
      continue;
    }

    const value = trimmed.slice(separatorIndex + 1).trim();
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      process.env[key] = value.slice(1, -1);
      continue;
    }

    process.env[key] = value;
  }
}

hydrateRootEnv();

const nextConfig: NextConfig = {
  // Hot-reload for Docker volumes
  experimental: {
    // App Router is active by default in Next.js 15
  },
  async headers() {
    return [
      {
        source: "/sw.js",
        headers: [
          {
            key: "Cache-Control",
            value: "no-cache, no-store, must-revalidate",
          },
        ],
      },
      {
        source: "/manifest.json",
        headers: [
          {
            key: "Cache-Control",
            value: "public, max-age=0, must-revalidate",
          },
        ],
      },
    ];
  },
  // Backend API proxy
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.API_INTERNAL_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
