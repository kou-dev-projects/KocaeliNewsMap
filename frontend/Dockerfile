FROM node:22-alpine

WORKDIR /app

# Install dependencies first (caching layer)
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev"]
