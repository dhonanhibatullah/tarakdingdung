# syntax=docker/dockerfile:1

################################################################################
# Build stage — install deps and produce the standalone Next server bundle
################################################################################
FROM node:22-alpine AS builder

WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1

# Pin pnpm to the version the lockfile was written with, from package.json's
# `packageManager` field.
RUN corepack enable && corepack prepare pnpm@12.3.4 --activate

# Dependency layer: rebuilt only when the manifest or lockfile changes, not on
# every source edit.
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

COPY . .
RUN pnpm build

################################################################################
# Runtime stage — ship the standalone bundle only, run unprivileged
################################################################################
FROM node:22-alpine AS runtime

WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

RUN addgroup -S nextjs && adduser -S -G nextjs -u 10001 nextjs

# `output: "standalone"` (next.config.ts) emits a self-contained server.js with
# a trimmed node_modules; static assets and public/ sit beside it.
COPY --from=builder --chown=nextjs:nextjs /app/public ./public
COPY --from=builder --chown=nextjs:nextjs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nextjs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000

# Node 22 has a global fetch; /login is public and always 200 (protected
# routes 307 to it without a session, which would still resolve r.ok).
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD node -e "fetch('http://127.0.0.1:'+(process.env.PORT||3000)+'/login').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"

CMD ["node", "server.js"]
