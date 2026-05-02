FROM node:20-alpine AS builder

WORKDIR /app/apps/web

COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm ci

COPY apps/web ./

ARG UMI_APP_API_BASE_URL
ENV UMI_APP_API_BASE_URL=${UMI_APP_API_BASE_URL}

RUN npm run build

FROM nginx:1.27-alpine

RUN printf '%s\n' \
    'server {' \
    '    listen 80;' \
    '    server_name _;' \
    '    root /usr/share/nginx/html;' \
    '    index index.html;' \
    '    location / {' \
    '        try_files $uri $uri/ /index.html;' \
    '    }' \
    '    location = /health {' \
    '        access_log off;' \
    '        add_header Content-Type text/plain;' \
    '        return 200 "ok\n";' \
    '    }' \
    '}' \
    > /etc/nginx/conf.d/default.conf
COPY --from=builder /app/apps/web/dist /usr/share/nginx/html

EXPOSE 80
