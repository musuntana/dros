FROM node:22-bookworm-slim AS base

ARG APT_MIRROR_HOST=mirrors.tuna.tsinghua.edu.cn
ARG NPM_REGISTRY=https://mirrors.tencent.com/npm/

ENV NEXT_TELEMETRY_DISABLED=1

WORKDIR /app/frontend

RUN if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
      sed -i "s|deb.debian.org|${APT_MIRROR_HOST}|g; s|security.debian.org|${APT_MIRROR_HOST}|g" /etc/apt/sources.list.d/debian.sources; \
    fi \
    && npm config set registry "${NPM_REGISTRY}" \
    && npm config set fetch-retries 5 \
    && npm config set fetch-retry-mintimeout 20000 \
    && npm config set fetch-retry-maxtimeout 120000

FROM base AS deps

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit

FROM base AS builder

ENV NEXT_STANDALONE=true

COPY --from=deps /app/frontend/node_modules ./node_modules
COPY frontend ./

RUN mkdir -p public
RUN npm run build

FROM node:22-bookworm-slim AS runtime

ENV NEXT_TELEMETRY_DISABLED=1 \
    NODE_ENV=production \
    HOSTNAME=0.0.0.0 \
    PORT=3000

WORKDIR /app/frontend

RUN addgroup --system nodejs \
    && adduser --system --ingroup nodejs nextjs

COPY --from=builder --chown=nextjs:nodejs /app/frontend/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/frontend/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /app/frontend/public ./public

EXPOSE 3000

USER nextjs

CMD ["node", "server.js"]
