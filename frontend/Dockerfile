FROM node:22-alpine AS builder

ARG NPM_VERSION=11.16.0
ARG VIDEO_API_BASE_URL=

ENV VIDEO_API_BASE_URL=${VIDEO_API_BASE_URL}

WORKDIR /app

RUN npm install --global "npm@${NPM_VERSION}"

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:1.28-alpine AS runtime

COPY docker/nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 8080

HEALTHCHECK --interval=10s --timeout=3s --retries=6 \
  CMD wget --quiet --output-document=- http://127.0.0.1:8080/healthz || exit 1
