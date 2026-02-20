/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  reactStrictMode: true,
  experimental: {
    serverComponentsExternalPackages: [],
  },
  env: {
    API_URL: process.env.API_URL || "http://localhost:8000",
  },
};

module.exports = nextConfig;
