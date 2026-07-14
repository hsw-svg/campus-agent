FROM node:24-alpine AS build

WORKDIR /app
COPY apps/web/package.json ./package.json
RUN npm install
COPY apps/web ./
RUN npm run build

FROM nginx:1.27-alpine

COPY infra/docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
