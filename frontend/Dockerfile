# syntax=docker/dockerfile:1.7

FROM node:24-alpine@sha256:ebfe2f90462722a7a4de65e91990e97fe0d401c70e0e762c5b53302f905ec1c1 AS frontend-builder

ARG PNPM_VERSION=12.4.2
ENV SOURCE_DATE_EPOCH=0
WORKDIR /workspace/frontend

ARG SITE_URL=http://127.0.0.1:8101
ENV SITE_URL=${SITE_URL}
ARG SITE_INDEXABLE=false
ENV SITE_INDEXABLE=${SITE_INDEXABLE}

RUN --mount=type=cache,target=/root/.npm \
    npm install --global "pnpm@${PNPM_VERSION}"
COPY --link package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN --mount=type=cache,target=/root/.npm \
    pnpm install --frozen-lockfile --ignore-scripts
COPY --link . ./
RUN pnpm rebuild \
    && pnpm build

FROM node:24-alpine@sha256:ebfe2f90462722a7a4de65e91990e97fe0d401c70e0e762c5b53302f905ec1c1 AS runtime
ENV NODE_ENV=production HOSTNAME=0.0.0.0 PORT=8101
WORKDIR /app/frontend/.next/standalone
COPY --link --from=frontend-builder --chown=1000:1000 /workspace/frontend/.next/standalone ./
COPY --link --from=frontend-builder --chown=1000:1000 /workspace/frontend/.next/static ./.next/static
COPY --link --from=frontend-builder --chown=1000:1000 /workspace/frontend/public ./public
USER node
EXPOSE 8101
CMD ["node", "server.js"]
