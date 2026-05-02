FROM node:20-alpine AS builder

WORKDIR /app/apps/web

COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm ci

COPY apps/web ./

ARG UMI_APP_API_BASE_URL=http://127.0.0.1:8000
ENV UMI_APP_API_BASE_URL=${UMI_APP_API_BASE_URL}

RUN npm run build

FROM nginx:1.27-alpine

COPY infra/docker/nginx-web.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/apps/web/dist /usr/share/nginx/html

EXPOSE 80
