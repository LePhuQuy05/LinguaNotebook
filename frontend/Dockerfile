FROM node:20-slim

WORKDIR /app

RUN npm install -g pnpm@9

COPY package.json ./
RUN pnpm install --no-frozen-lockfile 2>/dev/null || true

COPY . .

EXPOSE 3000
CMD ["pnpm", "dev"]
