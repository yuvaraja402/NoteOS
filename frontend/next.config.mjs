/** @type {import('next').NextConfig} */
const nextConfig = {
  // Emits .next/standalone so the Docker runtime image stays small.
  output: "standalone",
  agentRules: false,
};

export default nextConfig;
