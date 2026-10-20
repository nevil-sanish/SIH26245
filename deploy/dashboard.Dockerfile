FROM node:22.11.0-alpine AS build
WORKDIR /app
ARG NEXT_PUBLIC_API
ENV NEXT_PUBLIC_API=$NEXT_PUBLIC_API NEXT_TELEMETRY_DISABLED=1
COPY package.json package-lock.json* ./
RUN npm ci || npm install
COPY . .
RUN npm run build
FROM nginx:1.27.3-alpine
COPY --from=build /app/out /usr/share/nginx/html
