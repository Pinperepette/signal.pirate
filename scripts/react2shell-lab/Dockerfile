FROM node:20-slim

WORKDIR /app

# Installa Next.js vulnerabile (16.0.6 usa react-server-dom-webpack 19.1.0)
RUN npx create-next-app@16.0.6 vuln-app --yes --use-npm 2>/dev/null

WORKDIR /app/vuln-app

# Build
RUN npm run build

EXPOSE 3000

CMD ["npm", "run", "start"]
