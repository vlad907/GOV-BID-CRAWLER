FROM node:22-slim

WORKDIR /app

# Install deps first so they're cached unless package.json changes.
COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 3000
CMD ["npm", "run", "dev"]
