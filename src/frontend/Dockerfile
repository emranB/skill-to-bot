# Purpose: Build and serve the skill-to-bot drawing workspace.
FROM node:22-bookworm-slim AS build
WORKDIR /web
COPY src/frontend/package*.json ./
RUN npm ci
COPY src/frontend ./
RUN npm run build
FROM nginx:1.30.6-alpine
COPY src/frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /web/dist /usr/share/nginx/html
EXPOSE 5173
