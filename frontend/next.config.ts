import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Emit a self-contained server bundle so the Docker image can ship just
  // `.next/standalone` + static assets instead of the whole node_modules.
  output: "standalone",
};

export default nextConfig;
