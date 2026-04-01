FROM node:20-slim

WORKDIR /app

COPY package.json .
RUN npm install

COPY . .

EXPOSE 5629

CMD ["npx", "vite", "--port", "5629", "--host"]
