# syntax=docker/dockerfile:1.7

FROM node:24-alpine AS frontend-builder

ARG PNPM_VERSION=12.4.2
ENV SOURCE_DATE_EPOCH=0
WORKDIR /workspace/frontend

ARG SITE_URL=http://127.0.0.1:8101
ENV SITE_URL=${SITE_URL}

RUN --mount=type=cache,target=/root/.npm \
    npm install --global "pnpm@${PNPM_VERSION}"
COPY --link package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN --mount=type=cache,target=/root/.npm \
    pnpm install --frozen-lockfile --ignore-scripts
COPY --link . ./
RUN pnpm rebuild \
    && pnpm build

FROM node:24-alpine AS runtime
ENV NODE_ENV=production HOSTNAME=0.0.0.0 PORT=8101
WORKDIR /app/frontend/.next/standalone
COPY --link --from=frontend-builder --chown=1000:1000 /workspace/frontend/.next/standalone ./
COPY --link --from=frontend-builder --chown=1000:1000 /workspace/frontend/.next/static ./.next/static
COPY --link --from=frontend-builder --chown=1000:1000 /workspace/frontend/public ./public
USER node
EXPOSE 8101
CMD ["node", "server.js"]
