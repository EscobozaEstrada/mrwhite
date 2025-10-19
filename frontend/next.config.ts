import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  env: {
    JWT_SECRET: process.env.JWT_SECRET,
    NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL,
    NEXT_PUBLIC_APP_NAME: process.env.NEXT_PUBLIC_APP_NAME,
    NEXT_PUBLIC_APP_TITLE: process.env.NEXT_PUBLIC_APP_TITLE,
    NEXT_PUBLIC_APP_DESCRIPTION: process.env.NEXT_PUBLIC_APP_DESCRIPTION,
    NEXT_PUBLIC_DEFAULT_CONVERSATION_TITLE: process.env.NEXT_PUBLIC_DEFAULT_CONVERSATION_TITLE,
  },
  experimental: {
    // @ts-expect-error - allowedDevOrigins not yet in type definitions
    allowedDevOrigins: [
      process.env.FRONTEND_URL || 'http://3.85.132.24',
      'http://3.85.132.24',
      'http://3.85.132.24:5001',
      'http://localhost:5001',
      'http://3.85.132.24:3000',
    ],
  },
  images: {
    remotePatterns: [
      {
        protocol: 'http',
        hostname: '34.228.255.83',
        port: '5001',
        pathname: '/uploads/**',
      },
      {
        protocol: 'https',
        hostname: 'master-white-project.s3.us-east-1.amazonaws.com',
        pathname: '/**',
      },
      {
        protocol: 'https',
        hostname: '*.amazonaws.com',
        pathname: '/**',
      },
    ],
  },
  eslint: {
    ignoreDuringBuilds: true,
  },
  typescript: {
    ignoreBuildErrors: true,
  },
};

export default nextConfig;
